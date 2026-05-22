"""iLovePPT build.py —— 机械构建器：deck_plan.json → .pptx + PNG。

用法：python3 build.py deck_plan.json [--no-render]

deck_plan.json schema：{theme, output, slides: [{layout, ...fields}, ...]}
智能部分（brief→deck_plan、视觉自检）由 Claude 按文档流程做,不在本文件。
"""
import sys
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

from pptx import Presentation

HERE = Path(__file__).parent
for _p in [str(HERE.parent / "pptx"), str(HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import helpers as H
from themes import tech_blue as _tech_blue

THEMES: dict[str, ModuleType] = {"tech_blue": _tech_blue}


# ----- load_plan -----

def load_plan(path: str | Path) -> dict[str, Any]:
    """读 + 校验 deck_plan.json。记录 _plan_dir 供相对 output 解析。"""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    for field in ("theme", "output", "slides"):
        if field not in data:
            raise ValueError(f"deck_plan 缺字段: {field}")
    if not isinstance(data["slides"], list) or not data["slides"]:
        raise ValueError("deck_plan.slides 必须是非空 list")
    for i, slide in enumerate(data["slides"], 1):
        if "layout" not in slide:
            raise ValueError(f"deck_plan 第 {i} 页缺 layout 字段")
    data["_plan_dir"] = str(p.resolve().parent)
    return data


# ----- load_theme -----

def _extract_design_tokens(pptx_path: str) -> dict[str, Any]:
    """从 .pptx 提取主色(accent1)与中文字体(master ea typeface)。best-effort。"""
    from lxml import etree
    tokens: dict[str, Any] = {}
    try:
        prs = Presentation(pptx_path)
    except Exception:
        return tokens
    try:
        from pptx.oxml.ns import qn
        if prs.slide_masters:
            done = False
            for ph in prs.slide_masters[0].placeholders:
                for para in ph.text_frame.paragraphs:
                    for run in para.runs:
                        rPr = run._r.find(qn("a:rPr"))
                        if rPr is not None:
                            ea = rPr.find(qn("a:ea"))
                            if ea is not None and ea.get("typeface"):
                                tokens["font_header"] = ea.get("typeface")
                                tokens["font_body"] = ea.get("typeface")
                                done = True
                                break
                    if done:
                        break
                if done:
                    break
    except Exception:
        pass
    try:
        from pptx.dml.color import RGBColor
        for part in prs.part.package.iter_parts():
            pn = part.partname
            if "theme" in pn and pn.endswith(".xml"):
                root = etree.fromstring(part.blob)
                ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
                accent1 = root.find(".//a:accent1//a:srgbClr", ns)
                if accent1 is not None:
                    hx = accent1.get("val", "")
                    if len(hx) == 6:
                        tokens["primary"] = RGBColor(
                            int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
                        break
    except Exception:
        pass
    return tokens


def _extract_theme_from_pptx(pptx_path: str) -> ModuleType:
    """从用户 .pptx 提取主色与字体,派生临时主题模块。

    从 tech_blue.py 源码加载全新模块实例,再用提取的 token 覆盖
    FONT_* / PRIMARY 属性。token 提取 best-effort,未提取到的保留默认。
    """
    import importlib.util
    tokens = _extract_design_tokens(pptx_path)
    import themes.tech_blue as base_module
    base_path = Path(base_module.__file__)
    out_name = f"extracted_{Path(pptx_path).stem}"
    spec = importlib.util.spec_from_file_location(out_name, base_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法从 {base_path} 加载主题")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if "font_header" in tokens:
        mod.FONT_HEADER = tokens["font_header"]
        mod.FONT_BODY = tokens.get("font_body", tokens["font_header"])
    if "primary" in tokens:
        mod.PRIMARY = tokens["primary"]
    print(f"  从模板提取主题: {out_name}（主色 {tokens.get('primary', '默认')}）")
    return mod


def load_theme(theme_id: str) -> ModuleType:
    if theme_id in THEMES:
        return THEMES[theme_id]
    if str(theme_id).endswith(".pptx"):
        if not Path(theme_id).exists():
            raise FileNotFoundError(f"theme .pptx 不存在: {theme_id}")
        return _extract_theme_from_pptx(theme_id)
    raise ValueError(f"未知 theme: {theme_id}")


# ----- build_deck -----

def build_deck(plan: dict[str, Any]) -> Path:
    """按 deck_plan 逐 slide 调 make_*,存 .pptx,返回输出路径。"""
    theme = load_theme(plan["theme"])
    prs = Presentation()
    prs.slide_width = H.SLIDE_W
    prs.slide_height = H.SLIDE_H
    for i, slide in enumerate(plan["slides"], 1):
        layout = slide["layout"]
        fn = getattr(theme, f"make_{layout}", None)
        if fn is None:
            raise ValueError(f"第 {i} 页未知 layout: {layout}（theme 无 make_{layout}）")
        fields = {k: v for k, v in slide.items() if k != "layout"}
        try:
            fn(prs, **fields)
        except TypeError as e:
            raise ValueError(f"第 {i} 页 layout={layout}: {e}") from e
    out = Path(plan["output"]).expanduser()
    if not out.is_absolute():
        out = (Path(plan["_plan_dir"]) / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


# ----- render -----

def render(pptx_path: str | Path, out_dir: str | Path) -> list[Path]:
    """soffice → PDF → pdftoppm → 逐页 PNG。返回 PNG 路径列表。"""
    if shutil.which("soffice") is None:
        raise RuntimeError("soffice 未安装。请: brew install --cask libreoffice")
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm 未安装。请: brew install poppler")
    pptx_path = Path(pptx_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             str(pptx_path), "--outdir", str(out_dir)],
            check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"soffice 转 PDF 失败: {e.stderr}") from e
    pdf = out_dir / (pptx_path.stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError(f"soffice 跑了但未产 PDF: {pdf}")
    try:
        subprocess.run(
            ["pdftoppm", "-jpeg", "-r", "120", str(pdf), str(out_dir / "page")],
            check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftoppm 转 PNG 失败: {e.stderr}") from e
    return sorted(out_dir.glob("page-*.jpg"))


# ----- CLI -----

def main(argv: list[str]) -> None:
    if not argv:
        sys.exit("用法: python3 build.py deck_plan.json [--no-render]")
    plan_path = argv[0]
    do_render = "--no-render" not in argv
    plan = load_plan(plan_path)
    out = build_deck(plan)
    print(f"已生成 {out}")
    if do_render:
        render_dir = out.parent / (out.stem + "_render")
        pngs = render(out, render_dir)
        print(f"已渲染 {len(pngs)} 页 → {render_dir}")


if __name__ == "__main__":
    main(sys.argv[1:])
