#!/usr/bin/env python3
"""
derive_plan.py - P2-5 SSOT helper

从 author/<deck>_content.md 自动派生 builder/<deck>_plan.json,使 content.md
成为单一真实源 (SSOT)。builder Step 0.5 会用 derived_from_sha256 字段验证
plan 是否跟当前 content.md 同步。

Usage:
  # 默认输出到 <deck>/builder/<basename>_plan.json
  python3 scripts/derive_plan.py <content.md>

  # 显式指定输出
  python3 scripts/derive_plan.py <content.md> --output <plan.json>

  # dry-run(只打印 JSON 到 stdout)
  python3 scripts/derive_plan.py <content.md> --dry-run

Parsing rules:
- frontmatter (---...---) 解析:取 theme / output / footer_meta
- `## N. <action title>` 章节 → slide(layout 来自下一行 `<!-- layout: X -->` 注释)
- `<!-- pattern: X -->` 注释 → slide.pattern_id 字段
- 章节正文 bullet (`- ...`) → slide.items 或 slide.bullets
- 章节正文 image (`![alt](path)`) → slide.image_path
- 表格 (`| ... | ... |`) → slide.table_rows

Output schema (与 build.py 兼容):
  {
    "theme": "tech_blue",
    "output": "./deck_v1.pptx",
    "footer_meta": {classification, project, version},
    "derived_from": "<content.md path>",
    "derived_from_sha256": "<hash>",
    "derived_at": "<ISO timestamp>",
    "slides": [
      {"layout": "cover", "title": "...", ...},
      {"layout": "<X>", "title": "...", "pattern_id": "vp:...", ...},
      ...
    ]
  }

注意:这是 best-effort derive(LLM 仍然可能需要手动调整生成的 plan)。derive_plan.py 不调 LLM。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---- regex ----
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
CHAPTER_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
SPECIAL_HEADING_RE = re.compile(r"^##\s+\[([a-z_]+)\]\s*(.*?)\s*$", re.M)
LAYOUT_DIRECTIVE_RE = re.compile(r"<!--\s*layout:\s*([a-z_]+)\s*-->")
PATTERN_DIRECTIVE_RE = re.compile(r"<!--\s*pattern:\s*([^>]+?)\s*-->")
BULLET_RE = re.compile(r"^[-*]\s+(?:\*\*(.+?)\*\*[\s:：]*)?(.+?)\s*$", re.M)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$", re.M)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_yaml_simple(yaml_text: str) -> dict[str, Any]:
    """
    Very minimal yaml parser for frontmatter (no nested dicts, no anchors).
    Returns flat dict of top-level keys; values are raw strings (caller may parse).
    Supports nested 1-level via indent (for footer_meta block).
    """
    result: dict[str, Any] = {}
    lines = yaml_text.split("\n")
    current_key = None
    current_nested: dict[str, str] | None = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Top-level key:
        m_top = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if m_top and not line.startswith(" ") and not line.startswith("\t"):
            k, v = m_top.group(1), m_top.group(2).strip()
            current_key = k
            current_nested = None
            if v:
                # Inline value
                result[k] = _coerce(v)
            else:
                # Block follows (could be nested dict or list)
                result[k] = {}
                current_nested = result[k]
            continue
        # Nested key (indented)
        m_nest = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if m_nest and current_nested is not None and isinstance(current_nested, dict):
            k, v = m_nest.group(1), m_nest.group(2).strip()
            current_nested[k] = _coerce(v) if v else ""
            continue
    return result


def _coerce(v: str) -> Any:
    """Coerce yaml scalar."""
    v = v.strip().strip('"').strip("'")
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() in ("null", "~", ""):
        return None
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def parse_chapters(text: str) -> list[dict[str, Any]]:
    """
    Parse `## N. <title>` and `## [special]` headings as slides.
    Returns list of {chapter_idx, title, layout, pattern_id, body_text, kind: "content" | "special"}.
    """
    # Strip frontmatter
    fm_m = FRONTMATTER_RE.match(text)
    body_start = fm_m.end() if fm_m else 0
    body = text[body_start:]

    # Collect all `## ...` heading matches (both numbered and [special])
    all_matches = []
    for m in CHAPTER_HEADING_RE.finditer(body):
        all_matches.append((m.start(), m.end(), "content", m.group(1), m.group(2)))
    for m in SPECIAL_HEADING_RE.finditer(body):
        all_matches.append((m.start(), m.end(), "special", m.group(1), m.group(2)))
    all_matches.sort(key=lambda t: t[0])

    slides = []
    for i, (start, end, kind, num_or_name, title) in enumerate(all_matches):
        next_start = all_matches[i + 1][0] if i + 1 < len(all_matches) else len(body)
        section_text = body[end:next_start]

        # Find layout directive in first few lines (must be on a line by itself or after heading)
        layout_m = LAYOUT_DIRECTIVE_RE.search(section_text)
        pattern_m = PATTERN_DIRECTIVE_RE.search(section_text)

        slide: dict[str, Any] = {
            "kind": kind,
            "title": title.strip(),
            "body": section_text,
        }
        if kind == "content":
            slide["chapter_idx"] = int(num_or_name)
        else:
            slide["special"] = num_or_name  # e.g. "cover", "toc", "closing", "section_divider"

        if layout_m:
            slide["layout"] = layout_m.group(1)
        elif kind == "special":
            slide["layout"] = num_or_name
        else:
            slide["layout"] = None  # caller may flag as missing_layout_directive

        if pattern_m:
            slide["pattern_id"] = pattern_m.group(1).strip()

        slides.append(slide)

    return slides


def extract_bullets(section_text: str) -> list[dict[str, str]]:
    """Extract `- **Title**: body` or `- body` bullets."""
    items = []
    for m in BULLET_RE.finditer(section_text):
        title = m.group(1) or ""
        body = m.group(2) or ""
        if title:
            items.append({"title": title.strip(), "body": body.strip()})
        else:
            items.append({"body": body.strip()})
    return items


def extract_image_path(section_text: str) -> str | None:
    m = IMAGE_RE.search(section_text)
    if m:
        return m.group(2).strip()
    return None


def derive_slide_fields(slide: dict[str, Any]) -> dict[str, Any]:
    """
    Convert parsed slide into deck_plan slide entry, by layout.
    Layouts: cover / toc / section_divider / summary / closing / cards / bullet_list
             compare / pic_text / table / single_focus / quote / data / etc.
    """
    layout = slide.get("layout")
    body = slide.get("body", "")
    title = slide.get("title", "")

    out: dict[str, Any] = {"layout": layout, "title": title}
    if "pattern_id" in slide:
        out["pattern_id"] = slide["pattern_id"]

    bullets = extract_bullets(body)
    image_path = extract_image_path(body)

    if layout == "cover":
        # Try to extract subtitle: first non-bullet, non-image, non-blank line
        first_line = next(
            (
                ln.strip() for ln in body.split("\n")
                if ln.strip() and not ln.lstrip().startswith("<!--")
                and not ln.lstrip().startswith("-") and not ln.lstrip().startswith("!")
            ),
            "",
        )
        if first_line:
            out["subtitle"] = first_line
    elif layout == "toc":
        out["sections"] = [b["body"] for b in bullets if "body" in b]
    elif layout == "section_divider":
        # special: kind="special", title may be "1 · 背景"
        out["title"] = title
    elif layout in ("bullet_list", "summary"):
        items = [b["body"] for b in bullets if "body" in b]
        if layout == "summary":
            out["conclusions"] = items
        else:
            out["items"] = items
    elif layout in ("cards", "compare"):
        out["cards" if layout == "cards" else "items"] = [
            {"title": b.get("title", ""), "body": b.get("body", "")}
            for b in bullets
        ]
    elif layout in ("pic_text", "single_focus"):
        if image_path:
            out["image_path"] = image_path
        if bullets:
            out["bullets"] = [b["body"] for b in bullets if "body" in b]
        # subtitle / body line
        first_line = next(
            (ln.strip() for ln in body.split("\n")
             if ln.strip() and not ln.lstrip().startswith(("<!--", "-", "!"))),
            "",
        )
        if first_line:
            out["body"] = first_line
    elif layout == "closing":
        first_line = next(
            (ln.strip() for ln in body.split("\n")
             if ln.strip() and not ln.lstrip().startswith(("<!--", "-", "!"))),
            "",
        )
        if first_line:
            out["subtitle"] = first_line
    else:
        # Default: try generic bullets + image
        if bullets:
            out["bullets"] = bullets
        if image_path:
            out["image_path"] = image_path

    return out


def derive_plan(content_md_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    text = content_md_path.read_text(encoding="utf-8")

    # Parse frontmatter
    fm_m = FRONTMATTER_RE.match(text)
    frontmatter: dict[str, Any] = {}
    if fm_m:
        frontmatter = parse_yaml_simple(fm_m.group(1))

    # Parse chapters
    raw_slides = parse_chapters(text)
    slides = [derive_slide_fields(s) for s in raw_slides]

    # Build plan
    plan: dict[str, Any] = {
        "theme": frontmatter.get("theme", "tech_blue"),
        "output": str(frontmatter.get("output") or (
            output_path.parent.parent / "builder" / f"{content_md_path.stem.replace('_content','')}.pptx"
            if output_path else "./deck.pptx"
        )),
        "derived_from": str(content_md_path),
        "derived_from_sha256": sha256_file(content_md_path),
        "derived_at": datetime.now(timezone.utc).isoformat(),
        "slides": slides,
    }
    if isinstance(frontmatter.get("footer_meta"), dict):
        plan["footer_meta"] = frontmatter["footer_meta"]

    # Flag missing layout directives
    missing = [s for s in raw_slides if s["kind"] == "content" and not s.get("layout")]
    if missing:
        plan["_warnings_missing_layout"] = [s["title"] for s in missing]

    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive deck_plan.json from author/content.md (P2-5 SSOT helper).",
    )
    parser.add_argument(
        "content_md",
        type=Path,
        help="Path to <deck>/author/<deck_v1>_content.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <deck>/builder/<basename>_plan.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON to stdout, do not write file.",
    )
    args = parser.parse_args()

    if not args.content_md.exists():
        print(f"error: content.md not found: {args.content_md}", file=sys.stderr)
        return 1

    output_path = args.output
    if not output_path and not args.dry_run:
        # Default: <deck>/builder/<basename_without_content>_plan.json
        deck_dir = args.content_md.parent.parent
        basename = args.content_md.stem.replace("_content", "")
        output_path = deck_dir / "builder" / f"{basename}_plan.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

    plan = derive_plan(args.content_md, output_path)
    plan_json = json.dumps(plan, ensure_ascii=False, indent=2)

    if args.dry_run:
        print(plan_json)
    else:
        output_path.write_text(plan_json + "\n", encoding="utf-8")
        print(f"derived plan written: {output_path}", file=sys.stderr)
        if plan.get("_warnings_missing_layout"):
            print(
                f"⚠️  {len(plan['_warnings_missing_layout'])} chapter(s) missing "
                f"`<!-- layout: X -->` directive: {plan['_warnings_missing_layout']}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
