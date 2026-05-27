"""P1-1 backfill · 给 212 张 page meta.yaml 加 standard `variant` enum.

读 layout_variants.yaml SSOT,扫每张 meta.yaml,按启发推断 variant 写回。
单文件,只动 page-level meta.yaml,不动 placeholder_map / 模板级 meta.yaml。

启发:
  - 看 layout_type 锁定桶
  - 看 native_elements + name + 已有 variant 推 N(数字)+ 视觉元素(icon/photo/illustration)
  - 找 vocab 桶里最近 enum
  - 兜底:cards-other / process-other / 等 -other
  - other 类:islide / tree-hierarchy / misc
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path("/Users/pc2026/Documents/DevTools/iLovePPT")
VOCAB_PATH = REPO / "library/vocabularies/layout_variants.yaml"
ITEMS_ROOT = REPO / "library/pptx-templates/items"


def load_vocab() -> dict:
    with open(VOCAB_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["variants"]


VOCAB = load_vocab()


def vocab_for_lt(lt: str) -> list[str]:
    return [k for k, v in VOCAB.items() if v["layout_type"] == lt]


# ----- Heuristic helpers -----

NUM_WORDS_CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def extract_n(text_blobs: list[str]) -> int | None:
    """Try to extract dominant N (count) from name + native_elements + variant string."""
    joined = " ".join(text_blobs)
    # Look for "N 个/项/张/列/步/段/阶/层/节点/卡片/circle/cards/cols/rows/spoke" etc.
    pat = re.compile(r"(\d+)\s*(?:个|项|张|列|步|段|阶|层|节点|节|卡片|cards?|cols?|rows?|spokes?|item|tier|circle|node|stage|step|chain|round|序列)", re.I)
    counts: dict[int, int] = {}
    for m in pat.finditer(joined):
        n = int(m.group(1))
        counts[n] = counts.get(n, 0) + 1
    # Also literal patterns like "3-cols" "4-cards"
    pat2 = re.compile(r"\b(\d+)[-_](?:col|card|tier|step|row|node|stage|spoke|chain|item|stations?|hex|circle|fan|chains?|cells?|teardrop|diamond|station)", re.I)
    for m in pat2.finditer(joined):
        n = int(m.group(1))
        counts[n] = counts.get(n, 0) + 2
    if not counts:
        # CN words
        for w, n in NUM_WORDS_CN.items():
            if w in joined:
                counts[n] = counts.get(n, 0) + 1
                break
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def has_keyword(text_blobs: list[str], words: list[str]) -> bool:
    joined = " ".join(text_blobs).lower()
    return any(w.lower() in joined for w in words)


ICON_WORDS = ["icon", "图标"]
# Photo keywords — must be unambiguous (no substring overlap with negative phrases like "不含图")
PHOTO_WORDS = ["photo", "image", "图片", "实拍", "照片", "霓虹场景", "图块", "视觉块", "KV 图", "kv图", "大图", "双图", "多图", "三图横排", "右大图", "顶图", "封面图"]
ILLUSTRATION_WORDS = ["插画", "illustration", "vector art", "线稿", "卡通", "矢量图"]


def infer_visual(text_blobs: list[str]) -> str:
    """Return 'icon' | 'photo' | 'illustration' | 'mixed' | 'text' based on text blobs.

    For card/grid visual detection, prioritize signals from native_elements (visual SoT).
    """
    has_icon = has_keyword(text_blobs, ICON_WORDS)
    has_photo = has_keyword(text_blobs, PHOTO_WORDS)
    has_illu = has_keyword(text_blobs, ILLUSTRATION_WORDS)
    if has_photo and has_icon:
        return "mixed"
    if has_photo:
        return "photo"
    if has_illu and not has_icon:
        return "illustration"
    if has_icon:
        return "icon"
    return "text"


def pick_n_variant(prefix: str, n: int | None, available: list[str], fallback: str) -> str:
    """Pick variant_<n> from available set; if missing → nearest neighbor; else fallback."""
    if n is None:
        return fallback
    candidate = f"{prefix}{n}"
    if candidate in VOCAB:
        return candidate
    # find nearest in available pool
    pool = [k for k in available if k.startswith(prefix)]
    nums = []
    for k in pool:
        m = re.search(r"-(\d+)(?:-|$)", k)
        if m:
            nums.append((int(m.group(1)), k))
    if not nums:
        return fallback
    nearest = min(nums, key=lambda t: abs(t[0] - n))
    return nearest[1]


# ----- Layout-specific inference -----


def infer_cover(meta: dict, blobs: list[str]) -> str:
    """Cover variants: text-only / illustration / photo / geometric / other."""
    if has_keyword(blobs, ILLUSTRATION_WORDS + ["笔记本", "插画", "人物剪影"]):
        return "cover-illustration"
    if has_keyword(blobs, PHOTO_WORDS):
        return "cover-photo"
    if has_keyword(blobs, ["几何", "三角", "色块", "渐变", "霓虹", "六边形", "geometric"]):
        return "cover-geometric"
    if has_keyword(blobs, ["纯文字", "text only", "无装饰"]):
        return "cover-text-only"
    # default geometric for templates without literal "插画"
    return "cover-geometric"


def infer_toc(meta: dict, blobs: list[str]) -> str:
    """TOC: pick by N items."""
    n = extract_n(blobs)
    if n is None:
        return "toc-other"
    candidate = f"toc-{n}"
    if candidate in VOCAB:
        return candidate
    # Snap to nearest [3-8]
    if n < 3:
        return "toc-3"
    if n > 8:
        return "toc-8"
    return "toc-other"


def infer_section_divider(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, ILLUSTRATION_WORDS):
        return "section-divider-illustration"
    if has_keyword(blobs, PHOTO_WORDS):
        return "section-divider-photo"
    # Look for "01" "02" big number markers
    if has_keyword(blobs, ["大数字", "01", "02", "chapter", "编号", "数字编号"]):
        return "section-divider-numbered"
    return "section-divider-text"


def infer_summary(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, ["卡片", "card"]):
        return "summary-cards"
    if has_keyword(blobs, ["bullet", "要点"]):
        return "summary-bullet"
    return "summary-other"


def infer_closing(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, ILLUSTRATION_WORDS + ["插画"]):
        return "closing-illustration"
    if has_keyword(blobs, PHOTO_WORDS):
        return "closing-photo"
    return "closing-text-only"


def infer_quote(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, PHOTO_WORDS + ["头像"]):
        return "quote-with-photo"
    return "quote-large"


def infer_single_focus(meta: dict, blobs: list[str]) -> str:
    visual_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    if has_keyword(visual_blobs, ["%", "百分比", "percentage", "percent"]):
        return "single-focus-percentage"
    if has_keyword(visual_blobs, ["KPI", "大号数字", "大数字", "巨大数字"]):
        return "single-focus-kpi"
    if has_keyword(visual_blobs, ILLUSTRATION_WORDS + ["插画", "火箭", "人物剪影", "人物插画"]):
        return "single-focus-illustration"
    if has_keyword(visual_blobs, ["quote", "格言", "引言"]):
        return "single-focus-quote"
    if has_keyword(visual_blobs, ["左图", "右图", "左文", "右文", "左侧大图", "右侧大图"]):
        return "single-focus-text-image"
    if has_keyword(visual_blobs, PHOTO_WORDS):
        return "single-focus-image"
    return "single-focus-other"


def infer_cards(meta: dict, blobs: list[str]) -> str:
    """Cards: N (2/3/4/5/6) × visual (text/icon/photo/mixed); plus grid 2x2/3x2/3x3."""
    # Visual signals from native_elements + name only (visual SoT)
    visual_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    # Check grid first
    if has_keyword(blobs, ["2x2", "2x 2", "2×2", "2 x 2", "四象限网格"]):
        return "cards-grid-2x2"
    if has_keyword(blobs, ["3x3", "3×3"]):
        return "cards-grid-3x3"
    if has_keyword(blobs, ["3x2", "3×2", "6 cells", "6 格"]):
        return "cards-grid-3x2"
    n = extract_n(blobs)
    visual = infer_visual(visual_blobs)
    if n is None:
        return "cards-other"
    if n > 6:
        return "cards-other"
    # Snap N to {2,3,4,5,6}
    if n < 2:
        n = 2
    elif n > 6:
        n = 6
    # 5 only has -icon
    if n == 5:
        return "cards-5-icon"
    suffix = visual if visual != "illustration" else "icon"
    candidate = f"cards-{n}-{suffix}"
    if candidate in VOCAB:
        return candidate
    # fallback to -text
    if f"cards-{n}-text" in VOCAB:
        return f"cards-{n}-text"
    return "cards-other"


def infer_bullet_list(meta: dict, blobs: list[str]) -> str:
    n = extract_n(blobs)
    if has_keyword(blobs, ["checkbox", "复选框", "勾选"]):
        return "bullet-checkbox"
    if has_keyword(blobs, ["编号", "numbered", "01 02", "01/02"]):
        return "bullet-numbered"
    if has_keyword(blobs, PHOTO_WORDS):
        return "bullet-with-photo"
    if has_keyword(blobs, ICON_WORDS):
        return "bullet-with-icons"
    if n is None:
        return "bullet-other"
    if n < 3:
        n = 3
    if n > 6:
        n = 6
    return f"bullet-{n}"


def infer_data(meta: dict, blobs: list[str]) -> str:
    # Visual signal SoT for chart type detection
    visual_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    # KPI grid first (multiple % / KPI numbers is more specific signal)
    has_kpi = has_keyword(visual_blobs, ["KPI", "百分比", "Percent", "数字网格", "metric circles"])
    has_pct_data = has_keyword(visual_blobs, ["%"])
    has_donut = has_keyword(visual_blobs, ["donut", "环形图", "圆环"])
    has_pie = has_keyword(visual_blobs, ["饼图", "pie"])
    has_bar = has_keyword(visual_blobs, ["条形图", "bar chart", "柱状图", "柱图"])
    has_line = has_keyword(visual_blobs, ["折线图", "line chart", "上升曲线", "趋势线", "波峰增长"])
    has_table = has_keyword(visual_blobs, ["表格", "table", "n 列 n 行", "对比表"])
    has_gantt = has_keyword(visual_blobs, ["甘特", "gantt"])

    # Specific KPI + chart combos
    if has_kpi and (has_donut or has_pie):
        return "data-mixed-chart-kpi"
    if has_gantt:
        return "data-mixed-chart-kpi"  # gantt-like table is hybrid timeline-table chart
    if has_kpi or (has_pct_data and not (has_bar or has_line or has_donut or has_pie or has_table)):
        return "data-kpi-grid"
    if has_table:
        return "data-table"
    if has_donut or has_pie:
        return "data-chart-pie"
    if has_bar:
        return "data-chart-bar"
    if has_line:
        return "data-chart-line"
    if has_keyword(visual_blobs, ["面积图", "area chart", "堆叠"]):
        return "data-chart-area"
    return "data-other"


def infer_timeline(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, ["gantt", "甘特", "lane", "lane 4", "跨年"]):
        return "timeline-gantt"
    if has_keyword(blobs, ["zigzag", "Z 字", "Z字", "之字"]):
        return "timeline-zigzag"
    if has_keyword(blobs, ["阶梯", "staircase", "ascending stairs"]):
        return "timeline-staircase"
    n = extract_n(blobs)
    is_vertical = has_keyword(blobs, ["纵向", "垂直", "vertical"])
    is_horizontal = has_keyword(blobs, ["横向", "水平", "horizontal"]) or not is_vertical
    if n is None:
        return "timeline-other"
    if n < 3:
        n = 3
    direction = "v" if is_vertical else "h"
    if n > 7:
        return "timeline-h-7" if direction == "h" else "timeline-v-6"
    if direction == "h":
        if n == 7:
            return "timeline-h-7"
        return f"timeline-h-{n}"
    if n > 6:
        n = 6
    return f"timeline-v-{n}"


def infer_pyramid(meta: dict, blobs: list[str]) -> str:
    if has_keyword(blobs, ["倒漏斗", "倒金字塔", "inverted", "from top to bottom"]):
        return "pyramid-inverted"
    n = extract_n(blobs)
    if n is None:
        return "pyramid-other"
    if n <= 3:
        return "pyramid-3"
    if n == 4:
        return "pyramid-4"
    if n >= 5:
        return "pyramid-5"
    return "pyramid-other"


def infer_venn(meta: dict, blobs: list[str]) -> str:
    n = extract_n(blobs)
    if n == 2:
        return "venn-2"
    if n == 3:
        return "venn-3"
    if n == 4:
        return "venn-4"
    return "venn-other"


def infer_radial(meta: dict, blobs: list[str]) -> str:
    visual_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    if has_keyword(visual_blobs, ["org tree", "组织架构", "tree-hierarchy", "树形发散", "org-tree", "子节点向下树状"]):
        return "radial-tree"
    # map-anchor must be in name (primary structural signal), not just a background decoration
    name_only = [meta.get("name", "")]
    if has_keyword(name_only, ["地图", "map anchor", "china map", "城市站点", "城市分布", "中国地图"]):
        return "radial-map-anchor"
    if has_keyword(visual_blobs, ["hub-and-spoke", "hub spoke", "卫星节点", "satellites", "卫星", "卫星布局", "卫星圆点"]):
        return "radial-hub-spoke"
    n = extract_n(blobs)
    if n is None:
        return "radial-other"
    if n <= 3:
        return "radial-3-spoke"
    if n == 4:
        return "radial-4-spoke"
    if n == 5:
        return "radial-5-spoke"
    if n >= 6:
        return "radial-6-spoke"
    return "radial-other"


def infer_process_flow(meta: dict, blobs: list[str]) -> str:
    n = extract_n(blobs)
    is_cycle = has_keyword(blobs, ["cycle", "环形", "循环", "PDCA", "闭环", "round-trip", "loop", "回路"])
    is_funnel = has_keyword(blobs, ["漏斗", "funnel", "倒漏斗"])
    is_vertical = has_keyword(blobs, ["纵向", "垂直", "vertical", "上下", "顶向底"])
    is_zigzag = has_keyword(blobs, ["zigzag", "Z 字", "Z字", "之字", "弯折"])
    is_branching = has_keyword(blobs, ["分支", "1 源", "源到", "source-to", "branching", "branches"])
    if is_funnel:
        if n is None or n < 3:
            return "process-funnel-3"
        if n >= 5:
            return "process-funnel-5"
        return f"process-funnel-{n}"
    if is_branching:
        return "process-branching"
    if is_zigzag:
        return "process-zigzag"
    if is_cycle:
        if n is None or n < 3:
            return "process-cycle-3"
        if n >= 6:
            return "process-cycle-6"
        return f"process-cycle-{n}"
    if is_vertical:
        if n is None or n < 3:
            return "process-vertical-3"
        if n >= 6:
            return "process-vertical-6"
        return f"process-vertical-{n}"
    # Default: arrow horizontal
    if n is None:
        return "process-other"
    if n < 3:
        return "process-arrow-3"
    if n >= 6:
        return "process-arrow-6"
    return f"process-arrow-{n}"


def infer_quadrant(meta: dict, blobs: list[str]) -> str:
    # SWOT detection uses name + native_elements only (visual SoT)
    # (when_to_use / keywords often mention "适合 SWOT 类" for non-SWOT pages,
    # so those signals are too noisy)
    swot_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    if meta.get("variant"):
        swot_blobs.append(str(meta["variant"]))
    if has_keyword(swot_blobs, ["swot", "SWOT", "S W O T", "优势 劣势 机会 威胁", "优劣势机会"]):
        return "quadrant-swot"
    if has_keyword(blobs, ["重要 紧急", "重要紧急", "优先级矩阵", "priority matrix"]):
        return "quadrant-priority-matrix"
    if has_keyword(blobs, ["center figure", "中心 figure", "center number", "中心人物", "中心 puzzle", "puzzle", "center suit", "中心 image", "center image", "中心 chart", "围绕中心"]):
        return "quadrant-with-center"
    if has_keyword(blobs, ["fan", "扇形", "风扇", "blade"]):
        return "quadrant-fan"
    return "quadrant-2x2-generic"


def infer_comparison(meta: dict, blobs: list[str]) -> str:
    # Persona/dual-persona first (more specific visual signal)
    if has_keyword(blobs, ["persona", "双人", "dual persona", "双角色", "双 persona", "dual-persona", "男女 silhouette", "双 chain", "dual chain", "双轨 角色", "双轨角色"]):
        return "comparison-dual-persona"
    # pros/cons must use 优缺点 (CN tokens) not "cons" substring (matches "icons")
    pros_cons_blobs = [meta.get("name", "")] + meta.get("keywords", []) + meta.get("content_intent", [])
    if has_keyword(pros_cons_blobs, ["pros and cons", "pros/cons", "优点 缺点", "优缺点", "好处 坏处"]):
        return "comparison-pros-cons"
    # Arrow-transition: visual signal "→" or "转化" in name/native_elements is more specific
    visual_blobs = [meta.get("name", "")] + meta.get("native_elements", [])
    if has_keyword(visual_blobs, ["转化为", "转化箭头", "→", "input → output", "a → b"]):
        return "comparison-arrow-transition"
    if has_keyword(blobs, ["前后对比", "过去 现在", "before-after", "before vs after", "before/after"]):
        return "comparison-before-after"
    # generic before/after detection — only from primary visual signal
    if has_keyword(visual_blobs, ["before", "after", "前后"]):
        return "comparison-before-after"
    n = extract_n(blobs)
    if n is not None and n == 4:
        return "comparison-tier-4"
    if n is not None and n == 3:
        return "comparison-tier-3"
    if n == 2:
        return "comparison-2col"
    return "comparison-other"


def infer_other(meta: dict, blobs: list[str]) -> str:
    """layout_type==other category - tools / promo / tree / misc."""
    if has_keyword(blobs, ["iSlide", "islide"]):
        if has_keyword(blobs, ["library", "diagram", "icon-library", "vector", "picture", "插图库", "矢量库", "图标库", "图片库"]):
            return "other-islide-library"
        if has_keyword(blobs, ["promo", "90%", "广告", "节省 90%", "节省 ppt", "saves you"]):
            return "other-islide-promo"
        # design criteria / tool
        return "other-islide-tool"
    if has_keyword(blobs, ["tree", "层级", "组织架构", "hierarchy"]):
        return "other-tree-hierarchy"
    return "other-misc"


INFERENCE = {
    "cover": infer_cover,
    "toc": infer_toc,
    "section_divider": infer_section_divider,
    "summary": infer_summary,
    "closing": infer_closing,
    "quote": infer_quote,
    "single_focus": infer_single_focus,
    "cards": infer_cards,
    "bullet_list": infer_bullet_list,
    "data": infer_data,
    "timeline": infer_timeline,
    "pyramid": infer_pyramid,
    "venn": infer_venn,
    "radial": infer_radial,
    "process_flow": infer_process_flow,
    "quadrant": infer_quadrant,
    "comparison": infer_comparison,
    "other": infer_other,
}


def infer_variant(meta: dict) -> str:
    lt = meta.get("layout_type", "")
    if lt not in INFERENCE:
        return "other-misc"
    blobs = []
    if meta.get("name"):
        blobs.append(meta["name"])
    blobs.extend(meta.get("native_elements", []))
    blobs.extend(meta.get("keywords", []))
    blobs.extend(meta.get("content_intent", []))
    blobs.extend(meta.get("when_to_use", []))
    if meta.get("variant"):
        blobs.append(str(meta["variant"]))
    if meta.get("layout_hint"):
        blobs.append(str(meta["layout_hint"]))
    return INFERENCE[lt](meta, blobs)


def rewrite_yaml_with_variant(path: Path, new_variant: str) -> bool:
    """Rewrite yaml file to set variant=new_variant, preserve key order if possible."""
    text = path.read_text(encoding="utf-8")
    # Try simple regex replacement first to keep formatting
    if re.search(r"^variant:\s+.+$", text, re.M):
        new_text = re.sub(r"^variant:\s+.+$", f"variant: {new_variant}", text, count=1, flags=re.M)
    else:
        # No variant line — insert before layout_hint / page_number / template_name
        # Find insertion point: after `native_elements: ...` block, or before `page_number`
        # Simplest: insert before `page_number:` (every page has it)
        if re.search(r"^page_number:", text, re.M):
            new_text = re.sub(
                r"^(page_number:)",
                f"variant: {new_variant}\n\\1",
                text,
                count=1,
                flags=re.M,
            )
        else:
            # Append at end
            new_text = text.rstrip() + f"\nvariant: {new_variant}\n"
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main(dry_run: bool = False) -> int:
    page_files = sorted(ITEMS_ROOT.glob("*/pages/*/meta.yaml"))
    print(f"Found {len(page_files)} page meta.yaml files")
    by_variant: dict[str, int] = {}
    changes = 0
    no_change = 0
    samples = {}
    for p in page_files:
        with open(p, encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        new_variant = infer_variant(meta)
        old_variant = meta.get("variant")
        by_variant[new_variant] = by_variant.get(new_variant, 0) + 1
        if new_variant != old_variant:
            if not dry_run:
                rewrite_yaml_with_variant(p, new_variant)
            changes += 1
        else:
            no_change += 1
        # Capture sample
        if new_variant not in samples:
            samples[new_variant] = str(p.relative_to(REPO))
    print(f"\nChanged: {changes} / No-change: {no_change} / total: {len(page_files)}")
    print(f"\nUnique variants used: {len(by_variant)}")
    for v, n in sorted(by_variant.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {v}")
    return 0


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sys.exit(main(dry_run=dry))
