# Visual Patterns Library

**iLovePPT 的视觉模式知识库 + RAG 检索系统**。

让 `iloveppt-author` / `iloveppt`(Step 4 加视觉)在拓写 / 加视觉时**先查这个 library 找最匹配的 pattern**,而不是凭空造或局限于 13 个内置 layout。

---

## 目录结构

```
library/visual-patterns/
├── README.md                    本文件
├── INDEX.md                     人 + LLM 可读的 pattern 索引(grep 用)
├── ingest_workflow.md           ingest 流程(我 + 用户协作)
├── search.py                    底层查询 CLI
├── search.sh                    wrapper(agent 通过 Bash 调,自动用 venv)
├── patterns/                    pattern 主体
│   └── <id>/
│       ├── preview.png          视觉参考(从原始模板抠的那页)
│       └── pattern.yaml         metadata(给 LLM + RAG 用)
├── _source_inspiration/         用户上传的原始模板归档(.pptx / .png)
└── _rag/                        RAG infrastructure
    ├── .env                     API key + model 配置(gitignored,绝不 commit)
    ├── .venv/                   Python 3.11 精简 venv ~25MB(gitignored)
    ├── requirements.txt         deps:sqlite-vec + pyyaml(不再要 torch)
    ├── qwen_embedding.py        共享 lib:DashScope API 客户端 + sqlite-vec schema
    ├── embed_text.py            扫 patterns/*/pattern.yaml → 写 text_emb
    ├── embed_image.py           扫 patterns/*/preview.png → 写 image_emb
    └── patterns.sqlite          单 sqlite-vec DB 含 patterns + text_emb + image_emb 三表(gitignored)
```

---

## 三种使用场景

### 场景 1 · agent 查 pattern(主用法)

`iloveppt-author` 拓写 page X 时,通过 search.sh wrapper(自动用 venv,无需关心 Python 路径):

```bash
# 在 Stage D 拓写前,查 library 找匹配 pattern:
library/visual-patterns/search.sh \
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

iloveppt Step 1 看到 `pattern: pdca-loop` 注释 → Read pattern.yaml 看 `fallback_rendering` → 按指示渲染。

### 场景 2 · 用户给新模板 → 入库

用户:**"我有这份 .pptx 模板,请把里面的 pattern 入库"**

流程见 `ingest_workflow.md`。简版:
1. 渲染 .pptx 每页 → PNG
2. 我(Claude)Read 每页 → 推断 pattern.yaml 草稿
3. 用户审 / 改名 / 弃用
4. 通过的入 `patterns/<id>/`(pattern.yaml + preview.png)
5. 跑 `_rag/.venv/bin/python _rag/embed_text.py` + `embed_image.py` 重生 vec DB(text + image 都要 embed)

### 场景 3 · 人翻 INDEX.md(浏览)

INDEX.md 是人也能直接读的 markdown,按 category 分组,每个 pattern 一行描述 + 关键词。
新人想看"我们有哪些 pattern"直接打开 INDEX.md。

---

## 安装(hosted API,不需要 torch / sentence-transformers)

**Embedding 模型已切到阿里云 DashScope `tongyi-embedding-vision-plus-2026-03-06`**(同维度 1152,文本 + 图像同 API · 多模态原生)。

### ⚠️ API key 安全

`_rag/.env` 文件已 gitignored。**绝不 commit key**。配置方式:

```bash
# 已写好的方式 1(本仓库已配)
cat library/visual-patterns/_rag/.env
# DASHSCOPE_API_KEY=sk-...
# DASHSCOPE_EMBED_MODEL=tongyi-embedding-vision-plus-2026-03-06
# DASHSCOPE_API_URL=https://dashscope.aliyuncs.com/...

# 方式 2(环境变量,优先级 > .env)
export DASHSCOPE_API_KEY=sk-...
```

**安全建议**:若 key 在任何渠道明文外泄过(对话 / 截图 / 邮件)→ 去 https://dashscope.console.aliyun.com 立即 rotate。

### 直接用(venv 已建好)

```bash
# 重建 vec DB(加新 pattern 后必跑)· text 入库
library/visual-patterns/_rag/.venv/bin/python library/visual-patterns/_rag/embed_text.py

# image 入库(给 patterns 加 preview.png 后跑)
library/visual-patterns/_rag/.venv/bin/python library/visual-patterns/_rag/embed_image.py

# 查询(agent 用 search.sh wrapper)
library/visual-patterns/search.sh --query "PDCA 改进循环" --top-k 3 --format json
```

### 查询模式(3 mode)

```bash
# text mode(默认):text query → 查 text_emb 表
library/visual-patterns/search.sh --query "PDCA 改进循环" --top-k 5

# image mode(text→image 跨模态):用语言描述视觉风格找视觉相似 pattern
library/visual-patterns/search.sh --query "现代极简 蓝白" --mode image --top-k 5

# hybrid mode(融合,默认权重 text 0.6 + image 0.4)
library/visual-patterns/search.sh --query "PDCA + 现代极简" --mode hybrid --top-k 5

# image→image:用一张参考图找视觉相似 pattern(极强!)
library/visual-patterns/search.sh --query-image /path/to/inspiration.png --mode image --top-k 5
```

### 从头重建 venv(换机器 / 删了 .venv)

```bash
cd library/visual-patterns/_rag
python3.11 -m venv .venv             # 任意 Python 3.10-3.13(stdlib urllib 够,无 torch 依赖)
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt   # 只装 sqlite-vec + pyyaml,总 < 10MB

# 配 key
cp .env.example .env  # (若提供模板)
$EDITOR .env

# 验证 API 可达
.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from qwen_embedding import embed_text
v = embed_text('test')
print(f'API OK, dim {len(v)}')
"
```

---

## 设计原则

1. **LLM-first 索引**:INDEX.md 是给 LLM 看的语义索引,关键词丰富 + 结构化
2. **RAG 是 scale 工具**:< 30 pattern 时 grep INDEX.md 就够;30+ pattern 时 search.sh(RAG)更快更准
3. **原生多模态**:`search.sh --mode text|image|hybrid` 都已可用 —— text/image 同维 1152,跨模态查询直接走同一 API,**不再需要 CLIP 分立 stub**
4. **patterns 是产品资产**:版本控制(pattern.yaml + preview.png 入 git);`_rag/patterns.sqlite` 是 generated,gitignore
5. **API key 安全**:`_rag/.env` gitignored,绝不 commit;若 key 泄漏立刻去 dashscope 控制台 rotate
6. **pattern 是 inspiration,不一定有 rendering 实现**:第一版很多 pattern 只是"参考",author / designer 看到后用 diagram skill 现画。常用 pattern 后续可投资 Python `make_*` 函数加速渲染

---

## 跟现有 iLovePPT 的关系

| 资产 | 性质 | 跟 library 关系 |
|---|---|---|
| `${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/themes/tech_blue.py` | 13 内置 layout(Python make_*) | library pattern 可标 `matches_iloveppt_layout: <name>` 直接调用 |
| `${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/` | 现画工具(draw.io / matplotlib / mermaid) | library pattern 没有 Python 实现时,fallback 到这里现画 |
| `${CLAUDE_PROJECT_DIR}/templates/<name>.yaml` | .pptx 模板提取的 4 级 token | 跟 library 平行;templates 管"主题色字体",library 管"视觉表达模式" |
| `decks/<slug>/` | 单个 deck 工作目录 | library 是跨 deck 的知识库,decks/ 是单 deck 工作产物 |
