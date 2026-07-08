#!/usr/bin/env bash
# PostToolUse hook: lint files Claude just edited. Non-blocking on non-code files.
set -u
INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$FILE" ] && exit 0
case "$FILE" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff check --fix "$FILE" >&2 || exit 2   # exit 2 feeds findings back to Claude
    fi ;;
esac
exit 0
