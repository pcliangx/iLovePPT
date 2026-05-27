#!/usr/bin/env python3
"""扫指定 kb 的 preview.png → 计算 image embedding → 写 db.sqlite.image_emb。

用法跟 embed_text.py 一致(--kb / --id)。
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import yaml as _yaml

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from qwen_embedding import embed_image, get_api_key, open_db  # noqa: E402

LIBRARY_ROOT = SCRIPT_DIR.parent
VP_ROOT = LIBRARY_ROOT / "visual-patterns"
TPL_ROOT = LIBRARY_ROOT / "pptx-templates"


def _blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _should_skip_page(page_data: dict) -> bool:
    """跳过 iSlide 工具说明页(layout_type == 'other' AND needs_manual_review == true)。

    这类 page 的 keywords 含通用词(design criteria / template reference 等),
    embed 入库会污染 RAG 检索结果。
    """
    return (
        page_data.get("layout_type") == "other"
        and page_data.get("needs_manual_review") is True
    )


def _embed_one(db, item_id: str, preview: Path, api_key: str) -> bool:
    if not preview.exists():
        print(f"  skip(无 preview.png): {item_id}")
        return False
    vec = embed_image(preview, api_key=api_key)
    db.execute("DELETE FROM image_emb WHERE id = ?", (item_id,))
    db.execute("INSERT INTO image_emb(id, embedding) VALUES (?, ?)", (item_id, _blob(vec)))
    return True


def run(kb: str | None, target_id: str | None) -> None:
    api_key = get_api_key()
    db = open_db()
    done = 0

    if kb in (None, "visual-patterns"):
        vp_items = VP_ROOT / "items"
        if vp_items.exists():
            for d in sorted(vp_items.glob("*")):
                if not d.is_dir() or d.name.startswith(("_", ".")):
                    continue
                if target_id and d.name != target_id:
                    continue
                full_id = f"vp:{d.name}"
                print(f"[vp] {full_id}", flush=True)
                if _embed_one(db, full_id, d / "preview.png", api_key):
                    done += 1

    if kb in (None, "pptx-templates"):
        tpl_items = TPL_ROOT / "items"
        if tpl_items.exists():
            for tpl in sorted(tpl_items.glob("*")):
                if not tpl.is_dir() or tpl.name.startswith(("_", ".")):
                    continue
                if target_id and tpl.name != target_id:
                    continue
                tpl_id = f"tpl:{tpl.name}"
                print(f"[tpl] {tpl_id}", flush=True)
                if _embed_one(db, tpl_id, tpl / "preview.png", api_key):
                    done += 1
                pages = tpl / "pages"
                if pages.exists():
                    for pg in sorted(pages.glob("*/preview.png")):
                        page_dir = pg.parent
                        m = page_dir / "meta.yaml"
                        if not m.exists():
                            continue
                        pg_data = _yaml.safe_load(m.read_text(encoding="utf-8"))
                        pg_id = f"tpl:{pg_data['id']}"
                        if _should_skip_page(pg_data):
                            print(f"[tpl-page] SKIPPED (tool page): {pg_id}", flush=True)
                            # 清理已 embed 的旧数据(tpl_pages + text_emb + image_emb)
                            db.execute("DELETE FROM tpl_pages WHERE id = ?", (pg_id,))
                            db.execute("DELETE FROM text_emb WHERE id = ?", (pg_id,))
                            db.execute("DELETE FROM image_emb WHERE id = ?", (pg_id,))
                            continue
                        print(f"[tpl-page] {pg_id}", flush=True)
                        if _embed_one(db, pg_id, pg, api_key):
                            done += 1

    db.commit()
    db.close()
    print(f"done. {done} image(s) embedded.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb", choices=["visual-patterns", "pptx-templates"], default=None)
    p.add_argument("--id", default=None)
    args = p.parse_args()
    run(args.kb, args.id)


if __name__ == "__main__":
    main()
