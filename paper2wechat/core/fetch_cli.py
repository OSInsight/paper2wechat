"""
CLI helper to fetch/parse paper content without generating article prose.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .paper_fetcher import PaperFetcher


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and parse Arxiv paper/PDF into local cache."
    )
    parser.add_argument(
        "input",
        help="Arxiv URL/ID or local PDF path.",
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

    fetcher = PaperFetcher(cache_dir=args.cache_dir)
    source = args.input.strip()

    try:
        if _looks_like_url_or_arxiv_id(source):
            paper = _fetch_with_cache_fallback(fetcher, source)
            cache_key = paper.arxiv_id or _derive_cache_key_from_source(source)
        else:
            paper = fetcher.fetch_from_pdf(source)
            cache_key = Path(source).stem
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    safe_key = cache_key.replace("/", "_")
    parsed_path = Path(args.cache_dir) / "parsed" / f"{safe_key}.json"
    images_dir = Path(args.cache_dir) / "images" / safe_key

    if args.verbose:
        print(f"Source: {source}")
        print(f"Title: {paper.title}")
        print(f"Sections: {len(paper.sections)}")
        print(f"Images extracted: {len(paper.images)}")

    print(f"Parsed cache: {parsed_path}")
    print(f"Images dir: {images_dir}")


def _fetch_with_cache_fallback(fetcher: PaperFetcher, source: str):
    try:
        return fetcher.fetch_from_url(source)
    except Exception as original_error:
        arxiv_id = PaperFetcher.parse_arxiv_url(source)
        safe_id = arxiv_id.replace("/", "_")
        local_pdf = fetcher.download_dir / f"{safe_id}.pdf"
        if not local_pdf.exists() or local_pdf.stat().st_size <= 0:
            raise original_error
        return fetcher.fetch_from_pdf(
            str(local_pdf),
            arxiv_id=arxiv_id,
            source_url=source,
        )


def _looks_like_url_or_arxiv_id(value: str) -> bool:
    text = value.strip()
    if text.startswith(("http://", "https://")):
        return True
    arxiv_pattern = re.compile(r"^(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?$", re.IGNORECASE)
    return bool(arxiv_pattern.match(text))


def _derive_cache_key_from_source(value: str) -> str:
    try:
        return PaperFetcher.parse_arxiv_url(value)
    except ValueError:
        path = Path(value)
        if path.suffix.lower() == ".pdf":
            return path.stem
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")
        return safe or "paper"


if __name__ == "__main__":
    main()
