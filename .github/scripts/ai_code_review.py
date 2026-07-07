#!/usr/bin/env python3
"""Post an AI code review comment on a GitHub PR.

Usage:
    python ai_code_review.py <diff_file> <pr_number>

Required env vars:
    ANTHROPIC_API_KEY   — Claude API key
    GH_TOKEN            — GitHub token with pull-requests: write scope
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

REVIEW_PROMPT = textwrap.dedent("""
    You are a senior engineer reviewing a pull request for TradingAgents — a Python + TypeScript
    application that runs multi-agent LLM pipelines for financial analysis and serves them via
    a FastAPI backend and React web dashboard.

    Review the diff for:

    1. **Security** — injection risks, credential exposure, path traversal, input validation gaps,
       unsafe subprocess usage, open CORS, missing auth checks.

    2. **Cost** — unnecessary or redundant LLM API calls, missing caching, choosing an expensive
       model (`deep_think_llm`) where a cheaper one (`quick_think_llm`) would suffice, unbounded
       loops that call external APIs, SSE streams that never terminate.

    3. **Correctness** — race conditions in the asyncio/threading bridge (`call_soon_threadsafe`),
       missing error handling at system boundaries (HTTP, file I/O, LLM calls), off-by-one errors
       in debate round counting, state fields not cleared between graph phases.

    4. **Code quality** — clarity, maintainability, Python/TypeScript idioms; do NOT flag style
       issues already caught by ruff (line length, import order, etc.).

    Format your response as:
    - **Summary** (2 sentences max)
    - **Findings** — bullet list with severity (HIGH / MED / LOW) and `file:line` where known
    - If there are no significant issues, say so clearly and briefly.

    Be direct and specific. Skip generic praise.
""").strip()

MAX_DIFF_CHARS = 60_000


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: ai_code_review.py <diff_file> <pr_number>", file=sys.stderr)
        sys.exit(1)

    diff_path, pr_number = sys.argv[1], sys.argv[2]

    try:
        diff = open(diff_path).read().strip()
    except FileNotFoundError:
        print(f"Diff file not found: {diff_path}", file=sys.stderr)
        sys.exit(1)

    if not diff:
        print("Empty diff — nothing to review.")
        return

    if len(diff) > MAX_DIFF_CHARS:
        diff = (
            diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated — only the first 60K characters reviewed]"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — skipping AI review.", file=sys.stderr)
        sys.exit(0)

    import anthropic  # installed via langchain-anthropic transitive dep

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"{REVIEW_PROMPT}\n\n```diff\n{diff}\n```",
            }
        ],
    )

    review_text = message.content[0].text
    body = (
        "## AI Code Review\n\n"
        f"{review_text}\n\n"
        "*Reviewed by Claude claude-sonnet-4-6 · [TradingAgents CI](.github/workflows/ci.yml)*"
    )

    subprocess.run(
        ["gh", "pr", "comment", pr_number, "--body", body],
        check=True,
    )
    print(f"Posted review on PR #{pr_number}.")


if __name__ == "__main__":
    main()
