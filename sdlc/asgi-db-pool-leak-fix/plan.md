# Plan: ASGI 作用域级 to_thread 与 WebSocket 连接防泄漏实施与验证计划

---
类型: plan
状态: approved
创建: 2026-10-10
更新: 2026-10-12
实现针对: docs/sdlc/asgi-db-pool-leak-fix/spec.md
---

## 一、文件变更与创制清单

| 变动文件 | 类型 | 核心职责与改动点 |
| :--- | :---: | :--- |
| `uliweb/core/SimpleFrame.py` | 核心修改 | 1. 实现轻量级 `to_thread(func, /, *args, **kwargs)`，封装 `except: RollbackAll()` 与 `finally: ResetAll()`。<br>2. 在 `_open_websocket` 中为同步 WebSocket 处理器注入 `_sync_ws_wrapper`，记录回滚与释放警告日志。<br>3. 保留 `ORMSafeThreadPoolExecutor` 存根类与 `AsyncDispatcher.safe_executor` 向后兼容属性。<br>4. 增加 `AsyncDispatcher.to_thread` 实例代理方法并将 `to_thread` 导出至 `__all__`。<br>5. 替换遗留的 `asyncio.get_event_loop()` 为 `asyncio.get_running_loop()`。 |
| `uliweb/__init__.py` | 导出声明 | 顶层导出 `to_thread` 与 `ORMSafeThreadPoolExecutor`，加入 `__all__`。 |
| `test/test_async_dispatcher.py` | 单元测试 | 针对性补充 `to_thread` 异常回滚与释放、ContextVar 传播、只读防隐式提交、WebSocket 处理器释放及模块导出单元测试。 |
| `docs/sdlc/asgi-db-pool-leak-fix/` | 规范工件 | 准确记录方案 B 作用域级 `to_thread` 架构意图、规格说明书与实施验证计划。 |
| `sdlc/asgi-db-pool-leak-fix/` | 规范工件 | 保持与 `docs/sdlc/` 同步。 |

---

## 二、分步实施计划 (Step-by-Step Implementation)

### 阶段一：框架核心层连接生命周期闭环
1. **实现作用域级 `to_thread`**：
   - 在 `SimpleFrame.py` 中实现非侵入式的 `to_thread`。
   - 使用 `copy_context()` 传播 ContextVars 上下文，在工作线程内执行同步函数。
   - 在发生异常时触发 `RollbackAll()`，并在 `finally` 阶段调用 `ResetAll()`，记录失败详细日志。
   - 事务提交由业务函数显式控制，避免静默提交只读查询。
2. **强化 WebSocket 同步处理器生命周期**：
   - 在 `_open_websocket` 内部为同步处理器注入 `_sync_ws_wrapper`。
   - 异常路径执行 `RollbackAll()` 并记录警告日志，退出时在 `finally` 中执行 `ResetAll()` 并记录警告日志。
3. **向后兼容性与 API 规范化**：
   - 保留 `class ORMSafeThreadPoolExecutor(ThreadPoolExecutor): pass`。
   - 保留 `AsyncDispatcher.safe_executor`（返回 None）与 `AsyncDispatcher.to_thread`。
   - 将 `SimpleFrame.py` 中的 `asyncio.get_event_loop()` 全面替换为 `asyncio.get_running_loop()`。

### 阶段二：自动化单测开发与断言补充
1. **编写 `to_thread` 异常回滚与释放测试**：
   - 验证正常完成时工作线程调用 `ResetAll()`；
   - 验证抛出异常时工作线程依次调用 `RollbackAll()` 与 `ResetAll()`；
   - 验证 `dispatcher.to_thread` 代理方法行为一致。
2. **编写 ContextVar 传播测试**：
   - 验证在主协程中设置的 ContextVar 能够在工作线程中正确读取。
3. **编写只读防隐式提交测试**：
   - 验证普通只读业务执行后，工作线程不触发 `CommitAll()`。
4. **编写 WebSocket 同步处理器释放测试**：
   - 验证同步 WebSocket 处理函数在正常退出或异常抛出时均触发 `ResetAll()`。
5. **编写顶层导入兼容性测试**：
   - 验证 `from uliweb import to_thread, ORMSafeThreadPoolExecutor` 正常导出。

### 阶段三：全量自动化回归验证
1. **Uliweb3 全量测试回归**：
   - 运行 `pytest test/test_async_dispatcher.py test/test_request_async.py test/test_websocket.py test/test_sse_streaming.py -v`，要求 68 项测试全部通过（0 失败）。
2. **下游应用集成测试回归**：
   - 运行 Knowbot 测试 `PYTHONPATH=. pytest tests/ -v --ignore=tests/test_report_agent_skills.py`，要求 93 项测试 100% 绿灯。

---

## 三、验证与断言物理凭证 (Verification Checklist)

- [x] **单测 1**：`test_to_thread_calls_rollback_and_reset_all` 验证作用域级 `to_thread` 正常调用 ResetAll，异常调用 RollbackAll 与 ResetAll。
- [x] **单测 2**：`test_to_thread_contextvars_propagation` 验证 `to_thread` 正确继承与传播 ContextVar。
- [x] **单测 3**：`test_to_thread_no_implicit_commit` 验证 `to_thread` 只读查询不隐式提交事务。
- [x] **单测 4**：`test_websocket_sync_handler_resets_connection` 验证同步 WebSocket 处理器连接释放。
- [x] **单测 5**：`test_import_to_thread_from_uliweb` 验证顶层模块导出兼容性。
- [x] **框架相关单测**：全量测试 100% 绿灯（68/68 ASGI 测试通过）。
- [x] **业务全量单测**：Knowbot 93 项集成测试 100% 绿灯通过。
