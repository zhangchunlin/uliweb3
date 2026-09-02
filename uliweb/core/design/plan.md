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
- `uliweb/core/SimpleFrame.py`（修改）：实现 `Request`、`Response`、`AsyncDispatcher`、`UliwebRouter`、`ASGIApplication` 及中间件栈构建、同步适配器、路由匹配。所有 ASGI 相关实现集中于此。
- `uliweb/core/rules.py`（修改）：`expose` 装饰器、`_merge_rules()`、`GET/POST` 方法装饰器。
- `uliweb/core/context.py`（新增/修改）：基于 contextvars 的全局状态管理。
- `uliweb/utils/localproxy.py`（修改/复用）：`LocalProxy`、`Global`。
- `uliweb/__init__.py`（修改）：统一导出 Request、Response、expose、Middleware、ASGI_AVAILABLE、AsyncDispatcher 等。

组件与工具：
- `uliweb/core/dispatch.py`（修改）：事件分发 `acall` 异步化。
- `uliweb/core/template.py`（修改）：`AsyncTemplateLoader.load_async` / `generate_async`。
- `uliweb/mail`、`uliweb/contrib/*`（按需修改）：session / auth / cache 等异步适配（参考 `uliweb/contrib/session/middle_session.py`、`uliweb/contrib/auth/middle_auth.py`、`uliweb/contrib/cache/__init__.py` 的 `get_async_cache`）。
- `uliweb/asgi/profile.py`（修改）：Profile 性能分析迁移到 ASGI。

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
7. **类视图方法 auto-register 语义修正**（spec §3.17）：在 `parse_class` 的 else 分支（[rules.py:325-342](uliweb/core/rules.py#L325-L342)）前置 L1/L2/L3 守卫，跳过 HTTP 动词方法名 + 显式 opt-out/opt-in。
8. **错误响应状态码语义修正**（spec §3.18）：让 `error()` 的 `status` 参数在 ASGI 下生效——两处一行级改动（均集中在 `uliweb/core/SimpleFrame.py`）：
   - `AsyncDispatcher._error`（[SimpleFrame.py:2392](uliweb/core/SimpleFrame.py#L2392)）：`status_code=500` → `kwargs.get('status', 500)`。
   - `_handle_exception` 的 uliweb `HTTPError` 分支（[SimpleFrame.py:3452](uliweb/core/SimpleFrame.py#L3452)）：`status_code=403` → `exception.errors.get('status', 403)`。
   - 单测：`tests/test_error_status.py` 覆盖 `error(msg, status=400/403)` ASGI 返回对应状态码、未传 status 默认 500、抛 HTTPError 时按 `errors['status']` 返回；agent-gateway 回归（非法 id → 400 / 无权限 → 403 / 不存在 → 404）。
9. **验证与清理**：移除 werkzeug 依赖，跑通检查清单与测试。

## 风险与缓解

- 最可能弄坏什么：现有同步视图函数在适配器下的行为（POST 等同步属性访问会抛异常）→ 通过请求数据预加载 + 明确弃用提示缓解，并保留同步属性抛异常作为引导。
- 哪一步最冒险：中间件系统从 WSGI 迁移到纯 ASGI，接口差异大 → 提供高级/底层两套接口并支持混合，兼容传统 `process_*` 接口。
- 放弃了的其他做法及原因：新建独立 `starlette.py` 文件 → 放弃，统一集中于 `SimpleFrame.py` 以降低复杂度；使用 contextvars 直接代理而非 LocalProxy → 放弃，采用 LocalProxy 保持与 WSGI 一致的统一接口。

## 实际实现状态（已完成）

**核心改进点：**
1. 同步适配器机制：解决"大爆炸式"迁移问题，支持现有同步代码平滑过渡。
2. 强制异步化接口：避免 async property 兼容性陷阱，采用明确异步方法。
3. 渐进式迁移策略：支持外部异步、内部同步，降低迁移风险。

**技术架构改进：** Request/Response 修复 async property 陷阱；Dispatcher 内置同步适配器；中间件采用纯 ASGI 接口；状态管理用 contextvars 替代 threading.local。

**迁移收益：** 性能提升（更高并发）、功能增强（WebSocket/SSE）、生态整合（Python 异步生态）、未来兼容（现代 Web 标准）、平滑迁移（同步适配器渐进升级）。

**已实现功能：** ASGI 3.0 接口、Request/Response 异步对象、Werkzeug→Starlette 路由转换、模板异步渲染（协程池）、兼容中间件系统、错误处理、CORS、WebSocket、兼容配置系统、Profile 性能分析。

**实际实现特点：**
1. 渐进式迁移：支持逐步迁移到 ASGI。
2. 兼容性优先：保持与现有项目完全兼容。
3. 性能优化：通过协程池实现同步→异步平滑过渡。
4. 开发友好：提供详细错误信息与调试支持。
5. 代码集中：所有 ASGI 实现集中在 `SimpleFrame.py`。

**使用方式：** 用 Uvicorn / Hypercorn / Daphne 运行；继续使用 `settings.ini` 配置；保持 `@expose` 与视图接口；可逐步迁移。

**移除 werkzeug 后的验证快照：**
```
✓ Request: starlette.requests.Request
✓ Response: starlette.responses.Response
✓ Middleware: uliweb.Middleware
✓ expose: function
✓ ASGI_AVAILABLE: True
✓ Context proxies: available
✓ AsyncDispatcher: available
```

## 证明（如何证明它工作）

### 测试验收（Test Case Acceptance）

在 uliweb3 仓库根目录执行以下命令，对 `test/` 目录进行整体测试（含 doctest），作为本迁移的**验收门槛**：

```bash
# 在 uliweb3 根目录执行（不在 test/ 内，以避免相对路径/导入问题）
nosetests --with-doc test
```

- 该命令基于 nose + doctest 插件（`--with-doc`）运行 `test/` 下全部用例与文档测试。
- 关键覆盖用例文件（与本迁移相关）：
  - `test_async_dispatcher.py`：ASGI 分发、同步视图适配、事务安全（`sync_orm_wrapper` 提交/回滚）。
  - `test_request_async.py`：异步 Request 数据读取（`get_POST`/`get_FILES`/`get_json`）。
  - `test_expose.py` / `test_url_for.py` / `test_url.py`：路由与反向 URL。
  - `test_middleware.py` / `test_middleware_init.py`：中间件系统。
  - `test_websocket.py` / `test_sse_streaming.py`：WebSocket 与 SSE。
  - `test_mail.py`：邮件发送。
  - `test_orm*.py`、`test_cache.py`、`test_session.py` 等：功能组件异步适配。
- 注意事项：`test_cache.test_redis` 需本地 Redis（`localhost:6379`），未启动会报连接错误；Python 3.10+ 若缺 `pkg_resources`，相关静态文件用例会自动 `SkipTest`。
- 验收标准：上述命令执行通过（`OK`，无失败/错误）。

### 迁移检查清单

**核心组件：**
- [x] Request/Response 对象迁移（基于 Starlette）
- [x] Dispatcher 类重构（ASGI 接口）
- [x] URL 路由系统迁移（路由适配器）
- [x] 全局状态管理迁移（contextvars）
- [x] 中间件系统适配（兼容现有中间件）
- [x] 模板系统异步化（协程池）
- [x] 错误处理机制（完整异常处理）
- [x] WebSocket 支持（完整协议）

**功能组件：**
- [x] HTML 生成工具（保持兼容）
- [x] JSON 编码工具（保持兼容）
- [x] 静态文件服务：项目级 `project_dir/static/`、app 级 `apps/{app}/static/`、`pkg_resources` 查找、路径遍历防护、隐藏文件控制
- [x] 文件上传下载（异步化）
- [x] CORS 支持（内置）
- [x] 会话管理（`middle_session.py` 异步适配）
- [x] 认证系统（`middle_auth.py` 异步适配）
- [x] 数据库连接（同步 SQLAlchemy 经协程池）
- [x] 缓存系统（`get_async_cache` 异步适配器）

**测试验证：**
- [x] 单元测试（异步用例）
- [x] 集成测试（端到端）
- [x] 兼容性测试（现有项目）
- [x] WebSocket 功能测试
- [x] 性能测试对比
- [x] 压力/负载测试

### 迁移时间线（建议）

- **阶段一（1-2月）**：基础架构迁移、验证同步适配器、培训团队。
- **阶段二（2-4月）**：逐步迁移关键业务到异步、优化性能路径、完善测试。
- **阶段三（4-6月）**：全面异步化优化、性能调优与监控、生产验证。
- **阶段四（长期）**：插件异步化、社区生态、持续优化。

### 实现后补充说明

**Scope 状态管理特别说明：** `scope['state']` 提供统一状态容器，类型安全、便于中间件协作、性能优化；推荐中间件在 `scope['state']` 中初始化与传递状态。未来可扩展：类型化状态（TypedDict/dataclass）、状态验证、状态监控、状态持久化（如会话）。

**开发最佳实践：**
```python
# 推荐：明确的异步方法调用
post_data = await request.get_POST()
json_data = await request.get_json()
# 避免：使用已弃用的同步属性
# post_data = request.POST  # ❌ 会抛出异常

# 现有同步代码可继续使用（框架自动适配为异步执行）
@expose('/legacy/view')
def legacy_view():
    return {"status": "legacy function"}

# 混合模式开发
@expose('/mixed/view')
async def mixed_view():
    sync_result = await anyio.to_thread.run_sync(sync_function)
    async_result = await async_function()
    return {"sync": sync_result, "async": async_result}
```

**注意事项：**
- 技术：线程安全、上下文管理、依赖管理、异步操作错误处理与重试。
- 迁移：兼容性保证、监控线程池使用、合理配置预加载内存、混合模式调试支持。

**配置优化建议：**
```ini
[ASGI]
SYNC_THREAD_POOL_SIZE = 20        # 根据并发需求调整
PRELOAD_REQUEST_DATA = true       # 启用数据预加载
SYNC_FUNCTION_TIMEOUT = 30        # 同步函数超时时间
LOG_SYNC_ADAPTER_USAGE = true     # 记录适配器使用情况

[GLOBAL]
DEBUG = true                      # 开发阶段启用调试模式
```
