#!/usr/bin/env python3
"""跨 kb 检索 router · 唯一入口。

用法:
    library/search.sh --query "..."                                          # 全 kb 搜
    library/search.sh --query "..." --kb visual-patterns                     # 限 vp
    library/search.sh --query "..." --kb pptx-templates --type page          # 限 tpl 页
    library/search.sh --query "..." --preferred-template template_golden     # 优先该模板 · fallback vp

行为:
    若有 --preferred-template:
        1. 在 tpl_pages 查, parent=tpl:<name>
        2. 命中 ≥ top-k 且平均分 ≥ threshold → 直接返回
        3. 否则:fallback 到 visual-patterns + 合并 top-k
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "_rag"))
from qwen_embedding import embed_image, embed_text, get_api_key, open_db  # noqa: E402

DEFAULT_FALLBACK_THRESHOLD = 0.55
DEFAULT_TOP_K = 5


def _blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _query_table(db, kb_table: str, emb_table: str, q_blob: bytes, where: str, params: tuple, k: int):
    """通用表查询. kb_table ∈ {vp_items, tpl_templates, tpl_pages}, emb_table ∈ {text_emb, image_emb}."""
    sql = f"""SELECT k.id, k.text_doc, k.meta_path, k.preview_path,
                 {'k.category' if kb_table != 'tpl_pages' else 'k.layout_type'} AS cat,
                 {'NULL' if kb_table != 'tpl_pages' else 'k.template_id'} AS parent_id,
                 vec_distance_cosine(e.embedding, ?) AS distance
              FROM {kb_table} k JOIN {emb_table} e ON k.id = e.id
              {where}
              ORDER BY distance ASC
              LIMIT ?"""
    return db.execute(sql, (q_blob,) + params + (k,)).fetchall()


def _row_dict(r: tuple, row_type: str) -> dict:
    return {
        "id": r[0],
        "row_type": row_type,
        "category_or_layout": r[4] or "",
        "parent_id": r[5],
        "score": round(1 - r[6], 4),
        "distance": round(r[6], 4),
        "preview_path": r[3] or "",
        "meta_path": r[2] or "",
        "doc_preview": (r[1] or "")[:120] + ("..." if r[1] and len(r[1]) > 120 else ""),
    }


def search(
    query: str | None,
    query_image: str | None,
    kb: str,
    type_: str,
    category: str | None,
    preferred_template: str | None,
    top_k: int,
    fallback_threshold: float,
    mode: str,
    text_weight: float = 0.6,
    image_weight: float = 0.4,
) -> list[dict]:
    api_key = get_api_key()
    db = open_db()

    if query_image:
        q_vec = embed_image(query_image, api_key=api_key)
    elif query:
        q_vec = embed_text(query, api_key=api_key)
    else:
        raise ValueError("必须 --query 或 --query-image")
    q_blob = _blob(q_vec)

    emb_table = "image_emb" if mode == "image" else "text_emb"
    if mode == "hybrid":
        emb_table = "text_emb"

    pref_id = f"tpl:{preferred_template}" if preferred_template else None

    def _do_query(target_kb: str, target_type: str, filter_parent: str | None, k: int):
        out: list[dict] = []
        if target_kb in ("all", "visual-patterns") and target_type in ("any", "item"):
            where = "WHERE 1=1"
            params: tuple = ()
            if category:
                where += " AND k.category = ?"
                params = params + (category,)
            for r in _query_table(db, "vp_items", emb_table, q_blob, where, params, k):
                out.append(_row_dict(r, "vp_item"))
        if target_kb in ("all", "pptx-templates") and target_type in ("any", "template"):
            where = "WHERE 1=1"
            params = ()
            if category:
                where += " AND k.category = ?"
                params = params + (category,)
            for r in _query_table(db, "tpl_templates", emb_table, q_blob, where, params, k):
                out.append(_row_dict(r, "tpl_template"))
        if target_kb in ("all", "pptx-templates") and target_type in ("any", "page"):
            where = "WHERE 1=1"
            params = ()
            if filter_parent:
                where += " AND k.template_id = ?"
                params = params + (filter_parent,)
            if category:
                where += " AND k.layout_type = ?"
                params = params + (category,)
            for r in _query_table(db, "tpl_pages", emb_table, q_blob, where, params, k):
                out.append(_row_dict(r, "tpl_page"))
        return out

    if pref_id:
        primary = _do_query("pptx-templates", "page", pref_id, top_k)
        primary.sort(key=lambda x: x["distance"])
        for r in primary:
            r["source"] = "preferred-template"
        avg_score = (sum(r["score"] for r in primary) / len(primary)) if primary else 0.0
        if len(primary) >= top_k and avg_score >= fallback_threshold:
            db.close()
            return primary[:top_k]
        fallback = _do_query("visual-patterns", "item", None, top_k)
        for r in fallback:
            r["source"] = "visual-patterns"
        combined = primary + fallback
        combined.sort(key=lambda x: x["distance"])
        seen = set()
        deduped: list[dict] = []
        for r in combined:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            deduped.append(r)
        db.close()
        return deduped[:top_k]
    else:
        out = _do_query(kb, type_, None, top_k * 3)
        out.sort(key=lambda x: x["distance"])
        for r in out:
            r["source"] = "preferred-template" if r["row_type"].startswith("tpl_") else "visual-patterns"
        db.close()
        return out[:top_k]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query")
    p.add_argument("--query-image")
    p.add_argument("--mode", default="text", choices=["text", "image", "hybrid"])
    p.add_argument("--kb", default="all", choices=["visual-patterns", "pptx-templates", "all"])
    p.add_argument("--type", dest="type_", default="any", choices=["item", "template", "page", "any"])
    p.add_argument("--category", default=None)
    p.add_argument("--preferred-template", default=None)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument("--fallback-threshold", type=float, default=DEFAULT_FALLBACK_THRESHOLD)
    p.add_argument("--format", default="json", choices=["json", "text"])
    args = p.parse_args()

    if not args.query and not args.query_image:
        p.error("必须提供 --query 或 --query-image")

    results = search(
        query=args.query,
        query_image=args.query_image,
        kb=args.kb,
        type_=args.type_,
        category=args.category,
        preferred_template=args.preferred_template,
        top_k=args.top_k,
        fallback_threshold=args.fallback_threshold,
        mode=args.mode,
    )

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            src = r.get("source", "?")
            print(f"{r['score']:.3f}  [{src:>20}] [{r['row_type']:<12}] {r['id']:<50}")
            print(f"          {r['doc_preview']}")


if __name__ == "__main__":
    main()
