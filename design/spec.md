# Spec：Uliweb ASGI 迁移（需求与设计规格）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。生成提示词见文件末尾。
-->

---
类型: spec
来源: intent.md
状态: approved        <!-- 审阅通过 → approved，触发 Stage 3 plan mode -->
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

> 所有代码实现均位于 `uliweb/core/SimpleFrame.py`，而非独立的 `starlette.py` 文件。

### 3.2 架构对比

| 组件 | 原有 WSGI（Werkzeug） | 目标 ASGI（Starlette） |
|------|-----------|-----------|
| Request/Response | 继承 `werkzeug.Request/Response` | 继承 `starlette.requests.Request` 等 |
| URL 路由 | `werkzeug.routing.Map/Rule` | Starlette `Router/Route`（Werkzeug 风格转 Starlette 风格） |
| 应用 | `Dispatcher.__call__(environ, start_response)` | `AsyncDispatcher.__call__(scope, receive, send)` |
| 中间件 | WSGI 中间件链 | 纯 ASGI 中间件（高级 `dispatch` + 底层 `__call__`） |
| 全局状态 | `werkzeug.local.Local`（threading.local） | `LocalProxy`（contextvars / 普通全局） |

**核心文件依赖：** `uliweb/core/SimpleFrame.py`（核心分发器）、`uliweb/wsgi/*`（WSGI 工具，最终移除）。

### 3.3 迁移阶段

1. **阶段一 基础架构**：Request/Response、ASGI 接口（含同步适配器）、基本路由。
2. **阶段二 功能完整性**：中间件、模板、会话异步化。
3. **阶段三 性能优化**：WebSocket、异步数据库/缓存适配。
4. **阶段四 生态兼容**：插件适配、文档、统一导出接口。
5. **阶段五 完全移除 WSGI**：移除 werkzeug 依赖。

### 3.4 Request/Response 对象设计

**旧实现（Werkzeug）：**
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

**新实现（修复 async property 陷阱）：**
```python
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile
import json as jsn

class Request(StarletteRequest):
    """基于 Starlette 的 Request 类，修复兼容性陷阱"""

    @property
    def GET(self):
        return self.query_params

    @property
    def state(self):
        if 'state' not in self.scope:
            self.scope['state'] = {}
        return self.scope['state']

    async def get_POST(self):
        if self.method == "POST":
            form = await self.form()
            return form
        return {}

    async def get_FILES(self):
        if self.method == "POST":
            form = await self.form()
            return {k: v for k, v in form.items() if isinstance(v, UploadFile)}
        return {}

    async def get_json(self):
        import json as jsn
        body = await self.get_data()
        return jsn.loads(body)

    async def get_data(self):
        """返回原始请求体字节；表单解析会消费流"""
        return await self.body()

    async def get_params(self):
        get_params = self.query_params
        post_params = await self.get_POST()
        merged_params = {}
        merged_params.update(get_params)
        merged_params.update(post_params)
        return merged_params

    @property
    def is_xhr(self):
        return self.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'

    @property
    def path(self):
        return self.url.path

    @property
    def method(self):
        return self.scope.get("method", "")

    # 向后兼容的同步属性（已弃用，访问抛异常）
    @property
    def POST(self):
        raise RuntimeError("POST 属性已弃用，请使用 await request.get_POST() 方法。")

    @property
    def FILES(self):
        raise RuntimeError("FILES 属性已弃用，请使用 await request.get_FILES() 方法。")

    @property
    def json(self):
        raise RuntimeError("json 属性已弃用，请使用 await request.get_json() 方法。")

    @property
    def data(self):
        raise RuntimeError("data 属性已弃用，请使用 await request.get_data() 方法。")

    @property
    def params(self):
        return self.query_params

class Response(StarletteResponse):
    """基于 Starlette 的 Response 类，保持与现有 Uliweb 的兼容性"""
    def write(self, value):
        pass
```

**request.data 迁移对照表：**

| WSGI 用法 | ASGI 用法 |
|-----------|-----------|
| `request.data` | `await request.get_data()` |
| `json.loads(request.data)` | `await request.get_json()` |
| `request.POST` | `await request.get_POST()` |
| `request.FILES` | `await request.get_FILES()` |
| `request.params` | `await request.get_params()` |

