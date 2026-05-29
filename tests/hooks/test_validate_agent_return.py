"""组件 C(P0-1)· PostToolUse validator 单测。"""
import importlib.util
from pathlib import Path

_HOOK = Path(__file__).resolve().parents[2] / ".claude/hooks/validate_agent_return.py"
_spec = importlib.util.spec_from_file_location("validate_agent_return", _HOOK)
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)


def test_extract_text_handles_str_and_blocks():
    assert v._extract_text("hello") == "hello"
    assert v._extract_text({"content": "abc"}) == "abc"
    assert v._extract_text([{"type": "text", "text": "x"}, {"type": "text", "text": "y"}]) == "x\ny"
    assert v._extract_text(None) == ""


def test_extract_last_yaml_block():
    text = "preamble\n```yaml\na: 1\n```\nmid\n```yaml\nnext_action: pass\n```\n"
    block = v._extract_last_yaml_block(text)
    assert "next_action: pass" in block
    assert "a: 1" not in block  # 取最后一个 block
    assert v._extract_last_yaml_block("no fence here") is None


def test_load_critic_thresholds():
    t = v._load_critic_thresholds()
    assert t["block_severity"] == 3
    assert t["warn_accumulation"] == 5
    assert t["notes_min_severity"] == 1


def test_recompute_verdict():
    t = v._load_critic_thresholds()
    assert v._recompute_verdict([0, 0, 1], t) == "pass_with_notes"
    assert v._recompute_verdict([0, 0, 0], t) == "pass"
    assert v._recompute_verdict([0, 3, 1], t) == "needs_revision"
    assert v._recompute_verdict([2, 2, 2, 2, 2, 2], t) == "needs_revision"  # >5 个 2
    assert v._recompute_verdict([2, 2], t) == "pass_with_notes"


def test_validate_block_critic_ok():
    block = (
        "next_action: pass_with_notes\n"
        "verdict: pass_with_notes\n"
        "scores:\n"
        "  - {id: A1, severity: 0}\n"
        "  - {id: B9, severity: 1}\n"
        "  - {id: J5, severity: 2}\n"  # J5 不计入 → 不影响 verdict
    )
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 0, msg


def test_validate_block_critic_verdict_mismatch_blocks():
    block = (
        "next_action: pass\n"
        "verdict: pass\n"
        "scores:\n"
        "  - {id: A6, severity: 3}\n"  # 有 block → 应 needs_revision,声明 pass → 拦
    )
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 2
    assert "needs_revision" in msg


def test_validate_block_critic_severity_out_of_range_blocks():
    block = "next_action: pass\nverdict: pass\nscores:\n  - {id: A1, severity: 4}\n"
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 2


def test_validate_block_critic_verdict_ne_next_action_blocks():
    block = "next_action: pass\nverdict: needs_revision\n"
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 2


def test_validate_block_critic_no_scores_schema_only():
    # 无 scores → 只 schema 校验,不重算 → 合法枚举即放行
    block = "next_action: pass_with_notes\nverdict: pass_with_notes\n"
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 0


def test_validate_block_audience_score_out_of_range_blocks():
    block = "next_action: delivered\noverall_score: 11\nverdict: excellent\n"
    code, msg = v.validate_block("iloveppt-audience", block)
    assert code == 2


def test_validate_block_audience_ok():
    block = (
        "next_action: delivered\noverall_score: 9\nverdict: excellent\n"
        "per_page_scores:\n  - {page: 1, comprehension_5s: 9, info_density: 8, visual_appeal: 9, flow_coherence: 8}\n"
    )
    code, msg = v.validate_block("iloveppt-audience", block)
    assert code == 0, msg


def test_validate_block_bad_yaml_blocks():
    code, msg = v.validate_block("iloveppt-critic", "next_action: [unclosed\n")
    assert code == 2


def test_validate_block_unknown_next_action_blocks():
    code, msg = v.validate_block("iloveppt-builder", "next_action: teleport\n")
    assert code == 2


def test_validate_block_critic_bool_severity_blocks():
    # severity: true (yaml→Python bool) must be rejected (bool is int subclass)
    block = "next_action: pass\nverdict: pass\nscores:\n  - {id: A1, severity: true}\n"
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 2


def test_validate_block_audience_per_page_out_of_range_blocks():
    block = (
        "next_action: delivered\noverall_score: 9\nverdict: excellent\n"
        "per_page_scores:\n  - {page: 3, comprehension_5s: 9, info_density: 11, visual_appeal: 8, flow_coherence: 7}\n"
    )
    code, msg = v.validate_block("iloveppt-audience", block)
    assert code == 2


def test_validate_block_critic_j5_only_scores_no_block():
    # J5 excluded from recompute → sev empty → recompute skipped → declared accepted
    block = "next_action: pass\nverdict: pass\nscores:\n  - {id: J5, severity: 2}\n"
    code, msg = v.validate_block("iloveppt-critic", block)
    assert code == 0, msg


# ---------------------------------------------------------------------------
# C3 · main() subprocess tests
# ---------------------------------------------------------------------------
import json as _json
import subprocess
import sys as _sys


def _run_hook(payload: dict):
    return subprocess.run(
        [_sys.executable, str(_HOOK)],
        input=_json.dumps(payload), text=True, capture_output=True,
    )


def test_main_non_iloveppt_agent_passes():
    r = _run_hook({"tool_input": {"subagent_type": "Explore"},
                   "tool_response": "```yaml\nnext_action: teleport\n```"})
    assert r.returncode == 0


def test_main_no_yaml_block_passes():
    r = _run_hook({"tool_input": {"subagent_type": "iloveppt-critic"},
                   "tool_response": "just prose, no fence"})
    assert r.returncode == 0


def test_main_critic_mismatch_blocks():
    resp = ("summary text\n```yaml\nnext_action: pass\nverdict: pass\n"
            "scores:\n  - {id: A6, severity: 3}\n```")
    r = _run_hook({"tool_input": {"subagent_type": "iloveppt-critic"}, "tool_response": resp})
    assert r.returncode == 2
    assert "needs_revision" in r.stderr


def test_main_malformed_stdin_passes():
    r = subprocess.run([_sys.executable, str(_HOOK)], input="not json",
                       text=True, capture_output=True)
    assert r.returncode == 0  # 防御性:解析不了的 stdin 不崩不拦
