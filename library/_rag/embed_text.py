#!/usr/bin/env python3
"""扫指定 kb 的 meta.yaml → 计算 text embedding(batch API)→ 写 db.sqlite。

用法:
    .venv/bin/python embed_text.py                              # 扫两个 kb
    .venv/bin/python embed_text.py --kb visual-patterns          # 只 vp
    .venv/bin/python embed_text.py --kb pptx-templates --id template_golden  # 单条入库

P1-6 改造:先 collect 所有 doc → batch API(8 条/请求)→ 写 DB。
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
    embed_text_batch,
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


def _collect_vp_tasks(items_dir: Path, target_id: str | None) -> list[dict]:
    """扫 vp items,收集 embed 任务。返回 [{full_id, text_doc, write_fn_args}, ...]。"""
    tasks: list[dict] = []
    if not items_dir.exists():
        return tasks
    for d in sorted(items_dir.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        if target_id and d.name != target_id:
            continue
        meta_path = d / "meta.yaml"
        if not meta_path.exists():
            continue
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        short_id = data["id"]
        full_id = f"vp:{short_id}"
        text_doc = build_text_doc_vp(data)
        rel_meta = meta_path.relative_to(LIBRARY_ROOT).as_posix()
        preview = d / "preview.png"
        rel_preview = preview.relative_to(LIBRARY_ROOT).as_posix() if preview.exists() else None
        tasks.append({
            "kind": "vp",
            "full_id": full_id,
            "text_doc": text_doc,
            "vp_row": (full_id, text_doc, rel_meta, rel_preview, data.get("category"), _now()),
        })
    return tasks


def _collect_tpl_tasks(items_dir: Path, target_id: str | None) -> list[dict]:
    """扫 tpl items,收集 template + page embed 任务。"""
    tasks: list[dict] = []
    if not items_dir.exists():
        return tasks
    for d in sorted(items_dir.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        if target_id and d.name != target_id:
            continue
        meta_path = d / "meta.yaml"
        if not meta_path.exists():
            continue
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        short_id = data["id"]
        if "__" in short_id:
            raise ValueError(f"模板名不能含 '__'(跟 page id 分隔符冲突): {short_id}")
        full_id = f"tpl:{short_id}"
        text_doc = build_text_doc_tpl_template(data)
        rel_meta = meta_path.relative_to(LIBRARY_ROOT).as_posix()
        rel_preview = None
        preview = d / "preview.png"
        if preview.exists():
            rel_preview = preview.relative_to(LIBRARY_ROOT).as_posix()

        pages_dir = d / "pages"
        pages_count = len(list(pages_dir.glob("*/meta.yaml"))) if pages_dir.exists() else 0
        source_pptx = LIBRARY_ROOT / "pptx-templates" / "_source" / f"{short_id}.pptx"
        source_rel = source_pptx.relative_to(LIBRARY_ROOT).as_posix() if source_pptx.exists() else None

        vt_json = _json.dumps(data.get("visual_tokens", {}), ensure_ascii=False)
        vs_text = "\n".join(data.get("visual_signature", []))
        keywords_text = ",".join(data.get("keywords", []))
        recommended_text = ",".join(data.get("recommended_for", []))
        iLovePPT_can_replicate = (data.get("implementation") or {}).get("iLovePPT_can_replicate_pct")

        tasks.append({
            "kind": "tpl_template",
            "full_id": full_id,
            "text_doc": text_doc,
            "tpl_row": (
                full_id, data.get("name"), data.get("desc"), data.get("category"),
                keywords_text, recommended_text, vt_json, vs_text, iLovePPT_can_replicate,
                source_rel, pages_count, rel_meta, rel_preview, text_doc, _now(),
            ),
            "pages_dir": pages_dir,
            "parent_id": full_id,
        })

        # 同时收页 task
        if pages_dir.exists():
            for page_meta in sorted(pages_dir.glob("*/meta.yaml")):
                page_data = yaml.safe_load(page_meta.read_text(encoding="utf-8"))
                page_full_id = f"tpl:{page_data['id']}"
                if _should_skip_page(page_data):
                    tasks.append({
                        "kind": "tpl_page_skip",
                        "full_id": page_full_id,
                    })
                    continue
                page_text = build_text_doc_tpl_page(page_data)
                rel_pmeta = page_meta.relative_to(LIBRARY_ROOT).as_posix()
                ppreview = page_meta.parent / "preview.png"
                rel_ppreview = ppreview.relative_to(LIBRARY_ROOT).as_posix() if ppreview.exists() else None
                extras = {
                    "native_elements": page_data.get("native_elements"),
                    "copy_constraints": page_data.get("copy_constraints"),
                    "iLovePPT_can_replicate_pct": page_data.get("iLovePPT_can_replicate_pct"),
                    "matches_iloveppt_layout": page_data.get("matches_iloveppt_layout"),
                }
                extras_json = _json.dumps({k: v for k, v in extras.items() if v is not None}, ensure_ascii=False)
                tasks.append({
                    "kind": "tpl_page",
                    "full_id": page_full_id,
                    "text_doc": page_text,
                    "page_row": (
                        page_full_id, full_id, page_data.get("layout_type"),
                        page_data.get("page_index"), page_text, rel_pmeta, rel_ppreview,
                        extras_json, _now(),
                    ),
                })
    return tasks


def _write_task(db, task: dict, vec: list[float] | None) -> None:
    """根据 task.kind 写 DB。vec=None 表示 skip(无需 embed)。"""
    if task["kind"] == "vp":
        db.execute(
            "INSERT OR REPLACE INTO vp_items(id, text_doc, meta_path, preview_path, category, updated_at) VALUES (?,?,?,?,?,?)",
            task["vp_row"],
        )
        db.execute("DELETE FROM text_emb WHERE id = ?", (task["full_id"],))
        db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (task["full_id"], _vec_blob(vec)))
    elif task["kind"] == "tpl_template":
        db.execute(
            """INSERT OR REPLACE INTO tpl_templates(
                id, name, desc, category, keywords, recommended_for,
                visual_tokens_json, visual_signature, iLovePPT_can_replicate_pct,
                source_pptx_path, pages_count, meta_path, preview_path, text_doc, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            task["tpl_row"],
        )
        db.execute("DELETE FROM text_emb WHERE id = ?", (task["full_id"],))
        db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (task["full_id"], _vec_blob(vec)))
    elif task["kind"] == "tpl_page":
        db.execute(
            """INSERT OR REPLACE INTO tpl_pages(
                id, template_id, layout_type, page_index, text_doc,
                meta_path, preview_path, extras_json, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?)""",
            task["page_row"],
        )
        db.execute("DELETE FROM text_emb WHERE id = ?", (task["full_id"],))
        db.execute("INSERT INTO text_emb(id, embedding) VALUES (?, ?)", (task["full_id"], _vec_blob(vec)))
    elif task["kind"] == "tpl_page_skip":
        print(f"[tpl-page] SKIPPED (tool page): {task['full_id']}", flush=True)
        db.execute("DELETE FROM tpl_pages WHERE id = ?", (task["full_id"],))
        db.execute("DELETE FROM text_emb WHERE id = ?", (task["full_id"],))
        db.execute("DELETE FROM image_emb WHERE id = ?", (task["full_id"],))


