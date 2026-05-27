#!/usr/bin/env python3
"""Per-deck token cost tracker · P1-8。

CLI:
    track_cost.py update --state <state.json> --agent <name> --tokens-in <N> --tokens-out <M>
    track_cost.py show   --state <state.json>
    track_cost.py reset  --state <state.json>

state.json schema(由本工具维护 `cost` 块,其他字段不动):
    {
      ...existing state.json fields...,
      "cost": {
        "tokens_by_agent": {
          "brainstorm":  {"input": 0, "output": 0},
          "author":      {"input": 0, "output": 0},
          "critic":      {"input": 0, "output": 0},
          "builder":     {"input": 0, "output": 0},
          "audience":    {"input": 0, "output": 0},
          "extractor":   {"input": 0, "output": 0}
        },
        "totals": {"input": 0, "output": 0},
        "cost_usd": 0.00,
        "last_updated": "2026-05-27T..."
      }
    }

价格 hardcoded for Opus 4.7(2026-05 USD/1M token,见 PRICES 常量;
需更新时改 PRICES 常量即可)。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Opus 价格(USD per 1M token)· 来源 https://www.anthropic.com/pricing(2026-05)
PRICES = {
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.80, "output": 4.0},
}

AGENTS = ("brainstorm", "author", "critic", "builder", "audience", "extractor")


def _empty_cost_block() -> dict:
    return {
        "tokens_by_agent": {a: {"input": 0, "output": 0} for a in AGENTS},
        "totals": {"input": 0, "output": 0},
        "cost_usd": 0.00,
        "cost_usd_breakdown_by_agent": {a: 0.00 for a in AGENTS},
        "model": "opus",  # 默认全 opus,future P3-7 Haiku 路由再分
        "last_updated": "",
    }


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"state.json 解析失败 {path}: {e}")


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_cost_block(state: dict) -> dict:
    cost = state.get("cost")
    if not cost or "tokens_by_agent" not in cost:
        cost = _empty_cost_block()
        state["cost"] = cost
    # 老 schema (单 int) 升级到 {input, output}
    tba = cost["tokens_by_agent"]
    for a in AGENTS:
        if a not in tba:
            tba[a] = {"input": 0, "output": 0}
        elif isinstance(tba[a], int):
            # 兼容老格式:把单 int 当 output(保守)
            tba[a] = {"input": 0, "output": tba[a]}
    if "totals" not in cost:
        cost["totals"] = {"input": 0, "output": 0}
    if "cost_usd_breakdown_by_agent" not in cost:
        cost["cost_usd_breakdown_by_agent"] = {a: 0.00 for a in AGENTS}
    if "model" not in cost:
        cost["model"] = "opus"
    return cost


def _recompute(cost: dict) -> None:
    model = cost.get("model", "opus")
    price = PRICES.get(model, PRICES["opus"])
    tba = cost["tokens_by_agent"]
    total_in = sum(tba[a]["input"] for a in AGENTS)
    total_out = sum(tba[a]["output"] for a in AGENTS)
    cost["totals"] = {"input": total_in, "output": total_out}
    # 每 agent breakdown
    breakdown = {}
    for a in AGENTS:
        ai = tba[a]["input"]
        ao = tba[a]["output"]
        breakdown[a] = round(
            (ai / 1_000_000) * price["input"] + (ao / 1_000_000) * price["output"],
            4,
        )
    cost["cost_usd_breakdown_by_agent"] = breakdown
    cost["cost_usd"] = round(
        (total_in / 1_000_000) * price["input"]
        + (total_out / 1_000_000) * price["output"],
        4,
    )
    cost["last_updated"] = datetime.utcnow().isoformat() + "Z"


def cmd_update(args) -> int:
    if args.agent not in AGENTS:
        print(f"ERROR: --agent must be one of {AGENTS}, got {args.agent}", file=sys.stderr)
        return 2
    if args.tokens_in is None and args.tokens_out is None and args.tokens is None:
        print("ERROR: 至少传 --tokens-in / --tokens-out / --tokens 之一", file=sys.stderr)
        return 2
    path = Path(args.state)
    state = _load_state(path)
    cost = _ensure_cost_block(state)
    # 兼容旧用法 --tokens(默认算 output,保守贵)
    tin = args.tokens_in or 0
    tout = args.tokens_out if args.tokens_out is not None else (args.tokens or 0)
    cost["tokens_by_agent"][args.agent]["input"] += tin
    cost["tokens_by_agent"][args.agent]["output"] += tout
    _recompute(cost)
    _save_state(path, state)
    print(f"[track_cost] {args.agent} +{tin}in/+{tout}out → total ${cost['cost_usd']}")
    return 0


def cmd_show(args) -> int:
    path = Path(args.state)
    state = _load_state(path)
    if "cost" not in state:
        print("(no cost block)")
        return 0
    cost = _ensure_cost_block(state)
    _recompute(cost)
    if args.format == "json":
        print(json.dumps(cost, ensure_ascii=False, indent=2))
    else:
        print(f"deck: {path}")
        print(f"model: {cost['model']}")
        print(f"last_updated: {cost['last_updated']}")
        print(f"totals: in={cost['totals']['input']:,} out={cost['totals']['output']:,}")
        print(f"cost_usd: ${cost['cost_usd']}")
        print("by agent:")
        for a in AGENTS:
            t = cost["tokens_by_agent"][a]
            u = cost["cost_usd_breakdown_by_agent"][a]
            print(f"  {a:11s}  in={t['input']:>10,}  out={t['output']:>10,}  ${u}")
    _save_state(path, state)  # 即使 show 也回写一次(确保 recompute 持久化)
    return 0


def cmd_reset(args) -> int:
    path = Path(args.state)
    state = _load_state(path)
    state["cost"] = _empty_cost_block()
    state["cost"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    _save_state(path, state)
    print(f"[track_cost] reset cost block in {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-deck token cost tracker (P1-8)",
        epilog="schema 文档:docs/state_schema.md § cost block",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_up = sub.add_parser("update", help="累加 agent token usage")
    p_up.add_argument("--state", required=True, help="state.json 路径")
    p_up.add_argument("--agent", required=True, choices=AGENTS)
    p_up.add_argument("--tokens-in", type=int, default=None, help="input tokens 累加")
    p_up.add_argument("--tokens-out", type=int, default=None, help="output tokens 累加")
    p_up.add_argument("--tokens", type=int, default=None,
                      help="(legacy)单 int,记作 output tokens")
    p_up.set_defaults(func=cmd_update)

    p_sh = sub.add_parser("show", help="打印当前 cost 块")
    p_sh.add_argument("--state", required=True)
    p_sh.add_argument("--format", choices=["text", "json"], default="text")
    p_sh.set_defaults(func=cmd_show)

    p_rs = sub.add_parser("reset", help="清零 cost 块")
    p_rs.add_argument("--state", required=True)
    p_rs.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
