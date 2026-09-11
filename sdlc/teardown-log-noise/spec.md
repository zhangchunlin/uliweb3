# Spec：进程关闭/重载 teardown 日志降噪（teardown-log-noise）

---
类型: spec
来源: intent.md（draft）
状态: approved
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：服务停止 / `--reload` 重载时事件循环先拆，在途异步 DB 收尾 `cursor.close()` 跑在已关闭连接上，刷出大量 `Error closing cursor` / `closed database` / `KeyError: 'asyncio'`，正常关闭被当成出错、淹没问题日志。
- **范围取向**：只降噪，不掩盖真正错误。
- **验收标准**：
  - Given 关闭/重载阶段，When 触发在途 DB 收尾，Then 关闭阶段特有的 `closed database` / `KeyError: 'asyncio'` 以 **debug 级**输出并**归一到一条摘要**（非刷屏）。
  - Given 真实 500 错误，When 发生，Then 优先级不变、不被降级。
  - 文档给出优雅关闭顺序约定（先停后台任务，再 dispose engine）。
  - `nosetests --with-doc test` 全绿。

- **非目标**：不改变关闭/重载实际时序（本阶段只做日志降噪 + 文档约定）；不改 engine/连接真实生命周期。

## 2. 范围与边界

- 在范围内：ORM/连接收尾的关闭阶段日志处理；`uliweb/core/SimpleFrame.py` `_handle_lifespan_request` 的 shutdown 路径（~L1520-1566）；`docs/zh_CN` 补优雅关闭顺序。
- 在范围外：改变关闭时序本身；改连接/事务真实行为。
- 关联系统：`sdlc/orm-lazy-init-diagnostics`（同为运行期可诊断性增强）；既有"启动日志降级 debug"。

## 3. 设计

- **总体方案**：用"关闭阶段"标记区分正常关闭 vs 真错误，关闭期特有错误降 debug 并归一。

- **3.1 识别关闭阶段**
  - 在 lifespan `shutdown` 路径（`_handle_lifespan_request`）置一个"shutting down"标记（如 `scope`/实例属性或 contextvar），关闭期收尾代码据此判断。
  - 也可用"事件循环已被拆除"（`asyncio.get_running_loop()` 抛 `RuntimeError`）作为关闭期特征。

- **3.2 关闭期特有错误降级 + 归一**
  - 对匹配 `Cannot operate on a closed database.` / `KeyError: 'asyncio'` 的收尾异常：降为 `logger.debug`。
  - 多条同类错误归一到一条摘要（首条完整 + 后续计数），避免刷屏。
  - 明确只对"关闭阶段 + 已知噪音类型"降级，其它异常保持原级别。

- **3.3 文档**
  - `docs/zh_CN` 补"优雅关闭顺序"：先停后台任务（WS/事件总线/定时器），再 dispose engine；给出推荐 shutdown 流程。

## 4. 约束与策略落地

- 只降噪；真错误（500/未知异常）不降级。
- 关闭期识别需可靠，避免误降级真实错误。
- 改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- **"正在关闭"状态承载** → **已定案：dispatcher 实例属性**（lifespan `shutdown` 分支置 `self._shutting_down = True`）。最简单、副作用最小，符合保守非破坏性取向；不用 contextvar。
- **降级异常清单** → **已定案（保守）：仅 `sqlite3.ProgrammingError`**（关闭阶段因连接先被拆导致的 `Cannot operate on a closed database`）在关闭阶段降级为 debug；其它异常不降级。
- 结转：优雅关闭的实际时序调整（若文档约定与实现不符）留待后续独立评估。
