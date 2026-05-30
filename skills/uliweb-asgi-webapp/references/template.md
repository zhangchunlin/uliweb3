# 模板(Template)

Uliweb的模板系统简单易学，可以嵌入Python代码，支持模板继承和块功能。

## 特点

- 简单，易学
- 可以嵌入Python代码
- 不用过分关心Python代码的缩近，只要注意块结束时加pass
- Python代码与HTML可以交叉使用
- 支持模板的继承
- 支持类django的block的功能
- 提供一些方便的内置方法
- 支持环境的扩展
- 先编译成Python代码，然后再执行

## 基本语法

Uliweb的模板的语法很简单，只有以下几种类型的标记：

- `{{= result}}` - 用来输出的标记，会自动对输出的内容进行转义
- `{{<< result}}` - 用来输出非转义的内容
- `{{ ... }}` - 表示里面为Python代码
- `{{extend "template"}}` - 表示继承模板
- `{{include "template"}}` - 表示包含模板
- `{{block blockname}}{{end}}` - 用于定义一个块
- `{{# ... }}` - 单行注释
- `{{## ... ##}}` - 片段注释

## 模板继承

父模板 (layout.html)：

```html
<html>
<head>
<title>Title</title>
</head>
<body>
{{block main}}{{end}}
</body>
</html>
```

子模板 (index.html)：

```html
{{extend "layout.html"}}
{{block main}}
<p>This is child template.</p>
{{end}}
```

## 变量输出

```html
{{= "hello"}}
{{= title}}
```

## Python代码示例

```html
{{import os
out_write("<h1>Hello</h1>")
}}
```

## 循环和条件

```html
{{for item in items:}}
    <li>{{= item.name }}</li>
{{pass}}

{{if condition:}}
    <p>True</p>
{{else:}}
    <p>False</p>
{{pass}}
```

## 模板环境

Uliweb的模板在运行时也有一些对象和方法可以直接使用：

- escape() - 用来转换HTML的特殊符号
- out_write() - 在代码片段中向模板输出内容

## 参数配置

在 settings.ini 中可以配置模板选项：

```ini
[TEMPLATE]
namespace = {}
cache = True
check_modified_time = True
multilines = True
```

- cache - 是否启用模板对象缓存
- check_modified_time - 检查模板文件修改时间
- multilines - 支持多行Python代码

## 模板标签设置

缺省情况下，Uliweb的模板使用 `{{` 和 `}}` 来包括模板变量，也可以在模板中动态设置：

```
#uliweb-template-tag:[[,]]
```

表示使用 `[[` 和 `]]` 作为模板的标签。

## 视图返回值与模板自动渲染

当视图函数或类视图方法返回 dict 类型时，Uliweb 会自动查找并渲染对应的模板。

### 模板查找规则

模板查找使用 `settings.ini` 中的配置：

```ini
[GLOBAL]
TEMPLATE_TEMPLATE = ['{appname}/{view_class}/{function}.html', '{appname}/{function}.html', '{function}.html']
TEMPLATE_SUFFIX = '.html'
```

查找顺序：
1. `{appname}/{view_class}/{function}.html` - 类视图专用
2. `{appname}/{function}.html` - 函数视图或类视图
3. `{function}.html` - 通用模板

### 函数视图的模板查找

对于函数视图，模板路径为 `{appname}/{function_name}.html`：

```python
# 视图文件: apps/gateway/views.py
@expose('/')
def index():
    return {'title': 'Hello'}  # 查找: gateway/index.html
```

### 类视图的模板查找

对于类视图方法，模板路径为 `{appname}/{ViewClass}/{method_name}.html`：

```python
# 视图文件: apps/gateway/views.py
@expose('/user')
class UserView:
    @expose('')
    def list(self):
        return {'users': []}  # 查找: gateway/UserView/list.html

    @expose('/login')
    def login(self):
        return {'message': 'Please login'}  # 查找: gateway/UserView/login.html
```

### 手动指定模板

可以通过以下方式手动指定模板：

**方式1：使用 @expose 的 template 参数**

```python
@expose('/user', template='custom/user.html')
class UserView:
    pass
```

**方式2：在类方法上设置 __template__ 属性**

```python
class UserView:
    @expose('')
    def list(self):
        return {'users': []}

    # 手动指定模板
    list.__template__ = 'custom/list.html'
    # 或者使用字典格式
    list.__template__ = {'appname': 'gateway', 'view_class': 'UserView', 'function': 'list'}
```

### 模板目录结构示例

```
apps/
  gateway/
    templates/
      index.html              # 函数视图: gateway/index
      UserView/               # 类视图模板目录
        list.html             # UserView.list 方法
        login.html            # UserView.login 方法
      custom/
        list.html             # 手动指定的模板
```

## url_for 反向 URL 生成

模板中使用 `url_for()` 生成 URL，endpoint 必须使用完整路径：

| 视图类型 | endpoint 格式 | 示例 |
|----------|---------------|------|
| 函数视图 | `{app}.{module}.{func_name}` | `gateway.views.index` |
| 类视图 | `{app}.{module}.{ClassName}.{method_name}` | `gateway.views.AgentView.get` |

```html
<a href="{{= url_for('gateway.views.index') }}">首页</a>
<a href="{{= url_for('gateway.views.AgentView.get', agent_id=1) }}">查看</a>
```

{% alert class=warning %}
endpoint 必须包含完整路径 `gateway.views.AgentView.index`，不能只写 `AgentView.index`。
{% endalert %}
