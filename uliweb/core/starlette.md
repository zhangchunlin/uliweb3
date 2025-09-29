# Uliweb Starlette 集成模块 API 文档

## 概述

`uliweb/core/starlette.py` 模块提供了 Uliweb 框架与 Starlette ASGI 框架的完整集成，支持异步请求处理、WebSocket 和现代 ASGI 标准。

## 目录
- [1. 核心类](#1-核心类)
  - [1.1 Request 类](#11-request-类)
  - [1.2 Response 类](#12-response-类)
  - [1.3 UliwebRouter 类](#13-uliwebrouter-类)
  - [1.4 AsyncDispatcher 类](#14-asyncdispatcher-类)
  - [1.5 ASGIApplication 类](#15-asgiapplication-类)
- [2. 装饰器](#2-装饰器)
  - [2.1 expose 装饰器](#21-expose-装饰器)
  - [2.2 POST 装饰器](#22-post-装饰器)
  - [2.3 GET 装饰器](#23-get-装饰器)
- [3. 工具函数](#3-工具函数)
  - [3.1 上下文管理函数](#31-上下文管理函数)
  - [3.2 响应函数](#32-响应函数)
- [4. 使用示例](#4-使用示例)
- [5. 配置说明](#5-配置说明)

## 1. 核心类

### 1.1 Request 类

基于 Starlette 的 Request 类，保持与现有 Uliweb 的兼容性。

```python
from uliweb.core.starlette import Request

# 属性
request.GET           # 兼容 GET 参数访问 (query_params)
await request.POST    # 异步获取 POST 表单数据
await request.FILES   # 异步获取上传文件
await request.json    # 异步获取 JSON 数据
request.is_xhr        # 检查是否为 AJAX 请求
request.params        # 兼容 params 属性，合并 GET 和 POST 参数
```

**示例：**
```python
@expose('/api/data')
async def api_handler(request):
    # 获取 GET 参数
    page = request.GET.get('page', 1)

    # 获取 POST 数据
    if request.method == 'POST':
        form_data = await request.POST
        username = form_data.get('username')

    # 获取上传文件
    files = await request.FILES
    if 'avatar' in files:
        avatar_file = files['avatar']

    # 检查 AJAX 请求
    if request.is_xhr:
        return json({'status': 'success'})
```

### 1.2 Response 类

基于 Starlette 的 Response 类，保持与现有 Uliweb 的兼容性。

```python
from uliweb.core.starlette import Response

# 方法
response.write(value)  # 兼容 write 方法
```

### 1.3 UliwebRouter 类

Uliweb 路由适配器，将 Werkzeug 风格路由转换为 Starlette 风格。

```python
from uliweb.core.starlette import UliwebRouter

router = UliwebRouter()

# 添加 HTTP 路由
router.add_route(rule, endpoint, **kwargs)

# 添加 WebSocket 路由
router.add_websocket_route(rule, endpoint, **kwargs)

# 挂载子应用
router.mount(path, app, name=None)
```

**参数说明：**
- `rule`: 路由规则（支持 Werkzeug 格式：`<param>` 或 Starlette 格式：`{param}`）
- `endpoint`: 处理函数或类
- `kwargs`: 额外参数（methods, name 等）

### 1.4 AsyncDispatcher 类

支持 ASGI 3.0 接口的异步 Dispatcher，是 Uliweb ASGI 应用的核心。

```python
from uliweb.core.starlette import AsyncDispatcher

# 初始化
dispatcher = AsyncDispatcher(
    apps_dir='apps',
    project_dir=None,
    include_apps=None,
    start=True,
    default_settings=None,
    settings_file='settings.ini',
    local_settings_file='local_settings.ini'
)

# ASGI 接口
await dispatcher(scope, receive, send)
```

**初始化参数：**
- `apps_dir`: 应用目录（默认 'apps'）
- `project_dir`: 项目目录（默认当前目录）
- `include_apps`: 包含的应用列表
- `start`: 是否自动启动初始化
- `default_settings`: 默认设置
- `settings_file`: 设置文件名
- `local_settings_file`: 本地设置文件名

### 1.5 ASGIApplication 类

纯 ASGI 应用处理器，提供简单的 ASGI 应用创建接口。

```python
from uliweb.core.starlette import ASGIApplication

# 创建应用
app = ASGIApplication(project_dir='/path/to/project')

# ASGI 接口
await app(scope, receive, send)
```

## 2. 装饰器

### 2.1 expose 装饰器

适配现有的 expose 装饰器，用于注册视图函数到路由系统。

```python
from uliweb.core.starlette import expose

@expose('/hello')
def hello_view(request):
    return "Hello World"

@expose('/user/<user_id>')
def user_view(request, user_id):
    return f"User: {user_id}"

@expose('/api/data', methods=['GET', 'POST'])
async def api_handler(request):
    if request.method == 'GET':
        return json({'data': 'get'})
    else:
        form = await request.POST
        return json({'data': 'post'})
```

**支持参数：**
- `rule`: 路由规则
- `methods`: HTTP 方法列表
- `name`: 路由名称
- `template`: 模板文件
- `layout`: 布局文件
- `static`: 是否为静态视图

### 2.2 POST 装饰器

专门用于 POST 方法的快捷装饰器。

```python
from uliweb.core.starlette import POST

@POST('/submit')
async def submit_handler(request):
    form = await request.POST
    # 处理表单提交
    return json({'status': 'success'})
```

### 2.3 GET 装饰器

专门用于 GET 方法的快捷装饰器。

```python
from uliweb.core.starlette import GET

@GET('/data')
async def data_handler(request):
    page = request.GET.get('page', 1)
    return json({'page': page})
```

## 3. 工具函数

### 3.1 上下文管理函数

提供请求上下文的访问功能。

```python
from uliweb.core.starlette import (
    get_request, get_response, get_settings, get_application,
    request, response, settings, application
)

# 在视图函数中使用
@expose('/test')
async def test_view():
    current_request = get_request()
    current_settings = get_settings()
    current_app = get_application()

    # 或者使用全局代理对象
    user_agent = request.headers.get('user-agent')
    debug_mode = settings.DEBUG

    return f"User Agent: {user_agent}, Debug: {debug_mode}"
```

### 3.2 响应函数

提供常用的响应创建功能。

```python
from uliweb.core.starlette import redirect, json

@expose('/redirect')
def redirect_example():
    return redirect('/target')

@expose('/api/json')
def json_example():
    return json({'status': 'ok', 'data': [1, 2, 3]})
```

## 4. 使用示例

### 4.1 基本 ASGI 应用

```python
# asgi_app.py
import os
import sys
from uliweb.core.starlette import ASGIApplication

# 添加项目路径
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# 创建 ASGI 应用
application = ASGIApplication(project_dir=project_dir)
```

### 4.2 视图函数示例

```python
# apps/myapp/views.py
from uliweb.core.starlette import expose, json, redirect

@expose('/')
def index(request):
    return "Welcome to Uliweb Starlette"

@expose('/hello/<name>')
def hello(request, name):
    return f"Hello, {name}!"

@expose('/api/users')
async def api_users(request):
    if request.method == 'GET':
        # 模拟异步数据获取
        users = await get_users_async()
        return json({'users': users})
    elif request.method == 'POST':
        form = await request.POST
        user = await create_user_async(form)
        return json({'user': user})

@expose('/upload', methods=['POST'])
async def upload_file(request):
    files = await request.FILES
    if 'file' in files:
        uploaded_file = files['file']
        # 处理上传文件
        content = await uploaded_file.read()
        return json({'status': 'uploaded', 'size': len(content)})
    return json({'error': 'No file uploaded'}, status=400)
```

### 4.3 WebSocket 支持

```python
from uliweb.core.starlette import expose
from starlette.websockets import WebSocket

@expose('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## 5. 配置说明

### 5.1 基本配置

在 `settings.ini` 中配置 ASGI 相关设置：

```ini
[GLOBAL]
DEBUG = True
DEFAULT_CORS = False

# 模板配置
TEMPLATE_SUFFIX = .html
TEMPLATE_TEMPLATE = ['%s/%s', '%s/%s']

# 中间件配置（如果需要）
MIDDLEWARES = [
    # 中间件配置
]
```

### 5.2 运行 ASGI 应用

使用 Uvicorn、Hypercorn 或 Daphne 运行 ASGI 应用：

```bash
# 使用 Uvicorn
uvicorn asgi_app:application --host 0.0.0.0 --port 8000 --reload

# 使用 Hypercorn
hypercorn asgi_app:application --bind 0.0.0.0:8000

# 使用 Daphne
daphne -b 0.0.0.0 -p 8000 asgi_app:application
```

### 5.3 开发服务器配置

在开发环境中，可以配置热重载和调试模式：

```bash
uvicorn asgi_app:application --host 0.0.0.0 --port 8000 --reload --log-level debug
```

## 6. 注意事项

### 6.1 异步支持

- 所有视图函数都可以是异步的（使用 `async def`）
- 同步视图函数会在线程池中执行
- 使用 `await` 关键字访问异步属性（如 `request.POST`, `request.FILES`）

### 6.2 兼容性

- 保持与现有 Uliweb 代码的兼容性
- 支持现有的 `@expose` 装饰器语法
- 提供相同的全局代理对象（`request`, `response`, `settings`, `application`）

### 6.3 性能优化

- 利用 ASGI 的异步特性提高并发性能
- 支持 WebSocket 实时通信
- 更好的资源利用效率

## 7. 故障排除

### 7.1 常见问题

**路由不匹配**
- 检查路由规则格式是否正确
- 确保视图函数已正确使用 `@expose` 装饰器

**异步函数错误**
- 确保异步函数使用 `async def` 定义
- 使用 `await` 访问异步属性

**导入错误**
- 检查项目路径是否正确添加到 `sys.path`
- 确保所有依赖包已安装

### 7.2 调试技巧

启用调试模式查看详细错误信息：

```python
# 在 settings.ini 中设置
[GLOBAL]
DEBUG = True
```

查看路由信息：

```python
# 在代码中打印路由信息
from uliweb.core.starlette import __no_need_exposed__
print("Collected routes:", __no_need_exposed__)
```

## 8. Views 搜集合并机制

### 8.1 路由收集机制

Uliweb Starlette 模块实现了完整的 views 搜集和合并机制，与 Uliweb 原有的路由系统保持兼容。

#### 8.1.1 路由信息收集

当使用 `@expose` 装饰器时，路由信息会被收集到全局变量中：

```python
# 全局路由收集变量
__exposes__ = {}           # 路由暴露信息
__no_need_exposed__ = []   # 收集的路由信息（按时间戳排序）
__url_names__ = {}         # URL 名称映射
```

**收集过程：**
1. 当 `@expose` 装饰器被应用时，会收集以下信息：
   - 应用名称（从模块路径推断）
   - 端点名称（函数或方法的完整路径）
   - 路由规则
   - 路由参数（methods, name, template 等）
   - 时间戳（用于排序）

2. 路由信息被添加到 `__no_need_exposed__` 列表中

#### 8.1.2 路由合并

在应用初始化时，会调用 `_merge_rules()` 函数合并路由规则：

```python
def _merge_rules():
    """合并路由规则，类似 SimpleFrame.py 中的 merge_rules 函数"""
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

**合并逻辑：**
- 按时间戳排序，确保路由注册顺序
- 处理路由名称映射
- 合并相同路由规则（避免重复）
- 返回合并后的路由列表

### 8.2 视图模块自动导入

#### 8.2.1 自动导入机制

在 `AsyncDispatcher._import_views()` 方法中实现了视图模块的自动导入：

```python
async def _import_views(self):
    """导入视图模块，触发 expose 装饰器的执行"""
    # 添加项目目录到 Python 路径
    if self.project_dir not in sys.path:
        sys.path.insert(0, self.project_dir)

    # 收集所有应用的视图模块
    views_modules = []
    for app in self.apps:
        # 尝试导入 views.py
        try:
            views_module = f"apps.{app}.views"
            myimport(views_module)
            views_modules.append(views_module)
        except ImportError:
            # 如果 views.py 不存在，尝试导入 views 目录下的模块
            app_dir = self._get_app_dir(app)
            views_dir = os.path.join(app_dir, 'views')
            if os.path.exists(views_dir) and os.path.isdir(views_dir):
                # 导入 views 目录下的所有 Python 文件
                for filename in os.listdir(views_dir):
                    if filename.endswith('.py') and not filename.startswith('_'):
                        module_name = filename[:-3]
                        full_module = f"apps.{app}.views.{module_name}"
                        try:
                            myimport(full_module)
                            views_modules.append(full_module)
                        except ImportError:
                            pass
```

**导入策略：**
1. 首先尝试导入 `apps.{app}.views` 模块
2. 如果失败，扫描 `views` 目录下的所有 Python 文件
3. 导入每个文件作为独立的模块

#### 8.2.2 路由初始化

在 `AsyncDispatcher._init_routes()` 方法中完成路由的最终注册：

```python
async def _init_routes(self):
    """初始化路由，处理收集到的路由信息"""
    # 首先导入视图模块，这样 expose 装饰器才能被调用
    await self._import_views()

    # 合并路由规则
    merged_rules = _merge_rules()

    # 清空现有路由，避免重复
    self.router.routes.clear()
    self.router.router.routes.clear()

    # 注册路由到路由器
    for appname, endpoint, url, kw in merged_rules:
        # 转换 Werkzeug 风格路由到 Starlette 风格
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', url)

        # 处理静态视图
        static = kw.pop('static', None)
        if static:
            self.static_views.append(endpoint)

        # 注册路由
        self.router.add_route(starlette_rule, endpoint, **kw)
```

### 8.3 应用名称推断

在 `expose` 装饰器中实现了应用名称的自动推断：

```python
def _get_appname(module_name):
    parts = module_name.split('.')
    # 找到第一个不是 'views' 的部分作为应用名
    for part in parts:
        if part != 'views' and not part.startswith('_'):
            return part
    return parts[0] if parts else 'unknown'
```

**推断规则：**
- 从模块路径中提取应用名称
- 跳过 `views` 目录和以下划线开头的模块
- 返回第一个有效的应用名称

### 8.4 端点名称处理

支持不同类型的端点名称处理：

```python
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
```

**支持的类型：**
- 类方法：返回完整路径（module.class.method）
- 函数：直接返回函数对象
- 其他：转换为字符串

## 9. 路由匹配和执行流程

### 9.1 路由匹配机制

#### 9.1.1 路由匹配过程

当 HTTP 请求到达时，`AsyncDispatcher._match_route()` 方法负责路由匹配：

```python
async def _match_route(self, request):
    """异步路由匹配"""
    path = request.url.path
    method = request.method

    # 收集所有匹配的路由
    matched_routes = []

    # 遍历所有路由进行匹配
    for route in self.router.routes:
        if hasattr(route, 'path'):
            try:
                # 检查路径是否匹配
                if self._path_matches(route.path, path):
                    # 检查方法是否匹配
                    if hasattr(route, 'methods'):
                        if method in route.methods:
                            # 提取路径参数
                            path_params = self._extract_path_params(route.path, path)
                            matched_routes.append((route, path_params))
                    else:
                        # 如果没有指定方法，默认匹配 GET
                        if method == 'GET':
                            path_params = self._extract_path_params(route.path, path)
                            matched_routes.append((route, path_params))
            except Exception as e:
                continue

    # 如果有多个匹配的路由，选择最具体的那个
    if matched_routes:
        # 按路径长度排序，最长的路径最具体
        matched_routes.sort(key=lambda x: len(x[0].path), reverse=True)
        return matched_routes[0]

    # 如果没有匹配到路由，抛出 404 异常
    raise HTTPException(status_code=404)
```

**匹配策略：**
1. 遍历所有已注册的路由
2. 检查路径和方法是否匹配
3. 提取路径参数
4. 选择最具体的路由（路径最长的）

#### 9.1.2 路径匹配算法

```python
def _path_matches(self, route_path, request_path):
    """检查路径是否匹配"""
    # 简单的路径匹配逻辑
    if route_path == request_path:
        return True

    # 处理带参数的路径
    import re
    # 将 {param} 转换为正则表达式
    pattern = re.sub(r'\{([^}]+)\}', r'([^/]+)', route_path)
    pattern = '^' + pattern + '$'
    match = re.match(pattern, request_path)
    if match:
        return True

    # 如果正则匹配失败，尝试更简单的匹配
    route_parts = route_path.strip('/').split('/')
    request_parts = request_path.strip('/').split('/')

    if len(route_parts) != len(request_parts):
        return False

    for route_part, request_part in zip(route_parts, request_parts):
        if route_part.startswith('{') and route_part.endswith('}'):
            # 这是参数部分，可以匹配任何内容
            continue
        elif route_part != request_part:
            return False

    return True
```

### 9.2 视图函数执行流程

#### 9.2.1 请求处理准备

```python
def prepare_request(self, request, rule):
    """准备请求处理"""
    endpoint = rule.endpoint if hasattr(rule, 'endpoint') else rule

    # 绑定 endpoint 到 request
    request.rule = rule

    # 获取处理器
    _klass, mod, handler = self.get_handler(endpoint)

    # 设置应用名称
    request.appname = ''
    for p in self.apps:
        t = p + '.'
        if handler.__module__.startswith(t):
            request.appname = p
            break

    request.function = handler.__name__
    if _klass:
        request.view_class = _klass.__class__.__name__
        handler = getattr(_klass, handler.__name__)
    else:
        request.view_class = None

    return mod, _klass, handler
```

#### 9.2.2 视图函数调用

```python
async def call_view(self, mod, cls, handler, request, response=None, wrap_result=None, args=None, kwargs=None):
    """异步调用视图函数"""
    wrap = wrap_result or self.wrap_result
    env = await self.get_view_env()

    # 处理 __begin__ 和 __end__ 钩子
    if not hasattr(request, '_invokes'):
        request._invokes = {'begin': [], 'end': []}

    # 调用 __begin__
    begin_result = await self._process_begin(mod, request, response, env)
    if begin_result is not None:
        return await wrap(handler, begin_result, request, response, env)

    begin_result = await self._process_begin(cls, request, response, env)
    if begin_result is not None:
        return await wrap(handler, begin_result, request, response, env)

    # 预处理 __end__
    mod_end = await self._prepare_end(mod, request)
    cls_end = await self._prepare_end(cls, request)

    # 调用处理器
    result = await self.call_handler(handler, request, response, env, wrap, args, kwargs)

    # 调用 __end__
    if mod_end:
        end_result = await self._process_end(mod, request, response, env)
        if end_result is not None:
            return await wrap(handler, end_result, request, response, env)

    if cls_end:
        end_result = await self._process_end(cls, request, response, env)
        if end_result is not None:
            return await wrap(handler, end_result, request, response, env)

    return result
```

### 9.3 潜在问题和注意事项

#### 9.3.1 路由匹配问题

**问题1：路由参数格式转换**
- 当前实现将 Werkzeug 格式 `<param>` 转换为 Starlette 格式 `{param}`
- **潜在问题**：复杂参数类型（如 `<int:user_id>`）可能无法正确转换
- **建议**：需要扩展正则表达式以支持参数类型

**问题2：路径匹配算法**
- 当前使用简单的字符串分割和正则匹配
- **潜在问题**：对于复杂路径模式可能匹配不准确
- **建议**：使用 Starlette 内置的路由匹配机制

#### 9.3.2 视图导入问题

**问题1：模块导入顺序**
- 视图模块导入顺序影响路由注册顺序
- **潜在问题**：可能导致路由优先级混乱
- **建议**：确保导入顺序的一致性

**问题2：错误处理**
- 当前实现中导入失败会继续处理其他模块
- **潜在问题**：可能导致部分路由无法注册
- **建议**：提供更详细的错误日志和调试信息

#### 9.3.3 异步兼容性问题

**问题1：同步函数调用**
- 同步视图函数在线程池中执行
- **潜在问题**：可能影响性能，特别是高并发场景
- **建议**：鼓励使用异步视图函数

**问题2：上下文管理**
- 使用 `contextvars` 替代 `threading.local`
- **潜在问题**：某些同步库可能无法正确访问上下文
- **建议**：确保所有依赖库支持异步环境

#### 9.3.4 性能优化建议

1. **路由缓存**：考虑缓存路由匹配结果
2. **模块预加载**：在应用启动时预加载所有视图模块
3. **异步优化**：尽可能使用原生异步操作
4. **错误恢复**：实现更好的错误恢复机制

### 9.4 调试和监控

#### 9.4.1 路由调试

```python
# 查看收集的路由信息
from uliweb.core.starlette import __no_need_exposed__
print("Collected routes:", __no_need_exposed__)

# 查看最终注册的路由
from uliweb.core.starlette import AsyncDispatcher
dispatcher = AsyncDispatcher()
await dispatcher.init()
print("Registered routes:", [route.path for route in dispatcher.router.routes])
```

#### 9.4.2 性能监控

建议监控以下指标：
- 路由匹配时间
- 视图函数执行时间
- 模块导入时间
- 内存使用情况

## 10. 模块导出

### 10.1 主要导出项

```python
# 核心类
from uliweb.core.starlette import Request, Response, UliwebRouter, AsyncDispatcher, ASGIApplication

# 装饰器
from uliweb.core.starlette import expose, POST, GET

# 工具函数
from uliweb.core.starlette import get_request, get_response, get_settings, get_application
from uliweb.core.starlette import redirect, json

# 全局代理对象
from uliweb.core.starlette import request, response, settings, application

# 中间件
from uliweb.core.starlette import context_middleware
```

### 10.2 内部变量

```python
# 路由收集机制
__exposes__ = {}           # 路由暴露信息
__no_need_exposed__ = []   # 收集的路由信息
__url_names__ = {}         # URL 名称映射

# 上下文变量
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')
settings_var = contextvars.ContextVar('settings')
application_var = contextvars.ContextVar('application')
```

这个模块提供了完整的 Uliweb 到 Starlette 的迁移支持，使现有 Uliweb 项目能够充分利用现代 ASGI 框架的优势。
