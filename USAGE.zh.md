# iLovePPT 使用说明

> 端到端 PPT 生成工具：给主题/要点 → Claude 产出 `deck_plan.json` → `build.py` 渲染为 `.pptx` + PNG → Claude 视觉自检。

---

## 通过 agent 使用(主推)

iLovePPT 作为 Claude Code agent 部署:

```
@agent-iloveppt 做一份 <主题> 的 PPT,受众 <executive|technical|general|sales|investor>,时长 <N> 分钟
```

agent 两阶段:

- **Phase 1**:解析 brief → 设计大纲(action title + Minto + ghost deck test)→ 规划图层 → 返回 outline 结构供你批准
- **Phase 2**(批准后):生成配图 → 写 deck_plan.json → 跑 build.py → 视觉自检(≤ 3 轮)→ 返回 `.pptx` 路径 + review-needed 清单

把 agent 共享给别的项目:把本仓库的 `.claude/agents/iloveppt.md` 拷或软链到目标项目的 `.claude/agents/iloveppt.md`(同时需要 `skills/` 也可访问 —— 与现在的 skill 链接方式一致)。

详细设计:[docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md](docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md)。

---

## 一、这是什么

iLovePPT 是一个 Claude Code skill 库，目标是**复制人类快速生成 PPT 的能力**。你输入主题与要点，工具自动：

- 拓写每页文案（标题/要点/对比/数据）
- 选择合适的版式（11 种 layout）
- 规划并嵌入架构图、流程图、可视化（Claude 驱动，引用 `pic_text` 页）
- 套用统一风格（默认科技蓝主题）
- 逐页渲染 PNG + Claude 视觉自检 + 修复 deck_plan.json 后 rebuild

最终产物是一份可以直接打开的 `.pptx` 文件。

**关键概念**：`build.py` 是纯机械构建器（`deck_plan.json → .pptx + PNG`），不含任何 AI 逻辑。所有内容规划、图层决策、视觉自检均由 Claude 驱动。

---

## 二、快速开始（3 步）

### 1. 装依赖

```bash
git clone git@github.com:pcliangx/iLovePPT.git
cd iLovePPT
bash skills/pptx/scripts/check_deps.sh
```

脚本会输出 ✅/❌/⚠️ 清单。缺啥按提示装：

```bash
pip3 install python-pptx lxml 'markitdown[pptx]' Pillow pyyaml
brew install --cask libreoffice
brew install poppler
# 可选（画架构图）
brew install --cask drawio
brew install mermaid-cli
pip3 install matplotlib
```

**⚠️ macOS 用户注意**：LibreOffice 默认没装微软雅黑，渲染中文会 fallback 到 PingFang SC。如要与 Windows PowerPoint 显示一致，把微软雅黑字体文件放入 `~/Library/Fonts/`。

### 2. 跑示例

```bash
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json
```

产物：`deck_plan.json` 中 `output` 字段指定的路径（参考成品，深海蓝 + 科技蓝主题）。

### 3. 自定义你的 PPT

**方式 A：自由对话**

直接告诉 Claude "帮我做一份 XX 的 PPT"，Claude 追问必填字段后自动开始 7 步生成流程。

**方式 B：brief.yaml**

复制 `brief.example.yaml` 改字段：

```yaml
title: "你的 PPT 标题"
subtitle: "副标题"
outline:
  - "章节 1"
  - "章节 2"
  - "..."
key_points:
  - "关键论点 1"
  - "关键论点 2"
theme: tech_blue
output: ./my_deck.pptx
```

然后告诉 Claude "用这个 brief.yaml 帮我生成 PPT"。Claude 读取 brief，产出 `deck_plan.json`，再调用：

```bash
python3 skills/pptx-deck/build.py deck_plan.json
```

---

## 三、流水线与 deck_plan.json

### 完整流水线

```
用户 brief（brief.yaml 或自由对话）
    │
    ▼  Claude 7 步工作流（读 brief → 图层规划 → 拓写文案 → 写 deck_plan.json）
    │
    ▼  Claude 产出
deck_plan.json
    │
    ▼  build.py 机械执行（无 LLM，CLI：python3 build.py deck_plan.json）
.pptx + PNG（逐页渲染）
    │
    ▼  Claude 视觉 QA（Read PNG → 12 项 checklist → 修 deck_plan.json → rebuild）
最终产物
```

### deck_plan.json 结构

`deck_plan.json` 是 Claude 与 build.py 之间的分界面：

```json
{
  "theme": "tech_blue",
  "output": "./my_deck.pptx",
  "slides": [
    { "layout": "cover", "title": "...", "subtitle": "..." },
    { "layout": "toc", "sections": ["章节 1", "章节 2"] },
    { "layout": "bullet_list", "title": "...", "items": ["...", "..."] }
  ]
}
```

Claude 负责产出这个 JSON；build.py 负责将其渲染为 .pptx + PNG。

### build.py CLI

```bash
# 完整渲染（.pptx + PNG）
python3 skills/pptx-deck/build.py deck_plan.json

# 仅生成 .pptx，跳过 PNG 渲染
python3 skills/pptx-deck/build.py deck_plan.json --no-render
```

---

## 四、三个 skill 的关系

| Skill | 干嘛的 | 何时单独用 |
|---|---|---|
| `pptx-deck` | 端到端生成（主入口） | 给主题让它写整份 PPT |
| `pptx` | 底层 .pptx 读写 | 只想读已有 PPT，或局部改文字 |
| `diagram` | 架构图/流程图/数据可视化 | 只想出一张图 |

