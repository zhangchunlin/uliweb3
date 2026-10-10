# Plan: ASGI 线程池同步中间件与视图连接池泄露修复实施与验证计划

---
类型: plan
状态: approved
创建: 2026-10-10
实现针对: docs/intent/asgi-db-pool-leak-fix/spec.md
---

## 一、文件变更与创制清单

| 变动文件 | 类型 | 核心职责与改动点 |
| :--- | :---: | :--- |
| `uliweb/core/SimpleFrame.py` | 核心修改 | 1. 导入 `ResetAll`。<br>2. `_call_middleware_method` 增加 `sync_middleware_wrapper` 闭包与 Commit/Rollback/ResetAll 链路。<br>3. `sync_orm_wrapper` 与主请求生命周期增加 `ResetAll()` 释放。 |
| `uliweb/orm/__init__.py` | 兼容防御 | 在 `NamedEngine._create` 中对 SQLite 连接过滤 `pool_size`, `max_overflow`, `pool_timeout`。 |
| `test/test_async_dispatcher.py` | 单元测试 | 新增同步中间件成功与失败路径下的事务提交、回滚与 ResetAll 回调断言用例。 |
| `knowbot/apps/local_settings.ini` | 生产配置 | 更新 `[ORM] CONNECTION_ARGS = {'pool_size': 10, 'max_overflow': 15, 'pool_recycle': 300, 'pool_pre_ping': True, 'pool_timeout': 30}`。 |
| `knowbot/apps/settings.ini` | 文档规范 | 增加 PostgreSQL 生产推荐连接池配置注释模板。 |

---

## 二、分步实施计划 (Step-by-Step Implementation)

### 阶段一：框架核心层连接生命周期闭环
1. **重构 `SimpleFrame._call_middleware_method`**：
   - 提取同步中间件执行逻辑为闭包 `sync_middleware_wrapper`。
   - 子线程内包裹 `try...except...finally` 块，执行 `CommitAll()`、`RollbackAll()` 与 `ResetAll()`。
2. **强化 `sync_orm_wrapper` 与 ASGI 顶层栈**：
   - 在 `sync_orm_wrapper` 的 `finally` 阶段调用 `ResetAll()`。
   - 在 `_wrap_traditional_middleware` 请求失败及完成的 `finally` 阶段调用 `ResetAll()`。
3. **ORM 引擎参数防御**：
   - 在 `NamedEngine._create` 增加针对 SQLite 方言的连接池专有参数安全过滤。

### 阶段二：自动化单测开发与断言补充
1. **编写中间件成功提交与 Reset 测试**：
   - 在 `test_async_dispatcher.py` 中构造带 `process_request` 的同步中间件。
   - 使用 Mock 拦截 `CommitAll`、`RollbackAll`、`ResetAll`。
   - 模拟通过 ASGI 栈调用，断言 `CommitAll` 与 `ResetAll` 均被成功调用 1 次，`RollbackAll` 调用 0 次。
2. **编写中间件异常回滚与 Reset 测试**：
   - 构造抛出异常的同步中间件。
   - 断言捕获到预期异常，且 `RollbackAll` 与 `ResetAll` 各被成功调用 1 次，`CommitAll` 调用 0 次。

### 阶段三：全量自动化回归验证
1. **Uliweb3 全量测试回归**：
   - 运行 `pytest test/`，要求 321 项测试全部通过（0 失败）。
2. **下游应用集成测试回归**：
   - 运行 Knowbot 测试 `pytest tests/`，要求 97 项测试 100% 绿灯。
3. **真实数据库连接监控验证**：
   - 发起高频并发请求与 SSE 连接切换。
   - 通过 `pg_stat_activity` 校验 PostgreSQL 活跃连接状态，断言无任何残留 `idle in transaction`。

---

## 三、验证与断言物理凭证 (Verification Checklist)

- [x] **单测 1**：`test_async_dispatcher_sync_middleware_commit_and_reset` 验证通过。
- [x] **单测 2**：`test_async_dispatcher_sync_middleware_rollback_and_reset` 验证通过。
- [x] **单测 3**：`test_async_dispatcher_sync_handler_transaction_commit` 包含 `ResetAll` 断言通过。
- [x] **单测 4**：`test_async_dispatcher_sync_handler_transaction_rollback` 包含 `ResetAll` 断言通过。
- [x] **框架全量单测**：321 passed, 1 skipped, 0 failed（耗时 2.03s）。
- [x] **业务全量单测**：Knowbot 97 passed, 0 failed（耗时 5.12s）。
- [x] **数据库状态检查**：`pg_stat_activity` 监控确认 `idle in transaction` 为 0。
