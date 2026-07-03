# Per-deck cost budget

iLovePPT 每个 deck 都有 token cost tracking。**在此基础上加 budget ceiling**:用户在 brainstorm 阶段设上限,主线程在每轮 agent return 后检查,跨阈值 stderr warn,over budget 时暂停问用户。

## Why

老版本只记账不警告 — agent 可能跑出 $50 deck 用户毫不知情。本工具加了 3 道防线:

1. **brief.cost_budget_usd**:brainstorm 收 brief 时问用户上限(默认 10 USD)
2. **track_cost.py update 阈值 warn**:cost 跨 50% / 80% / 100% 时 stderr warn
3. **track_cost.py status 检查**:主线程每次 Task return 后跑,over 100% 暂停询问 user

## Cost block schema(state.json)

`<deck>/{brainstorm,author}/state.json` 里的 `cost` 块:

```json
{
  "cost": {
    "budget_usd": 10.0,
    "tokens_by_agent": {
      "brainstorm":  {"input": 0, "output": 0},
      "author":      {"input": 0, "output": 0},
      "critic":      {"input": 0, "output": 0},
      "builder":     {"input": 0, "output": 0},
      "audience":    {"input": 0, "output": 0},
      "extractor":   {"input": 0, "output": 0}
    },
    "totals": {"input": 0, "output": 0},
    "cost_usd": 0.00,
    "cost_usd_breakdown_by_agent": {
      "brainstorm": 0.00, "author": 0.00, "critic": 0.00,
      "builder": 0.00, "audience": 0.00, "extractor": 0.00
    },
    "model": "opus",
    "warned_at_pct": [],
    "warnings": [],
    "last_updated": "2026-05-27T..."
  }
}
```

| 字段 | 说明 |
|---|---|
| `budget_usd` | 用户在 brief 阶段设的 USD 上限(默认 10) |
| `tokens_by_agent` | 各 agent 累计 input / output token |
| `totals` | input / output 跨 agent 合计 |
| `cost_usd` | 按 PRICES 计算的总美元 cost(Opus 4.7) |
| `cost_usd_breakdown_by_agent` | 每个 agent 单独折算的 USD |
| `model` | hardcoded "opus"(Haiku 路由 future) |
| `warned_at_pct` | 已 warn 过的阈值(50/80/100),防重复 warn |
| `warnings` | 历次 warn 记录(append-only,主线程 / log review 用) |
| `last_updated` | UTC ISO timestamp |

## 价格(Opus 4.7)

