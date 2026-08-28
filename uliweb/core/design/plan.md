# Plan: Uliweb ASGI 迁移实现计划

<!--
plan.md 由工程师在 plan mode 里基于已批准的 spec.md 生成；审阅满意后提交。
要求：一个从没看过这段对话的工程师也能仅凭计划实现。
实现偏离计划时，在同一个提交里更新 plan.md。
-->

---
类型: plan
来源: spec.md / intent.md
状态: approved
创建: 2026-08-28
审批: zhangchunlin
---

## 改动的文件

核心框架：
- `uliweb/core/SimpleFrame.py`（修改）：实现 `Request`、`Response`、`AsyncDispatcher`、`UliwebRouter`、`ASGIApplication` 及中间件栈构建、同步适配器、路由匹配。
- `uliweb/core/rules.py`（修改）：`expose` 装饰器、`_merge_rules()`、`GET/POST` 方法装饰器。
- `uliweb/core/context.py`（新增/修改）：基于 contextvars 的全局状态管理。
- `uliweb/utils/localproxy.py`（修改/复用）：`LocalProxy`、`Global`。
- `uliweb/__init__.py`（修改）：统一导出 Request、Response、expose、Middleware、ASGI_AVAILABLE 等。

组件与工具：
- `uliweb/core/dispatch.py`（修改）：事件分发 `acall` 异步化。
- `uliweb/core/template.py`（修改）：`AsyncTemplateLoader.load_async` / `generate_async`。
- `uliweb/mail`、`uliweb/contrib/*`（按需修改）：session / auth / cache 等异步适配。

配置与文档：
- `settings.ini`（项目级）：新增 `[MIDDLEWARES]`、`[ASGI]` 配置示例。
- 本文档系列（intent / spec / plan）：作为迁移指南与审计轨迹。

## 工作顺序

1. **基础架构**：迁移 Request/Response（修复 async property 陷阱），实现 `AsyncDispatcher` 的 ASGI 3.0 接口与同步适配器（`anyio.to_thread.run_sync`），接入基本路由 `UliwebRouter`。
2. **全局状态**：引入 `LocalProxy`（contextvars / 普通全局），实现 `request_var` 上下文管理，接通 settings/application。
3. **中间件**：重设计 `Middleware` 基类（高级 `dispatch` + 底层 `__call__`），实现 `_build_middleware_stack` 链式调用，兼容传统 `process_*` 接口。
4. **路由与 URL 生成**：完成 `<type:name>` → `{name}` 转换、`_merge_rules`、`url_for` 反向 URL。
5. **周边组件异步化**：模板、事件分发、命令、HTML/UAML、JSON 工具。
6. **Settings 与 ASGI 处理程序**：`ASGIApplication` 单例，`make_application` 便捷入口。
7. **验证与清理**：移除 werkzeug 依赖，跑通检查清单与测试。

## 风险与缓解

- 最可能弄坏什么：现有同步视图函数在适配器下的行为（POST 等同步属性访问会抛异常）→ 通过请求数据预加载 + 明确弃用提示缓解，并保留同步属性抛异常作为引导。
- 哪一步最冒险：中间件系统从 WSGI 迁移到纯 ASGI，接口差异大 → 提供高级/底层两套接口并支持混合，兼容传统 `process_*` 接口。
- 放弃了的其他做法及原因：新建独立 `starlette.py` 文件 → 放弃，统一集中于 `SimpleFrame.py` 以降低复杂度；使用 contextvars 直接代理而非 LocalProxy → 放弃，采用 LocalProxy 保持与 WSGI 一致的统一接口。

## 证明（如何证明它工作）

- 测试：
  - `python -c "from uliweb import Request, Response, Middleware, expose; ..."` 验证核心导出。
  - `python -c "from uliweb.core.SimpleFrame import AsyncDispatcher; print(AsyncDispatcher)"` 验证 ASGI 分发器。
  - 单元/集成/兼容性/WebSocket/性能/压力测试全部通过（见检查清单）。
- 验证结果快照：
  - `Request: starlette.requests.Request`、`Response: starlette.responses.Response`、`Middleware: uliweb.Middleware`、`ASGI_AVAILABLE: True`、`AsyncDispatcher: available`。
- 部署证明：使用 Uvicorn / Hypercorn / Daphne 成功启动应用；`setup.cfg` 中已无 werkzeug 依赖。
