# 评审：一个 endpoint 可映射多个 URL（exposes-multi-url）

<!--
REVIEW.md 作为本意图工件链的 Deploy 阶段工件（前序：intent.md → spec.md → plan.md → 实施提交）。
记录本次评审结论（审计轨迹），并作为后续 AI 进评审环的评审策略。
前序工件见同目录 intent.md / spec.md / plan.md。
-->

---
类型: review
来源: plan.md（实施提交历史）
状态: approved
创建: 2026-09-08
评审: zhangchunlin（技术负责人）
---

## Passes（评审跑哪些 pass）

- **Bugs**：逻辑错误、坏掉的边界情况、细微回归
- **Security**：注入风险、认证缺口、日志里的 PII、路径遍历
- **Compliance**：改动符合 spec.md / plan.md 与设计原则（一个目的一个提交、不 reintroduce werkzeug、对外契约 EXPOSES 配置格式不变、sync/async 双轨只动 async）

## 评审对象（build 产物）

- 实施提交已合入 `asgi` 分支，共 3 个提交：
  - `c7637ee` docs(intent): exposes-multi-url intent 定案 + 生成 spec 与 plan
  - `f44724b` fix(SimpleFrame): `_init_routes` EXPOSES 改 URL 级去重/覆盖，一个 endpoint 可映射多个 URL + 单测
  - 本 REVIEW 提交
- 验收门槛（plan.md §终检）：`nosetests --with-doc test` 通过（**324 passed，OK**）。
- 覆盖：`_init_routes` 的 `registered_routes` 由 endpoint 级改为 path 级；新增局部闭包 `_register`（同 path 先移除旧路由再 add，实现「同 URL 后者覆盖 / 去重」）；merge 循环 + 4 处 EXPOSES 块（应用级 list/str、全局 list/str）全部改走 `_register`；删除 endpoint 级覆盖逻辑。

## 评审结论

| 维度 | 结论 | 备注 |
|------|------|------|
| **Bugs** | 通过 | 三场景验证 + 单测：同 endpoint 多 URL 共存（`/test` 与 `/`）；同 URL 不同 endpoint 后者覆盖（1 条、endpoint=b）；同 URL 同 endpoint 去重（1 条） |
| **Security** | 通过 | 无新增注入/路径面；EXPOSES 配置格式不变 |
| **Compliance** | 通过 | 一个目的一个提交；仅动 async `_init_routes`（sync 路径无 EXPOSES 覆盖逻辑，无需改）；EXPOSES 对外契约不变；应用级 str 分支保留 `url_map` 更新 |
| 测试 | 通过 | 验收命令全绿，新增 3 条 EXPOSES 单测 |

**审批决定：approve**。未发现 Important 级问题。

## 待跟进（结转至 Maintain 阶段，非阻塞）

1. `_init_routes_sync` 仍无 EXPOSES 处理（简化测试路径）：若将来 sync 路径需支持 EXPOSES 多 URL 语义，需另行补齐并与本 async 实现对齐。
2. `registered_routes` 现为 path→path 字典：未来若同一 starlette path 需区分不同 methods 的独立路由，去重粒度（当前按 path）需再评估。
