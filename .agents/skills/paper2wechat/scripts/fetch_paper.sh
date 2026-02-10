#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "${1:-}" == "" ]]; then
  cat <<'EOF'
Usage:
  bash .agents/skills/paper2wechat/scripts/fetch_paper.sh <url_or_id_or_pdf> [cache_dir]
  # Uses standalone parser from this skill package.
  # Artifacts are archived by paper: <cache_dir>/<paper_id>/{downloads,sources,parsed,images}

Examples:
  bash .agents/skills/paper2wechat/scripts/fetch_paper.sh https://arxiv.org/abs/2301.00000
  bash .agents/skills/paper2wechat/scripts/fetch_paper.sh 2301.00000 .paper2wechat
  bash .agents/skills/paper2wechat/scripts/fetch_paper.sh ./paper.pdf .paper2wechat
EOF
  exit 0
fi

INPUT="$1"
CACHE_DIR="${2:-.paper2wechat}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/parse_paper.py" "$INPUT" --cache-dir "$CACHE_DIR" --verbose