**兼容性改进要点：**
1. 避免 async property 陷阱：改用明确异步方法 `get_POST()/get_FILES()/get_json()`
2. 修复递归调用错误：`await super().json()` 而非 `await self.json()`
3. 强制异步化：`params` 改为 `get_params()`
4. 明确弃用策略：保留同步属性但抛异常引导迁移
5. 同步适配器支持：框架层自动同步→异步适配
6. 新增 `request.state` 请求级状态容器

### 3.5 Dispatcher 类设计

**旧 WSGI 接口：**
```python
class Dispatcher(object):
    def __call__(self, environ, start_response):
        response = self._open(environ)
        return response(environ, start_response)
```

**新实现（AsyncDispatcher）：**
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
        self._middleware_stack = None
        self.route_param_types = {}

    async def _async_init(self):
        if not self._initialized:
            await self.init()
            await self._init_routes()
            self._initialized = True

    async def __call__(self, scope, receive, send):
        if not self._initialized:
            await self._async_init()
        app = await self._build_middleware_stack()
        await app(scope, receive, send)

    async def handle_http(self, scope, receive, send):
        if not self._initialized:
            await self._async_init()
        request = Request(scope, receive, send)
        request_token = request_var.set(request)
        try:
            response = await self._open(request)
            await response(scope, receive, send)
        finally:
            request_var.reset(request_token)

    async def handle_websocket(self, scope, receive, send):
        from starlette.websockets import WebSocket
        websocket = WebSocket(scope, receive, send)
        websocket_token = request_var.set(websocket)
        try:
            await websocket.accept()
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                await self._handle_websocket_message(websocket, message)
        finally:
            request_var.reset(websocket_token)
```

### 3.6 URL 路由系统设计

将 Werkzeug 风格路由转换为 Starlette 风格，`UliwebRouter` 提供 `add_route` / `add_websocket_route` / `mount` / `bind` / `build` 等接口，并支持 `url_for` 反向 URL 生成、域名配置、外部链接、格式化与应用别名映射。

**参数转换：**
```python
def _convert_route_param(rule):
    """处理 <type:name> 格式
    例如: '/api/users/<int:user_id>' -> ('/api/users/{user_id}', {'user_id': 'int'})
    """
    param_types = {}
    def replacer(m):
        param = m.group(1)
        if ':' in param:
            param_type, param_name = param.split(':', 1)
            param_types[param_name] = param_type
            return '{' + param_name + '}'
        else:
            return '{' + param + '}'
    converted_rule = re.sub(r'<([^>]+)>', replacer, rule)
    return converted_rule, param_types
```

**路由收集 `_merge_rules()`**：合并所有应用路由，按时间戳排序、处理 URL 名称映射、合并重复规则、支持 HTTP 方法过滤。

**`url_for(endpoint, **values)`**：根据 endpoint 生成 URL，支持 `_domain_name`、`_external`、`_format`、应用别名映射。

### 3.7 全局状态管理设计

采用 `LocalProxy` 统一管理全局状态，支持两种存储方式：普通全局变量（settings/application）与 contextvars（request/response，通过 `use_contextvars=True`）。

**ASGI 环境下的定义：**
```python
from uliweb.utils.localproxy import LocalProxy, Global

# request/response 使用 contextvars（每协程独立）；settings/application 使用普通全局（全局一致）
request = LocalProxy('request', use_contextvars=True)
response = LocalProxy('response', use_contextvars=True)
settings = LocalProxy('settings', use_contextvars=False)
application = LocalProxy('application', use_contextvars=False)

