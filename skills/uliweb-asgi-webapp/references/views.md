# 视图(View)

{% alert class=info %}
**Uliweb3 异步变更说明**

Uliweb3 已从 Werkzeug/WSGI 迁移到 Starlette/ASGI 架构。主要变化：

**Request 对象变化：**
- `request.POST` 已弃用，请使用 `await request.get_POST()` 异步获取
- `request.FILES` 已弃用，请使用 `await request.get_FILES()` 异步获取
- `request.json` 已弃用，请使用 `await request.get_json()` 异步获取
- `request.params` 仅返回 GET 参数，请使用 `await request.get_params()` 获取合并参数

**同步适配器机制：**
- 同步视图函数仍然可以使用，框架会自动将其适配为异步执行
- 同步函数在协程池中执行，不会阻塞事件循环
- 建议重构为异步函数以获得更好的性能

**运行环境：**
- Uliweb3 是纯 ASGI 框架，需要使用 ASGI 服务器运行（如 Uvicorn、Hypercorn、Daphne）
- 不再支持 WSGI 模式

{% endalert %}


## view模块的定义

在Uliweb中，在一个app的目录下，所有以views开头的文件都将被视为视图模块。Uliweb会自动将所有有效的app的视图文件在启动时进行导入，其目的就是为了搜集所有的URL的定义。

## 基于函数的View方法

### view函数的定义

```python
@expose('/')
def index():
    pass
```

如果一个view函数没有使用expose来修饰的话，它将不会被用户所访问。

expose后面是可以没有参数的，如：

```python
@expose
def index():
    pass
```

那么这个时候，一个view函数的URL将被定义为 `/Appname/view_module_name/view_function_name`。

### view函数的参数

view函数是可以有参数的，但首先你需要先在它的URL中定义参数：

```python
@expose('/documents/<lang>/<path:filename>')
def show_document(filename, lang):
    return _show(filename, lang)
```

### view的环境

在Uliweb中，一个view函数是运行在某种环境中的，可以直接使用以下对象：

- application - Uliweb的实例
- request - 请求对象
- response - 应答对象
- url_for - 用来生成反向URL
- redirect - 用于重定向
- error - 用于输出错误信息
- settings - 定义在settings.ini中的配置项
- json - 用于将dict对象包装成json格式并返回

### view的返回

view函数可以返回多种类型的结果：

- dict变量 - 自动套用一个模板
- response对象 - 直接使用response对象
- 字符串 - 直接返回文本
- json对象 - 使用json函数包装
- Response实例 - 主动创建Response实例

### view模块的入口处理

可以在view模块中定义名为 `__begin__` 和 `__end__` 的特殊方法：

```python
def __begin__():
    from uliweb.contrib.auth.views import login

    if not request.user:
        return redirect(url_for(login) + '?next=%s' % url_for(doto_index))
```

## 基于类的View方法

Uliweb支持类的方式来定义view：

```python
@expose('/user')
class UserView(object):
    def __begin__(self):
        if not request.user:
            return redirect('/login?next=%s' % request.path)

    @expose('/login')
    def login(self):
        # URL = /user/login
        pass

    def register(self, name):
        # URL = /user/register/<name>
        pass

    @expose('add')
    def add_user(self):
        # URL = /user/add

    @expose('')
    def list(self):
        # URL = /user

    def _common(self):
        # 内部函数，不会被客户端访问到
```

类视图特性：
- 建议使用New Style Class
- 支持__begin__处理
- 如果方法名开始为'_'，则不会被exposed
- 在类上使用expose，类的方法上不使用expose，则会自动生成 /url/method_name 的链接形式

{% alert class=warning %}
**类视图 URL 最佳实践**

1. **类的根路径使用 `@expose('/path')`** - 不要在类路径末尾加 `/`
   ```python
   # 正确：URL = /gateway
   @expose('/gateway')
   class IndexView:
       @expose('')
       def index(self):
           pass

   # 错误：URL 会变成 /，不是 /gateway
   @expose('/gateway/')  # 不要这样写！
   class IndexView:
       @expose('')
       def index(self):
           pass
   ```

2. **类的 index 方法使用 `@expose('')`** - 不要使用 `@expose('/')`
   ```python
   # 正确：URL = /gateway
   @expose('/gateway')
   class IndexView:
       @expose('')
       def index(self):
           pass

   # 错误：URL 可能变成 /
   @expose('/')
   def index(self):
       pass
   ```

3. **子路由路径规则**：
   - `@expose('')` - 相对于类的根路径
   - `@expose('/login')` - 相对于类的根路径（会变成 /gateway/login）
   - `@expose('login')` - 同上，不带前导斜杠也可以

总结：类视图的根路径用 `/path`（无尾随斜杠），index 方法用 `''`（空字符串）。
{% endalert %}

### 类视图的模板自动渲染

类视图方法返回 dict 时，Uliweb 会自动查找并渲染模板。模板路径规则为 `{appname}/{ViewClass}/{method_name}.html`。

例如：

```python
@expose('/user')
class UserView:
    @expose('')
    def list(self):
        return {'users': []}  # 模板路径: testapp/UserView/list.html

    @expose('/login')
    def login(self):
        return {'message': 'Please login'}  # 模板路径: testapp/UserView/login.html
```

**模板查找顺序：**
1. `{appname}/{view_class}/{function}.html` - 类视图专用
2. `{appname}/{function}.html` - 函数视图或类视图
3. `{function}.html` - 通用模板

