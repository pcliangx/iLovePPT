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
  geometry    机械几何审计(越界 / 文字重叠 / 跨页标题一致性)—— 视觉 QA 精度项的
              机械化替代(LLM 读 120dpi JPG 测不准 0.1" 级差异,XML 里可以准确算);
              advisory,不影响 exit code,findings 由 builder Step 3 视觉 QA 消费
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

SECTIONS = ("fonts", "shapes", "geometry", "hyperlinks", "embedded", "security", "metadata", "themes", "masters")

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

    # ---- geometry(机械几何审计)---------------------------------------

    def _slide_size_in(self) -> tuple[float, float]:
        """从 presentation.xml 读 slide 尺寸(inches);读不到回落 16:9 默认。"""
        root = self._xml("ppt/presentation.xml")
        if root is not None:
            sz = root.find(_q("p:sldSz"))
            if sz is not None:
                return (int(sz.get("cx", 0)) / EMU_PER_INCH,
                        int(sz.get("cy", 0)) / EMU_PER_INCH)
        return (13.333, 7.5)

    def _shape_boxes(self) -> dict[int, list[dict[str, Any]]]:
        """每页 shape bbox 列表(inches)· 只收有 xfrm 的 shape。

        组合形状(p:grpSp)子形状的 a:off/a:ext 在组内子坐标系(chOff/chExt
        映射),直接当 slide 绝对坐标会产生假 off_canvas / text_overlap ——
        跳过组内子形状,用组本身的 bbox(slide 坐标)代表整组参与几何检查。
        """
        grp_tag = _q("p:grpSp")

        def _inside_group(el: ET.Element, parent_of: dict) -> bool:
            cur = parent_of.get(el)
            while cur is not None:
                if cur.tag == grp_tag:
                    return True
                cur = parent_of.get(cur)
            return False

        by_slide: dict[int, list[dict[str, Any]]] = {}
        for num, part in self.slides:
            root = self._xml(part)
            if root is None:
                continue
            parent_of = {c: p for p in root.iter() for c in p}
            boxes: list[dict[str, Any]] = []
            for name, ph_type, kind, elem in self._iter_shapes(root):
                if _inside_group(elem, parent_of):
                    continue
                xfrm = elem.find(f".//{_q('a:xfrm')}")
                if xfrm is None:
                    xfrm = elem.find(f".//{_q('p:xfrm')}")
                if xfrm is None:
                    continue
                off, ext = xfrm.find(_q("a:off")), xfrm.find(_q("a:ext"))
                if off is None or ext is None:
                    continue
                text = "".join((t.text or "") for t in elem.iter(_q("a:t")))
                # 首 run 字号(pt · 无则 0)
                sz = 0
                rpr = elem.find(f".//{_q('a:rPr')}")
                if rpr is not None and rpr.get("sz", "").isdigit():
                    sz = int(rpr.get("sz", "0")) // 100
                boxes.append({
                    "name": name, "kind": kind, "placeholder": ph_type,
                    "x": int(off.get("x", 0)) / EMU_PER_INCH,
                    "y": int(off.get("y", 0)) / EMU_PER_INCH,
                    "w": int(ext.get("cx", 0)) / EMU_PER_INCH,
                    "h": int(ext.get("cy", 0)) / EMU_PER_INCH,
                    "text": text, "font_pt": sz,
                })
            # 顶层组:组的 xfrm(p:grpSpPr/a:xfrm 的 off/ext)是 slide 坐标
            for grp in root.iter(grp_tag):
                if _inside_group(grp, parent_of):
                    continue  # 嵌套组由外层 bbox 覆盖
                xfrm = grp.find(f"{_q('p:grpSpPr')}/{_q('a:xfrm')}")
                if xfrm is None:
                    continue
                off, ext = xfrm.find(_q("a:off")), xfrm.find(_q("a:ext"))
                if off is None or ext is None:
                    continue
                cnvpr = grp.find(f"{_q('p:nvGrpSpPr')}/{_q('p:cNvPr')}")
                boxes.append({
                    "name": cnvpr.get("name", "") if cnvpr is not None else "",
                    "kind": "grpSp", "placeholder": None,
                    "x": int(off.get("x", 0)) / EMU_PER_INCH,
                    "y": int(off.get("y", 0)) / EMU_PER_INCH,
                    "w": int(ext.get("cx", 0)) / EMU_PER_INCH,
                    "h": int(ext.get("cy", 0)) / EMU_PER_INCH,
                    "text": "".join((t.text or "") for t in grp.iter(_q("a:t"))),
                    "font_pt": 0,
                })
            by_slide[num] = boxes
        return by_slide

    def section_geometry(self) -> dict[str, Any]:
        """机械几何审计 — 全部 advisory(WARNING/INFO),不影响 exit code。

        checks:
          off_canvas       shape 越出画布(x<0 / y<0 / 超右超下 > 0.02" 容差)→ WARNING
          text_overlap     同页两个**含文字** shape bbox 相交面积 > 20% 较小者
                           (文字叠文字;文字压在装饰 rect 上是 card 的正常做法,不查)→ WARNING
          title_alignment  跨内容页标题锚点漂移:top 文字 shape(y<1.2")的 x 差 > 0.1"
                           或首 run 字号不一致 → WARNING(visual-qa "跨页字号一致"机械化)
        """
        slide_w, slide_h = self._slide_size_in()
        tol = 0.02
        findings: list[dict[str, Any]] = []
        by_slide = self._shape_boxes()

        # 1. off_canvas(只查含文字 shape + 图片/表格 —— 无文字装饰形状出血是
        #    常见设计手法,如 cover 同心圆,不报)
        for num, boxes in by_slide.items():
            for b in boxes:
                if not b["text"].strip() and b["kind"] not in ("pic", "graphicFrame"):
                    continue
                over = []
                if b["x"] < -tol:
                    over.append(f"x={b['x']:.2f}<0")
                if b["y"] < -tol:
                    over.append(f"y={b['y']:.2f}<0")
                if b["x"] + b["w"] > slide_w + tol:
                    over.append(f"right={b['x'] + b['w']:.2f}>{slide_w:.2f}")
                if b["y"] + b["h"] > slide_h + tol:
                    over.append(f"bottom={b['y'] + b['h']:.2f}>{slide_h:.2f}")
                if over:
                    findings.append({
                        "check": "off_canvas", "severity": "WARNING",
                        "slide": num, "shape": b["name"],
                        "note": "越出画布: " + ", ".join(over),
                        "text": b["text"][:30],
                    })

        # 2. text_overlap(只查 文字 × 文字;跳过全幅背景/细线)
        def _is_decor(b: dict[str, Any]) -> bool:
            full_bleed = b["w"] >= slide_w * 0.95 and b["h"] >= slide_h * 0.95
            hairline = b["h"] < 0.15 or b["w"] < 0.15
            return full_bleed or hairline

        for num, boxes in by_slide.items():
            # font_pt >= 100 是装饰大字(single_focus big_number),bbox 大半是留白,
            # 其他 textbox 视觉上在数字下方但落在其 bbox 内 —— 不算文字碰撞
            text_boxes = [b for b in boxes
                          if b["text"].strip() and not _is_decor(b)
                          and b["font_pt"] < 100]
            for i, a in enumerate(text_boxes):
                for b in text_boxes[i + 1:]:
                    ix = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                    iy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                    if ix <= 0 or iy <= 0:
                        continue
                    inter = ix * iy
                    smaller = min(a["w"] * a["h"], b["w"] * b["h"])
                    # 阈值 35%:相邻堆叠 textbox 的 padding 相交常到 ~25%(视觉无碰撞),
                    # 真文字压字通常 > 50%
                    if smaller > 0 and inter / smaller > 0.35:
                        findings.append({
                            "check": "text_overlap", "severity": "WARNING",
                            "slide": num,
                            "shape": f"{a['name']} × {b['name']}",
                            "note": f"文字 shape 相交 {inter / smaller:.0%}(> 35% 较小者)",
                            "text": f"{a['text'][:15]!r} × {b['text'][:15]!r}",
                        })

        # 3. title_alignment(跨内容页 · top 文字 shape 锚点/字号一致性)
        # 候选限定"左锚页标题"形态:24-40pt + x < 3"(排除 cover 大标 / divider
        # 章号 / single_focus 居中大数字 —— 那些页 title 形态天然不同)
        titles: list[tuple[int, dict[str, Any]]] = []
        for num, boxes in by_slide.items():
            cands = [b for b in boxes
                     if b["text"].strip() and b["y"] < 1.2
                     and 24 <= b["font_pt"] <= 40 and b["x"] < 3.0]
            if cands:
                titles.append((num, min(cands, key=lambda b: b["y"])))
        if len(titles) >= 3:  # cover/divider 也可能混入,≥3 页才有统计意义
            xs = [t[1]["x"] for t in titles]
            szs = [t[1]["font_pt"] for t in titles if t[1]["font_pt"]]
            base_x = sorted(xs)[len(xs) // 2]  # median
            for num, b in titles:
                if abs(b["x"] - base_x) > 0.1:
                    findings.append({
                        "check": "title_alignment", "severity": "WARNING",
                        "slide": num, "shape": b["name"],
                        "note": f"标题 x={b['x']:.2f}\" 偏离中位 {base_x:.2f}\"(> 0.1\")",
                        "text": b["text"][:30],
                    })
            if szs and len(set(szs)) > 1:
                base_sz = Counter(szs).most_common(1)[0][0]
                for num, b in titles:
                    if b["font_pt"] and b["font_pt"] != base_sz:
                        findings.append({
                            "check": "title_alignment", "severity": "WARNING",
                            "slide": num, "shape": b["name"],
                            "note": f"标题字号 {b['font_pt']}pt ≠ 众数 {base_sz}pt(跨页字号不一致)",
                            "text": b["text"][:30],
                        })

        counts = Counter(f["severity"].lower() for f in findings)
        return {
            "slide_size_in": [round(slide_w, 3), round(slide_h, 3)],
            "summary": {
                "slides": len(self.slides),
                "warnings": counts["warning"],
                "info": counts["info"],
                "by_check": dict(Counter(f["check"] for f in findings)),
            },
            "findings": findings,
        }

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
    if "geometry" in report:
        g = report["geometry"]["summary"]
        lines.append(f"[geometry] warnings={g['warnings']} by_check={g['by_check']}")
        for f in report["geometry"]["findings"]:
            lines.append(
                f"  {f['severity']:<7} slide {f['slide']:>2} | {f['check']} | "
                f"{f['shape']} | {f['note']}"
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
