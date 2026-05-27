# 中英文混排渲染(P3-10)

## 痛点

`helpers.set_font(run, font, size)` 默认中文 EA 字段写 Microsoft YaHei,英文 latin 写 Arial。但**混排**时(如 "iLovePPT 是开源 PPT 工具")run-level fallback 不一致 — 英文片段可能 fallback 到中文字体或反之。

CLAUDE.md 核心不变量:**中文字体必须通过 lxml 写 `<a:ea>` + `<a:cs>`**(`helpers.set_font`)· 这是 #1 产物破损源。

## 解法

`helpers/_internals.py` 提供:

### `tokenize_mixed(text: str) -> list[dict]`

按语言切分混排字符串:

```python
from helpers._internals import tokenize_mixed

tokenize_mixed("iLovePPT 是 100% 开源工具")
# [{"text": "iLovePPT", "lang": "en"},
#  {"text": " 是 ", "lang": "zh"},
#  {"text": "100%", "lang": "num"},
#  {"text": " 开源工具", "lang": "zh"}]
```

启发:
- 全 ASCII → `en`
- 全数字 / 标点 → `num`
- 含中文(CJK Unified Ideographs U+4E00-U+9FFF)→ `zh`
- 混合段 → `zh`(中文 fallback 保守)

### `mixed_lang_text(paragraph, runs, *, default_font_size=18)`

每段独立设字体确保 fallback 一致:

```python
from helpers._internals import mixed_lang_text, tokenize_mixed

p = slide.shapes[0].text_frame.paragraphs[0]
runs = tokenize_mixed("iLovePPT 是开源 PPT 工具")
mixed_lang_text(p, runs, default_font_size=20)
```

每个 run:
- `lang=zh` → `set_font(run, FONT_CN, size)` · ea + cs + latin 全 YaHei
- `lang=en` → `set_font(run, FONT_LATIN, size)` · latin Arial · ea YaHei
- `lang=num` → `set_font(run, FONT_NUM, size)` · 数字字体

## 何时用

| 场景 | 推荐 |
|---|---|
| 纯中文段 / 纯英文段 | `set_font` 直接 |
| 标题混排("iLovePPT 培训") | `mixed_lang_text` + `tokenize_mixed` |
| body 含英文术语("用 SaaS 模式") | `mixed_lang_text` |
| 数字 + 单位("85%" / "¥1,000") | `set_font` 设 FONT_NUM 即可 |

## 测试

`tests/pptx/test_mixed_lang_text.py` · 验证 tokenize 切分 + 每 run 字体属性 + `<a:ea>` 全段 YaHei。
