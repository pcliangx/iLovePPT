"""验证 ingest pipeline end-to-end(mock embed API, 真跑 yaml + DB 写入)。"""

import importlib.util
import sys
from pathlib import Path

import pytest

if importlib.util.find_spec("sqlite_vec") is None or importlib.util.find_spec("yaml") is None:
    pytest.skip("sqlite-vec / pyyaml 未装。用 library/_rag/.venv/bin/python 跑", allow_module_level=True)

# P1-6 batch refactor 后 ingest_vp_item / ingest_tpl_template 单条函数已不存在。
# 新 API:_collect_vp_tasks / _collect_tpl_tasks + embed_*_batch + _write_task。
# 本文件测的是旧 API,test_id_namespacing.py::test_template_id_with_double_underscore_rejected
# 已覆盖关键 __ 校验逻辑(用新 API),其他端到端 ingest 测试待 P3 follow-up 重写。
pytest.skip("Pre-P1-6 batch API tests — pending rewrite", allow_module_level=True)

LIB_DIR = Path(__file__).resolve().parent.parent.parent / "library"
RAG_DIR = LIB_DIR / "_rag"
sys.path.insert(0, str(LIB_DIR))
sys.path.insert(0, str(RAG_DIR))


@pytest.fixture
def fake_lib(tmp_path, monkeypatch):
    """临时 library/ + DB。"""
    fake = tmp_path / "library"
    (fake / "visual-patterns" / "items").mkdir(parents=True)
    (fake / "pptx-templates" / "items").mkdir(parents=True)
    (fake / "pptx-templates" / "_source").mkdir(parents=True)

    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", tmp_path / "db.sqlite")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    import embed_text as et
    monkeypatch.setattr(et, "LIBRARY_ROOT", fake)
    monkeypatch.setattr(et, "VP_ROOT", fake / "visual-patterns")
    monkeypatch.setattr(et, "TPL_ROOT", fake / "pptx-templates")
    fake_vec = [0.0] * q.EMBED_DIM
    fake_vec[0] = 1.0
    monkeypatch.setattr(et, "embed_text", lambda text, **kw: fake_vec)
    monkeypatch.setattr(q, "embed_text", lambda text, **kw: fake_vec)
    yield fake, q


def test_ingest_vp_item(fake_lib):
    fake_path, q = fake_lib
    item_dir = fake_path / "visual-patterns" / "items" / "demo-pattern"
    item_dir.mkdir()
    (item_dir / "meta.yaml").write_text(
        "id: demo-pattern\nname: Demo\ncategory: process\n"
        "content_intent: [test]\nkeywords: [demo]\n",
        encoding="utf-8",
    )

    import embed_text as et
    db = q.open_db()
    full_id = et.ingest_vp_item(db, item_dir, api_key="test")
    db.commit()

    assert full_id == "vp:demo-pattern"
    row = db.execute("SELECT id, category FROM vp_items WHERE id = ?", (full_id,)).fetchone()
    assert row[0] == "vp:demo-pattern"
    assert row[1] == "process"
    emb_row = db.execute("SELECT id FROM text_emb WHERE id = ?", (full_id,)).fetchone()
    assert emb_row is not None
    db.close()


def test_ingest_tpl_template_with_pages(fake_lib):
    fake_path, q = fake_lib
    tpl_dir = fake_path / "pptx-templates" / "items" / "demo_tpl"
    tpl_dir.mkdir()
    (tpl_dir / "meta.yaml").write_text(
        "id: demo_tpl\nname: Demo Template\ncategory: marketing\n"
        "content_intent: [a]\nkeywords: [b]\n"
        "visual_tokens: {primary: '#000'}\nvisual_signature: [c]\n"
        "implementation: {iLovePPT_can_replicate_pct: 50}\n",
        encoding="utf-8",
    )
    page_dir = tpl_dir / "pages" / "01-cover"
    page_dir.mkdir(parents=True)
    (page_dir / "meta.yaml").write_text(
        "id: demo_tpl__01-cover\nname: Cover\ncategory: cover\n"
        "layout_type: cover\npage_index: 1\n"
        "content_intent: [open]\nkeywords: [cover]\n"
        "native_elements: [accent]\ncopy_constraints: {title_max_chars: 22}\n",
        encoding="utf-8",
    )

    import embed_text as et
    db = q.open_db()
    full_id = et.ingest_tpl_template(db, tpl_dir, api_key="test")
    db.commit()

    assert full_id == "tpl:demo_tpl"
    t_row = db.execute("SELECT id, name, pages_count FROM tpl_templates WHERE id = ?", (full_id,)).fetchone()
    assert t_row[0] == "tpl:demo_tpl"
    assert t_row[1] == "Demo Template"
    assert t_row[2] == 1

    p_row = db.execute(
        "SELECT id, template_id, layout_type FROM tpl_pages WHERE template_id = ?", (full_id,)
    ).fetchone()
    assert p_row[0] == "tpl:demo_tpl__01-cover"
    assert p_row[1] == "tpl:demo_tpl"
    assert p_row[2] == "cover"
    db.close()


def test_ingest_rejects_double_underscore(fake_lib):
    fake_path, q = fake_lib
    bad_dir = fake_path / "pptx-templates" / "items" / "bad__name"
    bad_dir.mkdir()
    (bad_dir / "meta.yaml").write_text("id: bad__name\nname: x\n", encoding="utf-8")

    import embed_text as et
    db = q.open_db()
    with pytest.raises(ValueError, match=r"__"):
        et.ingest_tpl_template(db, bad_dir, api_key="test")
    db.close()
