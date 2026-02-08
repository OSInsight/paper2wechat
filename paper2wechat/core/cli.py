"""
CLI interface for paper2wechat
"""
import argparse
import os
import re
import sys
from pathlib import Path

from .converter import PaperConverter
from .paper_fetcher import PaperFetcher


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Convert Arxiv papers to WeChat articles"
    )
    
    parser.add_argument(
        "input",
        help="Arxiv URL or PDF file path"
    )
    
    parser.add_argument(
        "--style",
        choices=["academic-science", "academic-tech", "academic-trend", "academic-applied"],
        default="academic-tech",
        help="Conversion style"
    )
    
    parser.add_argument(
        "--images",
        type=int,
        default=5,
        help="Maximum number of images"
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=5000,
        help="Maximum output length in words"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output markdown file path"
    )
    
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview output instead of saving"
    )
    
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Upload to WeChat as draft"
    )
    
    parser.add_argument(
        "--cover",
        help="Cover image path"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--cache-dir",
        default=".paper2wechat",
        help="Cache directory for downloads and parsed content"
    )

    parser.add_argument(
        "--allow-rule-based",
        action="store_true",
        help="Allow rule-based fallback rewriting when no LLM API key is configured",
    )
    
    return parser


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.allow_rule_based and not _has_llm_api_key():
        print(
            "Error: no LLM API key found for CLI mode.\n"
            "Set OPENROUTER_API_KEY (recommended) or ANTHROPIC_API_KEY.\n"
            "If you still want low-quality rule-based fallback, add --allow-rule-based.\n"
            "For chat-agent workflow without API key, use skill agent flow instead of raw CLI.",
            file=sys.stderr,
        )
        sys.exit(1)

    converter = PaperConverter(
        style=args.style,
        max_images=args.images,
        max_length=args.max_length,
        cache_dir=args.cache_dir,
    )

    try:
        is_url = _looks_like_url_or_arxiv_id(args.input)
        output_path = args.output

        if not args.preview and not output_path:
            output_path = str(_default_output_path(args.input))

        if args.verbose:
            print(f"Converting: {args.input}")
            print(f"Style: {args.style}")
            print(f"Max images: {args.images}")
            print(f"Max length: {args.max_length}")
            print(f"Cache dir: {args.cache_dir}")

        if is_url:
            article = converter.convert(args.input, output_path=output_path)
        else:
            article = converter.convert_pdf(args.input, output_path=output_path)

        if args.preview:
            print(article.to_markdown())
        else:
            print(f"Markdown generated: {output_path}")
            print(f"Word count: {article.word_count}")
            print(f"Images selected: {len(article.images)}")

        if args.draft:
            result = converter.upload_to_wechat(article, draft=True)
            if result.get("status") == "success":
                print("Uploaded to WeChat draft successfully.")
            else:
                print(
                    f"WeChat upload failed: {result.get('message') or result.get('stderr')}",
                    file=sys.stderr,
                )
                sys.exit(1)
    except Exception as exc:
        if args.verbose:
            raise
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


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


def _has_llm_api_key() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


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
