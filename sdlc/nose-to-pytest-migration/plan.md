# Plan: 把测试运行器从 nose 迁移到 pytest

---
类型: plan
状态: 已实现          <!-- 审阅通过后 → approved，进入实现；实现完成 → 已实现 -->
创建: 2026-10-14
---

## 背景（根因，已核实）

- nose 停更、无法跑 async 测试；pytest 现状 `pytest test/` = 421 passed + 5 errors（auth 顺序污染）
  + test_makeapp 偶发（命名）。
- 5 errors：`test_async_dispatcher.py::TestViewsImport::test_sqlite_pool_args_filtered` 调
  `get_connection('sqlite:///:memory:')` → `engine_manager.add('default', ...)` 整体替换
  test_auth 的全局 default engine（绑定了 user 模型）且不恢复。
- test_makeapp：`test_manage.py` 用 nose 风格 `setup/teardown`，pytest 只认 `setup_method`。
- doctest：`--with-doc` 非真实 doctest flag，`>>>` 当前未真正运行 → 迁移不涉及搬运 1500 doctest。

## 改动的文件

- `test/test_async_dispatcher.py`（修改，`test_sqlite_pool_args_filtered`）：
  `get_connection` 前存 `old = engine_manager.engines.get('default')`，断言后 `engines['default'] = old`。
- `test/test_manage.py`（修改）：`setup`→`setup_method`、`teardown`→`teardown_method`。
- 新增 `pytest.ini`（或 setup.cfg `[tool:pytest]`）：`testpaths=test`、doctest 策略（依拍板 A/B）。
- `AGENTS.md`、`test/README.md`（修改）：命令改为 `pytest test/`。

## 工作顺序

1. **修 pytest 顺序污染**：`test_sqlite_pool_args_filtered` 保存/恢复 `engine_manager['default']`。
2. **修 test_makeapp**：`test_manage.py` 改名 `setup_method/teardown_method`。
3. **pytest 配置**：新增 `pytest.ini`（推荐，独立于打包的 setup.cfg）：
   ```ini
   [pytest]
   testpaths = test
   addopts = --doctest-modules
   ```
   - `--doctest-modules` 启用 doctest（实测 ~167 doctest 全过，无需 `--doctest-glob`，仓库无 .txt doctest 文件）。
   - 不并入 setup.cfg 的 `[tool:pytest]`，避免与 `[metadata]/[options]` 打包配置混在同一文件、降低误改打包字段风险。
   - 若团队偏好 setup.cfg，也可放 `[tool:pytest]`，但需评估 `addopts` 是否影响其它打包命令。
4. **diff 用例集**：对比 `pytest test/`（438）与鼻式（426）收集集，确认多出的 12 项是什么，
   确保无意外多跑/少跑。
5. **文档更新（所有存续/权威文档）**：
   - `AGENTS.md`：`Test` 命令改为 `pytest test/`（唯一权威），移除 `nosetests --with-doc test` / `--with-doc` 误导性描述。
   - `test/README.md`：`Option 1 (Nose)` 改注为 legacy/可选；命令统一为 `pytest test/`；清理 `--with-doc`/`--with-doctest` 示例。
   - **不回改** `sdlc/*.md` 历史工件（它们是各 feature 当时的审计轨迹，保持原样）。
   - 全仓 `grep -rn "nosetests\|--with-doc\|--with-doctest"` 复查确认无残留存续文档引用。
6. **全量回归**：`pytest test/` → 0 failed / 0 error；`nosetests --with-doc test` 仍 OK（legacy 兜底）。

## 风险与缓解

- 顺序污染若 restore 不彻底（engine 对象被其它测试引用）→ 缓解：spike 验证 restore 引用还原可行；
  兜底升级为 conftest 级 `engine_manager`+`__models__` 快照（spec §3.1 备选）。
- 用例集 diff 出现 pytest 多收集的"脏"测试 → 缓解：plan 步骤 4 定位并决定 skip/修正。
- `asyncio.run` 与 pytest 原生 async 混用 → 缓解：统一"同步 def 内 asyncio.run"或"原生 async"任一风格，避免混乱。

## 证明（如何证明它工作）

- `pytest test/` → **0 failed、0 error**（修复前 5 errors + 偶发）。
- 顺序依赖消除：`pytest test/test_async_dispatcher.py::TestViewsImport::test_sqlite_pool_args_filtered test/test_auth.py` → 全绿。
- 任意子集独立绿：抽查 `pytest test/test_auth.py`、`pytest test/test_manage.py` 单跑绿。
- legacy 兜底：`nosetests --with-doc test` → OK。