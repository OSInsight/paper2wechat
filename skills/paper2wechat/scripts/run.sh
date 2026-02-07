#!/bin/bash

# paper2wechat CLI wrapper
# This script handles the command-line interface

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Python command: prefer current environment's `python`.
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON=python
  else
    PYTHON=python3
  fi
fi

COMMAND="${1:-}"

if [ -n "$COMMAND" ]; then
  shift
fi

case "$COMMAND" in
  convert|markdown)
    exec "$PYTHON" -m paper2wechat.core.cli "$@"
    ;;
  publish)
    exec "$PYTHON" -m paper2wechat.core.cli "$@" --draft
    ;;
  styles)
    cat <<'EOF'
academic-science
academic-tech
academic-trend
academic-applied
EOF
    ;;
  fetch|adapt)
    # For now these sub-commands map to conversion flow.
    exec "$PYTHON" -m paper2wechat.core.cli "$@"
    ;;
  "")
    exec "$PYTHON" -m paper2wechat.core.cli --help
    ;;
  *)
    # Backward compatible mode: first arg is actually the input path/url.
    exec "$PYTHON" -m paper2wechat.core.cli "$COMMAND" "$@"
    ;;
esac
