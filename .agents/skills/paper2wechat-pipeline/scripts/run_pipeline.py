#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_cmd(command: list[str], cwd: Path) -> str:
    process = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    output = (process.stdout or "") + (process.stderr or "")
    if process.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}\n{output}")
    return output


def parse_paper_id_from_fetch_output(output: str) -> Optional[str]:
    match = re.search(r"Parsed cache:\s+.*?/([^/]+)/parsed/[^/]+\\.json", output)
    if match:
        return match.group(1)
    return None


def normalize_cache_root(cache_root: str, workspace_root: Path) -> Path:
    cache_path = Path(cache_root)
    if not cache_path.is_absolute():
        cache_path = workspace_root / cache_path
    return cache_path.resolve()


def detect_paper_id_from_input(paper_input: str) -> Optional[str]:
    arxiv_match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", paper_input)
    if arxiv_match:
        return arxiv_match.group(1)
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Orchestrate paper2wechat full pipeline"
    )
    parser.add_argument("--paper", required=True, help="arXiv URL/ID or local PDF path")
    parser.add_argument(
        "--cache-root", default=".paper2wechat", help="Cache root directory"
    )
    parser.add_argument(
        "--article-md",
        default=None,
        help="Article markdown path; default .paper2wechat/<paper_id>/outputs/<paper_id>.md",
    )

    parser.add_argument(
        "--theme", default="ai-insight", help="Theme for wechat-publisher"
    )
    parser.add_argument(
        "--upload-images", action="store_true", help="Upload local images to WeChat"
    )
    parser.add_argument(
        "--create-draft", action="store_true", help="Create WeChat draft"
    )
    parser.add_argument(
        "--auto-thumb",
        action="store_true",
        help="Auto pick/upload cover image for draft",
    )
    parser.add_argument(
        "--keep-h1-in-draft", action="store_true", help="Keep first H1 in draft body"
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace_root = Path.cwd().resolve()
    cache_root = normalize_cache_root(args.cache_root, workspace_root)

    fetch_script = workspace_root / ".agents/skills/paper2wechat/scripts/fetch_paper.sh"
    style_script = (
        workspace_root / ".agents/skills/paper2wechat/scripts/detect_style.py"
    )
    publish_script = (
        workspace_root / ".agents/skills/wechat-publisher/scripts/publish_wechat.py"
    )

    if (
        not fetch_script.exists()
        or not style_script.exists()
        or not publish_script.exists()
    ):
        print("[error] Required skill scripts are missing.", file=sys.stderr)
        return 1

    print(f"[pipeline] parse paper: {args.paper}")
    fetch_output = run_cmd(
        ["bash", str(fetch_script), args.paper, str(cache_root)], cwd=workspace_root
    )
    print(fetch_output.strip())

    paper_id = parse_paper_id_from_fetch_output(
        fetch_output
    ) or detect_paper_id_from_input(args.paper)
    if not paper_id:
        print(
            "[error] Cannot resolve paper_id from parser output. Please inspect fetch logs.",
            file=sys.stderr,
        )
        return 1

    parsed_json = cache_root / paper_id / "parsed" / f"{paper_id}.json"
    if parsed_json.exists():
        print(f"[pipeline] style evidence: {parsed_json}")
        style_output = run_cmd(
            [sys.executable, str(style_script), str(parsed_json), "--json"],
            cwd=workspace_root,
        )
        print(style_output.strip())

    article_md = (
        Path(args.article_md).expanduser().resolve()
        if args.article_md
        else (cache_root / paper_id / "outputs" / f"{paper_id}.md")
    )
    if not article_md.exists():
        print("[pipeline] article markdown missing, stop before publish step.")
        print(f"[next] write article markdown at: {article_md}")
        print("[next] then re-run this command with same args (or pass --article-md).")
        return 0

    publish_command = [
        sys.executable,
        str(publish_script),
        "--input-md",
        str(article_md),
        "--theme",
        args.theme,
    ]
    if args.upload_images:
        publish_command.append("--upload-images")
    if args.create_draft:
        publish_command.append("--create-draft")
    if args.auto_thumb:
        publish_command.append("--auto-thumb")
    if args.keep_h1_in_draft:
        publish_command.append("--keep-h1-in-draft")

    print("[pipeline] publish via wechat-publisher")
    publish_output = run_cmd(publish_command, cwd=workspace_root)
    print(publish_output.strip())

    print("[pipeline] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
