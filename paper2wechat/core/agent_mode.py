"""
Agent mode entrypoint - parse natural language request and run conversion.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .converter import PaperConverter
from .paper_fetcher import PaperFetcher


STYLE_CHOICES = {
    "academic-science",
    "academic-tech",
    "academic-trend",
    "academic-applied",
}


@dataclass
class AgentIntent:
    source: str
    style: str
    images: int
    max_length: int
    output: Optional[str]
    preview: bool


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agent mode for paper2wechat (natural-language request -> markdown)."
    )
    parser.add_argument(
        "request",
        help="Natural language request or direct Arxiv URL/PDF path.",
    )
    parser.add_argument(
        "--style",
        choices=sorted(STYLE_CHOICES),
        help="Force style override.",
    )
    parser.add_argument(
        "--images",
        type=int,
        help="Force max images override.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        help="Force max output length override.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Force output markdown path.",
    )
    parser.add_argument(
        "--cache-dir",
        default=".paper2wechat",
        help="Cache directory for downloads and parsed content.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output.",
    )
    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    try:
        intent = parse_agent_request(args.request)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.style:
        intent.style = args.style
    if args.images is not None:
        intent.images = max(0, args.images)
    if args.max_length is not None:
        intent.max_length = max(400, args.max_length)
    if args.output:
        intent.output = args.output

    if not intent.output and not intent.preview:
        intent.output = str(_default_output_path(intent.source))

    converter = PaperConverter(
        style=intent.style,
        max_images=intent.images,
        max_length=intent.max_length,
        cache_dir=args.cache_dir,
    )

    if args.verbose:
        print(f"Agent source: {intent.source}")
        print(f"Style: {intent.style}")
        print(f"Max images: {intent.images}")
        print(f"Max length: {intent.max_length}")
        print(f"Output: {intent.output or '(preview)'}")
        print(f"Cache dir: {args.cache_dir}")

    try:
        if _looks_like_url_or_arxiv_id(intent.source):
            article = converter.convert(intent.source, output_path=intent.output)
        else:
            article = converter.convert_pdf(intent.source, output_path=intent.output)
    except Exception as exc:
        if args.verbose:
            raise
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if intent.preview:
        print(article.to_markdown())
        return

    print(f"Markdown generated: {intent.output}")
    print(f"Word count: {article.word_count}")
    print(f"Images selected: {len(article.images)}")
    print(f"Style used: {intent.style}")


def parse_agent_request(text: str) -> AgentIntent:
    request = (text or "").strip()
    if not request:
        raise ValueError("Request cannot be empty.")

    source = _extract_source(request)
    if not source:
        raise ValueError("No Arxiv URL/ID or PDF path found in request.")

    style = _extract_style(request) or "academic-tech"
    images = _extract_images(request) or 5
    max_length = _extract_max_length(request) or 5000
    output = _extract_output_path(request)
    preview = _extract_preview_flag(request)

    return AgentIntent(
        source=source,
        style=style,
        images=max(0, images),
        max_length=max(400, max_length),
        output=output,
        preview=preview,
    )


def _extract_source(text: str) -> Optional[str]:
    direct = text.strip().strip("`\"'")
    if direct.lower().endswith(".pdf"):
        return direct
    if _looks_like_url_or_arxiv_id(direct):
        return direct

    url_pattern = re.compile(
        r"https?://arxiv\.org/(abs|pdf)/[A-Za-z0-9.\-_/]+(?:v\d+)?(?:\.pdf)?",
        flags=re.IGNORECASE,
    )
    url_match = url_pattern.search(text)
    if url_match:
        return url_match.group(0)

    pdf_pattern = re.compile(r"([^\s'\"`]+\.pdf)\b", re.IGNORECASE)
    pdf_match = pdf_pattern.search(text)
    if pdf_match:
        return pdf_match.group(1)

    id_pattern = re.compile(r"\b(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?\b", re.IGNORECASE)
    id_match = id_pattern.search(text)
    if id_match:
        return id_match.group(0)

    return None


def _extract_style(text: str) -> Optional[str]:
    lowered = text.lower()

    explicit = re.search(
        r"\b(academic-science|academic-tech|academic-trend|academic-applied)\b",
        lowered,
    )
    if explicit:
        candidate = explicit.group(1)
        if candidate in STYLE_CHOICES:
            return candidate

    hints = [
        ("academic-science", ("science", "scientific", "理论", "科学", "严谨")),
        ("academic-tech", ("tech", "technical", "工程", "技术", "开发者", "实战", "落地")),
        ("academic-trend", ("trend", "future", "前沿", "趋势", "创新", "未来")),
        ("academic-applied", ("applied", "application", "应用", "行业", "商业")),
    ]
    for style, tokens in hints:
        for token in tokens:
            if token in lowered or token in text:
                return style
    return None


def _extract_images(text: str) -> Optional[int]:
    patterns = [
        r"--images\s+(\d+)",
        r"(\d+)\s*(?:images?|张图|图片)",
        r"(?:图|图片)\s*(\d+)\s*张",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_max_length(text: str) -> Optional[int]:
    patterns = [
        r"--max-length\s+(\d+)",
        r"(?:under|within|不超过|控制在)\s*(\d{3,5})\s*(?:words?|字)?",
        r"(\d{3,5})\s*(?:words?|字)\s*(?:以内|左右|以内输出)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_output_path(text: str) -> Optional[str]:
    patterns = [
        r"--output\s+([^\s]+\.md)\b",
        r"(?:output|输出(?:到|为)?)\s*[:：]?\s*([^\s]+\.md)\b",
        r"\b([^\s]+\.md)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_preview_flag(text: str) -> bool:
    lowered = text.lower()
    return ("--preview" in lowered) or ("preview" in lowered) or ("预览" in text)


def _looks_like_url_or_arxiv_id(value: str) -> bool:
    text = value.strip()
    if text.startswith(("http://", "https://")):
        return True
    arxiv_pattern = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?$", re.IGNORECASE)
    return bool(arxiv_pattern.match(text))


def _default_output_path(source: str) -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = _derive_output_stem(source)
    return output_dir / f"{stem}.md"


def _derive_output_stem(source: str) -> str:
    text = source.strip()
    if _looks_like_url_or_arxiv_id(text):
        try:
            arxiv_id = PaperFetcher.parse_arxiv_url(text)
            return arxiv_id.replace("/", "_")
        except ValueError:
            pass

    path = Path(text)
    if path.suffix.lower() == ".pdf":
        return path.stem

    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")
    return safe or "article"


if __name__ == "__main__":
    main()
