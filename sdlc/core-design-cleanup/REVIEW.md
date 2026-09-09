# 评审：清理 uliweb/core 设计缺陷（死代码/遮蔽/异常用错）

<!--
REVIEW.md 作为本意图工件链的 Deploy 阶段工件（前序：intent.md → spec.md → plan.md → 实施提交）。
记录本次清理的评审结论（审计轨迹），并作为后续 AI 进评审环的评审策略。
前序工件见同目录 intent.md / spec.md / plan.md。
-->

---
类型: review
来源: plan.md（实施提交历史）
状态: approved
创建: 2026-09-08
评审: zhangchunlin（技术负责人）
---

## Passes（评审跑哪些 pass）

- **Bugs**：逻辑错误、坏掉的边界情况、细微回归
- **Security**：注入风险、认证缺口、日志里的 PII、路径遍历
- **Compliance**：改动符合 spec.md / plan.md 与设计原则（asgi-migration 已批准设计、一个目的一个提交）

## 评审对象（build 产物）

- 实施提交已合入 `asgi` 分支（见 `git log`，工作区干净）。
- 验收门槛（plan.md §终检）：`nosetests --with-doc test` 通过（**320 passed，OK**）。
- 关键覆盖：`test/test_url_for_static.py`（context.py 删除后的 url_adapter/url_for_static 回归）、`test_async_dispatcher`、`test_expose`/`test_url_for`/`test_url`、`test_middleware*`。

## 评审结论

| 维度 | 结论 | 备注 |
|------|------|------|
| **Bugs** | 通过 | `get_settings` 加载器改名避免遮蔽（secretkey 命令不再 TypeError）；`get_rule`/`get_url_adapter` 去 werkzeug（manage 命令不再 AttributeError）；jsonp 用 `status_code=400`；dispatch 不再抛字符串 |
| **Security** | 通过 | 无新增注入/路径面；仅删死代码与失效别名 |
| **Compliance** | 通过 | 上下文真相源收敛为 SimpleFrame LocalProxy（与 asgi-migration §3.7 一致）；删除 context.py；未 reintroduce werkzeug；一个目的一个提交 |
| 测试 | 通过 | 验收命令全绿；受影响用例已回归 |

**审批决定：approve**。未发现 Important 级问题。

## 待跟进（结转至 Maintain 阶段，非阻塞）

- `get_rule` 重写为按 `router.iter_rules()` + Starlette `Match.FULL` 匹配：若某 URL 依赖精确路径参数语义，建议后续补充 `get_rule` 的针对性单测（当前无直接用例覆盖 manage 命令路径）。
- `context.py` 已删除：若外部项目仍有 `from uliweb.core.context import ...`，会 ImportError（内部已全部改指向 SimpleFrame）。

## 评审者使用方式（后续沿用）

- 评审意见上 `@claude` → 让 Claude 回应并修复。
- 某错误第二次被评审标出 → 把纠正写回 `AGENTS.md`。
- 评审也标记"改动让 AGENTS.md 过时"的情况。
- 封顶 nit：每次至多报告 5 条，其余汇总为计数。
- 不报告：生成文件、CI 已强制的任何内容。
