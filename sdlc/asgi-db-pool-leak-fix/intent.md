# Intent: 修复 ASGI 线程池同步中间件与视图导致的数据库连接永久泄露 (idle in transaction) 及连接池扩容

---
类型: intent
状态: approved
创建: 2026-10-10
作者: Jay JN1 Tang / Antigravity
关联工单/事故: 生产环境数据库连接异常 (QueuePool limit reached 30s timeout & PG idle in transaction 30~45min)
---

## 一、问题背景与生产痛点

在生产环境中，系统偶发出现 API 阻塞并抛出以下错误：
```text
sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 3 reached, connection timed out, timeout 30
```
经深入排查 PostgreSQL 活跃状态视图（`pg_stat_activity`），发现存在大量持续 30~45 分钟处于 `idle in transaction` 状态的数据库连接，卡在如下查询上：
- `SELECT httpcred... FROM httpcred WHERE httpcred."user" = 87 LIMIT 1`
- `SELECT usergroup.name... FROM usergroup, orgrole_usergroup_usergroups WHERE orgrole_usergroup_usergroups.orgrole_id = 2 ...`

### 深度根因分析
1. **子线程同步中间件导致连接泄露（idle in transaction）**：
   - Uliweb ORM 的 Engine 会话管理强依赖 `threading.local()` 保存 `local.session`。
   - 在 ASGI 模式下，事件循环运行在主线程，而传统同步中间件（如 `HttpcredMiddle.process_request`、`SessionMiddle.process_request`）由 `SimpleFrame.py` 的 `_call_middleware_method` 派发到 `ThreadPoolExecutor` 的 Worker 子线程中执行。
   - 当中间件在子线程中调用 `User.get(...)` 或访问关联关系时，子线程自动从 SQLAlchemy 的 `QueuePool` 借出连接并隐式开启数据库事务。
   - 框架此前在 `_call_middleware_method` 执行完毕后**没有任何事务收敛逻辑（无 Commit、无 Rollback，更无 ResetAll）**；而 ASGI 主请求在事件循环主线程结束时调用的 `CommitAll()`，由于 `threading.local()` 的线程隔离性，**完全触及不到子线程的 Session**。导致子线程借出的物理连接一直停留在 `idle in transaction` 状态，无法返还连接池。
2. **同步视图与生命周期未调用 `ResetAll()` 释放连接**：
   - 同步视图在 `_call_function` 内的 `sync_orm_wrapper` 虽然有 `CommitAll()`，但**缺失了 `ResetAll()`（即 session.close()）**。
   - 在 SQLAlchemy 的 `QueuePool` 机制中，仅仅 `Commit()` 只能让 PostgreSQL 服务端状态从 `idle in transaction` 变为 `idle`，但 `pool.checkedout()` 计数并不减少，物理连接仍然被该子线程持有，无法被其他请求或线程复用。
3. **单进程连接池容量过小**：
   - 原配置 `pool_size: 2, max_overflow: 3`，单个 Worker 进程最多仅允许持用 5 个物理连接。
   - 当单用户前端页面初始化发起 4~6 个并发请求（鉴权、用户自检、数据集查询、权限校验、会话列表、SSE 握手）时，若同时打在同一个 Worker 上，第 6 个请求必然因连接池耗尽而排队超时崩溃。

---

## 二、期望结果

1. **子线程同步中间件生命周期完整收尾**：
   - 同步中间件执行完毕后，在子线程中自动触发 `CommitAll()`。
   - 中间件若抛出异常，在子线程中自动触发 `RollbackAll()`。
   - 在 `finally` 阶段无条件执行 `ResetAll()`，调用 `session.close()` 将底层物理连接干净地归还给 `QueuePool`。
2. **同步视图与主请求生命周期释放保护**：
   - `sync_orm_wrapper` 在同步视图执行完毕后的 `finally` 阶段调用 `ResetAll()`。
   - ASGI 请求处理失败及主中间件链的 `finally` 阶段调用 `ResetAll()`。
3. **多方言连接池参数安全兼容**：
   - 优化 `NamedEngine._create`，针对 SQLite 驱动自动剔除 QueuePool 专属参数（`pool_size`, `max_overflow`, `pool_timeout`），防止在纯 SQLite 开发或单测环境下报 `TypeError: Invalid argument(s)`。
4. **连接池容量与健康探测提升**：
   - 生产环境连接池参数升级为 `pool_size: 10, max_overflow: 15, pool_recycle: 300, pool_pre_ping: True, pool_timeout: 30`。
   - 启用 `pool_pre_ping=True` 杜绝网络假死连接，配置 `pool_recycle=300` 定期回收长连接。

---

## 三、受影响系统与组件

- **受影响框架组件**：
  - `uliweb.core.SimpleFrame`：ASGI 中间件调度器与同步视图执行器。
  - `uliweb.orm.NamedEngine`：ORM 引擎创建与连接池初始化。
- **受影响应用**：
  - 所有基于 Uliweb3 ASGI 运行并使用 Uliweb ORM 的应用模块（含 Knowbot、Uliweb-Lapps 等）。
- **相关核心代码文件**：
  - `uliweb/core/SimpleFrame.py`
  - `uliweb/orm/__init__.py`
  - `test/test_async_dispatcher.py`

---

## 四、约束与原则

1. **绝对向后兼容**：不破坏既有 WSGI 模式（若仍有使用）、不改变任何中间件接口定义与视图返回值格式。
2. **零破坏性测试红线**：修改后必须跑通 Uliweb3 全量单元测试（321 passed）及业务端全量测试。
3. **事务安全性**：仅在成功路径执行 `CommitAll()`，发生异常时执行 `RollbackAll()`，无论成败 `ResetAll()` 均必须在 `finally` 中被 100% 触发。
