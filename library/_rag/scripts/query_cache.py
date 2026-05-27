#!/usr/bin/env python3
"""External query cache for iconify / Unsplash · P2-10.

Builder Step 4 (visual enhancement) 反复发明 iconify / Unsplash query;
本 helper 把历史成功 query 沉淀到 `library/_rag/external_query_cache.jsonl`,
让后续相似页直接 reuse。

Storage:
    library/_rag/external_query_cache.jsonl —— 每行 1 JSON record:
    {
      "service": "iconify" | "unsplash",
      "query":   "team meeting",
      "result":  {
          "icon_name":  "ic:baseline-groups",   # iconify 才有
          "photo_id":   "abc123def",            # unsplash 才有
          "color":      "#0A52BF",              # 可选
          "url":        "...",                  # 可选 attribution
          "extra":      {}                      # 任意扩展
      },
      "score":   0.85,
      "ts":      "2026-05-27T..."               # ISO UTC
    }

CLI:
    query_cache.py lookup --service iconify --query "team meeting" [--limit 3] [--threshold 80]
    query_cache.py add    --service iconify --query "team meeting" --icon-name "ic:baseline-groups" --score 0.85
    query_cache.py add    --service unsplash --query "city skyline" --photo-id "abc" --score 0.92
    query_cache.py stats
    query_cache.py path                       # 打印 cache 文件绝对路径

设计:
- fuzzy match (rapidfuzz) 阈值 80(可调)
- 返回 top-N 历史命中 (默认 3)
- 同 (service, query, result) 重复 add → 累加 hit_count(让常用 cache 浮上去)

Exit codes:
    0 - normal (lookup 命中或未命中都 0)
    2 - bad CLI args
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print(
        "ERROR: rapidfuzz 不可用 — 安装 library/_rag/.venv 或 pip install rapidfuzz",
        file=sys.stderr,
    )
    sys.exit(2)

# cache 文件位置:跟脚本同 _rag 目录(library/_rag/external_query_cache.jsonl)
CACHE_PATH = Path(__file__).resolve().parent.parent / "external_query_cache.jsonl"

SERVICES = ("iconify", "unsplash")
DEFAULT_THRESHOLD = 80
DEFAULT_LIMIT = 3


# ------------------------- I/O ------------------------- #

def _load_cache() -> list[dict]:
    """Read jsonl, drop malformed lines silently (forward-compat)."""
    if not CACHE_PATH.exists():
        return []
    rows: list[dict] = []
    for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # skip malformed
    return rows


def _save_cache(rows: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    CACHE_PATH.write_text(body + ("\n" if body else ""), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_key(result: dict) -> str:
    """识别相同 result(用于去重 / 累加 hit_count)."""
    # iconify
    if "icon_name" in result:
        return f"icon:{result['icon_name']}|color:{result.get('color', '')}"
    # unsplash
    if "photo_id" in result:
        return f"photo:{result['photo_id']}"
    # generic fallback
    return json.dumps(result, sort_keys=True, ensure_ascii=False)


# ------------------------- ops ------------------------- #

def lookup(service: str, query: str, limit: int, threshold: int) -> list[dict]:
    """Return top-N matching cache records (sorted by fuzz score DESC, then hit_count DESC)."""
    rows = [r for r in _load_cache() if r.get("service") == service]
    if not rows:
        return []
    # rapidfuzz: process.extract over queries(取多个 candidate);允许重复 candidate(每 row 1)
    candidates = [r.get("query", "") for r in rows]
    # token_set_ratio 比 ratio 更稳:"team meeting" vs "meeting team" 都 100
    scored: list[tuple[dict, float]] = []
    for idx, cand in enumerate(candidates):
        s = fuzz.token_set_ratio(query, cand)
        if s >= threshold:
            scored.append((rows[idx], s))
    # 排序:score DESC, hit_count DESC, ts DESC
    scored.sort(
        key=lambda x: (x[1], x[0].get("hit_count", 1), x[0].get("ts", "")),
        reverse=True,
    )
    out: list[dict] = []
    for row, s in scored[:limit]:
        out.append({**row, "fuzz_score": round(s, 1)})
    return out


def add(service: str, query: str, result: dict, score: float) -> dict:
    """Append or merge (累加 hit_count if same service+query+result_key)."""
    rows = _load_cache()
    key = _result_key(result)
    # 寻 existing 同 service+query+result
    for r in rows:
        if (
            r.get("service") == service
            and r.get("query") == query
            and _result_key(r.get("result", {})) == key
        ):
            r["hit_count"] = r.get("hit_count", 1) + 1
            r["score"] = max(r.get("score", 0.0), score)  # 取更高 score
            r["last_ts"] = _now_iso()
            _save_cache(rows)
            return r
    # new
    rec = {
        "service": service,
        "query": query,
        "result": result,
        "score": float(score),
        "hit_count": 1,
        "ts": _now_iso(),
        "last_ts": _now_iso(),
    }
    rows.append(rec)
    _save_cache(rows)
    return rec


def stats() -> dict:
    rows = _load_cache()
    out: dict = {
        "cache_path": str(CACHE_PATH),
        "total": len(rows),
        "by_service": {},
    }
    for s in SERVICES:
        s_rows = [r for r in rows if r.get("service") == s]
        out["by_service"][s] = {
            "count": len(s_rows),
            "total_hits": sum(r.get("hit_count", 1) for r in s_rows),
            "avg_score": (
                round(sum(r.get("score", 0.0) for r in s_rows) / len(s_rows), 3)
                if s_rows
                else None
            ),
            "unique_queries": len({r.get("query") for r in s_rows}),
        }
    # 其他 service(future-proof)
    other = [r for r in rows if r.get("service") not in SERVICES]
    if other:
        out["by_service"]["_other"] = {"count": len(other)}
    return out


# ------------------------- CLI ------------------------- #

def cmd_lookup(args) -> int:
    hits = lookup(args.service, args.query, args.limit, args.threshold)
    if args.format == "json":
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        if not hits:
            print(f"(no cache hit for service={args.service} query={args.query!r} "
                  f"@ threshold {args.threshold})")
            return 0
        print(f"# top-{len(hits)} cache hits for service={args.service} query={args.query!r}")
        for i, h in enumerate(hits, 1):
            r = h["result"]
            asset = r.get("icon_name") or r.get("photo_id") or "(?)"
            print(
                f"  {i}. fuzz={h['fuzz_score']:>5} | hit_count={h.get('hit_count', 1)} | "
                f"score={h.get('score', 0):.2f} | query={h['query']!r} | result={asset}"
            )
    return 0


def cmd_add(args) -> int:
    result: dict = {}
    if args.service == "iconify":
        if not args.icon_name:
            print("ERROR: iconify add 必须 --icon-name", file=sys.stderr)
            return 2
        result["icon_name"] = args.icon_name
    elif args.service == "unsplash":
        if not args.photo_id:
            print("ERROR: unsplash add 必须 --photo-id", file=sys.stderr)
            return 2
        result["photo_id"] = args.photo_id
    else:
        print(f"ERROR: unknown service {args.service}", file=sys.stderr)
        return 2
    if args.color:
        result["color"] = args.color
    if args.url:
        result["url"] = args.url
    rec = add(args.service, args.query, result, args.score)
    print(
        f"[query_cache] added/merged: service={rec['service']} query={rec['query']!r} "
        f"hit_count={rec['hit_count']} score={rec['score']}"
    )
    return 0


def cmd_stats(args) -> int:
    s = stats()
    if args.format == "json":
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    print(f"cache: {s['cache_path']}")
    print(f"total records: {s['total']}")
    for svc, info in s["by_service"].items():
        print(f"  [{svc}]")
        for k, v in info.items():
            print(f"    {k}: {v}")
    return 0


def cmd_path(args) -> int:
    print(str(CACHE_PATH))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="External query cache for iconify / Unsplash (P2-10).",
        epilog=(
            "用法示例:\n"
            "  query_cache.py lookup --service iconify --query 'team meeting'\n"
            "  query_cache.py add    --service iconify --query 'team meeting' "
            "--icon-name ic:baseline-groups --score 0.85\n"
            "  query_cache.py stats\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lk = sub.add_parser("lookup", help="模糊查 cache · top-N")
    p_lk.add_argument("--service", required=True, choices=SERVICES)
    p_lk.add_argument("--query", required=True)
    p_lk.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p_lk.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                      help=f"fuzz score lower bound 0-100 (default {DEFAULT_THRESHOLD})")
    p_lk.add_argument("--format", choices=["text", "json"], default="text")
    p_lk.set_defaults(func=cmd_lookup)

    p_ad = sub.add_parser("add", help="沉淀新 query / 累加 hit_count")
    p_ad.add_argument("--service", required=True, choices=SERVICES)
    p_ad.add_argument("--query", required=True)
    p_ad.add_argument("--score", type=float, required=True, help="0-1 between (user-supplied subjective quality)")
    p_ad.add_argument("--icon-name", help="iconify 必填(prefix:name)")
    p_ad.add_argument("--photo-id", help="unsplash 必填")
    p_ad.add_argument("--color", help="可选 hex (e.g. #0A52BF)")
    p_ad.add_argument("--url", help="可选 fetch URL / attribution")
    p_ad.set_defaults(func=cmd_add)

    p_st = sub.add_parser("stats", help="按 service 统计 cache 容量")
    p_st.add_argument("--format", choices=["text", "json"], default="text")
    p_st.set_defaults(func=cmd_stats)

    p_pt = sub.add_parser("path", help="打印 cache jsonl 绝对路径")
    p_pt.set_defaults(func=cmd_path)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
