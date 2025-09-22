# Uliweb 模板引擎

## 概述

`template.py` 是 Uliweb 框架的核心模板引擎模块，基于 Facebook 的 Tornado 模板系统修改而来。它提供了强大的模板编译、渲染和缓存功能，支持模板继承、包含、块定义等高级特性。

## 主要功能

### 1. 转义和编码函数

#### xhtml_escape(value)
HTML/XML 转义函数，转义字符 `<`, `>`, `&`。

#### xhtml_unescape(value)
HTML/XML 反转义函数。

#### json_encode(value)
JSON 编码函数，自动转义 `</` 为 `<\\/`。

#### json_decode(value)
JSON 解码函数。

#### url_escape(value, plus=True)
URL 编码函数，`plus` 参数控制是否将空格转换为 `+`。

#### url_unescape(value, encoding='utf-8', plus=True)
URL 解码函数。

#### utf8(value)
将字符串转换为 UTF-8 字节串。

#### to_unicode(value)
将字节串转换为 Unicode 字符串。

#### to_basestring(value)
转换为基本字符串类型（Python 2/3 兼容）。

#### linkify(text, shorten=False, extra_params="", require_protocol=False, permitted_protocols=["http", "https"])
将文本中的 URL 转换为 HTML 链接。

### 2. 核心类

#### Template 类
编译后的模板对象。

**构造函数参数：**
- `template_string`：模板字符串
- `begin_tag`：开始标签，默认为 `{{`
- `end_tag`：结束标签，默认为 `}}`
- `name`：模板名称
- `loader`：模板加载器
- `compress_whitespace`：是否压缩空白
- `filename`：文件名
- `debug`：调试模式
- `see`：调试查看函数
- `skip_extern`：是否跳过外部模板
- `log`：日志对象
- `multilines`：是否支持多行语法
- `comment`：是否添加注释

**主要方法：**
- `generate(vars=None, env=None)`：生成模板输出
- `_generate_python(loader, compress_whitespace)`：生成 Python 代码

#### Loader 类
模板加载器，负责模板的加载和缓存。

**构造函数参数：**
- `dirs`：模板目录列表
- `namespace`：命名空间
- `cache`：是否启用缓存
- `use_tmp`：是否使用临时文件
- `tmp_dir`：临时目录
- `begin_tag`：开始标签
- `end_tag`：结束标签
- `debug`：调试模式
- `see`：调试查看函数
- `max_size`：缓存最大大小
- `check_modified_time`：是否检查修改时间
- `skip_extern`：是否跳过外部模板
- `log`：日志对象
- `multilines`：是否支持多行语法
- `comment`：是否添加注释

**主要方法：**
- `load(name, skip='', skip_original='', default_template=None, layout=None)`：加载模板
- `resolve_path(filename, skip='', skip_original='', default_template=None)`：解析模板路径
- `print_tree(filename, path=None)`：打印模板树结构
- `print_blocks(filename, with_filename=True, path=None)`：打印模板块信息

#### LRUTmplatesCacheDict 类
LRU 缓存字典，支持模板缓存和过期检查。

### 3. 模板语法

#### 变量输出
```html
{{= expression }}          <!-- 转义输出 -->
{{$ expression }}          <!-- JSON 输出 -->
{{<< expression }}         <!-- 原始输出 -->
```

#### 控制结构
```html
{{if condition}}
    <!-- 内容 -->
{{elif condition}}
    <!-- 内容 -->
{{else}}
    <!-- 内容 -->
{{pass}}

{{for item in items}}
    <!-- 循环内容 -->
{{pass}}

{{while condition}}
    <!-- 循环内容 -->
{{pass}}

{{try}}
    <!-- 尝试内容 -->
{{except}}
    <!-- 异常处理 -->
{{finally}}
    <!-- 最终处理 -->
{{pass}}
```

#### 模板继承和包含
```html
{{extend "base.html"}}     <!-- 继承模板 -->
{{include "header.html"}}  <!-- 包含模板 -->
```

#### 块定义
```html
{{block block_name}}
    <!-- 块内容 -->
{{pass}}
```

