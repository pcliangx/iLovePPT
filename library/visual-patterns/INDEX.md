# Visual Patterns 索引

> **给 author / designer 用** —— Read 全文 + 按 content intent 选 pattern → Read 对应 pattern.yaml 看细节。
> **库小时(< 30 pattern)**直接读这份 INDEX 选;**库大时**用 `python3 search.py --query "..."` RAG 检索。
>
> 维护:加新 pattern 后,本文件 + `_rag/embed_text.py` 一起更新。

---

## 当前状态:**空库**

库已清空,等待用户提供新素材后重新入库。

按 `ingest_workflow.md` 流程入库:用户给 .pptx 或 PNG → 主线程推断 pattern.yaml 草稿 → 用户审 → 入 `patterns/<id>/` → 跑 `_rag/.venv/bin/python _rag/embed_text.py` → 同步更新本 INDEX.md。

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

*用 `skills/diagram/matplotlib_rc.py` 现画 · 通常不在本 library 范围*

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

1. 用户:`cp 新模板.pptx library/visual-patterns/_source_inspiration/`
2. 用户:跟主线程说"入库"
3. 主线程:渲染每页 PNG → Read → 推断 pattern.yaml 草稿
4. 主线程:列 draft 给用户审(改名 / 弃用 / 调字段)
5. 通过的入 `patterns/<id>/`(pattern.yaml + preview.png)
6. 跑 embedding:`library/visual-patterns/_rag/.venv/bin/python library/visual-patterns/_rag/embed_text.py`
7. 同步更新**本 INDEX.md**(加 entry 到对应 category)
8. 验证:`library/visual-patterns/search.sh --query "<新 pattern 关键词>" --top-k 3`

---

## 当前 infrastructure(已就绪)

✅ Python 3.11 venv:`_rag/.venv/`(sentence-transformers / sqlite-vec / torch / BGE-zh 全装)
✅ RAG 脚本:`_rag/embed_text.py`(扫 patterns/ 全部 → 写 text.sqlite)
✅ 查询 CLI:`search.sh`(自动用 venv,agent 通过 Bash 调)
✅ ingest 文档:`ingest_workflow.md`

入库新 pattern → embed → search 全链路已通,只等用户提供素材。
