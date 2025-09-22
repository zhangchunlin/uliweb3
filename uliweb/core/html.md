# uliweb/core/html.py 模块文档

## 概述

`html.py` 模块是 Uliweb 框架的核心 HTML 生成工具，提供了一系列用于动态生成 HTML 内容的类和函数。它支持链式调用和上下文管理器语法，使得 HTML 生成更加简洁和直观。

## 主要功能

### 1. to_attrs 函数

```python
def to_attrs(args, nocreate_if_none=['id', 'for', 'class'])
```

将 Python 字典转换为 HTML 属性字符串格式。

**参数:**
- `args`: 属性字典
- `nocreate_if_none`: 当值为 None 时不创建属性的键列表，默认为 ['id', 'for', 'class']

**返回值:** HTML 属性字符串

**示例:**
```python
attrs = {'class': 'demo', 'id': 'test', 'style': 'color: red'}
result = to_attrs(attrs)  # 输出: class="demo" id="test" style="color: red"
```

### 2. Buf 类

HTML 内容缓冲区类，用于构建 HTML 文档。

**初始化:**
```python
b = Buf(encoding='utf-8', newline=True)
```

**主要方法:**
- `_write(line)`: 写入内容到缓冲区
- `__lshift__(obj)`: 使用 `<<` 操作符添加内容
- `__getattr__(name)`: 动态创建标签对象

**示例:**
```python
b = Buf()
b << 'Hello'
b << Tag('br', None)
print(str(b))  # 输出: Hello<br />
```

### 3. Tag 类

HTML 标签类，支持上下文管理器和链式调用。

**初始化:**
```python
tag = Tag(tag_name, _value=DefaultValue, encoding='utf-8', newline=False, attrs=None, **kwargs)
```

**使用方式:**

1. **直接调用:**
```python
div = Tag('div', 'Hello World', _class='container')
```

2. **上下文管理器 (with 语句):**
```python
with Tag('div', _class='container') as div:
    div << '<p>Content</p>'
```

3. **链式调用:**
```python
Tag('a', 'Link', href='#').span('Text')
```

### 4. Div 类

`<div>` 标签的专用实现，继承自 `Tag` 类。

```python
div = Div('Content', _class='demo', style='display: none')
```

### 5. Builder 类

用于构建多个代码部分的工具类。

**初始化:**
```python
b = Builder('begin', 'body', 'end')
```

**使用示例:**
```python
b = Builder('header', 'content', 'footer')
b.header << '<h1>Title</h1>'
b.content << '<p>Main content</p>'
b.footer << '<footer>Footer</footer>'
print(b.text)  # 输出完整的 HTML
```

### 6. 辅助函数

#### begin_tag(tag, **kwargs)
生成开始标签。

```python
begin_tag('div', _class='container')  # 输出: <div class="container">
```

#### end_tag(tag)
生成结束标签。

```python
end_tag('div')  # 输出: </div>
```

#### Table(data, head=None, **kwargs)
生成 HTML 表格。

**参数:**
- `data`: 表格数据（二维列表）
- `head`: 表头数据（列表）
- `**kwargs`: 表格属性

**示例:**
```python
data = [['A1', 'B1'], ['A2', 'B2']]
head = ['Column A', 'Column B']
table = Table(data, head, _class='table')
```

## 使用示例

### 基本用法

```python
from uliweb.core.html import Buf, Tag

# 创建简单的 HTML
b = Buf()
with b.html:
    with b.head:
        b.title('My Page')
    with b.body:
        b.h1('Welcome')
        b.p('This is a paragraph.')
print(str(b))
```

### 创建表单

```python
form = Tag('form', method='post', action='/submit')
with form:
    Tag('input', type='text', name='username', placeholder='Username')
    Tag('input', type='password', name='password', placeholder='Password')
    Tag('input', type='submit', value='Login')
```

### 构建复杂布局

```python
# 使用 Builder 构建多部分内容
layout = Builder('header', 'main', 'sidebar', 'footer')

layout.header << '''
<header>
    <nav>Navigation</nav>
</header>
'''

layout.main << '''
<main>
    <article>Main content</article>
</main>
'''

print(layout.text)
```

## 注意事项

1. **编码处理:** 默认使用 UTF-8 编码，支持 Unicode 字符串
2. **属性转义:** 自动对属性值进行 HTML 转义，除了 `href` 和 `src` 属性
3. **空值处理:** 对于 `id`, `for`, `class` 属性，如果值为 None 则不生成该属性
4. **性能考虑:** 使用 StringIO 进行字符串构建，效率较高

## 高级特性

### 动态标签创建

```python
b = Buf()
# 动态创建任意标签
b.custom_tag('Content', _class='special')  # 创建 <custom_tag class="special">Content</custom_tag>
```

### 混合内容添加

```python
b = Buf()
b << 'Text content'
b << Tag('br', None)
b << ['Multiple', 'Items', Tag('span', 'inline')]
```

## 常见问题

**Q: 如何创建自闭合标签？**
A: 将 `_value` 参数设置为 `None`:
```python
Tag('br', None)  # 输出: <br />
Tag('img', None, src='image.jpg')  # 输出: <img src="image.jpg" />
```

**Q: 如何添加多个类？**
A: 使用字符串拼接或列表:
```python
Tag('div', _class='class1 class2')  # 多个类用空格分隔
```

**Q: 如何避免属性转义？**
A: 对于 `href` 和 `src` 属性，系统会自动避免转义。

这个模块提供了强大而灵活的 HTML 生成能力，是 Uliweb 框架视图层的重要组成部分。
