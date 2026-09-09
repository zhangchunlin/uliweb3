# 从 WSGI/Werkzeug 迁移到 ASGI/Starlette 指南

Uliweb3 是一个纯 ASGI 框架，从原来的 WSGI/Werkzeug 架构迁移到了 ASGI/Starlette 架构。本文档将帮助你将现有的 Uliweb 项目从 WSGI 模式迁移到 ASGI 模式。

## 概述

### 主要变化

- **不再依赖 Werkzeug**：Uliweb3 使用 Starlette 作为底层 HTTP 框架
- **ASGI 架构**：使用 ASGI 协议代替 WSGI
- **异步支持**：全面支持 async/await 语法
- **WebSocket 支持**：原生支持 WebSocket 连接

### 迁移优势

1. **更高的性能**：异步处理带来更好的并发能力
2. **WebSocket 支持**：支持实时双向通信
3. **现代 Python 生态**：更好地集成 Python 异步生态系统

## 快速开始

### 1. 运行方式

你可以继续使用 `uliweb runserver` 命令启动开发服务器：

```bash
# 使用 runserver 命令（推荐用于开发）
python manage.py runserver

# 指定端口
python manage.py runserver 8080

# 指定主机
python manage.py runserver 0.0.0.0:8000
```

或者使用 ASGI 服务器运行：

```bash
# 使用 Uvicorn
uvicorn app:application --host 0.0.0.0 --port 8000

# 或使用 Hypercorn
hypercorn app:application --bind 0.0.0.0:8000

# 或使用 Daphne
daphne app:application
```

### 2. 入口文件

如果需要自定义应用入口，更新为 ASGI 格式：

```python
# app.py
import os
from uliweb import ASGIApplication

# 获取项目目录
project_dir = os.path.dirname(os.path.abspath(__file__))

# 创建 ASGI 应用
application = ASGIApplication(
    apps_dir=os.path.join(project_dir, 'apps'),
    project_dir=project_dir
)
```

或者使用 `uliweb.manage` 中的便捷方法：

```python
# 方式1：使用 make_application
from uliweb.manage import make_application

application = make_application()

# 方式2：使用 make_simple_application（已自动适配 ASGI）
from uliweb.manage import make_simple_application

application = make_simple_application()
```

## Request/Response 迁移

### Request 对象变化

在 ASGI 模式下，访问请求数据的方式发生了变化。

#### POST 数据访问

旧的 WSGI 方式：

```python
@expose('/submit')
def submit(request):
    post_data = request.POST  # 同步访问
    return {'data': post_data}
```

新的 ASGI 方式：

```python
# 异步视图函数（推荐）
@expose('/submit')
async def submit(request):
    post_data = await request.get_POST()
    return {'data': post_data}

# 同步视图函数（框架会自动适配）
@expose('/submit')
def submit(request):
    # 框架会自动预加载数据
    if hasattr(request, '_cached_post_data'):
        post_data = request._cached_post_data
    return {'data': post_data}
```

#### JSON 数据访问

旧的 WSGI 方式：

```python
@expose('/api/data')
def api_data(request):
    json_data = request.json  # 同步访问
    return json_data
```

新的 ASGI 方式：

```python
# 异步视图函数（推荐）
@expose('/api/data')
async def api_data(request):
    json_data = await request.get_json()
    return json_data

# 同步视图函数
@expose('/api/data')
def api_data(request):
    if hasattr(request, '_cached_json_data'):
        json_data = request._cached_json_data
    return json_data
```

#### 文件上传访问

旧的 WSGI 方式：

```python
@expose('/upload')
def upload(request):
    files = request.FILES  # 同步访问
    return {'files': list(files.keys())}
```

新的 ASGI 方式：

```python
# 异步视图函数（推荐）
@expose('/upload')
async def upload(request):
    files = await request.get_FILES()
    return {'files': list(files.keys())}

# 同步视图函数
@expose('/upload')
def upload(request):
    if hasattr(request, '_cached_files_data'):
        files = request._cached_files_data
    return {'files': list(files.keys())}
```

### 响应对象

Response 对象仍然保持与之前类似的接口：

```python
from uliweb import Response

@expose('/json')
def json_view(request):
    response = Response(json={'message': 'hello'})
    return response

@expose('/text')
def text_view(request):
    response = Response('Hello World', content_type='text/plain')
    return response
```

## 中间件迁移

### 中间件配置

中间件配置方式保持不变：

```ini
[MIDDLEWARES]
# 格式：中间件路径, 优先级（数字越小越先执行）
uliweb.contrib.auth.middle_auth.AuthMiddle = 100
uliweb.contrib.session.middle_session.SessionMiddle = 200
myapp.middleware.MyMiddleware = 150
```

### 中间件开发

新的中间件需要支持 ASGI 接口：

