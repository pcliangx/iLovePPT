"""scripts/derive_plan.py 测试(P2 · layout 可渲染性校验 + pattern 退役)。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import derive_plan as dp  # noqa: E402

CONTENT_TMPL = """---
title: 测试 deck
theme: tech_blue
output: ./deck_v1.pptx
---

# Outline

## [cover]
<!-- layout: cover -->
副标题一句话

## 1. 本季度营收超预期
<!-- layout: {layout1} -->
- **营收**: 同比 +12%
- **毛利**: 环比 +3pp

## 2. 下季度三个动作
<!-- layout: {layout2} -->
<!-- pattern: tpl:finance_arrow__07-cards -->
- **动作一**: 扩产能
- **动作二**: 控成本
"""


def _write(tmp_path: Path, layout1="cards", layout2="bullet_list") -> Path:
    p = tmp_path / "author" / "deck_v1_content.md"
    p.parent.mkdir(parents=True)
    p.write_text(CONTENT_TMPL.format(layout1=layout1, layout2=layout2),
                 encoding="utf-8")
    return p


def test_derive_basic(tmp_path):
    plan = dp.derive_plan(_write(tmp_path))
    assert plan["theme"] == "tech_blue"
    layouts = [s["layout"] for s in plan["slides"]]
    assert layouts == ["cover", "cards", "bullet_list"]
    assert "_warnings_unrenderable_layout" not in plan


def test_retired_pattern_comment_not_in_plan(tmp_path):
    """<!-- pattern: --> 注释已退役,不允许派生 pattern_id(传给 make_* 会 TypeError)。"""
    plan = dp.derive_plan(_write(tmp_path))
    assert not any("pattern_id" in s for s in plan["slides"])


def test_plugin_layout_validates_ok(tmp_path):
    """tech_blue yaml 里为 null 的 layout(data/timeline)有 plugin 兜底,不应报。"""
    plan = dp.derive_plan(_write(tmp_path, layout1="data", layout2="timeline"))
    assert "_warnings_unrenderable_layout" not in plan


def test_fake_layout_flagged(tmp_path):
    plan = dp.derive_plan(_write(tmp_path, layout2="fancy_grid"))
    bad = plan["_warnings_unrenderable_layout"]
    assert len(bad) == 1
    assert bad[0]["layout"] == "fancy_grid"
    assert bad[0]["page"] == 3


def test_unknown_theme_degrades_to_warning(tmp_path):
    p = _write(tmp_path)
    text = p.read_text(encoding="utf-8").replace("theme: tech_blue",
                                                  "theme: nonexistent_xyz")
    p.write_text(text, encoding="utf-8")
    plan = dp.derive_plan(p)
    bad = plan["_warnings_unrenderable_layout"]
    assert len(bad) == 1 and "error" in bad[0]  # 降级为警告,不 raise


def test_derived_sha256_matches_content_and_detects_edit(tmp_path):
    """builder Step 0.5 SSOT verify 依赖:derived_from_sha256 是 content.md
    bytes 的 sha256;content 改动后 stored hash 必然 mismatch(DERIVATION_MISMATCH
    的判定依据)。"""
    import hashlib
    p = _write(tmp_path)
    plan = dp.derive_plan(p)
    assert plan["derived_from_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    stored = plan["derived_from_sha256"]
    p.write_text(p.read_text(encoding="utf-8") + "\n改动一行\n", encoding="utf-8")
    assert dp.sha256_file(p) != stored


def test_strict_theme_load_failure_exits_1(tmp_path, monkeypatch, capsys):
    """--strict 下 theme 加载失败(无法校验)必须 exit 1 —— 无法校验 ≠ 校验通过。"""
    p = _write(tmp_path)
    text = p.read_text(encoding="utf-8").replace("theme: tech_blue",
                                                  "theme: nonexistent_xyz")
    p.write_text(text, encoding="utf-8")
    monkeypatch.setattr(sys, "argv",
                        ["derive_plan.py", str(p), "--strict", "--dry-run"])
    assert dp.main() == 1
    capsys.readouterr()


def test_nonstrict_theme_load_failure_exits_0(tmp_path, monkeypatch, capsys):
    """非 strict:theme 加载失败仅 stderr 告警(advisory),exit 0。"""
    p = _write(tmp_path)
    text = p.read_text(encoding="utf-8").replace("theme: tech_blue",
                                                  "theme: nonexistent_xyz")
    p.write_text(text, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["derive_plan.py", str(p), "--dry-run"])
    assert dp.main() == 0
    capsys.readouterr()
