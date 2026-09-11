# Intent: 模型表名与 schema 一致性校验（model-table-schema-check）

---
类型: intent
状态: draft
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: agent-gateway 排障（uliweb-framework-improvement-proposals.md #3）

## 问题

- 模型未设 `__tablename__` 时框架默认 `get_tablename` 把类名转小写（吞驼峰/下划线），如 `UserExt` → `userext`；而迁移脚本建的是 `user_ext`。结果 ORM 查询报 `no such table: userext`，且功能在真库上从未生效、测试因 mock 未发现。

## 期望结果

- 提供官方**命令行工具**列出当前 engine 的 `model → table` 映射，便于迁移脚本与模型对齐。
- 提供 schema 一致性校验**命令行工具**：比对"模型期望的表/列" vs "DB 实际表/列"，输出差异清单（通用能力，替代 agent-gateway 自研 `migrate_db.py --check`）。
- 模型绑定后，若类名推导表名与显式 `__tablename__` 明显不同（含下划线/驼峰被吞），打一条 info 日志便于发现。

## 受影响的用户与系统

- 所有使用 ORM + 迁移脚本的用户。
- 相关文件：`uliweb/orm/__init__.py`（`get_tablename` ~L244、`Model`）、`uliweb/contrib/orm`、迁移工具链。

## 约束

- 不改变现有表名生成规则（向后兼容，已有表不破坏）。
- 校验/映射工具作为新增能力，不影响运行期主路径。

## 开放问题

- **形态** → **已定案：命令行工具**（`uliweb ...` 命令），不作为运行期主路径能力。
- **位置** → **已定案：`uliweb/contrib/orm`**。
- 待定：命令具体命名 / 子命令划分（如 `uliweb orm tables`、`uliweb orm check`）。
