# Uliweb 事件分发系统

## 概述

`dispatch` 模块实现了 Uliweb 框架的事件分发机制。它允许开发者在应用程序的不同部分之间进行松耦合的通信，通过定义事件主题（topic）和信号（signal）来实现组件间的解耦。

## 常量

模块定义了三个优先级常量，用于控制事件处理函数的执行顺序：

- `HIGH = 1`：高优先级
- `MIDDLE = 2`：中优先级（默认）
- `LOW = 3`：低优先级

## 核心函数

### bind(topic, signal=None, kind=MIDDLE, nice=-1)

事件绑定装饰器，用于将函数注册为特定事件主题的处理函数。

**参数：**
- `topic`：事件主题名称
- `signal`：可选，信号标识符
- `kind`：优先级类型（HIGH, MIDDLE, LOW），默认为 MIDDLE
- `nice`：自定义优先级数值，数值越小优先级越高

**使用示例：**
```python
@bind('init')
def process_init(sender, *args, **kwargs):
    # 处理初始化事件
    pass
```

### unbind(topic, func)

解除事件绑定，从指定主题中移除处理函数。

**参数：**
- `topic`：事件主题名称
- `func`：要移除的处理函数

### call(sender, topic, *args, **kwargs)

调用指定主题的所有处理函数，按优先级顺序执行，不返回值。

**参数：**
- `sender`：事件发送者
- `topic`：事件主题名称
- `*args`：传递给处理函数的位置参数
- `**kwargs`：传递给处理函数的关键字参数

### call_once(sender, topic, *args, **kwargs)

只调用一次指定主题的处理函数，避免重复执行。

**参数：**
- `sender`：事件发送者
- `topic`：事件主题名称
- `*args`：传递给处理函数的位置参数
- `**kwargs`：传递给处理函数的关键字参数

### get(sender, topic, *args, **kwargs)

调用指定主题的处理函数，按优先级顺序执行，返回第一个非 None 的结果。

**参数：**
- `sender`：事件发送者
- `topic`：事件主题名称
- `*args`：传递给处理函数的位置参数
- `**kwargs`：传递给处理函数的关键字参数

**返回值：**
第一个返回非 None 值的处理函数的结果，如果没有则返回 None。

### get_once(sender, topic, *args, **kwargs)

只调用一次指定主题的处理函数，返回结果并缓存。

**参数：**
- `sender`：事件发送者
- `topic`：事件主题名称
- `*args`：传递给处理函数的位置参数
- `**kwargs`：传递给处理函数的关键字参数

**返回值：**
处理函数的结果。

### reset()

重置所有事件绑定和调用记录，清空内部状态。

### print_topics()

调试函数，打印所有已注册的事件主题和处理函数信息。

## 使用示例

### 基本事件绑定和调用

```python
from uliweb.core.dispatch import bind, call

@bind('user_login')
def on_user_login(sender, user):
    print(f"User {user} logged in")

# 触发事件
call(None, 'user_login', 'john')
```

### 使用优先级

```python
from uliweb.core.dispatch import bind, HIGH, MIDDLE, LOW, call

@bind('init', kind=HIGH)
def high_priority_init(sender):
    print("High priority init")

@bind('init', kind=LOW)
def low_priority_init(sender):
    print("Low priority init")

@bind('init', kind=MIDDLE)
def middle_priority_init(sender):
    print("Middle priority init")

# 调用时会按优先级顺序执行：high_priority_init -> middle_priority_init -> low_priority_init
call(None, 'init')
```

### 带信号的事件处理

```python
from uliweb.core.dispatch import bind, call

@bind('model_save', signal='User')
def on_user_save(sender):
    print("User model saved")

@bind('model_save', signal='Product')
def on_product_save(sender):
    print("Product model saved")

# 只会触发 on_user_save
call(None, 'model_save', signal='User')
```

### 获取返回值

```python
from uliweb.core.dispatch import bind, get

@bind('calculate')
def calculate_a(sender, x, y):
    return None  # 不处理

@bind('calculate')
def calculate_b(sender, x, y):
    return x + y  # 处理并返回结果

# result 将是 5
result = get(None, 'calculate', 2, 3)