`pptx-deck` 内部会调用 `pptx` 与 `diagram`，你通常只跟 `pptx-deck` 打交道。

---

## 五、在 Claude Code 里用

把 skills/ 链接到目标项目：

```bash
ln -s /path/to/iLovePPT/skills/pptx       /path/to/your-project/.claude/skills/pptx
ln -s /path/to/iLovePPT/skills/pptx-deck  /path/to/your-project/.claude/skills/pptx-deck
ln -s /path/to/iLovePPT/skills/diagram    /path/to/your-project/.claude/skills/diagram
```

之后跟 Claude 说"帮我做一份 XX 的 PPT"，"我要做路演 deck"等，Claude 会自动触发对应 skill。

---

## 六、内置主题与自定义

### 内置：科技蓝
- 主色 `#1E6FE0` + 深海蓝 `#0B2A4A` + 浅蓝底 `#E6F0FC` + 青绿点睛 `#00D1C1`
- 字体：微软雅黑（中文）+ Helvetica Neue（英文/数字）

### 其他 10 套预设色板
见 `skills/pptx/design-system.md`：商务深蓝 / 党政红 / 极简白 / 咨询黑 / 莫兰迪灰 / 薄荷绿 / 暖橙 / 灰盐 / 酒红。

切换方法：改 `skills/pptx/helpers.py` 顶部的 `BRAND_*` 常量。

### 用你自己的 .pptx 提取主色与字体

在 brief.yaml 里把 theme 改为 .pptx 路径：

```yaml
theme: /path/to/your_template.pptx
```

工具会调用 `_extract_theme_from_pptx` 提取模板的主色与字体，生成临时主题模块。详见 `template-extract.md`。

---

## 七、11 种版式

| 版式 | 适用场景 |
|---|---|
| `cover` | 封面 |
| `toc` | 目录页 |
| `section_divider` | 章节扉页 |
| `single_focus` | 单点强调（大数字+大字） |
| `compare` | 二栏对比 |
| `cards` | 三栏卡片 |
| `bullet_list` | 5 点列表 |
| `table` | 数据表格 |
| `pic_text` | 左图右文（图+4 卡） |
| `summary` | 总结页 |
| `closing` | 封底 |

详细文案规范见 `skills/pptx-deck/content-writing.md`。

---

## 八、视觉自检流程

每生成一页，build.py 渲染 PNG，Claude 再逐页：
1. Read 该 PNG，按 12 项 checklist 找问题
2. 若有问题，修 deck_plan.json（字号过大 → 调小 / 文字过长 → 裁减）
3. 重新调用 build.py rebuild
4. 修 ≤ 3 次仍失败 → 标记 `review_needed`，人工最后审

12 项 checklist 与 prompt 模板见 `skills/pptx-deck/visual-qa.md`。

---

## 九、测试与验证

```bash
python3 -m pytest tests/ -v                                      # 单元/集成测试
python3 skills/pptx/examples/minimal_deck.py                    # pptx skill smoke test
bash skills/diagram/examples/render.sh                          # diagram smoke test
bash evals/run_eval.sh                                          # 回归 eval 集
```

---

## 十、目录结构

```
iLovePPT/
├── README.md
├── pyproject.toml
├── USAGE.zh.md                       # 本文件
├── evals/                            # 回归 eval 集（runner: bash evals/run_eval.sh）
├── docs/superpowers/{specs,plans}/   # 设计文档 & 实施计划
└── skills/
    ├── pptx-deck/                    # 端到端生成（主）
    │   ├── build.py                  # 机械构建器：deck_plan.json → .pptx + PNG
    │   ├── brief.example.yaml        # 用户输入模板（给 Claude 读）
    │   └── examples/demo_plan.json   # 可直接运行的演示 deck_plan
    ├── pptx/                         # 底层读写
    └── diagram/                      # 架构图/可视化
```

---

## 十一、常见问题

**Q: 生成的 PPT 字体不对/中文是花体？**
A: macOS 没装微软雅黑，LibreOffice 渲染时 fallback。装雅黑，或接受 fallback（Windows PowerPoint 打开会正常）。

**Q: soffice / pdftoppm 命令找不到？**
A: 跑 `bash skills/pptx/scripts/check_deps.sh`，按提示装。

**Q: 生成的 PPT 卡片重叠/文字溢出？**
A: Claude 视觉自检循环会修 deck_plan.json 后 rebuild。若仍不行，看终端的 `review_needed` 清单，手动调整 deck_plan.json 里对应页的字段。

**Q: 想加自己的主题？**
A: 复制 `skills/pptx-deck/themes/tech_blue.py` 为 `your_theme.py`，改 PRIMARY/PRIMARY_DEEP 等常量，在 `build.py` 的 `THEMES` 字典里注册。

**Q: 想读已有 PPT 提取内容？**
A: `python3 -m markitdown your_deck.pptx` 一行搞定。

---

## 十二、设计文档

- v2 完整设计（当前）：`docs/superpowers/specs/2026-05-22-iloveppt-v2-design.md`
- v2 实施计划（当前）：`docs/superpowers/plans/2026-05-22-iloveppt-v2.md`
- v1 初版设计（历史）：`docs/superpowers/specs/2026-05-21-killppts-skill-design.md`
- v1 初版计划（历史）：`docs/superpowers/plans/2026-05-21-killppts-skill.md`

---

GitHub: `https://github.com/pcliangx/iLovePPT`
