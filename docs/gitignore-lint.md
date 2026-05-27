# .gitignore Lint(P3-20)

3 份 .gitignore(根 + decks/ + library/_rag/ 暗规)散落 · 容易漏 / 重复 / 冲突。`scripts/gitignore_lint.py` 自动校。

## 用法

```bash
# 跑 lint
scripts/gitignore_lint.py

# JSON 输出(CI / dashboard 集成)
scripts/gitignore_lint.py --format json

# 自动修(merge 子规则 / 删 redundant)
scripts/gitignore_lint.py --fix
```

## 5 类检查

1. **conflict**:同模式在多个 .gitignore 重复定义 · 行为可能不同 → 报警
2. **shadowed**:子目录 .gitignore 规则被父级已 ignore 的规则掩盖 → 子规则无用
3. **redundant**:子 .gitignore 重复父级已有规则 → 可删
4. **untracked-but-should-be-ignored**:`git status` 看 untracked 含明显 secret(.env / .key / .pem / *.bak / *_secret.*)→ 应加 ignore
5. **tracked-but-listed-in-gitignore**:已 tracked 文件被 ignore 规则覆盖 → 矛盾(可能是历史遗留)

## CI 集成

跟 `.githooks/pre-commit`(P3-19)整合 · 有 error → reject commit:

```bash
# .githooks/pre-commit 末尾追加
scripts/gitignore_lint.py --format json | jq -e '.summary.errors == 0' > /dev/null || {
  echo "❌ .gitignore lint failed · 跑 scripts/gitignore_lint.py 看详情"
  exit 1
}
```

## 输出格式

text(默认):
```
.gitignore lint report
======================
✓ no conflicts
⚠ 2 shadowed rules in decks/.gitignore
✗ 1 untracked file should be ignored: decks/secret.env
```

json:
```json
{
  "summary": {"errors": 1, "warnings": 2},
  "issues": [{"type": "untracked", "file": "decks/secret.env", "suggested_pattern": "*.env"}]
}
```

## 退出码

- 0:全过
- 1:有 warning(shadowed / redundant)· 但不 block
- 2:有 error(conflict / untracked-secret / tracked-in-ignore)· CI 应 fail