__global__ = Global()
__global__.settings = pyini.Ini(lazy=True)
settings.set(__global__.settings)
```

**与 WSGI 版本对比：**

| 方面 | WSGI 版本 | ASGI 版本 |
|------|-----------|-----------|
| settings | LocalProxy (threading.local) | LocalProxy (普通全局, use_contextvars=False) |
| application | LocalProxy (threading.local) | LocalProxy (普通全局, use_contextvars=False) |
| request | LocalProxy (threading.local) | LocalProxy (contextvars, use_contextvars=True) |
| response | LocalProxy (threading.local) | LocalProxy (contextvars, use_contextvars=True) |

**设计优势：** 统一接口、灵活配置、默认兼容、ASGI 简化、唯一真实变量。
**注意事项：** settings/application 全局一致；协程隔离用 `use_contextvars=True`；使用前必须先初始化 Dispatcher；未初始化访问抛 `RuntimeError`。

### 3.8 中间件系统设计

中间件系统采用更适合 ASGI 的接口，仿照 Starlette 的两种方式，但使用 Uliweb 自己的中间件接口（只支持 ASGI 方式）：

1. **高级中间件接口（推荐）**：`async def dispatch(self, request, call_next):`
2. **底层 ASGI 中间件接口**：`async def __call__(self, scope, receive, send):`

**配置（settings.ini）：**
```ini
[MIDDLEWARES]
# 高级中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

**SimpleFrame 中间件重设计（核心实现）：**
```python
class Middleware(object):
    """纯 ASGI 中间件基类"""
    def __init__(self, application, settings):
        self.application = application
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return
        await self.process_request(scope)
        try:
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope): pass
    async def handle_exception(self, scope, receive, send, exception): raise exception
    async def dispatch(self, request, call_next):
        return await call_next(request)
```

**中间件链构建（`_build_middleware_stack`）**：从内到外包装应用，按配置逆序添加；通过 `hasattr(instance, 'dispatch')` 区分高级/底层接口，支持两种接口混合；兼容传统 `process_request/process_response/process_exception`（在 `_process_middleware` 中按序/逆序调用并经协程池异步执行）。

**执行顺序：** A Before → B Before → C Before → 应用处理 → C After → B After → A After。

**中间件开发最佳实践：** 大多数场景用高级接口；需 WebSocket/精细控制用底层 ASGI；预编译正则与缓存优化性能；`request.state` 在中间件间传递状态。

> **教程**：内置中间件、自定义/纯 ASGI/常用中间件（认证、限流、校验、响应格式化等）的完整示例代码与最佳实践见 `docs/zh_CN/02_core_concepts/middleware.md`（§ASGI 中间件开发）。

### 3.9 模板系统设计

提供 `AsyncTemplateLoader.load_async` + `generate_async` 异步渲染；实际实现中 Uliweb 模板系统通过协程池（`run_in_executor`）异步执行同步渲染。

### 3.10 事件分发系统设计

```python
@bind('init')
async def async_init_handler(sender):
    await some_async_operation()

async def acall(sender, topic, *args, **kwargs):
    if topic not in _receivers:
        return
    for nice, receiver in sorted(_receivers[topic], key=lambda x: x[0]):
        func = receiver['func'] or import_attr(receiver['func_name'])
        if asyncio.iscoroutinefunction(func):
            await func(sender, *args, **kwargs)
        else:
            await anyio.to_thread.run_sync(func, sender, *args, **kwargs)
```

### 3.11 命令系统设计

```python
class AsyncCommand(Command):
    async def handle_async(self, options, global_options, *args): pass
    def handle(self, options, global_options, *args):
        import asyncio
        return asyncio.run(self.handle_async(options, global_options, *args))
```

### 3.12 HTML/UAML 与 JSON 工具设计

- HTML 生成：`AsyncHTMLGenerator.generate_async`。
- UAML 解析：`uaml_to_html_async` 经 `anyio.to_thread.run_sync(Parser(uaml_text).run)`。
- JSON 编码：`AsyncJSONEncoder.aencode` 经 `anyio.to_thread.run_sync`；`json_dumps_async`。

### 3.13 Settings 配置迁移设计

**现有系统分析：** 从环境变量取 `SETTINGS`/`LOCAL_SETTINGS` 文件名；按顺序加载 默认→应用→项目→本地；支持 `default_settings` 运行时覆盖。关键配置项：`DEBUG`、`MIDDLEWARES`、`TEMPLATE`、`URL`、`DATABASES`、`GLOBAL_OBJECTS`。

