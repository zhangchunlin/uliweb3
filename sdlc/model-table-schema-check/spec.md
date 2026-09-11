# Spec：模型表名与 schema 一致性校验（model-table-schema-check）

---
类型: spec
来源: intent.md（draft，形态/位置已定案）
状态: approved
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：模型未设 `__tablename__` 时默认表名（`get_tablename` 转小写，吞驼峰/下划线）与迁移脚本命名不一致，导致 `no such table` 运行期才暴露，且测试因 mock 未发现。
- **范围取向（已定案）**：**命令行工具** + **放 `uliweb/contrib/orm`**；不改表名生成规则。
- **验收标准**：
  - Given 命令行工具，When 运行"列出映射"，Then 输出当前 engine 的 `model → table` 映射清单。
  - Given 命令行工具，When 运行"schema 校验"，Then 比对模型期望表/列 vs DB 实际表/列，输出差异清单。
  - Given 模型绑定后表名由类名推导、且与显式 `__tablename__` 明显不同（下划线/驼峰被吞），Then 打一条 info 日志。
  - `nosetests --with-doc test` 全绿。

- **非目标**：不改表名生成规则；不自动改库/迁移；不影响运行期主路径。

## 2. 范围与边界

- 在范围内：`uliweb/contrib/orm` 新增命令行工具（`uliweb ...`）；`get_tablename`/`Model` 表名推导的 info 日志；命令文档。
- 在范围外：改 `get_tablename` 规则；自动迁移/改表。
- 关联系统：`sdlc/nullpool-lazy-result-diagnostics`、`sdlc/orm-lazy-init-diagnostics`（同为 ORM 侧可诊断性增强）。

## 3. 设计

- **总体方案**：提供 `uliweb/contrib/orm` 下的命令行工具，把"模型 vs DB"对齐问题从运行期暴露提前到命令可查。

- **3.1 命令行工具（`uliweb/contrib/orm`）**
  - 新增子命令，如：
    - `uliweb orm tables`：列出当前 engine 各 model → table 映射（基于 `__models__`/engine `_models`）。
    - `uliweb orm check`：用 SQLAlchemy `Inspector` 比对"模型期望的表/列" vs "DB 实际表/列"，输出差异清单。
  - 命令基于已初始化 app/engine 运行（复用 `manage`/app 加载）。

- **3.2 表名推导 info 日志**
  - 模型绑定后，若"类名按 `get_tablename` 推导的表名"与"显式 `__tablename__`"不同（含下划线/驼峰被吞情形），打一条 `logger.info`（或 warning，见开放问题），便于及早发现命名漂移。

- **3.3 文档**
  - 在 `docs/zh_CN` 命令/ORM 章节补充 `uliweb orm tables/check` 用法与"表名对齐"最佳实践。

## 4. 约束与策略落地

- 不改表名生成规则，向后兼容（已有表不破坏）。
- 工具为新增能力，不影响运行期主路径。
- 改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- 待定：schema 校验子命令名 → **已定案：`uliweb orm check`**（`uliweb orm tables` 亦已定案）。
- 待定：表名推导日志级别 → **已定案：`INFO`**。
- 结转：校验差异的"可操作输出"（是否给建议修法）留待实现时细化。
