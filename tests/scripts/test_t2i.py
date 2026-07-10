"""t2i · text-to-image 单元测试(mock API · 不打真请求)。

验证:① PNG + .source.yaml 都写;② size round 到 32 倍数;③ seed 透传 payload;④ 配置缺 raise。
"""
import base64
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import t2i  # noqa: E402


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def _fake_b64_png() -> str:
    # 1x1 transparent PNG 的 base64
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40).decode()


def test_generate_writes_png_and_source_yaml(tmp_path):
    out = tmp_path / "cover.png"
    body = json.dumps({"data": [{"b64_json": _fake_b64_png()}]}).encode()
    with patch("urllib.request.urlopen", return_value=_FakeResp(body)):
        t2i.generate(
            "封面主视觉:科技感深蓝", out,
            model="doubao-seedream", base="https://x/api/v3", key="k",
            seed=42, size="1280x720",
        )
    assert out.exists()                       # PNG 写了
    src = out.with_suffix(".source.yaml")
    assert src.exists()                        # source.yaml 写了(reproducibility 强制)
    txt = src.read_text(encoding="utf-8")
    assert "tool: t2i" in txt
    assert "doubao-seedream" in txt
    assert '"封面主视觉:科技感深蓝"' in txt
    assert "seed: 42" in txt


def test_size_rounded_to_32_multiple(tmp_path):
    out = tmp_path / "x.png"
    body = json.dumps({"data": [{"b64_json": _fake_b64_png()}]}).encode()
    captured = {}

    class _Capture(_FakeResp):
        pass

    def fake_urlopen(req, timeout=None):
        captured["size"] = json.loads(req.data)["size"]
        return _FakeResp(body)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        t2i.generate("p", out, model="m", base="https://x", key="k", size="1300x700")
    # 1300→1280(32*40), 700→672(32*21)
    assert captured["size"] == "1280x672"


def test_missing_config_raises(tmp_path):
    # 既不传参也不设 env → SystemExit
    import os
    saved = {k: os.environ.pop(k, None) for k in ("T2I_API_BASE", "T2I_API_KEY")}
    try:
        try:
            t2i.generate("p", tmp_path / "y.png")
            assert False, "应 raise SystemExit"
        except SystemExit:
            pass
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
