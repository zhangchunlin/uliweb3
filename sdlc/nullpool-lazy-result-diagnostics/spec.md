# Spec：NullPool 惰性 Result 跨查询诊断（nullpool-lazy-result-diagnostics）

---
类型: spec
来源: intent.md（draft）
状态: approved
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：SQLite + `NullPool` + async 下，惰性 `Result` 未迭代完又开新查询，外层游标报 `Cannot operate on a closed database.`，报错位置与根因无关。
- **范围取向**：只增强可诊断性，不改惰性/连接语义；诊断仅在 debug/警告级。
- **验收标准**：
  - Given 同一连接上惰性 `Result` 未迭代完，When 又发起新查询，Then 给明确警告：`A lazy Result on connection X is still open while a new query started; materialize with list() first.`
  - Given 连接被关闭，When 报 `closed database`，Then（debug）带上该连接最后一次 close 的调用栈。
  - 连接 `acquire/release/close` 在 debug 级记录调用栈；关闭时如有活动游标打高优先级日志。
  - 真库 + 真 async 运行时的复现场景被单测覆盖。
  - `nosetests --with-doc test` 全绿。

- **非目标**：不改惰性 `Result`/连接语义；不改 `all()` 返回 self 的行为；不拖慢性能主线。

## 2. 范围与边界

- 在范围内：`uliweb/orm/__init__.py` `Result` 层（~L2649，`all` ~L2738、`filter` ~L2789、`connection`）+ 连接/会话层（`get_session` ~L558）；单测（真库 + async）。
- 在范围外：改连接池/事务真实行为；非 debug 的性能开销路径。
- 关联系统：与 #4（`all()` 惰性语义文档化 / `.list()`）**同根因，本 feature 一并处理**；`sdlc/orm-lazy-init-diagnostics`（同为 ORM 可诊断性增强）。

## 3. 设计

- **总体方案**：两条诊断分落两层——**Result 层**检测"惰性未迭代完又开新查询"，**连接/会话层**追踪连接生命周期调用栈。

- **3.1 Result 层：惰性跨查询检测**
  - `Result` 记录自身"是否已完整迭代/物化"状态（如 `_consumed` 标志）。
  - 在发起新查询/`filter`/迭代入口，若同一连接上存在未消耗的 `Result`，打警告（debug/警告级）提示先 `list()` 物化。
  - 与 #4 合并：文档显著标注 `all()` 是惰性（返回 `self`）；可选新增 `.list()`/`.materialize()`（若定案）。

- **3.2 连接/会话层：生命周期调用栈追踪**
  - 在连接 `acquire/release/close`（debug 级）记录调用栈。
  - 关闭时若仍有活动游标，打带完整链路的高优先级日志。
  - 包装 `Cannot operate on a closed database.` 时（debug）附加最后一次 close 的调用栈。

## 4. 约束与策略落地

- 追踪仅在 debug/警告级，不拖累性能主线。
- 不改惰性/连接语义；向后兼容。
- 改动跑 `nosetests --with-doc test` 无回归；复现场景用真库 + async 覆盖。

## 5. 开放问题与结转

- **"已完整迭代完"如何判定（`_consumed`）** → **已定案：简单保守非破坏性方案**。仅在 `Result` 上维护一个 `_consumed` 标志（迭代到 `StopIteration` 时置 `True`），在发起新查询（`filter()` 等）入口做一次检查，命中时打 **debug/警告级日志**（纯日志，不改变任何行为）。不做复杂状态机。
- **是否新增 `.list()`/`.materialize()`** → **已定案：新增 `.list()`**（立即物化并返回真 list），配合文档减少 `all()` 惰性误用。
- 结转：连接栈追踪若影响性能，收敛为 debug 开关；NullPool 特定配置的深度兼容留待验证。
