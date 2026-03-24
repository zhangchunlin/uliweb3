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
