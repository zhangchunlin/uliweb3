# Uliweb 从 Werkzeug 迁移到 Starlette 技术迁移指南

## 目录
- [1. 概述](#1-概述)
- [2. 架构对比分析](#2-架构对比分析)
  - [2.1 原有 WSGI 架构（基于 Werkzeug）](#21-原有-wsgi-架构基于-werkzeug)
  - [2.2 新的 ASGI 架构（基于 Starlette）](#22-新的-asgi-架构基于-starlette)
- [3. 迁移策略和阶段划分](#3-迁移策略和阶段划分)
  - [3.1 阶段一：基础架构迁移](#31-阶段一基础架构迁移)
  - [3.2 阶段二：功能完整性](#32-阶段二功能完整性)
  - [3.3 阶段三：性能优化](#33-阶段三性能优化)
  - [3.4 阶段四：生态兼容](#34-阶段四生态兼容)
  - [3.5 阶段五：完全移除 WSGI（最终目标）](#35-阶段五完全移除-wsgi最终目标)
- [4. 核心组件迁移实现](#4-核心组件迁移实现)
  - [4.1 Request/Response 对象迁移](#41-requestresponse-对象迁移)
  - [4.2 Dispatcher 类重构](#42-dispatcher-类重构)
  - [4.3 URL 路由系统迁移](#43-url-路由系统迁移)
  - [4.4 全局状态管理迁移](#44-全局状态管理迁移)
  - [4.5 中间件系统适配](#45-中间件系统适配)
  - [4.6 模板系统异步化](#46-模板系统异步化)
  - [4.7 事件分发系统异步化](#47-事件分发系统异步化)
  - [4.8 命令系统迁移](#48-命令系统迁移)
  - [4.9 HTML 和 UAML 生成工具迁移](#49-html-和-uaml-生成工具迁移)
  - [4.10 JSON 编码工具迁移](#410-json-编码工具迁移)
  - [4.11 ASGI 处理程序实现](#411-asgi-处理程序实现)
- [5. Settings 配置迁移策略](#5-settings-配置迁移策略)
  - [5.1 现有 Settings 系统分析](#51-现有-settings-系统分析)
  - [5.2 ASGI Settings 迁移方案](#52-asgi-settings-迁移方案)
- [6. 技术挑战与解决方案](#6-技术挑战与解决方案)
  - [6.1 同步到异步的迁移](#61-同步到异步的迁移)
  - [6.2 全局状态管理](#62-全局状态管理)
  - [6.3 URL 路由兼容性](#63-url-路由兼容性)
- [7. 性能优化机会](#7-性能优化机会)
  - [7.1 异步 I/O 操作](#71-异步-io-操作)
  - [7.2 并发处理能力](#72-并发处理能力)
  - [7.3 WebSocket 支持](#73-websocket-支持)
- [8. 实际实现状态总结](#8-实际实现状态总结)
  - [8.1 已实现的功能](#81-已实现的功能)
  - [8.2 实际实现特点](#82-实际实现特点)
  - [8.3 使用方式](#83-使用方式)
- [9. 迁移检查清单](#9-迁移检查清单)
  - [9.1 核心组件迁移状态](#91-核心组件迁移状态)
  - [9.2 功能组件迁移状态](#92-功能组件迁移状态)
  - [9.3 测试验证状态](#93-测试验证状态)
- [10. 总结和最佳实践](#10-总结和最佳实践)

## 1. 概述

本文档详细阐述了将 Uliweb 框架从基于 Werkzeug 的 WSGI 架构迁移到基于 Starlette 的 ASGI 架构的完整技术方案。该迁移将使 Uliweb 支持：

- **异步处理能力**：充分利用现代 Python 的 async/await 语法
- **WebSocket 支持**：原生支持实时双向通信
- **更高性能**：更好的并发处理能力
- **现代生态集成**：更好的 Python 异步生态整合

**重要改进：渐进式迁移策略**
- **同步适配器机制**：引入框架层自动同步/异步适配器，支持现有同步代码平滑过渡
- **强制异步化接口**：避免 async property 兼容性陷阱，采用明确的异步方法
- **渐进式迁移**：支持外部异步、内部同步的平滑过渡，降低迁移风险

## 2. 架构对比分析

### 2.1 原有 WSGI 架构（基于 Werkzeug）

Uliweb 原有架构使用 Werkzeug 作为底层 HTTP 处理框架，主要组件包括：

| 组件 | 实现方式 | 依赖 |
|------|----------|------|
| Request/Response 对象 | 继承自 `werkzeug.Request` 和 `werkzeug.Response` | werkzeug |
| URL 路由 | 使用 `werkzeug.routing.Map` 和 `Rule` | werkzeug.routing |
| WSGI 应用 | `Dispatcher` 类实现 `__call__` 方法 | 自定义 |
| 中间件系统 | 基于 WSGI 标准的中间件链 | 自定义 |
| 全局状态管理 | 使用 `werkzeug.local.Local` | werkzeug.local |

**核心文件依赖：**
- `uliweb/core/SimpleFrame.py`：核心分发器
- `uliweb/wsgi/*`：WSGI 相关工具和中间件

### 2.2 目标 ASGI 架构（基于 Starlette）

Starlette 是一个轻量级的 ASGI 框架/工具包，具有以下特性：

- **ASGI 兼容**：支持异步请求处理
- **高性能**：基于 async/await 语法
- **中间件支持**：丰富的中间件生态系统
- **WebSocket 支持**：原生 WebSocket 支持
- **背景任务**：支持后台异步任务

## 3. 迁移策略和阶段划分

### 3.1 阶段一：基础架构迁移（渐进式兼容）✅ 完成
- [x] 核心 Request/Response 对象迁移（修复 async property 陷阱）
  - 代码：`uliweb/core/starlette.py` 的 Request 类，实现了 get_POST(), get_FILES(), get_json() 等异步方法
- [x] ASGI 接口实现（包含同步适配器机制）
  - 代码：`uliweb/core/starlette.py` 的 AsyncDispatcher 类，实现 `__call__(scope, receive, send)`
  - 通过 `loop.run_in_executor()` 实现同步函数自动适配
- [x] 基本路由系统（支持同步视图函数自动适配）
  - 代码：`uliweb/core/rules.py` 的 Expose 类 + `uliweb/core/starlette.py` 的 UliwebRouter 类

**关键改进：同步适配器机制**
```python
# 在 Dispatcher 中实现同步视图函数自动适配
async def _call_view_function(self, func, request, *args, **kwargs):
    """智能调用视图函数，支持同步和异步函数"""
    if asyncio.iscoroutinefunction(func):
        # 异步函数直接调用
        return await func(request, *args, **kwargs)
    else:
        # 同步函数在线程池中执行，避免阻塞事件循环
        return await anyio.to_thread.run_sync(func, request, *args, **kwargs)
```

### 3.2 阶段二：功能完整性（兼容性优先）✅ 完成
- [x] 中间件系统迁移（保持现有接口兼容性）
  - 代码：`uliweb/core/starlette.py` 的 `_init_middlewares()`, `_process_middleware()` 方法
  - 支持 process_request/process_response/process_exception 传统接口和 ASGI 中间件接口
- [x] 模板系统适配（同步/异步渲染支持）
  - 代码：`uliweb/core/starlette.py` 的 `_render_template()` 方法，通过协程池实现
- [x] 会话管理（异步化改造）
  - 代码：`uliweb/contrib/session/middle_session.py` 的 async dispatch 方法

### 3.3 阶段三：性能优化（渐进异步化）⚠️ 部分完成
- [x] WebSocket 支持（纯异步功能）
  - 代码：`uliweb/core/starlette.py` 的 `handle_websocket()` 方法
- [x] 异步数据库驱动集成（可选，保持同步驱动兼容）
  - 当前通过协程池 `run_in_executor()` 适配同步 SQLAlchemy
- [ ] 缓存系统优化（支持同步/异步后端）- TODO：当前使用同步缓存后端

### 3.4 阶段四：生态兼容（平滑过渡）✅ 完成
- [x] 插件系统适配（提供迁移指南和工具）
  - 文档：`uliweb/core/asgi.md` 本文档作为迁移指南
- [x] 文档更新（包含兼容性说明和最佳实践）
  - 文档：本文档详细说明了兼容性保证和最佳实践
- [x] 弃用策略（明确迁移时间表和兼容性保证）
  - 文档：3.5.4 兼容性保障和 3.5.5 风险评估与缓解

### 3.5 阶段五：完全移除 WSGI（最终目标）❌ 未完成
- 当前仍保留 WSGI 兼容模式（uliweb/core/SimpleFrame.py）
- werkzeug 依赖尚未从 setup.py 中移除
- 这是长期目标，需要在确保 ASGI 框架稳定运行后才能开始

**目标**：完全移除所有 werkzeug 依赖和对 WSGI 的支持，只保留 ASGI 架构。

**前置条件**（必须在此阶段开始前完成）：
- 所有核心功能已完成 ASGI 迁移并稳定运行
- 现有项目可以无缝迁移到 ASGI 架构
- 插件生态系统完成适配

**具体计划**：

#### 3.5.1 模块重构（第一部分）

1. **保留 SimpleFrame.py 作为统一入口**
   - 保持 `uliweb/core/SimpleFrame.py` 不重命名
   - 将 WSGI 相关代码移至 `uliweb/core/wsgi_adapter.py`（可选保留）
   - 主要框架逻辑集中在 `uliweb/core/starlette.py`

2. **重构 uliweb/__init__.py**
   - 保留 ASGI/WSGI 双模式支持（与当前一致）
   - 移除 `ASGI_AVAILABLE` 检查（始终假设 Starlette 可用）
   - 简化导入逻辑，直接从 `starlette.py` 导入

#### 3.5.2 werkzeug 依赖清理（第二部分）

1. **识别所有 werkzeug 引用**
   ```
   搜索命令: grep -rn "from werkzeug\|import werkzeug" uliweb/

   需要检查的模块：
   - uliweb/core/SimpleFrame.py
   - uliweb/core/starlette.py
   - uliweb/utils/（工具模块）
   - uliweb/contrib/（插件模块）
   ```

2. **逐模块迁移**
   - Request/Response：已迁移到 Starlette
   - routing：已迁移到 Starlette
   - exceptions：考虑使用 Starlette 内置或自实现
   - local：已迁移到 contextvars

3. **更新依赖配置**
   - 更新 `setup.py` 中的 `install_requires`
   - 从 `werkzeug` 改为 `starlette`
   - 考虑保留 `werkzeug` 作为可选依赖（用于 WSGI 兼容模式）

#### 3.5.3 完整代码结构（目标状态）

```
uliweb/
├── __init__.py              # 统一入口，ASGI/WSGI 双模式
├── manage.py                # 管理命令入口
├── core/
│   ├── __init__.py
│   ├── starlette.py         # 主要 ASGI 框架（核心）
│   ├── SimpleFrame.py       # 统一框架（兼容层）
│   ├── wsgi_adapter.py      # WSGI 适配器（可选保留）
│   ├── context.py           # 上下文管理（contextvars）
│   ├── dispatch.py          # 事件分发
│   ├── template.py          # 模板系统
│   ├── rules.py             # 路由规则
│   ├── html.py              # HTML 工具
│   ├── js.py                # JS 工具
│   ├── uaml.py              # UAML 工具
│   └── asgi.md              # ASGI 迁移指南
├── contrib/
│   ├── auth/                # 认证（已适配 ASGI）
│   ├── session/             # 会话（已适配 ASGI）
│   ├── orm/                 # ORM（需适配）
│   └── ...
└── utils/                   # 工具模块
```

#### 3.5.4 兼容性保障

1. **向后兼容性策略**
   - 提供 `uliweb.core.wsgi_adapter` 作为独立模块
   - 需要 WSGI 的用户可以显式导入：`from uliweb.core.wsgi_adapter import Dispatcher`
   - 主要入口 `from uliweb import Dispatcher` 默认返回 ASGI 版本

2. **版本过渡方案**
   - v4.0: 标记 WSGI 模式为 deprecated
   - v4.1: 警告提示移除 WSGI 的时间表
   - v5.0: 完全移除 WSGI（如果社区同意）

3. **迁移工具**
   - 提供命令行工具检查项目中的 werkzeug 使用
   - 生成迁移报告和建议

#### 3.5.5 风险评估与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 现有项目不兼容 | 高 | 提供迁移指南和兼容性层 |
| 插件生态断裂 | 中 | 提供适配器框架和过渡期 |
| 性能回退 | 低 | 充分测试和优化 |
| WebSocket 依赖 | 中 | 确认 Starlette 满足需求 |

#### 3.5.6 时间线建议

- **Milestone 1** (v3.5): 完成所有核心组件 ASGI 迁移
- **Milestone 2** (v3.6): 简化代码结构，移除冗余
- **Milestone 3** (v4.0): 标记 WSGI 为 deprecated
- **Milestone 4** (v5.0): 完全移除 WSGI（需要社区共识）

**注意**：阶段五应该是长期目标，需要在确保 ASGI 框架稳定运行、插件生态完成适配后才能开始。建议以 major version 升级的方式推进此阶段。

## 4. 核心组件迁移实现

### 4.1 Request/Response 对象迁移（修复兼容性陷阱）

**旧的实现：**
```python
from werkzeug import Request as OriginalRequest, Response as OriginalResponse

class Request(OriginalRequest):
    GET = OriginalRequest.args
    POST = OriginalRequest.form
    params = OriginalRequest.values
    FILES = OriginalRequest.files

    @property
    def json(self):
        return json.loads(self.data)

    is_xhr = property(lambda x: x.environ.get('HTTP_X_REQUESTED_WITH', '')
                      .lower() == 'xmlhttprequest')
```

**改进的实现（修复 async property 陷阱）：**
```python
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile, FormData
import json as jsn

class Request(StarletteRequest):
    """基于 Starlette 的 Request 类，修复兼容性陷阱"""

    @property
    def GET(self):
        """兼容 GET 参数访问（同步属性）"""
        return self.query_params

    async def get_POST(self):
        """异步获取 POST 表单数据（强制异步方法）"""
        if self.method == "POST":
            form = await self.form()
            return form
        return {}

    async def get_FILES(self):
        """异步获取上传文件（强制异步方法）"""
        if self.method == "POST":
            form = await self.form()
            return {k: v for k, v in form.items() if isinstance(v, UploadFile)}
        return {}

    async def get_json(self):
        """异步获取 JSON 数据（强制异步方法，修复递归调用）"""
        return await super().json()

    @property
    def is_xhr(self):
        """检查是否为 AJAX 请求（同步属性）"""
        return self.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'

    async def get_params(self):
        """异步获取合并参数（强制异步方法，避免阻塞）"""
        # 由于 POST 数据需要异步读取，params 必须也是异步方法
        get_params = self.query_params
        post_params = await self.get_POST()

        # 合并 GET 和 POST 参数
        merged_params = {}
        merged_params.update(get_params)
        merged_params.update(post_params)
        return merged_params

    # 向后兼容的同步属性（标记为已弃用）
    @property
    def POST(self):
        """已弃用：同步访问 POST 数据会抛出异常"""
        raise RuntimeError(
            "POST 属性已弃用，请使用 await request.get_POST() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def FILES(self):
        """已弃用：同步访问 FILES 数据会抛出异常"""
        raise RuntimeError(
            "FILES 属性已弃用，请使用 await request.get_FILES() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def json(self):
        """已弃用：同步访问 JSON 数据会抛出异常"""
        raise RuntimeError(
            "json 属性已弃用，请使用 await request.get_json() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def params(self):
        """兼容 params 属性，返回 GET 参数

        注意：由于 POST 数据需要异步读取，此属性仅返回 GET (query) 参数。
        如需合并 GET 和 POST 参数，请在异步视图函数中：

        ```python
        @expose('/api/data')
        async def async_view():
            get_params = dict(request.query_params)
            post_params = dict(await request.get_POST())
            all_params = {**get_params, **post_params}
            return all_params
        ```
        """
        return self.query_params

class Response(StarletteResponse):
    """基于 Starlette 的 Response 类，保持与现有 Uliweb 的兼容性"""

    def write(self, value):
        """兼容 write 方法"""
        # 在异步环境中，write 方法需要特殊处理
        # 这里暂时保持接口兼容性
        pass
```

**兼容性改进说明：**

1. **避免 async property 陷阱**：将 `async def POST`、`async def FILES`、`async def json` 改为明确的异步方法 `get_POST()`、`get_FILES()`、`get_json()`
2. **修复递归调用错误**：`async def json` 中的 `return await self.json()` 改为 `return await super().json()`
3. **强制异步化**：`params` 属性改为异步方法 `get_params()`，因为需要异步读取 POST 数据
4. **明确的弃用策略**：保留同步属性但抛出异常，指导用户使用正确的异步方法
5. **同步适配器支持**：框架层提供同步到异步的自动适配，支持现有同步代码

**使用示例：**
```python
# 异步视图函数（推荐）
@expose('/api/data')
async def async_view():
    # 正确的异步访问方式
    post_data = await request.get_POST()
    json_data = await request.get_json()
    files = await request.get_FILES()
    params = await request.get_params()

    return {"status": "success"}

# 同步视图函数（通过适配器支持）
@expose('/sync/data')
def sync_view():
    # 框架会自动将同步函数包装为异步执行
    # 在同步函数内部，request.POST 等属性会抛出异常
    # 应该使用同步版本的替代方法或重构为异步

    # 错误示例（会抛出异常）：
    # post_data = request.POST  # ❌ RuntimeError

    # 正确做法：重构为异步或使用同步适配器
    return {"status": "sync function supported via adapter"}
```

### 4.2 Dispatcher 类重构

**旧的 WSGI 接口：**
```python
class Dispatcher(object):
    def __call__(self, environ, start_response):
        response = self._open(environ)
        return response(environ, start_response)
```


**实际实现（与规划一致但更完整）：**
```python
class AsyncDispatcher:
    """支持 ASGI 3.0 接口的异步 Dispatcher"""

    def __init__(self, apps_dir='apps', project_dir=None, include_apps=None,
                 start=True, default_settings=None, settings_file='settings.ini',
                 local_settings_file='local_settings.ini', **kwargs):

        self.apps_dir = apps_dir
        self.project_dir = project_dir
        self.include_apps = include_apps or []
        self.default_settings = default_settings or {}
        self.settings_file = settings_file
        self.local_settings_file = local_settings_file
        self.router = UliwebRouter()
        self._initialized = False

        if start:
            # 注意：使用 asyncio.create_task 可能导致竞态条件
            # 第一个请求可能在初始化完成前到达
            # handle_http 中有等待初始化完成的逻辑，这是正确的处理方式
            # 但在构造函数中创建任务可能导致初始化任务被取消
            # 建议：在应用启动时显式调用 init() 或使用事件等待
            asyncio.create_task(self._async_init())

    async def _async_init(self):
        """异步初始化方法"""
        if not self._initialized:
            await self.init()
            self._initialized = True

    async def __call__(self, scope, receive, send):
        """ASGI 3.0 接口实现"""
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")

    async def handle_http(self, scope, receive, send):
        """处理 HTTP 请求"""
        # 确保应用已初始化
        if not self._initialized:
            await self._async_init()

        request = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request_var.set(request)

        try:
            # 处理请求
            response = await self._open(request)
            await response(scope, receive, send)
        finally:
            # 清理上下文
            request_var.reset(request_token)

    async def handle_websocket(self, scope, receive, send):
        """处理 WebSocket 请求"""
        from starlette.websockets import WebSocket
        websocket = WebSocket(scope, receive, send)

        # 设置 WebSocket 上下文
        websocket_token = request_var.set(websocket)

        try:
            await websocket.accept()
            # 这里可以添加 WebSocket 处理逻辑
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                # 处理消息
                await self._handle_websocket_message(websocket, message)
        finally:
            request_var.reset(websocket_token)
```

### 4.3 URL 路由系统迁移

**旧的实现基于 Werkzeug：**
```python
from werkzeug.routing import Map, Rule
url_map = Map(strict_slashes=False)

# 路由注册
rules.add_rule(url_map, _url, endpoint, **kw)
```

**迁移到 Starlette 路由：**
```python
from starlette.routing import Route, Router, Mount
from starlette.applications import Starlette

**实际实现（与规划一致但更完整）：**
```python
class UliwebRouter:
    """Uliweb 路由适配器，将 Werkzeug 风格路由转换为 Starlette 风格"""

    def __init__(self):
        self.routes = []
        self.url_map = {}
        self.router = Router()

    def add_route(self, rule, endpoint, **kwargs):
        """转换 Werkzeug 风格路由到 Starlette 风格"""
        # 转换参数格式: <name> -> {name}
        # 注意：Werkzeug 的类型提示如 <int:id> 会被转换为 {id}，类型信息会丢失
        # 开发者需要在视图函数中进行类型转换
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)

        methods = kwargs.get('methods', ['GET'])
        name = kwargs.get('name')

        # 创建 Starlette 路由
        route = Route(starlette_rule, endpoint, methods=methods, name=name)

        self.routes.append(route)
        self.url_map[endpoint] = route
        self.router.routes.append(route)

        return route

    def add_websocket_route(self, rule, endpoint, **kwargs):
        """添加 WebSocket 路由"""
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)
        name = kwargs.get('name')

        from starlette.routing import WebSocketRoute
        route = WebSocketRoute(starlette_rule, endpoint, name=name)

        self.routes.append(route)
        self.url_map[endpoint] = route
        self.router.routes.append(route)

        return route

    def mount(self, path, app, name=None):
        """挂载子应用"""
        mount = Mount(path, app=app, name=name)
        self.router.routes.append(mount)
        return mount

# 路由收集机制，类似 SimpleFrame.py 中的 __exposes__
__exposes__ = {}
__no_need_exposed__ = []
__url_names__ = {}

def expose(rule=None, **kwargs):
    """适配现有的 expose 装饰器"""
    def decorator(func):
        # 收集路由信息，而不是直接注册
        from uliweb.utils.date import now
        from uliweb.utils._compat import ismethod, get_class

        # 获取应用名称
        def _get_appname(module_name):
            parts = module_name.split('.')
            # 找到第一个不是 'views' 的部分作为应用名
            for part in parts:
                if part != 'views' and not part.startswith('_'):
                    return part
            return parts[0] if parts else 'unknown'

        # 获取端点名称
        def _get_endpoint(func):
            if ismethod(func):
                _class = get_class(func)
                return '.'.join([_class.__module__, _class.__name__, func.__name__])
            elif callable(func):
                # 直接返回函数对象，而不是字符串端点名
                # 这样在路由匹配时可以直接调用函数
                return func
            else:
                return str(func)

        # 获取应用名和端点
        appname = _get_appname(func.__module__)
        endpoint = _get_endpoint(func)

        # 收集路由信息
        route_info = (appname, endpoint, rule, kwargs, now())
        __no_need_exposed__.append(route_info)

        # 设置函数属性，保持与 SimpleFrame.py 的兼容性
        setattr(func, '__exposed__', True)
        setattr(func, '__no_rule__', rule is None)
        if not hasattr(func, '__old_rule__'):
            setattr(func, '__old_rule__', {})
        getattr(func, '__old_rule__')[rule] = rule
        setattr(func, '__template__', kwargs.get('template'))
        setattr(func, '__layout__', kwargs.get('layout'))
        setattr(func, '__fixed_url__', rule and rule.startswith('!'))

        return func
    return decorator

def POST(rule, **kw):
    """POST 方法装饰器"""
    kw['methods'] = ['POST']
    return expose(rule, **kw)

def GET(rule, **kw):
    """GET 方法装饰器"""
    kw['methods'] = ['GET']
    return expose(rule, **kw)

def _merge_rules():
    """合并路由规则，类似 SimpleFrame.py 中的 merge_rules 函数"""
    from itertools import chain

    s = []
    index = {}
    for v in sorted(__no_need_exposed__, key=lambda x: x[4]):  # 按时间戳排序
        appname, endpoint, url, kw, timestamp = v
        if 'name' in kw:
            url_name = kw.pop('name')
        else:
            url_name = endpoint
        __url_names__[url_name] = endpoint
        methods = [y.upper() for y in kw.get('methods', [])]
        methods.sort()

        key = url, tuple(methods), kw.get('subdomain')
        i = index.get(key, None)
        if i is not None:
            s[i] = (appname, endpoint, url, kw)
        else:
            s.append((appname, endpoint, url, kw))
            index[key] = len(s) - 1

    return s
```

### 4.4 全局状态管理迁移

**旧的实现基于线程局部存储：**
```python
from werkzeug.local import Local, LocalManager
local = Local()
local.request = None
local.response = None
local_manager = LocalManager([local])

# 全局对象存储
__global__ = Global()
__global__.settings = pyini.Ini(lazy=True)
__global__.application = None
```


**实际实现（使用 contextvars）：**

Uliweb3 使用 Python 的 `contextvars` 模块来实现全局状态管理，它比线程局部存储更适合异步环境。所有的全局状态都存储在 `uliweb/core/context.py` 模块中，提供统一的访问接口。

```python
# uliweb/core/context.py
import contextvars

# 请求上下文变量
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')
settings_var = contextvars.ContextVar('settings')
application_var = contextvars.ContextVar('application')

# 获取当前值的辅助函数
def get_request():
    return request_var.get(None)

def get_response():
    return response_var.get(None)

def get_settings():
    return settings_var.get(None)

def get_application():
    return application_var.get(None)

# 代理类：从 contextvars 获取值
class GlobalSettingsProxy:
    """全局 settings 代理类，只从 contextvars 获取 settings"""

    def __init__(self):
        self._var = settings_var

    def _get_instance(self):
        result = self._var.get(None)
        if result is None:
            raise RuntimeError("settings not initialized. Please ensure AsyncDispatcher or Dispatcher has been created.")
        return result

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

    # ... 其他代理方法

class ContextProxy:
    """通用代理类，用于 request/response/application"""

    def __init__(self, var, default=None):
        self._var = var
        self._default = default

    def _get_instance(self):
        return self._var.get(self._default)

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

    # ... 其他代理方法

# 创建全局代理对象
settings_proxy = GlobalSettingsProxy()
request_proxy = ContextProxy(request_var, None)
response_proxy = ContextProxy(response_var, None)
application_proxy = ContextProxy(application_var, None)
```

**在 AsyncDispatcher 中设置上下文：**

```python
class AsyncDispatcher:
    def __init__(self, apps_dir='apps', project_dir=None, include_apps=None,
                 start=True, default_settings=None, settings_file='settings.ini',
                 local_settings_file='local_settings.ini', **kwargs):

        # ... 其他初始化代码

        # 加载 settings 并设置到 contextvars
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.settings = loop.run_until_complete(self._load_settings())

            # 关键：设置到 contextvars
            settings_var.set(self.settings)
            application_var.set(self)  # 设置当前应用实例
            loop.close()
        except Exception as e:
            # 错误处理
            pass
```

**在请求处理中更新上下文：**

```python
async def _open(self, request):
    """处理请求的核心方法"""
    # 设置请求上下文
    response = Response()
    response_token = response_var.set(response)
    settings_token = settings_var.set(self.settings)
    application_token = application_var.set(self)

    try:
        # 处理请求...
        response = await self._process_request(request)
        return response
    finally:
        # 清理上下文
        response_var.reset(response_token)
        settings_var.reset(settings_token)
        application_var.reset(application_token)
```

**导出供外部使用的接口：**

```python
# uliweb/__init__.py 和 uliweb/core/starlette.py
from .context import (
    settings_proxy,
    request_proxy,
    response_proxy,
    application_proxy
)

# 直接导出代理对象
settings = settings_proxy
request = request_proxy
response = response_proxy
application = application_proxy
```

**关键特性：**

1. **只使用 contextvars**：不再使用 `__global__` 回退机制，更简洁清晰
2. **统一的上下文管理**：所有模块使用相同的 contextvars 来源
3. **请求级别的隔离**：每个请求有独立的上下文，不会相互干扰
4. **异步友好**：`contextvars` 是 Python 3.7+ 引入的标准库，专门为异步场景设计
5. **向后兼容**：通过代理类保持与现有代码的兼容性

**注意事项：**

- 在使用任何全局对象（settings、request、response、application）之前，必须确保已经创建了 Dispatcher 并初始化了 contextvars
- 如果在未初始化的情况下访问 settings，会抛出 `RuntimeError` 提示用户初始化应用
- 在测试环境中，需要手动调用 `make_simple_application` 来初始化上下文

### 4.5 中间件系统适配

Uliweb3 迁移到 Starlette 后，中间件系统将采用更合适与 ASGI 的接口，仿照 Starlette 的两种方式，但不直接使用 Starlette 的中间件类。Uliweb 有自己的中间件接口，只支持 ASGI 方式的中间件接口。

Starlette 提供了两种主要的中间件实现方式：

1. **BaseHTTPMiddleware** - 高级中间件接口，适用于大多数场景
2. **纯 ASGI 中间件** - 底层接口，提供更大的灵活性

Uliweb 将实现自己的中间件接口，提供两种方式：

1. **高级中间件接口** - 仿照 Starlette 的 `BaseHTTPMiddleware`，提供 `async def dispatch(self, request, call_next):` 抽象程度较高的接口
2. **底层 ASGI 中间件接口** - 仿照 Starlette 的纯 ASGI 中间件，提供 `async def __call__(self, scope, receive, send):` 比较底层的接口

#### Uliweb 中间件接口实现

Uliweb 的中间件接口设计支持 ASGI 的异步特性：

##### 1. 高级中间件接口（推荐）

```python
from uliweb import Middleware

class MyAdvancedMiddleware(Middleware):
    """高级中间件接口 - 仿照 Starlette 的 BaseHTTPMiddleware"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        # 初始化中间件配置

    async def dispatch(self, request, call_next):
        """
        高级中间件处理方法
        :param request: 请求对象
        :param call_next: 调用下一个中间件或视图函数的异步函数
        :return: 响应对象
        """
        # 请求预处理
        await self.before_request(request)

        # 调用下一个中间件或视图函数
        response = await call_next(request)

        # 响应后处理
        response = await self.after_response(request, response)

        return response

    async def before_request(self, request):
        """请求预处理钩子"""
        # 在这里实现请求预处理逻辑
        pass

    async def after_response(self, request, response):
        """响应后处理钩子"""
        # 在这里实现响应后处理逻辑
        return response

# 使用示例
class LoggingMiddleware(Middleware):
    """请求日志记录中间件"""

    async def dispatch(self, request, call_next):
        import time
        import logging

        start_time = time.time()
        logging.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logging.info(f"Request completed: {response.status_code} in {process_time:.3f}s")
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logging.error(f"Request failed: {str(e)} in {process_time:.3f}s")
            raise
```

##### 2. 底层 ASGI 中间件接口

```python
from uliweb import Middleware
from typing import Dict, Any

class MyASGIMiddleware(Middleware):
    """底层 ASGI 中间件接口 - 仿照 Starlette 的纯 ASGI 中间件"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        # 初始化中间件配置

    async def __call__(self, scope: Dict[str, Any], receive, send):
        """
        ASGI 应用入口点
        :param scope: ASGI scope 字典
        :param receive: 接收消息的异步函数
        :param send: 发送消息的异步函数
        """
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 请求预处理
        await self.process_request(scope)

        try:
            # 调用下一个应用
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope):
        """请求预处理"""
        # 在这里实现请求预处理逻辑
        pass

    async def handle_exception(self, scope, receive, send, exception):
        """异常处理"""
        # 在这里实现异常处理逻辑
        raise exception

# 使用示例
class CORSMiddleware(Middleware):
    """CORS 中间件实现"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        self.allow_origins = settings.get_var('CORS/allow_origins', [])
        self.allow_methods = settings.get_var('CORS/allow_methods', ['GET', 'POST', 'PUT', 'DELETE'])
        self.allow_headers = settings.get_var('CORS/allow_headers', ['*'])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 包装 send 函数以添加 CORS 头
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                # 添加 CORS 头
                headers = message.get("headers", [])
                headers.extend([
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", ", ".join(self.allow_methods).encode()),
                    (b"access-control-allow-headers", ", ".join(self.allow_headers).encode()),
                ])
                message["headers"] = headers
            await send(message)

        # 处理预检请求
        if scope["method"] == "OPTIONS":
            await self.handle_preflight(scope, receive, send_with_cors)
        else:
            await self.application(scope, receive, send_with_cors)

    async def handle_preflight(self, scope, receive, send):
        """处理 CORS 预检请求"""
        from starlette.responses import Response

        response = Response(status_code=204)
        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
        response.headers["access-control-max-age"] = "86400"  # 24小时

        await response(scope, receive, send)
```

##### 3. 中间件配置和使用

在 `settings.ini` 中配置中间件：

```ini
[MIDDLEWARES]
# 高级中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

#### 4.5.1 内置中间件

Starlette 提供了一系列内置中间件，可以快速为应用添加常用功能。

##### CORSMiddleware - 跨域资源共享

```python
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from starlette.middleware import Middleware

app = Starlette(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "https://example.com",
                "https://www.example.com",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            ],
            allow_origin_regex=r"https://.*\.example\.com",
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["X-Custom-Header"],
            max_age=600  # 10分钟
        )
    ]
)
```

**配置参数详解：**
- `allow_origins`: 允许的源列表，可以使用正则表达式
- `allow_methods`: 允许的 HTTP 方法
- `allow_headers`: 允许的请求头
- `allow_credentials`: 是否允许携带凭据
- `expose_headers`: 暴露给客户端的响应头
- `max_age`: 预检请求缓存时间（秒）

##### GZipMiddleware - 响应压缩

```python
from starlette.middleware.gzip import GZipMiddleware

app = Starlette(
    middleware=[
        Middleware(
            GZipMiddleware,
            minimum_size=1000,  # 只压缩大于1KB的响应
            compresslevel=6     # 压缩级别（1-9）
        )
    ]
)
```

##### HTTPSRedirectMiddleware - HTTPS 重定向

```python
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = Starlette(
    middleware=[
        Middleware(HTTPSRedirectMiddleware)
    ]
)
```

##### TrustedHostMiddleware - 可信主机验证

```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = Starlette(
    middleware=[
        Middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "example.com",
                "*.example.com",
                "localhost",
                "127.0.0.1"
            ]
        )
    ]
)
```

#### 4.5.2 自定义中间件开发

##### 基础中间件开发

使用 `BaseHTTPMiddleware` 是最简单的自定义中间件方式：

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time

class TimingMiddleware(BaseHTTPMiddleware):
    """请求计时中间件示例"""

    def __init__(self, app, header_name: str = "X-Process-Time"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers[self.header_name] = str(process_time)

        return response
```

##### 请求预处理中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from typing import List
import re

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """请求验证中间件示例"""

    def __init__(
        self,
        app,
        required_headers: List[str] = None,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB
        allowed_methods: List[str] = None
    ):
        super().__init__(app)
        self.required_headers = required_headers or ['user-agent', 'accept']
        self.max_content_length = max_content_length
        self.allowed_methods = allowed_methods or [
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'
        ]

        # 编译正则表达式以提高性能
        self.content_type_pattern = re.compile(r'^application/(json|xml|x-www-form-urlencoded)')

    async def dispatch(self, request: Request, call_next):
        """请求处理方法 - 实现预处理逻辑"""
        # 执行请求预处理
        validation_result = await self.before_request(request)

        # 如果验证失败，直接返回错误响应
        if validation_result is not None:
            return validation_result

        # 验证通过，继续处理请求
        response = await call_next(request)
        return response

    async def before_request(self, request: Request) -> JSONResponse:
        """请求预处理钩子 - 执行具体验证"""
        # 1. 验证 HTTP 方法
        if request.method not in self.allowed_methods:
            return JSONResponse(
                {'error': f'Method {request.method} not allowed'},
                status_code=405
            )

        # 2. 验证必需的请求头
        missing_headers = [
            header for header in self.required_headers
            if header not in request.headers
        ]
        if missing_headers:
            return JSONResponse(
                {
                    'error': 'Missing required headers',
                    'missing_headers': missing_headers
                },
                status_code=400
            )

        # 3. 验证内容类型（对于有请求体的方法）
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '').lower()

            if not content_type:
                return JSONResponse(
                    {'error': 'Content-Type header is required for this method'},
                    status_code=400
                )

            # 验证内容类型格式
            if not self.content_type_pattern.match(content_type):
                return JSONResponse(
                    {
                        'error': 'Unsupported Content-Type',
                        'supported_types': [
                            'application/json',
                            'application/xml',
                            'application/x-www-form-urlencoded'
                        ]
                    },
                    status_code=415
                )

        # 验证通过，返回 None
        return None
```

##### 响应后处理中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
import json
import time
from typing import Dict, Any, Optional

class ResponseFormatterMiddleware(BaseHTTPMiddleware):
    """响应格式化中间件示例"""

    def __init__(
        self,
        app,
        enable_formatting: bool = True,
        include_timestamp: bool = True,
        include_request_id: bool = True,
        success_status_codes: list = None
    ):
        super().__init__(app)
        self.enable_formatting = enable_formatting
        self.include_timestamp = include_timestamp
        self.include_request_id = include_request_id
        self.success_status_codes = success_status_codes or [200, 201, 202, 204]

    async def dispatch(self, request: Request, call_next):
        """请求处理方法 - 实现响应后处理逻辑"""
        # 获取原始响应
        response = await call_next(request)

        # 执行响应后处理
        formatted_response = await self.after_response(request, response)

        return formatted_response

    async def after_response(
        self,
        request: Request,
        response: Response
    ) -> Response:
        """响应后处理钩子 - 执行具体格式化"""
        # 检查是否应该格式化
        if not self.should_format_response(request, response):
            return response

        try:
            # 获取响应内容
            content = await self.get_response_content(response)

            # 解析 JSON 内容
            if content:
                data = json.loads(content.decode('utf-8'))
            else:
                data = None

            # 构建格式化响应
            formatted_data = self.build_formatted_response(
                request, response, data
            )

            # 创建新响应
            return JSONResponse(
                content=formatted_data,
                status_code=response.status_code,
                headers=self.get_formatted_headers(response)
            )

        except (json.JSONDecodeError, UnicodeDecodeError, Exception) as e:
            # 格式化失败，记录错误并返回原始响应
            await self.log_formatting_error(request, response, e)
            return response

    def should_format_response(self, request: Request, response: Response) -> bool:
        """判断是否应该格式化响应"""
        # 检查是否启用格式化
        if not self.enable_formatting:
            return False

        # 检查状态码
        if response.status_code not in self.success_status_codes:
            return False

        # 检查内容类型
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' not in content_type:
            return False

        # 检查是否已经格式化过
        if response.headers.get('x-formatted') == 'true':
            return False

        return True

    def build_formatted_response(
        self,
        request: Request,
        response: Response,
        data: Any
    ) -> Dict[str, Any]:
        """构建格式化响应数据"""
        formatted_data = {
            'success': response.status_code in self.success_status_codes,
            'status_code': response.status_code,
            'data': data
        }

        # 添加时间戳
        if self.include_timestamp:
            formatted_data['timestamp'] = time.time()

        # 添加请求 ID
        if (self.include_request_id and
            hasattr(request.state, 'request_id')):
            formatted_data['request_id'] = request.state.request_id

        # 添加元数据
        formatted_data['meta'] = {
            'version': '1.0',
            'endpoint': str(request.url.path),
            'method': request.method
        }

        return formatted_data
```

#### 4.5.3 纯 ASGI 中间件

对于需要更底层控制的场景，可以直接实现 ASGI 协议接口：

```python
from starlette.types import ASGIApp, Scope, Receive, Send
from typing import Dict, Any

class ASGICustomMiddleware:
    """直接实现 ASGI 协议的中间件"""

    def __init__(self, app: ASGIApp, **kwargs):
        self.app = app
        self.config = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI 应用入口点 - 必须实现的接口"""
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 创建包装的 send 函数来拦截响应
        send_wrapper = self.create_send_wrapper(scope, send)

        # 请求预处理
        await self.process_request(scope)

        try:
            # 调用下一个应用
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            await self.handle_asgi_exception(scope, receive, send, e)

    def create_send_wrapper(self, scope: Scope, send: Send) -> Send:
        """创建 send 函数包装器"""
        async def send_wrapper(message: Dict[str, Any]) -> None:
            # 处理响应开始消息
            if message["type"] == "http.response.start":
                await self.process_response_start(scope, message)

            # 处理响应体消息
            elif message["type"] == "http.response.body":
                await self.process_response_body(scope, message)

            # 发送原始消息
            await send(message)

        return send_wrapper

    async def process_request(self, scope: Scope) -> None:
        """处理请求"""
        pass

    async def process_response_start(
        self,
        scope: Scope,
        message: Dict[str, Any]
    ) -> None:
        """处理响应开始消息"""
        pass

    async def process_response_body(
        self,
        scope: Scope,
        message: Dict[str, Any]
    ) -> None:
        """处理响应体消息"""
        pass

    async def handle_asgi_exception(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        exception: Exception
    ) -> None:
        """处理 ASGI 级异常"""
        pass
```

#### 4.5.4 中间件执行顺序

中间件按照添加的顺序依次执行，形成处理链：

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

class MiddlewareA(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware A: Before request")
        response = await call_next(request)
        print("Middleware A: After response")
        return response

class MiddlewareB(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware B: Before request")
        response = await call_next(request)
        print("Middleware B: After response")
        return response

class MiddlewareC(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware C: Before request")
        response = await call_next(request)
        print("Middleware C: After response")
        return response

app = Starlette(
    middleware=[
        Middleware(MiddlewareA),  # 最先执行
        Middleware(MiddlewareB),  # 其次执行
        Middleware(MiddlewareC)   # 最后执行（最接近应用）
    ]
)

# 执行顺序：
# A Before → B Before → C Before → 应用处理 → C After → B After → A After
```

#### 4.5.5 常用中间件示例

##### 认证中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request, call_next):
        # 跳过认证的路径
        public_paths = ['/login', '/register', '/docs', '/openapi.json']
        if request.url.path in public_paths:
            return await call_next(request)

        # 检查认证头
        auth_header = request.headers.get('authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JSONResponse(
                {'error': 'Authentication required'},
                status_code=401
            )

        # 验证 JWT token
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            # 将用户信息添加到请求状态
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                {'error': 'Token expired'},
                status_code=401
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                {'error': 'Invalid token'},
                status_code=401
            )

        response = await call_next(request)
        return response
```

##### 日志记录中间件

```python
import logging
from starlette.middleware.base import BaseHTTPMiddleware
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api')

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        # 记录请求信息
        logger.info(f"Request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # 记录响应信息
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} - "
                f"{process_time:.3f}s - {request.method} {request.url.path}"
            )

            return response

        except Exception as e:
            # 记录异常信息
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - "
                f"{process_time:.3f}s - {request.method} {request.url.path}"
            )
            raise
```

##### 限流中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, List

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute=60, burst_capacity=10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_identifier(self, request):
        # 多种方式识别客户端
        api_key = request.headers.get('x-api-key')
        if api_key:
            return f"api_key:{api_key}"

        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # 使用 IP 地址
        client_ip = request.client.host if request.client else 'unknown'
        return f"ip:{client_ip}"

    def _cleanup_old_requests(self, client_id, window_start):
        # 清理过期请求记录
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time >= window_start
        ]

    async def dispatch(self, request, call_next):
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        window_start = current_time - 60  # 1分钟窗口

        # 清理过期记录
        self._cleanup_old_requests(client_id, window_start)

        # 获取当前请求计数
        recent_requests = self.requests[client_id]
        request_count = len(recent_requests)

        # 检查是否超过限制
        if request_count >= self.requests_per_minute + self.burst_capacity:
            # 超过突发容量，直接拒绝
            return JSONResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests'
                },
                status_code=429,
                headers={'Retry-After': '60'}
            )
        elif request_count >= self.requests_per_minute:
            # 超过常规限制，但还在突发容量内
            # 计算需要等待的时间
            oldest_request = min(recent_requests)
            wait_time = 60 - (current_time - oldest_request)

            if wait_time > 0:
                return JSONResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'message': f'Please wait {wait_time:.1f} seconds',
                        'retry_after': wait_time
                    },
                    status_code=429,
                    headers={'Retry-After': str(int(wait_time))}
                )

        # 记录本次请求
        self.requests[client_id].append(current_time)

        # 添加速率限制头部
        response = await call_next(request)
        response.headers.update({
            'X-RateLimit-Limit': str(self.requests_per_minute),
            'X-RateLimit-Remaining': str(self.requests_per_minute - request_count),
            'X-RateLimit-Reset': str(int(current_time + 60))
        })

        return response
```


#### 4.5.6 中间件开发最佳实践

##### 4.5.7 SimpleFrame.py 中间件实现分析与修改方案

在 `SimpleFrame.py` 中，Uliweb 实现了一套基于 WSGI 的中间件系统。为了迁移到 ASGI 架构，我们需要对这套中间件系统进行重新设计，使其完全支持 ASGI 接口。

**SimpleFrame.py 中间件实现分析：**

1. **中间件定义**：
   - 中间件类需要继承自 `Middleware` 基类
   - 中间件类需要实现 `process_request`、`process_response` 或 `process_exception` 方法
   - 中间件在 `settings.ini` 中通过 `MIDDLEWARES` 配置项进行注册

2. **中间件执行流程**：
   - 在 `Dispatcher._open` 方法中处理中间件
   - 按顺序执行 `process_request` 方法
   - 在视图函数执行后，按逆序执行 `process_response` 方法
   - 在异常处理时，按逆序执行 `process_exception` 方法

3. **中间件排序**：
   - 通过 `ORDER` 属性或配置中的顺序值来确定中间件执行顺序
   - 默认排序值为 500

**迁移到纯 ASGI 的修改方案：**

对于现有使用 WSGI 中间件接口（`process_request`、`process_response`、`process_exception` 方法）的中间件，需要统一修改为 ASGI 接口。根据中间件的功能复杂度，有两种修改方式：

1. **复杂中间件**：建议完全重写为 ASGI 架构的中间件（高级接口或底层接口）
2. **简单中间件**：如果业务逻辑简单，可以考虑直接迁移到 Starlette 的中间件架构

为了完全支持 ASGI 架构，我们需要重新设计中间件系统，使其只支持 ASGI 接口：

1. **中间件基类重新设计**：
   - 重新设计 `Middleware` 基类，使其完全基于 ASGI
   - 提供两种中间件接口：
     - 高级接口：提供 `async def dispatch(self, request, call_next)` 方法
     - 底层接口：提供 `async def __call__(self, scope, receive, send)` 方法

2. **中间件执行流程重新设计**：
   - 在 ASGI Dispatcher 中实现新的中间件执行逻辑
   - 支持两种中间件接口的混合使用
   - 实现中间件链式调用机制

3. **中间件配置更新**：
   - 更新 `settings.ini` 中 `MIDDLEWARES` 配置项的处理方式
   - 支持新的中间件接口

**具体实现方案：**

```python
# 重新设计 Middleware 基类以支持纯 ASGI
class Middleware(object):
    """纯 ASGI 中间件基类"""

    def __init__(self, application, settings):
        self.application = application
        self.settings = settings

    async def __call__(self, scope, receive, send):
        """
        底层 ASGI 中间件接口
        :param scope: ASGI scope 字典
        :param receive: 接收消息的异步函数
        :param send: 发送消息的异步函数
        """
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 请求预处理
        await self.process_request(scope)

        try:
            # 调用下一个应用
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope):
        """请求预处理"""
        # 在这里实现请求预处理逻辑
        pass

    async def handle_exception(self, scope, receive, send, exception):
        """异常处理"""
        # 在这里实现异常处理逻辑
        # 默认重新抛出异常
        raise exception

    async def dispatch(self, request, call_next):
        """
        高级中间件接口
        :param request: 请求对象
        :param call_next: 调用下一个中间件或视图函数的异步函数
        :return: 响应对象
        """
        # 调用下一个中间件或视图函数
        response = await call_next(request)
        return response

# 在 ASGI Dispatcher 中实现新的中间件执行逻辑
class AsyncDispatcher:
    async def __call__(self, scope, receive, send):
        """ASGI 3.0 接口实现"""
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")

    async def handle_http(self, scope, receive, send):
        """处理 HTTP 请求"""
        # 确保应用已初始化
        if not self._initialized:
            await self._async_init()

        # 构建中间件链
        app = self._build_middleware_stack()

        # 处理请求
        await app(scope, receive, send)

    def _build_middleware_stack(self):
        """构建中间件调用链"""
        # 从内到外包装应用，形成中间件链
        app = self._handle_request

        # 按逆序添加中间件（确保按配置顺序执行）
        for middleware_cls in reversed(self.middlewares):
            middleware_instance = middleware_cls(self, self.settings)

            # 检查中间件类型
            if hasattr(middleware_instance, 'dispatch') and callable(middleware_instance.dispatch):
                # 高级中间件接口
                app = self._wrap_advanced_middleware(middleware_instance, app)
            elif hasattr(middleware_instance, '__call__') and callable(middleware_instance.__call__):
                # 底层 ASGI 中间件接口
                app = self._wrap_asgi_middleware(middleware_instance, app)
            else:
                # 不是有效的中间件，跳过
                continue

        return app

    def _wrap_advanced_middleware(self, middleware, next_app):
        """包装高级中间件"""
        async def app(scope, receive, send):
            # 只处理 HTTP 请求
            if scope["type"] != "http":
                await next_app(scope, receive, send)
                return

            # 创建请求对象
            request = Request(scope, receive, send)

            # 创建 call_next 函数
            async def call_next(request):
                # 创建新的 scope，可能需要修改
                new_scope = scope.copy()
                # 调用下一个应用
                response = await next_app(new_scope, receive, send)
                return response

            # 调用中间件
            response = await middleware.dispatch(request, call_next)

            # 发送响应
            await response(scope, receive, send)

        return app

    def _wrap_asgi_middleware(self, middleware, next_app):
        """包装底层 ASGI 中间件"""
        async def app(scope, receive, send):
            # 创建中间件实例的副本，设置下一个应用
            middleware.application = next_app
            # 调用中间件
            await middleware(scope, receive, send)

        return app

    async def _handle_request(self, scope, receive, send):
        """处理请求的核心逻辑"""
        request = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request_var.set(request)

        try:
            # 路由匹配
            rule, values = await self._match_route(request)
            mod, handler_cls, handler = self.prepare_request(request, rule)

            # 处理请求
            response = await self._open(request, values)
            await response(scope, receive, send)
        finally:
            # 清理上下文
            request_var.reset(request_token)

# 在 settings.ini 中配置中间件（更新格式）
[MIDDLEWARES]
# 高级中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

**新的中间件开发方式：**

1. **高级中间件接口（推荐）**：
```python
from uliweb import Middleware

class LoggingMiddleware(Middleware):
    """请求日志记录中间件 - 使用高级接口"""

    async def dispatch(self, request, call_next):
        import time
        import logging

        start_time = time.time()
        logging.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logging.info(f"Request completed: {response.status_code} in {process_time:.3f}s")
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logging.error(f"Request failed: {str(e)} in {process_time:.3f}s")
            raise
```

2. **底层 ASGI 中间件接口**：
```python
from uliweb import Middleware
from starlette.responses import Response

class CORSMiddleware(Middleware):
    """CORS 中间件 - 使用底层 ASGI 接口"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        self.allow_origins = settings.get_var('CORS/allow_origins', [])
        self.allow_methods = settings.get_var('CORS/allow_methods', ['GET', 'POST', 'PUT', 'DELETE'])
        self.allow_headers = settings.get_var('CORS/allow_headers', ['*'])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 包装 send 函数以添加 CORS 头
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                # 添加 CORS 头
                headers = message.get("headers", [])
                headers.extend([
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", ", ".join(self.allow_methods).encode()),
                    (b"access-control-allow-headers", ", ".join(self.allow_headers).encode()),
                ])
                message["headers"] = headers
            await send(message)

        # 处理预检请求
        if scope["method"] == "OPTIONS":
            await self.handle_preflight(scope, receive, send_with_cors)
        else:
            await self.application(scope, receive, send_with_cors)

    async def handle_preflight(self, scope, receive, send):
        """处理 CORS 预检请求"""
        response = Response(status_code=204)
        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
        response.headers["access-control-max-age"] = "86400"  # 24小时

        # 构造 ASGI 响应
        await response(scope, receive, send)
```

**配置更新：**

在 `settings.ini` 中配置中间件的方式保持不变，但中间件实现需要更新为纯 ASGI 接口：

```ini
[MIDDLEWARES]
# 高级中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

通过这种方式，我们可以确保中间件系统完全基于 ASGI 架构，不再兼容原有的 WSGI 方式，为 Uliweb 提供更现代、更高效的中间件处理机制。

##### 1. 选择合适的中间件类型

- **使用 BaseHTTPMiddleware**：适用于大多数 HTTP 请求处理场景
- **使用纯 ASGI 中间件**：需要处理 WebSocket、自定义协议或需要更精细控制时

##### 2. 性能优化

```python
class OptimizedMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # 预编译正则表达式
        self.pattern = re.compile(r'pattern')
        # 缓存计算结果
        self.cache = {}

    async def dispatch(self, request, call_next):
        # 快速路径：跳过不必要的处理
        if self.should_skip(request):
            return await call_next(request)

        # 使用缓存
        cache_key = self.get_cache_key(request)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 执行处理逻辑
        response = await call_next(request)
        result = await self.process_response(request, response)

        # 缓存结果
        self.cache[cache_key] = result
        return result
```

##### 3. 错误处理

```python
async def dispatch(self, request, call_next):
    try:
        response = await call_next(request)
        return await self.after_response(request, response)
    except SpecificException as e:
        # 处理特定异常
        return await self.handle_specific_error(request, e)
    except Exception as e:
        # 记录未预期异常
        logger.error(f"Unexpected error in middleware: {e}")
        # 重新抛出或返回通用错误响应
        raise
```

##### 4. 状态管理

使用 `request.state` 在中间件间传递状态：

```python
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 认证用户
        user = await self.authenticate(request)
        if user:
            # 将用户信息存储在 request.state 中
            request.state.user = user

        response = await call_next(request)
        return response

class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 从 request.state 获取用户信息
        user = getattr(request.state, 'user', None)
        if not user:
            return JSONResponse({'error': 'Unauthorized'}, status_code=401)

        # 检查权限
        if not self.check_permission(user, request.url.path):
            return JSONResponse({'error': 'Forbidden'}, status_code=403)

        response = await call_next(request)
        return response
```

通过采用 Starlette 的标准中间件接口，Uliweb3 可以获得更好的性能、更强的功能和更丰富的生态系统支持。同时，Starlette 的中间件系统与 FastAPI 完全兼容，为未来的功能扩展提供了良好的基础。

### 4.6 模板系统异步化

**当前同步模板渲染：**
```python
def template(self, filename, vars=None, env=None, default_template=None, layout=None):
    t = self.template_loader.load(filename, layout=layout,
                                  default_template=default_template)
    return t.generate(vars, env)
```

**异步模板渲染：**
```python
class AsyncTemplateLoader:
    def __init__(self, template_dirs, **kwargs):
        self.template_dirs = template_dirs
        self.template_cache = {}

    async def load_async(self, filename, layout=None, default_template=None):
        """异步加载模板"""
        cache_key = f"{filename}:{layout}:{default_template}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        # 异步查找和读取模板
        template_path = await self.resolve_path_async(filename)
        if not template_path and default_template:
            template_path = await self.resolve_path_async(default_template)

        if not template_path:
            raise TemplateNotFound(f"Template {filename} not found")

        async with aiofiles.open(template_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        # 处理布局
        if layout:
            layout_content = await self.load_layout_async(layout)
            content = layout_content.replace('{{ content }}', content)

        template = AsyncTemplate(content, template_path)
        self.template_cache[cache_key] = template
        return template

async def template(self, filename, vars=None, env=None, default_template=None, layout=None):
    """异步模板渲染"""
    t = await self.template_loader.load_async(filename, layout=layout,
                                             default_template=default_template)
    return await t.generate_async(vars, env)
```

### 4.7 事件分发系统异步化

**异步事件绑定和调用：**
```python
from uliweb.core.dispatch import bind, call, get

# 支持异步处理函数
@bind('init')
async def async_init_handler(sender):
    await some_async_operation()

# 异步调用版本
async def acall(sender, topic, *args, **kwargs):
    """异步调用事件处理函数"""
    if topic not in _receivers:
        return

    for nice, receiver in sorted(_receivers[topic], key=lambda x: x[0]):
        func = receiver['func'] or import_attr(receiver['func_name'])

        if asyncio.iscoroutinefunction(func):
            await func(sender, *args, **kwargs)
        else:
            await anyio.to_thread.run_sync(func, sender, *args, **kwargs)
```

### 4.8 命令系统迁移

**当前基于同步命令处理：**
```python
class Command(object):
    def handle(self, options, global_options, *args):
        """同步命令处理逻辑"""
        # 同步执行命令
        pass
```

**迁移到异步命令处理：**
```python
class AsyncCommand(Command):
    async def handle_async(self, options, global_options, *args):
        """异步命令处理逻辑"""
        # 异步执行命令
        pass

    def handle(self, options, global_options, *args):
        """同步到异步的适配器"""
        import asyncio
        return asyncio.run(self.handle_async(options, global_options, *args))
```

### 4.9 HTML 和 UAML 生成工具迁移

**HTML 生成工具异步支持：**
```python
class AsyncHTMLGenerator:
    async def generate_async(self, data):
        """异步生成 HTML 内容"""
        # 异步处理数据
        processed_data = await process_data_async(data)
        return self.generate(processed_data)

# UAML 解析器异步支持
async def uaml_to_html_async(uaml_text):
    """异步 UAML 到 HTML 转换"""
    # 在线程中运行同步 UAML 解析
    return await anyio.to_thread.run_sync(Parser(uaml_text).run)
```

### 4.10 JSON 编码工具迁移

**JSON 编码异步支持：**
```python
class AsyncJSONEncoder(JSONEncoder):
    async def aencode(self, obj):
        """异步 JSON 编码"""
        # 在线程中运行同步编码
        return await anyio.to_thread.run_sync(self.encode, obj)

async def json_dumps_async(obj, **kwargs):
    """异步 JSON 序列化"""
    encoder = AsyncJSONEncoder(**kwargs)
    return await encoder.aencode(obj)
```

### 4.11 ASGI 处理程序实现

**旧的 WSGI 处理程序：**
```python
import sys, os

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from uliweb.manage import make_simple_application
application = make_simple_application(project_dir=path)
```

**迁移到纯 ASGI 处理程序：**
```python
import sys, os
import asyncio
from uliweb.manage import make_application
from uliweb.core.SimpleFrame import AsyncDispatcher

# 将项目目录添加到 sys.path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

**实际实现（与规划一致但更完整）：**
```python
class ASGIApplication:
    """纯 ASGI 应用处理器"""

    def __init__(self, project_dir=None):
        self.project_dir = project_dir
        self.asgi_app = None
        self._initialized = False

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            # 处理 project_dir 为 None 的情况
            if self.project_dir is None:
                # 尝试获取当前工作目录作为默认项目目录
                self.project_dir = os.getcwd()

            # 创建 ASGI Dispatcher
            self.asgi_app = AsyncDispatcher(
                apps_dir=os.path.join(self.project_dir, 'apps'),
                project_dir=self.project_dir
            )
            self._initialized = True

    async def __call__(self, scope, receive, send):
        """ASGI 接口"""
        self._initialize()
        await self.asgi_app(scope, receive, send)

# 创建应用实例
application = ASGIApplication(project_dir=path)

# 创建应用的便捷函数
def create_application():
    """创建 ASGI 应用"""
    return ASGIApplication(project_dir=path)
```


**实际实现的关键特性：**

基于 `starlette.py` 的实际实现，Uliweb 的 Starlette 集成具有以下特点：

1. **完全兼容现有 Uliweb 架构**：保持与 SimpleFrame.py 相同的接口和设计模式
2. **渐进式迁移支持**：可以逐步将现有应用迁移到 ASGI
3. **保持现有配置系统**：继续使用现有的 settings.ini 配置机制
4. **模板系统兼容**：继续使用 Uliweb 的模板系统，支持异步渲染
5. **路由系统适配**：将 Werkzeug 风格路由转换为 Starlette 风格

6. **完整的模板渲染支持**：支持 Uliweb 模板系统的异步渲染
7. **中间件系统兼容**：支持现有的 Uliweb 中间件架构
8. **错误处理机制**：提供完整的异常处理和错误页面支持
9. **CORS 支持**：内置 CORS 跨域请求支持
10. **WebSocket 支持**：完整的 WebSocket 协议支持

**实际实现与规划的主要差异：**

1. **配置系统保持同步**：实际实现中配置加载仍然使用同步方式，通过协程池处理
2. **模板渲染使用协程池**：模板系统继续使用 Uliweb 的同步模板，通过 `run_in_executor` 在协程池中异步执行，而非真正的异步 I/O
3. **中间件系统简化**：实际实现采用更直接的中间件处理方式
4. **路由匹配优化**：实现了更精确的路由匹配算法，支持参数提取
5. **错误处理增强**：提供了更完善的异常处理和调试信息

**使用方式：**
- 使用 ASGI 服务器如 Uvicorn、Hypercorn、Daphne 运行应用
- 不再支持 WSGI 服务器
- 尽量保持与现有 Uliweb 项目的兼容性
- 可以逐步将应用迁移到 ASGI

## 5. Settings 配置迁移策略

### 5.1 现有 Settings 系统分析

基于 `manage.py` 和 `uliweb/core/SimpleFrame.py` 的分析，Uliweb 当前的 settings 系统具有以下特点：

**配置加载流程：**
1. 从环境变量获取 `SETTINGS` 和 `LOCAL_SETTINGS` 文件名
2. 按顺序加载：默认配置 → 应用配置 → 项目配置 → 本地配置
3. 支持 `default_settings` 参数进行运行时配置覆盖

**关键配置项：**
- `DEBUG`: 调试模式开关
- `MIDDLEWARES`: ASGI 中间件配置
- `TEMPLATE`: 模板系统配置
- `URL`: URL 路由映射
- `DATABASES`: 数据库配置
- `GLOBAL_OBJECTS`: 全局对象注册

### 5.2 ASGI Settings 迁移方案

**实际配置加载实现：**

基于 `starlette.py` 的实际实现，配置系统保持与现有 Uliweb 的兼容性：

```python
async def _load_settings(self):
    """异步加载设置"""
    from uliweb.core.SimpleFrame import get_settings as get_sync_settings

    # 处理 project_dir 为 None 的情况
    project_dir = self.project_dir
    if project_dir is None:
        project_dir = os.getcwd()

    # 使用协程池执行同步的 settings 加载
    loop = asyncio.get_event_loop()
    settings = await loop.run_in_executor(
        None,
        get_sync_settings,
        project_dir,
        self.include_apps,
        self.settings_file,
        self.local_settings_file,
        self.default_settings
    )

    return settings
```

**实际实现特点：**
1. **保持同步配置系统**：继续使用 Uliweb 的同步配置加载机制
2. **协程池异步化**：通过 `asyncio.run_in_executor` 将同步操作异步化
3. **完全兼容现有配置**：支持现有的 settings.ini 和 local_settings.ini
4. **环境变量支持**：保持 `SETTINGS` 和 `LOCAL_SETTINGS` 环境变量支持

**实际中间件处理：**

实际实现采用更直接的中间件处理方式，而不是复杂的适配器模式：

```python
async def _process_middleware(self, request, response, mod, handler_cls, handler, values):
    """异步处理中间件"""
    # 处理请求中间件
    for middleware in self.process_request_classes:
        middleware_instance = middleware(self, self.settings)
        if hasattr(middleware_instance, 'process_request'):
            middleware_response = await self._call_middleware_method(
                middleware_instance.process_request, request
            )
            if middleware_response is not None:
                return middleware_response

    # 调用视图函数
    try:
        view_response = await self.call_view(mod, handler_cls, handler, request, response, kwargs=values)
    except Exception as e:
        # 处理异常中间件
        for middleware in self.process_exception_classes:
            middleware_instance = middleware(self, self.settings)
            if hasattr(middleware_instance, 'process_exception'):
                exception_response = await self._call_middleware_method(
                    middleware_instance.process_exception, request, e
                )
                if exception_response is not None:
                    return exception_response
        raise

    # 处理响应中间件
    for middleware in self.process_response_classes:
        middleware_instance = middleware(self, self.settings)
        if hasattr(middleware_instance, 'process_response'):
            view_response = await self._call_middleware_method(
                middleware_instance.process_response, request, view_response
            )

    return view_response
```

**实际路由匹配实现：**

实际实现提供了更精确的路由匹配算法：

```python
async def _match_route(self, request):
    """异步路由匹配"""
    # 使用更直接的路由匹配方法
    path = request.url.path
    method = request.method

    # 收集所有匹配的路由
    matched_routes = []

    # 遍历所有路由进行匹配
    for route in self.router.routes:
        if hasattr(route, 'path'):
            # 对于 Starlette Route 对象，使用更直接的方法
            try:
                route_path = route.path
                route_methods = getattr(route, 'methods', ['GET'])

                # 检查路径是否匹配
                path_matches = self._path_matches(route_path, path)

                if path_matches:
                    # 检查方法是否匹配
                    if hasattr(route, 'methods'):
                        if method in route.methods:
                            # 提取路径参数
                            path_params = self._extract_path_params(route_path, path)
                            matched_routes.append((route, path_params))
                    else:
                        # 如果没有指定方法，默认匹配 GET
                        if method == 'GET':
                            path_params = self._extract_path_params(route_path, path)
                            matched_routes.append((route, path_params))
            except Exception:
                # 如果匹配出错，继续尝试下一个路由
                continue

    # 如果有多个匹配的路由，选择最具体的那个
    if matched_routes:
        # 按路径长度排序，最长的路径最具体
        matched_routes.sort(key=lambda x: len(x[0].path), reverse=True)
        selected_route = matched_routes[0]
        return selected_route

    # 如果没有匹配到路由，抛出 404 异常
    from starlette.exceptions import HTTPException
    raise HTTPException(status_code=404)
```

## 6. 技术挑战与解决方案

### 6.1 同步到异步的迁移（同步适配器机制）

**问题：** 现有代码库大量使用同步代码，直接迁移会导致"大爆炸式"重写

**解决方案：引入同步适配器机制**

**框架层同步适配器实现：**
```python
class AsyncDispatcher:
    """支持同步视图函数自动适配的异步 Dispatcher"""

    async def _call_view_function(self, func, request, *args, **kwargs):
        """智能调用视图函数，支持同步和异步函数"""
        if asyncio.iscoroutinefunction(func):
            # 异步函数直接调用
            return await func(request, *args, **kwargs)
        else:
            # 同步函数在线程池中执行，避免阻塞事件循环
            return await anyio.to_thread.run_sync(func, request, *args, **kwargs)

    async def _handle_sync_request_data(self, request):
        """为同步函数预加载请求数据"""
        # 在调用同步函数前，预加载所有需要的异步数据
        if request.method == "POST":
            # 预加载 POST 数据，避免同步函数中调用异步方法
            request._cached_post_data = await request.get_POST()
            request._cached_files_data = await request.get_FILES()

        # 预加载 JSON 数据
        if request.headers.get('content-type', '').startswith('application/json'):
            request._cached_json_data = await request.get_json()

        return request

    async def _open(self, request):
        """处理请求的核心方法，包含同步适配逻辑"""
        # 预加载请求数据
        request = await self._handle_sync_request_data(request)

        # 路由匹配和视图函数调用
        # ... 其他逻辑

        # 调用视图函数
        response = await self._call_view_function(view_func, request, **kwargs)
        return response
```

**同步适配器的优势：**
1. **渐进式迁移**：现有同步代码无需立即重写，可以逐步迁移
2. **性能平衡**：同步函数在独立线程中执行，不阻塞事件循环
3. **兼容性保证**：支持混合使用同步和异步代码
4. **开发友好**：降低迁移门槛，减少停机时间

**同步适配器的使用场景：**
```python
# 场景1：现有同步视图函数（无需修改）
@expose('/legacy/sync-view')
def legacy_sync_view():
    # 这个函数会被框架自动适配为异步执行
    # 注意：在同步函数中不能直接调用异步方法
    # 应该使用预加载的数据或重构为异步

    # 错误示例：
    # data = await request.get_POST()  # ❌ 同步函数中不能使用 await

    # 正确做法1：使用预加载的数据
    if hasattr(request, '_cached_post_data'):
        post_data = request._cached_post_data

    # 正确做法2：重构为异步函数
    return {"status": "legacy sync function"}

# 场景2：新的异步视图函数（推荐）
@expose('/new/async-view')
async def new_async_view():
    # 可以直接使用异步方法
    post_data = await request.get_POST()
    json_data = await request.get_json()
    return {"status": "new async function"}

# 场景3：混合使用（过渡期）
@expose('/mixed/view')
async def mixed_view():
    # 可以调用现有的同步业务逻辑
    sync_result = await anyio.to_thread.run_sync(sync_business_logic, data)
    # 同时使用新的异步功能
    async_result = await async_operation(data)
    return {"sync": sync_result, "async": async_result}
```

**同步适配器的配置选项：**
```python
# 在 settings.ini 中配置同步适配器行为
[ASGI]
# 同步函数线程池大小
SYNC_THREAD_POOL_SIZE = 20
# 是否启用请求数据预加载
PRELOAD_REQUEST_DATA = true
# 同步函数超时时间（秒）
SYNC_FUNCTION_TIMEOUT = 30
# 是否记录同步适配器使用情况
LOG_SYNC_ADAPTER_USAGE = true
```

### 6.2 全局状态管理

**问题：** Uliweb 使用 `werkzeug.local` 进行线程局部存储

**解决方案：**
1. 使用 `contextvars` 替代 `threading.local`
2. 实现请求上下文管理
3. 保持向后兼容的代理对象

### 6.3 URL 路由兼容性

**问题：** Werkzeug 和 Starlette 路由语法差异

**解决方案：**
1. 创建路由适配器层
2. 保持现有 `@expose` 装饰器接口不变
3. 内部映射到 Starlette 路由系统

## 7. 性能优化机会

### 7.1 异步 I/O 操作
- 数据库查询异步化
- 文件操作异步化
- 外部 API 调用异步化

### 7.2 并发处理能力
- 利用 ASGI 的并发特性
- 支持更多并发连接
- 更好的资源利用率

### 7.3 WebSocket 支持
- 实时通信功能
- 双向数据流
- 服务器推送能力

```python
@expose('/ws', websocket=True)
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

## 8. 实际实现状态总结

### 8.1 已实现的功能
基于 `starlette.py` 的实际实现，以下功能已经完成：

1. **ASGI 接口实现**：完整的 ASGI 3.0 接口支持
2. **Request/Response 对象**：基于 Starlette 的异步请求/响应对象
3. **路由系统**：支持 Werkzeug 风格路由到 Starlette 路由的转换
4. **模板渲染**：支持 Uliweb 模板系统的异步渲染
5. **中间件系统**：兼容现有 Uliweb 中间件架构
6. **错误处理**：完整的异常处理和错误页面支持
7. **CORS 支持**：内置跨域请求支持
8. **WebSocket 支持**：完整的 WebSocket 协议支持
9. **配置系统**：保持与现有 Uliweb 配置系统的兼容性
10. **Profile 性能分析**：已迁移到 ASGI 方式（参考 uliweb/asgi/profile.py）

### 8.2 实际实现特点
1. **渐进式迁移**：支持逐步将现有应用迁移到 ASGI
2. **兼容性优先**：保持与现有 Uliweb 项目的完全兼容
3. **性能优化**：通过协程池实现同步到异步的平滑过渡
4. **开发友好**：提供详细的错误信息和调试支持

### 8.3 使用方式
- **运行方式**：使用 ASGI 服务器如 Uvicorn、Hypercorn、Daphne
- **配置兼容**：继续使用现有的 settings.ini 配置
- **代码兼容**：保持现有的 @expose 装饰器和视图函数接口
- **渐进迁移**：可以逐步将应用迁移到 ASGI

## 9. 迁移检查清单

### 核心组件迁移状态
- [x] Request/Response 对象迁移（基于 Starlette 实现）
- [x] Dispatcher 类重构（ASGI 接口实现）
- [x] URL 路由系统迁移（路由适配器实现）
- [x] 全局状态管理迁移（contextvars 实现）
- [x] 中间件系统适配（兼容现有中间件）
- [x] 模板系统异步化（协程池异步渲染）
- [x] 错误处理机制（完整异常处理）
- [x] WebSocket 支持（完整协议支持）

### 功能组件迁移状态
- [x] HTML 生成工具支持（保持兼容）
- [x] JSON 编码工具支持（保持兼容）
- [x] 静态文件服务（兼容现有机制）
- [x] 文件上传下载（异步化支持）
- [x] CORS 支持（内置实现）
- [x] 会话管理迁移（已实现异步适配，参考 uliweb/contrib/session/middle_session.py）
- [x] 认证系统迁移（已实现异步适配，参考 uliweb/contrib/auth/middle_auth.py）
- [ ] 数据库连接异步化（TODO: 当前使用同步 SQLAlchemy，通过协程池异步化）
- [ ] 缓存系统异步化（TODO: 当前使用同步缓存后端，需要异步适配器）

### 测试验证状态
- [x] 单元测试支持（异步测试用例）
- [x] 集成测试验证（端到端功能测试）
- [x] 兼容性测试（现有项目验证）
- [x] WebSocket 功能测试（协议测试）
- [ ] 性能测试对比（TODO: 并发性能测试）
- [ ] 压力测试和负载测试（TODO: 大规模测试）

## 10. 总结和最佳实践

### 改进方案总结

**核心改进点：**

1. **同步适配器机制**：解决了"大爆炸式"迁移问题，支持现有同步代码平滑过渡
2. **强制异步化接口**：避免了 async property 兼容性陷阱，采用明确的异步方法
3. **渐进式迁移策略**：支持外部异步、内部同步的架构，降低迁移风险

**技术架构改进：**

- **Request/Response 对象**：修复了 async property 陷阱，改为明确的异步方法
- **Dispatcher 类**：内置同步适配器，自动处理同步/异步视图函数
- **中间件系统**：采用纯 ASGI 接口，简化架构并提升性能
- **状态管理**：使用 contextvars 替代 threading.local，支持异步环境

### 迁移收益
1. **性能提升**：异步处理能力，支持更高并发
2. **功能增强**：WebSocket、Server-Sent Events 等现代功能
3. **生态整合**：更好的 Python 异步生态集成
4. **未来兼容**：符合现代 Web 标准和发展趋势
5. **平滑迁移**：同步适配器机制支持渐进式升级

### 最佳实践

**迁移策略最佳实践：**

1. **渐进式迁移**：
   - 先在小规模项目中试点，验证同步适配器机制
   - 逐步将关键路径迁移到异步，保持业务连续性
   - 使用混合模式过渡，逐步减少同步代码比例

2. **代码重构指导**：
   - 优先重构高并发、I/O 密集的视图函数为异步
   - 保持现有同步代码，利用同步适配器机制
   - 避免在同步函数中调用异步方法，使用预加载数据

3. **测试验证策略**：
   - 单元测试：验证同步/异步函数在适配器中的行为
   - 集成测试：确保混合模式下的功能完整性
   - 性能测试：对比迁移前后的性能表现

**开发最佳实践：**

1. **异步代码编写**：
   ```python
   # 推荐：明确的异步方法调用
   post_data = await request.get_POST()
   json_data = await request.get_json()

   # 避免：使用已弃用的同步属性
   # post_data = request.POST  # ❌ 会抛出异常
   ```

2. **同步代码适配**：
   ```python
   # 现有同步代码可以继续使用
   @expose('/legacy/view')
   def legacy_view():
       # 框架会自动适配为异步执行
       # 注意：不能直接调用异步方法
       return {"status": "legacy function"}
   ```

3. **混合模式开发**：
   ```python
   @expose('/mixed/view')
   async def mixed_view():
       # 可以混合使用同步和异步代码
       sync_result = await anyio.to_thread.run_sync(sync_function)
       async_result = await async_function()
       return {"sync": sync_result, "async": async_result}
   ```

### 注意事项

**技术注意事项：**

1. **线程安全**：在异步环境中使用同步函数时注意线程安全问题
2. **上下文管理**：确保事件处理函数能够正确访问请求上下文
3. **依赖管理**：异步事件处理可能依赖其他异步服务，需要妥善管理
4. **错误处理**：为异步操作添加适当的错误处理和重试机制

**迁移注意事项：**

1. **兼容性保证**：同步适配器机制确保现有代码继续工作
2. **性能监控**：同步函数在线程池中执行，需要监控线程池使用情况
3. **资源管理**：预加载请求数据会增加内存使用，需要合理配置
4. **调试支持**：同步/异步混合模式需要更好的调试工具支持

**配置优化建议：**

```ini
[ASGI]
# 同步适配器配置优化
SYNC_THREAD_POOL_SIZE = 20        # 根据并发需求调整
PRELOAD_REQUEST_DATA = true       # 启用数据预加载
SYNC_FUNCTION_TIMEOUT = 30        # 同步函数超时时间
LOG_SYNC_ADAPTER_USAGE = true     # 记录适配器使用情况

[GLOBAL]
DEBUG = true                      # 开发阶段启用调试模式
```

### 迁移时间线建议

**阶段一（1-2个月）：基础架构迁移**
- 部署新的 ASGI 架构
- 验证同步适配器机制
- 培训开发团队

**阶段二（2-4个月）：功能迁移**
- 逐步迁移关键业务逻辑到异步
- 优化性能敏感路径
- 完善测试覆盖

**阶段三（4-6个月）：性能优化**
- 全面异步化优化
- 性能调优和监控
- 生产环境验证

**阶段四（长期）：生态完善**
- 贡献插件异步化
- 社区生态建设
- 持续优化和改进

### 实际实现验证
基于 `starlette.py` 的实际实现已经验证了以下关键功能：
- ASGI 3.0 接口的完整实现
- 与现有 Uliweb 项目的兼容性
- 异步模板渲染的性能优化
- WebSocket 协议的支持
- 错误处理和调试信息的完善

### 关于 Scope 状态管理的特别说明

**Scope 状态管理是 ASGI 架构的核心优势：**

1. **统一的状态传递机制**：`scope['state']` 提供了标准化的状态容器，避免了 WSGI 中通过 `request` 对象属性传递状态的混乱
2. **类型安全**：通过明确的键名约定，确保状态对象的类型安全
3. **中间件协作**：不同中间件可以通过 `scope['state']` 进行协作，实现复杂的功能组合
4. **性能优化**：避免了不必要的对象属性访问，直接通过字典键访问状态

**推荐的中间件开发模式：**

```python
class MyMiddleware(Middleware):
    async def __call__(self, scope, receive, send):
        # 1. 初始化状态容器
        if 'state' not in scope:
            scope['state'] = {}

        # 2. 设置中间件状态
        scope['state']['my_middleware'] = self._initialize_state()

        # 3. 处理请求
        try:
            await self.application(scope, receive, send)
        except Exception as e:
            # 4. 异常处理
            await self._handle_exception(scope, send, e)

    def _initialize_state(self):
        """初始化中间件状态"""
        return {"initialized_at": datetime.now()}

    async def _handle_exception(self, scope, send, exception):
        """异常处理逻辑"""
        # 使用 scope 中的状态信息进行错误处理
        pass
```

**状态管理的未来扩展性：**

1. **类型化状态**：未来可以考虑使用 TypedDict 或 dataclass 来定义状态结构
2. **状态验证**：添加状态验证机制，确保中间件设置的状态符合预期格式
3. **状态监控**：实现状态监控和调试工具，便于开发调试
4. **状态持久化**：支持状态在不同请求间的持久化（如会话状态）

通过这个完整的迁移方案，可以确保 Uliweb 从 Werkzeug 到 Starlette 的迁移过程中所有关键组件都被妥善处理，实现纯 ASGI 架构。特别是 Scope 状态管理机制的引入，为 Uliweb 提供了更现代化、更高效的状态管理方式。
