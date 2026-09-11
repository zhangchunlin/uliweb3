# Intent: NullPool 惰性 Result 跨查询诊断（nullpool-lazy-result-diagnostics）

---
类型: intent
状态: draft
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: agent-gateway 排障（uliweb-framework-improvement-proposals.md #2，与 #4 同根因）

## 问题

- SQLite + `NullPool` + async 下，惰性查询结果上迭代（`for a in agents`）的同时循环体内又发起另一条查询，外层游标报 `sqlite3.ProgrammingError: Cannot operate on a closed database.`——报错位置（外层 `fetchone`）与真正根因（内层查询关闭共享连接）毫无关联，且只在特定配置下复现，单测难覆盖。

## 期望结果

- 连接 `acquire / release / close` 时（debug 级）记录调用栈，关闭时如有活动游标打一条带完整链路的高优先级日志。
- 同一连接上"上一个 Result 未迭代完又发起新查询"时直接警告：`A lazy Result on connection X is still open while a new query started; materialize with list() first.`
- 报错信息增强：包装 `Cannot operate on a closed database` 时带上该连接最后一次 close 的调用栈。

## 受影响的用户与系统

- 使用惰性 `Result`（`Model.filter(...).all()`，`all()` 返回 `self` 惰性迭代）的 async 用户，尤其 NullPool + SQLite。
- 相关文件：`uliweb/orm/__init__.py` `Result` ~L2649（`all` ~L2738 返回 self、`filter` ~L2789、`connection = model.get_session()`）、连接/会话层。

## 约束

- 追踪仅在 debug/警告级，不拖累性能主线。
- 只增强可诊断性，不改惰性/连接语义。

## 开放问题

- 两条诊断落在**不同层**（不是二选一，各自 hook）：
  - "惰性 Result 未迭代完又开新查询"的检测 → **Result 层**（`Result` 持有 `self.connection`，~L2649；`all` ~L2738 返回 self）。
  - 连接 `acquire/release/close` 调用栈追踪、"closed database 带最后一次 close 栈" → **连接/会话层**（`get_session` ~L558 等）。
  - 待定：具体 hook 点分别在哪、debug 级开关放哪。
- 是否连同 #4（`all()` 惰性语义文档化 / `.list()`）一并处理——同根因，倾向合并为一个 feature。
