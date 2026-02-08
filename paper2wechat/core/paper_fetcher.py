"""
Paper fetching module - handles URL and PDF input
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from .models import ImageInfo, Paper, Section
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover - requests should exist in runtime deps.
    requests = None

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None


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

        page_lines_by_page: List[List[str]] = []
        for page in reader.pages:
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

        sections = self._split_sections(full_text)
        abstract = self._extract_abstract(full_text)
        cache_key = arxiv_id or pdf_file.stem
        images = self._extract_figures_by_caption(
            pdf_path=pdf_file,
            cache_key=cache_key,
        )
        if not images:
            images = self._extract_figures_with_pdfplumber(
                pdf_path=pdf_file,
                cache_key=cache_key,
            )
        if not images:
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
                header_cutoff = page_rect.y0 + page_rect.height * 0.10
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
                    if clip.width < 120 or clip.height < 80:
                        continue

                    pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), clip=clip, alpha=False)
                    if pix.width * pix.height < 180000:
                        continue

                    output_path = paper_image_dir / f"page_{page_index + 1:03d}_{seq:03d}.png"
                    pix.save(str(output_path))

                    caption_text = caption["text"]
                    extracted.append(
                        ImageInfo(
                            url=str(output_path.as_posix()),
                            caption=caption_text,
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
                    words = page.extract_words(
                        x_tolerance=2,
                        y_tolerance=2,
                        keep_blank_chars=False,
                    )
                    captions = self._find_figure_captions_from_words(words)
                    if not captions:
                        continue

                    images = page.images or []
                    header_cutoff = page.height * 0.10
                    for caption in captions:
                        cap_top = float(caption["top"])
                        rect = self._select_plumber_figure_bbox(
                            caption_top=cap_top,
                            page_width=float(page.width),
                            page_height=float(page.height),
                            header_cutoff=header_cutoff,
                            image_boxes=images,
                        )
                        if rect is None:
                            continue

                        x0, top, x1, bottom = rect
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
        candidates: List[Any] = []
        for rect in image_rects:
            if rect.y1 > cap_top + 4:
                continue
            if rect.y0 < header_cutoff:
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
            pad_x = page_rect.width * 0.01
            pad_y = page_rect.height * 0.01
            return fitz.Rect(
                max(page_rect.x0, best.x0 - pad_x),
                max(header_cutoff, best.y0 - pad_y),
                min(page_rect.x1, best.x1 + pad_x),
                min(caption_rect.y0 - 2, best.y1 + pad_y),
            )

        # Merge fragmented image objects (common in vector-heavy PDFs).
        fragment_pool: List[Any] = []
        for rect in image_rects:
            if rect.y1 > cap_top + 4:
                continue
            if rect.y0 < header_cutoff:
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
                pad_x = page_rect.width * 0.01
                pad_y = page_rect.height * 0.01
                return fitz.Rect(
                    max(page_rect.x0, union_x0 - pad_x),
                    max(header_cutoff, union_y0 - pad_y),
                    min(page_rect.x1, union_x1 + pad_x),
                    min(caption_rect.y0 - 2, union_y1 + pad_y),
                )

        # Fallback region if we cannot bind to an image object.
        top = max(header_cutoff, cap_top - page_rect.height * 0.32)
        bottom = cap_top - 6
        if bottom - top < 90:
            return None

        return fitz.Rect(
            page_rect.x0 + page_rect.width * 0.08,
            top,
            page_rect.x1 - page_rect.width * 0.08,
            bottom,
        )

    @staticmethod
    def _find_figure_captions_from_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not words:
            return []
        pattern = re.compile(r"^(figure|fig\.?)\s*\d+", re.IGNORECASE)

        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for word in words:
            line_key = int(round(float(word.get("top", 0)) / 3.0))
            grouped.setdefault(line_key, []).append(word)

        captions: List[Dict[str, Any]] = []
        for _, line_words in sorted(grouped.items(), key=lambda item: item[0]):
            sorted_words = sorted(line_words, key=lambda w: float(w.get("x0", 0)))
            text = " ".join(str(w.get("text", "")).strip() for w in sorted_words).strip()
            text = re.sub(r"\s+", " ", text)
            if not text or not pattern.match(text):
                continue

            top = min(float(w.get("top", 0)) for w in sorted_words)
            bottom = max(float(w.get("bottom", 0)) for w in sorted_words)
            captions.append(
                {
                    "text": text[:160],
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
    ) -> Optional[tuple[float, float, float, float]]:
        candidates: List[tuple[float, float, tuple[float, float, float, float]]] = []
        for image in image_boxes:
            x0 = float(image.get("x0", 0))
            x1 = float(image.get("x1", 0))
            top = float(image.get("top", 0))
            bottom = float(image.get("bottom", 0))

            if bottom > caption_top + 4:
                continue
            if top < header_cutoff:
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
            x0, top, x1, bottom = rect
            pad_x = page_width * 0.01
            pad_y = page_height * 0.01
            return (
                max(0.0, x0 - pad_x),
                max(header_cutoff, top - pad_y),
                min(page_width, x1 + pad_x),
                min(caption_top - 2, bottom + pad_y),
            )

        # Merge fragmented image blocks when no single large block exists.
        fragments: List[tuple[float, float, float, float]] = []
        for image in image_boxes:
            x0 = float(image.get("x0", 0))
            x1 = float(image.get("x1", 0))
            top = float(image.get("top", 0))
            bottom = float(image.get("bottom", 0))
            if bottom > caption_top + 4:
                continue
            if top < header_cutoff:
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
                    max(header_cutoff, union_top - pad_y),
                    min(page_width, union_x1 + pad_x),
                    min(caption_top - 2, union_bottom + pad_y),
                )

        top = max(header_cutoff, caption_top - page_height * 0.32)
        bottom = caption_top - 6
        if bottom - top < 90:
            return None
        return (
            page_width * 0.08,
            top,
            page_width * 0.92,
            bottom,
        )

    @staticmethod
    def _find_figure_captions(page: Any) -> List[Dict[str, Any]]:
        if fitz is None:
            return []

        captions: List[Dict[str, Any]] = []
        pattern = re.compile(r"^(figure|fig\.?)\s*\d+[\s:.\-]+", re.IGNORECASE)

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
            if not pattern.match(clean):
                continue

            captions.append({"text": clean[:160], "rect": fitz.Rect(x0, y0, x1, y1)})

        captions.sort(key=lambda item: item["rect"].y0)
        return captions

    def _prepare_image_dir(self, cache_key: str, reset: bool = False) -> Path:
        safe_key = cache_key.replace("/", "_")
        paper_image_dir = self.images_dir / safe_key
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
        digest = hashlib.md5()  # noqa: S324 - used only for duplicate detection.
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
