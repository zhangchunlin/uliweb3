# uliweb/core/js.py 模块文档

## 概述

`js.py` 模块是 Uliweb 框架的 JSON 编码工具，提供了自定义的 JSON 编码功能，支持 Python 2 和 Python 3 的兼容性处理，以及特殊数据类型的序列化。

## 主要功能

### 1. 转义处理

#### ESCAPE 正则表达式
```python
ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
```
用于匹配需要转义的控制字符和特殊字符。

#### ESCAPE_DCT 转义字典
包含常见字符的转义映射：
- `\` → `\\`
- `"` → `\"`
- `\b` → `\\b`
- `\f` → `\\f`
- `\n` → `\\n`
- `\r` → `\\r`
- `\t` → `\\t`
- 控制字符 (0x00-0x1F) → Unicode 转义格式

### 2. 核心函数

#### encode_basestring(s)
将 Python 字符串编码为 JSON 字符串格式。

**参数:**
- `s`: 要编码的字符串

**返回值:** JSON 格式的字符串

**示例:**
```python
result = encode_basestring('Hello "World"')  # 返回 '"Hello \"World\""'
```

#### encode_unicode(s)
将 Python Unicode 字符串编码为 JSON 字符串格式，处理 Python 2/3 兼容性。

**参数:**
- `s`: 要编码的 Unicode 字符串

**返回值:** JSON 格式的字符串

#### simple_value(v)
处理特殊数据类型的值转换。

**支持的转换:**
- 可调用对象: 调用函数获取返回值
- LazyString 对象: 转换为字符串
- Decimal 对象: 转换为字符串
- datetime 对象: 转换为字符串
- 其他类型: 直接返回

### 3. JSONEncoder 类

自定义 JSON 编码器类，提供灵活的 JSON 序列化功能。

#### 构造函数
```python
def __init__(self, encoding='utf-8', unicode=False, default=None)
```

**参数:**
- `encoding`: 编码格式，默认为 'utf-8'
- `unicode`: 是否使用 Unicode 编码，默认为 False
- `default`: 自定义值处理函数，默认为 None

#### 主要方法

##### iterencode(obj, key=False)
生成器方法，迭代编码对象为 JSON 字符串片段。

**参数:**
- `obj`: 要编码的对象
- `key`: 是否为字典键编码，默认为 False

**支持的编码类型:**
- 字符串 (str 和 unicode)
- None → 'null'
- True → 'true'
- False → 'false'
- 整数和浮点数
- 列表和元组
- 字典
- Decimal 对象
- datetime 对象
- 其他对象: 转换为字符串后编码

##### encode(obj)
将对象编码为完整的 JSON 字符串。

**参数:**
- `obj`: 要编码的对象

**返回值:** JSON 字符串

### 4. json_dumps 函数

便捷函数，用于将 Python 对象转换为 JSON 字符串。

```python
def json_dumps(obj, unicode=False, **kwargs)
```

**参数:**
- `obj`: 要序列化的 Python 对象
- `unicode`: 是否使用 Unicode 编码，默认为 False
- `**kwargs`: 传递给 JSONEncoder 的其他参数

**返回值:** JSON 字符串

## 使用示例

### 基本用法

```python
from uliweb.core.js import json_dumps

# 编码基本数据类型
data = {'name': 'John', 'age': 30, 'active': True}
json_str = json_dumps(data)
# 输出: '{"name": "John", "age": 30, "active": true}'

# 编码包含特殊字符的字符串
text = 'Line 1\nLine 2\tTab'
json_str = json_dumps(text)
# 输出: '"Line 1\\nLine 2\\tTab"'
```

### 处理特殊数据类型

```python
from decimal import Decimal
from datetime import datetime

data = {
    'price': Decimal('19.99'),
    'timestamp': datetime(2023, 10, 15, 14, 30, 45),
    'date': datetime(2023, 10, 15).date(),
    'time': datetime(2023, 10, 15, 14, 30, 45).time()
}

json_str = json_dumps(data)
# 输出: '{"price": "19.99", "timestamp": "2023-10-15 14:30:45", "date": "2023-10-15", "time": "14:30:45"}'
```