**手动指定模板：**

```python
# 方式1：使用 @expose 的 template 参数
@expose('/user', template='custom/user.html')
class UserView:
    pass

# 方式2：设置 __template__ 属性
class UserView:
    @expose('')
    def list(self):
        return {'users': []}

    list.__template__ = 'custom/list.html'
```

详细说明请参考 [模板文档](./template.md#视图返回值与模板自动渲染)。

## 异步视图

推荐使用异步视图函数：

```python
@expose('/api/data')
async def async_view():
    # 正确的异步访问方式
    post_data = await request.get_POST()
    json_data = await request.get_json()
    files = await request.get_FILES()
    params = await request.get_params()

    # 获取原始请求体（字节）
    body = await request.body()
    body_str = body.decode('utf-8')  # 解码为字符串

    return {"status": "success", "data": post_data}
```

{% alert class=info %}
**Request 数据获取方法对比：**

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `await request.body()` | `bytes` | 获取原始请求体（字节） |
| `await request.get_POST()` | `dict` | 获取表单数据 |
| `await request.get_json()` | `dict` | 获取 JSON 数据 |
| `await request.form()` | `FormData` | 获取表单/文件数据（Starlette） |

**注意事项：**
- `body()` 是异步方法，必须使用 `await` 调用
- 调用 `get_json()` 或 `get_POST()` 后，不能再调用 `body()`，因为流已经被消费
- 如果需要同时获取 body 和解析数据，建议先调用 `body()` 获取原始数据，然后再自行解析

{% alert class=warning %}
**`get_params()` 不解析 JSON body**

`await request.get_params()`（以及 `get_POST()`）只解析 **form 编码**（`application/x-www-form-urlencoded` / `multipart`），**不会**解析 `Content-Type: application/json` 的请求体。

- 浏览器 `fetch` + `JSON.stringify` 发送的是 JSON → `get_params()` 读到空 dict。
- 而 `requests`/`httpx` 用 `data=`（form 编码）发送则正常。
- 因此**同一端点可能「CLI 正常、浏览器报错」**，根因往往是 body 解析差异。

若端点需同时兼容 JSON 与 form，统一用「先 JSON、失败回退 form」：

```python
async def _read_json_or_params():
    try:
        data = await request.get_json()
        if data is not None:
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return await request.get_params() or {}
```
{% endalert %}

同步视图（通过适配器支持）：

```python
@expose('/sync/data')
def sync_view():
    # 框架会自动将同步函数包装为异步执行
    return {"status": "sync function supported via adapter"}
```

{% alert class=warning %}
**注意事项：**
- 在同步视图中不能直接调用 `await request.get_POST()` 等异步方法
- 如果需要访问 POST/JSON/FILES 数据，建议重构为异步函数
- 框架会为同步函数预加载请求数据，可以通过 `request._cached_post_data` 等属性访问
{% endalert %}

### 混合模式

可以在异步视图中调用同步函数（通过协程池）：

```python
import asyncio

@expose('/mixed/view')
async def mixed_view():
    # 调用同步函数
    sync_result = await asyncio.to_thread(sync_function, data)

    # 同时使用异步功能
    async_result = await async_operation(data)

    return {"sync": sync_result, "async": async_result}
```

## WebSocket 支持

Uliweb3 原生支持 WebSocket，可以用于实时双向通信。

### WebSocket 视图函数

```python
from starlette.websockets import WebSocket

@expose('/ws', websocket=True)
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        # 处理消息
        await websocket.send_text(f"Message: {data}")
```

### WebSocket 配置

在 `settings.ini` 中可以配置 WebSocket 相关选项：

```ini
[WEBSOCKET]
ping_interval = 30
ping_timeout = 10
```

## view环境的扩展

如果你认为上面的环境还不够，那么你可以直接向env中增加新的对象，然后在view方法中可以通过
env.object的方式来使用它。你需要在某个app的settings.py文件中增加相应的插件处理。如:


```python
from uliweb.core.dispatch import bind

@bind('prepare_default_env')
def prepare_default_env(sender, env):
    from uliweb.utils.textconvert import text2html
    env['text2html'] = text2html
```

Uliweb中已经定义了 `prepare_default_env` 这个plugin的插入点，你可以直接使用它。它的
作用就是向env中增加新的对象，如上面是增加了一个新的函数可以用来将文本转为HTML代码。

## App 之间的模块导入

Uliweb 启动时会把 **apps 目录加入 sys.path**，因此 App 之间可以直接使用标准 Python import：

```python
# apps/appa/views.py 中
from appb.models import User  # 直接 import，不需要带 apps. 前缀
from appb.utils import helper_func
```

## 常见问题

- **JSON API 返回 HTML**：uliweb 的 `wrap_result` 判断 JSON 需要路径含 `/api/` 或方法名含 `api`，或使用 `starlette.responses.JSONResponse` 直接返回
- **SSE 流式响应不工作**：需设置 `headers={'X-Accel-Buffering': 'no'}` 禁用代理缓冲
- **前端 fetch 流式读取失败**：不要用 `pipeThrough`，直接用 `response.body.getReader()` + `TextDecoder`
- **子进程流式输出**：用 `asyncio.wait_for(process.stdout.read(), timeout=0.1)` 循环读取
- **url_for Endpoint not found**：endpoint 必须使用完整路径 例如 `gateway.views.AgentView.index`，详细说明见 [模板文档](./template.md#url_for-反向-url-生成)。
