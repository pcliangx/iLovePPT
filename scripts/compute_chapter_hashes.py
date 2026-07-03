#!/usr/bin/env python3
"""
compute_chapter_hashes.py - P2-4 hot-reload helper

读 content.md,按 `## N. <title>` heading 分章,对每章 body 算 sha256;
可选写入 state.json.chapter_hashes 字段(供 critic/builder/audience hot-reload 用)。

Usage:
  # 仅打印 JSON(stdout)
  python3 compute_chapter_hashes.py <content.md>

  # 写入 state.json
  python3 compute_chapter_hashes.py <content.md> --state-json <state.json>

  # 既打印又写入
  python3 compute_chapter_hashes.py <content.md> --state-json <state.json> --print

Output JSON schema:
  {"1": "sha256:abc...", "2": "sha256:def...", ...}

state.json 写入会:
- 写 chapter_hashes 字段(覆盖旧值)
- 写 last_hash_update 字段(ISO 时间戳)
- 不动其他字段
- 文件不存在则报错(state.json 应该由 author / brainstorm 初始化)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CHAPTER_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.M)


def parse_chapters(content_md_text: str) -> dict[str, str]:
    """
    Parse `## N. <title>` headings, return {chapter_num_str: chapter_body}.
    Chapter body = text from heading line (inclusive) to next `## ` heading (exclusive).
    Frontmatter (--- ... ---) at top is excluded.
    """
    text = content_md_text

    # Strip frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]

    # Find all chapter headings with positions
    matches = list(CHAPTER_HEADING_RE.finditer(text))

    chapters: dict[str, str] = {}
    for i, m in enumerate(matches):
        chap_num = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].rstrip() + "\n"
        chapters[chap_num] = body

    return chapters


def hash_chapters(chapters: dict[str, str]) -> dict[str, str]:
    """sha256 of each chapter body. Returns {chap_num: 'sha256:<hex>'}."""
    return {
        num: f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
        for num, body in chapters.items()
    }


def write_state_json(state_path: Path, hashes: dict[str, str]) -> None:
    """Update state.json in place: write chapter_hashes + last_hash_update."""
    if not state_path.exists():
        raise FileNotFoundError(
            f"state.json not found: {state_path}\n"
            "state.json should be initialized by author / brainstorm before "
            "compute_chapter_hashes.py runs."
        )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["chapter_hashes"] = hashes
    state["last_hash_update"] = datetime.now(timezone.utc).isoformat()

    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute per-chapter SHA-256 hashes from content.md "
                    "(P2-4 hot-reload helper).",
    )
    parser.add_argument(
        "content_md",
        type=Path,
        help="Path to content.md (e.g. <deck>/author/deck_v1_content.md)",
    )
    parser.add_argument(
        "--state-json",
        type=Path,
        default=None,
        help="Optional path to state.json — write chapter_hashes + last_hash_update.",
    )
    parser.add_argument(
        "--print",
        dest="print_json",
        action="store_true",
        help="Also print hashes to stdout (default: only print if --state-json absent).",
    )
    args = parser.parse_args()

    if not args.content_md.exists():
        print(f"error: content.md not found: {args.content_md}", file=sys.stderr)
        return 1

    text = args.content_md.read_text(encoding="utf-8")
    chapters = parse_chapters(text)
    if not chapters:
        print(
            f"warning: no `## N. <title>` chapters found in {args.content_md}",
            file=sys.stderr,
        )

    hashes = hash_chapters(chapters)

    # Print to stdout unless --state-json and not --print
    if args.state_json is None or args.print_json:
        print(json.dumps(hashes, ensure_ascii=False, indent=2))

    if args.state_json is not None:
        try:
            write_state_json(args.state_json, hashes)
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
