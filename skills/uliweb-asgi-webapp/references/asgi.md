# Uliweb ASGI 支持

Uliweb3 已从 Werkzeug 迁移到 Starlette，实现了完整的 ASGI 支持。

## 架构变化

### 原有 WSGI 架构（已废弃）
- 基于 Werkzeug 的 Request/Response
- 使用 werkzeug.routing.Map 进行 URL 路由
- 基于 WSGI 标准

### 新的 ASGI 架构（当前）
- 基于 Starlette 的 Request/Response
- 使用 Starlette 路由系统
- 支持异步处理

## Uliweb3 重要变更

### Request 对象变更

**旧版（已弃用）：**
```python
post_data = request.POST
files = request.FILES
json_data = request.json
params = request.params        # 仅 GET 参数
values = request.values       # GET + POST 合并参数
```

**新版（推荐）：**
```python
post_data = await request.get_POST()
files = await request.get_FILES()
json_data = await request.get_json()
params = await request.get_params()    # GET + POST 合并参数（等价于旧 request.values，注意没有 request.get_values()方法）
```

#### request.get_params() 详细说明

`request.get_params()` 是一个异步方法，返回合并了 GET 参数和 POST 表单数据的字典。

**工作原理：**
- 合并 GET 参数（URL 查询字符串）和 POST 表单数据
- 如果同一个参数名同时出现在 GET 和 POST 中，POST 的值会覆盖 GET 的值

这与 Werkzeug 的 `Request.values` 属性行为完全一致。

**使用示例：**

```python
# 在异步视图中获取合并参数（等价于旧 request.values）
@expose('/api/data')
async def async_view():
    # 获取名为 'name' 的参数（可能来自 GET 或 POST）
    params = await request.get_params()
    name = params.get('name')

    # 或者直接使用
    name = (await request.get_params()).get('name')

    # 获取所有参数
    all_params = await request.get_params()
    return all_params

# 旧版写法（WSGI）
@expose('/api/data')
def async_view():
    name = request.values.get('name')
    all_params = request.values.to_dict()
    return all_params
```

### 同步适配器机制

Uliweb3 提供了同步适配器机制，支持现有同步代码平滑过渡：

- 同步函数会自动在协程池中执行
- 预加载请求数据避免同步函数中调用异步方法
- 可以在同一项目中混合使用同步和异步代码

### 全局状态管理

使用 contextvars 替代 threading.local，更适合异步环境：

```python
from uliweb import request, response, settings, application
```

## 运行方式

### 使用 Uvicorn

```bash
uvicorn asgi_handler:application --reload --port 8000
```

### 使用 Hypercorn

```bash
hypercorn asgi_handler:application --reload
```

### 使用 uliweb 内置命令

```bash
uliweb runserver
```

## ASGI 处理文件

创建 `asgi_handler.py`：

```python
import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from uliweb.manage import make_application

application = make_application(project_dir=path)
```

## 中间件

Uliweb3 的中间件系统支持 ASGI 接口：

```python
from uliweb import Middleware

class MyMiddleware(Middleware):
    async def dispatch(self, request, call_next):
        # 请求预处理
        response = await call_next(request)
        # 响应后处理
        return response
```

在 settings.ini 中配置：

```ini
[MIDDLEWARES]
my_middleware = 'myapp.middleware.MyMiddleware', 100
```

## WebSocket 支持

Uliweb3 支持 WebSocket：

```python
@expose('/ws', websocket=True)
async def websocket_endpoint(websocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

## 性能优化

- 使用异步视图函数获得最佳性能
- 合理使用同步适配器机制
- 启用模板缓存提高渲染性能

## 迁移指南

1. **更新 Request 访问方式**：将同步属性改为异步方法
2. **更新视图函数**：考虑使用 async def
3. **更新中间件**：使用异步接口
4. **更新 ASGI 服务器**：使用 uvicorn 或 hypercorn 替代 WSGI 服务器
