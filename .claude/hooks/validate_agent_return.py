#!/usr/bin/env python3
# .claude/hooks/validate_agent_return.py
"""PostToolUse hook · 校验 iloveppt-* subagent 的 return handoff YAML(组件 C / P0-1)。

设计原则:block(exit 2)极保守 —— 拿不准 / 无结构 / 非主流水线 agent 一律 exit 0 放行。
只在「明确可判定的违规」上 block:
  - return YAML 解析失败(主流水线 agent 末尾 yaml fence 不合法)
  - next_action / verdict 不在该 agent 枚举内,或 verdict != next_action(critic)
  - 分数越界(audience overall_score / 各维度)
  - critic scores[].severity 非 int 0-3,或据公式重算的 verdict 与声明不符
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # <repo>/.claude/hooks → <repo>
RUBRIC = REPO / ".claude/agents/critic-rubric.yaml"

# 注:iloveppt-template-extractor(旁路)return schema 不同,本 gate 不校验 → 故意不在此集合
ILOVEPPT_AGENTS = {
    "iloveppt-critic", "iloveppt-audience", "iloveppt-builder",
    "iloveppt-author", "iloveppt-brainstorm",
}

# next_action 枚举(来源:pipeline-protocol.md §4.2 / 各 agent return 契约)
NEXT_ACTION_ENUM = {
    "iloveppt-critic": {"pass", "pass_with_notes", "needs_revision"},
    "iloveppt-audience": {"delivered", "needs_author_rewrite", "needs_visual_redo", "needs_theme_fix"},
    "iloveppt-builder": {"dispatch_audience", "hard_stop"},
    "iloveppt-author": {
        "ask_user_for_outline_approval", "ask_user_for_content_approval",
        "dispatch_self_stage_d", "dispatch_critic",
    },
    "iloveppt-brainstorm": {"dispatch_author", "needs_self_revision", "ask_user"},
}


def _extract_text(resp) -> str:
    """从 tool_response(str / dict / content-block list)里抽出文本。"""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for k in ("content", "text", "output", "result"):
            val = resp.get(k)
            if isinstance(val, str):
                return val
            if isinstance(val, list):
                return _extract_text(val)
        return ""
    if isinstance(resp, list):
        parts = []
        for item in resp:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _extract_last_yaml_block(text: str) -> str | None:
    """抽末尾 ```yaml ... ``` fence;无则 None。"""
    blocks = re.findall(r"```ya?ml\s*\n(.*?)```", text, re.S | re.I)
    return blocks[-1] if blocks else None


def _load_critic_thresholds() -> dict:
    """从 critic-rubric.yaml 读 verdict 阈值(SSOT);读不到回落硬编码默认。"""
    try:
        data = yaml.safe_load(RUBRIC.read_text(encoding="utf-8")) or {}
        t = data.get("verdict_thresholds") or {}
        return {
            "block_severity": int(t.get("block_severity", 3)),
            "warn_accumulation": int(t.get("warn_accumulation", 5)),
            "notes_min_severity": int(t.get("notes_min_severity", 1)),
        }
    except Exception:
        return {"block_severity": 3, "warn_accumulation": 5, "notes_min_severity": 1}


# J5 是 advisory,不计入 verdict 重算(见 critic-rubric.yaml formula 注释 + 本计划偏离 #4)
_VERDICT_EXCLUDE_IDS = {"J5"}


def _recompute_verdict(severities: list[int], thresholds: dict) -> str:
    """按 critic-rubric.yaml 公式从整数 severity 列表算 verdict。"""
    block = thresholds["block_severity"]
    warn_cap = thresholds["warn_accumulation"]
    notes_min = thresholds["notes_min_severity"]
    if any(s == block for s in severities):
        return "needs_revision"
    if sum(1 for s in severities if s == 2) > warn_cap:
        return "needs_revision"
    if any(s >= notes_min for s in severities):
        return "pass_with_notes"
    return "pass"


def validate_block(agent: str, block: str) -> tuple[int, str]:
    """校验单个 handoff YAML block。返回 (exit_code, message)。0=放行 2=block。"""
    try:
        data = yaml.safe_load(block)
    except Exception as e:
        return 2, f"{agent} return YAML 解析失败: {e!r}"
    if not isinstance(data, dict):
        return 0, ""  # 非 dict 结构,保守放行

    na = data.get("next_action")
    enum = NEXT_ACTION_ENUM.get(agent, set())
    if na is not None and enum and na not in enum:
        return 2, f"{agent} next_action={na!r} 不在枚举 {sorted(enum)}"

    if agent == "iloveppt-critic":
        verdict = data.get("verdict")
        if verdict is not None and na is not None and verdict != na:
            return 2, f"critic verdict={verdict!r} 与 next_action={na!r} 不一致(应相等)"
        scores = data.get("scores")
        if isinstance(scores, list) and scores:
            sev: list[int] = []
            for item in scores:
                if not isinstance(item, dict):
                    continue
                s = item.get("severity")
                if not isinstance(s, int) or isinstance(s, bool) or not (0 <= s <= 3):
                    return 2, f"critic scores 项 {item.get('id')!r} severity={s!r} 必须是 int 0-3"
                if str(item.get("id")) not in _VERDICT_EXCLUDE_IDS:
                    sev.append(s)
            if sev:
                thresholds = _load_critic_thresholds()
                expected = _recompute_verdict(sev, thresholds)
                declared = verdict if verdict is not None else na
                if declared and declared != expected:
                    return 2, (
                        f"critic verdict 公式重算={expected!r} 但声明={declared!r} "
                        f"(severity={sev}) — 改 verdict 或 复查 severity"
                    )
        return 0, ""

    if agent == "iloveppt-audience":
        sc = data.get("overall_score")
        if isinstance(sc, int) and not (0 <= sc <= 10):
            return 2, f"audience overall_score={sc} 越界(应 0-10)"
        pps = data.get("per_page_scores")
        if isinstance(pps, list):
            for pg in pps:
                if not isinstance(pg, dict):
                    continue
                for dim in ("comprehension_5s", "info_density", "visual_appeal", "flow_coherence"):
                    dv = pg.get(dim)
                    if isinstance(dv, int) and not (1 <= dv <= 10):
                        return 2, f"audience page {pg.get('page')} {dim}={dv} 越界(应 1-10)"
        return 0, ""

    return 0, ""  # builder/author/brainstorm:本版只校 next_action 枚举


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        return 0  # stdin 非 JSON:防御性放行,绝不因 hook 自身崩溃卡流水线
    if not isinstance(payload, dict):
        return 0

    tool_input = payload.get("tool_input") or {}
    agent = tool_input.get("subagent_type") if isinstance(tool_input, dict) else None
    if agent not in ILOVEPPT_AGENTS:
        return 0

    text = _extract_text(payload.get("tool_response"))
    block = _extract_last_yaml_block(text)
    if not block:
        return 0  # 无 yaml fence:保守放行

    try:
        code, msg = validate_block(agent, block)
    except Exception:
        return 0  # validator 自身异常:放行(绝不误杀)
    if code == 2:
        print(f"[gate] BLOCK · {msg}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