def run(kb: str | None, target_id: str | None) -> None:
    api_key = get_api_key()

    # Phase 1: 先扫文件系统收 task(不开 DB)
    tasks: list[dict] = []
    if kb in (None, "visual-patterns"):
        tasks.extend(_collect_vp_tasks(VP_ROOT / "items", target_id))
    if kb in (None, "pptx-templates"):
        tasks.extend(_collect_tpl_tasks(TPL_ROOT / "items", target_id))

    if not tasks:
        print("done. 0 item(s) embedded.")
        return

    # Phase 2: 批量 embed(不开 DB · API call 期间不占 DB 锁)
    embed_tasks = [t for t in tasks if t["kind"] != "tpl_page_skip"]
    texts = [t["text_doc"] for t in embed_tasks]
    print(f"[embed_text] batching {len(texts)} text(s) ...", flush=True)
    vecs = embed_text_batch(texts, api_key=api_key, batch_size=8)
    assert len(vecs) == len(embed_tasks), f"batch returned {len(vecs)} vs {len(embed_tasks)}"

    # Phase 3: 开 DB · 一次性写完 · 立即 close 释放锁
    #   parallel_embed.sh 让 text + image 两进程并行,把 DB 占用窗口压到最小
    db = open_db()
    vec_by_id = {t["full_id"]: v for t, v in zip(embed_tasks, vecs)}
    done = 0
    COMMIT_EVERY = 20
    try:
        for task in tasks:
            if task["kind"] == "tpl_page_skip":
                _write_task(db, task, None)
            else:
                vec = vec_by_id[task["full_id"]]
                _write_task(db, task, vec)
                kind = task["kind"]
                if kind == "vp":
                    print(f"[vp] {task['full_id']}", flush=True)
                elif kind == "tpl_template":
                    print(f"[tpl] {task['full_id']}", flush=True)
                done += 1
            if done % COMMIT_EVERY == 0:
                db.commit()
        db.commit()
    finally:
        db.close()
    print(f"done. {done} item(s) embedded (batch API).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb", choices=["visual-patterns", "pptx-templates"], default=None,
                   help="限定 kb;不传则扫两个")
    p.add_argument("--id", default=None, help="单 item 入库(visual-patterns: <id>; pptx-templates: <template-name>)")
    args = p.parse_args()
    run(args.kb, args.id)


if __name__ == "__main__":
    main()
