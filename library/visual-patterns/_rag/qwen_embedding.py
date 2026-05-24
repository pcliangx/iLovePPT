"""DashScope tongyi-embedding-vision-plus 客户端封装 + sqlite-vec DB schema。

embed_text.py / embed_image.py / search.py 共用此 lib。

API:
    POST https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding
    Body: {"model": "tongyi-embedding-vision-plus-2026-03-06",
           "input": {"contents": [{"text": "..."} | {"image": "<url|data uri>"}]}}
    Returns: {"output": {"embeddings": [{"embedding": [float...]}]}, "usage": {...}}

Embedding dim: 1152(tongyi-embedding-vision-plus-2026-03-06,text 与 image 同维)

Image 输入支持:
    1. 公网 URL:{"image": "https://..."}
    2. 本地 PNG 转 base64 data URI:{"image": "data:image/png;base64,<...>"}

Schema(sqlite-vec):
    patterns       · id (PK) · text_doc · yaml_path · preview_path · category · updated_at
    text_emb       · id (PK,vec0) · embedding FLOAT[1152]
    image_emb      · id (PK,vec0) · embedding FLOAT[1152]

(文件名 qwen_embedding.py 保留以避免 cross-file import 重写;实际默认模型是
通义 tongyi-embedding-vision-plus,跟 Qwen 同属阿里通义系列,可通过 .env 切换。)
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EMBED_DIM = 1152
API_URL = os.environ.get(
    "DASHSCOPE_API_URL",
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding",
)
MODEL = os.environ.get("DASHSCOPE_EMBED_MODEL", "tongyi-embedding-vision-plus-2026-03-06")

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"
DB_PATH = SCRIPT_DIR / "patterns.sqlite"


def load_env() -> None:
    """读 _rag/.env 文件,把变量塞进 os.environ(若未已设)。"""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


def get_api_key() -> str:
    load_env()
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: DASHSCOPE_API_KEY 未设置。\n"
            f"  配置方式 1:写入 {ENV_FILE} (DASHSCOPE_API_KEY=sk-...)\n"
            "  配置方式 2:export DASHSCOPE_API_KEY=sk-...",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _post_json(payload: dict, api_key: str, timeout: int = 30) -> dict:
    req = Request(
        url=API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from DashScope: {body}") from e
    except URLError as e:
        raise RuntimeError(f"network error to DashScope: {e}") from e


def embed_text(text: str, *, api_key: str | None = None, retry: int = 3) -> list[float]:
    """调用多模态 embedding API embed 一段文本,返回 EMBED_DIM 维向量(默认 1152)。"""
    api_key = api_key or get_api_key()
    payload = {"model": MODEL, "input": {"contents": [{"text": text}]}}
    last_err = None
    for attempt in range(retry):
        try:
            r = _post_json(payload, api_key)
            return r["output"]["embeddings"][0]["embedding"]
        except RuntimeError as e:
            last_err = e
            if attempt < retry - 1:
                time.sleep(2**attempt)  # 1s, 2s
    raise RuntimeError(f"embed_text failed after {retry} retries: {last_err}")


def embed_image(image_path: Path | str, *, api_key: str | None = None, retry: int = 3) -> list[float]:
    """调用多模态 embedding API embed 一张图像,返回 EMBED_DIM 维向量(默认 1152)。

    image_path 可为本地路径(自动 base64)或公网 URL(以 http:// / https:// 开头)。
    """
    api_key = api_key or get_api_key()
    if isinstance(image_path, Path) or not str(image_path).startswith(("http://", "https://")):
        # local file → base64 data URI
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"image not found: {path}")
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        image_arg = f"data:{mime};base64,{b64}"
    else:
        image_arg = str(image_path)

    payload = {"model": MODEL, "input": {"contents": [{"image": image_arg}]}}
    last_err = None
    for attempt in range(retry):
        try:
            r = _post_json(payload, api_key)
            return r["output"]["embeddings"][0]["embedding"]
        except RuntimeError as e:
            last_err = e
            if attempt < retry - 1:
                time.sleep(2**attempt)
    raise RuntimeError(f"embed_image failed after {retry} retries: {last_err}")


def open_db() -> sqlite3.Connection:
    """打开 sqlite-vec DB,创建 schema 若不存在。"""
    try:
        import sqlite_vec
    except ImportError:
        print(
            "ERROR: sqlite-vec 未装。\n"
            "  cd library/visual-patterns/_rag && .venv/bin/pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.execute(
        """CREATE TABLE IF NOT EXISTS patterns (
            id TEXT PRIMARY KEY,
            text_doc TEXT,
            yaml_path TEXT,
            preview_path TEXT,
            category TEXT,
            updated_at TEXT
        )"""
    )
    db.execute(
        f"""CREATE VIRTUAL TABLE IF NOT EXISTS text_emb USING vec0(
            id TEXT PRIMARY KEY,
            embedding FLOAT[{EMBED_DIM}]
        )"""
    )
    db.execute(
        f"""CREATE VIRTUAL TABLE IF NOT EXISTS image_emb USING vec0(
            id TEXT PRIMARY KEY,
            embedding FLOAT[{EMBED_DIM}]
        )"""
    )
    return db


def build_text_doc(p: dict) -> str:
    """把 pattern.yaml 关键字段拼成 embed 用的 document。

    通义/Qwen 系列多模态 embedding 对中文 + 关键词敏感,重复关键概念是好事(不是 noise)。
    """
    parts: list[str] = []
    if name := p.get("name"):
        parts.append(name)
    if category := p.get("category"):
        parts.append(f"类别 {category}")
    for intent in p.get("content_intent", []):
        parts.append(intent)
    for w in p.get("when_to_use", []):
        parts.append(f"适用 {w}")
    for kw in p.get("keywords", []):
        parts.append(kw)
    return " · ".join(parts)
