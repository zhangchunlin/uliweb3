# Intent: 进程关闭/重载 teardown 日志降噪（teardown-log-noise）

---
类型: intent
状态: draft
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: agent-gateway 排障（uliweb-framework-improvement-proposals.md #5）

## 问题

- 服务停止 / `--reload` 重载时事件循环先拆，在途异步 DB 收尾 `cursor.close()` 跑在已关闭连接上，刷出大量 `Error closing cursor` / `sqlite3.ProgrammingError: Cannot operate on a closed database.` / `anyio ... KeyError: 'asyncio'`，正常关闭被当成出错。

## 期望结果

- 关闭阶段特有的 `closed database` / `KeyError: 'asyncio'` 降级为 debug 级，并归一到一条摘要，避免刷屏。
- 文档给出优雅关闭顺序约定：先停后台任务（WS/事件总线/定时器），再 dispose engine。

## 受影响的用户与系统

- 所有停止服务 / 使用 `--reload` 的开发者。
- 相关文件：ORM 连接/游标收尾；`uliweb/contrib/orm` 事务/连接相关中间件；关闭/重载流程。

## 约束

- 只降噪，不掩盖真正的 500 错误日志（真错误保持高优先级）。
- 与既有"启动日志降级 debug"方向一致。

## 开放问题

- 如何可靠识别"关闭阶段"（事件循环拆除中），避免误降级真实错误。
- 优雅关闭顺序文档放哪（`docs/zh_CN` 哪一节、是否进 AGENTS.md）。
