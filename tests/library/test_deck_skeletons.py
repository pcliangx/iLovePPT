"""deck-skeletons 活链路校验(P1 · skeleton→theme 断链事故回归防线)。

背景:Phase 0 退役 RAG 模板后,6 个 skeleton 的 suggested_theme 曾全部指向
不存在的 theme(finance_arrow / enterprise_skyline 等),brainstorm 预填后
要到 builder load_theme 才 fail-loud。此 gate 保证 skeleton 引用的 theme
永远真实可加载,且不携带已退役的 pattern 注释体系。
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SKELETONS = sorted((REPO / "library" / "deck-skeletons").glob("*/skeleton.yaml"))


def _load_theme(name: str):
    from build import load_theme
    return load_theme(name)


@pytest.mark.parametrize("skeleton_path", SKELETONS, ids=lambda p: p.parent.name)
def test_suggested_theme_loadable(skeleton_path):
    data = yaml.safe_load(skeleton_path.read_text(encoding="utf-8"))
    theme = data["suggested_theme"]
    mod = _load_theme(theme)  # 不存在会 raise
    assert getattr(mod, "_THEME_CONFIG", None) is not None, \
        f"{theme} 未走 yaml SSOT 路径"


@pytest.mark.parametrize("skeleton_path", SKELETONS, ids=lambda p: p.parent.name)
def test_no_retired_pattern_refs(skeleton_path):
    """suggested_pattern / tpl: 注释体系已随 RAG 退役,skeleton 不允许残留。"""
    text = skeleton_path.read_text(encoding="utf-8")
    assert "suggested_pattern" not in text
    assert "tpl:" not in text
    tmpl = skeleton_path.parent / "outline.md.tmpl"
    if tmpl.exists():
        assert "tpl:" not in tmpl.read_text(encoding="utf-8"), \
            f"{tmpl} 残留退役 pattern 注释"


@pytest.mark.parametrize("skeleton_path", SKELETONS, ids=lambda p: p.parent.name)
def test_tmpl_theme_matches_skeleton(skeleton_path):
    """outline.md.tmpl frontmatter 的 theme 必须与 skeleton.yaml 一致。"""
    data = yaml.safe_load(skeleton_path.read_text(encoding="utf-8"))
    tmpl = skeleton_path.parent / "outline.md.tmpl"
    if not tmpl.exists():
        pytest.skip("no tmpl")
    text = tmpl.read_text(encoding="utf-8")
    assert f"theme: {data['suggested_theme']}" in text
