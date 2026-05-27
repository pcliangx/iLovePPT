"""测试 library/_rag/scripts/redact.py · 4 类敏感模式 + 边界 case。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAG_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "library" / "_rag" / "scripts"
sys.path.insert(0, str(RAG_SCRIPTS))

from redact import redact, redact_dict  # noqa: E402


# --- 单类型 case ---

def test_redact_email():
    assert redact("联系 zhangsan@acme.com 报价") == "联系 <email> 报价"
    assert redact("multiple a@b.cn 和 foo.bar+x@example.io") == "multiple <email> 和 <email>"


def test_redact_phone_cn():
    assert redact("电话 13812345678") == "电话 <phone>"
    # 1 开头但非 3-9 的运营段不命中(13/14/15/16/17/18/19 才是合法手机号段)
    assert redact("固话 02012345678") == "固话 02012345678"
    # 手机号嵌入中文里:\b 边界仍能匹配
    assert redact("电话13912345678紧急") == "电话<phone>紧急"


def test_redact_money_usd():
    assert redact("预算 $10000") == "预算 <money_usd>"
    assert redact("成本 $1,234.56 万") == "成本 <money_usd> 万"
    # 小钱不脱敏(< 4 位)
    assert redact("门票 $50") == "门票 $50"


def test_redact_money_cny():
    assert redact("充值 ¥50000") == "充值 <money_cny>"
    # 全角 ￥
    assert redact("收入 ￥123456") == "收入 <money_cny>"
    # 含空格也可
    assert redact("年费 ¥ 10000") == "年费 <money_cny>"
    # 小钱不脱敏
    assert redact("茶水 ¥30") == "茶水 ¥30"


# --- 组合 case ---

def test_redact_all_combined():
    src = "张三 zhangsan@acme.com 13812345678 充值 ¥50000 找客户"
    expected = "张三 <email> <phone> 充值 <money_cny> 找客户"
    assert redact(src) == expected


def test_redact_mixed_usd_and_cny():
    src = "美区 $99999 国区 ¥600000"
    assert redact(src) == "美区 <money_usd> 国区 <money_cny>"


# --- 边界 case ---

def test_redact_empty_and_none():
    assert redact("") == ""
    assert redact(None) == ""


def test_redact_no_sensitive_content():
    src = "完全干净的一段话 没有任何邮箱手机号"
    assert redact(src) == src


# --- dict helper ---

def test_redact_dict_basic():
    d = {"query": "找 zhangsan@acme.com", "ts": "2026-05-27", "n": 3}
    out = redact_dict(d, ["query"])
    assert out["query"] == "找 <email>"
    # 非指定字段不变
    assert out["ts"] == "2026-05-27"
    assert out["n"] == 3
    # 原 dict 不被改(浅拷贝)
    assert d["query"] == "找 zhangsan@acme.com"


def test_redact_dict_non_string_field_ignored():
    d = {"query": None, "expanded_query": 123, "ts": "2026-05-27"}
    out = redact_dict(d, ["query", "expanded_query", "ts"])
    assert out["query"] is None
    assert out["expanded_query"] == 123
    assert out["ts"] == "2026-05-27"
