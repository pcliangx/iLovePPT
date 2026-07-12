#!/usr/bin/env python3
"""scripts/fix_ea_fonts.py — .pptx 产物端 EA 字体修复(html 高视觉轨 gate 配套)。

为什么存在:仓库 #1 不变量是"中文必须写 `<a:ea>`+`<a:cs>`",pptx 轨由
helpers.set_font 写侧保证;但 html 轨走 vendored html2pptx(pptxgenjs 单值
fontFace,只写 `<a:latin>`,且 vendored 代码不许改)—— 产物会系统性带着
latin-only 经典 bug。本脚本在**产物端**修:对每个含 CJK 文本、写了
`<a:latin>` 却缺 `<a:ea>` 的 run,插入 `<a:ea>` + `<a:cs>`。

ea 字体选择:
- `<a:latin>` 本身是 CJK 字体名(YaHei / PingFang / Source Han / 黑体 等,
  html2pptx CDP 检测常把真实渲染的中文字体写进 latin)→ ea 复用 latin
- 否则用 --font(默认 Microsoft YaHei,项目默认中文字体)

用法:
  python3 scripts/fix_ea_fonts.py deck.pptx                 # 原地修(自动备份 .pre_ea_fix.pptx)
  python3 scripts/fix_ea_fonts.py deck.pptx --output out.pptx
  python3 scripts/fix_ea_fonts.py deck.pptx --font "Source Han Sans CN"

Exit code:0 完成(stdout 报修复数,0 处可修也是 0);2 用法 / 文件错误。
配合读侧复检:`python3 scripts/audit_pptx.py <out> --sections fonts`(应 0 ERROR)。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
DEFAULT_FONT = "Microsoft YaHei"

# CJK 统一表意文字(与 audit_pptx.py HAN_RE 一致)
HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

# latin 槽里出现这些名字 → 本身就是 CJK 字体,ea 直接复用
CJK_FONT_NAME_RE = re.compile(
    r"(yahei|pingfang|heiti|simhei|simsun|songti|kaiti|mingliu|"
    r"source han|noto sans cjk|noto serif cjk|dengxian|fangsong|"
    r"微软|苹方|黑体|宋体|楷体|华文|思源)",
    re.IGNORECASE,
)


def _q(local: str) -> str:
    return f"{{{A_NS}}}{local}"


def fix_slide_xml(xml_bytes: bytes, fallback_font: str) -> tuple[bytes, int]:
    """修一页 slide XML,返回 (新 bytes, 修复 run 数)。无可修时原样返回。"""
    root = etree.fromstring(xml_bytes)
    fixed = 0
    for run in root.iter(_q("r")):
        t = run.find(_q("t"))
        text = (t.text or "") if t is not None else ""
        if not HAN_RE.search(text):
            continue
        rpr = run.find(_q("rPr"))
        if rpr is None:
            continue  # 无 rPr 走继承链,audit 归 INFO/WARNING,不属于 latin-only bug
        latin = rpr.find(_q("latin"))
        if latin is None:
            continue
        ea = rpr.find(_q("ea"))
        if ea is not None and (ea.get("typeface") or "").strip():
            continue  # 已有非空 <a:ea>,无需修
        latin_face = latin.get("typeface") or ""
        ea_face = latin_face if CJK_FONT_NAME_RE.search(latin_face) else fallback_font
        if ea is None:
            # schema 顺序:latin → ea → cs(插在 latin 之后合法)
            ea = etree.Element(_q("ea"))
            latin.addnext(ea)
        # 空 typeface="" 的 <a:ea> 与缺元素等价(audit 同判 ERROR),一并补
        ea.set("typeface", ea_face)
        cs = rpr.find(_q("cs"))
        if cs is None:
            cs = etree.Element(_q("cs"))
            ea.addnext(cs)
        if not (cs.get("typeface") or "").strip():
            cs.set("typeface", ea_face)
        fixed += 1
    if not fixed:
        return xml_bytes, 0
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                          standalone=True), fixed


def fix_pptx(src: Path, dst: Path, fallback_font: str = DEFAULT_FONT) -> dict[str, int]:
    """src → dst 全量重写 zip,slide XML 逐页修。返回 {slide part: 修复数}(仅含 >0 的)。"""
    stats: dict[str, int] = {}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(
            dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", info.filename):
                data, n = fix_slide_xml(data, fallback_font)
                if n:
                    stats[info.filename] = n
            zout.writestr(info, data)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=".pptx 产物端 EA 字体修复(latin-only CJK run 补 <a:ea>+<a:cs>)")
    parser.add_argument("pptx", help=".pptx 文件路径")
    parser.add_argument("--output", help="另存路径(默认原地修,改前备份 .pre_ea_fix.pptx)")
    parser.add_argument("--font", default=DEFAULT_FONT,
                        help=f"ea 回落字体(默认 {DEFAULT_FONT};latin 本身是 CJK 字体名时复用 latin)")
    args = parser.parse_args(argv)

    src = Path(args.pptx)
    if not src.is_file():
        print(f"文件不存在: {src}", file=sys.stderr)
        return 2
    try:
        zipfile.ZipFile(src).close()
    except zipfile.BadZipFile:
        print(f"不是合法 .pptx(zip 打不开): {src}", file=sys.stderr)
        return 2

    if args.output:
        dst = Path(args.output)
        stats = fix_pptx(src, dst, args.font)
    else:
        backup = src.with_suffix(".pre_ea_fix.pptx")
        shutil.copy2(src, backup)
        tmp = src.with_suffix(".ea_fix_tmp.pptx")
        stats = fix_pptx(backup, tmp, args.font)
        tmp.replace(src)
        dst = src
        print(f"备份: {backup}")

    total = sum(stats.values())
    print(f"修复 {total} 个 latin-only CJK run → {dst}")
    for part, n in sorted(stats.items()):
        print(f"  {part}: {n}")
    if total:
        print(f"复检: python3 scripts/audit_pptx.py {dst} --sections fonts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
