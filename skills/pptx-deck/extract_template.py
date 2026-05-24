"""extract_template.py — 从 .pptx 模板提取媒体 + 扩展 token + 跑 probe deck

用法:
    python3 skills/pptx-deck/extract_template.py templates/company_a.pptx
    python3 skills/pptx-deck/extract_template.py templates/company_a.pptx --no-probe

输出:
    extractor/template_company_a/    ← L1:解压 ppt/media/* 到这(在 deck working_dir 下)
    templates/company_a.yaml         ← L2:enriched 元数据 + extracted tokens
    /tmp/probe_company_a/page-*.jpg  ← probe deck 渲染图(若 --probe)
                                       agent 读这些 PNG 做视觉分析,
                                       结果写进 yaml.visual_observations
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree
import yaml

HERE = Path(__file__).parent
for _p in [str(HERE.parent / "pptx"), str(HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


# ----- L1:媒体提取 -----

def extract_media(pptx_path: Path, out_dir: Path) -> list[str]:
    """解压 .pptx 的 ppt/media/* 到 out_dir。返回提取的文件名列表。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    with zipfile.ZipFile(pptx_path) as z:
        for name in z.namelist():
            if name.startswith("ppt/media/") and not name.endswith("/"):
                fname = Path(name).name
                target = out_dir / fname
                with z.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(fname)
    return sorted(extracted)


# ----- L2:扩展 XML token 提取 -----

def _read_xml(pptx_path: Path, member: str) -> etree._Element | None:
    try:
        with zipfile.ZipFile(pptx_path) as z, z.open(member) as f:
            return etree.parse(f).getroot()
    except (KeyError, etree.XMLSyntaxError):
        return None


def _hex_from_srgb(elem: etree._Element | None) -> str | None:
    if elem is None:
        return None
    srgb = elem.find(".//a:srgbClr", NS)
    if srgb is None:
        return None
    val = srgb.get("val", "")
    return f"#{val.upper()}" if len(val) == 6 else None


def extract_extended_tokens(pptx_path: Path) -> dict[str, Any]:
    """提取扩展 design token。返回 dict,各字段可能为 None(模板未定义)。

    提取:
    - accent1..accent6 hex
    - dk1 / lt1(主文本色 / 主背景色)
    - master ea typeface(中文字体)
    - master title / body 默认字号(若 master 显式指定)
    - 背景类型(solidFill / gradFill / blipFill)
    """
    tokens: dict[str, Any] = {
        "accent1": None, "accent2": None, "accent3": None,
        "accent4": None, "accent5": None, "accent6": None,
        "dk1": None, "lt1": None,
        "font_ea": None,
        "title_size_pt": None, "body_size_pt": None,
        "background_type": None,
    }

    # theme1.xml: accent colors + dk1/lt1
    theme = _read_xml(pptx_path, "ppt/theme/theme1.xml")
    if theme is not None:
        scheme = theme.find(".//a:clrScheme", NS)
        if scheme is not None:
            for tag in ("accent1", "accent2", "accent3", "accent4",
                        "accent5", "accent6", "dk1", "lt1"):
                node = scheme.find(f"a:{tag}", NS)
                hx = _hex_from_srgb(node)
                if hx:
                    tokens[tag] = hx
                # dk1/lt1 也可能是 sysClr (windowText/window),记原始值
                elif node is not None and tag in ("dk1", "lt1"):
                    sys_clr = node.find("a:sysClr", NS)
                    if sys_clr is not None:
                        last = sys_clr.get("lastClr", "")
                        if len(last) == 6:
                            tokens[tag] = f"#{last.upper()}"

    # slideMaster1.xml: ea typeface + master title/body 字号
    master = _read_xml(pptx_path, "ppt/slideMasters/slideMaster1.xml")
    if master is not None:
        # 找第一个含 a:ea 的 run property
        for ea in master.iter(f"{{{NS['a']}}}ea"):
            tf = ea.get("typeface")
            if tf:
                tokens["font_ea"] = tf
                break
        # 标题字号:titleStyle 的 lvl1pPr/defRPr@sz
        title_def = master.find(".//p:titleStyle//a:lvl1pPr/a:defRPr", NS)
        if title_def is not None:
            sz = title_def.get("sz")
            if sz and sz.isdigit():
                tokens["title_size_pt"] = int(sz) // 100  # OOXML sz 是百分点
        # 正文字号:bodyStyle 的 lvl1pPr/defRPr@sz
        body_def = master.find(".//p:bodyStyle//a:lvl1pPr/a:defRPr", NS)
        if body_def is not None:
            sz = body_def.get("sz")
            if sz and sz.isdigit():
                tokens["body_size_pt"] = int(sz) // 100

        # 背景类型(master/cSld/bg/{bgPr,bgRef})
        bg = master.find(".//p:cSld/p:bg", NS)
        if bg is not None:
            bg_pr = bg.find("p:bgPr", NS)
            if bg_pr is not None:
                if bg_pr.find("a:solidFill", NS) is not None:
                    tokens["background_type"] = "solid"
                elif bg_pr.find("a:gradFill", NS) is not None:
                    tokens["background_type"] = "gradient"
                elif bg_pr.find("a:blipFill", NS) is not None:
                    tokens["background_type"] = "image"
            elif bg.find("p:bgRef", NS) is not None:
                tokens["background_type"] = "theme_ref"

    return tokens


# ----- probe deck -----

PROBE_DECK_PLAN = {
    "theme": None,  # 运行时填
    "output": None,  # 运行时填
    "slides": [
        {"layout": "cover",
         "title": "模板视觉探测",
         "subtitle": "8 页覆盖 8 种 layout,agent 读图后写 yaml"},
        {"layout": "toc",
         "sections": ["背景与问题", "解决方案", "数据验证", "组织保障", "落地节奏"]},
        {"layout": "section_divider", "num": 1, "title": "示例章节"},
        {"layout": "single_focus",
         "big_text": "测试大数字字体",
         "big_number": "87%",
         "explanation": "看大字号字体是否符合模板风格"},
        {"layout": "cards",
         "title": "三张并列卡片测试",
         "cards": [
             {"title": "卡 A", "body": "测试卡片底色 / 圆角 / 字号"},
             {"title": "卡 B", "body": "看左侧 accent 条颜色"},
             {"title": "卡 C", "body": "正文 18pt 是否合适"}]},
        {"layout": "bullet_list",
         "title": "要点列表测试",
         "items": ["看 bullet 缩进 / 行距 / 字号", "字体在小尺寸下渲染",
                   "项目符号样式", "整体留白感"]},
        {"layout": "summary",
         "conclusions": ["主色对比度 7:1 达 AAA",
                         "正文字体清晰可读",
                         "卡片视觉一致"]},
        {"layout": "closing",
         "subtitle": "完成 — 请 agent 看图分析"}
    ]
}


def run_probe_deck(pptx_path: Path, out_dir: Path) -> Path | None:
    """跑一份 probe deck:用 extracted theme + 内置 8-layout mini plan。

    返回 .pptx 路径(渲染目录在同级 *_render/)。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(json.dumps(PROBE_DECK_PLAN))  # deep copy
    plan["theme"] = str(pptx_path.resolve())
    probe_pptx = out_dir / "probe.pptx"
    plan["output"] = str(probe_pptx)

    # 写临时 plan 文件
    plan_file = out_dir / "probe_plan.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    # 跑 build.py
    build_script = HERE / "build.py"
    try:
        subprocess.run(
            ["python3", str(build_script), str(plan_file)],
            check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  [WARN] probe build failed: {e.stderr[-300:]}", file=sys.stderr)
        return None
    return probe_pptx if probe_pptx.exists() else None


# ----- yaml 写入 -----

def write_enriched_yaml(yaml_path: Path, pptx_path: Path,
                        media_files: list[str], tokens: dict[str, Any],
                        probe_render_dir: Path | None) -> None:
    """生成 enriched <name>.yaml(已有则 merge,不覆盖用户手填字段)。"""
    name = pptx_path.stem
    existing: dict[str, Any] = {}
    if yaml_path.exists():
        try:
            existing = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            existing = {}

    enriched: dict[str, Any] = {
        # 用户字段保留(若存在)
        "name": existing.get("name", name),
        "desc": existing.get("desc", "(请填:一句话描述模板用途)"),
        "recommended_for": existing.get("recommended_for", []),
        "owner": existing.get("owner", "(请填)"),
        "notes": existing.get("notes", ""),
        # extract 输出
        "extracted": {
            "source_pptx": str(pptx_path.resolve()),
            "media_files": media_files,
            "media_dir": f"extractor/template_{name}/",
            "tokens": {k: v for k, v in tokens.items() if v is not None},
        },
    }
    if probe_render_dir and probe_render_dir.exists():
        pngs = sorted([p.name for p in probe_render_dir.glob("page-*.jpg")])
        enriched["probe"] = {
            "render_dir": str(probe_render_dir),
            "page_count": len(pngs),
            "visual_observations": existing.get(
                "visual_observations",
                "(待 agent Read probe PNG 后填:对模板视觉风格的观察)"),
        }

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        yaml.dump(enriched, allow_unicode=True, sort_keys=False, indent=2),
        encoding="utf-8")


# ----- 入口 -----

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="提取 .pptx 模板的视觉资产 + token")
    parser.add_argument("pptx", help="模板 .pptx 路径")
    parser.add_argument("--no-probe", action="store_true",
                        help="跳过 probe deck 渲染(只做 L1+L2)")
    parser.add_argument("--working-dir", default=".",
                        help="工作目录(extractor/ 落在这下面),默认 cwd")
    args = parser.parse_args(argv)

    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.exists():
        print(f"[ERR] 模板不存在: {pptx_path}", file=sys.stderr)
        return 2

    working = Path(args.working_dir).resolve()
    name = pptx_path.stem

    # L1
    media_dir = working / "extractor" / f"template_{name}"
    print(f"[L1] 解压 media → {media_dir}")
    media_files = extract_media(pptx_path, media_dir)
    print(f"  {len(media_files)} 个文件: {', '.join(media_files[:5])}"
          + ("..." if len(media_files) > 5 else ""))

    # L2
    print(f"[L2] 抽 token")
    tokens = extract_extended_tokens(pptx_path)
    for k, v in tokens.items():
        if v is not None:
            print(f"  {k}: {v}")

    # probe
    probe_render_dir: Path | None = None
    if not args.no_probe:
        print(f"[probe] 跑 8-page probe deck → /tmp/probe_{name}/")
        probe_dir = Path(f"/tmp/probe_{name}")
        probe_pptx = run_probe_deck(pptx_path, probe_dir)
        if probe_pptx:
            probe_render_dir = probe_dir / "probe_render"
            if probe_render_dir.exists():
                pngs = sorted(probe_render_dir.glob("page-*.jpg"))
                print(f"  渲染 {len(pngs)} 页 → 让 agent Read 这些 PNG 写视觉观察")

    # 写 yaml
    templates_dir = pptx_path.parent
    yaml_path = templates_dir / f"{name}.yaml"
    print(f"[yaml] 写 → {yaml_path}")
    write_enriched_yaml(yaml_path, pptx_path, media_files, tokens, probe_render_dir)

    print(f"\n✓ 完成。下一步:")
    print(f"  · 检查 {yaml_path}(可手编 desc/notes)")
    print(f"  · 若 probe 跑了,让 agent Read /tmp/probe_{name}/probe_render/page-*.jpg")
    print(f"    然后填进 yaml.probe.visual_observations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
