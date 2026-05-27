#!/usr/bin/env python3
"""deck_diff.py · P3-13 跨 deck content.md 语义 diff.

`git diff content.md` 只看到 line-level 变化(哪一行字改了)· 看不到结构变化:
哪页删了 / 加了 / 重排了 / 换了 layout 或 pattern · 也分不清是 typo 修订
还是章节大改。本脚本走"章节对齐 + 语义分类"路线 · 输出 4 类变化:

  - **added**    : v2 出现 v1 没有的章节
  - **removed**  : v1 出现 v2 没有的章节
  - **modified** : 章节存在两边但 layout / pattern / 正文哈希变了(fuzzy title match)
  - **reordered**: 章节都在但顺序变了

Usage:
    scripts/deck_diff.py <v1.md> <v2.md>
    scripts/deck_diff.py decks/X/author/deck_v1_content.md decks/X/author/deck_v2_content.md
    scripts/deck_diff.py v1.md v2.md --format json
    scripts/deck_diff.py v1.md v2.md --output diff.md
    scripts/deck_diff.py v1.md v2.md --include-text-diff
    scripts/deck_diff.py v1.md v2.md --no-color           # 关闭终端着色
    scripts/deck_diff.py v1.md v2.md --threshold 75       # 调 fuzzy 阈值(默认 80)

依赖:
- stdlib(re / argparse / json / hashlib / difflib)· **零外部依赖**
- 可选 rapidfuzz(若装 · 优先用 · 跟 scripts/derive_plan.py 风格一致;
  没装 fallback difflib.SequenceMatcher · 两者对纯字符串 ratio 等价)

不调 LLM · 不写 deck artefact · 纯报告。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any, Optional

# ------------------------- regex(跟 scripts/derive_plan.py 对齐) ------------------------- #

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
CHAPTER_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
SPECIAL_HEADING_RE = re.compile(r"^##\s+\[([a-z_]+)\]\s*(.*?)\s*$", re.M)
LAYOUT_DIRECTIVE_RE = re.compile(r"<!--\s*layout:\s*([a-z_]+)\s*-->")
PATTERN_DIRECTIVE_RE = re.compile(r"<!--\s*pattern:\s*([^>]+?)\s*-->")


# ------------------------- fuzzy fallback ------------------------- #

def _fuzz_ratio(a: str, b: str) -> float:
    """Return 0-100 fuzz ratio. 取 max(plain ratio, partial ratio) · 让 "数据分析" ↔
    "数据分析(改)" 这类"加后缀"的修订也能匹上(纯 ratio = 73,partial = 100,
    阈值 80 时纯 ratio 会判 removed+added · 误判)。

    Prefer rapidfuzz when present;fallback difflib.SequenceMatcher · 纯 stdlib · partial
    用最长公共子串近似(`find_longest_match`)."""
    try:
        from rapidfuzz import fuzz  # type: ignore

        return max(float(fuzz.ratio(a, b)), float(fuzz.partial_ratio(a, b)))
    except ImportError:
        plain = SequenceMatcher(None, a, b).ratio() * 100.0
        # partial-ratio approximation: 最长公共子串占短串的比例 × 100
        if not a or not b:
            return plain
        short, long_ = (a, b) if len(a) <= len(b) else (b, a)
        m = SequenceMatcher(None, short, long_).find_longest_match(0, len(short), 0, len(long_))
        partial = (m.size / len(short)) * 100.0 if short else 0.0
        return max(plain, partial)


# ------------------------- data model ------------------------- #


@dataclass
class Chapter:
    """单章 · v1 / v2 共用."""

    idx: int  # 出现顺序(1-based)· 对 numbered = chapter num · 对 special = 0/sort-key
    kind: str  # "content" | "special"
    title: str
    layout: Optional[str]
    pattern_id: Optional[str]
    body: str  # 原始 section text (heading 之后到下一 heading 之前)
    sha256: str  # sha256 of normalized body
    raw_lines: list[str] = field(default_factory=list)  # for line-level diff
    special: Optional[str] = None  # for kind="special": e.g. "cover", "toc"


@dataclass
class DiffEntry:
    """单条 diff 记录."""

    category: str  # "added" | "removed" | "modified" | "reordered"
    v1_idx: Optional[int]  # v1 出现位置(1-based · None 表 added)
    v2_idx: Optional[int]  # v2 出现位置(None 表 removed)
    v1_title: Optional[str]
    v2_title: Optional[str]
    changes: list[str] = field(default_factory=list)  # ["title", "layout", "pattern", "body", "reorder"]
    details: dict[str, Any] = field(default_factory=dict)  # 具体 from→to
    text_diff: Optional[str] = None  # only when --include-text-diff


@dataclass
class DiffResult:
    v1_path: str
    v2_path: str
    v1_chapter_count: int
    v2_chapter_count: int
    diffs: list[DiffEntry] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


# ------------------------- parse ------------------------- #


def _normalize_body(text: str) -> str:
    """Strip 注释(layout/pattern)+ trailing whitespace · 让 sha256 反映**正文**变化."""
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("<!--") and s.endswith("-->"):
            continue
        lines.append(s)
    # 去 trailing blank
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def parse_chapters(path: Path) -> list[Chapter]:
    """Parse content.md → list[Chapter]. 跟 derive_plan.parse_chapters 同结构."""
    text = path.read_text(encoding="utf-8")

    # Strip frontmatter
    fm_m = FRONTMATTER_RE.match(text)
    body_start = fm_m.end() if fm_m else 0
    body = text[body_start:]

    matches: list[tuple[int, int, str, str, str]] = []
    for m in CHAPTER_HEADING_RE.finditer(body):
        matches.append((m.start(), m.end(), "content", m.group(1), m.group(2)))
    for m in SPECIAL_HEADING_RE.finditer(body):
        matches.append((m.start(), m.end(), "special", m.group(1), m.group(2)))
    matches.sort(key=lambda t: t[0])

    chapters: list[Chapter] = []
    for i, (start, end, kind, num_or_name, title) in enumerate(matches):
        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(body)
        section_text = body[end:next_start]

        layout_m = LAYOUT_DIRECTIVE_RE.search(section_text)
        pattern_m = PATTERN_DIRECTIVE_RE.search(section_text)

        idx = int(num_or_name) if kind == "content" else i + 1
        layout = layout_m.group(1) if layout_m else (num_or_name if kind == "special" else None)
        pattern_id = pattern_m.group(1).strip() if pattern_m else None

        normalized = _normalize_body(section_text)
        sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        chapters.append(
            Chapter(
                idx=idx,
                kind=kind,
                title=title.strip(),
                layout=layout,
                pattern_id=pattern_id,
                body=section_text,
                sha256=sha,
                raw_lines=section_text.splitlines(),
                special=num_or_name if kind == "special" else None,
            ),
        )

    return chapters


# ------------------------- align / diff ------------------------- #


def _match_key(c: Chapter) -> str:
    """Fuzzy match key. Special block 跟 special block 比(用 special name);
    content 跟 content 比(用 title)."""
    if c.kind == "special":
        return f"__special__:{c.special}"
    return c.title


def align_chapters(
    v1: list[Chapter],
    v2: list[Chapter],
    threshold: float = 80.0,
) -> list[tuple[Optional[Chapter], Optional[Chapter]]]:
    """
    Greedy 1:1 fuzzy align. v1 / v2 章节配对:
      - special:严格按 special name 精确匹(`cover` ↔ `cover`)
      - content:rapidfuzz.ratio(title) ≥ threshold 配对(每个 v2 章只能配一次)

    返回 list of (v1_chapter | None, v2_chapter | None) pairs:
      - both present → matched(进一步判 modified / reordered)
      - v1 only → removed
      - v2 only → added

    Note: greedy + best-match · 同一 v1 title 配多 v2 时取最高 ratio · 同 ratio 取出现顺序近的。
    """
    pairs: list[tuple[Optional[Chapter], Optional[Chapter]]] = []
    used_v2: set[int] = set()

    # Phase 1: special 精确匹
    for i1, c1 in enumerate(v1):
        if c1.kind != "special":
            continue
        for i2, c2 in enumerate(v2):
            if i2 in used_v2 or c2.kind != "special":
                continue
            if c1.special == c2.special:
                pairs.append((c1, c2))
                used_v2.add(i2)
                break
        else:
            pairs.append((c1, None))

    # Phase 2: content fuzzy match
    for i1, c1 in enumerate(v1):
        if c1.kind != "content":
            continue
        best_ratio = -1.0
        best_i2: Optional[int] = None
        for i2, c2 in enumerate(v2):
            if i2 in used_v2 or c2.kind != "content":
                continue
            r = _fuzz_ratio(c1.title, c2.title)
            if r >= threshold and r > best_ratio:
                best_ratio = r
                best_i2 = i2
            elif r == best_ratio and best_i2 is not None:
                # 同 ratio · 取 idx 更接近 c1.idx 的(避免乱序时配错)
                if abs(v2[i2].idx - c1.idx) < abs(v2[best_i2].idx - c1.idx):
                    best_i2 = i2
        if best_i2 is not None:
            pairs.append((c1, v2[best_i2]))
            used_v2.add(best_i2)
        else:
            pairs.append((c1, None))

    # Phase 3: v2 中没配上的 → added
    for i2, c2 in enumerate(v2):
        if i2 not in used_v2:
            pairs.append((None, c2))

    return pairs


def detect_reorder(matched: list[tuple[Chapter, Chapter]]) -> bool:
    """matched 对(v1_chap, v2_chap)按 v1 出现顺序 sort 后 · v2 idx 是否单调递增?
    不递增 = 有 reorder."""
    if len(matched) < 2:
        return False
    # 取 content + special 都参与(顺序整体看)· 用 v1 出现顺序 排
    sorted_by_v1 = sorted(matched, key=lambda p: (p[0].kind != "content", p[0].idx))
    v2_order = [p[1].idx for p in sorted_by_v1 if p[1].kind == "content"]
    # 单调递增?
    for i in range(1, len(v2_order)):
        if v2_order[i] <= v2_order[i - 1]:
            return True
    return False


def _line_level_text_diff(c1: Chapter, c2: Chapter) -> str:
    """Unified diff for two chapters' bodies. Truncated to 60 lines max."""
    diff_lines = list(
        unified_diff(
            c1.raw_lines,
            c2.raw_lines,
            fromfile=f"v1:{c1.title}",
            tofile=f"v2:{c2.title}",
            lineterm="",
            n=2,
        ),
    )
    if len(diff_lines) > 60:
        diff_lines = diff_lines[:60] + [f"... (+ {len(diff_lines) - 60} lines truncated)"]
    return "\n".join(diff_lines)


