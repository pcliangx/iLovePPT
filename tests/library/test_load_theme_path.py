"""验证 build.py:load_theme() 查找新路径 library/pptx-templates/_source/。"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "pptx-deck"))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "pptx"))


def test_repo_templates_dir_points_to_library(monkeypatch):
    import build
    actual = build._repo_templates_dir()
    expected_tail = ("library", "pptx-templates", "_source")
    parts = actual.parts
    assert parts[-3:] == expected_tail, f"got {parts[-3:]} expected {expected_tail}"


def test_find_template_in_library_pptx_templates_source(tmp_path, monkeypatch):
    import build
    fake_root = tmp_path / "fake_repo"
    fake_src = fake_root / "library" / "pptx-templates" / "_source"
    fake_src.mkdir(parents=True)
    (fake_src / "demo.pptx").write_bytes(b"PK\x03\x04 fake pptx")
    monkeypatch.setattr(build, "_repo_templates_dir", lambda: fake_src)
    found = build._find_template("demo")
    assert found is not None
    assert found.name == "demo.pptx"


def test_error_message_mentions_new_path(tmp_path, monkeypatch):
    import build
    monkeypatch.setattr(build, "_repo_templates_dir", lambda: tmp_path / "nonexistent")
    monkeypatch.setattr(build, "_list_available_templates", lambda: [])
    with pytest.raises(ValueError, match=r"library/pptx-templates"):
        build.load_theme("nonexistent_theme")
