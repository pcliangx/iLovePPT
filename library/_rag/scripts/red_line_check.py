#!/usr/bin/env python3
"""red_line_words 检查 · rapidfuzz 模糊匹配 + 拼音 fallback · P1-10。

现状 red_line_words grep 是 exact match,绕过套路:
  - 半角 / 全角:大概 / 大　概
  - 同义词 / 近形字:大概 / 大慨
  - 拼音:dagai

本脚本三层兜底:
  1. exact substring
  2. fuzzy(rapidfuzz · sliding window · ratio ≥ threshold)
  3. pinyin(pypinyin · normalize 后子串)

用法:
    red_line_check.py --content content.md --red-lines "大概,估计,大约" --format text
    red_line_check.py --content content.md --red-lines red_lines.txt --threshold 85 --format json

exit code:
    0  无命中
    2  有命中(便于 hook / CI)
    1  脚本错误(依赖缺失 / 文件读不到)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print("ERROR: rapidfuzz 未装。\n  library/_rag/.venv/bin/pip install rapidfuzz pypinyin",
          file=sys.stderr)
    sys.exit(1)

try:
    from pypinyin import pinyin, Style
except ImportError:
    print("ERROR: pypinyin 未装。\n  library/_rag/.venv/bin/pip install rapidfuzz pypinyin",
          file=sys.stderr)
    sys.exit(1)


def _to_pinyin(s: str) -> str:
    """中文 → 不带声调拼音(逐字连写),英文/数字保留原样。"""
    if not s:
        return ""
    out: list[str] = []
    for chunk in pinyin(s, style=Style.NORMAL, errors="default"):
        out.append(chunk[0] if chunk else "")
    return "".join(out).lower()


def check(content_path: str, red_lines: list[str], fuzzy_threshold: int = 85) -> list[dict]:
    """三层检查 · 返回命中列表 [{kind, matched, red_line, ratio, context}]。"""
    text = Path(content_path).read_text(encoding="utf-8")
    text_pinyin = _to_pinyin(text)
    hits: list[dict] = []
    seen: set[tuple[str, str, str]] = set()  # (kind, red_line, matched_first20) 去重

    for rl in red_lines:
        rl = rl.strip()
        if not rl:
            continue

        # === 1. exact ===
        if rl in text:
            idx = text.find(rl)
            ctx = text[max(0, idx - 20): idx + len(rl) + 20].replace("\n", "↵")
            key = ("exact", rl, rl)
            if key not in seen:
                seen.add(key)
                hits.append({
                    "kind": "exact",
                    "matched": rl,
                    "red_line": rl,
                    "ratio": 100,
                    "context": ctx,
                })
            continue  # exact 命中就别再 fuzzy / pinyin 兜底了

        # === 2. fuzzy(sliding window)===
        rl_len = len(rl)
        win = max(rl_len * 2, rl_len + 4)
        windows = []
        step = max(1, rl_len // 2)
        for i in range(0, max(1, len(text) - win + 1), step):
            windows.append((i, text[i:i + win]))
        if windows:
            choices = [w[1] for w in windows]
            best = process.extractOne(
                rl, choices, scorer=fuzz.partial_ratio, score_cutoff=fuzzy_threshold
            )
            if best:
                matched_chunk = best[0]
                ratio = int(best[1])
                # 找到原始 idx
                widx = choices.index(matched_chunk)
                orig_idx = windows[widx][0]
                ctx = text[max(0, orig_idx - 10): orig_idx + win + 10].replace("\n", "↵")
                preview = matched_chunk.strip()[:30]
                key = ("fuzzy", rl, preview)
                if key not in seen:
                    seen.add(key)
                    hits.append({
                        "kind": "fuzzy",
                        "matched": preview + ("..." if len(matched_chunk) > 30 else ""),
                        "red_line": rl,
                        "ratio": ratio,
                        "context": ctx,
                    })

        # === 3. pinyin ===
        rl_py = _to_pinyin(rl)
        if rl_py and len(rl_py) >= 2 and rl_py in text_pinyin:
            key = ("pinyin", rl, rl_py)
            if key not in seen:
                seen.add(key)
                hits.append({
                    "kind": "pinyin",
                    "matched": f"[pinyin:{rl_py}]",
                    "red_line": rl,
                    "ratio": 100,
                    "context": "(pinyin substring match)",
                })

    return hits


def main() -> int:
    p = argparse.ArgumentParser(
        description="red_line_words check · exact + fuzzy + pinyin"
    )
    p.add_argument("--content", required=True, help="待检查的 .md / .txt 文件")
    p.add_argument(
        "--red-lines",
        required=True,
        help="逗号分隔列表 或 文件路径(一行一词)",
    )
    p.add_argument("--threshold", type=int, default=85, help="fuzzy ratio 阈值(默认 85)")
    p.add_argument("--format", default="text", choices=["json", "text"])
    args = p.parse_args()

    content_path = Path(args.content)
    if not content_path.exists():
        print(f"ERROR: content 文件不存在: {content_path}", file=sys.stderr)
        return 1

    rl_arg = Path(args.red_lines)
    if rl_arg.exists():
        red_lines = [l.strip() for l in rl_arg.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    else:
        red_lines = [w.strip() for w in args.red_lines.split(",") if w.strip()]

    if not red_lines:
        print("WARN: 红线词列表为空", file=sys.stderr)
        return 0

    hits = check(args.content, red_lines, args.threshold)

    if args.format == "json":
        print(json.dumps(hits, indent=2, ensure_ascii=False))
    else:
        if not hits:
            print("[red_line_check] OK · 无命中")
        else:
            print(f"[red_line_check] 命中 {len(hits)} 处:")
            for h in hits:
                print(f"  [{h['kind']:6}] {h['ratio']:3}%  '{h['red_line']}' → '{h['matched']}'")
                if h.get("context") and h["kind"] != "pinyin":
                    print(f"            ctx: ...{h['context']}...")

    return 2 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
