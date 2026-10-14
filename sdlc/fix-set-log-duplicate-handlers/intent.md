# Intent: 修复 ASGI 模式下 set_log 重复初始化导致 Logger Handler 累加与日志重复输出

---
类型: intent
状态: approved
创建: 2026-10-14
---

- 作者: 框架组
- 关联工单/事故: ASGI 模式下 access_log 等配置的命名 Logger 输出两份日志

## 问题 （痛点）
- 在 ASGI 模式下，服务加载时（`make_application -> prepare()`）会首次调用 `self.set_log()` 并标记 `self._log_initialized = True`。
- 但是在首个请求到达并触发 `AsyncDispatcher.__call__ -> _async_init() -> init()` 时，`SimpleFrame.init()` 无条件且未判断 `_log_initialized`，再次调用了 `self.set_log()`。
- 此外，在 `SimpleFrame.set_log()` 中，仅对 `ROOT` logger 做了 `log.handlers = []` 清空，对 `[LOG.Loggers]` 中的其他命名 logger（如 `access`）未做 handlers 清空或去重，直接调用 `log.addHandler()`。
- 导致每次调用 `set_log()`，所有配置的命名 logger 都会重复累加挂载 handlers，最终引发请求访问日志和业务日志重复打印（输出两份）。

## 期望结果
- `SimpleFrame.init()` 增加 `if not hasattr(self, '_log_initialized') or not self._log_initialized:` 防御，与 `prepare()` 行为对齐，避免重复初始化日志系统。
- `SimpleFrame.set_log()` 对 `[LOG.Loggers]` 中的命名 logger 配置 handlers 时，实现幂等重置或去重，即使 `set_log()` 被多次显式调用，同名 Logger 挂载的 handlers 数量保持稳定，不发生线性累加。
- 在 `set_log()` 执行后标记 `self._log_initialized = True`。
- 增加针对 `set_log` 幂等性与 ASGI 初始化日志无重复 handler 的单元测试用例，`nosetests` 与 `pytest` 均全绿通过。

## 受影响的用户与系统
- `uliweb/core/SimpleFrame.py`：`SimpleFrame.init()` 与 `SimpleFrame.set_log()`。
- 所有使用 ASGI 部署并通过 `[LOG.Loggers]` 配置了命名 Logger（如 access、sql 等）的应用。

## 约束
- 保持向后兼容，不改变已有的日志配置语法和行为。
- 测试用例必须兼容 nose 1.3.7 与 pytest。
