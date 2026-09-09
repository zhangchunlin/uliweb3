# Spec：清理 uliweb/core 设计缺陷（死代码/遮蔽/异常用错）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: intent.md
状态: 待审阅        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-09-08
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：`uliweb/core` 在 ASGI 迁移的覆盖式重构中留下同名遮蔽死代码、异常别名用错、werkzeug 残留死路径、dispatch 抛字符串、双套上下文残留，导致潜在 bug 与维护负担。
- **已证实的具体 bug**：
  - `get_settings`（L900 加载器）被 L3607（访问器）遮蔽 → `uliweb/contrib/secretkey/commands.py:19` 调用加载器会 TypeError。
  - `get_rule`（L723）调 `url_map.bind(...).match(return_rule=True)`，而 `UliwebRouter.bind()` 返回 Starlette `Router` 无 `match()` → `manage.py get_rule` 命令 AttributeError。
  - `raise BadRequest("msg")`（L601/603）把 message 当 `status_code` 传给 Starlette HTTPException → 状态码变字符串。
  - `dispatch.py` L159/251 `raise "..."` 抛字符串 → Python 3 TypeError。
- **验收标准**：
  - 每个模块/类内名称唯一；`get_settings(project_dir=...)` 加载器可正常调用（secretkey 命令工作）。
  - `get_rule` 在 ASGI 下可用（manage 命令不炸）。
  - `raise BadRequest(...)`/`error()` 状态码语义正确。
  - `nosetests --with-doc test`（仓库根）全绿。
  - `skills/uliweb-asgi-webapp/` 与 `docs/zh_CN/` 中与本意图改动相关的文档已同步。

## 2. 范围与边界

- 在范围内：`uliweb/core/SimpleFrame.py`、`uliweb/core/dispatch.py`、`uliweb/core/context.py`，及受影响的 `uliweb/contrib/secretkey/commands.py`、`test/test_url_for_static.py`。
- 在范围外：模板/ORM/contrib 业务功能；`_init_routes`/`_init_settings` 等 sync/async 双轨的大重构（仅当顺带才动）。
- 关联系统：`uliweb/manage.py`（get_rule）、`uliweb/contrib/staticfiles`（get_url_adapter）。

## 3. 设计

- **总体方案**：让实现回归 asgi-migration 已批准的设计（LocalProxy 单一上下文机制），删除遮蔽/废弃/werkzeug 残留，修正异常用法；对外契约（`@expose`、`url_for`、`error()`、`redirect`/`json`、`url_for`）行为不变。

- **3.1 同名遮蔽**：
  - `AsyncDispatcher._sort_middlewares`：删 L1914 那份，保留 L2555。
  - `redirect`（L515 死版，XHR 分支恒不成立）→ 删，保留 L3621 生效版（`RedirectResponse`）。
  - `json`（L560 死版）→ 删，保留 L3627 生效版。
  - `get_settings`：把 L900 加载器**改名**（如 `load_settings_config`）并更新调用方（secretkey/commands.py），或把 L3607 访问器并入 context；确保二者不再同名冲突。**注意：不把访问器改名，避免破坏 `from uliweb.core.SimpleFrame import get_settings` 的现有访问语义。**

- **3.2 异常别名/status_code**：
  - 移除 `BadRequest`/`InternalServerError`/`NotFound` 三个误导别名（或明确各指语义）；`jsonp` 处 `raise BadRequest("...")` → `raise StarletteHTTPException(status_code=400, detail="...")`。
  - 清理 L727 werkzeug 过期注释。
  - 核对 `HTTPError`/`error()` 状态码路径（asgi-migration 已修 `_error`/`_handle_exception`，此处仅确认无回归）。

- **3.3 werkzeug 残留**：
  - `get_rule`：改用 `UliwebRouter` 的 ASGI 匹配能力重写（或按现有路由遍历匹配），移除 `url_map.bind(...).match()`。
  - `get_url_adapter`：去掉返回 Starlette `Router`（无 `build`）的 fallback 分支，统一返回 `UliwebRouter`。

- **3.4 dispatch.py**：L159/251 `raise "..."` → `raise Exception(...)`；`anyio` 提到模块顶部 import。

- **3.5 context.py 瘦身**：删除 `_ContextProxy`/`request_var`/`response_var`/`settings_var`/`settings_proxy`/`request_proxy`/`response_proxy`/`application_proxy` 及 `get_request`/`get_response`/`get_settings`（废弃残留）；保留/合并 `get_application`（改复用 SimpleFrame 的）；更新 `test_url_for_static.py` 不再依赖 `application_var`。

## 4. 约束与策略落地

- 保持对外契约向后兼容；不 reintroduce werkzeug；不新增依赖。
- 上下文真相源 = SimpleFrame LocalProxy；contextvars→线程必须用 `copy_context().run()` 桥接（新增同步执行点沿用此规则）。
- 每个改动跑 `pytest test/` 无回归。

## 5. 开放问题与结转

- 来自 intent.md：上下文真相源 → 已定案（SimpleFrame LocalProxy）；并发桥接 → 已定案（copy_context 规则）。
- `redirect`/`json` 保留语义：暂按当前生效版（L3621/3627），若 XHR 分支版有真实使用者再评估。
- werkzeug 残留 `get_rule` 是否保留（manage 命令是否常用）：结转至实现阶段，若 `get_rule` 命令低频，可标注 deprecated。
