"""敏感数据脱敏 · P3-21 · query log / 任意 user-supplied 文本写入前过一遍。

支持模式:
- 邮箱:`zhangsan@acme.com` → `<email>`
- 中国手机号:`13812345678` → `<phone>`
- 美元金额(≥ 4 位数):`$10000` / `$1,234.56` → `<money_usd>`
- 人民币金额(≥ 4 位数):`¥10000` / `￥1,234.56` → `<money_cny>`

约束:
- 金额触发阈值是 4 位整数起跳(小钱 `$50` 不算敏感, 不脱敏)。
- 仅替换字面 token, 不动周围中文 / 标点。
- silent on 空 / None 输入(返回 '')。

通用 PII 脱敏 utility(原服务 RAG query log;现独立,见 docs/security/secrets-protection.md)。
"""

from __future__ import annotations

import re

# 邮箱 · `+` / `.` / `-` 都是合法 local-part 字符;TLD 1+ 字符
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# 中国手机号 · 1[3-9] 起头 11 位 + 前后非数字断言(允许 ASCII / 中文 / 边界,但不让一串更长数字被误吃)
PHONE_CN_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")

# 美元 · $ + 数字 + 可选 `,` 千分位 + 可选 `.` 小数;后置 assertion 检查总数字 ≥ 4 位 · 防止 $50 这种小钱被吃
# pattern: $ 后整数部分(允许逗号分组)+ 可选小数
_MONEY_NUM_GRP = r"\d{1,3}(?:,\d{3})+|\d+"  # 1,234 或 10000
MONEY_USD_RE = re.compile(rf"\$\s*({_MONEY_NUM_GRP})(?:\.\d+)?")

# 人民币 · ¥ / ￥(全角)+ 数字 + 可选千分位 / 小数。允许 `¥` 后空格(`¥ 50000`)
MONEY_CNY_RE = re.compile(rf"[¥￥]\s*({_MONEY_NUM_GRP})(?:\.\d+)?")


def _count_digits(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


def _redact_money(text: str, pattern: re.Pattern, placeholder: str) -> str:
    """匹配后看整数部分总位数,< 4 → 不脱敏(保留 `$50` / `¥30` 这种小钱)。"""
    def sub(m: re.Match) -> str:
        int_part = m.group(1) or ""
        if _count_digits(int_part) < 4:
            return m.group(0)
        return placeholder
    return pattern.sub(sub, text)


def redact(text: str | None) -> str:
    """把敏感 token 替换成 `<placeholder>`。

    替换顺序:email → phone → money_usd → money_cny。
    先 email/phone 防数字段被金额规则误吃;货币之间互不冲突(prefix 不同)。

    Args:
        text: 原文 · None / '' → 返回 ''

    Returns:
        脱敏后的字符串。
    """
    if not text:
        return ""
    text = EMAIL_RE.sub("<email>", text)
    text = PHONE_CN_RE.sub("<phone>", text)
    text = _redact_money(text, MONEY_USD_RE, "<money_usd>")
    text = _redact_money(text, MONEY_CNY_RE, "<money_cny>")
    return text


def redact_dict(d: dict, fields: list[str]) -> dict:
    """对 dict 中指定 string 字段做 redact, 不可变(返回新 dict)。

    list 字段不递归(仅 top-level string)。non-string 字段原样保留。

    Args:
        d: 原 dict
        fields: 需要 redact 的 key list

    Returns:
        新 dict(浅拷贝 + 指定字段脱敏)
    """
    out = dict(d)
    for k in fields:
        v = out.get(k)
        if isinstance(v, str):
            out[k] = redact(v)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(redact(" ".join(sys.argv[1:])))
    else:
        # demo
        sample = "张三 zhangsan@acme.com 13812345678 充值 ¥50000 找客户 $10000"
        print(f"原文: {sample}")
        print(f"脱敏: {redact(sample)}")
