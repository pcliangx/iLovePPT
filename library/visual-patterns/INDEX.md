# Visual Patterns 索引

> **给 author / designer 用** —— Read 全文 + 按 content intent 选 pattern → Read 对应 pattern.yaml 看细节。
> **库小时(< 30 pattern)**直接读这份 INDEX 选;**库大时**用 `search.sh --query "..."` RAG 检索(多模态:text / image / hybrid 3 mode)。
>
> 维护:加新 pattern 后,本文件 + `_rag/embed_text.py` 一起更新。

---

## 当前状态:**空库**

库已清空,等待用户提供新素材后重新入库。

按 `ingest_workflow.md` 流程入库:用户给 .pptx 或 PNG → 主线程推断 pattern.yaml 草稿 → 用户审 → 入 `patterns/<id>/`(pattern.yaml + preview.png)→ 跑 `_rag/.venv/bin/python _rag/embed_text.py` + `embed_image.py`(双向多模态)→ 同步更新本 INDEX.md。

---

## 索引规则(入库时按此格式加 entry)

每个 entry 一行:`id` · 类别 · `n_items` · 一句话 intent · **关键词** · **何时用** · **何时不用** · 匹配 layout

按 category 分组 → 6 类:**process / cycle / comparison / hierarchy / data / relationship**

---

## category: process(顺序 / 步骤 / 流程)

*暂无 pattern · 入库后加 entry*

## category: cycle(循环 / 闭环)

*暂无 pattern · 入库后加 entry*

## category: comparison(对比 / 对决)

*暂无 pattern · 入库后加 entry · 现有 layout `compare` / `compare_pk` / `matrix_2x2` 也可用*

## category: hierarchy(层级 / 结构)

*暂无 pattern · 入库后加 entry*

## category: data(数据 / 图表)

*用 `${CLAUDE_PROJECT_DIR}/skills/diagram/matplotlib_rc.py` 现画 · 通常不在本 library 范围*

## category: relationship(关系 / 互动)

*暂无 pattern · 入库后加 entry*

---

## entry 模板(入库时复制此模板填)

```markdown
### <id-kebab-case>
- intent:<一句话 content 意图>
- n_items:<数字>
- 关键词:<中英文同义词列表>
- 用于:<典型场景>
- **不用于**:<边界 / 替代方案>
- 匹配现有 layout:**<layout 名 或 无>**
```

---

## 入库工作流

完整流程见 [`ingest_workflow.md`](ingest_workflow.md)。简版:

1. 用户:`cp 新模板.pptx ${CLAUDE_PROJECT_DIR}/library/visual-patterns/_source_inspiration/`
2. 用户:跟主线程说"入库"
3. 主线程:渲染每页 PNG → Read → 推断 pattern.yaml 草稿
4. 主线程:列 draft 给用户审(改名 / 弃用 / 调字段)
5. 通过的入 `patterns/<id>/`(pattern.yaml + preview.png)
6. 跑 embedding:`${CLAUDE_PROJECT_DIR}/library/visual-patterns/_rag/.venv/bin/python ${CLAUDE_PROJECT_DIR}/library/visual-patterns/_rag/embed_text.py`
7. 同步更新**本 INDEX.md**(加 entry 到对应 category)
8. 验证:`${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh --query "<新 pattern 关键词>" --top-k 3`

---

## 当前 infrastructure(已就绪 · 多模态)

✅ Python 3.11 venv:`_rag/.venv/`(sqlite-vec + pyyaml,精简版 < 10MB · 不再要 torch)
✅ Embedding 模型:**阿里云 DashScope · tongyi-embedding-vision-plus-2026-03-06**(dim 1152 · 文本图像同 API)
✅ RAG 脚本:`_rag/embed_text.py`(文本)+ `_rag/embed_image.py`(图像 · 多模态!)
✅ 查询 CLI:`search.sh`(支持 text / image / hybrid 3 mode)
✅ API key:`_rag/.env`(gitignored)
✅ ingest 文档:`ingest_workflow.md`

入库新 pattern → 双向 embed → 多模态 search 全链路已通,只等用户提供素材。

## 3 mode 用法 quick ref

| mode | query 类型 | 表 | 用途 |
|---|---|---|---|
| text(默认) | 文本 | text_emb | 按 content intent 找匹配 pattern |
| image | 文本 or 图像 | image_emb | 按视觉风格找(text→image 描述 or image-image 上传参考图) |
| hybrid | 文本 | text_emb + image_emb 融合 | 综合 content + 视觉匹配 |

`search.sh --query "..." --mode <text|image|hybrid>` 或 `search.sh --query-image <path>`。
