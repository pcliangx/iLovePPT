# Secrets / 敏感数据 protection

iLovePPT 是开源 agent team 工具,本身不存机密;但工作产物(brief / outline / content / 客户素材)经常含敏感信息。本文记录两道防线:

- **入仓前**:`.githooks/pre-commit` 扫 staged 文件(P3-19)
- **运行时**:`library/_rag/scripts/redact.py` 给 query log 脱敏(P3-21)

---

## 1 · Pre-commit hook(P3-19)

### 行为

`.githooks/pre-commit` 在 `git commit` 触发时扫所有 staged 文件:

| 规则 | 触发 | 处置 |
|---|---|---|
| `decks/<name>/_assets/raw/` 路径下任意文件 | 路径正则 | **拒绝 commit**(exit 1) |
| 文本文件正文含邮箱 (`x@y.tld`) | grep regex | **警告**(不阻断) |
| 文本文件正文含中国手机号 (`1[3-9]\d{9}` 含数字边界) | grep regex | **警告** |
| 文本文件正文含 `$\d{4,}` / `¥\d{4,}` | grep regex | **警告** |

文本文件指扩展名为 `.md` / `.yaml` / `.yml` / `.json` / `.txt` / `.csv` 的 staged file。二进制 / `.pptx` / 图片 跳过扫描(content 不可直接 grep)。

### 启用

仓库根目录跑一次:

```bash
bash scripts/install-hooks.sh
```

等价于:

```bash
git config core.hooksPath .githooks
```

(`.git/hooks/` 不入 git,所以 `core.hooksPath` 是把 hook 文件版本化的标准做法。)

### bypass 单次

```bash
git commit --no-verify
```

警告级规则不阻断 commit;此 bypass 仅对 raw 路径阻断规则生效。

### 关闭整仓 hook

```bash
git config --unset core.hooksPath
```

### 误报怎么办

警告类规则故意宽松(防漏报)。如确属误报(模板示例 / 文档教学的占位邮箱 / 价格范例):
- 警告不阻断,直接继续 commit 即可
- 也可在文档里把示例值改成明显假值(`<email@example.com>` / `¥XXX`)避免触发

阻断类规则(raw 路径)严格按路径模式匹配:
- 该路径下文件**严禁**入 git(`.gitignore` 已盖,正常应到不了 staged)
- 真要 commit:`git commit --no-verify` 显式 bypass + 自负风险

---

## 2 · RAG query log 脱敏(P3-21)

### 行为

`library/search.sh` 每次跑都会 append 一行到 `library/_rag/query_log.jsonl`(给 bench / 分析用)。query 原文常含 brief 内容(可能含客户名 / 邮箱 / 钱数等敏感字段)。

P3-21 之后默认走 `library/_rag/scripts/redact.py` 过滤:

| 模式 | 替换值 | 备注 |
|---|---|---|
| 邮箱 `local@domain.tld` | `<email>` | 含 `+` / `.` 子地址 |
| 中国手机号 `1[3-9]\d{9}` | `<phone>` | 仅 11 位 · 防误吃身份证 |
| 美元 `$\d{4,}` | `<money_usd>` | ≥ 4 位整数,小钱不脱敏 |
| 人民币 `¥/￥\d{4,}` | `<money_cny>` | 全/半角都支持 |

仅 `query` 和 `expanded_query` 字段过滤;`hits` / `ts` / `mode` 等元数据不变。脱敏后 log 多一字段 `redacted: true` 标记。

### debug 关闭

```bash
library/search.sh --no-redact --query "原始 query 含敏感数据"
```

仅当前调用关闭脱敏,适合排查 query 在 redact 链上的副作用(如脱敏后召回不对)。

### 程序里用

```python
import sys
sys.path.insert(0, 'library/_rag/scripts')
from redact import redact

redacted = redact("张三 zhangsan@acme.com 13812345678 充值 ¥50000")
# → "张三 <email> <phone> 充值 <money_cny>"
```

`redact_dict(d, fields)` 给指定 string 字段做 in-place 脱敏(返回新 dict):

```python
from redact import redact_dict
out = redact_dict({"query": "...", "ts": "...", "n": 3}, fields=["query"])
```

### 测试

```bash
library/_rag/.venv/bin/python -m pytest tests/library/test_redact.py -v
```

10 个 case 覆盖各类型 + 组合 + 边界 + dict helper。

---

## 已知限制

1. **pre-commit 不扫 `.pptx` / 图片正文** —— 二进制 grep 没意义。深度扫敏感建议另起工具(后续 P3-22 模板入库时做)。
2. **redact 不解 base64 / URL 编码** —— 仅扫明文。
3. **手机号正则故意保守**(11 位 1[3-9])—— 防误吃 14 位订单号 / 18 位身份证。海外手机号 / 座机号目前不脱敏。
4. **pre-commit hook 不是 server-side enforcement** —— `--no-verify` / 关 hook / 不 install 都能绕过。push 后 server-side 防护建议另起 P5 工作(`pre-receive` on hosting)。
