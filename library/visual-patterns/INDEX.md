# Visual Patterns 索引

> **给 author / designer 用** —— Read 全文 + 按 content intent 选 pattern → Read 对应 pattern.yaml 看细节。
> **库小时(< 30 pattern)**直接读这份 INDEX 选;**库大时**用 `search.sh --query "..."` RAG 检索(多模态:text / image / hybrid 3 mode)。
>
> 维护:加新 pattern 后,本文件 + `_rag/embed_text.py` 一起更新。

---

## 当前状态:**21 patterns**(首批入库 · 来源 `_source_inspiration/patterns.pptx`)

按 category 分组,每个 entry 一行摘要。详细字段(visual_structure / fallback_rendering 等)见各自 `patterns/<id>/pattern.yaml`。

---

## category: process(顺序 / 步骤 / 流程)· 10 个

### timeline-band-3
- intent:3 个时间段的阶段对比,带时段标签(20XX.XX-20XX.XX)
- n_items:3
- 关键词:时间轴 · timeline · phase · milestone · 阶段对比 · 里程碑 · 历程
- 用于:3 段时段对照(季度回顾 / 阶段汇报)· 时段差异需要色块强调
- **不用于**:时段超过 5 段 → quote-timeline-5 / arrow-chain-5-zigzag · 没有时间维度 → cards
- 匹配现有 layout:**无**

### funnel-3stage-icon
- intent:漏斗式 3 阶筛选 / 转化(从宽到窄)
- n_items:3
- 关键词:漏斗 · funnel · conversion · 销售漏斗 · 用户旅程 · AARRR
- 用于:转化 / 筛选场景(强调"从多到少")· 阶段顺序有递减语义
- **不用于**:阶段是平行 → cards · 强调循环 → cycle-donut-3-icon
- 匹配现有 layout:**无**

### pic-text-num-3
- intent:左侧一张场景图 + 右侧 3 编号要点
- n_items:3 + 1 image
- 关键词:配图 · 图文 · hero image · case study · 编号列表
- 用于:有清晰视觉锚点(产品图 / 场景照) + 3 要点
- **不用于**:没有合适配图 → num-col-3-line · 要点超过 4 条 → bullet_list
- 匹配现有 layout:**pic_text**(扩展用法)

### num-col-3-line
- intent:横排 3 个编号步骤,平等并列(轻量极简)
- n_items:3
- 关键词:三列 · 三步法 · three steps · 并列 · 极简 · 编号
- 用于:3 项平等并列(三步法 / 三大特性)· 想要轻量纯文本视觉
- **不用于**:项数 ≠ 3 → cards · 强递进 → arrow-chain
- 匹配现有 layout:**cards**(若纯文本三列 cards 已够)

### wave-step-3
- intent:3 步流程沿 S 形波浪曲线推进,有起伏感
- n_items:3
- 关键词:波浪 · wave · curve · 旅程 · journey · 3 步
- 用于:3 步流程想避免直线箭头的呆板 · 表达"起 / 转 / 合"节奏感
- **不用于**:严肃 / 正式场景 → arrow-chain · 节点数 > 5 → 波浪太挤
- 匹配现有 layout:**无**

### process-pill-3-arrow
- intent:3 步流程,顶部圆球编号 + 横向箭头 + 下方对应标题卡
- n_items:3
- 关键词:圆球 · pill · 三步法 · 起承转合 · 经验总结 · 改进路径
- 用于:3 步流程 + 每步要展开 1-2 行 · 顶部数字+底部完整卡的双层结构
- **不用于**:步骤 > 3 → arrow-chain · 是循环 → cycle-donut-3-icon
- 匹配现有 layout:**无**

### arrow-up-6-split
- intent:中央向上大箭头(分 3 层) + 两侧各 3 编号说明
- n_items:6(3 层 × 左右)
- 关键词:向上箭头 · upward arrow · 增长 · growth · 提升 · 进阶 · 6 项
- 用于:递进式 step1/2/3 + 每层细分 2 子项 · 强调"上升 / 增长"方向
- **不用于**:平铺并列 → cards · 不需要方向感 → cycle / hierarchy
- 匹配现有 layout:**无**

