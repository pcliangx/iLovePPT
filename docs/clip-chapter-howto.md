# `scripts/clip_chapter.py` 怎么用

P3-14 · 跨 deck 章节复制 · 当你在 deck A 写了一章觉得 deck B 也要用,**不必手动 copy-paste**。

## 一句话

```bash
scripts/clip_chapter.py decks/A/author/deck_v1_content.md --chapter 5 \
                        --target decks/B/author/deck_v1_content.md
```

把 deck A 的第 5 章 append 到 deck B 的 content.md 末尾,带 layout / pattern 注释 + 引用图片自动 cp 到 deck B 的 `author/charts/`。

## 使用场景

- 做 deck A 觉得某章解释得很好,想搬到 deck B(同主题不同受众)
- 多份 deck 共用某个"工具介绍" / "团队介绍"页,改一次同步多次嫌烦
- 把模板 deck 的一些"通用 closing / disclaimer"快速塞进新 deck
- 测试时构造 mock content.md(从其他 deck 拼一个起来跑 derive_plan)

## 命令语法

### 经典形

```bash
scripts/clip_chapter.py <source.md> --chapter <N> --target <target.md>
```

参数:
- `source.md`:source content.md path · 章节抽自这里
- `--chapter N` / `-c N`:抽第 N 章(对应 `## N. ...` 标题)
- `--target` / `--to` / `-t`:target content.md path · 章节 append 到这里

### URL-fragment 风格(等价)

```bash
scripts/clip_chapter.py decks/A/author/deck_v1_content.md#5 \
                        --to decks/B/author/deck_v1_content.md
```

`#N` 等同 `--chapter N` · 不能两个都给。

### 指定插入位置

默认 append 到 target EOF · 想插入到中间:

```bash
scripts/clip_chapter.py decks/A/.../content.md --chapter 5 \
                        --target decks/B/.../content.md \
                        --insert-after 3
```

把 source 第 5 章插到 target 的第 3 章之后(变成 target 的新第 4 章)。

### dry-run · 先看会做什么

```bash
scripts/clip_chapter.py decks/A/.../content.md --chapter 5 \
                        --target decks/B/.../content.md \
                        --dry-run
```

只 print,不改文件 / 不 cp 图片 · stderr 是日志,stdout 是 chapter 预览。

## 行为细则

### 1. 章节抽取

- regex `^##\s+(\d+)\.\s+(.+?)$` 找 source 里的 `## N. <title>`
- 找下一个 `## ` 标题(任何类型 · 包括 `## [section_divider]`),前面就是 chapter 主体
- **保留** layout / pattern 注释:`<!-- layout: X -->` `<!-- pattern: Y -->`
- **保留** 正文 / bullets / 表格 / 数据 source

### 2. 自动 renumber

target 已有的最大 chapter 数 + 1 = 新章节号 · **避免冲突**:

```
target 现有 chapter 1, 2, 3
source 第 5 章 append 到 target → 变成 target 的第 4 章
```

### 3. 图片资产同步

如果 chapter 含 `![alt](charts/foo.png)`:
- 找 `<source_dir>/charts/foo.png`
- cp 到 `<target_dir>/charts/foo.png`(target 已有同名 → 跳过 · `--overwrite-images` 强制覆盖)
- 同时 cp 同名 sidecar(`.py` / `.drawio` / `.mmd` / `.source.yaml`)· 符合"图片资产 reproducibility 强制"不变量(见 CLAUDE.md)
- **图片相对路径不改**:`charts/foo.png` 在 target content.md 仍是 `charts/foo.png`(target/charts/foo.png 存在 = OK)

### 4. 不做的事

- **不动 frontmatter**:target 的 metadata(audience / theme / top_recommendation 等)保持原样;source frontmatter 完全跳过
- **不动 [special] 标题**:`## [section_divider]` `## [toc]` `## [closing]` 不能用 `--chapter N` 抽(special 块用 manual edit)
- **不去重**:同章 clip 两次会出现两份 · 自行注意
- **不重 critic / audience**:clip 完 target deck **必须**重跑 critic D + audience(章节变了 → MECE / 节奏可能破),由主线程派发
- **不验证 layout / pattern enum**:clip 后 target 的 builder Step 0 self-check 会拦无效 pattern · 不在本脚本做

## 边界 case 与 caveat

| Case | 行为 |
|---|---|
| source 里没找到 `## N.` | exit code 2 + ERROR · 不改任何文件 |
| target 里没有任何 `## N.`(纯 special) | new_num = 1 |
| target 是新建空文件 | 走 append · 但建议先有 frontmatter |
| `--insert-after K` · target 没第 K 章 | exit code 2 + ERROR · 不改 |
| 图片绝对路径 / http(s) | skip cp · 保留引用(target 自行解决) |
| source = target | 允许 · 等于 chapter 自复制 + renumber(也许测试有用) |

## 验证(clip 完手动跑)

```bash
# 1. target content.md 语法 OK?
python3 scripts/derive_plan.py decks/B/author/deck_v1_content.md --dry-run | head -40

# 2. critic + audience 重跑(主线程派发)
# 跟主线程说:
# "decks/B clip 进了 1 章 · 重派 critic D + audience"

# 3. 渲染验证
python3 .claude/skills/pptx-deck/build.py decks/B/builder/deck_v1_plan.json
```

## 反模式

- ✗ 用 `clip_chapter.py` 跨 theme 复制(deck A `template_golden` chapter 5 -> deck B `tech_blue`):pattern id 是 `tpl:template_golden__...` · target builder 找不到 · 必须改 pattern。**先跑 dry-run 看 pattern 注释**
- ✗ clip 完不重 critic / audience:**章节增删是 MECE 大改** · CLAUDE.md "改前备份 + 统一命名" 不变量要求(章节增删 = Major iteration → 应升 v2 平行)
- ✗ 把 special 块 clip 进来:special 块结构 fragile · 用 manual edit

## 限制 / 已知不支持(后续可加)

- ❌ 跨 deck slug renumber 全部章节(只动新加的)
- ❌ pattern id 自动 rewrite(`tpl:A` -> `tpl:B`)
- ❌ 多 chapter 一次性 clip(`--chapters 3,5,7`)
- ❌ 反向操作(--remove-chapter)· 用 Edit / git revert

如有需要可在 follow-up 加。

## 关联

- `scripts/derive_plan.py` —— P2-5 SSOT helper · clip 完跑这个出新 plan
- `scripts/new_deck.py` —— P3-8 helper · 起新 deck 的入口
- CLAUDE.md "图片资产 reproducibility 强制" 不变量 —— sidecar cp 由本脚本继承
