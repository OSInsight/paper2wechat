"""
Paper fetching module - handles URL and PDF input
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from .models import ImageInfo, Paper, Section
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover - requests should exist in runtime deps.
    requests = None


class FetchError(RuntimeError):
    """Raised when paper fetching/parsing fails."""


ARXIV_ID_PATTERN = re.compile(
    r"(?P<id>(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?)",
    re.IGNORECASE,
)


class PaperFetcher:
    """Fetch paper content from various sources"""

    def __init__(self, cache_dir: str = ".paper2wechat", timeout: int = 30):
        self.timeout = timeout
        self.cache_root = Path(cache_dir)
        self.download_dir = self.cache_root / "downloads"
        self.parsed_dir = self.cache_root / "parsed"
        self.images_dir = self.cache_root / "images"

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_from_url(self, url: str) -> Paper:
        """
        Fetch paper from Arxiv URL
        
        Args:
            url: Arxiv URL (https://arxiv.org/abs/XXXX.XXXXX)
        
        Returns:
            Paper object with extracted content
        
        Raises:
            ValueError: If URL is invalid
            ConnectionError: If unable to fetch
        """
        arxiv_id = self.parse_arxiv_url(url)
        metadata = self._fetch_arxiv_metadata(arxiv_id)

        pdf_url = metadata.get("pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = self._download_pdf(pdf_url, arxiv_id)

        paper = self.fetch_from_pdf(
            str(pdf_path),
            arxiv_id=arxiv_id,
            source_url=url,
        )

        paper.title = metadata.get("title") or paper.title
        paper.abstract = metadata.get("abstract") or paper.abstract
        paper.authors = metadata.get("authors") or paper.authors
        paper.published_date = metadata.get("published_date") or paper.published_date
        paper.pdf_url = pdf_url
        paper.url = url

        self._save_parsed_cache(paper, cache_key=arxiv_id)
        return paper
    
    def fetch_from_pdf(
        self,
        pdf_path: str,
        arxiv_id: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Paper:
        """
        Fetch paper from local PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Paper object with extracted content
        
        Raises:
            FileNotFoundError: If PDF not found
            IOError: If PDF cannot be read
        """
        pdf_file = Path(pdf_path).expanduser().resolve()
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_file}")

        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - dependency issue
            raise FetchError("pypdf is required for PDF parsing.") from exc

        try:
            reader = PdfReader(str(pdf_file))
        except Exception as exc:
            raise FetchError(f"Unable to read PDF: {pdf_file}") from exc

        metadata = reader.metadata or {}
        title = self._clean_text(str(metadata.get("/Title", "") or "").strip())
        if not title:
            title = pdf_file.stem

        authors = self._parse_authors(
            self._clean_text(str(metadata.get("/Author", "") or "").strip())
        )

        page_texts: List[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            clean = self._clean_text(text)
            if clean:
                page_texts.append(clean)

        full_text = "\n\n".join(page_texts)
        if not full_text:
            raise FetchError(f"No extractable text found in PDF: {pdf_file}")

        sections = self._split_sections(full_text)
        abstract = self._extract_abstract(full_text)
        cache_key = arxiv_id or pdf_file.stem
        images = self._extract_pdf_images(reader, cache_key=cache_key)

        paper = Paper(
            title=title,
            authors=authors,
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
        """Extract arxiv ID from URL"""
        value = (url or "").strip()
        if not value:
            raise ValueError("Arxiv URL/ID cannot be empty.")

        # Accept bare IDs like 2301.00000 or cs/0112017.
        if ARXIV_ID_PATTERN.fullmatch(value):
            return value

        if "arxiv.org" in value:
            match = ARXIV_ID_PATTERN.search(value)
            if match:
                arxiv_id = match.group("id")
                return arxiv_id.removesuffix(".pdf")

        raise ValueError(f"Invalid Arxiv URL or ID: {url}")

    def _fetch_arxiv_metadata(self, arxiv_id: str) -> Dict[str, Any]:
        api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        xml_text = self._http_get(api_url).decode("utf-8", errors="replace")

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise FetchError(f"Failed to parse Arxiv API response for {arxiv_id}") from exc

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            raise FetchError(f"Arxiv paper not found: {arxiv_id}")

        title = self._clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        abstract = self._clean_text(
            entry.findtext("atom:summary", default="", namespaces=ns)
        )
        authors = [
            self._clean_text(author.findtext("atom:name", default="", namespaces=ns))
            for author in entry.findall("atom:author", ns)
            if self._clean_text(author.findtext("atom:name", default="", namespaces=ns))
        ]

        published_raw = entry.findtext("atom:published", default="", namespaces=ns)
        published_date = None
        if published_raw:
            try:
                published_date = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                published_date = None

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
            "published_date": published_date,
            "pdf_url": pdf_url,
        }

    def _download_pdf(self, pdf_url: str, arxiv_id: str) -> Path:
        safe_id = arxiv_id.replace("/", "_")
        output_path = self.download_dir / f"{safe_id}.pdf"
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        pdf_bytes = self._http_get(pdf_url)
        output_path.write_bytes(pdf_bytes)
        return output_path

    def _save_parsed_cache(self, paper: Paper, cache_key: str) -> None:
        safe_key = cache_key.replace("/", "_")
        cache_path = self.parsed_dir / f"{safe_key}.json"

        payload = {
            "title": paper.title,
            "authors": paper.authors,
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
            "saved_at": datetime.utcnow().isoformat() + "Z",
        }

        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _http_get(self, url: str) -> bytes:
        headers = {"User-Agent": "paper2wechat/0.1.0"}

        if requests is not None:
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.content
            except Exception as exc:
                raise FetchError(f"Request failed: {url}") from exc

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.URLError as exc:  # pragma: no cover
            raise FetchError(f"Request failed: {url}") from exc

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_authors(author_field: str) -> List[str]:
        if not author_field:
            return []
        parts = re.split(r",| and ", author_field)
        return [part.strip() for part in parts if part.strip()]

    def _extract_abstract(self, text: str) -> str:
        abstract_match = re.search(
            r"\babstract\b[:\s]*(.+?)(?=\n\s*\n|\n\s*\d+\.?\s+[A-Z]|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if abstract_match:
            return self._clean_text(abstract_match.group(1))

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
        safe_key = cache_key.replace("/", "_")
        paper_image_dir = self.images_dir / safe_key
        paper_image_dir.mkdir(parents=True, exist_ok=True)

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

                caption = f"Figure {seq} (page {page_idx + 1})"
                extracted.append(
                    ImageInfo(
                        url=str(output_path.as_posix()),
                        caption=caption,
                        position=seq,
                        relevance_score=self._estimate_image_relevance(
                            page_index=page_idx,
                            image_index=image_idx,
                            byte_length=len(data),
                        ),
                    )
                )
                seq += 1

        return extracted

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
