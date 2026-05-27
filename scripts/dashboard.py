#!/usr/bin/env python3
"""Cross-deck dashboard · P2-11 + P2-12 + layout-stats 子命令.

聚合 `decks/*/` 下每个 deck 的运行状态,产出 markdown / json 报表。

数据来源(每个 deck):
- `<deck>/{brainstorm,author,builder,audience}/state.json` → 取 cost 块(P1-8) / chapter_hashes
- `<deck>/audience/*audience*.md` → 取最新 round 的 verdict / score / triage(needs_visual_redo_pages)
- `<deck>/builder/deck_v1_plan.json`(或 archive)→ 取每 slide 的 layout(layout-stats 用)
- `<deck>/author/state.json.edit_history` → rework 次数

子命令:
    dashboard.py                          # 跨所有 deck 概览(默认 markdown)
    dashboard.py --deck <name>            # 单 deck 详情
    dashboard.py --format json            # JSON 输出
    dashboard.py --decks-root <path>      # 覆盖 decks/ 路径(默认 ./decks)
    dashboard.py layout-stats             # P2-12 · layout × failure_rate 聚合
    dashboard.py layout-stats --format json
    dashboard.py layout-stats --threshold 20  # warn cutoff %(default 20)

输出 schema:
- markdown:1 行 1 deck 表(Deck / Stage / Audience Score / Cost USD / Rework Count / Last Updated)
- json:list of dict

设计原则:
- **fail-soft**:任何 deck 缺数据(无 state.json / 无 audience report)→ 字段填 "-",不阻塞其他 deck
- **不修改任何文件**:dashboard 纯读

Notes:
- decks/ 是 gitignore 的,本工具只本地跑,不产 commit artefact
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ------------------------- regex / helpers ------------------------- #

# 匹配各种 round 文件名:
#   deck_v1_audience.r3.md / audience_report_tier1_r4.md / audience_report.md / audience_review_r2.md
_ROUND_RE = re.compile(r"(?:^|[_.])r(\d+)(?:[._]|$)")


def _round_of(name: str) -> int:
    m = _ROUND_RE.search(name)
    return int(m.group(1)) if m else 0


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _safe_get(d: dict | None, *keys, default=None):
    cur: Any = d
    for k in keys:
        if cur is None or not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


# ------------------------- audience parse ------------------------- #

# Score 提取顺序(取第一个能 match 的):
#   1. yaml 块里 `overall_score: 8.3` / `weighted_score: 9.13`
#   2. markdown 里 `加权平均.*8.3` / `平均分.*8.3`
#   3. yaml `simple_avg: 8.10`
_SCORE_PATTERNS = [
    re.compile(r"overall_score\s*:\s*([0-9]+\.?[0-9]*)"),
    re.compile(r"weighted_score\s*:\s*([0-9]+\.?[0-9]*)"),
    re.compile(r"加权平均\s*[:\*\s]*([0-9]+\.[0-9]+)"),
    re.compile(r"加权(?:平均)?\s*[\*]*\s*([0-9]+\.[0-9]+)\s*/\s*10"),
    re.compile(r"平均分\s*[:\*\s]*([0-9]+\.[0-9]+)"),
    re.compile(r"simple_avg\s*:\s*([0-9]+\.?[0-9]*)"),
]

_VERDICT_PATTERNS = [
    re.compile(r"verdict\s*:\s*([a-z_]+)", re.I),
    re.compile(r"整体\s*verdict\s*[:\*]*\s*\*?\*?([A-Za-z_]+)", re.I),
]

# triage / needs_visual_redo extraction:
#   yaml: `needs_visual_redo: [6]` / `needs_theme_fix: [14, 20]`
_NEEDS_VISUAL_REDO_RE = re.compile(
    r"needs_visual_redo\s*:\s*\[([0-9,\s]+)\]", re.I,
)
_NEEDS_THEME_FIX_RE = re.compile(
    r"needs_theme_fix\s*:\s*\[([0-9,\s]+)\]", re.I,
)
_NEEDS_AUTHOR_REWRITE_RE = re.compile(
    r"needs_author_rewrite\s*:\s*\[([0-9,\s]+)\]", re.I,
)


def _parse_int_list(group_str: str) -> list[int]:
    return [
        int(x.strip())
        for x in group_str.split(",")
        if x.strip().isdigit()
    ]


def _newest_audience_report(audience_dir: Path) -> Path | None:
    """取 audience/ 下最新 round 的 audience 报告."""
    if not audience_dir.exists():
        return None
    candidates = list(audience_dir.glob("*audience*.md")) + list(
        audience_dir.glob("*audience_report*.md")
    )
    # 去重
    candidates = sorted(set(candidates))
    if not candidates:
        return None
    # 选最大 round 号(回退到 mtime)
    return max(candidates, key=lambda p: (_round_of(p.name), p.stat().st_mtime))


def parse_audience_report(path: Path) -> dict:
    """提取 score / verdict / triage 三件套."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict = {"path": str(path), "round": _round_of(path.name)}

    for pat in _SCORE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                out["score"] = float(m.group(1))
                break
            except ValueError:
                continue

    for pat in _VERDICT_PATTERNS:
        m = pat.search(text)
        if m:
            out["verdict"] = m.group(1).lower().strip("* ")
            break

    triage: dict[str, list[int]] = {}
    for name, regex in (
        ("needs_visual_redo", _NEEDS_VISUAL_REDO_RE),
        ("needs_theme_fix", _NEEDS_THEME_FIX_RE),
        ("needs_author_rewrite", _NEEDS_AUTHOR_REWRITE_RE),
    ):
        m = regex.search(text)
        if m:
            triage[name] = _parse_int_list(m.group(1))
    out["triage"] = triage
    return out