```python
from uliweb import Middleware

class MyMiddleware(Middleware):
    """高级中间件接口（推荐）"""

    async def dispatch(self, request, call_next):
        """处理请求和响应"""
        # 请求处理逻辑
        print(f"请求: {request.method} {request.url.path}")

        # 调用下一个中间件或视图
        response = await call_next(request)

        # 响应处理逻辑
        response.headers['X-Custom-Header'] = 'value'

        return response
```

或者使用底层 ASGI 接口：

```python
class MyASGIMiddleware(Middleware):
    """底层 ASGI 中间件接口"""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 处理请求
        await self.process_request(scope)

        try:
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope):
        """请求预处理"""
        pass

    async def handle_exception(self, scope, receive, send, exception):
        """异常处理"""
        raise exception
```

## 异步视图函数

### 定义异步视图

推荐在高 I/O 场景下使用异步视图函数：

```python
@expose('/async/data')
async def async_data(request):
    """异步视图函数示例"""
    # 异步获取数据
    post_data = await request.get_POST()
    json_data = await request.get_json()

    # 异步操作示例
    result = await async_database_query()

    return {'result': result, 'post': post_data}

@expose('/ws')
async def websocket_endpoint(websocket):
    """WebSocket 视图示例"""
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"收到: {data}")
```

### 同步和异步混合

框架支持同步和异步视图函数混合使用：

```python
# 同步视图（框架会自动适配）
@expose('/sync')
def sync_view(request):
    return {'type': 'sync'}

# 异步视图
@expose('/async')
async def async_view(request):
    return {'type': 'async'}

# 混合使用
@expose('/mixed')
async def mixed_view(request):
    # 调用同步函数（自动在线程池中执行）
    import asyncio
    sync_result = await asyncio.to_thread(sync_function, arg)

    # 调用异步函数
    async_result = await async_function()

    return {'sync': sync_result, 'async': async_result}
```

## 迁移检查清单

### 1. 运行方式

- [ ] 可以继续使用 `python manage.py runserver` 进行开发调试
- [ ] 生产环境使用 ASGI 服务器（uvicorn, hypercorn, daphne）

### 2. 代码检查

- [ ] 检查是否使用了已弃用的同步属性
- [ ] 更新 POST、FILES、json 访问方式
- [ ] 确保异步视图函数正确使用 await

### 3. 中间件检查

- [ ] 验证中间件兼容性
- [ ] 必要时更新中间件为 ASGI 接口

### 4. 配置检查

- [ ] 检查 `settings.ini` 配置
- [ ] 确保静态文件配置正确
- [ ] 更新日志配置

## 常见问题

### Q: 现有代码需要大量修改吗？

A: 不需要。框架提供了同步适配器机制，现有同步代码可以继续工作，但建议逐步迁移到异步模式以获得更好的性能。

### Q: 如何处理已弃用的属性访问？

A: 以下属性已弃用，会抛出异常：
- `request.POST` - 使用 `await request.get_POST()`
- `request.FILES` - 使用 `await request.get_FILES()`
- `request.json` - 使用 `await request.get_json()`

在同步视图中，框架会自动预加载这些数据到缓存属性中。

### Q: 如何判断函数是同步还是异步？

A: 使用 `asyncio.iscoroutinefunction()` 检查：

```python
import asyncio

async def async_func():
    pass

def sync_func():
    pass

print(asyncio.iscoroutinefunction(async_func))  # True
print(asyncio.iscoroutinefunction(sync_func))   # False
```

### Q: runserver 命令有什么变化？

A: `runserver` 命令仍然支持，但现在启动的是 ASGI 开发服务器而不是 WSGI 服务器。命令用法保持不变。

### Q: 部署时有什么特别需要注意的？

A: 请参考 [部署指南](deployment.md)，主要变化是：
- 需要使用 ASGI 服务器（推荐 Uvicorn）
- 确保使用 ASGI 兼容的进程管理器

## 性能优化建议

### 1. 逐步迁移到异步

将高频 I/O 操作迁移到异步：

```python
# 优先迁移这些场景
@expose('/api/external')
async def call_external_api(request):
    # 数据库查询
    data = await db.query(...)

    # 外部 API 调用
    result = await fetch_external_api(...)

    return result
```

### 2. 使用连接池

对于数据库和缓存，使用连接池：

```python
# 数据库连接池
DATABASES = {
    'default': {
        'engine': 'uliweb.contrib.orm.MySQL',
        'name': 'mydb',
        'user': 'root',
        'password': 'password',
        'host': 'localhost',
        'pool_size': 20,  # 连接池大小
    }
}
```

### 3. 合理使用同步代码

对于 CPU 密集型操作，可以保持同步：

```python
@expose('/compute')
def compute(request):
    # CPU 密集型任务保持同步
    result = heavy_computation()
    return {'result': result}
```

## 相关文档

- [部署指南](deployment.md)
- [ASGI 迁移设计文档](../../../sdlc/asgi-migration/spec.md)
- [中间件文档](middleware.md)
- [视图文档](views.md)
