# Middleware 开发

{% alert class=info %}
**Uliweb3 异步变更说明**

Uliweb3 已迁移到 ASGI 架构。传统的 `process_request`、`process_response`、`process_exception` 方法仍然支持，并且框架会自动通过协程池将其适配为异步执行。新的 ASGI 中间件接口也已支持（`__init__`、`call_next` 方式）。

{% endalert %}

Uliweb中的Middleware是类似于django的Middleware，它可以在交易处理前和处理后，以
及出错时执行Middleware中的方法，起到一种通用的中间件的作用。Middleware是基于请
求的，它和平时的asgi middleware不同，asgi middleware是基于应用级的，当然也可以
处理请求，但是比Middleware还要底层，本文就不讨论了。


## 介绍

先以contrib.auth.middle_auth的AuthMiddle为例:


```
from uliweb import Middleware

class AuthMiddle(Middleware):
    ORDER = 100

    def process_request(self, request):
        from uliweb.contrib.auth import get_user
        request.user = get_user(request)
```

一个Middleware要从 `Middleware` 类派生。一般只需要定义三个方法:


```
process_request(request)
process_response(request, response)
process_exception(request, exception)
```

不同的Middleware可以根据需要分别定义不同的方法。

Middleware基类有一个缺省的 `__init__` 方法，如:


```
def __init__(self, application, settings):
    self.application = application
    self.settings = settings
```

你也可以自已定义一个，以便进行初始化的处理。


## 执行顺序

从上面的示例中，可以看到AuthMiddle中定义了一个 `ORDER` 的属性。Uliweb在调用
middlware时会根据 `ORDER` 的值先对Middleware进行排序，然后再根据顺序进行依次
调用。这里的顺序只是缺省的顺序，在用户进行配置时还可以进行修改。详见下面的配
置说明。


## 调用逻辑

下面列出执行的伪代码进行说明:


```
#排序
middlewares.sort()

#执行Middleware，执行process_request
for m in middlewares:
    if hasattr(m, 'process_request'):
        res = m.process_request(request)
        if res is not None:
            return res

#调用view方法
try:
    res = call_view()
except Exception, e:
    for m in reversed(middlewares):
        if hasattr(m, 'process_exception'):
            res = m.process_exception(request, e)
            if res is not None:
                break
    #继续抛出异常
    raise

#执行Middleware, 执行process_response
for m in reversed(middlewares):
    if hasattr(m, 'process_response'):
        res = m.process_response(request, res)
```


1. 先是对Middleware进行排序。
1. 对所有的Middleware中的process_request进行处理。如果有返回值不是None，则跳出
    循环。这里会对Middleware中是否有process_reqeust方法进行判断。后面类似。
1. 然后是执行view方法，获得response。在执行中，如果出错，则按倒序对Middleware
    进行处理。如果某个process_exception有返回值，则跳出循环。最后通过raise再次抛
    出异常，让整个应用捕获。
1. 如果没有异常，则按倒序执行Middleware中的process_response方法。这里和process_request
    不同。你需要强制返回response对象，因为它会传递到下一个处理方法中。


## 配置

有两个地方可以配置：apps/settings.ini和某个应用下的settings.ini。

Uliweb缺省定义了一个空的section:


```
[MIDDLEWARES]
```

它的定义形式为:


```
middleware_name = 'middleware_class_path'[, order]
```

前面的key是middleware的名字。后面的值可以有两种写法, 一种是只有middleware的类路径，
另一种是在类路径的后面还有一个顺序号。如果没有给出，则uliweb会自动从middleware
类的属性中获取ORDER的值，如果不存在，则缺省置为500。如果值为空，则当前的middleware
将被删除。

MIDDLEWARE的顺序如何确定？

在前面伪代码中，有一个对Middleware进行排序的处理。它会根据Middleware中的ORDER的
大小进行顺序。如果顺序号相同，则保持导入的顺序。

Uliweb中的app有些已经提供了settings.ini中的MIDDLEWARES的定义，它们只要你在
INSTALLED_APPS中包含app即可使用。顺序一般也定义好了。

因此当你自已写了Middleware或特殊情况下，才需要重新定义顺序。


## 在Contrib中定义的Midddleware

下面列出在contrib中定义的一些Middleware供参考:


* 'uliweb.contrib.auth.middle_auth.AuthMiddle' ORDER=100 app='auth'
    用于在请求进来时，向request添加一个user的对象。这样用户就可以直接通过request.user
    来判断用户是否已经登录和得到登录用户对象。
* 'uliweb.i18n.middle_i18n.I18nMiddle' ORDER=500 app='i18n'
    用于i18n的处理，设置语言类型
* 'uliweb.contrib.session.middle_session.SessionMiddle' ORDER=50 app='session'
    请求进来时自动读取session。请求结束时自动保存cookie。
* 'uliweb.orm.middle_transaction.TransactionMiddle' ORDER=80 app='orm'
    提供事务的支持。当view出错时，自动回滚，成功时自动提交。

