---
name: uliweb-asgi-webapp
description: 指导创建新的 Uliweb3 ASGI Web 应用，包括项目结构、App 开发、视图、模板和 ASGI 部署
license: MIT
allowed-tools: "Read,Write,ExecuteCommand,Glob,SearchFiles,ListFiles"
version: 1.0.0
---

# Uliweb ASGI Web 应用开发技能

## 概述

此技能提供创建 Uliweb3 ASGI Web 应用的完整指导。Uliweb3 是一个基于 Starlette 的 ASGI 框架，支持异步处理、WebSocket、模板渲染等功能。

## 核心特性

Uliweb3 具有以下独特的设计理念：

### 自动加载机制

Uliweb3 的一大特点是**自动加载**：只要在 `INSTALLED_APPS` 中添加一个 app，该 app 的以下文件会自动被框架加载和处理，**无需额外注册**：

- `settings.ini` - 应用配置，自动合并到全局 settings
- `views.py` - 视图文件，使用 `@expose` 装饰器定义的路由自动注册
- `commands.py` - 命令文件，自动注册为 uliweb 命令
- `models.py` - 数据模型（需要 orm 支持）
- `templates/` - 模板目录，自动添加到模板搜索路径
- `static/` - 静态文件目录，自动提供静态文件服务
- `info.ini` - 应用信息，用于应用管理界面

这种设计让开发者可以专注于业务逻辑，无需手动配置路由、命令等。

### 核心组件

Uliweb3 的核心实现位于 `uliweb/core/SimpleFrame.py`，包含以下主要组件：

- **Request/Response**: 基于 Starlette 的异步请求/响应对象
- **AsyncDispatcher**: ASGI 分发器，支持同步/异步视图函数自动适配
- **UliwebRouter**: 路由适配器，将 Werkzeug 风格路由转换为 Starlette 风格
- **ASGIApplication**: 纯 ASGI 应用处理器（单例模式），用于 uvicorn 等服务器
- **LocalProxy**: 全局状态管理，支持 contextvars 和普通全局变量

## 先决条件

- Python 3.7+
- 已安装 uliweb3：`pip install -e .`
- ASGI 服务器（如 uvicorn、hypercorn）

## 指导说明

### 步骤 1: 创建项目

使用 `uliweb makeproject` 命令创建新项目：

```bash
uliweb makeproject myproject
```

这会在当前目录下创建一个 `myproject` 目录，包含以下结构：

```
myproject/
├── apps/
│   ├── __init__.py
│   ├── settings.ini      # 项目配置
│   └── local_settings.ini
├── asgi_handler.py       # ASGI 启动文件
└── setup.py
```

### 步骤 2: 创建 App

进入项目目录，创建应用：

```bash
cd myproject
uliweb makeapp myapp
```

App 结构如下：

```
apps/myapp/
├── __init__.py
├── settings.ini
├── views.py              # 视图文件
├── models.py             # 数据模型
├── templates/            # 模板目录
│   └── index.html
└── static/               # 静态文件目录
```

### 步骤 3: 配置 settings.ini

在 `apps/settings.ini` 中配置应用。Uliweb 的 settings 配置采用类 ini 格式，但支持 Python 语法。

#### 配置加载顺序

settings 文件的加载顺序为（后者覆盖前者）：

1. `uliweb/core/default_settings.ini` - 框架默认配置
2. `apps/xxx/settings.ini` - 各 App 配置
3. `apps/settings.ini` - 项目全局配置
4. `apps/local_settings.ini` - 本地配置（通常不提交到版本控制）

#### 基本配置示例

```ini
[GLOBAL]
DEBUG = True
DEBUG_CONSOLE = False
TEMPLATE_SUFFIX = '.html'
ERROR_PAGE = 'error.html'
MIDDLEWARES = []            # 中间件配置（ASGI架构，支持异步）
HTMLPAGE_ENCODING = 'utf-8'
TIME_ZONE = 'Asia/Shanghai'

INSTALLED_APPS = [
    'uliweb.contrib.staticfiles',
    'uliweb.contrib.session',
    'myapp',
]

[SITE]
SITE_NAME = '我的网站'

# 模板目录
TEMPLATE_DIRS = []
```

{% alert class=info %}
**重要变更**：在 Uliweb3 中，`WSGI_MIDDLEWARES` 已更名为 `MIDDLEWARES`。传统的 `process_request`、`process_response`、`process_exception` 方法仍然支持，框架会自动将其适配为异步执行。
{% endalert %}

