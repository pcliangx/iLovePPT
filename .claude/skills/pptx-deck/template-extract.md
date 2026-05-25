# 从模板提取主色与字体

当用户在 `deck_plan.json` 的 `theme` 字段提供 `.pptx` 文件路径时，`build.py` 会调用
`_extract_theme_from_pptx()` 从该文件中提取两样东西，然后用它们覆盖 `tech_blue` 的默认值。

---

## 提取的内容（仅两项）

| 提取项 | XML 来源 | 用途 |
|---|---|---|
| 主题色（accent1） | `ppt/theme/theme1.xml` → `<a:accent1>` 下的 `<a:srgbClr val="..."/>` | 替换 `tech_blue` 的 PRIMARY 色 |
| 中文字体 | `ppt/slideMasters/slideMaster1.xml` → `<a:ea typeface="..."/>` | 替换 `tech_blue` 的 FONT_CN |

**不提取**：背景、spacing、装饰元素、layout 定义、动画、占位符尺寸。
提取后仍沿用 `tech_blue` 的全部 13 个 layout 函数，只把上面两个常量换掉。

---

## 调用方式

`deck_plan.json` 中：

```json
{
  "theme": "path/to/user_template.pptx",
  "output": "./out/deck.pptx",
  "slides": [...]
}
```

`theme` 为 `"tech_blue"` 时直接用内置主题；为 `.pptx` 路径时走提取流程。

---

## 降级方案（best-effort）

提取失败时静默降级，不中止构建：

| 失败情形 | 降级策略 |
|---|---|
| 文件损坏 / python-pptx 无法打开 | 完全退回 `tech_blue` |
| `<a:accent1>` 无 `srgbClr`（渐变色等） | 主题色退回 `tech_blue` 默认 |
| `<a:ea>` typeface 为空 / 缺失 | 中文字体退回 `Microsoft YaHei` |

提取是 best-effort：无法提取某 token 时静默退回 tech_blue 默认值，不中止构建、不打印 `[WARN]`。`build.py` 在终端打印提取结果行，显示实际使用的字体与主色（提取成功显示提取值，未提取到则显示"默认"），可由此判断哪些 token 被替换。

---

## 何时不走模板提取

- `theme` 为 `"tech_blue"` → 直接用内置主题，无需提取
- 用户只想读取 .pptx 内容（非用作模板）→ 不走本流程
- 用户模板已损坏 → 提示换模板，退回 `tech_blue`

---

## Anti-prompt

- 不要以为提取会"复刻"用户模板的整体视觉 —— 它只替换主色与中文字体
- 不要期望 spacing / 圆角 / 装饰块的风格被继承 —— layout 函数来自 `tech_blue`，不变
- 不要在提取失败时抛出异常中止构建 —— 应静默降级，退回 tech_blue 默认值