def diff_chapters(
    v1: list[Chapter],
    v2: list[Chapter],
    threshold: float = 80.0,
    include_text_diff: bool = False,
) -> list[DiffEntry]:
    """主 diff 入口 · 输出 [DiffEntry, ...]."""
    pairs = align_chapters(v1, v2, threshold=threshold)
    entries: list[DiffEntry] = []
    matched: list[tuple[Chapter, Chapter]] = []

    for v1_c, v2_c in pairs:
        if v1_c is None and v2_c is not None:
            entries.append(
                DiffEntry(
                    category="added",
                    v1_idx=None,
                    v2_idx=v2_c.idx,
                    v1_title=None,
                    v2_title=v2_c.title,
                    changes=["new"],
                    details={
                        "kind": v2_c.kind,
                        "layout": v2_c.layout,
                        "pattern_id": v2_c.pattern_id,
                    },
                ),
            )
        elif v1_c is not None and v2_c is None:
            entries.append(
                DiffEntry(
                    category="removed",
                    v1_idx=v1_c.idx,
                    v2_idx=None,
                    v1_title=v1_c.title,
                    v2_title=None,
                    changes=["gone"],
                    details={
                        "kind": v1_c.kind,
                        "layout": v1_c.layout,
                        "pattern_id": v1_c.pattern_id,
                    },
                ),
            )
        elif v1_c is not None and v2_c is not None:
            matched.append((v1_c, v2_c))
            changes: list[str] = []
            details: dict[str, Any] = {}
            if v1_c.title != v2_c.title:
                changes.append("title")
                details["title"] = {"from": v1_c.title, "to": v2_c.title}
            if v1_c.layout != v2_c.layout:
                changes.append("layout")
                details["layout"] = {"from": v1_c.layout, "to": v2_c.layout}
            if (v1_c.pattern_id or "") != (v2_c.pattern_id or ""):
                changes.append("pattern")
                details["pattern_id"] = {"from": v1_c.pattern_id, "to": v2_c.pattern_id}
            if v1_c.sha256 != v2_c.sha256:
                changes.append("body")
                details["sha256"] = {"from": v1_c.sha256[:12], "to": v2_c.sha256[:12]}
            if changes:
                entry = DiffEntry(
                    category="modified",
                    v1_idx=v1_c.idx,
                    v2_idx=v2_c.idx,
                    v1_title=v1_c.title,
                    v2_title=v2_c.title,
                    changes=changes,
                    details=details,
                )
                if include_text_diff and "body" in changes:
                    entry.text_diff = _line_level_text_diff(v1_c, v2_c)
                entries.append(entry)

    # Reorder check(整体级别 · 给一条独立 entry · 不重复 modified)
    if detect_reorder(matched):
        order_v1 = [
            (c1.idx, c1.title) for c1, _ in sorted(matched, key=lambda p: p[0].idx)
            if c1.kind == "content"
        ]
        order_v2 = [
            (c2.idx, c2.title) for c1, c2 in sorted(matched, key=lambda p: p[0].idx)
            if c1.kind == "content"
        ]
        entries.append(
            DiffEntry(
                category="reordered",
                v1_idx=None,
                v2_idx=None,
                v1_title=None,
                v2_title=None,
                changes=["order"],
                details={
                    "v1_order": order_v1,
                    "v2_order_when_matched": order_v2,
                },
            ),
        )

    return entries


