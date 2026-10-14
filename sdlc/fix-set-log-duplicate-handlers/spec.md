# Spec: 修复 set_log 重复初始化与 Logger Handlers 累加问题

---
类型: spec
状态: 已实现
创建: 2026-10-14
---

## 1. 背景与目标
在 ASGI 应用启动和首次请求处理过程中，`set_log()` 会被重复调用两次（`prepare()` 一次，`init()` 一次），且 `SimpleFrame.set_log()` 缺少针对命名 Logger 的 handlers 清空/幂等保护，导致 handlers 重复追加，造成日志重复打印。

目标：
1. 使 `SimpleFrame.init()` 具备日志初始化幂等保护。
2. 使 `SimpleFrame.set_log()` 对 `[LOG.Loggers]` 中的命名 Logger 配置具有幂等性，重置 handlers 时不重复追加。
3. 单元测试覆盖验证。

## 2. 详细设计

### 2.1 `SimpleFrame.init()` 防重复守护
在 `SimpleFrame.init()` 中（约第 1337 行）：
```python
# 修改前：
self.set_log()

# 修改后：
if not hasattr(self, '_log_initialized') or not self._log_initialized:
    self.set_log()
    self._log_initialized = True
```

### 2.2 `SimpleFrame.set_log()` 幂等保护
在 `SimpleFrame.set_log()` 中（约第 1494 行）：
```python
# process loggers
for logger_name, v in s.get_var('LOG.Loggers', {}).items():
    if logger_name == 'ROOT':
        log = logging.getLogger('')
        log.handlers = []
    else:
        log = logging.getLogger(logger_name)
        if 'handlers' in v:
            log.handlers = []

    if v.get('level'):
        log.setLevel(_get_level(v.get('level')))
    if 'propagate' in v:
        log.propagate = v.get('propagate')
    if 'handlers' in v:
        for h in v['handlers']:
            if h in handlers:
                log.addHandler(handlers[h])

self._log_initialized = True
```
- 当 `v` 包含 `handlers` 定义时，先将 `log.handlers` 置空，确保重新配置时不重复追加旧 Handler。
- 方法末尾设置 `self._log_initialized = True`。

### 2.3 测试用例设计
编写 runner 无关（兼容 nose 与 pytest）的测试用例：
1. 验证 `set_log()` 多次调用时，命名 Logger 的 handlers 数量保持恒定（幂等）。
2. 验证 ASGI 应用经历 `prepare()` 到 `init()` 完整流程后，配置的命名 Logger 仅包含 1 个 Handler，避免重复日志。

## 3. 验收标准
- `nosetests --with-doc test/test_async_dispatcher.py` 运行通过。
- `pytest test/test_async_dispatcher.py` 运行通过。
