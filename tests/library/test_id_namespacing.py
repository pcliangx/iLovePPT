"""验证 id 命名空间:vp: / tpl: 前缀 + tpl: 模板↔页用 __ 分隔。"""

import importlib.util
import sys
from pathlib import Path

import pytest

if importlib.util.find_spec("sqlite_vec") is None or importlib.util.find_spec("yaml") is None:
    pytest.skip("sqlite-vec / pyyaml 未装。用 library/_rag/.venv/bin/python 跑", allow_module_level=True)

RAG_DIR = Path(__file__).resolve().parent.parent.parent / "library" / "_rag"
sys.path.insert(0, str(RAG_DIR))


@pytest.fixture
def db(tmp_path, monkeypatch):
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", tmp_path / "test.sqlite")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    conn = q.open_db()
    yield conn
    conn.close()


def test_vp_and_tpl_ids_coexist(db):
    db.execute(
        "INSERT INTO vp_items(id, text_doc, meta_path, category) VALUES (?,?,?,?)",
        ("vp:timeline-band-3", "doc", "visual-patterns/items/timeline-band-3/meta.yaml", "process"),
    )
    db.execute(
        "INSERT INTO tpl_templates(id, name, source_pptx_path, pages_count, text_doc) VALUES (?,?,?,?,?)",
        ("tpl:template_golden", "golden", "pptx-templates/_source/template_golden.pptx", 8, "doc"),
    )
    db.execute(
        "INSERT INTO tpl_pages(id, template_id, layout_type, page_index, text_doc) VALUES (?,?,?,?,?)",
        ("tpl:template_golden__01-cover", "tpl:template_golden", "cover", 1, "doc"),
    )
    rows = db.execute(
        "SELECT id FROM vp_items UNION ALL SELECT id FROM tpl_templates UNION ALL SELECT id FROM tpl_pages"
    ).fetchall()
    ids = sorted(r[0] for r in rows)
    assert ids == sorted([
        "vp:timeline-band-3",
        "tpl:template_golden",
        "tpl:template_golden__01-cover",
    ])


def test_template_id_with_double_underscore_rejected(tmp_path, monkeypatch):
    """ingest_tpl_template 应在 id 含 __ 时 raise ValueError (在 embed API 之前)。"""
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", tmp_path / "test.sqlite")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    import embed_text as et
    item_dir = tmp_path / "bad__name"
    item_dir.mkdir()
    (item_dir / "meta.yaml").write_text("id: bad__name\nname: x\n", encoding="utf-8")

    db = q.open_db()
    try:
        with pytest.raises(ValueError, match="__"):
            et.ingest_tpl_template(db, item_dir, api_key="test")
    finally:
        db.close()


def test_page_id_format(db):
    """页 id 必须形如 tpl:<template>__<NN-slug>"""
    db.execute(
        "INSERT INTO tpl_pages(id, template_id, layout_type, page_index, text_doc) VALUES (?,?,?,?,?)",
        ("tpl:template_golden__04-single-focus", "tpl:template_golden", "single-focus", 4, "doc"),
    )
    pid = db.execute("SELECT id FROM tpl_pages").fetchone()[0]
    prefix, payload = pid.split(":", 1)
    assert prefix == "tpl"
    assert "__" in payload
    tpl_part, page_part = payload.split("__", 1)
    assert tpl_part == "template_golden"
    assert page_part == "04-single-focus"
