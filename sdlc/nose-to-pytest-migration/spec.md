# Spec: 把测试运行器从 nose 迁移到 pytest

---
类型: spec
状态: 已实现        <!-- 审阅通过后 → approved，触发 plan mode；实现完成 → 已实现 -->
创建: 2026-10-14
---

## 1. 背景与目标

nose 停更且无法跑 async 测试，与框架 ASGI 化冲突。目标：pytest 成为唯一权威验收入口，
`pytest test/` 全绿；async 原生可跑；doctest 策略明确；测试顺序隔离。

**基线（已实测）**：
| 命令 | 结果 |
|---|---|
| `nosetests --with-doc test`（现状权威） | 426 OK（但 doctest 实际未运行，见 §2） |
| `pytest test/`（现状） | 438 收集；421 passed + 5 errors（auth 顺序）+ test_makeapp 偶发 |
| `pytest --doctest-modules test/` | 605 收集（与鼻式 426 差异大） |

## 2. 关键事实（调查结论）

1. **doctest 当前未真正运行**：`--with-doc` 不是 nose 文档化 doctest flag（真实是 `--with-doctest`）；
   `test_orm.py` 1546 个 `>>>` 在带/不带 flag 下收集数不变（83），说明这些 doctest 只是 docstring，
   **从未作为 doctest 用例执行**。→ 迁移不涉及"搬运 1500 活 doctest"，风险低。
2. **pytest 顺序污染（5 errors）**：`test_async_dispatcher.py::TestViewsImport::test_sqlite_pool_args_filtered`
   调 `get_connection('sqlite:///:memory:')` → `engine_manager.add('default', ...)` 整体替换
   test_auth 在 import 期绑定了 user 模型的全局 default engine 且不恢复 → test_auth 的
   `get_model('user')` 报 ModelNotFound。pytest 收集顺序把 async_dispatcher 排在 auth 前触发。
3. **test_makeapp 命名**：`test_manage.py` 用 nose 风格 `setup/teardown`，pytest 只认
   `setup_method/teardown_method` → 残留 `maketest/` 从不清理。

## 3. 总体方案

### 3.1 修 pytest 顺序污染（test_auth 5 error）
在 `test_sqlite_pool_args_filtered` 内快照并恢复 `engine_manager['default']`
（`old = engine_manager.engines.get('default')` → 断言后 `engines['default'] = old`）。
根除"测试改全局 ORM engine 状态"的泄漏。

### 3.2 修 test_makeapp
`test_manage.py` 的 `setup`/`teardown` → `setup_method`/`teardown_method`（nose/pytest 双兼容）。

### 3.3 新增 pytest 配置
新增 `pytest.ini`（独立于打包用的 setup.cfg，避免混用 `[tool:pytest]` 与 `[metadata]/[options]`）：
```ini
[pytest]
testpaths = test
addopts = --doctest-modules
```
- `--doctest-modules` 启用 doctest（实测 ~167 doctest 全部通过，见 §1 基线；仓库无 .txt doctest 文件，无需 `--doctest-glob`）。

### 3.4 doctest 策略（已定：保留/启用）
- **采用方案 B：真正启用 doctest**，成本低（实测 `pytest --doctest-modules test/` = 588 passed，其中 ~167 个 doctest 全过、0 失败）。
- 理由：doctest 内容当前有效且可跑通过，保留即"少改动"（用户倾向）；仅需 `--doctest-modules` 配置项，无需逐文件改写。
- 不做的事：不迁移/改写任何 doctest 内容；不启用 `--doctest-glob`（无 .txt doctest）。

### 3.5 文档与闸门
- `AGENTS.md`：`Test` 命令改为 `pytest test/`（唯一权威），移除 `nosetests --with-doc test` 及误导性的 `--with-doc`。
- `test/README.md`：Nose 改注为 legacy/可选；命令统一 `pytest test/`；清理 doctest 命令示例。
- `sdlc/*.md` 历史工件**不回改**（审计轨迹），仅本次迁移自身新增的 3 份工件反映新约定。
- 全仓 `grep` 复查存续文档无 `nosetests`/`--with-doc` 残留。
- CI（如有）：gate 改为 `pytest test/`。

## 4. 顾虑点
1. pytest 收集 438 > nose 426：多出的项需确认（可能是 pytest 收集了鼻式忽略的、或 doctest 模块），
   需在 plan 阶段 diff 两份用例集，确保无意外多跑/少跑。
2. `asyncio.run` 与 pytest 的 event loop：pytest 有 anyio/asyncio 插件，同步 `def` + `asyncio.run` 与
   原生 async 测试并存，需统一风格避免混乱。
3. `test_manage.py` 依赖相对路径/`maketest` 落盘，pytest 与 nose 对 cwd 处理不同，需固定执行目录。

## 5. 开放问题与结转
- doctest → **已定方案 B（保留/启用）**，成本低（实测全过）。
- nose 何时完全退役 → 本 feature 只做"pytest 权威化"，nose 保留 legacy 兼容，不在本 scope 删除。
- CI gate 迁移是否纳入本 feature → 视仓库是否有 CI 配置而定。

## 验收标准
- 仓库根 `pytest test/` → **0 failed、0 error**（全绿）。
- `pytest test/test_async_dispatcher.py::TestViewsImport::test_sqlite_pool_args_filtered test/test_auth.py` → 全绿（顺序依赖消除）。
- 任意子集 `pytest test/<file>` 独立绿。
- `AGENTS.md`/`test/README.md` 命令已更新为 `pytest test/`。