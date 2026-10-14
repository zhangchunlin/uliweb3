# Plan: 修复 set_log 重复初始化与 Logger Handlers 累加问题

---
类型: plan
状态: 已完成
创建: 2026-10-14
---

## 实施步骤

1. **修改 SimpleFrame.py**
   - 在 `SimpleFrame.init()` 中添加 `_log_initialized` 检查，与 `prepare()` 行为保持一致。
   - 在 `SimpleFrame.set_log()` 中，处理命名 Logger 时如果配置了 `handlers`，先清空已有 `log.handlers`，并在末尾设置 `self._log_initialized = True`。

2. **编写测试用例**
   - 在 `test/test_async_dispatcher.py` 中添加 `test_set_log_idempotent_no_duplicate_handlers`。
   - 同步函数 + 异步驱动，兼容 `nosetests` 与 `pytest`。

3. **测试验证**
   - 执行 `nosetests --with-doc test/test_async_dispatcher.py`。
   - 执行 `pytest test/test_async_dispatcher.py`。
   - 在主项目运行复现脚本，验证 `access` logger 输出从 2 条恢复为 1 条。

4. **提交 Gerrit 并监控审查**
   - 创建标准 commit（包含 Change-Id）。
   - 推送至 `review` (`refs/for/asgi`)。
   - 轮询 Gerrit review 状态。
