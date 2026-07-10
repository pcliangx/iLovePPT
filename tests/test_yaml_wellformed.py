"""全仓 yaml parse gate(P0 · critic-rubric.yaml 损坏事故的回归防线)。

背景:critic-rubric.yaml 曾因引号未闭合 + 内容重复拼接导致 yaml.safe_load
ParserError,B9/J1-J4 定义丢失 —— critic 量化评分的 SSOT 静默失效,hook 只能
靠硬编码阈值 fallback。此 gate 保证所有 git-tracked yaml 永远可 parse,
且 rubric 结构完整。CI 跑 pytest 即覆盖。
"""
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def _tracked_yaml_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.yaml", "*.yml"],
        capture_output=True, text=True, cwd=REPO, check=True,
    ).stdout.split()
    return out


@pytest.mark.parametrize("relpath", _tracked_yaml_files())
def test_yaml_parses(relpath):
    text = (REPO / relpath).read_text(encoding="utf-8")
    try:
        list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        pytest.fail(f"{relpath} 不是合法 yaml: {e}")


def test_critic_rubric_schema_complete():
    """rubric 是 critic 20 项量化评分的 SSOT:项数、字段、severity 四档都不能缺。"""
    data = yaml.safe_load(
        (REPO / ".claude/agents/critic-rubric.yaml").read_text(encoding="utf-8"))
    assert data["verdict_thresholds"] == {
        "block_severity": 3, "warn_accumulation": 5, "notes_min_severity": 1}
    items = (data["section_a_pyramid"] + data["section_b_alignment"]
             + data["section_judgmental"])
    ids = [x["id"] for x in items]
    assert ids == [
        "A1", "A2", "A3", "A4", "A5", "A6", "A7",
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9",
        "J1", "J2", "J3", "J4",
    ], f"rubric 项数/顺序漂移: {ids}"
    for item in items:
        for field in ("id", "name", "description",
                      "evidence_requirement", "severity_examples"):
            assert field in item, f"{item.get('id')} 缺 {field}"
        assert set(item["severity_examples"]) == {"0", "1", "2", "3"}, \
            f"{item['id']} severity_examples 不是 0-3 四档"
