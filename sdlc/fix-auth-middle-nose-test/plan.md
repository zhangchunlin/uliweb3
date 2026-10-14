# Plan: 把 pytest-only 的 auth 中间件测试转为 nose 可执行

---
类型: plan
状态: 已实现          <!-- 审阅通过后 → approved，进入实现；实现完成 → 已实现 -->
创建: 2026-10-14
---

## 背景（根因，已核实）

`nosetests --with-doc test`（权威入口）426 tests / 1 error，唯一失败来自上游 33d4b02 新增的
`test/test_auth_middle_asgi.py`：`@pytest.mark.anyio` + `async def` + `monkeypatch` 均为 pytest 专属，
nose 1.3.7 不注入 `monkeypatch`（→ error），且不执行 `async def`（→ 第二个用例静默 no-op）。
spike 已验证：`patch.dict(functions._Finder__objects, ...)` + `asyncio.run()` 在同步测试中可完整跑通
`AuthMiddle.dispatch`。

## 改动的文件

- `test/test_auth_middle_asgi.py`（修改，仅此一个）：
  - 移除 `import pytest` 与 `@pytest.mark.anyio`。
  - `test_auth_middle_syncs_user_to_scope` → 同步 `def`，内部 `async def _run()` + `asyncio.run(_run())`；
    `monkeypatch.setitem(...)` → `patch.dict(functions._Finder__objects, {...})`。
  - `test_call_next_propagates_scope_keys_on_success_and_error` → 同步 `def` + `asyncio.run(...)`；
    `pytest.raises(RuntimeError)` → `try/except RuntimeError`。
  - 保留全部断言与 MockUser/MockRequest。

## 工作顺序

1. 重写 `test/test_auth_middle_asgi.py`（按 spec §3）。
2. **权威验证**：`nosetests --with-doc test` 全量 → 426 passed、0 error。
3. **pytest 兼容**：`pytest test/test_auth_middle_asgi.py` → 2 passed。
4. 确认无残留工件、工作区干净。

## 风险与缓解

- `asyncio.run` 在 3.8–3.13 可用（AGENTS.md 支持范围）→ 无风险。
- `patch.dict` 还原原字典项，spike 已验证 → 无风险。
- 移除 pytest 装饰器不影响 nose 收集同步 `def test_*` → 无风险。

## 证明（如何证明它工作）

- **权威**：`nosetests --with-doc test` → **426 passed、0 error**（修复前 1 error）。
- **兼容**：`pytest test/test_auth_middle_asgi.py` → 2 passed。
- **真正执行**：nose 下两个用例都真实运行（不再静默 no-op / error）。