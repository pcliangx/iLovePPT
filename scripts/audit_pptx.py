#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""scripts/audit_pptx.py — 读侧 .pptx 机械审计(纯 stdlib · 不调 LLM)。

为什么存在:CLAUDE.md 把"中文 run 缺 `<a:ea>` → 跨平台 fallback 丑字体"列为 #1 产物破损源,
但此前仓库只有**写侧**保证(helpers.set_font / _fix_ph_font)+ 人工抽 5 页 grep。
本脚本补**读侧全量校验**:扫描产出 .pptx 里每个含 CJK 文本的 run,机械判定 ea 字体状态。
设计参考 mavis pptx skill 的 audit_pptx.py(7-section 结构化 JSON 审计),按本仓库不变量重写。

Sections(--sections csv · 默认只跑 fonts):
  fonts       EA 字体审计 —— 唯一影响 exit code 的 section(builder Step 2.9 gate 用)
  shapes      每页 shape 清单(位置 / 尺寸 / 文字预览 / placeholder)
  hyperlinks  超链接清单(外链 URL / 内部 action)
  embedded    嵌入对象 + 媒体清单(OLE / media)
  security    MSIP 敏感性标签 + customXml part(企业模板 ingest 合规参考)
  metadata    docProps 文档属性
  themes      theme*.xml 色板 + 字体方案
  masters     master / layout 使用计数
  all         全部

fonts 判定规则(severity):
  ERROR    run 含 CJK 文本、写了 `<a:latin>` 却没写 `<a:ea>` —— set_font 未走 lxml ea 路径的经典 bug
  WARNING  run 的 ea 指向 theme token(+mn-ea/+mj-ea)但 theme ea 为空;或继承链无任何 ea 来源
  INFO     run 未声明字体、由 theme minorFont ea 兜底(tier1 模板页常见,可接受)
  OK       run 显式声明了非空 ea

Exit code:
  0  未跑 fonts,或 fonts 无 ERROR(--strict 时还要求无 WARNING)
  1  fonts ERROR ≥ 1(--strict 时 WARNING 也算)
  2  用法 / 文件错误

用法:
  python3 scripts/audit_pptx.py deck.pptx                          # EA gate(JSON)
  python3 scripts/audit_pptx.py deck.pptx --sections all           # 全量审计
  python3 scripts/audit_pptx.py deck.pptx --format text            # 人读摘要
也可 `uv run scripts/audit_pptx.py ...`(PEP 723 · 零依赖)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "cu": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
    "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
}

SECTIONS = ("fonts", "shapes", "hyperlinks", "embedded", "security", "metadata", "themes", "masters")

# CJK 统一表意文字(基本区 + 扩展 A + 兼容区)—— 命中即该 run 需要 ea 字体
HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

EMU_PER_INCH = 914400


def _q(tag: str) -> str:
    """'a:ea' → '{ns}ea'"""
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