**ASGI 迁移方案：** 保持同步配置系统，经 `asyncio.run_in_executor` 异步化 `_load_settings`；实际中间件处理采用直接的 `_process_middleware`（请求/异常/响应三段）；实际路由匹配采用更精确的 `_match_route`（按路径长度选择最具体路由，未匹配抛 404）。

### 3.14 技术挑战与解决方案

**同步→异步迁移（同步适配器机制）：**
```python
async def _call_view_function(self, func, request, *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
        return await func(request, *args, **kwargs)
    else:
        return await anyio.to_thread.run_sync(func, request, *args, **kwargs)

async def _handle_sync_request_data(self, request):
    if request.method == "POST":
        request._cached_post_data = await request.get_POST()
        request._cached_files_data = await request.get_FILES()
    if request.headers.get('content-type', '').startswith('application/json'):
        request._cached_json_data = await request.get_json()
    return request
```
优势：渐进式迁移、性能平衡、兼容性保证、开发友好。三种使用场景：现有同步视图（无需修改）、新异步视图（推荐）、混合模式（过渡期）。配置项：`SYNC_THREAD_POOL_SIZE` / `PRELOAD_REQUEST_DATA` / `SYNC_FUNCTION_TIMEOUT` / `LOG_SYNC_ADAPTER_USAGE`。

**全局状态管理：** 用 contextvars 替代 threading.local，实现请求上下文管理，保持向后兼容代理对象。

**URL 路由兼容性：** 创建路由适配器层，保持 `@expose` 接口不变，内部映射到 Starlette 路由。

### 3.15 性能优化机会

- **异步 I/O 操作**：数据库查询、文件操作、外部 API 调用异步化。
- **并发处理能力**：利用 ASGI 并发特性，支持更多并发连接与更好资源利用率。
- **WebSocket 支持**：实时通信、双向数据流、服务器推送。

```python
@expose('/ws', websocket=True)
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

### 3.16 ASGI 处理程序设计

**旧 WSGI 处理程序：**
```python
import sys, os

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from uliweb.manage import make_simple_application
application = make_simple_application(project_dir=path)
```

**新实现（ASGIApplication 单例模式）：**
```python
import sys, os
from uliweb.manage import make_application
from uliweb.core.SimpleFrame import AsyncDispatcher

# 将项目目录添加到 sys.path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

