#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""scripts/check_source_fidelity.py — 源材料 claim 级保真校验(确定性 · 不调 LLM)。

为什么存在:数据驱动 deck(财报 / 销售分析)最致命的失败是**关键数字丢失或落错章节页**。
此前只有 audience LLM 评分(主观),无逐条机械核对。本脚本借鉴 mavis pptx skill 的
Source Content Verification:claims 清单逐条 → 在 deck 文本里找 → 核对落位页。

分工:claims 清单由人/LLM 起草一次(author Stage D 产出 `deck_v{N}_claims.yaml`,
来自 brief 的已确认数据口径);本脚本做**确定性核对**(audience Step 0.0.5 调用)。

claims yaml schema:
    claims:
      - id: q1_revenue                # 必填 · 唯一
        desc: "Q1 营收 1.2 亿元"       # 人读说明
        patterns: ["1.2亿", "120,000,000"]   # 任一命中即 found(归一化子串匹配)
        regex: "营收[^\\n]{0,10}1\\.2"  # 可选 · 与 patterns 并存(any-of · 对原文匹配)
        expect_pages: [5, 6]          # 可选 · 章号口径(content.md `## N`)·
                                      # 命中页与之有交集才算落位正确(仅 .md 输入判定)
        required: true                # 默认 true · false 时缺失不导致 fail

归一化规则:NFKC(全角→半角)→ 去空白/千分位逗号/顿号 → casefold。
"１２０,０００" 与 "120000" 因此互相命中。

deck 输入二选一(⚠️ 两者页号口径不同):
  *.pptx        每页文本 = slide XML 全部 <a:t>(含表格),页号 = slide 物理序号
                (含 cover/toc/divider,与 content.md 章号**不**1:1);因此 .pptx
                输入只判 missing,expect_pages 落位(misplaced)判定自动跳过
  *content.md   按 `## N.` 标题切页,页号 = 章号 N —— claims 的 expect_pages
                按此口径写,落位判定仅在 content.md 输入下生效
报告 summary.page_basis 标注本次口径:chapter(.md)| slide(.pptx)

Exit code: 0 全部 required claim found 且落位正确;1 有 missing / misplaced;2 用法错误

用法:
  python3 scripts/check_source_fidelity.py builder/deck_v1.pptx --claims author/deck_v1_claims.yaml
  python3 scripts/check_source_fidelity.py author/deck_v1_content.md --claims author/deck_v1_claims.yaml --format text
也可 `uv run scripts/check_source_fidelity.py ...`(PEP 723 自带 pyyaml)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import yaml

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_STRIP_RE = re.compile(r"[\s,，、]+")


@dataclass
class Claim:
    id: str
    desc: str = ""
    patterns: list[str] = field(default_factory=list)
    regex: str | None = None
    expect_pages: list[int] = field(default_factory=list)
    required: bool = True


def normalize(s: str) -> str:
    """NFKC 全半角归一 → 去空白/千分位逗号/顿号 → casefold"""
    return _STRIP_RE.sub("", unicodedata.normalize("NFKC", s)).casefold()


