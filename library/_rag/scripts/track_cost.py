#!/usr/bin/env python3
"""Per-deck token cost tracker · P1-8 + P3-17 budget。

CLI:
    track_cost.py update --state <state.json> --agent <name> --tokens-in <N> --tokens-out <M>
    track_cost.py show   --state <state.json>
    track_cost.py status --deck <working_dir>          # P3-17 · 主线程派发后跑,看是否 over budget
    track_cost.py reset  --state <state.json>
    track_cost.py set-budget --state <state.json> --budget <USD>   # P3-17 · 中途改 budget

state.json schema(由本工具维护 `cost` 块,其他字段不动):
    {
      ...existing state.json fields...,
      "cost": {
        "budget_usd": 10.0,            # P3-17 · brainstorm 收 brief 时填,默认 10
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
        "warned_at_pct": [],           # P3-17 · 已 warn 过的阈值,防止重复 warn(50/80/100)
        "warnings": [],                # P3-17 · 历次 warning 记录(append-only,主线程 / log review)
        "last_updated": "2026-05-27T..."
      }
    }

价格 hardcoded for Opus 4.7(2026-05 USD/1M token,见 PRICES 常量;
需更新时改 PRICES 常量即可)。

P3-17 budget 行为:
- update 后,若 cost_usd / budget_usd 跨过 50% / 80% / 100% 阈值(且未 warn 过)
  → stderr warn + state.cost.warnings[] append + state.cost.warned_at_pct append
- 100% 跨过时 exit code 2(主线程感知 over budget;否则 0)
- 主线程跑 `status --deck <wd>`:over budget(>=100%) → exit 2 + 显示询问 user 提示
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

# P3-17 · budget warning 阈值(%)
WARN_THRESHOLDS = (50, 80, 100)
DEFAULT_BUDGET_USD = 10.0


def _empty_cost_block(budget_usd: float = DEFAULT_BUDGET_USD) -> dict:
    return {
        "budget_usd": budget_usd,
        "tokens_by_agent": {a: {"input": 0, "output": 0} for a in AGENTS},
        "totals": {"input": 0, "output": 0},
        "cost_usd": 0.00,
        "cost_usd_breakdown_by_agent": {a: 0.00 for a in AGENTS},
        "model": "opus",  # 默认全 opus,future P3-7 Haiku 路由再分
        "warned_at_pct": [],
        "warnings": [],
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
    # P3-17 · budget / warning 字段升级(老 state.json 没有这些字段)
    if "budget_usd" not in cost:
        cost["budget_usd"] = DEFAULT_BUDGET_USD
    if "warned_at_pct" not in cost:
        cost["warned_at_pct"] = []
    if "warnings" not in cost:
        cost["warnings"] = []
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


def _check_budget_thresholds(cost: dict) -> tuple[list[int], bool]:
    """P3-17 · 检查跨过的 budget 阈值。

    Returns:
        (newly_crossed_pct, over_100): newly_crossed_pct 是这次新跨过(且未 warn)的阈值列表;
        over_100 表示当前 cost_usd >= budget_usd(100%)。
    """
    budget = cost.get("budget_usd", DEFAULT_BUDGET_USD)
    if budget <= 0:
        return [], False
    cur_pct = (cost["cost_usd"] / budget) * 100
    already_warned = set(cost.get("warned_at_pct", []))
    newly_crossed = []
    for threshold in WARN_THRESHOLDS:
        if cur_pct >= threshold and threshold not in already_warned:
            newly_crossed.append(threshold)
    over_100 = cur_pct >= 100
    return newly_crossed, over_100


def _emit_warnings(cost: dict, newly_crossed: list[int]) -> None:
    """P3-17 · stderr warn + state.cost.warnings[] append + warned_at_pct append。"""
    budget = cost.get("budget_usd", DEFAULT_BUDGET_USD)
    cur_pct = (cost["cost_usd"] / budget) * 100 if budget > 0 else 0
    ts = datetime.utcnow().isoformat() + "Z"
    for threshold in newly_crossed:
        msg = (
            f"[budget-warn] cost ${cost['cost_usd']:.4f} / budget ${budget:.2f} "
            f"= {cur_pct:.1f}% · 跨过 {threshold}% 阈值"
        )
        if threshold == 100:
            msg += " · OVER BUDGET · 主线程应暂停询问用户(继续 / 终止 / 提 budget)"
        print(msg, file=sys.stderr)
        cost["warnings"].append({
            "threshold_pct": threshold,
            "cost_usd": cost["cost_usd"],
            "budget_usd": budget,
            "ts": ts,
        })
        cost["warned_at_pct"].append(threshold)


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
    # P3-17 · 阈值检测 + warn
    newly_crossed, over_100 = _check_budget_thresholds(cost)
    if newly_crossed:
        _emit_warnings(cost, newly_crossed)
    _save_state(path, state)
    print(f"[track_cost] {args.agent} +{tin}in/+{tout}out → total ${cost['cost_usd']}")
    # exit code 2 = over 100%(主线程感知,可 ask user)
    return 2 if over_100 and 100 in newly_crossed else 0


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
        budget = cost.get("budget_usd", DEFAULT_BUDGET_USD)
        cur_pct = (cost["cost_usd"] / budget) * 100 if budget > 0 else 0
        print(f"deck: {path}")
        print(f"model: {cost['model']}")
        print(f"last_updated: {cost['last_updated']}")
        print(f"totals: in={cost['totals']['input']:,} out={cost['totals']['output']:,}")
        print(f"cost_usd: ${cost['cost_usd']}  ·  budget: ${budget:.2f}  ·  used: {cur_pct:.1f}%")
        if cost.get("warned_at_pct"):
            print(f"warned_at_pct: {cost['warned_at_pct']}")
        print("by agent:")
        for a in AGENTS:
            t = cost["tokens_by_agent"][a]
            u = cost["cost_usd_breakdown_by_agent"][a]
            print(f"  {a:11s}  in={t['input']:>10,}  out={t['output']:>10,}  ${u}")
    _save_state(path, state)  # 即使 show 也回写一次(确保 recompute 持久化)
    return 0


def cmd_status(args) -> int:
    """P3-17 · 主线程派发后跑,看是否 over budget。

    locate state.json:
      <deck>/author/deck_v1_state.json(主优先)
      <deck>/brainstorm/state.json(brainstorm 阶段)
      <deck>/state.json(legacy)
    """
    deck = Path(args.deck)
    candidates = [
        deck / "author" / "deck_v1_state.json",
        deck / "brainstorm" / "state.json",
        deck / "state.json",
    ]
    state_path = None
    for c in candidates:
        if c.exists():
            state_path = c
            break
    if state_path is None:
        print(f"(no state.json found in {deck}; candidates: {[str(c) for c in candidates]})",
              file=sys.stderr)
        return 0  # 没 state 不算错,只是没数据
    state = _load_state(state_path)
    if "cost" not in state:
        print(f"(no cost block in {state_path})")
        return 0
    cost = _ensure_cost_block(state)
    _recompute(cost)
    budget = cost.get("budget_usd", DEFAULT_BUDGET_USD)
    cur_pct = (cost["cost_usd"] / budget) * 100 if budget > 0 else 0
    over_100 = cur_pct >= 100

    payload = {
        "state_path": str(state_path),
        "cost_usd": cost["cost_usd"],
        "budget_usd": budget,
        "used_pct": round(cur_pct, 2),
        "over_budget": over_100,
        "warned_at_pct": cost.get("warned_at_pct", []),
        "recent_warnings": cost.get("warnings", [])[-3:],  # 最近 3 条
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        flag = "OVER BUDGET" if over_100 else "ok"
        print(f"[budget-status] {flag} · ${cost['cost_usd']:.4f} / ${budget:.2f} = {cur_pct:.1f}%")
        if over_100:
            print(
                "  → 主线程行动:暂停 + 询问用户三选一:(1) 继续 (2) 终止 (3) 提 budget(set-budget)",
                file=sys.stderr,
            )
    _save_state(state_path, state)
    return 2 if over_100 else 0


def cmd_set_budget(args) -> int:
    """P3-17 · 中途改 budget(用户答'提 budget' 后主线程跑)。"""
    if args.budget <= 0:
        print("ERROR: --budget 必须 > 0", file=sys.stderr)
        return 2
    path = Path(args.state)
    state = _load_state(path)
    cost = _ensure_cost_block(state)
    old = cost["budget_usd"]
    cost["budget_usd"] = float(args.budget)
    # 提 budget 时,清掉所有 >= 新阈值的 warn 记录(让 warn 重新生效)
    if args.budget > old:
        cost["warned_at_pct"] = [
            p for p in cost.get("warned_at_pct", [])
            if (cost["cost_usd"] / cost["budget_usd"]) * 100 >= p
        ]
    cost["last_updated"] = datetime.utcnow().isoformat() + "Z"
    _save_state(path, state)
    print(f"[track_cost] budget ${old:.2f} → ${args.budget:.2f}")
    return 0


def cmd_reset(args) -> int:
    path = Path(args.state)
    state = _load_state(path)
    # 保留 budget(reset 只清 token 跟 warn 历史,budget 不动)
    old_budget = DEFAULT_BUDGET_USD
    if "cost" in state and "budget_usd" in state["cost"]:
        old_budget = state["cost"]["budget_usd"]
    state["cost"] = _empty_cost_block(budget_usd=old_budget)
    state["cost"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    _save_state(path, state)
    print(f"[track_cost] reset cost block in {path} (budget kept: ${old_budget:.2f})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-deck token cost tracker (P1-8 + P3-17 budget)",
        epilog="schema 文档:docs/cost-budget.md",
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

    p_st = sub.add_parser("status", help="P3-17 · 主线程派发后看 budget 状态(exit 2 = over)")
    p_st.add_argument("--deck", required=True, help="deck 工作目录")
    p_st.add_argument("--format", choices=["text", "json"], default="text")
    p_st.set_defaults(func=cmd_status)

    p_sb = sub.add_parser("set-budget", help="P3-17 · 改 budget(用户提 budget 后跑)")
    p_sb.add_argument("--state", required=True)
    p_sb.add_argument("--budget", type=float, required=True, help="新 budget USD")
    p_sb.set_defaults(func=cmd_set_budget)

    p_rs = sub.add_parser("reset", help="清零 cost 块(budget 保留)")
    p_rs.add_argument("--state", required=True)
    p_rs.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
