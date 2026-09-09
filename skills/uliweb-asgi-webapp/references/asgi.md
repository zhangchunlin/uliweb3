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

#### 已弃用属性的错误处理

Uliweb3 对一些已弃用的同步属性提供了明确的错误提示：

```python
# 访问这些属性会抛出 RuntimeError 异常，提示正确的异步用法
request.POST    # RuntimeError: POST 属性已弃用，请使用 await request.get_POST() 方法。
request.FILES   # RuntimeError: FILES 属性已弃用，请使用 await request.get_FILES() 方法。
request.json    # RuntimeError: json 属性已弃用，请使用 await request.get_json() 方法。
request.values  # RuntimeError: values 属性已弃用，请使用 await request.get_params() 方法。
```

**重要说明**：`request.values` 在 Uliweb3 中会抛出异常，强制开发者使用 `await request.get_params()` 来获取完整的合并参数。

#### 其他已弃用属性的迁移

| 旧版（已弃用） | 新版 |
|--------------|------|
| `request.is_xhr` | `request.headers.get('X-Requested-With') == 'XMLHttpRequest'` |
| `request.environ['REMOTE_ADDR']` | `request.client.host` |
| `from uliweb import redirect` | `from starlette.responses import RedirectResponse` |

**示例**：

```python
# request.is_xhr 迁移
# 旧版
if request.is_xhr:
    return json({'status': 'ok'})

# 新版
if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
    return json({'status': 'ok'})

# request.client.host 迁移
# 旧版
ip = request.environ['REMOTE_ADDR']

# 新版
ip = request.client.host

# RedirectResponse 迁移
# 旧版
from uliweb import redirect
return redirect('/next')

# 新版
from starlette.responses import RedirectResponse
return RedirectResponse(url='/next', status_code=302)
```

#### 同步视图中的参数获取（不推荐）

在同步视图中，如果需要获取请求参数，可以使用以下方式：

```python
from uliweb import request
import asyncio

def sync_view():
    try:
        # 尝试在事件循环中获取参数
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            params = loop.run_until_complete(request.get_params())
        else:
            # 在异步上下文中，返回空字典
            params = {}
    except RuntimeError:
        # 没有事件循环，框架应该已经预加载了请求数据
        # 如果需要手动处理，可以记录警告
        params = {}

    # 使用 params 进行处理
    return {'data': params}
```

**推荐方案**：将同步视图改为异步视图

这种 try/except RuntimeError 的模式本身就说明代码结构有问题。最简单的解决方案是直接将同步视图改为异步视图：

```python
# 旧版：同步视图（需要处理事件循环）
def login():
    try:
        loop = asyncio.get_event_loop()
        params = loop.run_until_complete(request.get_params())
    except RuntimeError:
        params = {}
    # ...

# 新版：异步视图（推荐）
async def login():
    params = await request.get_params()
    # ...
```

**建议**：优先使用异步视图函数，避免处理复杂的同步/异步适配逻辑。

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

### 从 `process_*` 迁移到 `dispatch`

传统的 `process_request` / `process_response` / `process_exception` 中间件是 **WSGI 时代的相位模型**，与 ASGI 的流式/异步/双向模型不匹配（例如响应需整体缓冲、无法覆盖 WebSocket/lifespan/SSE）。Uliweb3 会在启动期对仍使用 `process_*` 的中间件输出一次 `logger.warning` 提醒：**它们将在 3.1 之后移除**。新中间件请一律用 `Middleware.dispatch(request, call_next)`。

单个 `process_*` 中间件的对等 `dispatch` 写法：

```python
from uliweb import Middleware

class MyMiddleware(Middleware):
    async def dispatch(self, request, call_next):
        # —— process_request 阶段：返回非 None 即短路，不进入响应阶段 ——
        r = self.process_request(request) if hasattr(self, 'process_request') else None
        if r is not None:
            return r
        try:
            response = await call_next(request)
        except Exception as e:
            # —— process_exception 阶段：返回非 None 则吞掉异常 ——
            r = self.process_exception(request, e) if hasattr(self, 'process_exception') else None
            if r is not None:
                return r
            raise
        # —— process_response 阶段 ——
        return self.process_response(request, response) if hasattr(self, 'process_response') else response
```