#### FUNCTIONS 配置

用于定义公共函数：

```ini
[FUNCTIONS]
flash = 'uliweb.contrib.flashmessage.flash'
```

使用方式：
```python
from uliweb import functions
flash = functions.flash('message')
```

#### DECORATORS 配置

用于定义公共装饰器：

```ini
[DECORATORS]
check_role = 'myapp.decorators.check_role'
```

使用方式：
```python
from uliweb import decorators

@decorators.check_role('superuser')
@expose('/admin')
def admin():
    pass
```

#### BINDS 配置

用于绑定信号处理：

```ini
[BINDS]
audit.post_save = 'myapp.models.audit_post_save'
```

#### 字符串引用扩展

支持在字符串中使用 `{{expr}}` 引用配置项：

```ini
[DEFAULT]
a = 'http://abc.com'
b = '{{DEFAULT.a}}/index'
```
b 的值将变为 `http://abc.com/index`

#### 环境变量引用

支持引入环境变量：

```ini
[DB]
host = '$MYSQL_HOST'
port = '${MYSQL_PORT}'
```

#### settings 取值方式

在代码中使用 settings，**推荐使用属性访问**（最常用、最直观）：

```python
# 在 view 函数中直接使用（已注入）
@expose('/')
def index():
    debug = settings.GLOBAL.DEBUG
    site_name = settings.SITE.SITE_NAME
    return {'debug': debug}
```

以上写法等同于属性访问链式取值，例如 `settings.MAIL.HOST` 对应配置段 `[MAIL]` 中的 `HOST` 项。其他方式（较少用，作为补充）：

```python
# 通用方式（在任意位置）
from uliweb import settings
debug = settings.get_var('GLOBAL/DEBUG')   # 使用斜杠路径
debug = settings['GLOBAL']['DEBUG']        # 字典方式
```

> 推荐在文档与代码中以 `settings.段名.项名`（如 `settings.MAIL.HOST`）作为常用写法。

### 步骤 4: 编写视图

Uliweb3 使用 `@expose` 装饰器定义 URL 路由：

```python
# coding=utf-8
from uliweb import expose

@expose('/')
def index():
    return {'message': 'Hello World!'}

@expose('/hello/<name>')
def hello(name):
    return {'name': name}

# 类视图
@expose('/user')
class UserView:
    @expose('/')
    def index(self):
        return {'users': []}

    @expose('/login')
    def login(self):
        return {}
```

#### 视图约定（建议做法）

**类视图建议利用类级 `@expose` 的自动暴露约定**。当在 class 级别写了 `@expose('/xxx')`，该 class 下除 `_` 开头以外的方法会自动 expose 到 class expose 下的同名 endpoint，无需在类方法里再额外写 `@expose`（可以写注释说明这一点，让读者知道该方法是作为路由自动暴露的）：

```python
# coding=utf-8
from uliweb import expose

# 类级 @expose 下，非 _ 开头的方法会自动暴露到 /user/<方法名>
@expose('/user')
class UserView:
    def index(self):          # 自动暴露为 /user/index
        return {'users': []}

    def profile(self, id):    # 自动暴露为 /user/profile/<id>
        return {'profile': id}

    def _helper(self):        # _ 开头的方法不会被暴露为路由
        return 'internal'
```

需要注意的约定边界（与 uliweb3 代码 `rules.py` 一致）：

- **方法名是 HTTP 动词时默认不自动暴露**：`get/post/put/delete/patch/head/options/trace/connect` 这些方法名会默认被跳过（此时更像 Flask MethodView / RESTful 风格）。若确实要把它们当普通方法名路径暴露，可在方法上设置 `方法名.__auto_expose__ = True` 强制；若要显式禁止某个公开方法被暴露，设置 `方法名.__no_auto_expose__ = True`。
- **方法级单独写 `@expose`** 的类方法会使用其自己的显式规则，不会被自动暴露覆盖（可用来覆盖默认的 `/user/<方法名>` 路径）。
- 带 `@expose('/')`（根路径）的类，方法会自动暴露为 `/方法名`。

**重要：Uliweb3 异步变更**
- `request.POST` 已弃用，使用 `await request.get_POST()`
- `request.FILES` 已弃用，使用 `await request.get_FILES()`
- `request.json` 已弃用，使用 `await request.get_json()`
- 同步视图函数仍然可用，框架会自动适配

### 步骤 5: 编写模板

#### 模板路径约定（建议做法）

