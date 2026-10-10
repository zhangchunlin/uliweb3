# Intent: ASGI 作用域级 to_thread 与 WebSocket 同步处理器数据库连接生命周期管理与防泄漏

---
类型: intent
状态: approved
创建: 2026-10-10
更新: 2026-10-12
作者: Jay JN1 Tang / Antigravity
关联工单/事故: 生产环境数据库连接异常 (QueuePool limit reached 30s timeout & PG idle in transaction 30~45min)
---

## 一、问题背景与治理阶段说明

在生产环境中，系统偶发出现 API 阻塞并抛出以下错误：
```text
sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 3 reached, connection timed out, timeout 30
```
经深入排查 PostgreSQL 活跃状态视图（`pg_stat_activity`），发现存在大量持续 30~45 分钟处于 `idle in transaction` 状态的数据库连接。

### 1.1 治理阶段回顾（前序基线提交已合入）
- **Commit `1f09c23`**：针对传统 HTTP 请求同步中间件（如 `HttpcredMiddle.process_request`、`SessionMiddle.process_request`）以及同步视图，在 `SimpleFrame.py` 中引入了 `sync_middleware_wrapper` 和 `sync_orm_wrapper`，实现了子线程内的 `CommitAll/RollbackAll/ResetAll` 闭环，并在 `NamedEngine._create` 中对 SQLite 连接过滤了连接池参数。
- **Commit `f58e453`**：针对 ASGI 协程视图（`iscoroutinefunction`），在 `call_handler` 中增加了非流式响应的 `CommitAll()`、异常回滚 `RollbackAll()` 以及 `finally: ResetAll()` 归还连接，并在 `AsyncDispatcher.__call__` 外层增加了兜底释放。

### 1.2 本次变更治理焦点（Patchset 12 核心交付）
在前序 HTTP 链路治理完成后，深度分析发现仍存在以下两处关键的**物理连接泄露盲区**：

1. **异步视图在 Worker 线程池中执行同步 ORM 操作未释放连接**：
   - 在 ASGI 模式的异步视图中，开发者广泛使用 `await asyncio.to_thread(func)` 或 `loop.run_in_executor(None, func)` 将耗时的同步操作（如会话查询、用户信息获取、批量数据处理）派发到后台工作线程中执行。
   - 工作线程在执行涉及 ORM 的操作时，会在该子线程的 `threading.local` 中借出数据库连接并隐式开启事务。
   - 由于标准库 `asyncio.to_thread` 对 Uliweb ORM 的线程局部存储（`threading.local`）一无所知，任务完成后线程直接归还线程池挂起，连接未调用 `ResetAll()`，导致该物理连接永久停留在 `idle in transaction` 状态；主请求在主线程结束时的生命周期清理，由于线程隔离完全无法触及子线程持有的 Session。
2. **同步 WebSocket 处理器在子线程执行未闭环**：
   - 同步 WebSocket 处理器在 `AsyncDispatcher._open_websocket` 中通过 `loop.run_in_executor` 派发到子线程执行。
   - 原有逻辑缺少针对工作线程内部的异常回滚与 `finally: ResetAll()` 闭环，一旦发生断开或异常，子线程中的数据库连接无法返还连接池。

---

## 二、期望成果与架构选型

### 2.1 方案选型：方案 B（轻量级作用域 to_thread）
历经对全局事件循环执行器替换（`ORMSafeThreadPoolExecutor` 劫持 `loop.set_default_executor`）的架构评估后，确认全局劫持存在如下缺陷：
- 侵入性过强，过度接管标准库 asyncio 内部调度机制；
- 引入了全局多 Dispatcher 竞争锁、loop 切换检测、弱引用终结器、在途任务排空超时及潜在死锁防护，累积 300+ 行非核心代码，系统复杂度高。

因此，技术评审明确决议采用 **方案 B（极简非侵入设计）**：
1. **轻量级显式 `to_thread`**：提供与标准库 `asyncio.to_thread` 签名完全一致的 `to_thread(func, /, *args, **kwargs)` 工具函数，在工作线程内部封装 `try: ... except: RollbackAll(); raise finally: ResetAll()`，并透明传播 `ContextVar`。
2. **显式事务边界原则**：仅在异常时自动触发 `RollbackAll()`，任务正常完成仅执行 `ResetAll()`，事务提交权显式交给业务函数自行决定（避免只读操作被隐式自动提交）。
3. **WebSocket 同步处理器安全包装**：在 `_open_websocket` 中对同步 WebSocket 处理器注入 `_sync_ws_wrapper`，统一实现异常回滚与 `finally: ResetAll()` 闭环。
4. **向后兼容与平滑演进**：保留 `ORMSafeThreadPoolExecutor` 存根类与 `AsyncDispatcher.safe_executor` 属性，确保老旧引用不发生 AttributeError。
5. **现代化改造**：全面替换废弃的 `asyncio.get_event_loop()` 为 `asyncio.get_running_loop()`。

---

## 三、受影响系统与组件

- **框架核心文件**：
  - `uliweb/core/SimpleFrame.py`：新增 `to_thread`、`ORMSafeThreadPoolExecutor` 存根、`_sync_ws_wrapper`、替换 `get_event_loop()`。
  - `uliweb/__init__.py`：顶层导出 `to_thread`。
  - `test/test_async_dispatcher.py`：精炼并新增针对 `to_thread` 与 WebSocket 释放的专属单元测试。
- **下游业务适配**：
  - 异步视图中的后台任务派发由 `asyncio.to_thread` 迁移为 `from uliweb import to_thread`。

---

## 四、约束与原则

1. **绝对向后兼容**：不破坏既有 ASGI/WSGI 运行模式，保持既有 API 签名稳定。
2. **零侵入与零副作用**：不篡改全局事件循环执行器，不影响非 ORM 任务的线程池调度性能。
3. **100% 测试通过保证**：Uliweb3 单元测试及下游 Knowbot 测试全量通过，无语法错误。
