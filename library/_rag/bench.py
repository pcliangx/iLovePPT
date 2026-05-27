#!/usr/bin/env python3
"""RAG regression bench · 跑 7 query golden set,对比 baseline 防回归。

用法:
    library/_rag/.venv/bin/python library/_rag/bench.py --label baseline
    library/_rag/.venv/bin/python library/_rag/bench.py --label after-P0-4 --mode both
    library/_rag/.venv/bin/python library/_rag/bench.py --label test --queries custom_queries.yaml

行为:
    1. 读 bench_queries.yaml(SSOT · 7 query + expected + category_hint)
    2. 对每 query 跑 search()(直接 import library/search.py 不走 subprocess · 7×subprocess 多 1s+ 没必要)
    3. 计算指标:命中率 / 平均分 / gap / low-gap 数
    4. 输出 bench_results/<date>-<label>.{json,md}

Note:
    - 直接 import search.py 的 search() 函数 → 不触发 main() 的 query_log 写入,
      bench 跑多少遍都不会污染 query_log.jsonl
    - 默认开 expand_query + inverse_category(跟 CLI 默认一致)
    - 修改 bench_queries.yaml 的 query 集 = 之前 baseline 失效,需重跑 baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
LIBRARY_DIR = SCRIPT_DIR.parent
RESULTS_DIR = SCRIPT_DIR / "bench_results"

# import search.py from parent library/
sys.path.insert(0, str(LIBRARY_DIR))
from search import expand_query, search  # noqa: E402


DEFAULT_QUERIES_YAML = SCRIPT_DIR / "bench_queries.yaml"


def _run_one_query(
    q_def: dict,
    mode: str,
    top_k: int,
    kb: str,
    type_: str,
    low_gap_threshold: float,
    no_expand: bool,
    no_inverse_category: bool,
) -> dict:
    """跑单 query 返回标准化结果 dict。

    跟 CLI 行为对齐:
      - 默认开 expand_query(--no-expand 关)
      - 默认开 inverse_category penalty(--no-inverse-category 关 · 用来跑 P0-4 改动前的纯 baseline)
      - 默认 top_k=5
    """
    raw_query = q_def["query"]
    expected_short = q_def["expected_top1"]
    expected_id = f"tpl:{expected_short}"

    expanded = expand_query(raw_query, enabled=not no_expand)

    hits = search(
        query=expanded,
        query_image=None,
        kb=kb,
        type_=type_,
        category=None,
        preferred_template=None,
        top_k=top_k,
        fallback_threshold=0.55,
        mode=mode,
        inverse_category=not no_inverse_category,
    )

    top1 = hits[0] if hits else None
    top2 = hits[1] if len(hits) > 1 else None

    top1_id = top1["id"] if top1 else None
    top1_score = top1["score"] if top1 else 0.0
    top2_score = top2["score"] if top2 else 0.0
    gap_to_2 = round(top1_score - top2_score, 4) if top1 and top2 else None

    expected_match = top1_id == expected_id

    rank_of_expected: int | None = None
    for i, h in enumerate(hits):
        if h["id"] == expected_id:
            rank_of_expected = i + 1
            break

    hits_brief = [
        {
            "rank": i + 1,
            "id": h["id"],
            "score": h["score"],
            "row_type": h.get("row_type", ""),
            "category_or_layout": h.get("category_or_layout") or "",
        }
        for i, h in enumerate(hits)
    ]

    return {
        "query": raw_query,
        "expanded_query": expanded if expanded != raw_query else None,
        "expected_top1": expected_short,
        "expected_top1_id": expected_id,
        "actual_top1": (top1_id or "").replace("tpl:", "") if top1_id else None,
        "actual_top1_id": top1_id,
        "top1_score": top1_score,
        "top2_score": top2_score,
        "gap_to_2": gap_to_2,
        "low_gap": (gap_to_2 is not None and gap_to_2 < low_gap_threshold),
        "expected_match": expected_match,
        "rank_of_expected": rank_of_expected,
        "category_hint": q_def.get("category_hint"),
        "notes": q_def.get("notes"),
        "hits": hits_brief,
    }


def _summarise(per_query: list[dict], low_gap_threshold: float) -> dict:
    q_count = len(per_query)
    hits = sum(1 for r in per_query if r["expected_match"])
    avg_top1 = sum(r["top1_score"] for r in per_query) / q_count if q_count else 0.0
    gaps = [r["gap_to_2"] for r in per_query if r["gap_to_2"] is not None]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0.0
    low_gap_count = sum(1 for r in per_query if r["low_gap"])
    return {
        "query_count": q_count,
        "top1_hit_rate": hits,
        "top1_hit_rate_pct": round(hits / q_count, 4) if q_count else 0.0,
        "avg_top1_score": round(avg_top1, 4),
        "avg_gap": round(avg_gap, 4),
        "low_gap_count": low_gap_count,
        "low_gap_threshold": low_gap_threshold,
    }


def _render_markdown(payload: dict) -> str:
    """生成 bench markdown · 人读 friendly。"""
    s = payload["summary"]
    lines: list[str] = []
    lines.append(f"# RAG Bench: {payload['label']} · {payload['date']} · mode={payload['mode']}")
    lines.append("")
    lines.append(f"_Generated: {payload['ts']}_")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| Query 总数 | {s['query_count']} |")
    lines.append(f"| Top-1 命中数 | {s['top1_hit_rate']}/{s['query_count']} |")
    lines.append(f"| 命中率 | {s['top1_hit_rate_pct'] * 100:.1f}% |")
    lines.append(f"| 平均 Top-1 score | {s['avg_top1_score']:.4f} |")
    lines.append(f"| 平均 gap (#1 - #2) | {s['avg_gap']:.4f} |")
    lines.append(f"| Low-gap 数 (<{s['low_gap_threshold']}) | {s['low_gap_count']}/{s['query_count']} |")
    lines.append("")
    lines.append("## Details")
    lines.append("")
    lines.append("| Query | Expected | Actual #1 | Score #1 | Score #2 | Gap | Match? | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in payload["queries"]:
        actual = r["actual_top1"] or "(none)"
        mark = "✓" if r["expected_match"] else "✗"
        actual_disp = actual if r["expected_match"] else f"{actual} (expected rank={r['rank_of_expected']})"
        gap_disp = f"{r['gap_to_2']:.4f}" if r["gap_to_2"] is not None else "n/a"
        notes_parts: list[str] = []
        if r["low_gap"]:
            notes_parts.append("low-gap")
        if r.get("notes"):
            notes_parts.append(r["notes"])
        notes_disp = "; ".join(notes_parts)
        lines.append(
            f"| {r['query']} | {r['expected_top1']} | {actual_disp} | "
            f"{r['top1_score']:.4f} | {r['top2_score']:.4f} | {gap_disp} | {mark} | {notes_disp} |"
        )
    lines.append("")
    lines.append("## Per-query top-5 hits")
    lines.append("")
    for r in payload["queries"]:
        lines.append(f"### `{r['query']}`")
        lines.append("")
        lines.append(f"- expected: `{r['expected_top1_id']}` · rank={r['rank_of_expected']}")
        if r.get("expanded_query"):
            lines.append(f"- expanded: `{r['expanded_query']}`")
        lines.append("")
        lines.append("| Rank | ID | Score | Type | Cat/Layout |")
        lines.append("|---|---|---|---|---|")
        for h in r["hits"]:
            lines.append(
                f"| {h['rank']} | `{h['id']}` | {h['score']:.4f} | {h['row_type']} | "
                f"{h.get('category_or_layout', '')} |"
            )
        lines.append("")
    return "\n".join(lines)


def run_bench(
    queries_yaml: Path,
    label: str,
    mode: str,
    out_dir: Path,
    no_expand: bool,
    no_inverse_category: bool = False,
) -> dict:
    """跑一次 bench,返回 payload(已写文件)。"""
    spec = yaml.safe_load(queries_yaml.read_text(encoding="utf-8"))
    queries_def = spec["queries"]
    settings = spec.get("settings", {})
    top_k = settings.get("top_k", 5)
    kb = settings.get("kb", "pptx-templates")
    type_ = settings.get("type", "template")
    low_gap_threshold = settings.get("low_gap_threshold", 0.05)

    per_query: list[dict] = []
    for q_def in queries_def:
        per_query.append(
            _run_one_query(
                q_def=q_def,
                mode=mode,
                top_k=top_k,
                kb=kb,
                type_=type_,
                low_gap_threshold=low_gap_threshold,
                no_expand=no_expand,
                no_inverse_category=no_inverse_category,
            )
        )

    now = datetime.now(timezone.utc)
    payload = {
        "label": label,
        "date": now.strftime("%Y-%m-%d"),
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "settings": {
            "top_k": top_k,
            "kb": kb,
            "type": type_,
            "no_expand": no_expand,
            "no_inverse_category": no_inverse_category,
            "low_gap_threshold": low_gap_threshold,
        },
        "summary": _summarise(per_query, low_gap_threshold),
        "queries": per_query,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")
    json_path = out_dir / f"{date_str}-{label}.json"
    md_path = out_dir / f"{date_str}-{label}.md"
    if mode != "text":
        json_path = out_dir / f"{date_str}-{label}-{mode}.json"
        md_path = out_dir / f"{date_str}-{label}-{mode}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")

    payload["_json_path"] = str(json_path)
    payload["_md_path"] = str(md_path)
    return payload


def main():
    p = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="RAG regression bench · 跑 golden query set 对比 baseline",
    )
    p.add_argument("--label", required=True, help="bench 标签 · e.g. baseline / after-P0-4 / hybrid-test")
    p.add_argument(
        "--queries",
        default=str(DEFAULT_QUERIES_YAML),
        help=f"query SSOT yaml(默认 {DEFAULT_QUERIES_YAML.name})",
    )
    p.add_argument(
        "--mode",
        default="text",
        choices=["text", "hybrid", "both"],
        help="跑 text / hybrid / both(都跑)",
    )
    p.add_argument(
        "--out-dir",
        default=str(RESULTS_DIR),
        help=f"输出目录(默认 {RESULTS_DIR.name}/)",
    )
    p.add_argument("--no-expand", action="store_true", help="关闭 query 静态扩展(跟 CLI 一致)")
    p.add_argument(
        "--no-inverse-category",
        action="store_true",
        help="关闭 P0-4 的 inverse-category penalty(用来跑 P0-4 前的原始 baseline)",
    )
    args = p.parse_args()

    queries_yaml = Path(args.queries)
    if not queries_yaml.exists():
        print(f"ERROR: queries yaml 不存在 — {queries_yaml}", file=sys.stderr)
        sys.exit(2)
    out_dir = Path(args.out_dir)

    modes = ["text", "hybrid"] if args.mode == "both" else [args.mode]
    for m in modes:
        payload = run_bench(
            queries_yaml=queries_yaml,
            label=args.label,
            mode=m,
            out_dir=out_dir,
            no_expand=args.no_expand,
            no_inverse_category=args.no_inverse_category,
        )
        s = payload["summary"]
        print(
            f"[bench] {args.label} mode={m} · "
            f"hit={s['top1_hit_rate']}/{s['query_count']} ({s['top1_hit_rate_pct'] * 100:.1f}%) · "
            f"avg_top1={s['avg_top1_score']:.4f} · avg_gap={s['avg_gap']:.4f} · "
            f"low_gap={s['low_gap_count']}/{s['query_count']}"
        )
        print(f"  → {payload['_json_path']}")
        print(f"  → {payload['_md_path']}")


if __name__ == "__main__":
    main()
