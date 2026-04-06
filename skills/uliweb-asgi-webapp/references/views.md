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
        # URL = /login
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
