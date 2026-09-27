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

### 块结束语法说明

- `{{block blockname}}` 可以使用 `{{end}}` 或 `{{end blockname}}` 结束（推荐使用后者以提高可读性）
- `{{if}}` / `{{for}}` / `{{while}}` 等 Python 代码块必须使用 `{{pass}}` 结束

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
{{elif other_condition:}}
    <p>Other</p>
{{else:}}
    <p>False</p>
{{pass}}
```

{% alert class=warning %}
**重要：Python 代码块必须使用 `{{pass}}` 结束**

- `{{if}}` / `{{for}}` / `{{while}}` 等必须用 `{{pass}}` 结束，不能用 `{{end}}`
- `{{block}}` 可以用 `{{end}}` 结束，也使用 `{{end blockname}}` 提高可读性
{% endalert %}

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

## 常见坑（实际踩过）

### 1. 别把顶层变量命名为 `item`

如果父模板（如 `layout.html`）里有菜单/循环用了 `item` 作循环变量：

```html
<!-- layout.html -->
{{for item in functions.iter_menu_item('MAINMENU', nav_active):}}
  ...
{{pass}}
```

那么任何 `{{extend "layout.html"}}` 的子模板里，顶层 `item` 会被 layout 的循环变量**遮蔽**——子模板里 `item['status']` 拿到的是最后一个菜单项而不是你传入的字典，表现为 `KeyError: 'status'`。**规避**：子模板传变量时避开 `item`，改用 `mail`、`record`、`thread` 等命名。

### 2. 字典用下标、对象用属性

Uliweb 模板里 `{{= x['k'] }}` 和 `{{= x.k }}` 编译结果不同：

- 对 **dict**：`{{= x['k'] }}` 可以正常取键；`{{= x.k }}` 会 `AttributeError`（dict 没有属性 `k`）。
- 对 **对象**（如 `SimpleNamespace`、ORM 实例）：`{{= x.k }}` 才有效。

所以视图返回的如果是 dict，模板里请统一用 `x['key']`；返回对象则用 `x.attr`。二者不要混用。另外 `{{if x['key']:}}`、`{{= ', '.join(x['list']) }}` 等对 dict 下标都可用。

### 3. 输出 HTML 正文用 `{{<< }}`（不转义），普通文本用 `{{= }}`

`{{= }}` 会转义 HTML（`<p>` → `&lt;p&gt;`）。若要在详情页原样渲染邮件/富文本正文，用：

```html
{{<< mail['html'] }}   <!-- 原样输出，不转义 -->
```

只有信任的内容才用 `{{<< }}`；不可信的输入继续用 `{{= }}` 防 XSS。

### 4. 继承布局的模板不能在测试里用裸 `Template(src)` 编译

带 `{{extend}}` 的模板若直接用裸 `Template(src)` 编译会报 `ParseError: extends block found, but no template loader`。测试须用 `uliweb.core.template.Loader([TMPL_DIR], namespace=...)` 再 `load(...).generate(vars=...)` 走通 layout+block 完整链路。
