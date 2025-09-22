# uliweb/core/uaml.py 模块文档

## 概述

`uaml.py` 模块实现了 UAML (Uliweb Abstract Markup Language) 解析器，这是一种简洁的标记语言，用于生成 HTML 内容。UAML 语法类似于 HAML 和 Jade，但更简单易用，支持缩进层级结构和简洁的属性语法。

## 主要功能

### 1. UAML 语法解析
- 解析缩进层级结构
- 处理标签、属性和文本内容
- 支持注释和 verbatim 块
- 自动处理类名和 ID 属性

### 2. HTML 生成
- 将 UAML 转换为标准 HTML
- 支持自定义标签处理器
- 自动处理标签嵌套和闭合

### 3. 语法特性
- 简洁的类名和 ID 语法（`.class` 和 `#id`）
- 自动属性引用处理
- 支持多行文本和原始内容块

## 核心类

### Parser 类

UAML 解析器，负责解析 UAML 语法并生成 HTML。

**构造函数：**
```python
def __init__(self, text, writer=None)
```

**参数：**
- `text`: UAML 文本内容
- `writer`: 可选的 Writer 实例，默认为 None（使用默认 Writer）

**主要方法：**

#### run()
执行解析并返回生成的 HTML 字符串。

```python
def run(self)
```

**返回值：** HTML 字符串

#### generate()
生成器方法，产生解析令牌。

```python
def generate(self)
```

**生成：** (token_type, indent_level, value) 元组

### Writer 类

HTML 生成器，负责将解析令牌转换为 HTML。

**主要方法：**

#### unknown(indent, v)
处理未知标签的默认方法。

```python
def unknown(self, indent, v)
```

**参数：**
- `indent`: 缩进级别
- `v`: (tag_name, value, attributes) 元组

#### unknown_begin(indent, v)
处理开始标签的默认方法。

```python
def unknown_begin(self, indent, v)
```

#### unknown_close(indent, v)
处理闭合标签的默认方法。

```python
def unknown_close(self, indent, v)
```

#### comment(indent, line)
处理注释行。

```python
def comment(self, indent, line)
```

**参数：**
- `indent`: 缩进级别
- `line`: 注释内容

#### verbatim(indent, value)
处理原始文本内容。

```python
def verbatim(self, indent, value)
```

## UAML 语法

### 1. 基本标签语法

```uaml
div
    p 这是一个段落
    a(href="/link") 链接文本
```

**转换为：**
```html
<div>
    <p>这是一个段落</p>
    <a href="/link">链接文本</a>
</div>
```

### 2. 类和 ID 属性

```uaml
div.container#main
    p.note 带类名的段落
    span#unique 带ID的span
```

**转换为：**
```html
<div class="container" id="main">
    <p class="note">带类名的段落</p>
    <span id="unique">带ID的span</span>
</div>
```

### 3. 属性语法

```uaml
input(type="text", name="username", placeholder="请输入用户名")
form(method="post", action="/submit")
```

**转换为：**
```html
<input type="text" name="username" placeholder="请输入用户名" />
<form method="post" action="/submit"></form>
```

### 4. 文本内容

#### 行内文本
```uaml
p | 这是一行文本内容
```

#### 多行文本（使用 | 前缀）
```uaml
div
    | 第一行文本
    | 第二行文本
    | 第三行文本
```

### 5. 注释

```uaml
// 这是一个注释行
div
    p 内容 // 行内注释（不支持）
```

**转换为：**
```html
<!-- 这是一个注释行 -->
<div>
    <p>内容</p>
</div>
```

### 6. Verbatim 块（原始内容）

```uaml
{{{
<script>
function test() {
    console.log("原始 JavaScript 代码");
}
</script>
}}}
```

**转换为：**
```html
<script>
function test() {
    console.log("原始 JavaScript 代码");
}
</script>
```

### 7. 缩进层级

UAML 使用缩进来表示标签的嵌套关系：

```uaml
ul
    li 项目1
    li 项目2
    li
        a(href="#") 带链接的项目
```

**转换为：**
```html
<ul>
    <li>项目1</li>
    <li>项目2</li>
    <li>
        <a href="#">带链接的项目</a>
    </li>
</ul>
```

## 使用示例

### 基本用法

```python
from uliweb.core.uaml import Parser

uaml_text = """
div.container
    h1 标题
    p 段落内容
    ul
        li 项目1
        li 项目2
"""

parser = Parser(uaml_text)
html_output = parser.run()
print(html_output)
```

**输出：**
```html
<div class="container">
    <h1>标题</h1>
    <p>段落内容</p>
    <ul>
        <li>项目1</li>
        <li>项目2</li>
    </ul>
</div>
```

### 复杂表单示例

