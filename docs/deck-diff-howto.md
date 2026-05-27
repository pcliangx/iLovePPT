# `scripts/deck_diff.py` 怎么用

P3-13 · 跨 deck content.md 的**语义 diff**。`git diff content.md` 只看到行级文字变化(line +/-) · 看不到结构层面发生了什么 —— 哪页加了 / 删了 / 重排了 / layout 或 pattern 换了 / 还是只改了几个字。`deck_diff.py` 在 line-level 之上做了一层章节对齐 + 类别分类 · 直接告诉你"这次 v1 → v2 到底动了什么"。

## 一句话

```bash
scripts/deck_diff.py decks/X/author/deck_v1_content.md decks/X/author/deck_v2_content.md
```

返回 4 类变化 · 标准退出码:**0 = 无 diff**,**1 = 有 diff**(跟 git diff 一致 · 适合 CI hook)。

## 使用场景

- **review v1 → v2 升版**:章节增删 / SCQA 变 / >3 页连锁(CLAUDE.md "改前备份 + 统一命名" Major iteration)发生时 · 一眼看清整体动了多少
- **接手别人的 deck**:同名 v1 / v2 拿到不知道改了啥 · 跑一次 diff 比 git log 直观
- **dashboard 联动**(P2-11):dashboard 显示某 deck 状态时 · 调 deck_diff 看每两个相邻版本之间的演进
- **CI gate**(进阶):章节增删超过 N 个 → 自动触发 critic D 重跑
- **layout 设计反馈**:跨多 deck 跑 deck_diff · 哪些 layout / pattern 经常出现在 `modified` 里 = 设计可能有问题(选做 · 见下文 § 跨 deck 聚合)

## 4 类变化

| 类别 | 含义 | 触发 |
|---|---|---|
| **added** | v2 有 v1 没有的章节 | fuzzy title match 配不上任何 v1 章节 |
| **removed** | v1 有 v2 没有的章节 | fuzzy title match 配不上任何 v2 章节 |
| **modified** | 章节两边都在 · 但 title / layout / pattern / body 不同 | fuzzy title match 配上 · 但任一字段变了 |
| **reordered** | 章节都在 · 但顺序变了 | matched 对按 v1 idx 排后 · v2 idx 不单调递增 |

### fuzzy match 阈值

默认 80(0-100) · 取 `max(ratio, partial_ratio)` :
- `ratio`: 整体相似度(Levenshtein-style)· 强调字数一致
- `partial_ratio`: 子串相似度 · `数据分析` ↔ `数据分析(改)` = 100(整串当子串能 fit) → 判 modified · 不会误判 removed + added

太低(< 60) → 不相关章节误判 modified;太高(> 90) → 微改也判 added+removed。调整看 `--threshold`。

### 为什么是 fuzzy 而不是 exact / sha

- Exact title match:大多数实际修改会改 title(措辞调整 / 加副标题),exact 直接 fail
- sha 比较:正文 sha 跟 title 是两件事 · 章节存不存在的判断**必须**先于 body 改没改

### 章节顺序 = chapter_idx 不是出现顺序

`## 1. ...` `## 2. ...` 标题里的数字是 chapter_idx。v1 中 chapter 3 移到 v2 chapter 5 但仍单调递增 = 不算 reorder(因为中间塞了 added)· 真 reorder 是 [1, 2, 3] → [1, 3, 2] 这种。

## 命令语法

### 经典形

```bash
scripts/deck_diff.py <v1.md> <v2.md>
```

### 选项

| flag | 默认 | 含义 |
|---|---|---|
| `--format text\|json` | `text` | 输出格式(json 给 dashboard / CI) |
| `--output <path>` | stdout | 写文件(自动关闭 ANSI 色) |
| `--include-text-diff` | off | modified 章节 + line-level unified diff(只 text 格式) |
| `--threshold <0-100>` | 80 | fuzzy title match 阈值 |
| `--no-color` | auto | 强制关闭 ANSI 色(non-tty / `--output` 时自动关) |

### Json 给 dashboard / CI

```bash
scripts/deck_diff.py v1.md v2.md --format json
```

schema:

