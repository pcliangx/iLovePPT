# pptx-deck 主流程（Claude 执行）

端到端：用户 brief → 完整 .pptx。机械部分由 build.py 做，智能部分由 Claude 照本文档做。
二者用 deck_plan.json 接缝隔开。

## 接缝：deck_plan.json

Claude 产出、build.py 消费。schema：

```json
{
  "theme": "tech_blue",
  "output": "./out/deck.pptx",
  "slides": [
    {"layout": "cover", "title": "...", "subtitle": "..."},
    ...
  ]
}
```

`theme` 为 `"tech_blue"` 或 `.pptx` 模板路径（见 [template-extract.md](template-extract.md)）。

## 流程（Claude 逐步执行）

1. **读 brief** —— 用户的自由描述或 brief.yaml。确认有：主题、章节大纲、输出路径意图。
2. **图层规划** —— 按 [diagram-planning.md](diagram-planning.md) 判断哪些章节配图。需图的，先调 [[diagram]] skill 出 PNG。
3. **逐页拓写** —— 在展开每页之前，先按 [content-writing.md](content-writing.md) 的「deck 级论证结构」设计好行动式标题与 Minto 论证弧（通过 Ghost deck test 后再逐页拓写）。每页选合适 layout（11 种，见 SKILL.md）。配图页用 `pic_text`，`image_path` 指向第 2 步生成的 PNG。
4. **写 deck_plan.json** —— 把 theme / output / slides 写成 JSON 文件。
5. **构建** —— `python3 build.py deck_plan.json`，产出 .pptx + 每页渲染 PNG。
6. **视觉自检** —— 按 [visual-qa.md](visual-qa.md) 逐页 Read 渲染 PNG，发现问题改 deck_plan.json，重跑 build.py。至多 3 轮，仍不过的页标 review-needed。
7. **交付** —— 最终 .pptx + review-needed 清单（若有）。

## build.py 的能力边界

build.py 只做机械构建：deck_plan.json → .pptx + PNG。它**不**拓写文案、**不**规划图、**不**做视觉自检。那些是 Claude 照本文档及子文档做的智能步骤。

CLI：`python3 build.py deck_plan.json [--no-render]`

## 11 种 layout

cover / toc / section_divider / single_focus / compare / cards / bullet_list / table / pic_text / summary / closing。各 layout 的字段见 [content-writing.md](content-writing.md)；选型规则见同文档。

## Anti-prompt

- 不要指望跑 build.py 就能从 brief 直接出好 deck —— 它只构建，智能在 Claude。
- 不要跳过视觉自检（第 6 步）就交付。
- 配图必须在写 deck_plan.json 之前生成好 PNG（build.py 不画图）。
