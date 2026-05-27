"""DashScope tongyi-embedding-vision-plus 客户端封装 + sqlite-vec DB schema。

embed_text.py / embed_image.py / search.py 共用此 lib。

Schema:
    vp_items       · visual-patterns 的 items(扁平)
    tpl_templates  · pptx-templates 的模板管理表
    tpl_pages      · pptx-templates 的页表
    text_emb       · 跨 kb 共享文本向量(id 前缀 vp: / tpl: 区分来源)
    image_emb      · 跨 kb 共享图像向量

API:
    POST https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding
    EMBED_DIM = 1152(text/image 同维)
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
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
DB_PATH = SCRIPT_DIR / "db.sqlite"


def load_env() -> None:
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
            f"  方式 1: 写入 {ENV_FILE} (DASHSCOPE_API_KEY=sk-...)\n"
            "  方式 2: export DASHSCOPE_API_KEY=sk-...",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _post_json(payload: dict, api_key: str, timeout: int = 30) -> dict:
    req = Request(
        url=API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from DashScope: {body}") from e
    except URLError as e:
        raise RuntimeError(f"network error: {e}") from e


def embed_text(text: str, *, api_key: str | None = None, retry: int = 3) -> list[float]:
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
                time.sleep(2**attempt)
    raise RuntimeError(f"embed_text failed after {retry} retries: {last_err}")


def _image_to_arg(image_path: Path | str) -> str:
    """把 image path 转成 API 接受的 data URL 或直接 URL。"""
    if isinstance(image_path, Path) or not str(image_path).startswith(("http://", "https://")):
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"image not found: {path}")
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"
    return str(image_path)


def embed_image(image_path: Path | str, *, api_key: str | None = None, retry: int = 3) -> list[float]:
    api_key = api_key or get_api_key()
    image_arg = _image_to_arg(image_path)

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


def _embed_batch_request(
    contents: list[dict], *, api_key: str, retry: int = 3
) -> list[list[float]]:
    """单次 batch API 调用,返回 contents 顺序对应的 embedding 列表。

    DashScope tongyi-embedding-vision-plus 支持 contents 内多 item batch,
    返回 output.embeddings[i].embedding(i 跟 contents 顺序对齐)。
    """
    payload = {"model": MODEL, "input": {"contents": contents}}
    last_err = None
    for attempt in range(retry):
        try:
            r = _post_json(payload, api_key, timeout=60)
            embs = r["output"]["embeddings"]
            # API 可能不保序,按 text_index 排;若没有该字段则按返回顺序
            if embs and "text_index" in embs[0]:
                embs = sorted(embs, key=lambda x: x.get("text_index", 0))
            elif embs and "index" in embs[0]:
                embs = sorted(embs, key=lambda x: x.get("index", 0))
            return [e["embedding"] for e in embs]
        except RuntimeError as e:
            last_err = e
            if attempt < retry - 1:
                time.sleep(2**attempt)
    raise RuntimeError(f"_embed_batch_request failed after {retry} retries: {last_err}")


def embed_text_batch(
    texts: list[str],
    *,
    api_key: str | None = None,
    batch_size: int = 8,
    retry: int = 3,
) -> list[list[float]]:
    """批量计算 text embedding,返回 [embedding, ...] 顺序对齐 texts。

    阿里云 tongyi-embedding-vision-plus 单请求上限按 contents 长度切分(默认 8)。
    若 batch 整个失败 → fallback 退化为单 item 重试(保证可用,只是退化为串行)。
    """
    api_key = api_key or get_api_key()
    if not texts:
        return []
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        contents = [{"text": t} for t in chunk]
        try:
            embs = _embed_batch_request(contents, api_key=api_key, retry=retry)
            if len(embs) != len(chunk):
                raise RuntimeError(
                    f"batch returned {len(embs)} embeddings, expected {len(chunk)}"
                )
            out.extend(embs)
        except RuntimeError as e:
            # batch 失败 → fallback 单条
            print(f"[embed_text_batch] batch {i}-{i+len(chunk)} failed: {e}; fallback single", flush=True)
            for t in chunk:
                out.append(embed_text(t, api_key=api_key, retry=retry))
    return out


def embed_image_batch(
    image_paths: list[Path | str],
    *,
    api_key: str | None = None,
    batch_size: int = 4,
    retry: int = 3,
) -> list[list[float]]:
    """批量计算 image embedding,返回 [embedding, ...] 顺序对齐 image_paths。

    image batch_size 默认更小(base64 payload 大),实测 4 是稳妥值。
    """
    api_key = api_key or get_api_key()
    if not image_paths:
        return []
    out: list[list[float]] = []
    for i in range(0, len(image_paths), batch_size):
        chunk = image_paths[i : i + batch_size]
        contents = [{"image": _image_to_arg(p)} for p in chunk]
        try:
            embs = _embed_batch_request(contents, api_key=api_key, retry=retry)
            if len(embs) != len(chunk):
                raise RuntimeError(
                    f"batch returned {len(embs)} embeddings, expected {len(chunk)}"
                )
            out.extend(embs)
        except RuntimeError as e:
            print(f"[embed_image_batch] batch {i}-{i+len(chunk)} failed: {e}; fallback single", flush=True)
            for p in chunk:
                out.append(embed_image(p, api_key=api_key, retry=retry))
    return out


def open_db(db_path: Path | None = None) -> sqlite3.Connection:
    """打开 sqlite-vec DB, 创建 schema 若不存在。"""
    try:
        import sqlite_vec
    except ImportError:
        print(
            "ERROR: sqlite-vec 未装。\n"
            "  cd library/_rag && .venv/bin/pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    db = sqlite3.connect(db_path or DB_PATH, timeout=30)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    # P3-6 · WAL mode + busy_timeout 防 parallel 锁
    # parallel_embed.sh 让 text + image 两进程同时写 db.sqlite,WAL 才能多 reader / 单 writer 并发
    # · journal_mode=WAL · 写不阻塞读;运行时生成 db.sqlite-wal / db.sqlite-shm 辅助文件
    # · busy_timeout=10000 · 元数据写撞锁时等 10s 再报(大多场景 < 10s 写完)
    # · synchronous=NORMAL · WAL 模式下 NORMAL 跟 FULL 持久性差不多但快
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA synchronous=NORMAL")

    # 1. visual-patterns items(扁平)
    db.execute(
        """CREATE TABLE IF NOT EXISTS vp_items (
            id TEXT PRIMARY KEY,
            text_doc TEXT,
            meta_path TEXT,
            preview_path TEXT,
            category TEXT,
            updated_at TEXT
        )"""
    )

    # 2. pptx-templates 模板管理表
    db.execute(
        """CREATE TABLE IF NOT EXISTS tpl_templates (
            id TEXT PRIMARY KEY,
            name TEXT,
            desc TEXT,
            category TEXT,
            keywords TEXT,
            recommended_for TEXT,
            visual_tokens_json TEXT,
            visual_signature TEXT,
            iLovePPT_can_replicate_pct INTEGER,
            source_pptx_path TEXT,
            pages_count INTEGER,
            meta_path TEXT,
            preview_path TEXT,
            text_doc TEXT,
            updated_at TEXT
        )"""
    )

    # 3. pptx-templates 页表
    db.execute(
        """CREATE TABLE IF NOT EXISTS tpl_pages (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            layout_type TEXT,
            page_index INTEGER,
            text_doc TEXT,
            meta_path TEXT,
            preview_path TEXT,
            extras_json TEXT,
            updated_at TEXT
        )"""
    )

    # 4-5. 共享向量表
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
    db.commit()
    return db


def build_text_doc_vp(p: dict) -> str:
    """visual-patterns item 的 text_doc 拼接。"""
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


def build_text_doc_tpl_template(p: dict) -> str:
    """pptx-templates 模板级 text_doc · 自然语言拼接,提升 embedding 上下文增益。"""
    name = p.get("name", "")
    desc = p.get("desc", "")
    category = p.get("category", "")
    sentences: list[str] = []
    if name:
        head = name + ("。" + desc if desc else "")
        sentences.append(head)
    if category:
        sentences.append(f"这是一套 {category} 类别的 PPT 模板。")
    if intents := p.get("content_intent", []):
        sentences.append("适合内容包括:" + "、".join(intents) + "。")
    if whens := p.get("when_to_use", []):
        sentences.append("适用场景:" + "、".join(whens) + "。")
    if sigs := p.get("visual_signature", []):
        sentences.append("视觉特征:" + "、".join(sigs) + "。")
    if recs := p.get("recommended_for", []):
        sentences.append("推荐受众或场景:" + "、".join(recs) + "。")
    if kws := p.get("keywords", []):
        sentences.append("关键词:" + "、".join(kws) + "。")
    return " ".join(sentences)


def build_text_doc_tpl_page(p: dict) -> str:
    """pptx-templates 页级 text_doc · 自然语言拼接。

    variant 字段(P1-1)与 layout_type 同级拼到 head,提升 RAG separation —
    e.g. cards-3-icon vs cards-4-photo 可区分。
    """
    name = p.get("name", "")
    lt = p.get("layout_type", "")
    variant = p.get("variant", "")
    sentences: list[str] = []
    head_bits = []
    if name:
        head_bits.append(name)
    if lt:
        head_bits.append(f"layout 类型为 {lt}")
    if variant:
        head_bits.append(f"variant 为 {variant}")
    if head_bits:
        sentences.append("。".join(head_bits) + "。")
    if cat := p.get("category"):
        sentences.append(f"分类:{cat}。")
    if intents := p.get("content_intent", []):
        sentences.append("适合内容:" + "、".join(intents) + "。")
    if whens := p.get("when_to_use", []):
        sentences.append("适用场景:" + "、".join(whens) + "。")
    if els := p.get("native_elements", []):
        sentences.append("页面元素:" + "、".join(els) + "。")
    if kws := p.get("keywords", []):
        sentences.append("关键词:" + "、".join(kws) + "。")
    return " ".join(sentences)