class ASGIApplication:
    """纯 ASGI 应用处理器（单例模式）"""

    _instance = None
    _instance_project_dir = None
    _instance_asgi_app = None

    def __new__(cls, project_dir=None):
        # 单例模式：只创建一次实例
        if cls._instance is None or cls._instance_project_dir != project_dir:
            cls._instance = super(ASGIApplication, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance_project_dir = project_dir
        return cls._instance

    def __init__(self, project_dir=None):
        self.project_dir = project_dir

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            if self.project_dir is None:
                self.project_dir = os.getcwd()
            ASGIApplication._instance_asgi_app = AsyncDispatcher(
                apps_dir='apps',
                project_dir=self.project_dir
            )
            self._initialized = True

    async def __call__(self, scope, receive, send):
        """ASGI 接口"""
        self._initialize()
        await ASGIApplication._instance_asgi_app(scope, receive, send)

# 创建应用实例
application = ASGIApplication(project_dir=path)

# 创建应用的便捷函数
def create_application():
    """创建 ASGI 应用"""
    return ASGIApplication(project_dir=path)
```

**关键特性：** 完全兼容现有架构；渐进式迁移；保持 `settings.ini` 配置；模板经协程池异步渲染；Werkzeug→Starlette 路由适配；兼容中间件；完整错误处理；内置 CORS；WebSocket 支持。

**与原规划的主要差异：** 所有代码位于 `SimpleFrame.py`（无独立 `starlette.py`）；配置加载保持同步（协程池处理）；模板渲染用协程池；中间件简化（直接处理，支持传统+ASGI 接口）；路由匹配优化（更精确，支持参数提取）；错误处理增强。

### 3.17 类视图方法 auto-register 语义修正

**现状问题**（详见 [intent.md](#) §问题 第 3 条）：

```python
@expose('/gateway/agents')
class AgentView:
    def get(self, agent_id):        ...   # → /gateway/agents/get/{agent_id}
    def delete(self, agent_id):     ...   # → /gateway/agents/delete/{agent_id}
    def regenerate_key(self, id):   ...   # → /gateway/agents/regenerate_key/{id}
```

`parse_class`（[rules.py:246](uliweb/core/rules.py#L246)）对类所有 public 方法无差别注册；相对路径 = 方法名 + / + 参数（[rules.py:364-366](uliweb/core/rules.py#L364-L366)）。这与 Flask `MethodView` / Django CBV / FastAPI 习惯**不一致**，且与方法级 `@expose('/<int:id>')` 装饰器**叠加**产生 N×2 重复路由（用户案例：4 个方法 + 4 个模块级 = 8 条重复）。

**修正方案（双层防御，向后兼容）：**

1. **L1 启发式跳过**（[rules.py:325-342](uliweb/core/rules.py#L325-L342) `parse_class` else 分支前置）：
   - 当方法名（不区分大小写）属于 HTTP 动词集合 `{'get','post','put','delete','patch','head','options','trace','connect'}` 时，**跳过 auto-register**。
   - 直觉：方法名取 HTTP 动词，意图是"我是该 HTTP method 的处理器"，不是"我是独立路由"。
   - 兼容：现有依赖此行为（把方法名当路径段）的代码极少；如有，需显式 `@expose` 或重命名方法。

2. **L2 显式 opt-out 标记**：方法设 `__no_auto_expose__ = True` → 一定不 auto-register（即便不是 HTTP 动词名）。
   - 用于类内 helper 方法（如 `get_owned_agent`）想保留公开但不被路由收录的场景。
   - 类级 `__no_auto_expose__ = True` → 整个类所有方法都不 auto-register（与 Flask `MethodView` 等价）。

3. **L3 显式 opt-in 标记**（可选）：方法设 `__auto_expose__ = True` → 强制走方法名作路径段，绕过 L1（防止未来新增 HTTP 动词时误伤用户代码）。

**新相对路径生成规则**（伪代码）：

```python
HTTP_METHODS = frozenset({'get','post','put','delete','patch','head','options','trace','connect'})

def parse_class(self, f):
    for name in dir(f):
        func = getattr(f, name)
        if not (ismethod(func) or inspect.isfunction(func)): continue
        if name.startswith('_'): continue
        if hasattr(func, '__exposed__') and func.__exposed__:   # 已有 @expose
            ...  # 走原 258-303 分支
            continue
        # 新增 L1+L2+L3 守卫
        if getattr(f, '__no_auto_expose__', False) and not getattr(func, '__auto_expose__', False):
            continue
        if getattr(func, '__no_auto_expose__', False):
            continue
        if name.lower() in HTTP_METHODS and not getattr(func, '__auto_expose__', False):
            continue
        # 走原 325-342 分支（auto-register）
        ...
```

**验收标准：**

- 现有 `AgentView.get`/`AgentView.delete` 在 `@expose('/gateway/agents')` 下 **不再**被 auto-register，路由表只剩 `@expose('/gateway/agents/<int:agent_id>')` 显式声明的 1 条（DELETE）或 1 条（GET）。
- 旧依赖"方法名当路径段"语义的代码：若方法名不在 HTTP 动词集，仍按原行为工作（向后兼容）。
- 单元测试 `tests/test_class_method_expose.py` 覆盖：
  1. HTTP 动词方法名 → 跳过 auto-register
  2. `__no_auto_expose__ = True` → 跳过
  3. `__auto_expose__ = True` + HTTP 动词名 → 强制走原行为
  4. 现有 4 套业务场景（agent-gateway）回归全部通过

**对外接口影响：** 仅新增三个 dunder 属性（`__no_auto_expose__` / `__auto_expose__` / 类级 `__no_auto_expose__`）；不修改 `@expose` 装饰器签名；不修改 `parse_class` 公共方法签名；不修改 `Expose` 类行为。**完全向后兼容**。

### 3.18 错误响应状态码语义（`error()` 的 `status` 参数在 ASGI 下失效）

**背景 / 触发来源：** 在 agent-gateway 应用中发现，`error(msg, status=400/403/404)` 传入的
`status` 在 ASGI 路径下**完全失效**，导致"非法参数 / 无权限 / 未找到"等语义错误统一返回 500，
客户端无法按状态码区分错误类型。这是本 ASGI 迁移中错误处理环节的**缺陷**，需要在框架侧修复。

**现状问题（两处，一处硬编码忽略 `status`，一处语义不统一）：**

1. **`AsyncDispatcher._error`**（[SimpleFrame.py:2392](uliweb/core/SimpleFrame.py#L2392)）：
   ASGI 下视图内调用 `error()` 不抛异常，而是经由 `env['error'] = self._error`（[SimpleFrame.py:2336](uliweb/core/SimpleFrame.py#L2336)）
   **直接返回响应**，硬编码 `status_code=500`，无视 `kwargs` 里的 `status`：
   ```python
   def _error(self, message='', errorpage=None, **kwargs):
       from starlette.responses import JSONResponse
       if hasattr(message, '__str__'):
           message = str(message)
       return JSONResponse({'error': message}, status_code=500)   # ← 无视 kwargs 里的 status
   ```
   这与文档契约（`error()` 抛异常、无需 return，见 `docs/zh_CN` 教程）相悖：视图 `error("...")` 不带
   return 会静默返回 200 + body `"None"`。

2. **`_handle_exception` 对 uliweb `HTTPError` 的处理**（[SimpleFrame.py:3438-3455](uliweb/core/SimpleFrame.py#L3438-L3455)）：
   当 `error()` 抛出的 `HTTPError` 被捕获时，其 `errors` dict 里已有 `status`，但处理器硬编码
   `status_code=403`：
   ```python
   if hasattr(exception, 'errorpage') and hasattr(exception, 'errors'):
       message = exception.errors.get('message', str(exception))
       ...
       return JSONResponse({'error': message}, status_code=403)   # ← 应取 exception.errors['status']
   ```

**契约 / 期望行为：** `error(message, errorpage=None, request=None, appname=None, **kwargs)`
（[SimpleFrame.py:544](uliweb/core/SimpleFrame.py#L544)）的 `**kwargs` 约定支持 `status`。
`error()` 应始终**抛 `HTTPError`**（与文档「无需 return」一致），最终响应状态码由
`_handle_exception` 遵循 `errors['status']`，未传 `status` 时统一默认 **500**（`error()` 属通用
服务器错误，403「Forbidden」不宜作默认）。

**修正方案：**

1. `_error` 不再返回响应，改为抛 `HTTPError`（与模块级 `error()` 一致）：
   ```python
   def _error(self, message='', errorpage=None, **kwargs):
       if hasattr(message, '__str__'):
           message = str(message)
       kwargs.setdefault('message', message)
       raise HTTPError(errorpage, **kwargs)
   ```

2. `_handle_exception` 读取 `exception.errors.get('status', 500)`（默认统一为 500）：
   ```python
   status = exception.errors.get('status', 500)
   return JSONResponse({'error': message}, status_code=status)
   ```

**验收标准：**

- 视图 `error(msg, status=400)` 在 ASGI 请求下返回 HTTP 400（而非 500）；`status=403` → 403；未传 `status` → 500。
- `error(msg)` **无需 return** 即生效（不再返回 200 + "None"）。
- `raise HTTPError(message=..., status=...)` 被 `_handle_exception` 捕获时，返回 `errors['status']` 指定的状态码（默认 500）。
- 对现有全部调用 `error(msg)`（未传 status）的项目零行为变化（仍 500）。
- agent-gateway 回归：`GET /gateway/message_detail/{非法id}` → 400、跨用户访问 → 403、不存在 → 404。

**对外接口影响：** 不改 `error()` 签名、不改 `HTTPError` 结构；`_error` 由"返回响应"改为"抛
`HTTPError`"，与模块级 `error()` 语义对齐，恢复文档「无需 return」契约。**向后兼容**。

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
