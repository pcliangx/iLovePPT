"""pptx skill smoke test — 8 行核心代码生成 3 页 .pptx。

跑通=helper + 字体 EA + 渲染管线 OK。

依赖：python-pptx, lxml,（可选验证）soffice + pdftoppm
"""
import sys
from pathlib import Path

_helpers_path = str(Path(__file__).parent.parent)
if _helpers_path not in sys.path:
    sys.path.insert(0, _helpers_path)

from pptx import Presentation
from pptx.util import Inches
import helpers as H


def main(out="/tmp/iloveppt_minimal.pptx"):
    prs = Presentation()
    prs.slide_width = H.SLIDE_W
    prs.slide_height = H.SLIDE_H

    # 页 1：封面
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    H.rect(s, 0, 0, H.SLIDE_W, H.SLIDE_H, H.BRAND_DARK)
    box = s.shapes.add_textbox(Inches(0.55), Inches(2.8), Inches(12), Inches(2))
    H.fix_textbox_margins(box.text_frame)
    r = box.text_frame.paragraphs[0].add_run()
    r.text = "iLovePPT minimal smoke test"
    H.set_font(r, size=44, bold=True, color=H.WHITE)

    # 页 2：内容（card + bullets）
    s = prs.slides.add_slide(prs.slide_layouts[6])
    H.card(s, Inches(0.55), Inches(1.4), Inches(12.2), Inches(5.6),
           fill=H.BRAND_TINT, border=H.GRAY_300, accent=H.BRAND_PRIMARY)
    H.bullets(s, Inches(1.0), Inches(1.7), Inches(11), Inches(5),
              items=["验证 EA 字段中文不 fallback",
                     "验证 textbox margin 归零",
                     "验证 card 圆角 + 左色条",
                     "验证 bullet ▎ 现代风"])

    # 页 3：表格
    s = prs.slides.add_slide(prs.slide_layouts[6])
    H.table_modern(s, Inches(0.55), Inches(1.4), Inches(12.2), Inches(3),
                   headers=["指标", "Q1", "Q2", "Q3"],
                   rows=[["收入", "100", "120", "150"],
                         ["利润", "20", "25", "32"],
                         ["客户数", "8", "12", "18"]])

    prs.save(out)
    print(f"✅ saved: {out}")


if __name__ == "__main__":
    main()
