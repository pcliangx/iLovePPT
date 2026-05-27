#!/usr/bin/env python3
"""扫指定 kb 的 meta.yaml → 计算 text embedding → 写 db.sqlite。

用法:
    .venv/bin/python embed_text.py                              # 扫两个 kb
    .venv/bin/python embed_text.py --kb visual-patterns          # 只 vp
    .venv/bin/python embed_text.py --kb pptx-templates --id template_golden  # 单条入库
"""

from __future__ import annotations

import argparse
import json as _json
import struct
import sys
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from qwen_embedding import (  # noqa: E402
    build_text_doc_tpl_page,
    build_text_doc_tpl_template,
    build_text_doc_vp,
    embed_text,
    get_api_key,
    open_db,
)

LIBRARY_ROOT = SCRIPT_DIR.parent
VP_ROOT = LIBRARY_ROOT / "visual-patterns"
TPL_ROOT = LIBRARY_ROOT / "pptx-templates"


def _vec_blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _should_skip_page(page_data: dict) -> bool:
    """跳过 iSlide 工具说明页(layout_type == 'other' AND needs_manual_review == true)。

    这类 page 的 keywords 含通用词(design criteria / template reference 等),
    embed 入库会污染 RAG 检索结果。
    """
    return (
        page_data.get("layout_type") == "other"
        and page_data.get("needs_manual_review") is True
    )


def ingest_vp_item(db, item_dir: Path, api_key: str) -> str:
    meta_path = item_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    short_id = data["id"]
    full_id = f"vp:{short_id}"
    text_doc = build_text_doc_vp(data)
    vec = embed_text(text_doc, api_key=api_key)
    rel_meta = meta_path.relative_to(LIBRARY_ROOT).as_posix()
    preview = item_dir / "preview.png"
    rel_preview = preview.relative_to(LIBRARY_ROOT).as_posix() if preview.exists() else None

    db.execute(
        "INSERT OR REPLACE INTO vp_items(id, text_doc, meta_path, preview_path, category, updated_at) VALUES (?,?,?,?,?,?)",
        (full_id, text_doc, rel_meta, rel_preview, data.get("category"), _now()),
    )
    db.execute("DELETE FROM text_emb WHERE id = ?", (full_id,))
    db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (full_id, _vec_blob(vec)))
    return full_id


