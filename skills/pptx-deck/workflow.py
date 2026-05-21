"""KillPPTs pptx-deck — 端到端 workflow 骨架。

用法：
    python3 workflow.py path/to/brief.yaml

流程：parse_brief → load_theme → outline → per-slide(generate + render + vision_check) → save
vision_check 当前实现为：导出 PNG,打印路径,默认接受。
真实使用时由 Claude 调本脚本后逐张看图,出 issue JSON 再 fix。
"""
import os, sys, subprocess, json
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.util import Inches

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "pptx"))
sys.path.insert(0, str(HERE))

import helpers as H
from themes import tech_blue as T


# ----- 1. parse_brief -----

REQUIRED = {"title", "outline", "theme", "output"}


def parse_brief(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    missing = REQUIRED - set(data.keys())
    if missing:
        raise ValueError(f"brief 缺字段: {missing}")
    data.setdefault("subtitle", "")
    data.setdefault("page_count_target", None)
    data.setdefault("key_points", [])
    data.setdefault("reference_pptx", None)
    return data


# ----- 2. load_theme -----

THEMES = {"tech_blue": T}


def load_theme(theme_id):
    if theme_id in THEMES:
        return THEMES[theme_id]
    if str(theme_id).endswith(".pptx"):
        raise NotImplementedError(
            "template-ingest 走 LLM 流程,见 template-ingest.md;"
            "本骨架先实现 tech_blue 路径"
        )
    raise ValueError(f"未知 theme: {theme_id}")


# ----- 3. outline → page_specs -----

def estimate_page_count(brief):
    if brief["page_count_target"]:
        return brief["page_count_target"]
    return int(len(brief["outline"]) * 1.5) + 4


def generate_outline(brief, theme):
    """根据 brief 生成 page_spec list。LLM 在真实运行时会替换此函数。
    本骨架返回固定的简版 outline 跑通 pipeline。"""
    specs = []
    specs.append({"layout": "cover", "title": brief["title"],
                  "subtitle": brief.get("subtitle", "")})
    specs.append({"layout": "toc", "sections": brief["outline"]})
    for i, sec in enumerate(brief["outline"], 1):
        specs.append({"layout": "section_divider", "num": i, "title": sec})
        specs.append({"layout": "bullet_list", "title": sec,
                      "items": brief.get("key_points",
                                          [f"{sec} 要点 1", f"{sec} 要点 2"])[:5]})
    specs.append({"layout": "summary",
                  "conclusions": brief.get("key_points",
                                            ["结论 1", "结论 2", "结论 3"])})
    specs.append({"layout": "closing", "contact_info": "谢谢"})
    return specs


# ----- 4. generate_slide -----

def generate_slide(prs, spec, theme):
    fn = getattr(theme, f"make_{spec['layout']}")
    kwargs = {k: v for k, v in spec.items() if k != "layout"}
    return fn(prs, **kwargs)


# ----- 5. render_one_slide -----

def render_one_slide(prs, idx, out_png):
    """导出全 deck PDF,然后 pdftoppm 截第 idx 页。"""
    tmpdir = Path("/tmp/killppts_render")
    tmpdir.mkdir(exist_ok=True)
    pptx_tmp = tmpdir / "current.pptx"
    prs.save(str(pptx_tmp))
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf",
         str(pptx_tmp), "--outdir", str(tmpdir)],
        check=True, capture_output=True,
    )
    pdf = tmpdir / "current.pdf"
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", "120",
         "-f", str(idx), "-l", str(idx),
         str(pdf), str(tmpdir / "slide_only")],
        check=True, capture_output=True,
    )
    candidates = list(tmpdir.glob(f"slide_only-{idx}*.jpg"))
    if not candidates:
        raise RuntimeError(f"渲染失败,未找到第 {idx} 页 jpg")
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    candidates[0].rename(out_png)


def vision_check(image_path, intent):
    """占位：默认接受。真实运行时 Claude 用 Read tool 看图后输出 issue JSON。"""
    print(f"  [vision_check] {image_path} (intent: {intent})")
    return []


def fix_slide(slide, issues):
    """根据 issues 修 slide。骨架占位：不修。"""
    print(f"  [fix_slide] 应用 {len(issues)} 个修复")
    return slide


# ----- 6. main loop -----

def run(brief_path):
    brief = parse_brief(brief_path)
    theme = load_theme(brief["theme"])
    outline = generate_outline(brief, theme)

    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

    review_needed = []

    for idx, spec in enumerate(outline, 1):
        print(f"slide {idx}/{len(outline)}: {spec['layout']}")
        slide = generate_slide(prs, spec, theme)
        png_path = f"/tmp/killppts_render/page_{idx:02d}.png"
        try:
            render_one_slide(prs, idx, png_path)
        except subprocess.CalledProcessError as e:
            print(f"  warning: render failed: {e}; marking review-needed")
            review_needed.append({"idx": idx, "reason": "render_failed"})
            continue

        attempts = 0
        issues = vision_check(png_path, intent=spec["layout"])
        while issues and attempts < 3:
            slide = fix_slide(slide, issues)
            render_one_slide(prs, idx, png_path)
            issues = vision_check(png_path, intent=spec["layout"])
            attempts += 1
        if issues:
            review_needed.append({"idx": idx, "reason": "vision_unresolved",
                                  "issues": issues})

    out = Path(brief["output"]).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(f"\nDone: {out}")
    if review_needed:
        print(f"Warning: {len(review_needed)} pages need review:")
        for r in review_needed:
            print(f"  - page {r['idx']}: {r['reason']}")
    return out, review_needed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python3 workflow.py path/to/brief.yaml")
    run(sys.argv[1])
