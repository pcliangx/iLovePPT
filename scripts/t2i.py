#!/usr/bin/env python3
"""t2i · text-to-image(OpenAI-compatible `images.generate`)。

服务 **html / lark-whiteboard / lark-slides** 三轨封面 / 主视觉(iloveppt-designer 调)。
默认 doubao-seedream(Volcengine Ark),任意 OpenAI-compatible images endpoint 都行。

**Reproducibility 强制**:每张图跟同名 `.source.yaml` 记 prompt + model + seed + ts + size + api_base。
缺 source.yaml = bug(audience source-fidelity 会拦;"只有 PNG 等于让用户重画")。

配置(env):
  T2I_MODEL=doubao-seedream-4-5-251128
  T2I_API_BASE=https://ark.cn-beijing.volces.com/api/v3
  T2I_API_KEY=<key>

CLI:
  t2i.py "封面主视觉:科技感深蓝渐变 + 抽象网络节点" --out slides/cover.png [--seed 42] [--size 1280x720]

Exit:0 ok · 2 配置缺 / API HTTP error。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PIXEL_MULTIPLE = 32  # 多数 t2i 模型要求边长是 32 的倍数


def _parse_size(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def _round_to_multiple(n: int, m: int = PIXEL_MULTIPLE) -> int:
    return max(m, (n // m) * m)


def generate(
    prompt: str,
    out: Path,
    *,
    model: str | None = None,
    base: str | None = None,
    key: str | None = None,
    seed: int | None = None,
    size: str = "1280x720",
) -> Path:
    """调 t2i API → 写 PNG + 同名 .source.yaml。返回 PNG path。"""
    model = model or os.environ.get("T2I_MODEL") or "doubao-seedream-4-5-251128"
    base = (base or os.environ.get("T2I_API_BASE") or "").rstrip("/")
    key = key or os.environ.get("T2I_API_KEY")
    if not base or not key:
        raise SystemExit(
            "t2i: T2I_API_BASE / T2I_API_KEY 未配(export 后重跑;t2i 是 html/lark 轨封面主视觉可选增强)"
        )
    w, h = (_round_to_multiple(n) for n in _parse_size(size))
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "size": f"{w}x{h}",
        "response_format": "b64_json",
    }
    if seed is not None:
        payload["seed"] = int(seed)

    req = urllib.request.Request(
        f"{base}/images/generations",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        raise SystemExit(f"t2i: API HTTP {e.code}: {body}") from e

    b64 = resp["data"][0].get("b64_json") or ""
    if not b64:
        raise SystemExit(f"t2i: API 返回无 b64_json: {json.dumps(resp)[:300]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))

    # reproducibility 强制:同名 .source.yaml
    src = out.with_suffix(".source.yaml")
    seed_repr = seed if seed is not None else "null  # nondeterministic · 复现需显式 --seed"
    src.write_text(
        "# t2i reproducibility · 自动生成(t2i.py),勿手改\n"
        f"tool: t2i\n"
        f"model: {model}\n"
        f"prompt: {json.dumps(prompt, ensure_ascii=False)}\n"
        f"seed: {seed_repr}\n"
        f"size: {w}x{h}\n"
        f"ts: {int(time.time())}\n"
        f"api_base: {base}\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({w}x{h}) + {src}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="t2i text-to-image (OpenAI-compatible images.generate)")
    ap.add_argument("prompt", help="画面描述")
    ap.add_argument("--out", required=True, help="输出 PNG 路径(同名 .source.yaml 自动写)")
    ap.add_argument("--seed", type=int, help="seed(复现用;不传 = nondeterministic)")
    ap.add_argument("--size", default="1280x720", help="尺寸 WxH(自动 round 到 32 倍数)")
    ap.add_argument("--model", help="override T2I_MODEL")
    ap.add_argument("--base", help="override T2I_API_BASE")
    ap.add_argument("--key", help="override T2I_API_KEY")
    a = ap.parse_args()
    generate(a.prompt, Path(a.out), model=a.model, base=a.base, key=a.key, seed=a.seed, size=a.size)


if __name__ == "__main__":
    main()
