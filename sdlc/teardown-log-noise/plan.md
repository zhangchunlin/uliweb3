# Plan：进程关闭/重载 teardown 日志降噪（teardown-log-noise）

---
类型: plan
来源: spec.md（approved）
状态: 待执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. feat(SimpleFrame)：置"正在关闭"标记**
      在 `_handle_lifespan_request` 的 `shutdown` 分支（~L1553-1556）置 `self._shutting_down = True`（dispatcher 实例属性，spec §5 定案；不用 contextvar）。
      验证：lifespan shutdown 事件后 `_shutting_down` 为 True；`nosetests` 全绿。

- [ ] **2. feat(orm)：关闭阶段 `sqlite3.ProgrammingError` 降级 + 归一**
      在连接/游标收尾关闭的异常处理处，若 `self._shutting_down` 且异常为 `sqlite3.ProgrammingError`（含 `Cannot operate on a closed database`），降为 `logger.debug` 并归一到一条摘要（首条完整 + 后续计数）；其它异常不降级（spec §5 保守定案）。
      验证：模拟关闭期连接已拆的游标关闭，断言 debug 级 + 归一、无刷屏；非关闭阶段/非该异常类型不降级；`nosetests` 全绿。

- [ ] **3. docs(zh_CN)：补"优雅关闭顺序"**
      约定：先停后台任务（WS/事件总线/定时器），再 dispose engine；给出推荐 shutdown 流程，说明关闭期 `Cannot operate on a closed database` 属正常收尾噪音。
      验证：渲染审阅小节完整。

- [ ] **4. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；3 处改动落位。

## 验证命令
- `nosetests --with-doc test`（仓库根）

## 风险与缓解
- **最可能弄坏**：误降级真实 `sqlite3.ProgrammingError` → 缓解：仅 `_shutting_down` 为真且匹配该类型/消息才降级，其它一律不降。
- **最冒险一步**：第 1 步改 lifespan shutdown 路径 → 缓解：改动最小（仅置布尔标记），不触碰关闭时序。
- **放弃的做法**：不在此阶段改关闭/重载实际时序（spec §5 结转），只做日志降噪 + 文档约定。
