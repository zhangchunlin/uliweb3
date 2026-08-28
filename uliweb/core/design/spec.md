# Spec：Uliweb ASGI 迁移（需求与设计规格）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。生成提示词见文件末尾。
-->

---
类型: spec
来源: intent.md
状态: 待审阅        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-08-28
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：Uliweb 需从基于 Werkzeug 的 WSGI 架构迁移到基于 Starlette 的 ASGI 架构，以获得异步处理、WebSocket、更高并发与现代生态；同时保证现有同步代码平滑过渡、外部接口向后兼容。
- **用户故事 / 验收标准**：
  - 给定一个现有 Uliweb 项目，其 `@expose` 视图函数无需改写即可运行，且框架自动将其适配为异步执行。
  - 给定一个新视图函数以 `async def` 编写，其可通过 `await request.get_POST()` / `get_FILES()` / `get_json()` 读取请求数据。
  - 给定一个 `/ws` WebSocket 端点，其可完成原生双向实时通信。
  - 给定 `settings.ini` 中的 `MIDDLEWARES` 配置，传统 `process_request/process_response/process_exception` 与 ASGI 中间件均可生效。
  - 应用可通过 Uvicorn / Hypercorn / Daphne 运行，且不再依赖 werkzeug。
- **非目标**（明确不做，防范围蔓延）：不做跨框架（FastAPI/Django）适配；不做 UAML/taglib 等已移除特性的回填；不为旧 WSGI 保留运行时兼容层。

## 2. 范围与边界

- 在范围内：核心组件（Request/Response、Dispatcher、路由、全局状态）、中间件、模板、事件分发、命令、HTML/UAML、JSON 工具、Settings 配置的 ASGI 迁移与同步适配。
- 在范围外：新增业务功能、数据库驱动异步化（保持同步驱动经协程池兼容）、第三方异步生态集成。
- 关联系统：`uliweb/core/SimpleFrame.py` 为核心承载；`uliweb/core/rules.py`、`uliweb/core/context.py`、`uliweb/utils/localproxy.py`、`uliweb/__init__.py` 为接口面。

## 3. 设计

### 3.1 总体方案

以"渐进式兼容 + 同步适配器"为核心：用 Starlette 的 Request/Response/路由作为基座，在 `uliweb/core/SimpleFrame.py` 中扩展出 `Request`、`AsyncDispatcher`、`UliwebRouter`、`ASGIApplication` 等组件；通过 `anyio.to_thread.run_sync` 将同步函数放入线程池执行，实现"外部异步、内部同步"的平滑过渡。

### 3.2 架构对比

| 组件 | 原有 WSGI（Werkzeug） | 目标 ASGI（Starlette） |
|------|-----------|-----------|
| Request/Response | 继承 `werkzeug.Request/Response` | 继承 `starlette.requests.Request` 等 |
| URL 路由 | `werkzeug.routing.Map/Rule` | Starlette `Router/Route`（Werkzeug 风格转 Starlette 风格） |
| 应用 | `Dispatcher.__call__(environ, start_response)` | `AsyncDispatcher.__call__(scope, receive, send)` |
| 中间件 | WSGI 中间件链 | 纯 ASGI 中间件（高级 `dispatch` + 底层 `__call__`） |
| 全局状态 | `werkzeug.local.Local`（threading.local） | `LocalProxy`（contextvars / 普通全局） |

### 3.3 迁移阶段

1. **阶段一 基础架构**：Request/Response、ASGI 接口（含同步适配器）、基本路由。
2. **阶段二 功能完整性**：中间件、模板、会话异步化。
3. **阶段三 性能优化**：WebSocket、异步数据库/缓存适配。
4. **阶段四 生态兼容**：插件适配、文档、统一导出接口。
5. **阶段五 完全移除 WSGI**：移除 werkzeug 依赖。

### 3.4 组件设计要点

#### Request/Response
- 继承 Starlette，修复 async property 陷阱：将 `POST/FILES/json/data` 改为明确的异步方法 `get_POST()/get_FILES()/get_json()/get_data()`，`params` 改为 `get_params()`。
- 保留同步属性但抛 `RuntimeError` 引导迁移；新增 `request.state` 请求级状态容器。
- 迁移对照：`request.data → await request.get_data()`、`request.POST → await request.get_POST()` 等。

#### Dispatcher（AsyncDispatcher）
- 实现 ASGI 3.0 `__call__(scope, receive, send)`，按 scope type 分派 `handle_http` / `handle_websocket`。
- 同步函数通过 `anyio.to_thread.run_sync` 在线程池执行，避免阻塞事件循环。
- 请求上下文用 `request_var.set/reset` 管理。

#### URL 路由（UliwebRouter）
- 将 Werkzeug 风格 `<type:name>` 转换为 Starlette 风格 `{name}`，并提取参数类型。
- `url_for` 支持 endpoint 生成 URL、域名、外部链接、格式化、应用别名映射。

#### 全局状态（LocalProxy）
- 统一接口，`use_contextvars` 控制存储方式：request/response 用 contextvars（每协程独立），settings/application 用普通全局（全局一致）。
- 未初始化访问时抛 `RuntimeError` 提示初始化。

#### 中间件
- 提供高级接口（`async def dispatch(self, request, call_next)`）与底层 ASGI 接口（`async def __call__(self, scope, receive, send)`）。
- `_build_middleware_stack` 从内到外包装形成调用链，支持两种接口混合。
- 兼容现有 `process_request/process_response/process_exception`，经协程池异步执行。

#### 其他组件
- 模板：`AsyncTemplateLoader.load_async` + `generate_async`。
- 事件分发：`acall` 异步调用，协程函数直接 `await`，否则线程池。
- 命令：`AsyncCommand.handle_async` + 同步适配器。
- HTML/UAML、JSON：`anyio.to_thread.run_sync` 封装异步版本。
- Settings：保持同步加载，经 `asyncio.run_in_executor` 异步化；提供更精确的路由匹配。

## 4. 约束与策略落地

- 品牌 / 安全 / 合规 / UX 约束：
  - 兼容性优先：`@expose`、`settings.ini`、传统中间件接口、`url_for` 等对外契约保持不变。
  - 实现集中：所有 ASGI 相关实现位于 `uliweb/core/SimpleFrame.py`。
  - 安全：静态文件服务内置路径遍历防护、隐藏文件访问控制；中间件保留 `request.state` 协作模式。
- 需要在工程介入前解决掉的顾虑点：
  - async property 陷阱 → 已定案：改用明确异步方法 + 弃用同步属性抛异常。
  - 同步/异步混合的数据访问 → 已定案：请求数据预加载 + 同步适配器。
  - 中间件 WSGI→ASGI 接口差异 → 已定案：统一为纯 ASGI 中间件接口。

## 5. 开放问题与结转

- 来自 intent.md 的开放问题：
  - 线程池容量与线程安全 → 计划阶段通过配置项（`SYNC_THREAD_POOL_SIZE`）与最佳实践解决。
  - 请求数据预加载的开销 → 计划阶段以 `PRELOAD_REQUEST_DATA` 开关控制。
  - contrib 异步化排期 → 结转至后续维护阶段，按优先级逐个迁移。

---

### 附：生成本 spec 的提示词（供固化）

```
请阅读附件 intent.md，为把它整合进我们现有代码库产出"需求与设计 spec"。
应用你手头可用的 skills，使计划符合我们的品牌规范、安全策略与 UX 标准。
把 spec 完整写成 spec.md，准备交给工程团队。请清晰描述任何顾虑点，
特别是你无法同时满足相互矛盾策略的地方。
```
