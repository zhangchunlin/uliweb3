# Intent: 让规范命令 `nosetests --with-doc test` 全绿（修 pytest-only 的 auth 中间件测试）

---
类型: intent
状态: approved            <!-- draft → 提交给产品负责人审阅修正 -->
创建: 2026-10-14
---

- 作者: 张春林（框架组）
- 关联工单/事故: 上游 33d4b02（feat(asgi): 遵循 ASGI 规范同步认证用户至 scope['user']）引入

## 问题 （今天做不到什么 / 痛点）
- **规范命令 `nosetests --with-doc test` 不是全绿**：426 tests，1 error ——
  `test_auth_middle_asgi.test_auth_middle_syncs_user_to_scope` 报
  `TypeError: test_auth_middle_syncs_user_to_scope() missing 1 required positional argument: 'monkeypatch'`。
- 根因：上游新增的 `test/test_auth_middle_asgi.py` 是**纯 pytest 写法**——`@pytest.mark.anyio`、
  `async def` 测试、`monkeypatch` fixture。nose 1.3.7 不支持：
  - `monkeypatch` 是 pytest 专属 fixture，nose 不注入 → 该用例直接 error；
  - 同文件第二个 `async def` 测试（`test_call_next_propagates_scope_keys_on_success_and_error`）
    在 nose 下被静默丢弃（协程对象未 await，函数体从不执行）→ 实际是 no-op，未被真正测试。

## 期望结果 （更好的情况长什么样）
- 规范命令 `nosetests --with-doc test` 在仓库根执行 → **426 passed、0 error**。
- `test_auth_middle_asgi.py` 里的两条测试在 nose 下**真正执行**（不再静默跳过/报错）。
- 兼顾：转换后**不破坏 pytest**（`pytest test/test_auth_middle_asgi.py` 仍绿），两者都能跑。

## 受影响的用户与系统
- 测试：`test/test_auth_middle_asgi.py`（两个用例）。
- 被测：`uliweb/contrib/auth/middle_auth.py::AuthMiddle.dispatch`、
  `uliweb/core/SimpleFrame.py::_wrap_advanced_middleware`（scope key 传播）。
- 运行器：nose 1.3.7（权威）、pytest（兼容保留）。

## 约束
- **nose 是唯一权威验收入口**；改动必须让 `nosetests --with-doc test` 全绿。
- 不改产品运行时代码；只改测试文件本身。
- 不改断言语义：两条测试验证的行为（auth 同步 user 到 scope、scope key 在成功/异常路径传播）必须保留并被真正执行。
- 不引入对新第三方依赖的需求。

## 开放问题
- 第二个用例（`test_call_next_propagates_scope_keys_on_success_and_error`）当前在 nose 下静默 no-op，
  需确认它是否本就该跑——是，应转为真正执行（见 spec）。