`scripts/track_cost.py` PRICES 常量(USD per 1M token,来源 https://www.anthropic.com/pricing 2026-05):

| model | input | output |
|---|---|---|
| opus | $15.00 | $75.00 |
| sonnet | $3.00 | $15.00 |
| haiku | $0.80 | $4.00 |

**iLovePPT 全 agent 默认走 opus**(详 CLAUDE.md § 架构表),所以 cost 按 opus 算。如果 future Haiku 路由部分 agent,改 `tokens_by_agent` 进 `model_by_agent` schema + recompute。

## CLI 用法

### update — 累加 token usage(agent 内部跑)

```bash
python3 scripts/track_cost.py update \
    --state <deck>/author/deck_v1_state.json \
    --agent author \
    --tokens-in 1500 \
    --tokens-out 3000
```

**返回**:
- `exit 0` → 阈值未跨,继续
- `exit 2` → 跨过 100% 阈值(stderr 也 warn 这一信号)

**跨阈值 warn 示例**(stderr):
```
[budget-warn] cost $5.4500 / budget $10.00 = 54.5% · 跨过 50% 阈值
```

### status — 主线程派发后检查 budget(新增)

```bash
python3 scripts/track_cost.py status \
    --deck /abs/path/to/deck-working-dir
```

**locate state.json**:按顺序找 `<deck>/author/deck_v1_state.json` → `<deck>/brainstorm/state.json` → `<deck>/state.json`,取第一个存在的。

**返回**:
- `exit 0` → ok
- `exit 2` → over budget,主线程**暂停**问用户(三选一)

文本 output 示例:
```
[budget-status] OVER BUDGET · $12.3400 / $10.00 = 123.4%
  → 主线程行动:暂停 + 询问用户三选一:(1) 继续 (2) 终止 (3) 提 budget(set-budget)
```

JSON output(`--format json`)适合主线程 parse:
```json
{
  "state_path": "/abs/.../author/deck_v1_state.json",
  "cost_usd": 12.34,
  "budget_usd": 10.0,
  "used_pct": 123.4,
  "over_budget": true,
  "warned_at_pct": [50, 80, 100],
  "recent_warnings": [...]
}
```

### show — 详细 cost breakdown

```bash
python3 scripts/track_cost.py show \
    --state <deck>/author/deck_v1_state.json
```

文本 output:
```
deck: /abs/.../author/deck_v1_state.json
model: opus
last_updated: 2026-05-27T12:34:56Z
totals: in=85,000 out=120,000
cost_usd: $10.275  ·  budget: $10.00  ·  used: 102.8%
warned_at_pct: [50, 80, 100]
by agent:
  brainstorm   in=    10,000  out=    15,000  $1.275
  author       in=    25,000  out=    40,000  $3.375
  critic       in=    15,000  out=    25,000  $2.1
  builder      in=    20,000  out=    25,000  $2.175
  audience     in=    15,000  out=    15,000  $1.35
  extractor    in=         0  out=         0  $0.0
```

### set-budget — 中途改 budget(用户答"提 budget"后跑)

```bash
python3 scripts/track_cost.py set-budget \
    --state <deck>/author/deck_v1_state.json \
    --budget 25
```

提 budget 后:
- 若新 budget > 旧 budget,清掉 `warned_at_pct` 里**已不再 >= 当前 used_pct** 的阈值(让 warn 重新生效)
- 若新 budget < 旧 budget,保留全部 warn 历史(防止 warn 不再 trigger)

### reset — 清零 cost 块(budget 保留)

```bash
python3 scripts/track_cost.py reset \
    --state <deck>/author/deck_v1_state.json
```

reset 只清 token / warn 历史,**budget 不动**。用于 deck 重做 / 跑 ablation。

## 主线程怎么用(pipeline 集成)

详见 [`.claude/pipeline-protocol.md § 0d. Cost budget 检查`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#0d-cost-budget-检查p3-17)。简短版:

1. **brainstorm 收 brief 阶段**:必问 `cost_budget_usd`(默认 10);写到 `brief.md` 必填字段 + `brainstorm/state.json` cost.budget_usd
2. **agent 跑完 return 后**:主线程**立即**跑 `track_cost.py status --deck <wd>`
3. **exit 2 / over budget**:暂停 + 询问用户:
   - (1) 继续 → 写 sentinel `<deck>/.budget_overridden`,本次 deck 不再检查
   - (2) 终止 → 不再派 agent,告知用户已有产物路径
   - (3) 提 budget → 跑 `set-budget --budget <new>`,继续派下一棒

## 怎么改 budget

### Brief 阶段(brainstorm 还没 dispatch_author)

用户在对话里告诉 brainstorm:"预算改成 20"。brainstorm 更新 `collected.cost_budget_usd` + 重写 brief.md。

### 中途(已经在跑 author / critic / builder / audience)

用户在主线程**询问"over budget 三选一"时答 (3)**,主线程跑 `set-budget --budget <new>`,继续派下一棒。

也可用户主动喊"提 budget 到 X" — 主线程跑同样命令。

## 怎么 reset

```bash
# 清 token / warn 历史,保留 budget
python3 scripts/track_cost.py reset \
    --state <deck>/author/deck_v1_state.json

# 同时改 budget
python3 scripts/track_cost.py set-budget \
    --state <deck>/author/deck_v1_state.json --budget 20
```

reset 不删 cost block,只清里面的 token 累计 + warn 历史。`last_updated` 更新到 reset 时刻。

## FAQ

**Q: 默认 10 USD 怎么估的?**
A: 一份 standard deck(brief + 5 章节 + 5 视觉)在我们的 dogfood 经验里大概 $3-8。10 USD 留 ~2× 余量,既不会 false alarm,也不让 runaway agent 跑到 $50。复杂 deck(20 + 页 / 多轮 audience)需要 brief 阶段提到 $20-25。

**Q: 我不想要 budget warning 怎么办?**
A: brief 阶段答"不限",brainstorm 写 `cost_budget_usd: 9999`。effective disable。

**Q: 跨 100% 后主线程一定会停吗?**
A: 默认会暂停问 user。**用户选 (1) 继续后**,主线程在 `<deck>/.budget_overridden` 写 sentinel,后续不再跑 status 检查。下次 reset / 新 deck 重新生效。

**Q: token 是怎么传给 track_cost.py 的?**
A: 由各 agent 在 SendMessage / Task return 后自己跑 `track_cost.py update --agent <name>`(详 cost tracking 设计;主线程不代写)。本预算机制只加 budget 校验层,不改 update 路径。

**Q: 多 deck 同时跑会冲突吗?**
A: 不会。每个 deck 自己的 state.json,track_cost.py 只读 `--deck` 指向的目录。
