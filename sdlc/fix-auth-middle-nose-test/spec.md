# Spec: 把 pytest-only 的 auth 中间件测试转为 nose 可执行

---
类型: spec
状态: 已实现        <!-- 审阅通过后 → approved，触发 plan mode；实现完成 → 已实现 -->
创建: 2026-10-14
---

## 1. 背景与目标

规范命令 `nosetests --with-doc test` 当前 426 tests / 1 error。唯一失败是上游 33d4b02 引入的
`test/test_auth_middle_asgi.py`——纯 pytest 写法（`@pytest.mark.anyio`、`async def`、`monkeypatch`），
nose 无法运行。

目标：该文件在 nose 下全绿且**两个用例都被真正执行**；同时不破坏 pytest 兼容。

## 2. 范围与边界

- 范围内：转换 `test/test_auth_middle_asgi.py` 为 runner 无关（nose + pytest 双兼容）写法。
- 范围外：不改任何产品代码；不改 `test_auth.py`/`test_manage.py`（那是 pytest 特有顺序/命名问题，非权威 runner 下的失败）。

## 3. 总体方案

把两条 `async def test_*` 改为同步 `def test_*`，用 `asyncio.run()` 驱动异步被测代码；用
`unittest.mock.patch.dict` 替换 `monkeypatch.setitem`。

- **测试 1 `test_auth_middle_syncs_user_to_scope`**：
  - `def test_auth_middle_syncs_user_to_scope():`（同步）
  - 内部 `async def _run():` 承载原 async 逻辑，末尾 `asyncio.run(_run())`。
  - `with patch.dict(functions._Finder__objects, {...})` 替代 `monkeypatch.setitem(...)`（两条）。
  - 断言不变。
- **测试 2 `test_call_next_propagates_scope_keys_on_success_and_error`**：
  - `def test_call_next_propagates_scope_keys_on_success_and_error():`（同步）
  - 原逻辑包进 `asyncio.run(...)`（成功路径 + 异常路径的 finally 传播）。
  - `pytest.raises(RuntimeError)` 替换为 `try/except RuntimeError` 断言（避免 pytest 依赖）。
- 文件级：移除 `import pytest` 与 `@pytest.mark.anyio`。

## 4. 顾虑点

1. `asyncio.run` 在 nose 与 pytest 下均可使用（Python 3.10+，AGENTS.md 支持 3.8–3.13；
   3.8/3.9 也有 `asyncio.run`）→ 兼容。
2. `patch.dict(functions._Finder__objects, ...)` 能正确恢复原字典项（context manager 退出即还原）
   → spike 已验证。
3. 移除 `@pytest.mark.anyio` 后 pytest 仍能收集同步 `def test_*` → 是。

## 5. 开放问题与结转

- 无阻塞项。第二个用例在 nose 下由"静默 no-op"转为"真正执行"，属行为修正，非断言变更。

## 验收标准
- 仓库根 `nosetests --with-doc test` → **426 passed、0 error**。
- `pytest test/test_auth_middle_asgi.py` → 2 passed（pytest 兼容不回归）。