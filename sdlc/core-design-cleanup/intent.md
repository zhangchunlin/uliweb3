# Intent: 清理 uliweb/core 中的设计缺陷（死代码/遮蔽/异常用错）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 sdlc/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: draft            <!-- draft → 审阅通过 → approved -->
创建: 2026-09-08
---

- 作者: zhangchunlin
- 关联工单/事故: uliweb/core 设计评审

## 问题 （今天做不到什么 / 痛点）
- `uliweb/core/SimpleFrame.py` 在 ASGI 迁移的"覆盖式重构"中留下多处**同名定义互相遮蔽**：后定义覆盖前定义，前面的成为死代码，且行为/签名不一致，极易踩坑。
  - `redirect`（L515 vs L3621）、`json`（L560 vs L3627）行为不同；`get_settings`（L900 vs L3607）**签名不同**，同名覆盖会让"加载 settings"调用炸掉；`AsyncDispatcher._sort_middlewares`（L1914 vs L2555）完全重复。
- **异常别名用错**：`BadRequest`/`InternalServerError`/`NotFound` 三名字都指向同一个 `starlette.exceptions.HTTPException`（L22-24），无法用类型区分 400/404/500；且 `raise BadRequest("msg")`（L601、L603）把 message 当 status_code 传入，状态码变字符串，属潜在 bug。
- **werkzeug 迁移死代码**：`get_rule`（L723）调 `url_map.bind(...).match(return_rule=True)`，而 `url_map` 现为 `UliwebRouter`，其 `bind()` 返回 Starlette `Router` 无 `match()` → AttributeError；`get_url_adapter`（L675）fallback 分支同样拿不到 `build()`。
- `dispatch.py`：L159、L251 `raise "..."` 抛字符串，Python 3 下触发 `TypeError`；`acall`/`aget` 循环体内 `import anyio`。
- context.py 与 SimpleFrame 存在**两套并存的上下文机制**（`_ContextProxy`/`ContextVar` vs `LocalProxy`），职责重叠、互相引用，易混淆。

## 期望结果 （更好的情况长什么样）
- 消除同名遮蔽：每个模块/类中名称唯一，删除被覆盖的死代码，保留语义正确的那份。
- 异常体系可区分 400/404/500；`error()`/`HTTPError` 状态码语义正确，不再把 message 当 status_code。
- 移除 werkzeug 残留死路径（`get_rule`/`get_url_adapter` fallback），ASGI 路径为主。
- dispatch.py 抛异常用 `raise Exception(...)`；`anyio` 提到模块顶部。
- 明确单一上下文机制，消除双套代理。

## 受影响的用户与系统
- 依赖 `uliweb.core.SimpleFrame` 内部 API 的框架代码与 contrib。
- 相关文件：`uliweb/core/SimpleFrame.py`、`uliweb/core/dispatch.py`、`uliweb/core/context.py`。

## 约束
- 保持对外契约向后兼容：`@expose`、`url_for`、`error()`、`redirect`/`json` 的行为不变。
- 不引入新依赖；继续不 reintroduce werkzeug。
- 改动需跑通 `nosetests --with-doc test` / `pytest test/`。

## 开放问题

- **上下文机制以哪套为真相源** → 已定案：**SimpleFrame 的 LocalProxy**。与 asgi-migration/spec.md §3.7 设计一致，且 plan.md 明确放弃「contextvars 直接代理」（即 context.py 的 `_ContextProxy`/raw `request_var` 残留）。context.py 的 `_ContextProxy`/`request_var`/`response_var`/`settings_var`/proxies 为废弃方案残留，应删；`get_application` 与 SimpleFrame 重复，改直接复用 SimpleFrame 的。
- **contextvars 在 ASGI 协程并发下是否可用** → 已验证可完全满足：请求级隔离靠 per-Task Context；线程桥接统一用 `copy_context().run()`（视图适配器 L2878+、WebSocket L1809/1814、中间件 L3399）。需约定：**任何新增同步执行点必须继续用 `copy_context().run()` 桥接**，否则线程内读 `request`/`response` 代理会得 None。
- **redirect/json 以哪份语义为准** → 待实现阶段结合调用方确认（XHR 分支版 vs 简化版），暂定保留对外导出行为，删除被遮蔽的死代码。
- **修复优先级与拆提交粒度** → 按「一个目的一个提交」拆分：死代码遮蔽、异常用错、werkzeug 残留、dispatch 字符串 raise、context.py 瘦身。