# ------------------------- deck-level aggregate ------------------------- #

def _collect_cost(deck_path: Path) -> dict:
    """跨 brainstorm / author / builder / audience state.json 聚合 cost 块."""
    total_in = 0
    total_out = 0
    total_usd = 0.0
    found = False
    for sub in ("brainstorm", "author", "critic", "builder", "audience"):
        sjson = _read_json(deck_path / sub / "state.json")
        cost = _safe_get(sjson, "cost")
        if not cost:
            continue
        found = True
        totals = _safe_get(cost, "totals", default={})
        total_in += int(totals.get("input", 0) or 0)
        total_out += int(totals.get("output", 0) or 0)
        total_usd += float(cost.get("cost_usd", 0) or 0)
    return {
        "found": found,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "cost_usd": round(total_usd, 4),
    }


def _rework_count(deck_path: Path) -> int:
    """edit_history 长度 - 1(第 1 轮不算 rework);也兼容 archive/*.r{N}.{ext} 数."""
    # 1. author state.json.edit_history
    author_state = _read_json(deck_path / "author" / "state.json")
    history = _safe_get(author_state, "edit_history", default=[])
    if history:
        return max(0, len(history) - 1)
    # 2. fallback: count archive files
    archives = list((deck_path / "author" / "archive").glob("*.r*.*")) if (
        deck_path / "author" / "archive"
    ).exists() else []
    return len(archives)


def _last_updated(deck_path: Path) -> str:
    """取所有 state.json 最大 mtime → ISO date."""
    mtimes: list[float] = []
    for sub in ("brainstorm", "author", "critic", "builder", "audience"):
        p = deck_path / sub / "state.json"
        if p.exists():
            mtimes.append(p.stat().st_mtime)
    if not mtimes:
        # 退一步:整个 deck dir mtime
        if deck_path.exists():
            mtimes.append(deck_path.stat().st_mtime)
    if not mtimes:
        return "-"
    from datetime import datetime, timezone
    return datetime.fromtimestamp(max(mtimes), tz=timezone.utc).date().isoformat()


def _stage_of(deck_path: Path, audience_info: dict) -> str:
    """简单状态机:看哪个 agent 已产 state.json + audience verdict."""
    if audience_info.get("verdict") in ("ship", "pass"):
        return "done"
    if audience_info.get("score") is not None and audience_info["score"] >= 9.0:
        return "done"
    if audience_info.get("path"):
        return "audience"
    if (deck_path / "builder" / "state.json").exists():
        return "builder"
    if (deck_path / "critic").exists() and any((deck_path / "critic").glob("*.md")):
        return "critic"
    if (deck_path / "author" / "state.json").exists():
        return "author"
    if (deck_path / "brainstorm" / "state.json").exists():
        return "brainstorm"
    return "init"


def summarize_deck(deck_path: Path) -> dict:
    """跑单 deck 的全字段聚合."""
    audience_dir = deck_path / "audience"
    aud_path = _newest_audience_report(audience_dir)
    aud_info = parse_audience_report(aud_path) if aud_path else {}

    cost = _collect_cost(deck_path)

    return {
        "deck": deck_path.name,
        "stage": _stage_of(deck_path, aud_info),
        "audience_score": aud_info.get("score"),
        "audience_round": aud_info.get("round"),
        "audience_verdict": aud_info.get("verdict"),
        "audience_path": aud_info.get("path"),
        "triage": aud_info.get("triage", {}),
        "cost_usd": cost["cost_usd"] if cost["found"] else None,
        "tokens_in": cost["tokens_in"] if cost["found"] else None,
        "tokens_out": cost["tokens_out"] if cost["found"] else None,
        "rework_count": _rework_count(deck_path),
        "last_updated": _last_updated(deck_path),
    }


# ------------------------- layout-stats (P2-12) ------------------------- #

