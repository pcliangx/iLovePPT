# API Key Rotation

`library/_rag/.env` 保存 DashScope API key 单点 · 推荐**季度 rotation** 降低泄露风险。

## 工具

`library/_rag/scripts/rotate_api_key.py`(P3-18 加)

## 用法

```bash
# 列历史备份
library/_rag/.venv/bin/python library/_rag/scripts/rotate_api_key.py --list-backups

# 轮换(stdin 输入新 key,避免 shell history 留痕)
echo "sk-NEW-KEY" | library/_rag/.venv/bin/python library/_rag/scripts/rotate_api_key.py --stdin

# 或显式 --new-key
library/_rag/.venv/bin/python library/_rag/scripts/rotate_api_key.py --new-key "sk-NEW-KEY"

# 回滚到某次备份
library/_rag/.venv/bin/python library/_rag/scripts/rotate_api_key.py --rollback 2026-05-27T10:00:00
```

## 行为

1. 备份当前 `.env` 到 `.env.bak.<ISO-timestamp>`
2. 替换 `DASHSCOPE_API_KEY=...` 行为新值
3. 验证:跑一次 `embed_text("test")` smoke test
4. 通过 → 报 success
5. 失败 → 自动 rollback + 报 error

## 推荐周期

- 季度(每 3 个月)定期轮换
- 怀疑泄露时立即轮换
- 团队人员变动后轮换

## 备份保留

`.env.bak.<timestamp>` 不入 git(`.env.*` 已 gitignore)· 本地保留以备回滚 · 季度可手动清理旧备份。
