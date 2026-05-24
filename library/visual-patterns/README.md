# Visual Patterns Library

**iLovePPT 的视觉模式知识库 + RAG 检索系统**。

让 `iloveppt-author` / `iloveppt-designer` 在拓写 / 加视觉时**先查这个 library 找最匹配的 pattern**,而不是凭空造或局限于 13 个内置 layout。

---

## 目录结构

```
library/visual-patterns/
├── README.md                    本文件
├── INDEX.md                     人 + LLM 可读的 pattern 索引(grep 用)
├── patterns/                    pattern 主体
│   └── <id>/
│       ├── preview.png          视觉参考(从原始模板抠的那页)
│       ├── pattern.yaml         metadata(给 LLM + RAG 用)
│       └── source_ref.md        来自哪份 .pptx 第几页
├── _source_inspiration/         用户上传的原始模板归档
│   └── <name>.pptx 或 .png
├── _rag/                        RAG infrastructure
│   ├── text.sqlite              文本 embedding(sqlite-vec,生成,gitignore)
│   ├── image.sqlite             图像 embedding(CLIP,Phase 3 启用,gitignore)
│   ├── embed_text.py            (重)生成文本 embedding
│   ├── embed_image.py           CLIP 图像 embedding(stub,Phase 3)
│   └── requirements.txt         Python 依赖
├── search.py                    查询 CLI(agent 通过 Bash 调)
└── ingest_workflow.md           ingest 流程(我 + 用户协作)
```

---

## 三种使用场景

### 场景 1 · agent 查 pattern(主用法)

`iloveppt-author` 拓写 page X 时:

```bash
# 在 Stage D 拓写前,查 library 找匹配 pattern:
python3 library/visual-patterns/search.py \
    --query "3 阶段流程 有验证循环" \
    --category process \
    --top-k 5 \
    --format json
```

返回 top-5 候选 → agent Read 各自 `pattern.yaml` → 选最匹配的 → 在 `content.md` 嵌入注释:

```markdown
## 3. PDCA 持续改进
<!-- pattern: pdca-loop -->

- ...
```

builder Step 1 看到 `pattern: pdca-loop` 注释 → Read pattern.yaml 看 `fallback_rendering` → 按指示渲染。

### 场景 2 · 用户给新模板 → 入库

用户:**"我有这份 .pptx 模板,请把里面的 pattern 入库"**

流程见 `ingest_workflow.md`。简版:
1. 渲染 .pptx 每页 → PNG
2. 我(Claude)Read 每页 → 推断 pattern.yaml 草稿
3. 用户审 / 改名 / 弃用
4. 通过的入 `patterns/<id>/`
5. 跑 `python3 _rag/embed_text.py` 重生 vec DB

### 场景 3 · 人翻 INDEX.md(浏览)

INDEX.md 是人也能直接读的 markdown,按 category 分组,每个 pattern 一行描述 + 关键词。
新人想看"我们有哪些 pattern"直接打开 INDEX.md。

---

## 安装(已激活 · 本仓库使用方式)

**本仓库的 venv 已建好,位于 `_rag/.venv/`(用 Python 3.11,因为 3.14 太新无 torch wheel)。**

直接用 venv 的 Python 跑(不需要 `source activate`):

```bash
# 重建 vec DB(加新 pattern 后必跑)
library/visual-patterns/_rag/.venv/bin/python library/visual-patterns/_rag/embed_text.py

# 查询(agent 通过 Bash 调用)
library/visual-patterns/_rag/.venv/bin/python library/visual-patterns/search.py \
    --query "PDCA 改进循环" --top-k 3 --format json
```

### 如果从头开始重建 venv(例如换机器 / 删了 .venv)

```bash
cd library/visual-patterns/_rag
/Users/pc2026/.local/bin/python3.11 -m venv .venv   # 或任意 Python 3.10-3.13
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt           # ~20s
.venv/bin/python embed_text.py                       # 首次下载 BGE ~100MB,后续秒级
```

**注意**:不要用 Homebrew Python 3.14(torch 没 wheel,源码编译耗时极长)。Python 3.10-3.13 都行。

---

## 设计原则

1. **LLM-first 索引**:INDEX.md 是给 LLM 看的语义索引,关键词丰富 + 结构化
2. **RAG 是 scale 工具**:< 30 pattern 时 grep INDEX.md 就够;30+ pattern 时 search.py(RAG)更快更准
3. **多模态扩展点保留**:`search.py --mode text|image|hybrid`;CLIP 当前是 stub,未来加(用户素材库视觉风格多样化时)
4. **patterns 是产品资产**:版本控制(pattern.yaml + preview.png 入 git);`_rag/*.sqlite` 是 generated,gitignore
5. **pattern 是 inspiration,不一定有 rendering 实现**:第一版很多 pattern 只是"参考",author / designer 看到后用 diagram skill 现画。常用 pattern 后续可投资 Python `make_*` 函数加速渲染

---

## 跟现有 iLovePPT 的关系

| 资产 | 性质 | 跟 library 关系 |
|---|---|---|
| `skills/pptx-deck/themes/tech_blue.py` | 13 内置 layout(Python make_*) | library pattern 可标 `matches_iloveppt_layout: <name>` 直接调用 |
| `skills/diagram/` | 现画工具(draw.io / matplotlib / mermaid) | library pattern 没有 Python 实现时,fallback 到这里现画 |
| `templates/<name>.yaml` | .pptx 模板提取的 4 级 token | 跟 library 平行;templates 管"主题色字体",library 管"视觉表达模式" |
| `decks/<slug>/` | 单个 deck 工作目录 | library 是跨 deck 的知识库,decks/ 是单 deck 工作产物 |