所以，当你使用了上面几个app时，它会自动按:


```
'uliweb.contrib.session.middle_session.SessionMiddle'
'uliweb.contrib.auth.middle_auth.AuthMiddle'
'uliweb.orm.middle_transaction.TransactionMiddle'
'uliweb.i18n.middle_i18n.I18nMiddle'
```

的顺序来执行。


## ASGI 中间件开发

{% alert class=info %}
**Uliweb3 异步变更说明**

在 ASGI 架构下，`Middleware` 基类同时提供两种**异步接口**，与上面传统的 `process_*` 同步接口并存：
框架会自动把传统的 `process_request` / `process_response` / `process_exception` 经协程池适配为异步执行，
因此传统写法仍可继续使用。新代码推荐使用下面的异步接口。
{% endalert %}

### 高级接口（`dispatch`，推荐）

对大多数 HTTP 请求处理场景，推荐实现 `async def dispatch(self, request, call_next):` 高级接口：

```python
from uliweb import Middleware

class TimingMiddleware(Middleware):
    """请求计时中间件示例"""

    async def dispatch(self, request, call_next):
        import time
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers['X-Process-Time'] = str(process_time)

        return response
```

`call_next(request)` 会调用下一个中间件或最终视图函数；返回值是 `response` 对象，可在返回前对其进行修改。
支持拆成 `before_request` / `after_response` 钩子：

```python
from uliweb import Middleware

class MyAdvancedMiddleware(Middleware):
    async def dispatch(self, request, call_next):
        await self.before_request(request)
        response = await call_next(request)
        return await self.after_response(request, response)

    async def before_request(self, request):
        """请求预处理钩子"""
        pass

    async def after_response(self, request, response):
        """响应后处理钩子"""
        return response
```

### 底层 ASGI 接口（`__call__`）

需要处理 WebSocket、自定义协议或更精细的底层控制时，使用底层 ASGI 接口 `async def __call__(self, scope, receive, send):`：

```python
from uliweb import Middleware
from typing import Dict, Any

class MyASGIMiddleware(Middleware):
    def __init__(self, application, settings):
        super().__init__(application, settings)

    async def __call__(self, scope: Dict[str, Any], receive, send):
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 请求预处理
        await self.process_request(scope)

        try:
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope):
        pass

    async def handle_exception(self, scope, receive, send, exception):
        raise exception
```

### 纯 ASGI 中间件

也可以完全不依赖 `Middleware` 基类，直接实现 ASGI 协议：

```python
from starlette.types import ASGIApp, Scope, Receive, Send
from typing import Dict, Any

class ASGICustomMiddleware:
    def __init__(self, app: ASGIApp, **kwargs):
        self.app = app
        self.config = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                await self.process_response_start(scope, message)
            elif message["type"] == "http.response.body":
                await self.process_response_body(scope, message)
            await send(message)

        await self.process_request(scope)
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            await self.handle_asgi_exception(scope, receive, send, e)

    async def process_request(self, scope: Scope) -> None: pass
    async def process_response_start(self, scope, message): pass
    async def process_response_body(self, scope, message): pass
    async def handle_asgi_exception(self, scope, receive, send, exception): pass
```

### 配置与执行顺序

在 `settings.ini` 的 `[MIDDLEWARES]` 段中配置中间件，格式为 `middleware_name = 'middleware_class_path'[, order]`：

```ini
[MIDDLEWARES]
# 高级接口中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 接口中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

按 `order` 从小到大执行，形成处理链；高级与底层接口中间件可混用：

```
A Before → B Before → C Before → 应用处理 → C After → B After → A After
```

### 常用中间件示例

- **认证（JWT）**：校验 `Authorization: Bearer <token>`，跳过公开路径（`/login`、`/register`、`/docs` 等），失败返回 401。
- **限流**：按 `x-api-key` / `request.state.user_id` / IP 识别客户端，按 1 分钟窗口计数，超限返回 429 并带 `Retry-After` 头。
- **请求验证**：校验 HTTP 方法（405）、必需请求头（400）、`Content-Type`（415）。
- **响应格式化**：把 JSON 响应包装成 `{success, status_code, data, meta}` 统一结构。
- **请求日志**：记录 `method` / `url.path` / `status_code` / 耗时。

### 中间件开发最佳实践

- **选择接口**：大多数 HTTP 场景用高级 `dispatch` 接口；需要 WebSocket / 精细控制时用底层 `__call__` 接口。
- **性能**：预编译正则表达式、缓存计算结果；快速路径下用 `if self.should_skip(request): return await call_next(request)` 跳过不必要处理。
- **错误处理**：在 `dispatch` 中用 `try/except` 捕获特定异常并返回对应错误响应；未知异常 `raise` 交由上层处理。
- **状态传递**：中间件间通过 `request.state` 传递状态，例如认证中间件写入 `request.state.user`，授权中间件读取。

