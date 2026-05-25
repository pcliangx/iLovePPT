"""验证 search.py router · preferred-template 优先 + fallback 行为。"""

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

if importlib.util.find_spec("sqlite_vec") is None or importlib.util.find_spec("yaml") is None:
    pytest.skip("sqlite-vec / pyyaml 未装。用 library/_rag/.venv/bin/python 跑", allow_module_level=True)

LIB_DIR = Path(__file__).resolve().parent.parent.parent / "library"
RAG_DIR = LIB_DIR / "_rag"
sys.path.insert(0, str(LIB_DIR))
sys.path.insert(0, str(RAG_DIR))


@pytest.fixture
def db_with_fixtures(tmp_path, monkeypatch):
    import qwen_embedding as q
    monkeypatch.setattr(q, "DB_PATH", tmp_path / "test.sqlite")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    db = q.open_db()

    def vec(a, b, c):
        v = [0.0] * q.EMBED_DIM
        v[0], v[1], v[2] = a, b, c
        norm = sum(x * x for x in v) ** 0.5
        return [x / norm if norm else 0.0 for x in v]

    items = [
        ("vp:item-near",   "process item near query",  vec(1.0, 0.1, 0.0), "vp_items"),
        ("vp:item-far",    "unrelated noise",          vec(0.0, 0.0, 1.0), "vp_items"),
        ("tpl:template_golden__01-cover", "cover golden", vec(0.9, 0.2, 0.0), "tpl_pages"),
        ("tpl:template_golden__02-toc",   "toc golden",   vec(0.85, 0.25, 0.0), "tpl_pages"),
        ("tpl:template_golden", "golden template",      vec(0.95, 0.15, 0.0), "tpl_templates"),
    ]

    for id_, doc, v, table in items:
        if table == "vp_items":
            db.execute(
                "INSERT INTO vp_items(id, text_doc, category) VALUES (?,?,?)",
                (id_, doc, "process"),
            )
        elif table == "tpl_pages":
            db.execute(
                "INSERT INTO tpl_pages(id, template_id, layout_type, page_index, text_doc) VALUES (?,?,?,?,?)",
                (id_, "tpl:template_golden", "cover", 1, doc),
            )
        elif table == "tpl_templates":
            db.execute(
                "INSERT INTO tpl_templates(id, name, category, source_pptx_path, pages_count, text_doc) VALUES (?,?,?,?,?,?)",
                (id_, "golden", "enterprise-modern", "pptx-templates/_source/template_golden.pptx", 2, doc),
            )
        blob = struct.pack(f"{len(v)}f", *v)
        db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (id_, blob))
    db.commit()
    yield db, q
    db.close()


def _patch_embed(monkeypatch, query_vec):
    """让 embed_text 返回固定 query 向量。"""
    import qwen_embedding as q
    monkeypatch.setattr(q, "embed_text", lambda text, **kw: query_vec)
    monkeypatch.setattr(q, "embed_image", lambda p, **kw: query_vec)
    import search as s
    monkeypatch.setattr(s, "embed_text", lambda text, **kw: query_vec)
    monkeypatch.setattr(s, "embed_image", lambda p, **kw: query_vec)


def test_search_all_returns_mixed(db_with_fixtures, monkeypatch):
    db, q = db_with_fixtures
    v = [0.0] * q.EMBED_DIM
    v[0] = 1.0
    _patch_embed(monkeypatch, v)
    import search as s
    results = s.search(
        query="x", query_image=None, kb="all", type_="any",
        category=None, preferred_template=None, top_k=5,
        fallback_threshold=0.55, mode="text",
    )
    ids = [r["id"] for r in results]
    assert "vp:item-near" in ids
    assert "tpl:template_golden__01-cover" in ids


def test_preferred_template_returns_pages(db_with_fixtures, monkeypatch):
    db, q = db_with_fixtures
    v = [0.0] * q.EMBED_DIM
    v[0] = 1.0
    _patch_embed(monkeypatch, v)
    import search as s
    results = s.search(
        query="x", query_image=None, kb="all", type_="any",
        category=None, preferred_template="template_golden", top_k=2,
        fallback_threshold=0.0, mode="text",
    )
    ids = [r["id"] for r in results]
    for r in results:
        assert r["source"] == "preferred-template"
        assert r["parent_id"] == "tpl:template_golden"
    assert "tpl:template_golden__01-cover" in ids


def test_fallback_when_score_low(db_with_fixtures, monkeypatch):
    """阈值 0.99 强制触发 fallback,vp items 应出现。"""
    db, q = db_with_fixtures
    v = [0.0] * q.EMBED_DIM
    v[0] = 1.0
    _patch_embed(monkeypatch, v)
    import search as s
    results = s.search(
        query="x", query_image=None, kb="all", type_="any",
        category=None, preferred_template="template_golden", top_k=5,
        fallback_threshold=0.99, mode="text",
    )
    sources = {r["source"] for r in results}
    assert "visual-patterns" in sources


def test_type_filter_page_only(db_with_fixtures, monkeypatch):
    db, q = db_with_fixtures
    v = [0.0] * q.EMBED_DIM
    v[0] = 1.0
    _patch_embed(monkeypatch, v)
    import search as s
    results = s.search(
        query="x", query_image=None, kb="pptx-templates", type_="page",
        category=None, preferred_template=None, top_k=5,
        fallback_threshold=0.55, mode="text",
    )
    for r in results:
        assert r["row_type"] == "tpl_page"
