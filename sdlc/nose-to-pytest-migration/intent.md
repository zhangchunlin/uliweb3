# Intent: 把测试运行器从 nose 迁移到 pytest

---
类型: intent
状态: approved            <!-- draft → 提交给产品负责人审阅修正 -->
创建: 2026-10-14
---

- 作者: 张春林（框架组）
- 关联工单/事故: 无（长期技术债；由 auth 中间件测试暴露：nose 无法跑 async 测试）

## 问题 （今天做不到什么 / 痛点）
- **nose 已停止维护**（最后版本 1.3.7 发布于 2015 年），且**无法运行 `async def` 测试**。
- 框架正全面 ASGI 化，async 测试越来越多（如 `test_auth_middle_asgi.py`、`test_async_dispatcher.py`），
  鼻式必须改写/降级才能跑，长期不可持续。
- `pytest` 默认 `pytest test/` **非全绿**：421 passed + **5 errors**（`test_auth` 顺序污染）+
  `test_makeapp` 偶发失败（nose 风格 `setup/teardown` 被 pytest 忽略）。
- **doctest 现状存疑**：AGENTS.md/README 的权威命令 `nosetests --with-doc test` 中，`--with-doc` 并非 nose
  文档化的 doctest flag（真实的是 `--with-doctest`/`--doctest-tests`）；实测 `test_orm.py` 的 1546 个 `>>>`
  在带/不带 flag 下都是 83 项、不变化——说明这些 doctest **当前根本没有被真正运行**，只是 docstring。

## 期望结果 （更好的情况长什么样）
- **pytest 成为唯一权威验收入口**：仓库根 `pytest test/` 全绿（0 failed、0 error）。
- `async def` 测试原生可跑，不再需要鼻式降级/改写。
- doctest 策略明确：要么在 pytest 下真正启用并验证（`--doctest-modules` + 对齐收集集），要么明确不启用并移除误导性的 `--with-doc` 约定。
- 测试顺序隔离：任何子集/任何顺序 `pytest test/<file>` 都绿（消除 auth 顺序污染等）。
- nose 作为 legacy 入口保留至迁移完成，但不再作为验收闸门。

## 受影响的用户与系统
- 运行器：nose 1.3.7（现状权威）→ pytest（目标权威）。
- 测试文件：`test/test_auth.py`（顺序污染）、`test/test_manage.py`（setup/teardown 命名）、
  `test/test_async_dispatcher.py::test_sqlite_pool_args_filtered`（engine 状态泄漏）。
- 文档：`AGENTS.md`、`test/README.md`（命令与约定）。
- 配置：新增 pytest 配置（pytest.ini 或 setup.cfg `[tool:pytest]`）。

## 约束
- 不改变框架产品运行时行为（纯测试基建迁移）。
- 不删除/跳过任何测试断言；测试仍真实验证其声称的行为。
- 迁移后 `nosetests --with-doc test` 仍应尽量保持可跑（legacy 兜底），但不再是闸门。
- 遵守 AGENTS.md：测试失败改代码/测试装置、不改产品逻辑迎合测试。

## 开放问题
- doctest 是否要真正启用？（取决于 `>>>` 内容是否还有效、是否值得维护）——需在 spec 阶段核实并拍板。
- pytest 顺序污染（test_auth）用"修污染源 restore"还是"固定测试顺序/conftest 隔离"解决？
- pytest 是否纳入 CI 作为唯一 gate，nose 何时退役。