```json
{
  "v1_path": "...",
  "v2_path": "...",
  "v1_chapter_count": 3,
  "v2_chapter_count": 4,
  "summary": {"added": 1, "removed": 0, "modified": 2, "reordered": 0},
  "diffs": [
    {
      "category": "modified",
      "v1_idx": 2, "v2_idx": 2,
      "v1_title": "数据分析", "v2_title": "数据分析(改)",
      "changes": ["title", "pattern", "body"],
      "details": {
        "title": {"from": "数据分析", "to": "数据分析(改)"},
        "pattern_id": {"from": "tpl:finance_arrow__05-data", "to": "tpl:finance_arrow__08-data"},
        "sha256": {"from": "9d063f55de9d", "to": "c89007dd6cbb"}
      },
      "text_diff": null
    }
  ]
}
```

`text_diff` 字段只在 `--include-text-diff` 且 modified 章节 body 变了时填(text format 用 · json 留 null)。

### line-level 细看

```bash
scripts/deck_diff.py v1.md v2.md --include-text-diff
```

每个 modified 章节后会跟一个 unified diff(类似 `git diff --no-color`),展示具体哪几行字变了。truncate 在 60 行。

## 完整例

```bash
# Mock 2 个 content.md
mkdir -p /tmp/diff-test
cat > /tmp/diff-test/v1.md <<'EOF'
# Demo v1

## 1. 开场
<!-- layout: cover -->
内容 1。

## 2. 数据分析
<!-- layout: data -->
<!-- pattern: tpl:finance_arrow__05-data -->
数据内容。

## 3. 总结
<!-- layout: closing -->
EOF

cat > /tmp/diff-test/v2.md <<'EOF'
# Demo v2

## 1. 开场
<!-- layout: cover -->
内容 1.1。

## 2. 数据分析(改)
<!-- layout: data -->
<!-- pattern: tpl:finance_arrow__08-data -->
数据内容(更新)。

## 3. 新增章节 SWOT
<!-- layout: quadrant -->
<!-- pattern: tpl:business_geometric__05-quadrant -->
SWOT 内容。

## 4. 总结
<!-- layout: closing -->
EOF

scripts/deck_diff.py /tmp/diff-test/v1.md /tmp/diff-test/v2.md
```

输出(text format · 部分):

```
=== deck_diff ===
  v1: /tmp/diff-test/v1.md  (3 chapters)
  v2: /tmp/diff-test/v2.md  (4 chapters)

summary: +1 added · -0 removed · ~2 modified · ↻0 reordered

--- ADDED (1) ---
  + v2 #3 · 新增章节 SWOT
      (kind=content · layout=quadrant · pattern=tpl:business_geometric__05-quadrant)

--- MODIFIED (2) ---
  ~ #1 · 开场
      changed: body
        body: 1cd169a360ec → a9d0be79eb57
  ~ #2 · 数据分析 → 数据分析(改)
      changed: title, pattern, body
        title: '数据分析' → '数据分析(改)'
        pattern_id: 'tpl:finance_arrow__05-data' → 'tpl:finance_arrow__08-data'
        body: 9d063f55de9d → c89007dd6cbb
```

### 期待 vs 实际

| 期待 | 实际 |
|---|---|
| chapter 1(开场)· text changed | ✓ modified · body sha changed |
| chapter 2(数据分析)· title + pattern + body | ✓ modified · 三字段都列了 from→to |
| 新增章节 SWOT | ✓ added · v2 #3 |
| 总结从 #3 → #4(无真 reorder) | ✓ summary `↻0 reordered`(单调递增 = 不算 reorder) |

## 边界 case

| Case | 行为 |
|---|---|
| 文件不存在 | exit 2 + stderr ERROR |
| identical files | exit 0 · "no semantic differences detected" |
| v1 / v2 没 `## N.` 章节(纯 special) | special 按 name 精确匹(`cover ↔ cover`) |
| 同 title 多次出现 | greedy · 取 fuzz ratio 最高 + idx 最近的(每个 v2 章只被配一次) |
| body 完全相同但加了 / 改了 `<!-- layout: -->` 注释 | sha256 用 normalized body(去注释)· 算 layout 字段变 · 不算 body 变 |
| frontmatter 改 | 不算 diff · 本脚本不解析 frontmatter(theme / audience / footer 变化用 git diff 自己看) |
| 章节里有 markdown table / code block | sha 算的是整段 normalized body · 表格 / 代码内容变了会触发 body diff |

## 跟其他工具的关系

| 工具 | 关系 |
|---|---|
| `scripts/derive_plan.py`(P2-5) | 共享 parser regex(`CHAPTER_HEADING_RE` / `LAYOUT_DIRECTIVE_RE` / `PATTERN_DIRECTIVE_RE`)· 风格一致 |
| `scripts/clip_chapter.py`(P3-14) | clip 完跑 deck_diff 看动了哪几章 |
| `scripts/dashboard.py`(P2-11) | dashboard 可调 deck_diff 看每 deck 的版本演进(JSON 接入 · summary 字段直接展示) |
| `git diff content.md` | line-level / 语法盲 · deck_diff 是结构感知 / 章节级 |