class PptxAudit:
    """单 .pptx 的只读审计器。zipfile + ElementTree,不依赖 python-pptx。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.zf = zipfile.ZipFile(self.path)
        self.names = set(self.zf.namelist())
        self.slides: list[tuple[int, str]] = sorted(
            (int(m.group(1)), n)
            for n in self.names
            if (m := re.fullmatch(r"ppt/slides/slide(\d+)\.xml", n))
        )

    # ---- 基础读取 -------------------------------------------------------

    def _xml(self, name: str) -> ET.Element | None:
        if name not in self.names:
            return None
        return ET.fromstring(self.zf.read(name))

    def _rels(self, part: str) -> dict[str, dict[str, str]]:
        """part 的 rels:rId → {target, mode, type}"""
        d = Path(part)
        rels_name = str(d.parent / "_rels" / (d.name + ".rels"))
        root = self._xml(rels_name)
        out: dict[str, dict[str, str]] = {}
        if root is None:
            return out
        for rel in root.iter(_q("rel:Relationship")):
            out[rel.get("Id", "")] = {
                "target": rel.get("Target", ""),
                "mode": rel.get("TargetMode", "Internal"),
                "type": rel.get("Type", "").rsplit("/", 1)[-1],
            }
        return out

    def _theme_fonts(self) -> dict[str, dict[str, str]]:
        """第一份 theme 的 fontScheme:{major: {latin, ea, cs}, minor: {...}}"""
        out = {"major": {}, "minor": {}}
        theme_names = sorted(n for n in self.names if re.fullmatch(r"ppt/theme/theme\d+\.xml", n))
        if not theme_names:
            return out
        root = self._xml(theme_names[0])
        if root is None:
            return out
        for key, tag in (("major", "a:majorFont"), ("minor", "a:minorFont")):
            font_el = root.find(f".//{_q(tag)}")
            if font_el is None:
                continue
            for sub in ("latin", "ea", "cs"):
                el = font_el.find(_q(f"a:{sub}"))
                out[key][sub] = (el.get("typeface") or "") if el is not None else ""
        return out

    def _iter_shapes(self, root: ET.Element):
        """yield (shape_name, ph_type, shape_kind, elem) — 覆盖 sp/pic/graphicFrame/cxnSp(含组内嵌套)"""
        for kind in ("sp", "pic", "graphicFrame", "cxnSp"):
            for elem in root.iter(_q(f"p:{kind}")):
                cnvpr = elem.find(f".//{_q('p:cNvPr')}")
                name = cnvpr.get("name", "") if cnvpr is not None else ""
                ph = elem.find(f".//{_q('p:ph')}")
                ph_type = (ph.get("type") or "body") if ph is not None else None
                yield name, ph_type, kind, elem

    # ---- sections -------------------------------------------------------

    def section_fonts(self) -> dict[str, Any]:
        theme = self._theme_fonts()
        theme_ea = {"+mn-ea": theme["minor"].get("ea", ""), "+mj-ea": theme["major"].get("ea", "")}
        findings: list[dict[str, Any]] = []
        counts = Counter()
        cjk_runs = 0
        for num, part in self.slides:
            root = self._xml(part)
            if root is None:
                continue
            for shape_name, ph_type, _kind, elem in self._iter_shapes(root):
                for run in elem.iter(_q("a:r")):
                    t = run.find(_q("a:t"))
                    text = (t.text or "") if t is not None else ""
                    if not HAN_RE.search(text):
                        continue
                    cjk_runs += 1
                    rpr = run.find(_q("a:rPr"))
                    ea_el = rpr.find(_q("a:ea")) if rpr is not None else None
                    latin_el = rpr.find(_q("a:latin")) if rpr is not None else None
                    ea = ea_el.get("typeface", "") if ea_el is not None else ""
                    latin = latin_el.get("typeface", "") if latin_el is not None else ""

                    if ea:
                        resolved = theme_ea.get(ea, ea)
                        if resolved:
                            counts["ok"] += 1
                            continue
                        severity, note, resolved_font = (
                            "WARNING",
                            f"ea 指向 theme token {ea!r} 但 theme ea 为空",
                            "",
                        )
                    elif latin:
                        severity, note, resolved_font = (
                            "ERROR",
                            "run 只写了 <a:latin> 未写 <a:ea> — set_font 未走 lxml ea 路径的经典 bug",
                            "",
                        )
                    else:
                        inherited = theme_ea["+mn-ea"]
                        if inherited:
                            severity, note, resolved_font = (
                                "INFO",
                                "run 未声明字体,由 theme minorFont ea 兜底(占位符/模板页可接受)",
                                inherited,
                            )
                        else:
                            severity, note, resolved_font = (
                                "WARNING",
                                "run 未声明 ea 且 theme ea 为空 — 渲染端将自行 fallback",
                                "",
                            )
                    counts[severity.lower()] += 1
                    findings.append({
                        "slide": num,
                        "shape": shape_name,
                        "placeholder": ph_type,
                        "severity": severity,
                        "text": text[:30],
                        "latin": latin,
                        "ea": ea,
                        "ea_resolved": resolved_font,
                        "note": note,
                    })
        return {
            "theme_fonts": theme,
            "summary": {
                "slides": len(self.slides),
                "cjk_runs": cjk_runs,
                "ok": counts["ok"],
                "info": counts["info"],
                "warnings": counts["warning"],
                "errors": counts["error"],
            },
            "findings": findings,
        }

    def section_shapes(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for num, part in self.slides:
            root = self._xml(part)
            if root is None:
                continue
            for name, ph_type, kind, elem in self._iter_shapes(root):
                xfrm = elem.find(f".//{_q('a:xfrm')}")
                if xfrm is None:  # graphicFrame 用 p:xfrm
                    xfrm = elem.find(f".//{_q('p:xfrm')}")
                pos = {}
                if xfrm is not None:
                    off, ext = xfrm.find(_q("a:off")), xfrm.find(_q("a:ext"))
                    if off is not None and ext is not None:
                        pos = {
                            "x_in": round(int(off.get("x", 0)) / EMU_PER_INCH, 2),
                            "y_in": round(int(off.get("y", 0)) / EMU_PER_INCH, 2),
                            "w_in": round(int(ext.get("cx", 0)) / EMU_PER_INCH, 2),
                            "h_in": round(int(ext.get("cy", 0)) / EMU_PER_INCH, 2),
                        }
                text = "".join(
                    (t.text or "") for t in elem.iter(_q("a:t"))
                )[:50]
                out.append({
                    "slide": num, "name": name, "kind": kind,
                    "placeholder": ph_type, **pos, "text_preview": text,
                })
        return out

    def section_hyperlinks(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        rid_attr = _q("r:id")
        for num, part in self.slides:
            root = self._xml(part)
            if root is None:
                continue
            rels = self._rels(part)
            for hl in root.iter(_q("a:hlinkClick")):
                rid = hl.get(rid_attr, "")
                rel = rels.get(rid, {})
                out.append({
                    "slide": num,
                    "target": rel.get("target", ""),
                    "mode": rel.get("mode", ""),
                    "action": hl.get("action", ""),
                    "tooltip": hl.get("tooltip", ""),
                })
        return out

    def section_embedded(self) -> dict[str, Any]:
        embeddings = [
            {"path": n, "size": self.zf.getinfo(n).file_size}
            for n in sorted(self.names) if n.startswith("ppt/embeddings/")
        ]
        media = [
            {"path": n, "size": self.zf.getinfo(n).file_size}
            for n in sorted(self.names) if n.startswith("ppt/media/")
        ]
        ext_counts = Counter(Path(m["path"]).suffix.lower() for m in media)
        return {
            "embeddings": embeddings,
            "media_count": len(media),
            "media_by_ext": dict(ext_counts),
            "media": media,
        }

    def section_security(self) -> dict[str, Any]:
        msip: list[dict[str, str]] = []
        root = self._xml("docProps/custom.xml")
        if root is not None:
            for prop in root.iter(_q("cu:property")):
                name = prop.get("name", "")
                if not name.startswith("MSIP_Label"):
                    continue
                val_el = next(iter(prop), None)
                msip.append({"name": name, "value": (val_el.text or "") if val_el is not None else ""})
        custom_xml = sorted(n for n in self.names if re.fullmatch(r"customXml/item\d+\.xml", n))
        return {"msip_labels": msip, "custom_xml_parts": custom_xml}

    def section_metadata(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        core = self._xml("docProps/core.xml")
        if core is not None:
            out["core"] = {
                re.sub(r"^\{.*\}", "", el.tag): (el.text or "") for el in core
            }
        app = self._xml("docProps/app.xml")
        if app is not None:
            out["app"] = {
                re.sub(r"^\{.*\}", "", el.tag): (el.text or "")
                for el in app if el.text and not list(el)
            }
        return out

    def section_themes(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name in sorted(n for n in self.names if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)):
            root = self._xml(name)
            if root is None:
                continue
            colors: dict[str, str] = {}
            scheme = root.find(f".//{_q('a:clrScheme')}")
            if scheme is not None:
                for slot in scheme:
                    slot_name = re.sub(r"^\{.*\}", "", slot.tag)
                    srgb = slot.find(_q("a:srgbClr"))
                    sysc = slot.find(_q("a:sysClr"))
                    if srgb is not None:
                        colors[slot_name] = srgb.get("val", "")
                    elif sysc is not None:
                        colors[slot_name] = sysc.get("lastClr", "")
            fonts: dict[str, dict[str, str]] = {}
            for key, tag in (("major", "a:majorFont"), ("minor", "a:minorFont")):
                font_el = root.find(f".//{_q(tag)}")
                if font_el is not None:
                    fonts[key] = {
                        sub: (el.get("typeface") or "")
                        for sub in ("latin", "ea", "cs")
                        if (el := font_el.find(_q(f"a:{sub}"))) is not None
                    }
            out.append({"part": name, "colors": colors, "fonts": fonts})
        return out

    def section_masters(self) -> dict[str, Any]:
        usage: Counter = Counter()
        for _num, part in self.slides:
            rels = self._rels(part)
            layout_target = next(
                (r["target"] for r in rels.values() if r["type"] == "slideLayout"), ""
            )
            if not layout_target:
                continue
            layout_part = "ppt/" + layout_target.replace("../", "")
            layout_root = self._xml(layout_part)
            layout_name = layout_part
            if layout_root is not None:
                csld = layout_root.find(_q("p:cSld"))
                if csld is not None and csld.get("name"):
                    layout_name = csld.get("name", layout_part)
            usage[layout_name] += 1
        masters = [n for n in self.names if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", n)]
        layouts = [n for n in self.names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", n)]
        return {
            "masters": len(masters),
            "layouts_total": len(layouts),
            "layout_usage": dict(usage.most_common()),
        }


def audit(path: str | Path, sections: list[str]) -> dict[str, Any]:
    """跑指定 sections,返回结构化 dict。sections 元素必须 ∈ SECTIONS。"""
    a = PptxAudit(path)
    report: dict[str, Any] = {"file": str(path), "slides": len(a.slides)}
    for sec in sections:
        report[sec] = getattr(a, f"section_{sec}")()
    return report


def _render_text(report: dict[str, Any]) -> str:
    lines = [f"audit: {report['file']}  (slides={report['slides']})"]
    if "fonts" in report:
        s = report["fonts"]["summary"]
        lines.append(
            f"[fonts] cjk_runs={s['cjk_runs']} ok={s['ok']} info={s['info']} "
            f"warnings={s['warnings']} errors={s['errors']}"
        )
        for f in report["fonts"]["findings"]:
            lines.append(
                f"  {f['severity']:<7} slide {f['slide']:>2} | {f['shape']} | "
                f"latin={f['latin'] or '-'} ea={f['ea'] or '-'} | {f['text']!r} | {f['note']}"
            )
    for sec in ("shapes", "hyperlinks"):
        if sec in report:
            lines.append(f"[{sec}] {len(report[sec])} 条")
    if "embedded" in report:
        e = report["embedded"]
        lines.append(f"[embedded] embeddings={len(e['embeddings'])} media={e['media_count']} {e['media_by_ext']}")
    if "security" in report:
        sec_ = report["security"]
        lines.append(f"[security] msip_labels={len(sec_['msip_labels'])} custom_xml={len(sec_['custom_xml_parts'])}")
    if "masters" in report:
        m = report["masters"]
        lines.append(f"[masters] masters={m['masters']} layouts={m['layouts_total']} usage={m['layout_usage']}")
    for sec in ("metadata", "themes"):
        if sec in report:
            lines.append(f"[{sec}] {json.dumps(report[sec], ensure_ascii=False)[:200]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="读侧 .pptx 机械审计(EA 字体 gate + 结构化清单)")
    parser.add_argument("pptx", help=".pptx 文件路径")
    parser.add_argument("--sections", default="fonts",
                        help=f"csv,可选 {','.join(SECTIONS)} 或 all(默认 fonts)")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--strict", action="store_true", help="WARNING 也算 fail(默认只 ERROR)")
    args = parser.parse_args(argv)

    path = Path(args.pptx)
    if not path.is_file():
        print(f"文件不存在: {path}", file=sys.stderr)
        return 2
    sections = list(SECTIONS) if args.sections.strip() == "all" else [
        s.strip() for s in args.sections.split(",") if s.strip()
    ]
    bad = [s for s in sections if s not in SECTIONS]
    if bad:
        print(f"未知 section: {bad},可选 {SECTIONS}", file=sys.stderr)
        return 2

    try:
        report = audit(path, sections)
    except zipfile.BadZipFile:
        print(f"不是合法 .pptx(zip 打不开): {path}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report))

    if "fonts" in report:
        s = report["fonts"]["summary"]
        if s["errors"] or (args.strict and s["warnings"]):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