### arrow-chain-5-zigzag
- intent:横向 5 个同色箭头串联,上下交错引线 + 描述
- n_items:5
- 关键词:箭头链 · arrow chain · 路线图 · roadmap · 5 阶段 · 项目历程
- 用于:5 阶段长流程紧凑展示 · 阶段同等重要(单色避免抢戏)
- **不用于**:需要强调阶段差异 → step-arrow-multicolor-5-icon · 循环 → cycle
- 匹配现有 layout:**无**

### step-arrow-multicolor-5-icon
- intent:5 个彩色箭头 + 每步配 icon,上下交错 zigzag 描述
- n_items:5
- 关键词:多彩箭头 · multicolor arrow · 5 步 · 图标 · icon · 客户旅程 · 工作流
- 用于:5 步流程每步性质不同需要色彩区分 · 想用 icon 加快识别
- **不用于**:同质递进 → arrow-chain-5-zigzag · 不需要 icon → arrow-chain
- 匹配现有 layout:**无**

### quote-timeline-5
- intent:顶部大引号引言 + 下方 5 个 20XX 年份节点(zigzag dot)
- n_items:5
- 关键词:引言 · quote · 名言 · 时间轴 · 发展历程 · history · 里程碑
- 用于:权威发声 + 历史佐证 · 公司/产品发展时间线
- **不用于**:没有引言 → timeline-band-3 / arrow-chain · 节点 ≠ 5 → 找变体
- 匹配现有 layout:**无**

---

## category: cycle(循环 / 闭环)· 4 个

### cycle-donut-3-icon
- intent:环形 3 段循环 + 中央 icon 表示主题
- n_items:3
- 关键词:环形 · donut · 循环 · cycle · loop · 闭环 · 3 段 · PDCA · 持续改进
- 用于:3 段循环流程 + icon 强化主题 · 经典视觉适合正式 deck
- **不用于**:4 段 → donut-quad-4-icon · 多次迭代 → pdca-iterations
- 匹配现有 layout:**无**

### cycle-tri-fan-3
- intent:圆切 3 等份扇形 + 中央三角负空间
- n_items:3
- 关键词:三角 · triangle · 铁三角 · 三要素 · three pillars · balance · 平衡
- 用于:强调"三元素必须平衡或互依" · 三要素无明显流转但有内在关联
- **不用于**:有明确顺序 → cycle-donut-3-icon · 4 元素 → donut-quad-4-icon
- 匹配现有 layout:**无**

### pdca-iterations
- intent:多个 PDCA 循环并列(01 → 01 → ... → n)展示反复迭代
- n_items:可变(典型 4)
- 关键词:PDCA · 戴明环 · kaizen · 持续改进 · 迭代 · plan do check act
- 用于:内容明确是 PDCA / Kaizen / 敏捷迭代 · 强调"一次不够要反复"
- **不用于**:只一次 PDCA → cycle-donut-3-icon · 非 PDCA 框架 → cycle 通用
- 匹配现有 layout:**无**

### donut-quad-4-icon
- intent:环形 4 段 + 中央人物 / 主题 icon
- n_items:4
- 关键词:4 维 · 4 quadrants · 环形 · donut · 中心人物 · persona · 能力模型
- 用于:4 维度围绕一个中心(人物 / 主题 / 模型)· 4 项无强顺序
- **不用于**:3 或 5 维度 → 找变体 · 强调流转 → cycle-donut-3-icon
- 匹配现有 layout:**matrix_2x2**(若是静态 4 象限)

---

## category: comparison(对比 / 对决)· 2 个 · 现有 layout `compare` / `compare_pk` / `matrix_2x2` 也可用

### cards-flag-3
- intent:3 张顶部撕角的旗帜风格卡片(每卡顶部 icon 圆 + 标题 + 描述)
- n_items:3
- 关键词:旗帜 · flag · 卡片 · 三选项 · 三方案 · 对比 · 经验教训 · 撕角
- 用于:3 张并列对比卡 + 装饰 icon · 偏现代设计感 deck
- **不用于**:项数 > 3 → cards · 强对决 → vs-bilateral-5
- 匹配现有 layout:**cards**(本 pattern 是带撕角+icon 圆的变体)