```python
uaml_text = """
form.form-horizontal#userForm(method="post", action="/save")
    .form-group
        label(for="name") | 姓名：
        input.form-control(type="text", name="name", id="name")
    .form-group
        label(for="email") | 邮箱：
        input.form-control(type="email", name="email", id="email")
    .form-group
        button.btn.btn-primary(type="submit") | 提交
"""

parser = Parser(uaml_text)
print(parser.run())
```

**输出：**
```html
<form class="form-horizontal" id="userForm" method="post" action="/save">
    <div class="form-group">
        <label for="name">姓名：</label>
        <input class="form-control" type="text" name="name" id="name" />
    </div>
    <div class="form-group">
        <label for="email">邮箱：</label>
        <input class="form-control" type="email" name="email" id="email" />
    </div>
    <div class="form-group">
        <button class="btn btn-primary" type="submit">提交</button>
    </div>
</form>
```

### 自定义标签处理

```python
from uliweb.core.uaml import Writer, Parser

class CustomWriter(Writer):
    def do_custom_tag(self, indent, value, **kwargs):
        # 自定义标签处理逻辑
        return indent * ' ' + f'<custom data-value="{value}">{value}</custom>'

uaml_text = "custom_tag(attr='value') | 自定义内容"
parser = Parser(uaml_text, CustomWriter())
print(parser.run())
```

**输出：**
```html
<custom data-value="自定义内容">自定义内容</custom>
```

## 语法详细说明

### 标签名称解析

UAML 使用以下规则解析标签名称：

1. **默认标签：** 如果没有指定标签名，默认为 `div`
2. **类和ID：** 使用 `.class` 和 `#id` 语法
3. **组合语法：** `tag.class#id` 格式

**示例：**
```uaml
// 默认为 div 标签
.container#main

// 明确指定标签
span.highlight#item1
```

### 属性解析规则

1. **简单属性：** `name=value` 格式
2. **引号处理：** 自动处理单引号和双引号
3. **布尔属性：** `disabled` 等属性可以省略值
4. **类名合并：** 多个 `.class` 和 `class=` 属性会自动合并

### 缩进规则

- 使用空格进行缩进（建议使用 2 或 4 个空格）
- 缩进级别决定标签嵌套关系
- 不支持混合使用空格和制表符

### 文本处理

1. **行内文本：** 使用 `|` 前缀表示文本行
2. **自动修剪：** 文本内容前后的空格会被自动修剪
3. **转义处理：** 文本内容会自动进行 HTML 转义

## 高级特性

### 自定义标签扩展

可以通过继承 `Writer` 类来添加自定义标签处理：

```python
class MyWriter(Writer):
    def begin_my_component(self, indent, value, **kwargs):
        return indent * ' ' + f'<my-component data-config="{value}">'

    def close_my_component(self, indent):
        return indent * ' ' + '</my-component>'

# 使用自定义 writer
parser = Parser("my_component | 配置数据", MyWriter())
```

### 模板集成

UAML 可以与 Uliweb 模板系统集成使用：

```python
from uliweb.core.template import template
from uliweb.core.uaml import Parser

def uaml_filter(text):
    """模板过滤器，将 UAML 转换为 HTML"""
    return Parser(text).run()

# 在模板中使用
# {{= uaml_filter('div.container\n    p 内容') }}
```

## 性能考虑

1. **解析性能：** UAML 解析使用正则表达式和生成器，性能较好
2. **内存使用：** 逐行处理，内存占用较低
3. **缓存：** 建议对频繁使用的 UAML 片段进行缓存

## 常见问题

### Q: 如何处理特殊字符？

A: UAML 会自动对文本内容进行 HTML 转义。如果需要原始内容，使用 verbatim 块：

```uaml
{{{
<div class="raw-html">
    原始 HTML 内容
</div>
}}}
```

### Q: 如何创建自闭合标签？

A: UAML 会自动识别自闭合标签（如 `input`, `img`, `br` 等）。对于其他标签，需要明确指定内容：

```uaml
// 自闭合标签
input(type="text")

// 非自闭合标签需要内容或子元素
div
    | 内容
```

### Q: 如何处理复杂的属性值？

A: 使用引号包裹复杂属性值：

```uaml
div(data-json='{"name": "value", "array": [1, 2, 3]}')
```

### Q: 如何添加多个类？

A: 可以使用多种方式：

```uaml
// 方式1：使用多个 .class
div.class1.class2

// 方式2：使用 class 属性
div(class="class1 class2")

// 方式3：混合使用
div.class1(class="class2")
```

## 最佳实践

1. **保持一致性：** 使用统一的缩进风格（建议 2 或 4 个空格）
2. **合理分组：** 将相关的标签组织在一起，提高可读性
3. **注释使用：** 使用注释说明复杂的结构
4. **模块化：** 将常用的 UAML 片段封装为可重用的组件
5. **测试验证：** 始终验证生成的 HTML 是否符合预期

UAML 提供了一种简洁、直观的方式来生成 HTML 内容，特别适合在模板和配置文件中使用，可以显著减少代码量并提高可读性。
