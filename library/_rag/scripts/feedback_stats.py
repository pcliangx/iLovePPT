#!/usr/bin/env python3
"""P3-5 · RAG quality feedback loop stats

输入:`library/_rag/feedback.jsonl`(append-only · audience agent 写)
输出:每 pattern 的 (avg_score, count) 表 + 哪些 pattern 触发降权(avg<7.0 + count>=3)

用法:
    library/_rag/.venv/bin/python library/_rag/scripts/feedback_stats.py
    library/_rag/.venv/bin/python library/_rag/scripts/feedback_stats.py --feedback /path/feedback.jsonl
    library/_rag/.venv/bin/python library/_rag/scripts/feedback_stats.py --format json

用于:user 月度 review,看哪些 pattern 反复拉低 audience 评分,决定是否
人工 retire / 重做该 pattern。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAG_DIR = SCRIPT_DIR.parent
DEFAULT_FEEDBACK_PATH = RAG_DIR / "feedback.jsonl"

# 跟 library/search.py 同源(若改这里, search.py 常量也要改 · SSOT 是 search.py)
FEEDBACK_AVG_THRESHOLD = 7.0
FEEDBACK_MIN_COUNT = 3
FEEDBACK_PENALTY_FACTOR = 0.9


def load_feedback(path: Path) -> tuple[dict[str, dict], int, int]:
    """Read jsonl, 聚合 stats.

    Returns: (stats_dict, total_rows, skipped_rows)
    """
    stats: dict[str, dict] = {}
    total = 0
    skipped = 0
    if not path.exists():
        return stats, total, skipped
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"[feedback_stats] WARN: line {line_no} JSON 解析失败 — {e}",
                    file=sys.stderr,
                )
                skipped += 1
                continue
            pid = rec.get("chosen_pattern_id")
            score = rec.get("audience_score")
            if not pid or not isinstance(score, (int, float)):
                skipped += 1
                continue
            entry = stats.setdefault(
                pid,
                {"count": 0, "sum_score": 0.0, "avg_score": 0.0, "min_score": float("inf"),
                 "max_score": float("-inf"), "decks": set()},
            )
            entry["count"] += 1
            entry["sum_score"] += float(score)
            entry["min_score"] = min(entry["min_score"], float(score))
            entry["max_score"] = max(entry["max_score"], float(score))
            deck = rec.get("deck")
            if deck:
                entry["decks"].add(deck)
    for pid, e in stats.items():
        e["avg_score"] = round(e["sum_score"] / e["count"], 4) if e["count"] > 0 else 0.0
        # 把 set 转 sorted list 便于序列化 / 打印
        e["decks"] = sorted(e["decks"])
    return stats, total, skipped


def is_penalized(entry: dict) -> bool:
    return entry["count"] >= FEEDBACK_MIN_COUNT and entry["avg_score"] < FEEDBACK_AVG_THRESHOLD


def print_text(stats: dict, total: int, skipped: int) -> None:
    print(f"=== Feedback stats ===")
    print(f"Total rows: {total} · Skipped (malformed): {skipped} · Unique patterns: {len(stats)}")
    print(f"Penalty rule: avg_score < {FEEDBACK_AVG_THRESHOLD} AND count >= {FEEDBACK_MIN_COUNT} → score × {FEEDBACK_PENALTY_FACTOR}")
    print()
    if not stats:
        print("(no feedback data)")
        return

    rows = sorted(stats.items(), key=lambda kv: (kv[1]["avg_score"], -kv[1]["count"]))

    print(f"{'pattern_id':<55s}  {'avg':>6s}  {'count':>6s}  {'min':>5s}  {'max':>5s}  {'decks':>6s}  {'penalty':>8s}")
    print("-" * 105)
    penalized_count = 0
    for pid, e in rows:
        penalty_str = "YES" if is_penalized(e) else ""
        if is_penalized(e):
            penalized_count += 1
        print(
            f"{pid:<55s}  {e['avg_score']:6.2f}  {e['count']:6d}  "
            f"{e['min_score']:5.1f}  {e['max_score']:5.1f}  {len(e['decks']):6d}  {penalty_str:>8s}"
        )

    print()
    print(f"Penalized patterns: {penalized_count} / {len(stats)}")
    if penalized_count > 0:
        print()
        print("=== Patterns triggering penalty ===")
        for pid, e in rows:
            if is_penalized(e):
                decks_preview = ", ".join(e["decks"][:3]) + ("..." if len(e["decks"]) > 3 else "")
                print(f"  - {pid}  (avg={e['avg_score']:.2f}, count={e['count']}, decks=[{decks_preview}])")


def print_json(stats: dict, total: int, skipped: int) -> None:
    out = {
        "total_rows": total,
        "skipped_rows": skipped,
        "unique_patterns": len(stats),
        "penalty_rule": {
            "avg_threshold": FEEDBACK_AVG_THRESHOLD,
            "min_count": FEEDBACK_MIN_COUNT,
            "penalty_factor": FEEDBACK_PENALTY_FACTOR,
        },
        "patterns": [
            {
                "pattern_id": pid,
                "avg_score": e["avg_score"],
                "count": e["count"],
                "min_score": e["min_score"] if e["min_score"] != float("inf") else None,
                "max_score": e["max_score"] if e["max_score"] != float("-inf") else None,
                "deck_count": len(e["decks"]),
                "decks": e["decks"],
                "penalized": is_penalized(e),
            }
            for pid, e in sorted(stats.items(), key=lambda kv: (kv[1]["avg_score"], -kv[1]["count"]))
        ],
    }
    out["penalized_count"] = sum(1 for p in out["patterns"] if p["penalized"])
    print(json.dumps(out, ensure_ascii=False, indent=2))


def main() -> int:
    p = argparse.ArgumentParser(
        description="P3-5 · audience feedback 月度 review 工具 · 看哪些 pattern 反复拉低评分",
        epilog="跟 library/search.py 同规则;改 search.py 常量后这里也要同步。",
    )
    p.add_argument(
        "--feedback",
        default=str(DEFAULT_FEEDBACK_PATH),
        help=f"feedback.jsonl 路径(默认 {DEFAULT_FEEDBACK_PATH})",
    )
    p.add_argument("--format", choices=["text", "json"], default="text")
    args = p.parse_args()

    feedback_path = Path(args.feedback)
    stats, total, skipped = load_feedback(feedback_path)

    if args.format == "json":
        print_json(stats, total, skipped)
    else:
        print_text(stats, total, skipped)

    return 0


if __name__ == "__main__":
    sys.exit(main())