# ------------------------- render ------------------------- #


# ANSI colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def _color(s: str, c: str, enabled: bool) -> str:
    if not enabled:
        return s
    return f"{c}{s}{C.RESET}"


def render_text(
    result: DiffResult,
    include_text_diff: bool = False,
    color: bool = True,
) -> str:
    """git-diff 风格的 text 输出."""
    lines: list[str] = []
    lines.append(_color("=== deck_diff ===", C.BOLD + C.CYAN, color))
    lines.append(f"  v1: {result.v1_path}  ({result.v1_chapter_count} chapters)")
    lines.append(f"  v2: {result.v2_path}  ({result.v2_chapter_count} chapters)")
    lines.append("")
    s = result.summary
    lines.append(
        _color(
            f"summary: +{s.get('added', 0)} added · -{s.get('removed', 0)} removed · "
            f"~{s.get('modified', 0)} modified · ↻{s.get('reordered', 0)} reordered",
            C.BOLD,
            color,
        ),
    )
    lines.append("")

    if not result.diffs:
        lines.append(_color("✓ no semantic differences detected", C.GREEN, color))
        return "\n".join(lines) + "\n"

    # Group by category for readability
    groups = {"added": [], "removed": [], "modified": [], "reordered": []}
    for e in result.diffs:
        groups[e.category].append(e)

    for cat, entries in groups.items():
        if not entries:
            continue
        sym, col = {
            "added": ("+", C.GREEN),
            "removed": ("-", C.RED),
            "modified": ("~", C.YELLOW),
            "reordered": ("↻", C.MAGENTA),
        }[cat]
        lines.append(_color(f"--- {cat.upper()} ({len(entries)}) ---", C.BOLD + col, color))

        for e in entries:
            if cat == "added":
                lines.append(
                    _color(
                        f"  {sym} v2 #{e.v2_idx} · {e.v2_title}",
                        col,
                        color,
                    ),
                )
                d = e.details
                meta = []
                if d.get("kind"):
                    meta.append(f"kind={d['kind']}")
                if d.get("layout"):
                    meta.append(f"layout={d['layout']}")
                if d.get("pattern_id"):
                    meta.append(f"pattern={d['pattern_id']}")
                if meta:
                    lines.append(_color(f"      ({' · '.join(meta)})", C.DIM, color))
            elif cat == "removed":
                lines.append(
                    _color(
                        f"  {sym} v1 #{e.v1_idx} · {e.v1_title}",
                        col,
                        color,
                    ),
                )
                d = e.details
                meta = []
                if d.get("kind"):
                    meta.append(f"kind={d['kind']}")
                if d.get("layout"):
                    meta.append(f"layout={d['layout']}")
                if d.get("pattern_id"):
                    meta.append(f"pattern={d['pattern_id']}")
                if meta:
                    lines.append(_color(f"      ({' · '.join(meta)})", C.DIM, color))
            elif cat == "modified":
                pos_str = (
                    f"v1 #{e.v1_idx} → v2 #{e.v2_idx}"
                    if e.v1_idx != e.v2_idx
                    else f"#{e.v1_idx}"
                )
                title_str = (
                    e.v1_title if e.v1_title == e.v2_title
                    else f"{e.v1_title} → {e.v2_title}"
                )
                lines.append(_color(f"  {sym} {pos_str} · {title_str}", col, color))
                lines.append(
                    _color(f"      changed: {', '.join(e.changes)}", C.DIM, color),
                )
                for k, v in e.details.items():
                    if k == "sha256":
                        lines.append(
                            _color(
                                f"        body: {v['from']} → {v['to']}",
                                C.DIM,
                                color,
                            ),
                        )
                    else:
                        lines.append(
                            _color(
                                f"        {k}: {v.get('from')!r} → {v.get('to')!r}",
                                C.DIM,
                                color,
                            ),
                        )
                if include_text_diff and e.text_diff:
                    for ln in e.text_diff.splitlines():
                        if ln.startswith("+") and not ln.startswith("+++"):
                            lines.append(_color(f"        {ln}", C.GREEN, color))
                        elif ln.startswith("-") and not ln.startswith("---"):
                            lines.append(_color(f"        {ln}", C.RED, color))
                        elif ln.startswith("@@"):
                            lines.append(_color(f"        {ln}", C.CYAN, color))
                        else:
                            lines.append(_color(f"        {ln}", C.DIM, color))
            elif cat == "reordered":
                lines.append(_color(f"  {sym} chapter order changed", col, color))
                v1_order = e.details.get("v1_order", [])
                v2_order = e.details.get("v2_order_when_matched", [])
                lines.append(
                    _color(
                        f"      v1 idx seq: {[i for i, _ in v1_order]}",
                        C.DIM,
                        color,
                    ),
                )
                lines.append(
                    _color(
                        f"      v2 idx seq: {[i for i, _ in v2_order]}",
                        C.DIM,
                        color,
                    ),
                )
        lines.append("")

    return "\n".join(lines) + "\n"