def ingest_tpl_template(db, item_dir: Path, api_key: str) -> str:
    meta_path = item_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    short_id = data["id"]
    if "__" in short_id:
        raise ValueError(f"模板名不能含 '__'(跟 page id 分隔符冲突): {short_id}")
    full_id = f"tpl:{short_id}"
    text_doc = build_text_doc_tpl_template(data)
    vec = embed_text(text_doc, api_key=api_key)
    rel_meta = meta_path.relative_to(LIBRARY_ROOT).as_posix()
    rel_preview = None
    preview = item_dir / "preview.png"
    if preview.exists():
        rel_preview = preview.relative_to(LIBRARY_ROOT).as_posix()

    pages_dir = item_dir / "pages"
    pages_count = len(list(pages_dir.glob("*/meta.yaml"))) if pages_dir.exists() else 0
    source_pptx = LIBRARY_ROOT / "pptx-templates" / "_source" / f"{short_id}.pptx"
    source_rel = source_pptx.relative_to(LIBRARY_ROOT).as_posix() if source_pptx.exists() else None

    vt_json = _json.dumps(data.get("visual_tokens", {}), ensure_ascii=False)
    vs_text = "\n".join(data.get("visual_signature", []))
    keywords_text = ",".join(data.get("keywords", []))
    recommended_text = ",".join(data.get("recommended_for", []))
    iLovePPT_can_replicate = (data.get("implementation") or {}).get("iLovePPT_can_replicate_pct")

    db.execute(
        """INSERT OR REPLACE INTO tpl_templates(
            id, name, desc, category, keywords, recommended_for,
            visual_tokens_json, visual_signature, iLovePPT_can_replicate_pct,
            source_pptx_path, pages_count, meta_path, preview_path, text_doc, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            full_id, data.get("name"), data.get("desc"), data.get("category"),
            keywords_text, recommended_text, vt_json, vs_text, iLovePPT_can_replicate,
            source_rel, pages_count, rel_meta, rel_preview, text_doc, _now(),
        ),
    )
    db.execute("DELETE FROM text_emb WHERE id = ?", (full_id,))
    db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (full_id, _vec_blob(vec)))

    if pages_dir.exists():
        for page_meta in sorted(pages_dir.glob("*/meta.yaml")):
            page_data = yaml.safe_load(page_meta.read_text(encoding="utf-8"))
            page_full_id = f"tpl:{page_data['id']}"
            if _should_skip_page(page_data):
                print(f"[tpl-page] SKIPPED (tool page): {page_full_id}", flush=True)
                # 清理已 embed 的旧数据(tpl_pages + text_emb + image_emb)
                db.execute("DELETE FROM tpl_pages WHERE id = ?", (page_full_id,))
                db.execute("DELETE FROM text_emb WHERE id = ?", (page_full_id,))
                db.execute("DELETE FROM image_emb WHERE id = ?", (page_full_id,))
                continue
            ingest_tpl_page(db, page_meta.parent, parent_id=full_id, api_key=api_key)
    return full_id


def ingest_tpl_page(db, page_dir: Path, parent_id: str, api_key: str) -> str:
    meta_path = page_dir / "meta.yaml"
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    short_id = data["id"]
    full_id = f"tpl:{short_id}"
    text_doc = build_text_doc_tpl_page(data)
    vec = embed_text(text_doc, api_key=api_key)
    rel_meta = meta_path.relative_to(LIBRARY_ROOT).as_posix()
    preview = page_dir / "preview.png"
    rel_preview = preview.relative_to(LIBRARY_ROOT).as_posix() if preview.exists() else None

    extras = {
        "native_elements": data.get("native_elements"),
        "copy_constraints": data.get("copy_constraints"),
        "iLovePPT_can_replicate_pct": data.get("iLovePPT_can_replicate_pct"),
        "matches_iloveppt_layout": data.get("matches_iloveppt_layout"),
    }
    extras_json = _json.dumps({k: v for k, v in extras.items() if v is not None}, ensure_ascii=False)

    db.execute(
        """INSERT OR REPLACE INTO tpl_pages(
            id, template_id, layout_type, page_index, text_doc,
            meta_path, preview_path, extras_json, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            full_id, parent_id, data.get("layout_type"), data.get("page_index"),
            text_doc, rel_meta, rel_preview, extras_json, _now(),
        ),
    )
    db.execute("DELETE FROM text_emb WHERE id = ?", (full_id,))
    db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (full_id, _vec_blob(vec)))
    return full_id


def run(kb: str | None, target_id: str | None) -> None:
    api_key = get_api_key()
    db = open_db()
    done = 0

    if kb in (None, "visual-patterns"):
        items_dir = VP_ROOT / "items"
        if items_dir.exists():
            for d in sorted(items_dir.iterdir()):
                if not d.is_dir() or d.name.startswith(("_", ".")):
                    continue
                if target_id and d.name != target_id:
                    continue
                print(f"[vp] {d.name} ...", flush=True)
                ingest_vp_item(db, d, api_key)
                done += 1

    if kb in (None, "pptx-templates"):
        items_dir = TPL_ROOT / "items"
        if items_dir.exists():
            for d in sorted(items_dir.iterdir()):
                if not d.is_dir() or d.name.startswith(("_", ".")):
                    continue
                if target_id and d.name != target_id:
                    continue
                print(f"[tpl] {d.name} ...", flush=True)
                ingest_tpl_template(db, d, api_key)
                done += 1

    db.commit()
    db.close()
    print(f"done. {done} item(s) embedded.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb", choices=["visual-patterns", "pptx-templates"], default=None,
                   help="限定 kb;不传则扫两个")
    p.add_argument("--id", default=None, help="单 item 入库(visual-patterns: <id>; pptx-templates: <template-name>)")
    args = p.parse_args()
    run(args.kb, args.id)


if __name__ == "__main__":
    main()
