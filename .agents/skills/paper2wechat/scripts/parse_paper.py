#!/usr/bin/env python
"""Standalone parser for paper2wechat skill.

This script vendors the proven parsing/image-extraction implementation from the
original core fetcher, while remaining self-contained inside the skill package.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import logging
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import warnings
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None


ARXIV_ID_PATTERN = re.compile(
    r"(?P<id>(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?)",
    re.IGNORECASE,
)

HEADER_CUTOFF_RATIO = 0.06
HEADER_GUARD_RATIO = 0.03
RELAXED_HEADER_EXTRA_RATIO = 0.04
ALT_SIDE_MARGIN_RATIO = 0.02
ALT_TOP_WINDOW_RATIO = 0.68
WIDE_SIDE_MARGIN_RATIO = 0.015
WIDE_TOP_WINDOW_RATIO = 0.80
WIDE_FIGURE_MIN_WIDTH_RATIO = 0.74
CLUSTER_X_GAP_RATIO = 0.28
NEIGHBOR_X_EXPAND_RATIO = 0.42
FRAGMENT_COVERAGE_THRESHOLD = 0.10
# For broad overview/framework figures, prefer wider crops to avoid clipped edges.
FORCE_WIDE_NARROW_RATIO = 0.86
BROAD_TOP_FLOOR_RATIO = 0.008
BROAD_SIDE_PAD_RATIO = 0.028
BROAD_PAD_X_SCALE = 0.055
BROAD_PAD_Y_SCALE = 0.045

MAX_SOURCE_IMAGES = 12
SOURCE_MIN_BYTES = 12 * 1024
SOURCE_RASTER_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
)
SOURCE_VECTOR_EXTENSIONS = (".pdf",)
SOURCE_GRAPHIC_EXTENSIONS = SOURCE_RASTER_EXTENSIONS + SOURCE_VECTOR_EXTENSIONS + (".eps", ".ps", ".svg")

HTTP_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
HTTP_MAX_ATTEMPTS = 4
HTTP_BACKOFF_BASE_SECONDS = 1.4

# If the PDF is large, prefer skipping TeX/source fetching by default.
# This avoids long source downloads and huge unpack times on oversized papers.
AUTO_SKIP_SOURCE_PDF_BYTES = 30 * 1024 * 1024
AUTO_SKIP_SOURCE_PDF_PAGES = 50


class _PDFMinerFontBBoxFilter(logging.Filter):
    """Suppress noisy FontBBox warnings from malformed embedded font descriptors."""

    NEEDLE = "Could not get FontBBox from font descriptor because"

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        return self.NEEDLE not in message


def _configure_runtime_noise_filters() -> None:
    """Keep parser stderr clean for known non-fatal third-party warnings."""

    warnings.filterwarnings(
        "ignore",
        message=r"Could not get FontBBox from font descriptor because .* cannot be parsed as 4 floats",
    )

    font_logger = logging.getLogger("pdfminer.pdffont")
    if not any(isinstance(flt, _PDFMinerFontBBoxFilter) for flt in font_logger.filters):
        font_logger.addFilter(_PDFMinerFontBBoxFilter())


_configure_runtime_noise_filters()


@dataclass
class ImageInfo:
    url: str
    caption: str
    position: int
    relevance_score: float = 0.5


@dataclass
class Section:
    title: str
    content: str
    level: int = 1


@dataclass
class Paper:
    title: str
    authors: List[str] = field(default_factory=list)
    affiliations: List[str] = field(default_factory=list)
    abstract: str = ""
    published_date: Optional[datetime] = None
    arxiv_id: Optional[str] = None
    pdf_url: Optional[str] = None
    sections: List[Section] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    url: Optional[str] = None


class FetchError(RuntimeError):
    """Raised when paper fetching/parsing fails."""


class PaperFetcher:
    """Fetch paper content from arXiv or local PDF."""

    def __init__(
        self,
        cache_dir: str = ".paper2wechat",
        timeout: int = 30,
        *,
        verbose: bool = False,
        log_interval_seconds: float = 2.0,
        source_policy: str = "auto",
    ):
        self.timeout = timeout
        self.verbose = bool(verbose)
        self.log_interval_seconds = float(log_interval_seconds)
        self.source_policy = (source_policy or "auto").strip().lower()
        self.cache_root = Path(cache_dir)
        self.paper_key = ""
        self.paper_dir = self.cache_root
        self.download_dir = self.paper_dir / "downloads"
        self.source_dir = self.paper_dir / "sources"
        self.parsed_dir = self.paper_dir / "parsed"
        self.images_dir = self.paper_dir / "images"
        self.last_image_backend = "unknown"
        self.last_source_status = ""
        self.last_source_figure_blocks = 0

        self.cache_root.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str) -> None:
        if not self.verbose:
            return
        stamp = time.strftime("%H:%M:%S")
        print(f"[paper2wechat {stamp}] {message}", file=sys.stderr, flush=True)

    @staticmethod
    def _safe_key(value: str) -> str:
        return (value or "paper").replace("/", "_")

    def _activate_paper_workspace(self, cache_key: str) -> str:
        safe_key = self._safe_key(cache_key)
        self.paper_key = safe_key
        self.paper_dir = self.cache_root / safe_key
        self.download_dir = self.paper_dir / "downloads"
        self.source_dir = self.paper_dir / "sources"
        self.parsed_dir = self.paper_dir / "parsed"
        self.images_dir = self.paper_dir / "images"

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        return safe_key

    def fetch_from_url(self, url: str) -> Paper:
        arxiv_id = self.parse_arxiv_url(url)
        self._activate_paper_workspace(arxiv_id)
        self._log(f"Input: arXiv {arxiv_id}")
        try:
            self._log("Fetching metadata (API/abs fallback)...")
            metadata = self._fetch_arxiv_metadata(arxiv_id)
        except FetchError:
            self._log("Metadata fetch failed; continuing with PDF-only parsing.")
            metadata = {}

        pdf_url = metadata.get("pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        self._log(f"Ensuring PDF cached: {pdf_url}")
        pdf_path = self._download_pdf(pdf_url, arxiv_id)

        self._log(f"Parsing PDF: {pdf_path.as_posix()}")
        paper = self.fetch_from_pdf(
            str(pdf_path),
            arxiv_id=arxiv_id,
            source_url=f"https://arxiv.org/abs/{arxiv_id}",
        )

        paper.title = metadata.get("title") or paper.title
        paper.abstract = metadata.get("abstract") or paper.abstract
        paper.authors = metadata.get("authors") or paper.authors
        paper.affiliations = metadata.get("affiliations") or paper.affiliations
        paper.published_date = metadata.get("published_date") or paper.published_date
        paper.pdf_url = pdf_url
        paper.url = f"https://arxiv.org/abs/{arxiv_id}"

        self._save_parsed_cache(paper, cache_key=arxiv_id)
        return paper

    def fetch_from_pdf(
        self,
        pdf_path: str,
        arxiv_id: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Paper:
        pdf_file = Path(pdf_path).expanduser().resolve()
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_file}")
        cache_key = arxiv_id or pdf_file.stem
        self._activate_paper_workspace(cache_key)
        self._log(f"Workspace: {self.paper_dir.as_posix()}")

        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover
            raise FetchError("pypdf is required for PDF parsing.") from exc

        try:
            reader = PdfReader(str(pdf_file))
        except Exception as exc:
            raise FetchError(f"Unable to read PDF: {pdf_file}") from exc

        total_pages = len(getattr(reader, "pages", []) or [])
        self._log(f"PDF loaded: {total_pages} pages")
        try:
            pdf_bytes = int(pdf_file.stat().st_size)
        except Exception:
            pdf_bytes = 0
        if pdf_bytes:
            self._log(f"PDF size: {pdf_bytes/1e6:.1f}MB")

        metadata = reader.metadata or {}
        title = self._clean_text(str(metadata.get("/Title", "") or "").strip())
        if not title:
            title = pdf_file.stem

        authors = self._parse_authors(
            self._clean_text(str(metadata.get("/Author", "") or "").strip())
        )

        page_lines_by_page: List[List[str]] = []
        start_extract = time.monotonic()
        last_page_log = start_extract
        for index, page in enumerate(reader.pages, start=1):
            now = time.monotonic()
            if self.verbose and (now - last_page_log) >= self.log_interval_seconds:
                self._log(f"Extracting text: page {index}/{total_pages}")
                last_page_log = now
            text = page.extract_text() or ""
            clean = self._normalize_page_text(text)
            lines = [line.strip() for line in clean.splitlines() if line.strip()]
            if lines:
                page_lines_by_page.append(lines)

        line_counter = Counter(
            line
            for lines in page_lines_by_page
            for line in set(lines)
            if len(line) <= 90
        )

        page_texts: List[str] = []
        for lines in page_lines_by_page:
            filtered = [
                line
                for line in lines
                if not self._is_repeated_noise_line(line, frequency=line_counter.get(line, 0))
            ]
            if filtered:
                page_texts.append("\n".join(filtered))

        full_text = "\n\n".join(page_texts)
        if not full_text:
            raise FetchError(f"No extractable text found in PDF: {pdf_file}")

        affiliations = self._extract_affiliations_from_text(full_text)
        sections = self._split_sections(full_text)
        abstract = self._extract_abstract(full_text)
        self.last_image_backend = "none"
        images: List[ImageInfo] = []

        should_try_source = False
        if arxiv_id:
            policy = self.source_policy
            if policy in {"never", "no", "false", "0"}:
                should_try_source = False
            elif policy in {"always", "yes", "true", "1"}:
                should_try_source = True
            else:
                # auto
                oversized = (pdf_bytes and pdf_bytes >= AUTO_SKIP_SOURCE_PDF_BYTES) or (
                    total_pages and total_pages >= AUTO_SKIP_SOURCE_PDF_PAGES
                )
                should_try_source = not oversized
                if oversized:
                    reasons: List[str] = []
                    if pdf_bytes and pdf_bytes >= AUTO_SKIP_SOURCE_PDF_BYTES:
                        reasons.append(f"size {pdf_bytes/1e6:.1f}MB >= {AUTO_SKIP_SOURCE_PDF_BYTES/1e6:.0f}MB")
                    if total_pages and total_pages >= AUTO_SKIP_SOURCE_PDF_PAGES:
                        reasons.append(f"pages {total_pages} >= {AUTO_SKIP_SOURCE_PDF_PAGES}")
                    reason_text = ", ".join(reasons) if reasons else "oversized PDF"
                    self.last_source_status = f"auto-skip source ({reason_text})"
                    self._log(f"Auto-skip TeX/source extraction: {reason_text}")

        if arxiv_id and should_try_source:
            self._log("Trying TeX-source figure extraction...")
            images = self._extract_images_from_arxiv_source(
                arxiv_id=arxiv_id,
                cache_key=cache_key,
            )
            if images:
                self._log(f"TeX-source images: {len(images)} (figure blocks: {self.last_source_figure_blocks})")
                if self.last_source_figure_blocks > len(images):
                    self._log("Supplementing with PDF figures (missing TeX assets)...")
                    images = self._supplement_source_images_with_pdf(
                        source_images=images,
                        pdf_path=pdf_file,
                        cache_key=cache_key,
                        required_count=self.last_source_figure_blocks,
                    )
                if self.last_image_backend != "tex-source+pdf-supplement":
                    self.last_image_backend = "tex-source"
            else:
                self._log(f"TeX-source extraction yielded 0 images ({self.last_source_status or 'no status'}).")
        if not images:
            self._log("Trying PDF caption-based extraction...")
            images = self._extract_figures_by_caption(
                pdf_path=pdf_file,
                cache_key=cache_key,
            )
            if images:
                self.last_image_backend = "pdf-caption"
        if not images:
            self._log("Trying PDFPlumber-based extraction...")
            images = self._extract_figures_with_pdfplumber(
                pdf_path=pdf_file,
                cache_key=cache_key,
            )
            if images:
                self.last_image_backend = "pdf-plumber"
        if not images:
            self._log("Trying PyMuPDF (fitz) largest-figure extraction...")
            images = self._extract_largest_figures_with_fitz(
                pdf_path=pdf_file,
                cache_key=cache_key,
                max_images=8,
            )
            if images:
                self.last_image_backend = "pdf-fitz-largest"
        if not images:
            self._log("Trying embedded-image extraction...")
            images = self._extract_pdf_images(reader, cache_key=cache_key)
            if images:
                self.last_image_backend = "pdf-embedded"

        self._log(f"Image backend: {self.last_image_backend} (images: {len(images)})")

        paper = Paper(
            title=title,
            authors=authors,
            affiliations=affiliations,
            abstract=abstract,
            arxiv_id=arxiv_id,
            pdf_url=str(pdf_file),
            sections=sections,
            images=images,
            url=source_url or str(pdf_file),
        )

        self._save_parsed_cache(paper, cache_key=cache_key)
        return paper

    @staticmethod
    def parse_arxiv_url(url: str) -> str:
        value = (url or "").strip()
        if not value:
            raise ValueError("Arxiv URL/ID cannot be empty.")

        if ARXIV_ID_PATTERN.fullmatch(value):
            return value

        if "arxiv.org" in value:
            match = ARXIV_ID_PATTERN.search(value)
            if match:
                return match.group("id").removesuffix(".pdf")

        raise ValueError(f"Invalid Arxiv URL or ID: {url}")

    def _fetch_arxiv_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        api_urls = [
            f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
            f"https://arxiv.org/api/query?id_list={arxiv_id}",
        ]
        last_error: Optional[Exception] = None

        for api_url in api_urls:
            try:
                # arXiv API endpoints are frequently rate-limited (HTTP 429). We keep retries
                # low here and fall back to parsing the abs HTML page if needed.
                xml_text = self._http_get(api_url, max_attempts=1).decode("utf-8", errors="replace")
            except FetchError as exc:
                last_error = exc
                continue

            metadata = self._parse_arxiv_metadata_xml(xml_text)
            if metadata is not None:
                return metadata

        fallback = self._fetch_arxiv_metadata_from_abs_page(arxiv_id)
        if fallback is not None:
            return fallback

        if last_error is not None:
            raise FetchError(f"Failed to fetch arXiv metadata for {arxiv_id}") from last_error
        raise FetchError(f"Arxiv paper not found: {arxiv_id}")

    def _parse_arxiv_metadata_xml(self, xml_text: str) -> Optional[Dict[str, Any]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        entry = root.find("atom:entry", ns)
        if entry is None:
            return None

        title = self._clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = self._clean_text(
            entry.findtext("atom:summary", default="", namespaces=ns)
        )
        authors: List[str] = []
        affiliations: List[str] = []
        for author in entry.findall("atom:author", ns):
            author_name = self._clean_text(
                author.findtext("atom:name", default="", namespaces=ns)
            )
            if author_name:
                authors.append(author_name)

            affiliation = self._clean_text(
                author.findtext("arxiv:affiliation", default="", namespaces=ns)
            )
            if affiliation:
                affiliations.append(affiliation)

        published_raw = entry.findtext("atom:published", default="", namespaces=ns)
        published_date = self._parse_published_date(published_raw)

        pdf_url = None
        for link in entry.findall("atom:link", ns):
            href = link.attrib.get("href", "").strip()
            content_type = link.attrib.get("type", "").strip()
            title_attr = link.attrib.get("title", "").strip()
            if (
                content_type == "application/pdf"
                or title_attr.lower() == "pdf"
                or href.endswith(".pdf")
            ):
                pdf_url = href
                break

        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "affiliations": self._dedupe_preserve_order(affiliations),
            "published_date": published_date,
            "pdf_url": pdf_url,
        }

    def _fetch_arxiv_metadata_from_abs_page(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        try:
            html_text = self._http_get(abs_url).decode("utf-8", errors="replace")
        except FetchError:
            return None

        title = (
            self._extract_html_meta_content(html_text, "citation_title")
            or self._extract_arxiv_title_from_html(html_text)
        )

        authors = self._extract_html_meta_multi(html_text, "citation_author")
        affiliations = self._extract_html_meta_multi(html_text, "citation_author_institution")
        affiliations.extend(self._extract_html_meta_multi(html_text, "citation_author_affiliation"))
        abstract = (
            self._extract_arxiv_abstract_from_html(html_text)
            or self._extract_html_meta_content(html_text, "description")
            or ""
        )
        if abstract.lower().startswith("abstract:"):
            abstract = abstract.split(":", 1)[-1].strip()

        date_raw = self._extract_html_meta_content(html_text, "citation_date")
        published_date = self._parse_published_date(date_raw)

        pdf_url = self._extract_html_meta_content(html_text, "citation_pdf_url")
        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        if not any((title, abstract, authors, affiliations, pdf_url)):
            return None

        return {
            "title": title or "",
            "abstract": abstract or "",
            "authors": authors,
            "affiliations": self._dedupe_preserve_order(affiliations),
            "published_date": published_date,
            "pdf_url": pdf_url,
        }

    @staticmethod
    def _extract_html_meta_content(html_text: str, name: str) -> str:
        escaped = re.escape(name)
        patterns = [
            re.compile(
                rf"<meta[^>]*\bname=[\"']{escaped}[\"'][^>]*\bcontent=[\"']([^\"']+)[\"'][^>]*>",
                flags=re.IGNORECASE,
            ),
            re.compile(
                rf"<meta[^>]*\bcontent=[\"']([^\"']+)[\"'][^>]*\bname=[\"']{escaped}[\"'][^>]*>",
                flags=re.IGNORECASE,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(html_text)
            if match:
                return html.unescape(match.group(1).strip())
        return ""

    def _extract_html_meta_multi(self, html_text: str, name: str) -> List[str]:
        escaped = re.escape(name)
        pattern = re.compile(
            rf"<meta[^>]*\bname=[\"']{escaped}[\"'][^>]*\bcontent=[\"']([^\"']+)[\"'][^>]*>",
            flags=re.IGNORECASE,
        )
        results: List[str] = []
        for match in pattern.finditer(html_text):
            value = html.unescape(match.group(1).strip())
            clean = self._clean_text(value)
            if clean:
                results.append(clean)
        return results

    def _extract_arxiv_title_from_html(self, html_text: str) -> str:
        match = re.search(
            r"<h1[^>]*class=[\"'][^\"']*\btitle\b[^\"']*[\"'][^>]*>(.*?)</h1>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        text = self._strip_html_tags(match.group(1))
        text = re.sub(r"^\s*title\s*:\s*", "", text, flags=re.IGNORECASE)
        return self._clean_text(text)

    def _extract_arxiv_abstract_from_html(self, html_text: str) -> str:
        match = re.search(
            r"<blockquote[^>]*class=[\"'][^\"']*\babstract\b[^\"']*[\"'][^>]*>(.*?)</blockquote>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        text = self._strip_html_tags(match.group(1))
        text = re.sub(r"^\s*abstract\s*:\s*", "", text, flags=re.IGNORECASE)
        return self._clean_text(text)

    @staticmethod
    def _strip_html_tags(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_published_date(value: Optional[str]) -> Optional[datetime]:
        raw = (value or "").strip()
        if not raw:
            return None
        normalized = raw.replace("Z", "+00:00")
        for candidate in (normalized, normalized.replace("/", "-")):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
        date_match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", raw)
        if date_match:
            try:
                year, month, day = map(int, date_match.groups())
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _download_pdf(self, pdf_url: str, arxiv_id: str) -> Path:
        safe_id = arxiv_id.replace("/", "_")
        output_path = self.download_dir / f"{safe_id}.pdf"
        if output_path.exists() and output_path.stat().st_size > 0:
            try:
                with output_path.open("rb") as handle:
                    head = handle.read(512)
            except Exception:
                head = b""
            if head.startswith(b"%PDF") and not self._looks_like_html_payload(head):
                self._log(f"PDF cached: {output_path.as_posix()} ({output_path.stat().st_size} bytes)")
                return output_path
            self._log("PDF cache looks invalid; re-downloading.")
            output_path.unlink(missing_ok=True)

        self._http_download_to_file(
            pdf_url,
            output_path,
            description=f"PDF {arxiv_id}",
        )
        return output_path

    def _download_arxiv_source(self, arxiv_id: str) -> Optional[Path]:
        safe_id = arxiv_id.replace("/", "_")
        output_path = self.download_dir / f"{safe_id}-source.bin"
        if output_path.exists() and output_path.stat().st_size > 0:
            try:
                head = output_path.read_bytes()[:512]
            except Exception:
                head = b""
            if head and not self._looks_like_html_payload(head):
                self._log(f"Source cached: {output_path.as_posix()} ({output_path.stat().st_size} bytes)")
                return output_path
            self._log("Source cache looks invalid; re-downloading.")
            output_path.unlink(missing_ok=True)

        source_urls = [
            f"https://arxiv.org/src/{arxiv_id}",
            f"https://export.arxiv.org/src/{arxiv_id}",
        ]
        for source_url in source_urls:
            try:
                self._http_download_to_file(
                    source_url,
                    output_path,
                    description=f"arXiv source {arxiv_id}",
                )
            except FetchError:
                continue
            try:
                source_bytes = output_path.read_bytes()
            except Exception:
                continue
            if not source_bytes or self._looks_like_html_payload(source_bytes):
                output_path.unlink(missing_ok=True)
                continue
            return output_path

        return None

    def _extract_images_from_arxiv_source(self, arxiv_id: str, cache_key: str) -> List[ImageInfo]:
        source_payload = self._download_arxiv_source(arxiv_id)
        if source_payload is None:
            self.last_source_status = "source payload unavailable"
            return []

        extracted_source_dir = self.source_dir
        if extracted_source_dir.exists():
            shutil.rmtree(extracted_source_dir)
        extracted_source_dir.mkdir(parents=True, exist_ok=True)

        if not self._unpack_arxiv_source_archive(source_payload, extracted_source_dir):
            self.last_source_status = "source archive unpack failed"
            return []

        figure_entries, figure_block_count = self._parse_tex_figure_entries(extracted_source_dir)
        self.last_source_figure_blocks = figure_block_count
        if not figure_entries:
            if figure_block_count > 0:
                self.last_source_status = "figure blocks found but no includegraphics assets"
            else:
                self.last_source_status = "no figure entries found in tex source"
        by_name, by_stem = self._index_source_files(extracted_source_dir)
        materialized: List[Tuple[Path, str]] = []
        seen_source_paths = set()

        with tempfile.TemporaryDirectory(prefix="p2w-source-images-") as temp_output:
            temp_output_dir = Path(temp_output)

            for entry in figure_entries:
                if len(materialized) >= MAX_SOURCE_IMAGES:
                    break
                resolved = self._resolve_source_graphic_path(
                    include_token=entry["include"],
                    tex_dir=entry["tex_dir"],
                    source_root=extracted_source_dir,
                    by_name=by_name,
                    by_stem=by_stem,
                )
                if resolved is None:
                    continue
                source_key = str(resolved.resolve())
                if source_key in seen_source_paths:
                    continue

                output = self._materialize_source_image(
                    source_path=resolved,
                    output_dir=temp_output_dir,
                    sequence=len(materialized) + 1,
                )
                if output is None:
                    continue

                caption = entry.get("caption") or f"Figure {len(materialized) + 1}"
                materialized.append((output, caption))
                seen_source_paths.add(source_key)

            if not materialized:
                for candidate in self._collect_fallback_source_images(extracted_source_dir):
                    if len(materialized) >= MAX_SOURCE_IMAGES:
                        break
                    source_key = str(candidate.resolve())
                    if source_key in seen_source_paths:
                        continue

                    output = self._materialize_source_image(
                        source_path=candidate,
                        output_dir=temp_output_dir,
                        sequence=len(materialized) + 1,
                    )
                    if output is None:
                        continue

                    caption = f"Figure {len(materialized) + 1}"
                    materialized.append((output, caption))
                    seen_source_paths.add(source_key)

            if not materialized:
                self.last_source_status = "source figures found but materialization failed"
                return []

            paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=True)
            extracted: List[ImageInfo] = []
            for index, (source_image, caption) in enumerate(materialized, start=1):
                ext = source_image.suffix.lower()
                if ext == ".jpeg":
                    ext = ".jpg"
                output_path = paper_image_dir / f"src_{index:03d}{ext}"
                shutil.copy2(source_image, output_path)
                relevance = round(max(0.72, 0.98 - (index - 1) * 0.018), 3)
                extracted.append(
                    ImageInfo(
                        url=str(output_path.as_posix()),
                        caption=caption,
                        position=index,
                        relevance_score=relevance,
                    )
                )

        deduped = self._deduplicate_images(extracted)
        if self.last_source_figure_blocks > len(deduped):
            self.last_source_status = (
                f"tex source images {len(deduped)}/{self.last_source_figure_blocks}; "
                "remaining figures likely drawn in LaTeX (tikz/forest)"
            )
        else:
            self.last_source_status = f"tex source images {len(deduped)}"
        return deduped

    def _unpack_arxiv_source_archive(self, payload_path: Path, output_dir: Path) -> bool:
        if payload_path.stat().st_size <= 0:
            return False

        try:
            with tarfile.open(str(payload_path), "r:*") as tar_obj:
                self._safe_extract_tar(tar_obj, output_dir)
            return True
        except Exception:
            pass

        try:
            with zipfile.ZipFile(str(payload_path), "r") as zip_obj:
                self._safe_extract_zip(zip_obj, output_dir)
            return True
        except Exception:
            pass

        payload = payload_path.read_bytes()
        if payload[:2] == b"\x1f\x8b":
            try:
                decompressed = gzip.decompress(payload)
            except Exception:
                decompressed = b""
            if decompressed:
                inner_path = output_dir / "_decompressed.bin"
                inner_path.write_bytes(decompressed)
                if self._unpack_arxiv_source_archive(inner_path, output_dir):
                    inner_path.unlink(missing_ok=True)
                    return True
                inner_path.unlink(missing_ok=True)

        if self._contains_latex_markers(payload):
            (output_dir / "main.tex").write_bytes(payload)
            return True

        return any(output_dir.rglob("*.tex"))

    @staticmethod
    def _safe_extract_tar(tar_obj: tarfile.TarFile, destination: Path) -> None:
        destination_resolved = destination.resolve()
        for member in tar_obj.getmembers():
            member_name = member.name.strip()
            if not member_name:
                continue
            candidate = (destination / member_name).resolve()
            if not PaperFetcher._is_within_directory(candidate, destination_resolved):
                continue
            try:
                # Python 3.12+ recommends explicit extraction filter for safer defaults
                # and to avoid future deprecation warnings.
                tar_obj.extract(member, path=str(destination), filter="data")
            except TypeError:
                tar_obj.extract(member, path=str(destination))

    @staticmethod
    def _safe_extract_zip(zip_obj: zipfile.ZipFile, destination: Path) -> None:
        destination_resolved = destination.resolve()
        for name in zip_obj.namelist():
            clean_name = name.strip()
            if not clean_name:
                continue
            candidate = (destination / clean_name).resolve()
            if not PaperFetcher._is_within_directory(candidate, destination_resolved):
                continue
            zip_obj.extract(clean_name, path=str(destination))

    @staticmethod
    def _is_within_directory(candidate: Path, root: Path) -> bool:
        try:
            candidate.resolve().relative_to(root.resolve())
        except Exception:
            return False
        return True

    def _parse_tex_figure_entries(self, source_root: Path) -> Tuple[List[Dict[str, Any]], int]:
        entries: List[Dict[str, Any]] = []
        figure_block_count = 0
        tex_files = sorted(
            source_root.rglob("*.tex"),
            key=lambda path: (len(path.parts), path.as_posix()),
        )
        for tex_path in tex_files:
            try:
                content = tex_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Remove LaTeX comments while keeping escaped \%.
            content = re.sub(r"(?<!\\)%[^\n]*", "", content)
            blocks = self._extract_figure_blocks(content)
            figure_block_count += len(blocks)
            for block in blocks:
                includes = self._extract_includegraphics_paths(block)
                if not includes:
                    continue
                caption = self._extract_caption_from_figure_block(block)
                for include in includes:
                    entries.append(
                        {
                            "tex_dir": tex_path.parent,
                            "include": include,
                            "caption": caption,
                        }
                    )
        return entries, figure_block_count

    @staticmethod
    def _extract_figure_blocks(tex_content: str) -> List[str]:
        if not tex_content:
            return []
        pattern = re.compile(
            r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}",
            flags=re.IGNORECASE | re.DOTALL,
        )
        return [match.group(1) for match in pattern.finditer(tex_content)]

    @staticmethod
    def _extract_includegraphics_paths(figure_block: str) -> List[str]:
        paths: List[str] = []
        patterns = [
            re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}", re.IGNORECASE),
            re.compile(r"\\includesvg(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}", re.IGNORECASE),
        ]
        for pattern in patterns:
            for match in pattern.finditer(figure_block):
                value = (match.group(1) or "").strip()
                if value:
                    paths.append(value)
        return paths

    def _extract_caption_from_figure_block(self, figure_block: str) -> str:
        caption_head = re.search(
            r"\\caption(?:\[[^\]]*\])?\s*\{",
            figure_block,
            flags=re.IGNORECASE,
        )
        if not caption_head:
            return ""
        open_brace_index = caption_head.end() - 1
        raw_caption = self._extract_latex_braced_text(figure_block, open_brace_index)
        return self._sanitize_latex_caption(raw_caption)

    @staticmethod
    def _extract_latex_braced_text(text: str, open_brace_index: int) -> str:
        if open_brace_index < 0 or open_brace_index >= len(text) or text[open_brace_index] != "{":
            return ""
        depth = 0
        chars: List[str] = []
        for ch in text[open_brace_index:]:
            if ch == "{":
                depth += 1
                if depth == 1:
                    continue
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            if depth >= 1:
                chars.append(ch)
        return "".join(chars).strip()

    def _sanitize_latex_caption(self, caption: str) -> str:
        value = caption or ""
        value = re.sub(r"\\label\{[^{}]*\}", "", value)
        value = re.sub(r"\\(?:eq|auto)?ref\{[^{}]*\}", "", value)
        value = re.sub(r"\\cite\w*\{[^{}]*\}", "", value)
        for _ in range(3):
            collapsed = re.sub(
                r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}",
                r"\1",
                value,
            )
            if collapsed == value:
                break
            value = collapsed
        value = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", value)
        value = value.replace("{", "").replace("}", "")
        return self._clean_text(value)[:260]

    @staticmethod
    def _index_source_files(source_root: Path) -> Tuple[Dict[str, List[Path]], Dict[str, List[Path]]]:
        by_name: Dict[str, List[Path]] = {}
        by_stem: Dict[str, List[Path]] = {}
        for file_path in source_root.rglob("*"):
            if not file_path.is_file():
                continue
            by_name.setdefault(file_path.name.lower(), []).append(file_path)
            by_stem.setdefault(file_path.stem.lower(), []).append(file_path)
        return by_name, by_stem

    def _resolve_source_graphic_path(
        self,
        include_token: str,
        tex_dir: Path,
        source_root: Path,
        by_name: Dict[str, List[Path]],
        by_stem: Dict[str, List[Path]],
    ) -> Optional[Path]:
        token = (include_token or "").strip().strip("\"'").replace("\\", "/")
        if not token:
            return None
        if token.startswith("http://") or token.startswith("https://"):
            return None
        if "$" in token or "{" in token or "}" in token:
            return None
        token = token.split("#", 1)[0].strip()
        if not token:
            return None

        token_path = Path(token)
        candidate_paths: List[Path] = []
        if token_path.suffix:
            candidate_paths.append(tex_dir / token_path)
        else:
            candidate_paths.append(tex_dir / token_path)
            for extension in SOURCE_GRAPHIC_EXTENSIONS:
                candidate_paths.append(tex_dir / f"{token}{extension}")

        for candidate in candidate_paths:
            if not candidate.exists() or not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SOURCE_GRAPHIC_EXTENSIONS:
                continue
            return candidate

        best = self._best_source_file_matches(
            token=token_path.name.lower(),
            by_name=by_name,
            by_stem=by_stem,
        )
        if best is None:
            return None
        try:
            if not self._is_within_directory(best, source_root):
                return None
        except Exception:
            return None
        return best

    def _best_source_file_matches(
        self,
        token: str,
        by_name: Dict[str, List[Path]],
        by_stem: Dict[str, List[Path]],
    ) -> Optional[Path]:
        options: List[Path] = []
        if token in by_name:
            options.extend(by_name[token])

        token_stem = Path(token).stem.lower()
        if token_stem in by_stem:
            options.extend(by_stem[token_stem])

        if not options:
            return None

        ranked = sorted(
            {path.resolve() for path in options if path.suffix.lower() in SOURCE_GRAPHIC_EXTENSIONS},
            key=self._source_file_rank,
            reverse=True,
        )
        return ranked[0] if ranked else None

    @staticmethod
    def _source_file_rank(path: Path) -> float:
        name = path.name.lower()
        extension = path.suffix.lower()
        try:
            size = float(path.stat().st_size)
        except Exception:
            size = 0.0

        score = min(size / (256 * 1024), 12.0)
        if "fig" in name or "figure" in name:
            score += 3.5
        if "logo" in name or "icon" in name or "banner" in name:
            score -= 3.0
        if extension in SOURCE_RASTER_EXTENSIONS:
            score += 2.0
        if extension in SOURCE_VECTOR_EXTENSIONS:
            score += 1.0
        return score

    def _materialize_source_image(
        self,
        source_path: Path,
        output_dir: Path,
        sequence: int,
    ) -> Optional[Path]:
        extension = source_path.suffix.lower()
        if extension in SOURCE_RASTER_EXTENSIONS:
            try:
                if source_path.stat().st_size < SOURCE_MIN_BYTES:
                    return None
            except Exception:
                return None
            final_ext = ".jpg" if extension == ".jpeg" else extension
            output_path = output_dir / f"source_{sequence:03d}{final_ext}"
            try:
                shutil.copy2(source_path, output_path)
            except Exception:
                return None
            return output_path

        if extension in SOURCE_VECTOR_EXTENSIONS:
            output_path = output_dir / f"source_{sequence:03d}.png"
            if self._rasterize_pdf_with_pdftoppm(source_path=source_path, output_path=output_path):
                return output_path
            if fitz is not None:
                try:
                    document = fitz.open(str(source_path))
                    try:
                        if document.page_count <= 0:
                            return None
                        first_page = document.load_page(0)
                        pix = first_page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0), alpha=False)
                        if pix.width < 120 or pix.height < 80:
                            return None
                        pix.save(str(output_path))
                    finally:
                        document.close()
                except Exception:
                    return None
                return output_path
            if self._rasterize_pdf_with_sips(source_path=source_path, output_path=output_path):
                return output_path

        return None

    @staticmethod
    def _rasterize_pdf_with_pdftoppm(source_path: Path, output_path: Path) -> bool:
        output_prefix = str(output_path.with_suffix(""))
        try:
            result = subprocess.run(
                [
                    "pdftoppm",
                    "-png",
                    "-singlefile",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    "-cropbox",
                    "-r",
                    "360",
                    str(source_path),
                    output_prefix,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return False

        if result.returncode != 0:
            return False
        if not output_path.exists():
            return False
        try:
            return output_path.stat().st_size > 4096
        except Exception:
            return False

    @staticmethod
    def _rasterize_pdf_with_sips(source_path: Path, output_path: Path) -> bool:
        try:
            result = subprocess.run(
                ["sips", "-s", "format", "png", str(source_path), "--out", str(output_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return False

        if result.returncode != 0:
            return False
        if not output_path.exists():
            return False
        try:
            return output_path.stat().st_size > 1024
        except Exception:
            return False

    def _collect_fallback_source_images(self, source_root: Path) -> List[Path]:
        candidates: List[Path] = []
        for file_path in source_root.rglob("*"):
            if not file_path.is_file():
                continue
            extension = file_path.suffix.lower()
            if extension not in SOURCE_RASTER_EXTENSIONS and extension not in SOURCE_VECTOR_EXTENSIONS:
                continue
            try:
                if file_path.stat().st_size < SOURCE_MIN_BYTES:
                    continue
            except Exception:
                continue
            candidates.append(file_path)

        ranked = sorted(candidates, key=self._source_file_rank, reverse=True)
        return ranked[:MAX_SOURCE_IMAGES]

    def _supplement_source_images_with_pdf(
        self,
        source_images: List[ImageInfo],
        pdf_path: Path,
        cache_key: str,
        required_count: int,
    ) -> List[ImageInfo]:
        temp_key = f"{cache_key}__pdfsupp"
        pdf_images = self._extract_figures_by_caption(
            pdf_path=pdf_path,
            cache_key=temp_key,
        )
        if not pdf_images:
            return source_images

        paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=False)
        existing_signatures = [self._caption_signature(image.caption) for image in source_images]
        merged = list(source_images)
        need = max(0, required_count - len(source_images))
        added = 0

        for image in pdf_images:
            if need > 0 and added >= need:
                break
            if self._caption_is_duplicate(image.caption, existing_signatures):
                continue

            source_path = Path(image.url)
            if not source_path.exists():
                continue

            ext = source_path.suffix.lower() or ".png"
            if ext == ".jpeg":
                ext = ".jpg"
            output_path = paper_image_dir / f"pdfsupp_{added + 1:03d}{ext}"
            try:
                shutil.copy2(source_path, output_path)
            except Exception:
                continue

            merged.append(
                ImageInfo(
                    url=str(output_path.as_posix()),
                    caption=image.caption,
                    position=len(merged) + 1,
                    relevance_score=image.relevance_score,
                )
            )
            existing_signatures.append(self._caption_signature(image.caption))
            added += 1

        self._cleanup_image_dir(temp_key)
        if added > 0:
            self.last_source_status = (
                f"{self.last_source_status}; supplemented {added} figure(s) from PDF fallback"
            )
            self.last_image_backend = "tex-source+pdf-supplement"
        return merged

    def _cleanup_image_dir(self, cache_key: str) -> None:
        safe_key = self._safe_key(cache_key)
        if safe_key == self.paper_key:
            target_dir = self.images_dir
        else:
            target_dir = self.images_dir / f"_{safe_key}"
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

    @staticmethod
    def _caption_signature(caption: str) -> str:
        text = (caption or "").lower()
        text = re.sub(r"^\s*(figure|fig\.?)\s*\d+\s*[:.\-]?\s*", "", text, flags=re.IGNORECASE)
        tokens = [tok for tok in re.findall(r"[a-z0-9]+", text) if len(tok) > 2]
        return " ".join(tokens[:24])

    @classmethod
    def _caption_is_duplicate(cls, caption: str, signatures: List[str]) -> bool:
        candidate = cls._caption_signature(caption)
        if not candidate:
            return False
        for signature in signatures:
            if not signature:
                continue
            if candidate == signature:
                return True
            if candidate in signature or signature in candidate:
                if min(len(candidate), len(signature)) >= 26:
                    return True
            ratio = SequenceMatcher(None, candidate, signature).ratio()
            if ratio >= 0.72:
                return True
        return False

    @staticmethod
    def _contains_latex_markers(payload: bytes) -> bool:
        if not payload:
            return False
        head = payload[:8192]
        return (
            b"\\documentclass" in head
            or b"\\begin{document}" in head
            or b"\\begin{figure" in head
        )

    @staticmethod
    def _looks_like_html_payload(payload: bytes) -> bool:
        if not payload:
            return False
        sample = payload[:512].lower().lstrip()
        return sample.startswith(b"<!doctype html") or sample.startswith(b"<html")

    def _save_parsed_cache(self, paper: Paper, cache_key: str) -> None:
        safe_key = self._safe_key(cache_key)
        cache_path = self.parsed_dir / f"{safe_key}.json"

        payload = {
            "title": paper.title,
            "authors": paper.authors,
            "affiliations": paper.affiliations,
            "abstract": paper.abstract,
            "published_date": paper.published_date.isoformat()
            if paper.published_date
            else None,
            "arxiv_id": paper.arxiv_id,
            "pdf_url": paper.pdf_url,
            "url": paper.url,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "level": section.level,
                }
                for section in paper.sections
            ],
            "images": [
                {
                    "url": image.url,
                    "caption": image.caption,
                    "position": image.position,
                    "relevance_score": image.relevance_score,
                }
                for image in paper.images
            ],
            "saved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _http_get(self, url: str, *, max_attempts: int = HTTP_MAX_ATTEMPTS) -> bytes:
        max_attempts = max(1, int(max_attempts))
        headers = {"User-Agent": "paper2wechat-skill/1.0"}

        if requests is not None:
            last_error: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    self._log(f"HTTP GET (attempt {attempt}/{max_attempts}): {url}")
                    response = requests.get(url, headers=headers, timeout=self.timeout)
                except Exception as exc:
                    last_error = exc
                    self._log(f"HTTP error: {type(exc).__name__}: {exc}")
                    if attempt >= max_attempts:
                        break
                    time.sleep(self._compute_retry_delay(attempt=attempt))
                    continue

                if response.status_code < 400:
                    self._log(f"HTTP {response.status_code}: {url} ({len(response.content)} bytes)")
                    return response.content

                if response.status_code in HTTP_RETRY_STATUS_CODES and attempt < max_attempts:
                    self._log(f"HTTP {response.status_code}, retrying: {url}")
                    time.sleep(
                        self._compute_retry_delay(
                            attempt=attempt,
                            retry_after=response.headers.get("Retry-After", ""),
                        )
                    )
                    continue

                try:
                    response.raise_for_status()
                except Exception as exc:
                    raise FetchError(f"Request failed: {url}") from exc

            raise FetchError(f"Request failed: {url}") from last_error

        request = urllib.request.Request(url, headers=headers)
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                self._log(f"HTTP GET (attempt {attempt}/{max_attempts}): {url}")
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                    self._log(f"HTTP 200: {url} ({len(payload)} bytes)")
                    return payload
            except urllib.error.HTTPError as exc:  # pragma: no cover
                last_error = exc
                if exc.code in HTTP_RETRY_STATUS_CODES and attempt < max_attempts:
                    retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                    self._log(f"HTTP {exc.code}, retrying: {url}")
                    time.sleep(
                        self._compute_retry_delay(
                            attempt=attempt,
                            retry_after=retry_after,
                        )
                    )
                    continue
                raise FetchError(f"Request failed: {url}") from exc
            except urllib.error.URLError as exc:  # pragma: no cover
                last_error = exc
                self._log(f"HTTP error: {type(exc).__name__}: {exc}")
                if attempt >= max_attempts:
                    break
                time.sleep(self._compute_retry_delay(attempt=attempt))
                continue

        raise FetchError(f"Request failed: {url}") from last_error

    def _http_download_to_file(self, url: str, output_path: Path, *, description: str) -> None:
        headers = {"User-Agent": "paper2wechat-skill/1.0"}
        tmp_path = output_path.with_suffix(output_path.suffix + ".part")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)

        def _log_progress(downloaded: int, total: int, started_at: float, prefix: str) -> None:
            if not self.verbose:
                return
            elapsed = max(1e-6, time.monotonic() - started_at)
            rate = downloaded / elapsed
            if total > 0:
                pct = downloaded / total * 100
                self._log(
                    f"{prefix}: {downloaded/1e6:.1f}MB/{total/1e6:.1f}MB ({pct:.1f}%) at {rate/1e6:.2f}MB/s"
                )
            else:
                self._log(f"{prefix}: {downloaded/1e6:.1f}MB downloaded at {rate/1e6:.2f}MB/s")

        self._log(f"Downloading {description}: {url}")
        started_at = time.monotonic()
        last_log = started_at

        try:
            if requests is not None:
                last_error: Optional[Exception] = None
                for attempt in range(1, HTTP_MAX_ATTEMPTS + 1):
                    try:
                        self._log(f"HTTP stream (attempt {attempt}/{HTTP_MAX_ATTEMPTS}): {url}")
                        response = requests.get(
                            url,
                            headers=headers,
                            timeout=self.timeout,
                            stream=True,
                        )
                    except Exception as exc:
                        last_error = exc
                        self._log(f"HTTP error: {type(exc).__name__}: {exc}")
                        if attempt >= HTTP_MAX_ATTEMPTS:
                            break
                        time.sleep(self._compute_retry_delay(attempt=attempt))
                        continue

                    try:
                        if response.status_code >= 400:
                            if response.status_code in HTTP_RETRY_STATUS_CODES and attempt < HTTP_MAX_ATTEMPTS:
                                self._log(f"HTTP {response.status_code}, retrying: {url}")
                                time.sleep(
                                    self._compute_retry_delay(
                                        attempt=attempt,
                                        retry_after=response.headers.get("Retry-After", ""),
                                    )
                                )
                                continue
                            response.raise_for_status()

                        total = int(response.headers.get("Content-Length", "0") or 0)
                        downloaded = 0
                        with tmp_path.open("wb") as handle:
                            for chunk in response.iter_content(chunk_size=128 * 1024):
                                if not chunk:
                                    continue
                                handle.write(chunk)
                                downloaded += len(chunk)
                                now = time.monotonic()
                                if self.verbose and (now - last_log) >= self.log_interval_seconds:
                                    _log_progress(downloaded, total, started_at, description)
                                    last_log = now
                    finally:
                        try:
                            response.close()
                        except Exception:
                            pass

                    if tmp_path.stat().st_size <= 0:
                        raise FetchError(f"Downloaded empty payload: {url}")
                    tmp_path.replace(output_path)
                    self._log(f"Downloaded {description}: {output_path.as_posix()} ({output_path.stat().st_size} bytes)")
                    return

                raise FetchError(f"Request failed: {url}") from last_error

            request = urllib.request.Request(url, headers=headers)
            last_error: Optional[Exception] = None
            for attempt in range(1, HTTP_MAX_ATTEMPTS + 1):
                try:
                    self._log(f"HTTP stream (attempt {attempt}/{HTTP_MAX_ATTEMPTS}): {url}")
                    with urllib.request.urlopen(request, timeout=self.timeout) as response:
                        total = int(getattr(response, "length", 0) or response.headers.get("Content-Length", "0") or 0)
                        downloaded = 0
                        with tmp_path.open("wb") as handle:
                            while True:
                                chunk = response.read(128 * 1024)
                                if not chunk:
                                    break
                                handle.write(chunk)
                                downloaded += len(chunk)
                                now = time.monotonic()
                                if self.verbose and (now - last_log) >= self.log_interval_seconds:
                                    _log_progress(downloaded, total, started_at, description)
                                    last_log = now
                except urllib.error.HTTPError as exc:  # pragma: no cover
                    last_error = exc
                    if exc.code in HTTP_RETRY_STATUS_CODES and attempt < HTTP_MAX_ATTEMPTS:
                        retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                        self._log(f"HTTP {exc.code}, retrying: {url}")
                        time.sleep(self._compute_retry_delay(attempt=attempt, retry_after=retry_after))
                        continue
                    raise FetchError(f"Request failed: {url}") from exc
                except urllib.error.URLError as exc:  # pragma: no cover
                    last_error = exc
                    self._log(f"HTTP error: {type(exc).__name__}: {exc}")
                    if attempt >= HTTP_MAX_ATTEMPTS:
                        break
                    time.sleep(self._compute_retry_delay(attempt=attempt))
                    continue

                if tmp_path.exists() and tmp_path.stat().st_size > 0:
                    tmp_path.replace(output_path)
                    self._log(f"Downloaded {description}: {output_path.as_posix()} ({output_path.stat().st_size} bytes)")
                    return

            raise FetchError(f"Request failed: {url}") from last_error
        finally:
            if tmp_path.exists() and not output_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    @staticmethod
    def _compute_retry_delay(attempt: int, retry_after: str = "") -> float:
        retry_after = (retry_after or "").strip()
        if retry_after.isdigit():
            try:
                return max(0.3, float(retry_after))
            except ValueError:
                pass
        return HTTP_BACKOFF_BASE_SECONDS * attempt

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_authors(author_field: str) -> List[str]:
        if not author_field:
            return []
        parts = re.split(r",| and ", author_field)
        return [part.strip() for part in parts if part.strip()]

    def _extract_affiliations_from_text(self, text: str, max_items: int = 6) -> List[str]:
        if not text:
            return []

        normalized = text.replace("\r", "\n")
        lines = [self._clean_text(line) for line in normalized.splitlines() if line.strip()]
        if not lines:
            return []

        front_lines: List[str] = []
        for line in lines:
            lower = line.lower()
            if re.fullmatch(r"abstract[:\s]*", lower):
                break
            if self._looks_like_section_heading(line):
                break
            front_lines.append(line)
            if len(front_lines) >= 80:
                break

        if not front_lines:
            front_lines = lines[:80]

        keyword_pattern = re.compile(
            r"\b("
            r"university|institute|college|school|department|faculty|laboratory|lab|"
            r"research\s+center|research\s+lab|research\s+institute|center|centre|"
            r"academy|hospital|corp(?:oration)?|inc\.?|ltd\.?|llc|company|team"
            r")\b|大学|学院|研究所|实验室|研究院|中心|公司|团队",
            flags=re.IGNORECASE,
        )
        stop_pattern = re.compile(
            r"\b(figure|table|abstract|introduction|keywords?|references?)\b",
            flags=re.IGNORECASE,
        )
        email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")

        candidates: List[str] = []
        for line in front_lines:
            if len(line) < 4 or len(line) > 180:
                continue
            if stop_pattern.search(line):
                continue
            if not keyword_pattern.search(line):
                continue
            if sum(ch.isdigit() for ch in line) > max(6, int(len(line) * 0.2)):
                continue
            for chunk in self._split_affiliation_candidates(line):
                cleaned = self._normalize_affiliation_text(chunk)
                if cleaned and keyword_pattern.search(cleaned):
                    candidates.append(cleaned)

        front_blob = "\n".join(front_lines)
        for domain in email_pattern.findall(front_blob):
            label = self._domain_to_org_label(domain)
            if label:
                candidates.append(label)

        return self._dedupe_preserve_order(candidates)[:max_items]

    @staticmethod
    def _normalize_affiliation_text(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = re.sub(
            r"^[\W\d_]*\s*also affiliated with\s*[:：-]?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"^\(?\d+\)?\s*[:：-]?\s*", "", cleaned)
        cleaned = re.sub(r"^[\W\d_]+", "", cleaned)
        cleaned = re.sub(r"[;,.，。:：\s]+$", "", cleaned)
        cleaned = re.sub(r"\s*\([^)]*@[^)]*\)", "", cleaned)
        if len(cleaned) < 4:
            return ""
        return cleaned

    @staticmethod
    def _split_affiliation_candidates(text: str) -> List[str]:
        value = (text or "").strip()
        if not value:
            return []
        normalized = re.sub(
            r"(?<=[A-Za-z\u4e00-\u9fff])\d{1,2}(?=[A-Z\u4e00-\u9fff])",
            "; ",
            value,
        )
        normalized = re.sub(r"(?:(?<=\s)|^)\d{1,2}(?=[A-Za-z\u4e00-\u9fff])", "", normalized)
        parts = [segment.strip() for segment in re.split(r"[;；|]+", normalized) if segment.strip()]
        return parts or [value]

    @staticmethod
    def _domain_to_org_label(domain: str) -> Optional[str]:
        value = (domain or "").strip().lower().strip(".")
        if not value:
            return None

        public_domains = {
            "gmail.com",
            "outlook.com",
            "hotmail.com",
            "qq.com",
            "163.com",
            "126.com",
            "yahoo.com",
            "proton.me",
            "icloud.com",
        }
        if value in public_domains:
            return None

        parts = [segment for segment in value.split(".") if segment]
        if len(parts) < 2:
            return None

        token = parts[-2]
        if not token or token in {
            "mail",
            "email",
            "cs",
            "ece",
            "dept",
            "ac",
            "edu",
            "org",
            "net",
            "com",
            "cn",
        }:
            return None
        if len(token) <= 2:
            return None

        token = token.replace("-", " ")
        if len(token) <= 4:
            return token.upper()
        return token.title()

    @staticmethod
    def _dedupe_preserve_order(values: List[str]) -> List[str]:
        seen = set()
        deduped: List[str] = []
        for value in values:
            key = value.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(value.strip())
        return deduped

    def _extract_abstract(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        for idx, line in enumerate(lines):
            if re.fullmatch(r"abstract[:\s]*", line, flags=re.IGNORECASE):
                abstract_lines: List[str] = []
                for inner in lines[idx + 1 :]:
                    if not inner:
                        if abstract_lines:
                            break
                        continue
                    if self._looks_like_section_heading(inner):
                        break
                    if self._is_noise_line(inner):
                        continue
                    abstract_lines.append(inner)
                    if len(" ".join(abstract_lines).split()) >= 220:
                        break
                if abstract_lines:
                    return self._clean_text(" ".join(abstract_lines))

        abstract_match = re.search(
            r"\babstract\b[:\s]*(.+?)(?=\n\s*(1|i)\.?\s+introduction\b|\bintroduction\b|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if abstract_match:
            return self._clean_text(abstract_match.group(1))[:1200]

        words = text.split()
        return " ".join(words[:180]).strip()

    def _split_sections(self, text: str) -> List[Section]:
        heading_pattern = re.compile(
            r"^\s*(\d+(\.\d+)*)?\s*"
            r"(abstract|introduction|background|related work|method|methods|approach|"
            r"experiments?|results?|discussion|conclusion|conclusions)\s*$",
            flags=re.IGNORECASE,
        )

        sections: List[Section] = []
        current_title = "Main Content"
        current_lines: List[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if heading_pattern.match(line):
                if current_lines:
                    sections.append(
                        Section(
                            title=current_title.title(),
                            content="\n".join(current_lines).strip(),
                            level=2,
                        )
                    )
                current_title = re.sub(r"^\d+(\.\d+)*\s*", "", line).strip()
                current_lines = []
                continue

            current_lines.append(line)

        if current_lines:
            sections.append(
                Section(
                    title=current_title.title(),
                    content="\n".join(current_lines).strip(),
                    level=2,
                )
            )

        if not sections:
            sections.append(Section(title="Main Content", content=text.strip(), level=2))

        return sections

    def _extract_pdf_images(self, reader: Any, cache_key: str) -> List[ImageInfo]:
        paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=True)

        extracted: List[ImageInfo] = []
        seq = 1

        for page_idx, page in enumerate(reader.pages):
            page_images = getattr(page, "images", None)
            if page_images is None:
                continue

            try:
                images_on_page = list(page_images)
            except Exception:
                continue

            for image_idx, image_obj in enumerate(images_on_page):
                data = getattr(image_obj, "data", None)
                if not isinstance(data, (bytes, bytearray)) or len(data) < 2048:
                    continue

                name_hint = str(getattr(image_obj, "name", "") or "")
                ext = self._detect_image_extension(data, name_hint=name_hint)
                if ext is None:
                    continue

                output_path = paper_image_dir / f"page_{page_idx + 1:03d}_{seq:03d}{ext}"
                output_path.write_bytes(bytes(data))

                extracted.append(
                    ImageInfo(
                        url=str(output_path.as_posix()),
                        caption=f"Figure {seq} (page {page_idx + 1})",
                        position=seq,
                        relevance_score=self._estimate_image_relevance(
                            page_index=page_idx,
                            image_index=image_idx,
                            byte_length=len(data),
                        ),
                    )
                )
                seq += 1

        return self._deduplicate_images(extracted)

    def _extract_largest_figures_with_fitz(
        self,
        pdf_path: Path,
        cache_key: str,
        max_images: int = 8,
    ) -> List[ImageInfo]:
        if fitz is None or max_images <= 0:
            return []

        paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=True)
        extracted: List[ImageInfo] = []

        try:
            document = fitz.open(str(pdf_path))
        except Exception:
            return []

        try:
            candidates: List[Tuple[float, int, Any]] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                page_rect = page.rect
                header_cutoff = page_rect.y0 + page_rect.height * HEADER_CUTOFF_RATIO
                rects = self._collect_fitz_image_rects(page)
                for rect in rects:
                    if rect.y0 < header_cutoff:
                        continue
                    if rect.width < page_rect.width * 0.20:
                        continue
                    if rect.height < page_rect.height * 0.06:
                        continue
                    area = rect.width * rect.height
                    candidates.append((area, page_index, rect))

            if not candidates:
                return []

            candidates.sort(key=lambda item: item[0], reverse=True)
            selected = candidates[: max_images * 2]

            seq = 1
            for _, page_index, rect in selected:
                page = document.load_page(page_index)
                page_rect = page.rect
                header_cutoff = page_rect.y0 + page_rect.height * HEADER_CUTOFF_RATIO

                pad_x = max(page_rect.width * 0.01, rect.width * 0.02)
                pad_y = max(page_rect.height * 0.01, rect.height * 0.03)
                clip = fitz.Rect(
                    max(page_rect.x0, rect.x0 - pad_x),
                    max(header_cutoff, rect.y0 - pad_y),
                    min(page_rect.x1, rect.x1 + pad_x),
                    min(page_rect.y1, rect.y1 + pad_y),
                )

                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False)
                except Exception:
                    continue

                if pix.width * pix.height < 220000:
                    continue

                output_path = paper_image_dir / f"page_{page_index + 1:03d}_{seq:03d}.png"
                try:
                    pix.save(str(output_path))
                except Exception:
                    continue

                extracted.append(
                    ImageInfo(
                        url=str(output_path.as_posix()),
                        caption=f"Figure (page {page_index + 1})",
                        position=seq,
                        relevance_score=self._estimate_caption_image_relevance(
                            page_index=page_index,
                            clip_height=clip.height,
                        ),
                    )
                )
                seq += 1

                if len(extracted) >= max_images:
                    break
        finally:
            document.close()

        return self._deduplicate_images(extracted)

    def _extract_figures_by_caption(self, pdf_path: Path, cache_key: str) -> List[ImageInfo]:
        if fitz is None:
            return []

        paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=True)
        extracted: List[ImageInfo] = []
        seq = 1

        try:
            document = fitz.open(str(pdf_path))
        except Exception:
            return []

        try:
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                captions = self._find_figure_captions(page)
                if not captions:
                    continue

                page_rect = page.rect
                header_cutoff = page_rect.y0 + page_rect.height * HEADER_CUTOFF_RATIO
                header_guard = page_rect.y0 + page_rect.height * HEADER_GUARD_RATIO
                relaxed_header_cutoff = max(
                    header_guard,
                    header_cutoff - page_rect.height * RELAXED_HEADER_EXTRA_RATIO,
                )
                image_rects = self._collect_fitz_image_rects(page)
                for caption in captions:
                    cap_rect = caption["rect"]
                    clip = self._select_fitz_figure_bbox(
                        caption_rect=cap_rect,
                        page_rect=page_rect,
                        header_cutoff=header_cutoff,
                        image_rects=image_rects,
                    )
                    if clip is None:
                        continue

                    clip = self._expand_fitz_clip_by_neighbors(
                        clip=clip,
                        page_rect=page_rect,
                        image_rects=image_rects,
                        caption_top=cap_rect.y0,
                        top_guard=header_guard,
                    )
                    clip = self._promote_to_wide_caption_window(
                        clip=clip,
                        page_rect=page_rect,
                        caption_top=cap_rect.y0,
                        top_guard=header_guard,
                        caption_text=caption["text"],
                    )
                    broad_figure = self._is_broad_figure_caption(caption["text"])
                    width_ratio = clip.width / max(page_rect.width, 1e-6)
                    if broad_figure and width_ratio < 0.95:
                        clip = fitz.Rect(
                            min(clip.x0, page_rect.x0 + page_rect.width * WIDE_SIDE_MARGIN_RATIO),
                            clip.y0,
                            max(clip.x1, page_rect.x1 - page_rect.width * WIDE_SIDE_MARGIN_RATIO),
                            clip.y1,
                        )

                    if clip.width < 120 or clip.height < 80:
                        alt_top = max(header_guard, cap_rect.y0 - page_rect.height * WIDE_TOP_WINDOW_RATIO)
                        alt_bottom = cap_rect.y0 - 2
                        alt = fitz.Rect(
                            page_rect.x0 + page_rect.width * WIDE_SIDE_MARGIN_RATIO,
                            alt_top,
                            page_rect.x1 - page_rect.width * WIDE_SIDE_MARGIN_RATIO,
                            alt_bottom,
                        )
                        if alt.width < 120 or alt.height < 80:
                            continue
                        clip = alt

                    bottom_limit = cap_rect.y0 - max(2.0, page_rect.height * 0.003)
                    if broad_figure:
                        pad_x = max(page_rect.width * BROAD_SIDE_PAD_RATIO, clip.width * BROAD_PAD_X_SCALE)
                        pad_y = max(page_rect.height * 0.018, clip.height * BROAD_PAD_Y_SCALE)
                        top_floor = page_rect.y0 + page_rect.height * BROAD_TOP_FLOOR_RATIO
                    else:
                        pad_x = max(page_rect.width * 0.020, clip.width * 0.040)
                        pad_y = max(page_rect.height * 0.016, clip.height * 0.040)
                        top_floor = relaxed_header_cutoff
                    clip = fitz.Rect(
                        max(page_rect.x0, clip.x0 - pad_x),
                        max(top_floor, clip.y0 - pad_y),
                        min(page_rect.x1, clip.x1 + pad_x),
                        min(bottom_limit, clip.y1 + pad_y),
                    )
                    if clip.width < 120 or clip.height < 80:
                        continue

                    pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False)
                    if pix.width * pix.height < 180000:
                        alt_top = max(header_guard, cap_rect.y0 - page_rect.height * WIDE_TOP_WINDOW_RATIO)
                        alt_bottom = cap_rect.y0 - 2
                        alt = fitz.Rect(
                            page_rect.x0 + page_rect.width * WIDE_SIDE_MARGIN_RATIO,
                            alt_top,
                            page_rect.x1 - page_rect.width * WIDE_SIDE_MARGIN_RATIO,
                            alt_bottom,
                        )
                        if alt.width < 120 or alt.height < 80:
                            continue

                        alt_pix = page.get_pixmap(
                            matrix=fitz.Matrix(2.2, 2.2),
                            clip=alt,
                            alpha=False,
                        )
                        if alt_pix.width * alt_pix.height < 180000:
                            continue

                        clip = alt
                        pix = alt_pix

                    output_path = paper_image_dir / f"page_{page_index + 1:03d}_{seq:03d}.png"
                    pix.save(str(output_path))

                    extracted.append(
                        ImageInfo(
                            url=str(output_path.as_posix()),
                            caption=caption["text"],
                            position=seq,
                            relevance_score=self._estimate_caption_image_relevance(
                                page_index=page_index,
                                clip_height=clip.height,
                            ),
                        )
                    )
                    seq += 1
        finally:
            document.close()

        return self._deduplicate_images(extracted)

    def _extract_figures_with_pdfplumber(self, pdf_path: Path, cache_key: str) -> List[ImageInfo]:
        try:
            import pdfplumber
        except Exception:
            return []

        paper_image_dir = self._prepare_image_dir(cache_key=cache_key, reset=True)
        extracted: List[ImageInfo] = []
        seq = 1

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    try:
                        words = page.extract_words(
                            x_tolerance=2,
                            y_tolerance=2,
                            keep_blank_chars=False,
                        )
                    except Exception:
                        # Skip pages with malformed font metadata instead of aborting
                        # extraction for the entire paper.
                        continue
                    captions = self._find_figure_captions_from_words(words)
                    if not captions:
                        continue

                    images = page.images or []
                    header_cutoff = page.height * HEADER_CUTOFF_RATIO
                    header_guard = page.height * HEADER_GUARD_RATIO
                    relaxed_header_cutoff = max(
                        header_guard,
                        header_cutoff - page.height * RELAXED_HEADER_EXTRA_RATIO,
                    )
                    for caption in captions:
                        cap_top = float(caption["top"])
                        rect = self._select_plumber_figure_bbox(
                            caption_top=cap_top,
                            page_width=float(page.width),
                            page_height=float(page.height),
                            header_cutoff=header_cutoff,
                            image_boxes=images,
                            caption_text=caption["text"],
                        )
                        if rect is None:
                            continue

                        x0, top, x1, bottom = rect
                        broad_figure = self._is_broad_figure_caption(caption["text"])
                        width_ratio = (x1 - x0) / max(float(page.width), 1e-6)
                        if broad_figure and width_ratio < 0.95:
                            x0 = min(x0, float(page.width) * WIDE_SIDE_MARGIN_RATIO)
                            x1 = max(x1, float(page.width) * (1.0 - WIDE_SIDE_MARGIN_RATIO))

                        if broad_figure:
                            pad_x = max(float(page.width) * BROAD_SIDE_PAD_RATIO, (x1 - x0) * BROAD_PAD_X_SCALE)
                            pad_y = max(float(page.height) * 0.018, (bottom - top) * BROAD_PAD_Y_SCALE)
                            top_floor = float(page.height) * BROAD_TOP_FLOOR_RATIO
                        else:
                            pad_x = max(float(page.width) * 0.020, (x1 - x0) * 0.035)
                            pad_y = max(float(page.height) * 0.016, (bottom - top) * 0.035)
                            top_floor = relaxed_header_cutoff

                        bottom_limit = cap_top - max(2.0, float(page.height) * 0.003)
                        x0 = max(0.0, x0 - pad_x)
                        x1 = min(float(page.width), x1 + pad_x)
                        top = max(top_floor, top - pad_y)
                        bottom = min(bottom_limit, bottom + pad_y)
                        if bottom - top < 1:
                            continue
                        if x1 - x0 < 120 or bottom - top < 80:
                            continue

                        try:
                            cropped = page.within_bbox((x0, top, x1, bottom))
                            rendered = cropped.to_image(resolution=220)
                            output_path = paper_image_dir / f"page_{page_index + 1:03d}_{seq:03d}.png"
                            rendered.original.save(str(output_path))
                        except Exception:
                            continue

                        extracted.append(
                            ImageInfo(
                                url=str(output_path.as_posix()),
                                caption=caption["text"],
                                position=seq,
                                relevance_score=self._estimate_caption_image_relevance(
                                    page_index=page_index,
                                    clip_height=bottom - top,
                                ),
                            )
                        )
                        seq += 1
        except Exception:
            return []

        return self._deduplicate_images(extracted)

    @staticmethod
    def _collect_fitz_image_rects(page: Any) -> List[Any]:
        if fitz is None:
            return []
        rects: List[Any] = []
        try:
            images = page.get_images(full=True)
        except Exception:
            return []
        for image in images:
            if not image:
                continue
            xref = image[0]
            try:
                for rect in page.get_image_rects(xref):
                    rects.append(rect)
            except Exception:
                continue
        return rects

    @staticmethod
    def _select_fitz_figure_bbox(
        caption_rect: Any,
        page_rect: Any,
        header_cutoff: float,
        image_rects: List[Any],
    ) -> Optional[Any]:
        if fitz is None:
            return None

        cap_top = caption_rect.y0
        header_guard = page_rect.y0 + page_rect.height * HEADER_GUARD_RATIO
        candidates: List[Any] = []
        for rect in image_rects:
            if rect.y1 > cap_top + 4:
                continue
            if rect.y0 < header_guard:
                continue
            if rect.width < page_rect.width * 0.16:
                continue
            if rect.height < page_rect.height * 0.06:
                continue
            distance = cap_top - rect.y1
            if distance < -2:
                continue
            area = rect.width * rect.height
            candidates.append((distance, -area, rect))

        if candidates:
            _, _, best = sorted(candidates, key=lambda item: (item[0], item[1]))[0]

            cluster: List[Any] = [best]
            for rect in image_rects:
                if rect is best:
                    continue
                if rect.y1 > cap_top + 4:
                    continue
                if rect.y0 < header_guard:
                    continue
                if rect.width < page_rect.width * 0.10:
                    continue
                if rect.height < page_rect.height * 0.04:
                    continue

                x_gap = page_rect.width * CLUSTER_X_GAP_RATIO
                if rect.x1 < best.x0 - x_gap or rect.x0 > best.x1 + x_gap:
                    continue

                overlap = min(rect.y1, best.y1) - max(rect.y0, best.y0)
                if overlap < min(rect.height, best.height) * 0.12 and abs(rect.y0 - best.y0) > page_rect.height * 0.06:
                    continue

                cluster.append(rect)

            if len(cluster) >= 2:
                union_x0 = min(r.x0 for r in cluster)
                union_y0 = min(r.y0 for r in cluster)
                union_x1 = max(r.x1 for r in cluster)
                union_y1 = max(r.y1 for r in cluster)
                union = fitz.Rect(union_x0, union_y0, union_x1, union_y1)
                best_area = best.width * best.height
                union_area = union.width * union.height
                if union_area >= best_area * 1.20 and union.height <= page_rect.height * 0.72:
                    best = union

            pad_x = page_rect.width * 0.01
            pad_y = page_rect.height * 0.01
            return fitz.Rect(
                max(page_rect.x0, best.x0 - pad_x),
                max(header_guard, best.y0 - pad_y),
                min(page_rect.x1, best.x1 + pad_x),
                min(caption_rect.y0 - 2, best.y1 + pad_y),
            )

        fragment_pool: List[Any] = []
        for rect in image_rects:
            if rect.y1 > cap_top + 4:
                continue
            if rect.y0 < header_guard:
                continue
            if cap_top - rect.y1 > page_rect.height * 0.62:
                continue
            if rect.width < page_rect.width * 0.04:
                continue
            if rect.height < page_rect.height * 0.025:
                continue
            area = rect.width * rect.height
            if area < page_rect.width * page_rect.height * 0.0004:
                continue
            fragment_pool.append(rect)

        if len(fragment_pool) >= 2:
            union_x0 = min(rect.x0 for rect in fragment_pool)
            union_y0 = min(rect.y0 for rect in fragment_pool)
            union_x1 = max(rect.x1 for rect in fragment_pool)
            union_y1 = max(rect.y1 for rect in fragment_pool)
            union_w = union_x1 - union_x0
            union_h = union_y1 - union_y0
            if union_w >= page_rect.width * 0.28 and union_h >= page_rect.height * 0.10:
                union_area = max(union_w * union_h, 1.0)
                covered_area = sum(rect.width * rect.height for rect in fragment_pool)
                coverage = covered_area / union_area
                if coverage >= FRAGMENT_COVERAGE_THRESHOLD:
                    pad_x = page_rect.width * 0.01
                    pad_y = page_rect.height * 0.01
                    return fitz.Rect(
                        max(page_rect.x0, union_x0 - pad_x),
                        max(header_guard, union_y0 - pad_y),
                        min(page_rect.x1, union_x1 + pad_x),
                        min(caption_rect.y0 - 2, union_y1 + pad_y),
                    )

        top = max(header_guard, cap_top - page_rect.height * ALT_TOP_WINDOW_RATIO)
        bottom = cap_top - 2
        if bottom - top < 90:
            return None

        return fitz.Rect(
            page_rect.x0 + page_rect.width * ALT_SIDE_MARGIN_RATIO,
            top,
            page_rect.x1 - page_rect.width * ALT_SIDE_MARGIN_RATIO,
            bottom,
        )

    @staticmethod
    def _expand_fitz_clip_by_neighbors(
        clip: Any,
        page_rect: Any,
        image_rects: List[Any],
        caption_top: float,
        top_guard: float,
    ) -> Any:
        if fitz is None:
            return clip

        neighbors: List[Any] = []
        for rect in image_rects:
            if rect.y1 > caption_top + 6:
                continue
            if rect.y0 < top_guard:
                continue
            if rect.width < page_rect.width * 0.03:
                continue
            if rect.height < page_rect.height * 0.02:
                continue
            if rect.x1 < clip.x0 - page_rect.width * NEIGHBOR_X_EXPAND_RATIO:
                continue
            if rect.x0 > clip.x1 + page_rect.width * NEIGHBOR_X_EXPAND_RATIO:
                continue

            vertical_overlap = min(rect.y1, clip.y1) - max(rect.y0, clip.y0)
            align_close = (
                vertical_overlap >= min(rect.height, clip.height) * 0.08
                or abs(rect.y0 - clip.y0) <= page_rect.height * 0.04
                or abs(rect.y1 - clip.y1) <= page_rect.height * 0.04
            )
            if not align_close:
                continue
            neighbors.append(rect)

        if not neighbors:
            return clip

        union_x0 = min([clip.x0] + [r.x0 for r in neighbors])
        union_y0 = min([clip.y0] + [r.y0 for r in neighbors])
        union_x1 = max([clip.x1] + [r.x1 for r in neighbors])
        union_y1 = max([clip.y1] + [r.y1 for r in neighbors])

        pad_x = page_rect.width * 0.012
        pad_y = page_rect.height * 0.012
        return fitz.Rect(
            max(page_rect.x0, union_x0 - pad_x),
            max(top_guard, union_y0 - pad_y),
            min(page_rect.x1, union_x1 + pad_x),
            min(caption_top - 2, union_y1 + pad_y),
        )

    @staticmethod
    def _promote_to_wide_caption_window(
        clip: Any,
        page_rect: Any,
        caption_top: float,
        top_guard: float,
        caption_text: str,
    ) -> Any:
        if fitz is None:
            return clip

        width_ratio = clip.width / max(page_rect.width, 1e-6)
        broad_hint = PaperFetcher._is_broad_figure_caption(caption_text)
        if width_ratio >= WIDE_FIGURE_MIN_WIDTH_RATIO and not broad_hint:
            return clip

        wide = fitz.Rect(
            page_rect.x0 + page_rect.width * WIDE_SIDE_MARGIN_RATIO,
            max(top_guard, caption_top - page_rect.height * WIDE_TOP_WINDOW_RATIO),
            page_rect.x1 - page_rect.width * WIDE_SIDE_MARGIN_RATIO,
            min(page_rect.y1, caption_top - 2),
        )
        if wide.width < 120 or wide.height < 80:
            return clip
        if broad_hint and width_ratio <= FORCE_WIDE_NARROW_RATIO:
            return wide
        if wide.get_area() > clip.get_area() * 1.15:
            return wide
        return clip

    @staticmethod
    def _find_figure_captions(page: Any) -> List[Dict[str, Any]]:
        if fitz is None:
            return []

        captions: List[Dict[str, Any]] = []
        pattern = re.compile(r"(figure|fig\.?)\s*\d+[\s:.\-]+", re.IGNORECASE)

        try:
            blocks = page.get_text("blocks")
        except Exception:
            return []

        for block in blocks:
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text = block[:5]
            clean = re.sub(r"\s+", " ", str(text or "")).strip()
            if not clean:
                continue

            match = pattern.search(clean)
            if not match:
                continue
            if match.start() > 18:
                continue

            captions.append(
                {
                    "text": clean[match.start() : match.start() + 160],
                    "rect": fitz.Rect(x0, y0, x1, y1),
                }
            )

        captions.sort(key=lambda item: item["rect"].y0)
        return captions

    @staticmethod
    def _find_figure_captions_from_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not words:
            return []
        pattern = re.compile(r"(figure|fig\.?)\s*\d+[\s:._\-]+", re.IGNORECASE)

        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for word in words:
            line_key = int(round(float(word.get("top", 0)) / 3.0))
            grouped.setdefault(line_key, []).append(word)

        captions: List[Dict[str, Any]] = []
        for _, line_words in sorted(grouped.items(), key=lambda item: item[0]):
            sorted_words = sorted(line_words, key=lambda w: float(w.get("x0", 0)))
            text = " ".join(str(w.get("text", "")).strip() for w in sorted_words).strip()
            text = re.sub(r"\s+", " ", text)
            if not text:
                continue

            match = pattern.search(text)
            if not match:
                continue
            if match.start() > 18:
                continue

            top = min(float(w.get("top", 0)) for w in sorted_words)
            bottom = max(float(w.get("bottom", 0)) for w in sorted_words)
            captions.append(
                {
                    "text": text[match.start() : match.start() + 160],
                    "top": top,
                    "bottom": bottom,
                }
            )
        return captions

    @staticmethod
    def _select_plumber_figure_bbox(
        caption_top: float,
        page_width: float,
        page_height: float,
        header_cutoff: float,
        image_boxes: List[Dict[str, Any]],
        caption_text: str = "",
    ) -> Optional[Tuple[float, float, float, float]]:
        header_guard = page_height * HEADER_GUARD_RATIO
        candidates: List[Tuple[float, float, Tuple[float, float, float, float]]] = []
        for image in image_boxes:
            x0 = float(image.get("x0", 0))
            x1 = float(image.get("x1", 0))
            top = float(image.get("top", 0))
            bottom = float(image.get("bottom", 0))

            if bottom > caption_top + 4:
                continue
            if top < header_guard:
                continue
            if x1 - x0 < page_width * 0.16:
                continue
            if bottom - top < page_height * 0.06:
                continue

            distance = caption_top - bottom
            area = (x1 - x0) * (bottom - top)
            candidates.append((distance, -area, (x0, top, x1, bottom)))

        if candidates:
            _, _, rect = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
            best_x0, best_top, best_x1, best_bottom = rect
            best_w = best_x1 - best_x0
            best_h = best_bottom - best_top

            cluster: List[Tuple[float, float, float, float]] = [rect]
            x_gap = page_width * CLUSTER_X_GAP_RATIO
            for image in image_boxes:
                x0 = float(image.get("x0", 0))
                x1 = float(image.get("x1", 0))
                top = float(image.get("top", 0))
                bottom = float(image.get("bottom", 0))
                if (x0, top, x1, bottom) == rect:
                    continue
                if bottom > caption_top + 4:
                    continue
                if top < header_guard:
                    continue
                if x1 - x0 < page_width * 0.03:
                    continue
                if bottom - top < page_height * 0.02:
                    continue
                if x1 < best_x0 - x_gap or x0 > best_x1 + x_gap:
                    continue

                overlap = min(bottom, best_bottom) - max(top, best_top)
                aligned = (
                    overlap >= min(bottom - top, best_h) * 0.05
                    or abs(top - best_top) <= page_height * 0.12
                    or abs(bottom - best_bottom) <= page_height * 0.12
                )
                if not aligned:
                    continue
                cluster.append((x0, top, x1, bottom))

            if len(cluster) >= 2:
                union_x0 = min(r[0] for r in cluster)
                union_top = min(r[1] for r in cluster)
                union_x1 = max(r[2] for r in cluster)
                union_bottom = max(r[3] for r in cluster)
                union_w = union_x1 - union_x0
                union_h = union_bottom - union_top
                union_area = max(union_w * union_h, 1.0)
                covered_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in cluster)
                coverage = covered_area / union_area
                if (
                    union_w >= page_width * 0.36
                    and union_h >= page_height * 0.12
                    and coverage >= FRAGMENT_COVERAGE_THRESHOLD
                ):
                    rect = (union_x0, union_top, union_x1, union_bottom)

            rect = PaperFetcher._promote_to_wide_window_tuple(
                rect=rect,
                page_width=page_width,
                page_height=page_height,
                caption_top=caption_top,
                caption_text=caption_text,
            )

            x0, top, x1, bottom = rect
            pad_x = page_width * 0.012
            pad_y = page_height * 0.012
            return (
                max(0.0, x0 - pad_x),
                max(header_guard, top - pad_y),
                min(page_width, x1 + pad_x),
                min(caption_top - 2, bottom + pad_y),
            )

        fragments: List[Tuple[float, float, float, float]] = []
        for image in image_boxes:
            x0 = float(image.get("x0", 0))
            x1 = float(image.get("x1", 0))
            top = float(image.get("top", 0))
            bottom = float(image.get("bottom", 0))
            if bottom > caption_top + 4:
                continue
            if top < header_guard:
                continue
            if caption_top - bottom > page_height * 0.62:
                continue
            if x1 - x0 < page_width * 0.04:
                continue
            if bottom - top < page_height * 0.025:
                continue
            area = (x1 - x0) * (bottom - top)
            if area < page_width * page_height * 0.0004:
                continue
            fragments.append((x0, top, x1, bottom))

        if len(fragments) >= 2:
            union_x0 = min(rect[0] for rect in fragments)
            union_top = min(rect[1] for rect in fragments)
            union_x1 = max(rect[2] for rect in fragments)
            union_bottom = max(rect[3] for rect in fragments)
            union_w = union_x1 - union_x0
            union_h = union_bottom - union_top
            if union_w >= page_width * 0.28 and union_h >= page_height * 0.10:
                pad_x = page_width * 0.01
                pad_y = page_height * 0.01
                return (
                    max(0.0, union_x0 - pad_x),
                    max(header_guard, union_top - pad_y),
                    min(page_width, union_x1 + pad_x),
                    min(caption_top - 2, union_bottom + pad_y),
                )

        top = max(header_guard, caption_top - page_height * WIDE_TOP_WINDOW_RATIO)
        bottom = caption_top - 2
        if bottom - top < 90:
            return None
        return (
            page_width * WIDE_SIDE_MARGIN_RATIO,
            top,
            page_width * (1.0 - WIDE_SIDE_MARGIN_RATIO),
            bottom,
        )

    @staticmethod
    def _promote_to_wide_window_tuple(
        rect: Tuple[float, float, float, float],
        page_width: float,
        page_height: float,
        caption_top: float,
        caption_text: str,
    ) -> Tuple[float, float, float, float]:
        x0, top, x1, bottom = rect
        width_ratio = (x1 - x0) / max(page_width, 1e-6)
        broad_hint = PaperFetcher._is_broad_figure_caption(caption_text)
        if width_ratio >= WIDE_FIGURE_MIN_WIDTH_RATIO and not broad_hint:
            return rect

        wide_top = max(page_height * HEADER_GUARD_RATIO, caption_top - page_height * WIDE_TOP_WINDOW_RATIO)
        wide_bottom = caption_top - 2
        wide = (
            page_width * WIDE_SIDE_MARGIN_RATIO,
            wide_top,
            page_width * (1.0 - WIDE_SIDE_MARGIN_RATIO),
            wide_bottom,
        )
        wide_area = max((wide[2] - wide[0]) * (wide[3] - wide[1]), 1.0)
        cur_area = max((x1 - x0) * (bottom - top), 1.0)
        if broad_hint and width_ratio <= FORCE_WIDE_NARROW_RATIO:
            return wide
        if wide[2] - wide[0] >= 120 and wide[3] - wide[1] >= 80 and wide_area > cur_area * 1.15:
            return wide
        return rect

    @staticmethod
    def _is_broad_figure_caption(caption_text: str) -> bool:
        text = (caption_text or "").lower()
        broad_tokens = (
            "(a)",
            "(b)",
            "(c)",
            "overview",
            "framework",
            "taxonomy",
            "task suite",
            "pipeline",
            "architecture",
            "system diagram",
            "left:",
            "right:",
        )
        if any(token in text for token in broad_tokens):
            return True

        match = re.search(r"(?:figure|fig\.?)\s*(\d+)", text, re.IGNORECASE)
        if match:
            try:
                number = int(match.group(1))
            except ValueError:
                number = 0
            # Early figures are often global overview charts; prefer safer wide fallback.
            if 0 < number <= 2:
                return True
        return False

    def _prepare_image_dir(self, cache_key: str, reset: bool = False) -> Path:
        safe_key = self._safe_key(cache_key)
        if safe_key == self.paper_key:
            paper_image_dir = self.images_dir
        else:
            paper_image_dir = self.images_dir / f"_{safe_key}"
        paper_image_dir.mkdir(parents=True, exist_ok=True)

        if reset:
            for old in paper_image_dir.glob("*"):
                if old.is_file():
                    old.unlink()

        return paper_image_dir

    def _deduplicate_images(self, images: List[ImageInfo]) -> List[ImageInfo]:
        deduped: List[ImageInfo] = []
        seen_hashes = set()

        for image in images:
            image_path = Path(image.url)
            if not image_path.exists() or image_path.stat().st_size <= 0:
                continue

            file_hash = self._hash_file(image_path)
            if file_hash in seen_hashes:
                image_path.unlink(missing_ok=True)
                continue

            seen_hashes.add(file_hash)
            deduped.append(image)

        return deduped

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.md5()  # noqa: S324 - dedupe only
        with path.open("rb") as file_obj:
            while True:
                chunk = file_obj.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _normalize_page_text(text: str) -> str:
        if not text:
            return ""

        normalized = text.replace("\r", "\n")
        normalized = normalized.replace("-\n", "")
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
        normalized = re.sub(r"[ \t]{2,}", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        lines: List[str] = []
        for raw_line in normalized.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if re.fullmatch(r"(\d+|Page \d+|arXiv:.*)", line, flags=re.IGNORECASE):
                continue
            lines.append(line)

        return "\n".join(lines).strip()

    @staticmethod
    def _is_repeated_noise_line(line: str, frequency: int) -> bool:
        if frequency < 3:
            return False
        if re.search(r"\b(arxiv|proceedings|copyright|acm)\b", line, re.IGNORECASE):
            return True
        return len(line) < 80

    @staticmethod
    def _is_noise_line(line: str) -> bool:
        lower = line.lower()
        if re.search(r"\b(copyright|permission|acm|isbn|doi)\b", lower):
            return True
        return False

    @staticmethod
    def _looks_like_section_heading(line: str) -> bool:
        return bool(
            re.match(
                r"^\s*(\d+(\.\d+)*)?\s*"
                r"(introduction|background|related work|method|methods|approach|"
                r"experiments?|results?|discussion|conclusion|references?)\b",
                line,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _estimate_caption_image_relevance(page_index: int, clip_height: float) -> float:
        page_bonus = max(0.0, 0.75 - page_index * 0.04)
        height_bonus = min(clip_height / 900.0, 1.0) * 0.25
        score = 0.35 + page_bonus + height_bonus
        return round(min(score, 1.0), 3)

    @staticmethod
    def _detect_image_extension(data: bytes, name_hint: str = "") -> Optional[str]:
        lower_name = (name_hint or "").lower()
        for candidate in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"):
            if lower_name.endswith(candidate):
                return ".jpg" if candidate == ".jpeg" else candidate

        header = data[:12]
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if header.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if header[:6] in (b"GIF87a", b"GIF89a"):
            return ".gif"
        if header.startswith(b"BM"):
            return ".bmp"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return ".webp"
        if header[:4] in (b"II*\x00", b"MM\x00*"):
            return ".tif"
        return None

    @staticmethod
    def _estimate_image_relevance(
        page_index: int,
        image_index: int,
        byte_length: int,
    ) -> float:
        size_bonus = min(byte_length / (512 * 1024), 1.0) * 0.3
        page_bonus = max(0.0, 0.8 - page_index * 0.05)
        position_bonus = max(0.0, 0.2 - image_index * 0.02)
        score = 0.2 + size_bonus + page_bonus + position_bonus
        return round(min(score, 1.0), 3)


def parse_input(source: str) -> Tuple[str, Optional[str], Optional[Path]]:
    raw = (source or "").strip()
    if not raw:
        raise ValueError("Input cannot be empty.")

    local_path = Path(raw).expanduser()
    if local_path.exists() and local_path.is_file():
        if local_path.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF file is supported for local input: {raw}")
        return "pdf", None, local_path.resolve()

    if ARXIV_ID_PATTERN.fullmatch(raw):
        return "arxiv", raw, None

    if "arxiv.org" in raw:
        match = ARXIV_ID_PATTERN.search(raw)
        if not match:
            raise ValueError(f"Invalid Arxiv URL: {raw}")
        arxiv_id = match.group("id")
        if arxiv_id.endswith(".pdf"):
            arxiv_id = arxiv_id[: -len(".pdf")]
        return "arxiv", arxiv_id, None

    if raw.lower().endswith(".pdf"):
        raise FileNotFoundError(f"PDF not found: {raw}")

    raise ValueError(f"Unsupported input: {raw}")


def safe_key(value: str) -> str:
    return (value or "paper").replace("/", "_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone parser for Arxiv paper/PDF.")
    parser.add_argument("input", help="Arxiv URL/ID or local PDF path")
    parser.add_argument("--cache-dir", default=".paper2wechat", help="Cache directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--source",
        choices=("auto", "always", "never"),
        default="auto",
        help="Whether to fetch arXiv TeX/source for figure extraction (default: auto)",
    )
    args = parser.parse_args()

    mode, arxiv_id, local_pdf = parse_input(args.input.strip())
    fetcher = PaperFetcher(
        cache_dir=args.cache_dir,
        verbose=args.verbose,
        source_policy=args.source,
    )

    if args.verbose:
        if mode == "arxiv":
            print(f"Mode: arXiv ({arxiv_id})", file=sys.stderr, flush=True)
        else:
            print(f"Mode: PDF ({local_pdf})", file=sys.stderr, flush=True)

    if mode == "arxiv":
        assert arxiv_id is not None
        paper = fetcher.fetch_from_url(f"https://arxiv.org/abs/{arxiv_id}")
        cache_key = safe_key(arxiv_id)
    else:
        assert local_pdf is not None
        paper = fetcher.fetch_from_pdf(str(local_pdf))
        cache_key = safe_key(local_pdf.stem)

    paper_root = Path(args.cache_dir) / cache_key
    parsed_path = paper_root / "parsed" / f"{cache_key}.json"
    images_dir = paper_root / "images"

    if args.verbose:
        print("Backend: skill-parser")
        print(f"Source: {args.input}")
        print(f"Title: {paper.title}")
        print(f"Sections: {len(paper.sections)}")
        print(f"Images extracted: {len(paper.images)}")
        print(f"Image backend: {fetcher.last_image_backend}")
        if fetcher.last_source_status:
            print(f"TeX source status: {fetcher.last_source_status}")
        print(f"Paper dir: {paper_root.as_posix()}")

    print(f"Parsed cache: {parsed_path.as_posix()}")
    print(f"Images dir: {images_dir.as_posix()}")


if __name__ == "__main__":
    main()
