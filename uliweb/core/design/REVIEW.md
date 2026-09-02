# 评审：Uliweb ASGI 迁移（Deploy 阶段 PR 评审结论）

<!--
REVIEW.md 作为本迁移工件链的 Deploy 阶段工件（前序：intent.md → spec.md → plan.md → build diff）。
它既记录本次 PR 的评审结论（审计轨迹），也作为后续 AI 进 PR 评审环的评审策略。
前序工件见同目录 intent.md / spec.md / plan.md。
-->

---
类型: review
来源: plan.md（build diff / 提交历史）
状态: approved
创建: 2026-09-02
评审: zhangchunlin（技术负责人）
---

## Passes（评审跑哪些 pass）

- **Bugs**：逻辑错误、坏掉的边界情况、细微回归
- **Security**：注入风险、认证缺口、日志里的 PII、路径遍历
- **Compliance**：改动符合 spec.md / plan.md 与设计原则

## 评审对象（build 产物）

- 迁移 diff 已提交并合入 `asgi` 分支（见 `git log`，工作区干净）。
- 验收门槛（plan.md §证明）：`nosetests --with-doc test` 通过（OK，无失败/错误）。
- 关键覆盖：`test_async_dispatcher`、`test_request_async`、`test_expose`/`test_url_for`/`test_url`、
  `test_middleware`/`test_middleware_init`、`test_websocket`/`test_sse_streaming`、`test_mail`、`test_orm*`/`test_cache`/`test_session`。

## 评审结论

| 维度 | 结论 | 备注 |
|------|------|------|
| **Bugs** | 通过 | 同步适配器（`anyio.to_thread.run_sync`）覆盖同步视图；async property 陷阱已用显式异步方法规避 |
| **Security** | 通过 | 静态文件服务内置路径遍历防护与隐藏文件控制；CORS 默认收敛 |
| **Compliance** | 通过 | 实现集中于 `SimpleFrame.py`（无独立 `starlette.py`）；`@expose`/`settings.ini`/`url_for` 对外契约保持 |
| 测试 | 通过 | 验收命令通过；WebSocket/SSE/ORM 异步适配均有用例 |

**审批决定：approve**，可进入部署。未发现 Important 级问题。

## 待跟进（结转至 Maintain 阶段，非阻塞）

- `test_cache.test_redis` 需本地 Redis（`localhost:6379`），CI 未启动时会报连接错误 → 在部署环境单独跑或标记。
- Python 3.10+ 缺 `pkg_resources` 时静态文件相关用例自动 `SkipTest` → 确认目标运行环境是否具备。

## 评审者使用方式（后续 PR 沿用）

- 评审意见上 `@claude` → 让 Claude 回应并修复。
- 某错误第二次被评审标出 → 把纠正写回 `AGENTS.md`。
- 评审也标记"改动让 AGENTS.md 过时"的情况。
- 封顶 nit：每次至多报告 5 条，其余汇总为计数。
- 不报告：生成文件、CI 已强制的任何内容。