模板文件路径也有约定，**非必要不要指定自定义路径，而用约定的路径**。当视图返回字典且未显式指定 `template=` 时，Uliweb3 会按 `TEMPLATE_TEMPLATE` 约定自动查找模板（对应 `uliweb/core/default_settings.ini` 的 `TEMPLATE_TEMPLATE`）：

- **函数视图**：查找 `templates/<函数名>.html`
- **类视图**：查找 `templates/<类名>/<方法名>.html`

例如上面的类视图 `UserView.index`，默认模板就是 `templates/UserView/index.html`；函数视图 `index` 默认模板是 `templates/index.html`。因此建议把模板放在约定的路径下（可以写注释说明这一点），避免在每个视图里额外指定 `template=` 参数。

只有需要自定义模板文件名时才在 `@expose(..., template='xxx.html')` 中显式指定。

在 `templates/` 目录下创建模板文件：

```html
{{extend "layout.html"}}

{{block content}}
<h1>{{= title }}</h1>
<ul>
{{for item in items:}}
    <li>{{= item.name }}</li>
{{pass}}
</ul>
{{end}}
```

模板语法：
- `{{= variable }}` - 输出转义内容
- `{{<< variable }}` - 输出非转义内容
- `{{extend "parent.html"}}` - 继承模板
- `{{include "partial.html"}}` - 包含模板
- `{{block name}}{{end}}` - 定义块

### 步骤 6: 全局对象

在视图中可用的全局对象：

```python
from uliweb import (
    request,      # 请求对象
    response,     # 响应对象
    settings,     # 配置对象
    redirect,     # 重定向
    url_for,      # 反向URL生成
    json,         # JSON响应
    expose       # URL装饰器
)
```

### 步骤 7: 运行应用

使用 ASGI 服务器运行：

```bash
# 使用 uvicorn
uvicorn asgi_handler:application --reload --port 8000

# 使用 hypercorn
hypercorn asgi_handler:application --reload
```

或使用 uliweb 内置命令：

```bash
uliweb runserver
```

### 步骤 8: 部署配置

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

## 输出格式

技能输出为可运行的 Uliweb3 ASGI Web 项目，包含：
- 完整的项目结构
- 配置好的 settings.ini
- 示例视图和模板
- ASGI 启动文件

## 错误处理

常见错误及解决方案：

1. **找不到模块**：确保项目目录在 sys.path 中
2. **模板未找到**：检查 templates 目录是否存在
3. **静态文件404**：确保已添加 `uliweb.contrib.staticfiles` 到 INSTALLED_APPS
4. **POST数据获取错误**：使用 `await request.get_POST()` 替代 `request.POST`

## 示例

创建 Todo 应用示例：

```python
# coding=utf-8
from uliweb import expose, request, redirect, url_for

@expose('/todo')
class Todo:
    def __init__(self):
        from uliweb.orm import get_model
        self.model = get_model('todo')

    @expose('/')
    def index(self):
        return {'todos': self.model.all()}

    def new(self):
        title = request.POST.get('title')
        if title:
            todo = self.model(title=title)
            todo.save()
        return redirect(url_for(Todo.index))

    def delete(self, id):
        todo = self.model.get(int(id))
        if todo:
            todo.delete()
        return redirect(url_for(Todo.index))
```

配合模板 `templates/Todo/index.html`：

```html
{{extend "layout.html"}}

{{block content}}
<h2>待办事项</h2>
<ul>
{{for todo in todos:}}
    <li>
        {{= todo.title }}
        <a href="/todo/delete/{{= todo.id }}">删除</a>
    </li>
{{pass}}
</ul>

<form action="/todo/new" method="post">
    <input type="text" name="title" />
    <input type="submit" value="添加" />
</form>
{{end}}
```

## 参考文档

详细文档请参考：
- `references/architecture.md` - Uliweb 架构和机制
- `references/basic.md` - 基础开发教程
- `references/globals.md` - 全局环境对象
- `references/views.md` - 视图开发指南
- `references/template.md` - 模板系统
- `references/staticfiles.md` - 静态文件服务，包括 url_for_static 的使用
- `references/debug_logging.md` - 调试模式与日志级别，包括 WebSocket debug 日志控制
- `references/debugging.md` - 调试与复现技巧（懒加载、httpx 复现、临时库、绕认证、body 解析）
- `references/asgi.md` - ASGI 迁移指南，包括 middleware 的迁移
- `references/db.md` - 数据库使用指南
- `references/test_server.md` - 测试服务器，用于单元测试中启动真实 ASGI 服务器
