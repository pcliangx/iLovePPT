# 图层规划（diagram planning）

> workflow 第 3 步。读完 brief、加载主题之后、拓写 outline 之前执行。
> 目标：**主动判断哪些章节该配图**，而不是等内容写完才发现"全是文字墙"。

## 核心原则：一图胜千文

**能用图形表达的观点，就不要用文字堆。** 凡涉及结构、流程、关系、数据对比的
内容，都应主动调用 AI 绘图能力（[[diagram]] skill）生成图——一张清晰的图，
胜过三行 bullet。

判断犹豫时**倾向于画图**：文字墙是 deck 最大的失败模式。本步骤的存在就是为了
强制兑现这条原则——读完 brief 立刻想"哪里能上图"，而不是事后补救。

## 为什么要单独一步

如果不主动规划，deck 很容易变成纯文字 bullet 堆叠——读者看不懂系统结构、记不住流程。
图层规划强制在拓写文案**之前**就回答："这一章，用一张图能不能讲得更清楚？"

一个好的 deck，每 4-5 页至少有 1 张图（架构 / 流程 / 数据 / 关系）。

## 输入与输出

**输入**：用户的 brief（自由描述或 brief.yaml）—— Claude 读取后得到的章节大纲（`outline`）与关键要点（`key_points`）。

**输出**：`diagram_plan` —— 一个 list，每项标记一个建议配图的章节：

```json
[
  {
    "section_idx": 2,
    "section": "技术架构",
    "diagram_type": "arch_diagram",
    "tool": "draw.io",
    "intent": "展示三层架构与模块依赖"
  }
]
```

## 决策规则：4 类图的触发判断

逐个扫描 `outline` 章节（结合 `key_points` 语义），判断是否命中以下信号。
每个章节最多配 1 张图。

| 内容信号（章节标题 / 要点里出现） | 图类型 `diagram_type` | 推荐工具 `tool` | 落到 [[diagram]] 的子文档 |
|---|---|---|---|
| 系统由…组成、分 N 层、模块 / 组件 / 微服务 / 技术栈 / 拓扑 | `arch_diagram` | draw.io | `drawio.md` |
| 步骤 / 阶段 / 流程 / 先后 / 时序 / 环节 / pipeline | `flow` | draw.io | `drawio.md` |
| 趋势 / 增长 / 占比 / 对比 / 指标 / 百分比 / 数据 | `chart` | matplotlib | `matplotlib.md` |
| 角色关系 / 依赖 / 交互 / 连接 / 映射（≤ 5 节点） | `simple_relation` | draw.io | `drawio.md` |

**结构性图形（流程图 / 架构图 / 矩阵 / 决策树 / 关系图）一律优先 draw.io** —— 配色精确、布局可控、跨图视觉一致。Mermaid 仅作极快草图备选,数据图用 matplotlib;`simple_relation` 若需在 PowerPoint 内可编辑,可改用 pptx-native。完整决策表见 [[diagram]] `SKILL.md`。

### 判断时的注意点

- **章节标题是主要线索，`key_points` 是补充**：标题"落地路径"含"路径"偏流程，但若要点全是数字，则应选 `chart`。
- **一个章节只配最相关的一张图**：既有架构又有流程时，挑承载信息量最大的。
- **不是每章都要图**：纯观点 / 背景陈述类章节（如"背景与意义"）通常不配图。
- **节点数决定架构图 vs 关系图**：> 5 节点或有嵌套层次走 `arch_diagram`；≤ 5 节点的简单关系走 `simple_relation`。两者都用 draw.io 出图；`simple_relation` 若需 PowerPoint 内可编辑可改 pptx-native。

## Claude 语义判断

图层规划是一个 **Claude 执行的推理步骤**，没有对应的 Python 函数。

Claude 读 brief 后按本文档的决策规则做**语义判断**——理解每章真正讲什么，而不只是匹配字面关键词。纯关键词匹配容易漏掉语义（如"评审机制"其实是流程图）；Claude 必须推理每章的本质内容再决策。

产出是一个 `diagram_plan` JSON 列表（见上方示例），Claude 在进入页面拓写步骤前在内部记录这个列表，并在写 `deck_plan.json` 时据此将对应页改为 `pic_text` 版式并填入 `image_path`。

## 与 deck_plan.json / pic_text 的衔接

Claude 在图层规划后进行页面拓写，将需要配图的章节直接写成 `pic_text` 版式：

**工作流程：**

1. Claude 先调 [[diagram]] skill，按 `diagram_plan` 中的 `tool` 生成图 → 得到 PNG 路径
2. 在 `deck_plan.json` 中，该章节对应的 slide 直接写成 `pic_text` 版式，填入 `image_path`（PNG 路径）与 `points`（右侧说明卡片，从要点提炼）

```json
{
  "layout": "pic_text",
  "title": "技术架构",
  "image_path": "diagrams/arch_diagram.png",
  "points": [
    {"title": "三层架构", "body": "前端 / API / 数据层解耦"},
    {"title": "微服务", "body": "独立部署，按需扩容"},
    {"title": "数据流", "body": "事件驱动，低延迟"},
    {"title": "安全", "body": "网关统一鉴权"}
  ]
}
```

图必须在写 `deck_plan.json` **之前**生成好，`build.py` 会直接用 `image_path` 嵌入。

## 密度自检

拓完 outline 后回头看 `diagram_plan`：

- 总页数 ÷ 图数 > 5 → 偏少，重新扫一遍有没有漏判的流程 / 架构章节
- 连续 3 张图 → 偏多，挑信息量最大的保留，其余降级为 bullet
- 全 deck 0 张图 → 几乎一定是漏判，重新审视每章

## Anti-prompt

- 不要等文案写完才想图——图层规划必须在页面拓写（写 deck_plan.json）之前
- 不要每章都硬塞图——背景 / 观点类章节不配图
- 不要混用工具——同一 deck 的图尽量同一套工具，避免视觉割裂（见 [[diagram]] 选型表）
- 不要只信骨架的关键词命中——Claude 必须做语义判断覆盖