## 跟 P2-11 dashboard 联动建议

dashboard 在每 deck 行除了显示 stage / cost / score · 可加一列 "版本演进":扫 `decks/<X>/author/deck_v*_content.md` · 对相邻版本跑 `deck_diff.py --format json` · 在 markdown 展示成 `v1→v2: +3 ~2 -0 / v2→v3: +0 ~5 -1`。

具体集成(假设的接入点):

```python
# 在 dashboard.py 里读 deck 元数据时
import json
import subprocess
from pathlib import Path

def get_version_evolution(deck_dir: Path) -> list[dict]:
    """Return [{from_v, to_v, summary}, ...] of consecutive content.md diffs."""
    contents = sorted(deck_dir.glob("author/deck_v*_content.md"))
    if len(contents) < 2:
        return []
    rows = []
    for v1, v2 in zip(contents, contents[1:]):
        out = subprocess.run(
            ["scripts/deck_diff.py", str(v1), str(v2), "--format", "json"],
            capture_output=True, text=True, check=False,
        )
        if out.returncode in (0, 1):
            data = json.loads(out.stdout)
            rows.append({
                "from": v1.stem, "to": v2.stem,
                "summary": data["summary"],
            })
    return rows
```

dashboard 输出加列:

```
Deck             Stage      Audience  Cost  Evolution
data-report      audience   8.7       $1.2  v1→v2: +1 ~2 -0
quarterly-2026   builder    -         $0.6  v1→v2: +0 ~5 -1 / v2→v3: +3 ~1 -0
```

## 跨 deck 聚合(advisory · 选做)

如果想跨多 deck 看"哪些 layout 经常变":

```bash
# 一行 shell · 用 jq 聚合
for deck in decks/*; do
  for pair in $(ls "$deck"/author/deck_v*_content.md 2>/dev/null | paste - - | head); do
    v1=$(echo $pair | awk '{print $1}')
    v2=$(echo $pair | awk '{print $2}')
    [ -n "$v2" ] && scripts/deck_diff.py "$v1" "$v2" --format json 2>/dev/null
  done
done | jq -s '
  [.[] | .diffs[] | select(.category == "modified") | .details.layout.from // .details.layout.to // empty]
  | group_by(.) | map({layout: .[0], count: length}) | sort_by(-.count)
'
```

输出 = 哪些 layout 最常被改 = layout 设计可能有问题(措辞难写 / pattern 不合适)。

## 反模式

- ✗ **拿 deck_diff 替代 critic / audience**:本脚本看的是**结构变化**,**不**评内容质量(论据强不强 / SCQA 通不通 / 配色对不对)。改完仍要重派 critic D / audience(章节增删 = MECE 大改 / CLAUDE.md 不变量)
- ✗ **--threshold 拉到 < 60 然后 modified 一片**:fuzzy 是配对工具不是相似度报告 · 阈值太低会把不相关章节配上去 · 反而漏 added / removed
- ✗ **靠 deck_diff 修 plan.json**:本脚本只读 content.md(P2-5 单源)· plan.json 改了不会反映 · 修 plan 跑 `scripts/derive_plan.py` 重派

## 限制 / 已知不支持(后续可加)

- ❌ frontmatter diff(theme / footer / audience 变化)· 用 `git diff` 自己看
- ❌ 三方 diff(v1 vs v2 vs v3 一次对比)
- ❌ subsection level(章节内 `### N.x` 二级 heading · 现在只对一级 `## N.`)
- ❌ pattern category 智能映射(`tpl:A__05` 跟 `tpl:B__05` 视为同模式 · 跨模板时 false positive)
- ❌ image 资产 diff(charts/X.png 改没改)

## 关联

- `scripts/derive_plan.py` —— P2-5 SSOT helper · parser 共享 regex
- `scripts/clip_chapter.py` —— P3-14 章节复制 · clip 完跑 deck_diff 看效果
- `scripts/dashboard.py` —— P2-11 跨 deck 聚合 · 加 "Evolution" 列(见上文)
- CLAUDE.md "改前备份 + 统一命名" 不变量 —— Major iteration 触发条件之一就是"章节增删 / SCQA 变 / >3 页连锁",deck_diff 帮你判断是不是 Major