def render_json(result: DiffResult) -> str:
    payload = {
        "v1_path": result.v1_path,
        "v2_path": result.v2_path,
        "v1_chapter_count": result.v1_chapter_count,
        "v2_chapter_count": result.v2_chapter_count,
        "summary": result.summary,
        "diffs": [asdict(e) for e in result.diffs],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ------------------------- main ------------------------- #


def run_diff(
    v1_path: Path,
    v2_path: Path,
    threshold: float = 80.0,
    include_text_diff: bool = False,
) -> DiffResult:
    v1 = parse_chapters(v1_path)
    v2 = parse_chapters(v2_path)
    diffs = diff_chapters(
        v1, v2,
        threshold=threshold,
        include_text_diff=include_text_diff,
    )
    summary: dict[str, int] = {"added": 0, "removed": 0, "modified": 0, "reordered": 0}
    for e in diffs:
        summary[e.category] = summary.get(e.category, 0) + 1

    return DiffResult(
        v1_path=str(v1_path),
        v2_path=str(v2_path),
        v1_chapter_count=len(v1),
        v2_chapter_count=len(v2),
        diffs=diffs,
        summary=summary,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Semantic diff between two deck content.md files (P3-13).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("v1", type=Path, help="Path to v1 content.md")
    parser.add_argument("v2", type=Path, help="Path to v2 content.md")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Write output to file (default: stdout).",
    )
    parser.add_argument(
        "--include-text-diff", action="store_true",
        help="For modified chapters, include line-level unified diff (text format only).",
    )
    parser.add_argument(
        "--threshold", type=float, default=80.0,
        help="Fuzzy title match threshold 0-100 (default: 80).",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color codes (text format only).",
    )
    args = parser.parse_args()

    if not args.v1.exists():
        print(f"ERROR: v1 not found: {args.v1}", file=sys.stderr)
        return 2
    if not args.v2.exists():
        print(f"ERROR: v2 not found: {args.v2}", file=sys.stderr)
        return 2

    result = run_diff(
        args.v1, args.v2,
        threshold=args.threshold,
        include_text_diff=args.include_text_diff,
    )

    # Auto-disable color if writing to file or not a tty
    color_enabled = not args.no_color and (args.output is None) and sys.stdout.isatty()

    if args.format == "json":
        out = render_json(result)
    else:
        out = render_text(
            result,
            include_text_diff=args.include_text_diff,
            color=color_enabled,
        )

    if args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"diff written: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)

    # Exit code: 0 if no changes, 1 if changes exist (git-diff convention)
    return 1 if result.diffs else 0


if __name__ == "__main__":
    sys.exit(main())
