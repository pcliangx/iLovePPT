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