def load_claims(path: str | Path) -> list[Claim]:
    """加载 + 校验 claims yaml。schema 不合规 fail-loud(ValueError)。"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError(f"{path}: 顶层必须是 dict 且含 claims list")
    claims: list[Claim] = []
    seen: set[str] = set()
    for i, raw in enumerate(data["claims"]):
        if not isinstance(raw, dict) or not raw.get("id"):
            raise ValueError(f"{path}: claims[{i}] 缺 id")
        cid = str(raw["id"])
        if cid in seen:
            raise ValueError(f"{path}: claims id 重复 {cid!r}")
        seen.add(cid)
        patterns = [str(p) for p in (raw.get("patterns") or []) if str(p).strip()]
        regex = raw.get("regex") or None
        if not patterns and not regex:
            raise ValueError(f"{path}: claims[{cid}] patterns / regex 至少给一个")
        if regex:
            try:
                re.compile(regex)
            except re.error as e:
                raise ValueError(f"{path}: claims[{cid}] regex 非法: {e}") from e
        expect_pages = [int(p) for p in (raw.get("expect_pages") or [])]
        claims.append(Claim(
            id=cid,
            desc=str(raw.get("desc", "")),
            patterns=patterns,
            regex=regex,
            expect_pages=expect_pages,
            required=bool(raw.get("required", True)),
        ))
    return claims


# ---- deck 文本提取 ---------------------------------------------------------

def _pages_from_pptx(path: Path) -> dict[int, str]:
    pages: dict[int, str] = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            m = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
            if not m:
                continue
            root = ET.fromstring(zf.read(name))
            texts = [t.text or "" for t in root.iter(f"{{{A_NS}}}t")]
            pages[int(m.group(1))] = "\n".join(texts)
    return dict(sorted(pages.items()))


# 与 derive_plan.py CHAPTER_HEADING_RE / compute_chapter_hashes.py 同一切页
# 正则(`## N.` 严格形式),三处须同步 —— 否则同一 content.md 切页不一致
_MD_HEADING_RE = re.compile(r"^##\s+(\d+)\.\s+", re.MULTILINE)


def _pages_from_md(path: Path) -> dict[int, str]:
    """content.md 按 `## N.` 标题切页(repo 约定:每个 ## N. 是一个内容页)"""
    text = path.read_text(encoding="utf-8")
    matches = list(_MD_HEADING_RE.finditer(text))
    pages: dict[int, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        pages[int(m.group(1))] = text[m.start():end]
    return pages


def extract_pages(path: str | Path) -> dict[int, str]:
    p = Path(path)
    if p.suffix.lower() == ".pptx":
        return _pages_from_pptx(p)
    if p.suffix.lower() == ".md":
        pages = _pages_from_md(p)
        if not pages:
            raise ValueError(f"{p}: 没解析出任何 `## N.` 页(不是 content.md 格式?)")
        return pages
    raise ValueError(f"{p}: 只支持 .pptx / .md 输入")


# ---- 核对 ------------------------------------------------------------------

def check_claims(claims: list[Claim], pages: dict[int, str],
                 *, page_basis: str = "chapter") -> dict[str, Any]:
    """page_basis: "chapter"(content.md 章号,expect_pages 同口径)|
    "slide"(.pptx 物理序号,与 expect_pages 章号口径不同 → 跳过 misplaced 判定,
    只判 missing)。"""
    norm_pages = {n: normalize(t) for n, t in pages.items()}
    results: list[dict[str, Any]] = []
    n_missing = n_misplaced = n_pass = 0
    fail = False
    for c in claims:
        hit_pages = sorted(
            n for n in pages
            if any(normalize(p) in norm_pages[n] for p in c.patterns)
            or (c.regex and re.search(c.regex, pages[n]))
        )
        if not hit_pages:
            status = "missing"
            n_missing += 1
        elif (page_basis == "chapter" and c.expect_pages
              and not set(hit_pages) & set(c.expect_pages)):
            status = "misplaced"
            n_misplaced += 1
        else:
            status = "pass"
            n_pass += 1
        if status != "pass" and c.required:
            fail = True
        results.append({
            "id": c.id,
            "desc": c.desc,
            "status": status,
            "required": c.required,
            "hit_pages": hit_pages,
            "expect_pages": c.expect_pages,
        })
    return {
        "summary": {
            "total": len(claims),
            "pass": n_pass,
            "missing": n_missing,
            "misplaced": n_misplaced,
            "pages_scanned": len(pages),
            "page_basis": page_basis,
            "verdict": "fail" if fail else "pass",
        },
        "claims": results,
    }


def _render_text(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        f"verdict={s['verdict']}  total={s['total']} pass={s['pass']} "
        f"missing={s['missing']} misplaced={s['misplaced']}  "
        f"(pages={s['pages_scanned']} basis={s.get('page_basis', 'chapter')})"
    ]
    if s.get("page_basis") == "slide":
        lines.append("  note: .pptx 输入页号=slide 物理序号,与 expect_pages 章号"
                     "口径不同,misplaced 判定已跳过(只判 missing)")
    for r in report["claims"]:
        mark = {"pass": "✓", "missing": "✗ MISSING", "misplaced": "✗ MISPLACED"}[r["status"]]
        opt = "" if r["required"] else " (optional)"
        exp = f" expect={r['expect_pages']}" if r["expect_pages"] else ""
        lines.append(f"  {mark:<12} {r['id']}{opt}: {r['desc']}  hit={r['hit_pages']}{exp}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="源材料 claim 级保真校验(数字逐条核对 + 落位检查)")
    parser.add_argument("deck", help="deck_v{N}.pptx 或 deck_v{N}_content.md")
    parser.add_argument("--claims", required=True, help="claims yaml 路径")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)

    try:
        claims = load_claims(args.claims)
        pages = extract_pages(args.deck)
    except (OSError, ValueError, zipfile.BadZipFile, yaml.YAMLError) as e:
        print(f"输入错误: {e}", file=sys.stderr)
        return 2

    basis = "slide" if Path(args.deck).suffix.lower() == ".pptx" else "chapter"
    report = check_claims(claims, pages, page_basis=basis)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json"
          else _render_text(report))
    return 0 if report["summary"]["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
