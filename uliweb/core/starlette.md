# Uliweb 从 Werkzeug 迁移到 Starlette 技术迁移指南

## 目录
- [1. 概述](#1-概述)
- [2. 架构对比分析](#2-架构对比分析)
  - [2.1 当前 WSGI 架构（基于 Werkzeug）](#21-当前-wsgi-架构基于-werkzeug)
  - [2.2 目标 ASGI 架构（基于 Starlette）](#22-目标-asgi-架构基于-starlette)
- [3. 迁移策略和阶段划分](#3-迁移策略和阶段划分)
  - [3.1 阶段一：基础架构迁移](#31-阶段一基础架构迁移)
  - [3.2 阶段二：功能完整性](#32-阶段二功能完整性)
  - [3.3 阶段三：性能优化](#33-阶段三性能优化)
  - [3.4 阶段四：生态兼容](#34-阶段四生态兼容)
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
- [5. 技术挑战与解决方案](#5-技术挑战与解决方案)
  - [5.1 同步到异步的迁移](#51-同步到异步的迁移)
  - [5.2 全局状态管理](#52-全局状态管理)
  - [5.3 URL 路由兼容性](#53-url-路由兼容性)
- [6. 性能优化机会](#6-性能优化机会)
  - [6.1 异步 I/O 操作](#61-异步-io-操作)
  - [6.2 并发处理能力](#62-并发处理能力)
  - [6.3 WebSocket 支持](#63-websocket-支持)
- [7. 测试和验证策略](#7-测试和验证策略)
  - [7.1 单元测试](#71-单元测试)
  - [7.2 集成测试](#72-集成测试)
  - [7.3 兼容性测试](#73-兼容性测试)
  - [7.4 性能测试](#74-性能测试)
- [8. 迁移检查清单](#8-迁移检查清单)
- [9. 总结和最佳实践](#9-总结和最佳实践)

## 1. 概述

本文档详细阐述了将 Uliweb 框架从基于 Werkzeug 的 WSGI 架构迁移到基于 Starlette 的 ASGI 架构的完整技术方案。该迁移将使 Uliweb 支持：

- **异步处理能力**：充分利用现代 Python 的 async/await 语法
- **WebSocket 支持**：原生支持实时双向通信
- **更高性能**：更好的并发处理能力
- **现代生态集成**：更好的 Python 异步生态整合

迁移过程将直接采用纯 ASGI 架构，不再支持 WSGI 兼容模式。

## 2. 架构对比分析

### 2.1 当前 WSGI 架构（基于 Werkzeug）

Uliweb 当前使用 Werkzeug 作为底层 HTTP 处理框架，主要组件包括：

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

### 3.1 阶段一：基础架构迁移
- 核心 Request/Response 对象迁移
- ASGI 接口实现
- 基本路由系统

### 3.2 阶段二：功能完整性
- 中间件系统迁移
- 模板系统适配
- 会话管理

### 3.3 阶段三：性能优化
- 异步数据库驱动集成
- 缓存系统优化
- WebSocket 支持

### 3.4 阶段四：生态兼容
- 插件系统适配
- 文档更新

## 4. 核心组件迁移实现

### 4.1 Request/Response 对象迁移

**当前实现：**
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

**迁移方案：**
```python
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile, FormData
import json

class Request(StarletteRequest):
    """纯 ASGI Request 对象"""

    @property
    def GET(self):
        """兼容 GET 参数访问"""
        return self.query_params

    @property
    async def POST(self):
        """异步获取 POST 表单数据"""
        if self.method == "POST":
            form = await self.form()
            return form
        return {}

    @property
    async def FILES(self):
        """异步获取上传文件"""
        if self.method == "POST":
            form = await self.form()
            return {k: v for k, v in form.items() if isinstance(v, UploadFile)}
        return {}

    @property
    async def json(self):
        """异步获取 JSON 数据"""
        return await self.json()

    @property
    def is_xhr(self):
        """检查是否为 AJAX 请求"""
        return self.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'
```

### 4.2 Dispatcher 类重构

**当前 WSGI 接口：**
```python
class Dispatcher(object):
    def __call__(self, environ, start_response):
        response = self._open(environ)
        return response(environ, start_response)
```

**迁移为 ASGI 接口：**
```python
class Dispatcher:
    """支持 ASGI 3.0 接口的 Dispatcher"""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive, send)
            response = await self._open(request)
            await response(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")
```

### 4.3 URL 路由系统迁移

**当前基于 Werkzeug：**
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

class UliwebRouter:
    def __init__(self):
        self.routes = []
        self.url_map = {}

    def add_route(self, rule, endpoint, **kwargs):
        """转换 Werkzeug 风格路由到 Starlette 风格"""
        # 转换参数格式: <name> -> {name}
        import re
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)

        methods = kwargs.get('methods', ['GET'])
        route = Route(starlette_rule, endpoint, methods=methods)

        self.routes.append(route)
        self.url_map[endpoint] = route
        return route

# 适配现有的 expose 装饰器
def expose(rule=None, **kwargs):
    def decorator(func):
        # 自动检测函数类型并注册到路由
        app = application_var.get()
        app.router.add_route(rule, func, **kwargs)
        return func
    return decorator
```

### 4.4 全局状态管理迁移

**当前基于线程局部存储：**
```python
from werkzeug.local import Local, LocalManager
local = Local()
local.request = None
local.response = None
local_manager = LocalManager([local])
```

**迁移到上下文变量：**
```python
import contextvars

# 使用 contextvars 替代 threading.local
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')
settings_var = contextvars.ContextVar('settings')

# 上下文管理中间件
async def context_middleware(request, call_next):
    """管理请求上下文"""
    token = request_var.set(request)
    try:
        response = await call_next(request)
        return response
    finally:
        request_var.reset(token)
```

### 4.5 中间件系统适配

**创建 ASGI 中间件适配器：**
```python
class ASGIMiddlewareAdapter:
    def __init__(self, app, middleware_classes):
        self.app = app
        self.middleware_classes = middleware_classes
        self._sort_middlewares()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # 处理请求中间件
        response = None
        for middleware_cls in self.middleware_classes:
            middleware = middleware_cls()
            if hasattr(middleware, 'process_request'):
                response = await middleware.process_request(request)
                if response is not None:
                    break

        # 处理视图
        if response is None:
            try:
                response = await self.app(scope, receive, send)
            except Exception as e:
                # 处理异常中间件
                for middleware_cls in reversed(self.middleware_classes):
                    middleware = middleware_cls()
                    if hasattr(middleware, 'process_exception'):
                        response = await middleware.process_exception(request, e)
                        if response is not None:
                            break
                if response is None:
                    raise

        # 处理响应中间件
        for middleware_cls in reversed(self.middleware_classes):
            middleware = middleware_cls()
            if hasattr(middleware, 'process_response'):
                response = await middleware.process_response(request, response)

        await response(scope, receive, send)
```

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

**当前 WSGI 处理程序：**
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

# 纯 ASGI 应用
class ASGIApplication:
    """纯 ASGI 应用处理器"""

    def __init__(self, project_dir=None):
        self.project_dir = project_dir or path
        self.asgi_app = None
        self._initialized = False

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            # 创建 ASGI Dispatcher
            self.asgi_app = AsyncDispatcher(
                apps_dir=os.path.join(self.project_dir, 'apps'),
                project_dir=self.project_dir
            )
            self._initialized = True

    # ASGI 接口
    async def __call__(self, scope, receive, send):
        self._initialize()
        await self.asgi_app(scope, receive, send)

# 创建应用实例
application = ASGIApplication(project_dir=path)

# 创建应用的便捷函数
def create_application():
    """创建 ASGI 应用"""
    return ASGIApplication(project_dir=path)
```

**配置示例：**
```ini
[GLOBAL]
# ASGI 服务器配置
ASGI_SERVER = uvicorn  # 可选: uvicorn, hypercorn, daphne
ASGI_HOST = 0.0.0.0
ASGI_PORT = 8000
ASGI_WORKERS = 1

# 兼容性设置 - 保持与现有配置的兼容性
DEBUG = True
DEBUG_TEMPLATE = False
TEMPLATE_SUFFIX = '.html'
DEFAULT_CORS = False
FILESYSTEM_ENCODING = utf-8
DEFAULT_ENCODING = utf-8
ERROR_PAGE = 'error.html'

# 中间件配置 - 从 WSGI_MIDDLEWARES 迁移到 ASGI 中间件
MIDDLEWARES = {
    'context_middleware': ['uliweb.core.starlette.ContextMiddleware', 100],
    'static_middleware': ['uliweb.contrib.staticfiles.middleware', 200],
}

# 模板配置
TEMPLATE = {
    'auto_reload': True,
    'cache_size': 50,
}

# URL 配置 - 保持与现有配置兼容
URL = {
    '/': 'views.index',
}

# 数据库配置（异步版本）
DATABASES = {
    'default': {
        'ENGINE': 'uliweb.contrib.orm',  # 需要异步 ORM 支持
        'CONNECTION': 'postgresql://user:pass@localhost/dbname',
        'ASYNC': True,
    }
}

# 命令系统配置 - 保持与 manage.py 兼容
[COMMANDS]
# 异步命令处理器
ASYNC_COMMAND_HANDLER = 'uliweb.core.starlette.AsyncCommandHandler'

# 开发服务器配置
[DEVELOPMENT]
# 异步开发服务器选项
ASGI_DEV_SERVER = 'uvicorn'
ASGI_RELOAD = True
ASGI_DEBUG = True
```

**使用方式：**
- 使用 ASGI 服务器如 Uvicorn、Hypercorn、Daphne 运行应用
- 不再支持 WSGI 服务器
- 保持与现有配置文件的兼容性

## 5. Settings 配置迁移策略

### 5.1 现有 Settings 系统分析

基于 `manage.py` 和 `uliweb/core/SimpleFrame.py` 的分析，Uliweb 当前的 settings 系统具有以下特点：

**配置加载流程：**
1. 从环境变量获取 `SETTINGS` 和 `LOCAL_SETTINGS` 文件名
2. 按顺序加载：默认配置 → 应用配置 → 项目配置 → 本地配置
3. 支持 `default_settings` 参数进行运行时配置覆盖

**关键配置项：**
- `DEBUG`: 调试模式开关
- `WSGI_MIDDLEWARES`: WSGI 中间件配置
- `TEMPLATE`: 模板系统配置
- `URL`: URL 路由映射
- `DATABASES`: 数据库配置
- `GLOBAL_OBJECTS`: 全局对象注册

### 5.2 ASGI Settings 迁移方案

**配置加载兼容性：**
```python
class AsyncDispatcher:
    def __init__(self, apps_dir='apps', project_dir=None, include_apps=None,
                 start=True, default_settings=None, settings_file='settings.ini',
                 local_settings_file='local_settings.ini', **kwargs):

        # 保持与现有配置加载逻辑兼容
        self.settings_file = settings_file or os.environ.get('SETTINGS', 'settings.ini')
        self.local_settings_file = local_settings_file or os.environ.get('LOCAL_SETTINGS', 'local_settings.ini')

        # 异步配置加载
        self.settings = await self.load_settings_async(
            project_dir, include_apps, self.settings_file,
            self.local_settings_file, default_settings
        )

    async def load_settings_async(self, project_dir, include_apps, settings_file,
                                 local_settings_file, default_settings):
        """异步加载配置"""
        settings_paths = await self.collect_settings_paths_async(
            project_dir, include_apps, settings_file, local_settings_file
        )

        settings = pyini.Ini(lazy=True, basepath=os.path.join(project_dir, 'apps'))
        for path in settings_paths:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
                settings.read_string(content, path)

        # 应用默认配置
        if default_settings:
            settings.update(default_settings)

        return settings
```

**中间件配置迁移：**
```ini
# 从 WSGI_MIDDLEWARES 迁移到 ASGI 中间件
[MIDDLEWARES]
# 格式: 中间件名称 = [中间件类路径, 优先级, 配置参数]
context_middleware = ['uliweb.core.starlette.ContextMiddleware', 100]
static_middleware = ['uliweb.contrib.staticfiles.AsyncStaticFilesMiddleware', 200, {'directory': 'static'}]

# 兼容性配置 - 支持现有 WSGI 中间件的自动转换
[COMPATIBILITY]
AUTO_CONVERT_WSGI_MIDDLEWARES = True
```

**开发服务器配置：**
```ini
[DEVELOPMENT]
# 异步开发服务器配置
ASGI_DEV_SERVER = uvicorn
ASGI_HOST = localhost
ASGI_PORT = 8000
ASGI_RELOAD = True
ASGI_DEBUG = True
ASGI_WORKERS = 1

# 兼容现有 runserver 命令参数
DEV_SERVER_OPTIONS = {
    '--host': 'ASGI_HOST',
    '--port': 'ASGI_PORT',
    '--no-reload': 'ASGI_RELOAD=False',
    '--no-debug': 'ASGI_DEBUG=False',
}
```

### 5.3 环境变量和命令行参数兼容性

**环境变量兼容：**
```python
# 保持现有环境变量支持
SETTINGS_FILE = os.environ.get('SETTINGS', 'settings.ini')
LOCAL_SETTINGS_FILE = os.environ.get('LOCAL_SETTINGS', 'local_settings.ini')

# 新增 ASGI 相关环境变量
ASGI_SERVER = os.environ.get('ASGI_SERVER', 'uvicorn')
ASGI_HOST = os.environ.get('ASGI_HOST', 'localhost')
ASGI_PORT = int(os.environ.get('ASGI_PORT', '8000'))
```

**命令行参数适配：**
```python
class AsyncRunserverCommand(Command):
    """异步版本的 runserver 命令"""

    option_list = (
        make_option('--asgi-server', dest='asgi_server', default='uvicorn',
                   help='ASGI server to use (uvicorn, hypercorn, daphne)'),
        make_option('--asgi-host', dest='asgi_host', default='localhost',
                   help='Hostname to bind to'),
        make_option('--asgi-port', dest='asgi_port', type='int', default=8000,
                   help='Port to bind to'),
        make_option('--asgi-workers', dest='asgi_workers', type='int', default=1,
                   help='Number of worker processes'),
    )

    async def handle_async(self, options, global_options, *args):
        """异步处理运行服务器命令"""
        # 将命令行参数转换为 ASGI 服务器配置
        asgi_config = {
            'server': options.asgi_server,
            'host': options.asgi_host,
            'port': options.asgi_port,
            'workers': options.asgi_workers,
        }

        await self.run_asgi_server(asgi_config, global_options)
```

## 6. 技术挑战与解决方案

### 6.1 同步到异步的迁移

**问题：** 现有代码库大量使用同步代码

**解决方案：**
1. 使用 `anyio.to_thread.run_sync` 处理阻塞操作
2. 逐步迁移关键路径到异步
3. 提供同步到异步的包装器

```python
async def run_sync_in_thread(func, *args):
    """在线程中运行同步函数"""
    return await anyio.to_thread.run_sync(func, *args)
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

## 7. 测试和验证策略

### 7.1 单元测试
- 保持现有测试用例通过
- 新增异步测试用例
- 测试覆盖核心组件

### 7.2 集成测试
- 端到端功能测试
- 性能对比测试

### 7.3 兼容性测试
- 现有项目迁移测试
- 第三方插件兼容性
- 配置和设置验证

### 7.4 性能测试
- 并发连接测试
- 响应时间测试
- 资源使用测试

## 8. 迁移检查清单

### 核心组件迁移
- [ ] Request/Response 对象迁移
- [ ] Dispatcher 类重构（ASGI 接口）
- [ ] URL 路由系统迁移
- [ ] 全局状态管理迁移（contextvars）
- [ ] 中间件系统适配（ASGI 中间件）
- [ ] 事件分发系统异步化
- [ ] 命令系统迁移（异步命令处理）
- [ ] 模板系统异步化

### 功能组件迁移
- [ ] HTML 生成工具异步支持
- [ ] JSON 编码工具异步支持
- [ ] UAML 解析器异步支持
- [ ] 静态文件服务迁移
- [ ] 文件上传下载异步化
- [ ] 会话管理迁移
- [ ] 认证系统迁移
- [ ] 数据库连接异步化
- [ ] 缓存系统异步化

### 工具和调试
- [ ] 测试工具迁移（异步测试支持）
- [ ] 调试工具迁移
- [ ] 性能分析工具迁移
- [ ] 热重载支持迁移
- [ ] 开发服务器异步化

### 测试验证
- [ ] 单元测试更新（异步测试用例）
- [ ] 集成测试验证
- [ ] 性能测试对比（并发性能）
- [ ] 兼容性测试（现有项目）
- [ ] WebSocket 功能测试
- [ ] 压力测试和负载测试

### 文档和示例
- [ ] 迁移指南文档完善
- [ ] 异步编程最佳实践
- [ ] 示例代码更新（异步示例）
- [ ] API 文档更新
- [ ] 常见问题解答（FAQ）
- [ ] 故障排除指南

### 生态系统集成
- [ ] 第三方插件兼容性处理
- [ ] 异步数据库驱动集成
- [ ] 异步缓存后端支持
- [ ] 异步任务队列集成
- [ ] WebSocket 客户端库支持
- [ ] 异步监控和日志工具

## 9. 总结和最佳实践

### 迁移收益
1. **性能提升**：异步处理能力，支持更高并发
2. **功能增强**：WebSocket、Server-Sent Events 等现代功能
3. **生态整合**：更好的 Python 异步生态集成
4. **未来兼容**：符合现代 Web 标准和发展趋势

### 最佳实践
1. **渐进式迁移**：先在小规模项目中试点，逐步推广
2. **充分测试**：确保每个迁移步骤都经过充分测试
3. **监控性能**：迁移前后进行性能对比监控
4. **文档更新**：及时更新相关文档和示例

### 注意事项
1. **线程安全**：在异步环境中使用同步函数时注意线程安全问题
2. **上下文管理**：确保事件处理函数能够正确访问请求上下文
3. **依赖管理**：异步事件处理可能依赖其他异步服务，需要妥善管理
4. **错误处理**：为异步操作添加适当的错误处理和重试机制

通过这个完整的迁移方案，可以确保 Uliweb 从 Werkzeug 到 Starlette 的迁移过程中所有关键组件都被妥善处理，实现纯 ASGI 架构。