#### 函数定义
```html
{{def function_name()}}
    <!-- 函数内容 -->
{{pass}}
```

#### 资源管理
```html
{{use resource_name}}      <!-- 使用资源 -->
{{link resource_name}}     <!-- 链接资源 -->
{{head resource_name}}     <!-- 头部资源 -->
{{head_link resource_name}} <!-- 头部链接资源 -->
```

### 4. 默认命名空间

模板引擎提供了以下默认函数：
- `escape`：xhtml_escape 别名
- `json_dumps`：JSON 编码
- `xhtml_escape`：HTML 转义
- `url_escape`：URL 编码
- `json_encode`：JSON 编码
- `squeeze`：压缩空白
- `linkify`：链接转换
- `datetime`：日期时间模块

### 5. 工具函数

#### template(text, vars=None, env=None, **kwargs)
直接渲染模板字符串。

#### template_py(text, **kwargs)
生成模板的 Python 代码。

#### template_file(filename, vars=None, env=None, dirs=None, loader=None, layout=None, **kwargs)
渲染模板文件。

#### template_file_py(filename, dirs=None, loader=None, layout=None, **kwargs)
生成模板文件的 Python 代码。

### 6. 自定义节点

可以通过 `register_node(name, node)` 注册自定义模板节点：
```python
from uliweb.core.template import register_node, BaseNode, BaseBlockNode

# 注册简单节点
class MyNode(BaseNode):
    def generate(self, writer):
        # 生成代码逻辑
        pass

# 注册块节点
class MyBlockNode(BaseBlockNode):
    def generate(self, writer):
        # 生成代码逻辑
        pass

register_node('mynode', MyNode)
register_node('myblock', MyBlockNode)
```

### 7. 调试功能

#### 模板树查看
```python
loader.print_tree('template.html')
```

#### 块信息查看
```python
loader.print_blocks('template.html')
```

## 使用示例

### 基本模板渲染
```python
from uliweb.core.template import template

result = template("Hello, {{= name }}!", {'name': 'World'})
print(result)  # 输出: Hello, World!
```

### 文件模板渲染
```python
from uliweb.core.template import template_file

result = template_file('index.html', {'title': '首页'}, dirs=['templates'])
```

### 模板继承
**base.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{= title }}</title>
</head>
<body>
    {{<< content }}
</body>
</html>
```

**page.html:**
```html
{{extend "base.html"}}
{{block content}}
    <h1>欢迎页面</h1>
    <p>这是页面内容</p>
{{pass}}
```

### 包含模板
```html
{{include "header.html"}}
<main>
    <!-- 主要内容 -->
</main>
{{include "footer.html"}}
```

### 条件判断
```html
{{if user}}
    <p>欢迎, {{= user.name }}</p>
{{else}}
    <p>请先登录</p>
{{pass}}
```

### 循环遍历
```html
<ul>
{{for item in items}}
    <li>{{= item.name }}</li>
{{pass}}
</ul>
```

## 配置选项

模板引擎支持以下配置选项：

- **begin_tag**：开始标签，默认 `{{`
- **end_tag**：结束标签，默认 `}}`
- **compress_whitespace**：是否压缩空白，默认根据文件扩展名判断
- **debug**：调试模式，默认 False
- **multilines**：多行语法支持，默认 False
- **comment**：是否添加行注释，默认 True
- **cache**：是否启用缓存，默认 True
- **check_modified_time**：是否检查文件修改时间，默认 False

## 性能优化

### 缓存机制
模板引擎使用 LRU 缓存来存储编译后的模板，避免重复编译。

### 空白压缩
对于 HTML 和 JS 文件，自动压缩多余空白字符。

### 预编译
支持生成模板的 Python 代码，便于调试和性能分析。

## 错误处理

模板解析错误会抛出 `ParseError` 异常，包含详细的错误信息和行号。

```python
from uliweb.core.template import ParseError

try:
    result = template("{{invalid syntax}}", {})
except ParseError as e:
    print(f"模板错误: {e}")
```

## 扩展性

模板引擎支持通过自定义节点和函数进行扩展，可以轻松添加新的模板语法和功能。