def _slides_layouts(plan_json_path: Path) -> dict[int, str]:
    """读 deck_plan.json 把 page_no(1-based) → layout 映射."""
    data = _read_json(plan_json_path) or {}
    slides = data.get("slides", []) or []
    out: dict[int, str] = {}
    for idx, slide in enumerate(slides, start=1):
        layout = slide.get("layout") or "unknown"
        out[idx] = str(layout)
    return out


def _pick_plan_path(deck_path: Path) -> Path | None:
    """优先 deck_v1_plan.json,fallback deck_plan.json 旧名."""
    for cand in (
        deck_path / "builder" / "deck_v1_plan.json",
        deck_path / "builder" / "deck_plan.json",
    ):
        if cand.exists():
            return cand
    return None


def _all_audience_reports(audience_dir: Path) -> list[Path]:
    if not audience_dir.exists():
        return []
    return sorted(
        set(list(audience_dir.glob("*audience*.md")) + list(audience_dir.glob("*audience_report*.md")))
    )


def collect_layout_stats(deck_paths: list[Path], all_rounds: bool = False) -> dict:
    """对所有 deck 聚合:每 layout 出现 N 次 / needs_visual_redo N 次.

    Args:
        deck_paths: deck 目录列表
        all_rounds: True 时遍历每个 deck 所有 audience round(累计 needs_visual_redo
                    历史,呈现 layout 真实失败率);False 时只看最新 round
    """
    total = defaultdict(int)
    redo = defaultdict(int)
    redo_by_deck: dict[str, dict[str, list[int]]] = {}

    for dp in deck_paths:
        plan = _pick_plan_path(dp)
        if not plan:
            continue
        layouts = _slides_layouts(plan)
        for layout in layouts.values():
            total[layout] += 1

        # parse audience reports
        if all_rounds:
            aud_paths = _all_audience_reports(dp / "audience")
        else:
            latest = _newest_audience_report(dp / "audience")
            aud_paths = [latest] if latest else []

        seen_pages: set[int] = set()  # avoid double-count same page across rounds
        deck_redo: dict[str, list[int]] = defaultdict(list)
        for ap in aud_paths:
            aud = parse_audience_report(ap)
            redo_pages = aud.get("triage", {}).get("needs_visual_redo", []) or []
            for page_no in redo_pages:
                key = (page_no, layouts.get(page_no, "unknown"))
                if key in seen_pages:
                    continue
                seen_pages.add(key)
                layout = layouts.get(page_no, "unknown")
                redo[layout] += 1
                deck_redo[layout].append(page_no)
        if deck_redo:
            redo_by_deck[dp.name] = dict(deck_redo)

    rows = []
    for layout, t in sorted(total.items(), key=lambda x: -x[1]):
        r = redo[layout]
        rate = (r / t * 100.0) if t else 0.0
        rows.append({
            "layout": layout,
            "total": t,
            "redo": r,
            "failure_rate_pct": round(rate, 1),
        })
    return {
        "rows": rows,
        "by_deck": redo_by_deck,
        "mode": "all_rounds" if all_rounds else "latest_round",
    }


# ------------------------- formatters ------------------------- #

def _fmt(x: Any, default: str = "-") -> str:
    if x is None:
        return default
    return str(x)


def render_overview_md(rows: list[dict]) -> str:
    out = []
    out.append("# iLovePPT cross-deck dashboard\n")
    out.append("| Deck | Stage | Audience Score | Verdict | Cost USD | Rework Count | Last Updated |")
    out.append("|---|---|---|---|---|---|---|")
    for r in rows:
        score = (
            f"{r['audience_score']:.2f}" if isinstance(r.get("audience_score"), (int, float)) else "-"
        )
        verdict = _fmt(r.get("audience_verdict"))
        cost = (
            f"${r['cost_usd']:.2f}" if isinstance(r.get("cost_usd"), (int, float)) else "-"
        )
        out.append(
            f"| {r['deck']} | {r['stage']} | {score} | {verdict} | {cost} | "
            f"{_fmt(r.get('rework_count'), '0')} | {r['last_updated']} |"
        )
    return "\n".join(out) + "\n"


def render_deck_detail_md(deck: dict) -> str:
    out = [f"# Deck · {deck['deck']}\n"]
    out.append(f"- **Stage**: `{deck['stage']}`")
    out.append(f"- **Last updated**: {deck['last_updated']}")
    out.append(f"- **Rework count**: {deck['rework_count']}")
    score = (
        f"{deck['audience_score']:.2f}"
        if isinstance(deck.get("audience_score"), (int, float)) else "-"
    )
    out.append(f"- **Audience score** (latest r{_fmt(deck.get('audience_round'), '?')}): {score}")
    out.append(f"- **Verdict**: {_fmt(deck.get('audience_verdict'))}")
    cost = (
        f"${deck['cost_usd']:.4f}"
        if isinstance(deck.get("cost_usd"), (int, float)) else "(no cost tracked)"
    )
    out.append(f"- **Cost**: {cost}")
    if isinstance(deck.get("tokens_in"), int):
        out.append(
            f"- **Tokens**: in={deck['tokens_in']:,} / out={deck['tokens_out']:,}"
        )
    out.append("")
    triage = deck.get("triage", {})
    if triage:
        out.append("## Triage (latest audience round)")
        for k, v in triage.items():
            out.append(f"- `{k}`: {v}")
    if deck.get("audience_path"):
        out.append(f"\n*Source: `{deck['audience_path']}`*")
    return "\n".join(out) + "\n"


