# 全局环境

Uliweb提供了必要的运行环境和运行对象，因此称之为全局环境。

## 全局对象

有一些全局性的对象可以方便地从 uliweb 中导入：

```python
from uliweb import (application, request, response,
    settings, Request, Response)
```

### application

记录整个Uliweb项目的运行实例，全局唯一。application是 `uliweb.core.SimpleFrame.AsyncDispatcher` 的实例。

在 ASGI 环境下，application 对象包含以下主要属性：
- `router`: 路由管理器（UliwebRouter 实例）
- `settings`: 配置对象
- `apps`: 已安装的应用列表
- `domains`: 域名配置

### Request

基于Starlette的Request类，支持异步访问方式。

**Uliweb3 重要变更**：
- `request.POST` 已弃用，请使用 `await request.get_POST()`
- `request.FILES` 已弃用，请使用 `await request.get_FILES()`
- `request.json` 已弃用，请使用 `await request.get_json()`
- `request.params` 仅返回GET参数，请使用 `await request.get_params()` 获取合并参数
- `@expose` 装饰器默认支持 GET、POST、PUT 方法，如需限制请使用 `methods` 参数

### response

响应对象代理，可以直接使用。

特殊属性：
- `response.template` - 用于重新指派渲染使用的模板

### settings

配置信息对象。

## 全局方法

```python
from uliweb import (redirect, json, POST, GET,
    url_for, expose, get_app_dir, get_apps, functions,
    decorators)
```

### redirect

```python
def redirect(location, code=302):
```

返回一个Response对象，用于实现URL跳转。

### json

```python
def json(data, **json_kwargs):
```

将一个data处理成json格式，并返回一个Response对象。

### expose

用来将URL与view方法进行映射。详见视图文档。

### url_for

```python
def url_for(endpoint, **values):
```

根据endpoint可以反向获得URL，endpoint可以是字符串格式或函数对象。

### functions

从settings.ini中的FUNCTIONS中导入方法：

```python
from uliweb import functions
func = functions.hello
```

### decorators

在settings.ini中定义DECORATORS，可以用作装饰器：

```python
from uliweb import decorators

@decorators.check_role('superuser')
@expose('/hello')
def hello():
    pass
```

## 请求相关属性

request对象在处理过程中还有一些属性：

- `request.appname` - 当前请求对应的view方法的appname名称
- `request.rule` - 解析出来的Rule对象
- `request.function` - view函数名
- `request.session` - 如果安装了session App，则会自动绑定
- `request.user` - 如果安装了auth App，则会自动绑定用户对象
