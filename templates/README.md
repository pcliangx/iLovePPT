# templates/ —— 项目预制 .pptx 模板

> 把你常用的 `.pptx` 模板放在这里,在 brief 里用**短名**引用,不必每次贴长路径。

## 怎么用

### 1. 放模板

把 `.pptx` 文件直接放进本目录:

```
templates/
├── README.md             ← 本文件(进 git)
├── example.yaml          ← 元数据 schema 示例(进 git)
├── company_a.pptx        ← 你的模板(.gitignore,本地)
├── company_a.yaml        ← 元数据(本地)
├── customer_b.pptx
├── customer_b.yaml
├── roadshow.pptx
└── internal.pptx
```

⚠️ **`.pptx` 不进 git**(防机密 logo/disclaimer 误 commit)。`.yaml` 元数据也不进 git(可能含 owner 邮箱等)。**只有 README 进 git**,作为门牌 + 使用说明。

### 2. brief 里短名引用

```yaml
theme: company_a       # 自动解析为 templates/company_a.pptx
output: ./deck_v1.pptx
```

或者跑 build.py:

```bash
python3 skills/pptx-deck/build.py deck_plan.json
# deck_plan.json 里 theme: company_a
```

### 3.(可选)配元数据 `<name>.yaml`

每个模板配一份 `<name>.yaml`,让 brainstorm agent 在对话时**提示你这个模板适合什么场景**:

```yaml
# templates/company_a.yaml
name: 公司外部提案模板
desc: 用于客户演示 / 销售提案 / 路演
recommended_for: [executive, sales]
owner: 销售部 (alice@example.com)
notes: |
  本模板封面深色,subtitle 字号偏小(建议 ≤ 25 字)
  数据图建议用浅色 background(matplotlib 默认透明即可)
```

agent 在 Stage A 问"用哪个模板?"时会列出来:

```
你这边有几个模板:
- company_a (公司外部提案模板,推荐 executive/sales): 客户演示 / 销售提案
- customer_b (...)
- tech_blue (内置,默认科技蓝)
```

## 查找顺序

`load_theme(name)` 按以下顺序查找:

| 优先级 | 查找位置 | 用途 |
|---|---|---|
| 1 | `<内置 themes>` | `tech_blue` 等代码 theme |
| 2 | 含 `/` 或 `.pptx` 后缀 | 当路径处理(向后兼容) |
| 3 | `<deck 工作目录>/templates/<name>.pptx` | 当前 deck 项目专属模板 |
| 4 | `<iLovePPT repo>/templates/<name>.pptx` | 全局共享(本目录) |

## 模板提取的能力边界

`load_theme(<.pptx>)` 走 `_extract_theme_from_pptx`,**只提取**:

| 提取项 | 用途 |
|---|---|
| 主题色 `<a:accent1>` | 替换 `tech_blue` 的 PRIMARY |
| 中文字体 `<a:ea typeface>` | 替换默认 Microsoft YaHei |

**不提取**:背景图 / 装饰元素 / 自定义 layout / 圆角风格 / 间距 / 动画 / 模板内容。

也就是说,模板**只用于换色 + 换字体**,布局仍然是 iLovePPT 内置的 13 种 layout。如果要"完全照模板视觉风格出稿",超出本系统能力——需要写自定义 theme 模块(类似 `skills/pptx-deck/themes/tech_blue.py`)。

## 多人协作建议

团队共享模板的两种模式:

| 模式 | 怎么做 |
|---|---|
| **私有 Git 仓库镜像** | 团队建一个 private repo 存模板,本目录 `git clone` 或加 git submodule(`.gitignore` 已忽略 .pptx,需手动覆盖) |
| **共享盘 / OneDrive** | 模板放共享盘,本地 `ln -s <共享盘>/templates/* templates/` 符号链接进来 |
| **CI 注入** | 团队 CI build 时从 secrets 拉模板放进本目录 |

挑你方便的方式。
