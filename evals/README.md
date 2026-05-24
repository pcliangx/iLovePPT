# iLovePPT Eval 回归集

固定 deck_plan → build → render,检出 layout / build 代码回归。

## 跑

```bash
bash evals/run_eval.sh
```

## 评分

runner 出 `${CLAUDE_PROJECT_DIR}/evals/_run/scorecard.md` 模板。Claude 用 Read 看
`${CLAUDE_PROJECT_DIR}/evals/plans/<name>_render/page-*.jpg`,按 `rubric.md` 逐页记 fail 项,填 scorecard。

## 回归判定

新 scorecard 对比 `${CLAUDE_PROJECT_DIR}/evals/baseline/scorecard.md`。fail 项变多 = 回归。

## 为什么用固定 plan

eval 隔离"layout / build 代码"的确定性回归,不掺 Claude brief→plan 拓写的不确定性。

## 目录

- `plans/` —— 固定参考 deck_plan（8 个,Task 6 产出）
- `rubric.md` —— 16 项评分标准
- `run_eval.sh` —— 批量 build + render + 出 scorecard 模板
- `baseline/` —— 基准 scorecard（Task 7 产出）
- `_run/` —— 每次跑的临时产物（git 忽略）
