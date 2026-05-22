"""build.py 单元测试。"""
import json
from pathlib import Path

import pytest

from build import load_plan, load_theme, build_deck, _extract_design_tokens
from themes import tech_blue


def _write_plan(tmp_path, data):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_plan_valid(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./out.pptx",
        "slides": [{"layout": "cover", "title": "T", "subtitle": "S"}]})
    plan = load_plan(p)
    assert plan["theme"] == "tech_blue"
    assert plan["_plan_dir"] == str(tmp_path.resolve())


def test_load_plan_missing_field_raises(tmp_path):
    p = _write_plan(tmp_path, {"theme": "tech_blue", "slides": []})
    with pytest.raises(ValueError) as e:
        load_plan(p)
    assert "output" in str(e.value)


def test_load_plan_slide_missing_layout_raises(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./o.pptx",
        "slides": [{"title": "无 layout"}]})
    with pytest.raises(ValueError) as e:
        load_plan(p)
    assert "第 1 页" in str(e.value)


def test_load_theme_tech_blue():
    assert load_theme("tech_blue") is tech_blue


def test_load_theme_unknown_raises():
    with pytest.raises(ValueError):
        load_theme("nope")


def test_load_theme_pptx_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_theme("/tmp/does_not_exist_xyz.pptx")


def test_build_deck_produces_pptx(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./deck.pptx",
        "slides": [
            {"layout": "cover", "title": "标题", "subtitle": "副标题"},
            {"layout": "bullet_list", "title": "要点", "items": ["a", "b"]}]})
    plan = load_plan(p)
    out = build_deck(plan)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.parent == tmp_path.resolve()


def test_build_deck_unknown_layout_raises(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx",
        "slides": [{"layout": "nonexistent_xyz"}]})
    plan = load_plan(p)
    with pytest.raises(ValueError) as e:
        build_deck(plan)
    assert "未知 layout" in str(e.value)


def test_build_deck_bad_field_raises_with_page_number(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx",
        "slides": [{"layout": "cover", "wrong_field": "x"}]})
    plan = load_plan(p)
    with pytest.raises(ValueError) as e:
        build_deck(plan)
    assert "第 1 页" in str(e.value)