### 自定义编码器

```python
from uliweb.core.js import JSONEncoder

# 创建自定义编码器
encoder = JSONEncoder(unicode=True, default=simple_value)

class CustomObject:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"Custom: {self.value}"

data = {'obj': CustomObject('test')}
json_str = encoder.encode(data)
# 输出: '{"obj": "Custom: test"}'
```

## 特性说明

### Python 2/3 兼容性

模块使用 `uliweb.utils._compat` 中的兼容性工具来处理 Python 2 和 Python 3 的差异：
- `callable`: 检测对象是否可调用
- `integer_types`: 整数类型
- `iteritems`: 字典迭代
- `u`: Unicode 处理
- `text_type`: 文本类型
- `PY2`: Python 2 检测标志

### 特殊字符转义

自动处理以下特殊字符的转义：
- 控制字符 (0x00-0x1F)
- 引号 (`"`)
- 反斜杠 (`\`)
- 退格符 (`\b`)
- 换页符 (`\f`)
- 换行符 (`\n`)
- 回车符 (`\r`)
- 制表符 (`\t`)

### 数据类型支持

支持编码的数据类型包括：
- 基本类型: None, bool, int, float
- 字符串类型: str, unicode
- 集合类型: list, tuple, dict
- 数值类型: Decimal
- 时间类型: datetime, date, time
- 其他对象: 通过 `str()` 转换

## 性能考虑

### 生成器设计

`iterencode` 方法使用生成器模式，可以：
- 减少内存使用，特别是处理大型对象时
- 支持流式处理
- 提高编码效率

### 缓存优化

转义字典 `ESCAPE_DCT` 使用预定义的映射，避免重复计算。

## 与标准库对比

### 优势
1. **更好的兼容性**: 处理 Python 2/3 差异
2. **特殊类型支持**: 支持 Decimal 和 datetime 对象
3. **自定义扩展**: 通过 `default` 参数支持自定义序列化
4. **Unicode 控制**: 可控制是否使用 Unicode 编码

### 使用场景
- 需要处理特殊数据类型的 JSON 序列化
- 需要 Python 2/3 兼容的 JSON 编码
- 需要自定义序列化逻辑
- 需要控制 Unicode 编码行为

## 最佳实践

### 处理大型对象

对于大型对象，建议使用 `iterencode` 方法进行流式处理：

```python
from uliweb.core.js import JSONEncoder

encoder = JSONEncoder()
large_data = [...]  # 大型数据集

# 流式处理
with open('output.json', 'w') as f:
    for chunk in encoder.iterencode(large_data):
        f.write(chunk)
```

### 自定义序列化

通过 `default` 参数实现自定义序列化：

```python
def custom_serializer(obj):
    if hasattr(obj, 'to_json'):
        return obj.to_json()
    elif isinstance(obj, set):
        return list(obj)
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

encoder = JSONEncoder(default=custom_serializer)
data = {'set_data': {1, 2, 3}}
json_str = encoder.encode(data)
# 输出: '{"set_data": [1, 2, 3]}'
```

### 错误处理

```python
try:
    json_str = json_dumps(complex_object)
except Exception as e:
    print(f"JSON encoding error: {e}")
    # 处理编码错误
```

## 注意事项

1. **循环引用**: 不支持处理循环引用的对象
2. **自定义对象**: 默认通过 `str()` 转换，可能需要自定义序列化
3. **性能**: 对于简单数据类型，标准库的 `json.dumps` 可能更快
4. **兼容性**: 主要针对 Uliweb 框架内部使用，API 可能变化

这个模块为 Uliweb 框架提供了稳定可靠的 JSON 编码功能，特别适合处理 Web 应用中的数据传输和序列化需求。