**唯一的坑：实例化时机**。legacy 中间件每请求 new 一个实例；`dispatch` 中间件在构建期单例化。若老中间件在 `self` 上存了每请求状态，迁移时必须改为**从 `request` 读取**（例如存 `request` 的属性），不要依赖 `self` 上的瞬时状态。

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

### WSGI App 改造成 ASGI App 事项清单

将一个现有的 WSGI Uliweb 项目迁移到 ASGI（Uliweb3）时，需要检查和修改以下事项：

#### 1. 依赖检查

- [ ] 移除对 Werkzeug 的直接依赖（Uliweb3 已使用 Starlette）
- [ ] 检查并更新其他可能依赖 WSGI 的库
- [ ] 确保使用兼容 ASGI 的第三方库

#### 2. Request/Response 变更

- [ ] `request.POST` → `await request.get_POST()`
- [ ] `request.FILES` → `await request.get_FILES()`
- [ ] `request.json` → `await request.get_json()`
- [ ] `request.params` → `request.query_params`（GET 参数）
- [ ] `request.values` → `await request.get_params()`（GET + POST 合并）
- [ ] 检查是否有同步访问 POST/FILES/JSON 的代码，改为异步调用

#### 3. 视图函数

- [ ] 考虑将关键视图改为 `async def`
- [ ] 同步视图仍可使用，但会在协程池中执行
- [ ] 检查是否有长时间运行的同步操作，考虑异步化

#### 4. 中间件

- [ ] 传统中间件（process_request/process_response/process_exception）目前仍兼容，但**会在 3.1 之后移除**（启动期有 `logger.warning` 提醒）；新中间件改用 `dispatch`（见上文"从 process_* 迁移到 dispatch"）
- [ ] ASGI 中间件需要实现 `async def __call__(self, scope, receive, send)`
- [ ] 检查自定义中间件是否需要更新

#### 5. 全局对象

- [ ] `from uliweb import request, response, settings, application` 仍然可用
- [ ] 注意 `settings` 和 `application` 使用 `Global()` 而非 contextvars
- [ ] `request` 和 `response` 使用 contextvars

#### 6. URL 路由

- [ ] `@expose` 装饰器仍然工作
- [ ] URL 参数格式保持不变：`/user/<id>`
- [ ] 检查是否有自定义路由适配器

#### 7. 静态文件

- [ ] 确保 `uliweb.contrib.staticfiles` 在 `INSTALLED_APPS` 中
- [ ] 检查 `settings.GLOBAL.STATIC_URL` 配置

#### 8. Session 和认证

- [ ] `uliweb.contrib.session` 已更新为 ASGI 兼容版本
- [ ] 检查自定义 session 存储是否兼容异步

#### 9. 数据库和 ORM

- [ ] `uliweb.contrib.orm` 已更新
- [ ] 检查 `from uliweb import models` 是否仍然可用（注意：目前可能不完全兼容）
- [ ] 异步模型操作使用 `await`

#### 10. 模板

- [ ] 模板语法保持不变
- [ ] 确保模板加载器配置正确

#### 11. 命令行工具

- [ ] 使用 `uliweb runserver` 替代旧的 WSGI 服务器
- [ ] 测试所有自定义命令是否正常工作

#### 12. 部署

- [ ] 使用 ASGI 服务器（uvicorn、hypercorn、daphne）
- [ ] 更新部署配置（nginx、gunicorn 等）
- [ ] 注意 ASGI 和 WSGI 服务器的差异

### 快速迁移步骤

1. **创建 ASGI 启动文件**：
```python
# asgi_handler.py
from uliweb.manage import make_application
application = make_application(project_dir=path)
```

2. **测试运行**：
```bash
uvicorn asgi_handler:application --reload
```

3. **逐项检查上述清单**

4. **更新代码**：根据检查结果修改代码

5. **全面测试**：确保所有功能正常工作
