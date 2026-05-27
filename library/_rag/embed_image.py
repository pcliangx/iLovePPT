#!/usr/bin/env python3
"""扫指定 kb 的 preview.png → 计算 image embedding(batch API)→ 写 db.sqlite.image_emb。

用法跟 embed_text.py 一致(--kb / --id)。

P1-6 改造:先 collect 所有 preview path → batch API(4 张/请求)→ 写 DB。
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import yaml as _yaml

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from qwen_embedding import embed_image_batch, get_api_key, open_db  # noqa: E402

LIBRARY_ROOT = SCRIPT_DIR.parent
VP_ROOT = LIBRARY_ROOT / "visual-patterns"
TPL_ROOT = LIBRARY_ROOT / "pptx-templates"


def _blob(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _should_skip_page(page_data: dict) -> bool:
    """跳过 iSlide 工具说明页(layout_type == 'other' AND needs_manual_review == true)。"""
    return (
        page_data.get("layout_type") == "other"
        and page_data.get("needs_manual_review") is True
    )


def _collect_tasks(kb: str | None, target_id: str | None) -> tuple[list[dict], list[dict]]:
    """收集 embed tasks + skip tasks。

    Returns:
        embed_tasks: [{full_id, preview_path}, ...]
        skip_tasks:  [{full_id}, ...]
    """
    embed_tasks: list[dict] = []
    skip_tasks: list[dict] = []

    if kb in (None, "visual-patterns"):
        vp_items = VP_ROOT / "items"
        if vp_items.exists():
            for d in sorted(vp_items.glob("*")):
                if not d.is_dir() or d.name.startswith(("_", ".")):
                    continue
                if target_id and d.name != target_id:
                    continue
                full_id = f"vp:{d.name}"
                preview = d / "preview.png"
                if not preview.exists():
                    print(f"  skip(无 preview.png): {full_id}")
                    continue
                embed_tasks.append({"full_id": full_id, "preview_path": preview})

    if kb in (None, "pptx-templates"):
        tpl_items = TPL_ROOT / "items"
        if tpl_items.exists():
            for tpl in sorted(tpl_items.glob("*")):
                if not tpl.is_dir() or tpl.name.startswith(("_", ".")):
                    continue
                if target_id and tpl.name != target_id:
                    continue
                tpl_id = f"tpl:{tpl.name}"
                preview = tpl / "preview.png"
                if preview.exists():
                    embed_tasks.append({"full_id": tpl_id, "preview_path": preview})
                else:
                    print(f"  skip(无 preview.png): {tpl_id}")

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
                            skip_tasks.append({"full_id": pg_id})
                            continue
                        embed_tasks.append({"full_id": pg_id, "preview_path": pg})
    return embed_tasks, skip_tasks


def run(kb: str | None, target_id: str | None) -> None:
    api_key = get_api_key()
    db = open_db()

    embed_tasks, skip_tasks = _collect_tasks(kb, target_id)

    # 处理 skip
    for st in skip_tasks:
        print(f"[tpl-page] SKIPPED (tool page): {st['full_id']}", flush=True)
        db.execute("DELETE FROM tpl_pages WHERE id = ?", (st["full_id"],))
        db.execute("DELETE FROM text_emb WHERE id = ?", (st["full_id"],))
        db.execute("DELETE FROM image_emb WHERE id = ?", (st["full_id"],))

    if not embed_tasks:
        db.commit()
        db.close()
        print("done. 0 image(s) embedded.")
        return

    paths = [t["preview_path"] for t in embed_tasks]
    print(f"[embed_image] batching {len(paths)} image(s) ...", flush=True)
    vecs = embed_image_batch(paths, api_key=api_key, batch_size=4)
    assert len(vecs) == len(embed_tasks), f"batch returned {len(vecs)} vs {len(embed_tasks)}"

    done = 0
    COMMIT_EVERY = 20
    for task, vec in zip(embed_tasks, vecs):
        full_id = task["full_id"]
        db.execute("DELETE FROM image_emb WHERE id = ?", (full_id,))
        db.execute("INSERT INTO image_emb(id, embedding) VALUES (?, ?)", (full_id, _blob(vec)))
        done += 1
        # 简化输出:只 print 大类
        if full_id.startswith("vp:") or "__" not in full_id.split(":")[1]:
            print(f"[{full_id}]", flush=True)
        if done % COMMIT_EVERY == 0:
            db.commit()

    db.commit()
    db.close()
    print(f"done. {done} image(s) embedded (batch API).")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb", choices=["visual-patterns", "pptx-templates"], default=None)
    p.add_argument("--id", default=None)
    args = p.parse_args()
    run(args.kb, args.id)


if __name__ == "__main__":
    main()
