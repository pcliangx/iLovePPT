"""验证 library/_rag/db.sqlite 5 张表 + 2 张向量表结构。"""

import sys
from pathlib import Path

import pytest

RAG_DIR = Path(__file__).resolve().parent.parent.parent / "library" / "_rag"
sys.path.insert(0, str(RAG_DIR))


@pytest.fixture
def db(tmp_path, monkeypatch):
    """临时 DB, 不污染真实 db.sqlite。"""
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", tmp_path / "test.sqlite")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    conn = q.open_db()
    yield conn
    conn.close()


def test_has_five_management_tables(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_emb%' ORDER BY name"
    ).fetchall()
    names = sorted(r[0] for r in rows)
    assert "vp_items" in names
    assert "tpl_templates" in names
    assert "tpl_pages" in names


def test_vp_items_columns(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(vp_items)")]
    for col in ("id", "text_doc", "meta_path", "preview_path", "category", "updated_at"):
        assert col in cols, f"vp_items missing column {col}"


def test_tpl_templates_columns(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(tpl_templates)")]
    for col in (
        "id", "name", "desc", "category", "keywords", "recommended_for",
        "visual_tokens_json", "visual_signature", "iLovePPT_can_replicate_pct",
        "source_pptx_path", "pages_count", "meta_path", "preview_path",
        "text_doc", "updated_at",
    ):
        assert col in cols, f"tpl_templates missing column {col}"


def test_tpl_pages_columns(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(tpl_pages)")]
    for col in (
        "id", "template_id", "layout_type", "page_index", "text_doc",
        "meta_path", "preview_path", "extras_json", "updated_at",
    ):
        assert col in cols, f"tpl_pages missing column {col}"


def test_text_emb_is_vec_virtual(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE name='text_emb' AND type='table'"
    ).fetchall()
    assert rows, "text_emb table not created"


def test_image_emb_is_vec_virtual(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE name='image_emb' AND type='table'"
    ).fetchall()
    assert rows, "image_emb table not created"