def render_layout_stats_md(stats: dict, threshold: float = 20.0) -> str:
    out = ["# iLovePPT · layout-level audience failure rate (P2-12)\n"]
    mode = stats.get("mode", "latest_round")
    out.append(f"*Mode: `{mode}` · failure_rate = needs_visual_redo_count / total_appearances*\n")
    out.append("| Layout | Total Appearances | Visual Redo Count | Failure Rate |")
    out.append("|---|---|---|---|")
    high_failure: list[dict] = []
    for r in stats["rows"]:
        rate = r["failure_rate_pct"]
        out.append(f"| {r['layout']} | {r['total']} | {r['redo']} | {rate}% |")
        if rate > threshold and r["total"] >= 3:
            high_failure.append(r)
    if high_failure:
        out.append("")
        out.append(f"## Warning · layouts above {threshold:.0f}% failure rate")
        out.append("")
        for hf in high_failure:
            out.append(
                f"- **{hf['layout']}** failure rate {hf['failure_rate_pct']}% "
                f"({hf['redo']}/{hf['total']}) — candidate for P3 refinement"
            )
    if stats.get("by_deck"):
        out.append("")
        out.append("## needs_visual_redo by deck × layout")
        for deck, layouts in stats["by_deck"].items():
            for layout, pages in layouts.items():
                out.append(f"- `{deck}` · {layout} · pages {pages}")
    return "\n".join(out) + "\n"


# ------------------------- CLI ------------------------- #

def _resolve_decks_root(args) -> Path:
    if args.decks_root:
        return Path(args.decks_root).resolve()
    return (Path.cwd() / "decks").resolve()


def _list_decks(decks_root: Path) -> list[Path]:
    if not decks_root.exists():
        return []
    return sorted(
        [p for p in decks_root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    )


def cmd_overview(args) -> int:
    decks_root = _resolve_decks_root(args)
    decks = _list_decks(decks_root)
    if args.deck:
        decks = [d for d in decks if d.name == args.deck]
        if not decks:
            print(f"ERROR: deck {args.deck!r} not found under {decks_root}", file=sys.stderr)
            return 2

    rows = [summarize_deck(d) for d in decks]

    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.deck and rows:
        print(render_deck_detail_md(rows[0]))
        return 0
    print(render_overview_md(rows))
    return 0


def cmd_layout_stats(args) -> int:
    decks_root = _resolve_decks_root(args)
    decks = _list_decks(decks_root)
    if args.deck:
        decks = [d for d in decks if d.name == args.deck]
        if not decks:
            print(f"ERROR: deck {args.deck!r} not found under {decks_root}", file=sys.stderr)
            return 2

    stats = collect_layout_stats(decks, all_rounds=args.all_rounds)

    if args.format == "json":
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0
    print(render_layout_stats_md(stats, threshold=args.threshold))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="iLovePPT cross-deck dashboard (P2-11 / P2-12).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  scripts/dashboard.py                       # 跨 deck 概览\n"
            "  scripts/dashboard.py --deck iloveppt-training\n"
            "  scripts/dashboard.py --format json\n"
            "  scripts/dashboard.py layout-stats          # P2-12 layout failure rate\n"
        ),
    )
    parser.add_argument("--decks-root", help="decks/ 目录(默认 ./decks)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--deck", help="单 deck 详情(过滤)")

    sub = parser.add_subparsers(dest="cmd")

    p_ls = sub.add_parser(
        "layout-stats",
        help="P2-12 · 按 layout 聚合 audience needs_visual_redo failure rate",
    )
    p_ls.add_argument("--decks-root", help="decks/ 目录(默认 ./decks)")
    p_ls.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_ls.add_argument("--deck", help="只看单 deck")
    p_ls.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="failure rate %% warn threshold(default 20)",
    )
    p_ls.add_argument(
        "--all-rounds",
        action="store_true",
        help="遍历每 deck 所有 audience round 累积 needs_visual_redo "
             "(default 只看最新 round)",
    )
    p_ls.set_defaults(func=cmd_layout_stats)

    args = parser.parse_args()
    if args.cmd is None:
        return cmd_overview(args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
