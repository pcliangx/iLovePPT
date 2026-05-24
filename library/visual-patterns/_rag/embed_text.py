#!/usr/bin/env python3
"""扫 library/visual-patterns/patterns/ 全部 pattern.yaml,调阿里云 DashScope
多模态 embedding API(默认 tongyi-embedding-vision-plus-2026-03-06)生成文本
embedding 写入 patterns.sqlite 的 text_emb 表(FLOAT[EMBED_DIM=1152])。

用法:
    cd library/visual-patterns/_rag
    .venv/bin/python embed_text.py            # 全量重建(text_emb)
    .venv/bin/python embed_text.py --only <id>  # 只更新某 1 个 pattern

依赖:
    requirements.txt(sqlite-vec + pyyaml · 不需要 sentence-transformers / torch)
API key:
    DASHSCOPE_API_KEY env var,或 _rag/.env 文件(gitignored)
模型:
    .env 里 DASHSCOPE_EMBED_MODEL 配置(默认 tongyi-embedding-vision-plus-2026-03-06)

embed 的 document(给多模态 embedding API 的文本)= name + category + content_intent
+ when_to_use + keywords 拼成一行。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml 未装。.venv/bin/pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# 本地 lib(同目录)
sys.path.insert(0, str(Path(__file__).parent))
from qwen_embedding import build_text_doc, embed_text, get_api_key, open_db  # noqa: E402


PATTERNS_DIR = Path(__file__).parent.parent / "patterns"


def load_pattern(yaml_path: Path) -> dict | None:
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ✗ 解析失败 {yaml_path}: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"  ✗ {yaml_path} 不是合法 yaml dict", file=sys.stderr)
        return None
    if "id" not in data:
        print(f"  ✗ {yaml_path} 缺 id 字段", file=sys.stderr)
        return None
    return data


def main():
    parser = argparse.ArgumentParser(description="(Re)build TEXT embeddings via DashScope multimodal embedding API")
    parser.add_argument("--only", help="只更新某 1 个 pattern id(增量)")
    args = parser.parse_args()

    api_key = get_api_key()  # 验证 key 在 env 或 .env

    if not PATTERNS_DIR.exists():
        print(f"ERROR: patterns 目录不存在: {PATTERNS_DIR}", file=sys.stderr)
        sys.exit(1)

    yaml_files: list[Path] = []
    if args.only:
        candidate = PATTERNS_DIR / args.only / "pattern.yaml"
        if not candidate.exists():
            print(f"ERROR: {candidate} 不存在", file=sys.stderr)
            sys.exit(1)
        yaml_files = [candidate]
    else:
        yaml_files = sorted(PATTERNS_DIR.glob("*/pattern.yaml"))

    if not yaml_files:
        print(f"没有找到 pattern.yaml(查的:{PATTERNS_DIR}/*/pattern.yaml)")
        return

    db = open_db()
    now = datetime.now(timezone.utc).isoformat()

    count = 0
    for yp in yaml_files:
        p = load_pattern(yp)
        if not p:
            continue

        pid = p["id"]
        doc = build_text_doc(p)
        preview = yp.parent / "preview.png"

        try:
            vec = embed_text(doc, api_key=api_key)
        except RuntimeError as e:
            print(f"  ✗ {pid}: {e}", file=sys.stderr)
            continue

        import struct

        emb_blob = struct.pack(f"{len(vec)}f", *vec)
        db.execute(
            "INSERT OR REPLACE INTO patterns(id, text_doc, yaml_path, preview_path, category, updated_at) VALUES (?,?,?,?,?,?)",
            (pid, doc, str(yp), str(preview), p.get("category", ""), now),
        )
        db.execute(
            "INSERT OR REPLACE INTO text_emb(id, embedding) VALUES (?, ?)",
            (pid, emb_blob),
        )
        count += 1
        print(f"  ✓ {pid}  ←  {doc[:80]}{'...' if len(doc) > 80 else ''}")

    db.commit()
    db.close()
    print(f"\n完成 · embed {count} 个 pattern (text) → patterns.sqlite")


if __name__ == "__main__":
    main()
