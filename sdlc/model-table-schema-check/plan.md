# Plan：模型表名与 schema 一致性校验（model-table-schema-check）

---
类型: plan
来源: spec.md（approved）
状态: 待执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. feat(contrib/orm)：`uliweb orm tables` 命令**
      在 `uliweb/contrib/orm/subcommands.py` 新增 `OrmCommand(Command)`，`name='orm'`、`self.args='[tables|check]'`，按首参派发（命令系统为单层 `uliweb <name>`，故用 `name='orm'` + 子参数实现 `uliweb orm tables/check`）。
      `tables`：列出当前 engine 各 model → table 映射（遍历 `orm.__models__` / engine `_models`，含引擎名）。
      验证：`uliweb orm tables` 输出映射清单；未初始化/无 engine 给指引；`nosetests` 全绿。

- [ ] **2. feat(contrib/orm)：`uliweb orm check` 命令**
      用 SQLAlchemy `Inspector` 比对"模型期望的表/列" vs "DB 实际表/列"，输出差异清单（缺失表/列、多余列等）。
      验证：对已知不匹配场景输出差异；一致时无差异；`nosetests` 全绿。

- [ ] **3. feat(orm)：表名推导 info 日志（`INFO` 级，spec §5 定案）**
      模型绑定后，若类名按 `get_tablename`（~L244）推导的表名与显式 `__tablename__` 不同（下划线/驼峰被吞），打 `logger.info`。
      验证：类名推导 vs 显式 `__tablename__` 不同时 info 日志出现；相同时不报；`nosetests` 全绿。

- [ ] **4. docs(zh_CN)：命令用法 + 表名对齐最佳实践**
      补 `uliweb orm tables/check` 用法，及"模型表名与迁移脚本对齐"最佳实践。
      验证：渲染审阅文档完整。

- [ ] **5. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；改动落位。

## 验证命令
- `nosetests --with-doc test`（仓库根）
- `uliweb orm tables` / `uliweb orm check`（在测试 app 目录手验输出）

## 风险与缓解
- **最可能弄坏**：`OrmCommand` 干扰现有 `uliweb init/revision/diff/current/upgrade` → 缓解：独立 `name='orm'`，不影响既有命令注册。
- **最冒险一步**：第 3 步在模型绑定处打 info 日志 → 缓解：仅当推导表名与显式 `__tablename__` 不同才打 `INFO`（spec §5 定案），相同/无显式 `__tablename__` 不报。
- **放弃的做法**：不改 `get_tablename` 表名生成规则、不自动改库/迁移（spec §1/§4）；命令为新增能力，不影响运行期主路径。
