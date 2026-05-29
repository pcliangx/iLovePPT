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