### vs-bilateral-5
- intent:中央 VS 圆 + 左灰(劣势)右蓝(优势)各 5 条
- n_items:5 vs 5
- 关键词:VS · versus · pros and cons · 优劣 · 二元对比 · 线上线下 · 新旧对比
- 用于:两个方案强对比每侧 4-6 条 · 想明显偏向一侧 · 营销 / 提案突出优势
- **不用于**:三方对比 → compare 3-col · 中立 → matrix_2x2 / compare_pk
- 匹配现有 layout:**compare_pk**(本 pattern 是 5 vs 5 多条变体)

---

## category: hierarchy(层级 / 结构)· 2 个

### tri-pyramid-4sub-3
- intent:大三角拆 4 子三角(中间倒置)+ 3 编号说明在外围
- n_items:3
- 关键词:金字塔 · pyramid · 三角 · triangle · 铁三角 · iron triangle · 三要素 · 战略三角
- 用于:三要素的不可分割性 / 铁三角 · 想用极简几何 · 偏理工 / 框架类
- **不用于**:项数 ≠ 3 → cycle / cards · 多层级树 → org-tree-multilevel
- 匹配现有 layout:**无**

### org-tree-multilevel
- intent:顶级 → 部门 → 总监 → 子部门 4 级树
- topology:tree top-down,4 levels
- 关键词:组织架构 · org chart · 组织图 · 架构图 · hierarchy · 公司结构 · 部门 · 汇报关系
- 用于:真实组织架构(部门 / 角色 / 汇报)· 多级层级 ≥ 3 级
- **不用于**:只 2 级 → cards · mind map → 用 diagram skill
- 匹配现有 layout:**无**(fallback:`drawio`,iLovePPT diagram skill 首选)

---

## category: data(数据 / 图表)

*用 `${CLAUDE_PROJECT_DIR}/skills/diagram/matplotlib_rc.py` 现画 · 通常不在本 library 范围*

---

## category: relationship(关系 / 互动)· 3 个

### dual-arc-cycle-4
- intent:中央双向弧形循环(A↔B)+ 四角描述卡
- n_items:4 outer cards + 2 hubs
- 关键词:双向 · bidirectional · 双弧 · dual arc · 反馈 · feedback loop · A B 互动
- 用于:双方互动 / 反馈,4 条具体表现 · 想表达"持续双向流动"
- **不用于**:单向流程 → arrow-chain · 三方 → cycle-tri-fan-3
- 匹配现有 layout:**无**

### central-bidir-6
- intent:中央大圆主题 + 左右双向箭头 + 各 3 编号说明
- n_items:6(中心 + 3+3)
- 关键词:中央枢纽 · hub · 双向 · 中心议题 · bilateral · 6 项 · 经验教训 · 总分结构
- 用于:中心议题 + 左右两组对照(总 3+3 = 6 条)· 复盘类内容(经验 + 教训)
- **不用于**:单侧延伸 → arrow-up-6-split · 不需要中心 → vs-bilateral-5
- 匹配现有 layout:**无**

### converge-loop-2-4in
- intent:大循环箭头框 + 中央 icon + 左右 2 节点 + 各 4 输入
- n_items:8 inputs + 2 hubs + 1 center
- 关键词:汇聚 · converge · 多源 · multi-source · 中央枢纽 · 闭环 · 4 输入 · 工作流汇聚
- 用于:两组输入 / 两个角色汇聚到一个中心 · "多源汇流 + 闭环"
- **不用于**:单一线性流 → arrow-chain · 3+ 节点汇聚 → diagram skill 自由画
- 匹配现有 layout:**无**

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
6. 跑 embedding:`${CLAUDE_PROJECT_DIR}/library/visual-patterns/_rag/.venv/bin/python ${CLAUDE_PROJECT_DIR}/library/visual-patterns/_rag/embed_text.py`(+ `embed_image.py`)
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

入库新 pattern → 双向 embed → 多模态 search 全链路已通。当前 21 patterns(text + image emb 均已生成)。

## 3 mode 用法 quick ref

| mode | query 类型 | 表 | 用途 |
|---|---|---|---|
| text(默认) | 文本 | text_emb | 按 content intent 找匹配 pattern |
| image | 文本 or 图像 | image_emb | 按视觉风格找(text→image 描述 or image-image 上传参考图) |
| hybrid | 文本 | text_emb + image_emb 融合 | 综合 content + 视觉匹配 |

`search.sh --query "..." --mode <text|image|hybrid>` 或 `search.sh --query-image <path>`。
