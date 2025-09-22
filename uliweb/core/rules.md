# Uliweb URL路由规则系统

## 概述

`rules.py` 是 Uliweb 框架中用于处理 URL 路由规则的核心模块。它提供了装饰器和函数来定义、管理和合并 URL 路由规则，支持 RESTful 风格的路由、应用前缀、子域名等高级功能。

## 核心概念

### URL 路由规则
URL 路由规则定义了 URL 路径与处理函数之间的映射关系。当用户访问特定 URL 时，框架会根据这些规则找到对应的处理函数。

### 装饰器模式
通过 `@expose` 装饰器，可以方便地将函数或类方法暴露为 URL 路由端点。

## 主要组件

### 全局变量

- `__exposes__`: 存储需要暴露的路由规则
- `__no_need_exposed__`: 存储不需要额外暴露的路由规则
- `__app_rules__`: 存储应用级别的路由规则
- `__url_route_rules__`: 存储 URL 路由替换规则
- `__url_names__`: 存储 URL 名称到端点的映射
- `reserved_keys`: 保留关键字列表，不能用作路由名称

### 核心函数

#### `expose(rule=None, **kwargs)`
路由装饰器函数，用于将函数或类方法暴露为 URL 路由端点。

**参数:**
- `rule`: URL 规则路径，可选
- `restful`: 是否使用 RESTful 风格，默认为 False
- `replace`: 是否替换现有规则，默认为 False
- `template`: 模板路径，可选
- `layout`: 布局模板，可选
- `**kwargs`: 其他传递给路由规则的参数

**示例:**
```python
@expose('/hello')
def hello():
    return 'Hello World'

@expose('/user/<id>')
def user_detail(id):
    return f'User {id}'
```

#### `merge_rules()`
合并所有路由规则，生成最终的路由表。

#### `add_rule(map, url, endpoint=None, **kwargs)`
向路由映射中添加单个规则。

#### `clear_rules()`
清空所有路由规则。

#### `set_app_rules(rules=None)`
设置应用级别的路由规则。

#### `set_urlroute_rules(rules=None)`
设置 URL 路由替换规则。

### Expose 类

`Expose` 类是 `@expose` 装饰器的核心实现，提供了丰富的路由配置选项。

#### 构造函数参数

- `rule`: URL 规则路径
- `restful`: 是否使用 RESTful 风格
- `replace`: 是否替换现有规则
- `template`: 模板路径
- `layout`: 布局模板
- `**kwargs`: 其他路由参数

#### 主要方法

- `_get_app_prefix(appname)`: 获取应用前缀
- `_get_app_subdomin(appname)`: 获取应用子域名
- `_fix_url(appname, rule)`: 修正 URL 路径
- `_fix_route(rule)`: 应用路由替换规则
- `parse(f)`: 解析函数或类
- `parse_function(f)`: 解析函数
- `parse_class(f)`: 解析类

## 使用示例

### 基本路由

```python
from uliweb.core.rules import expose

@expose('/index')
def index():
    return 'Welcome to index page'

@expose('/user/<username>')
def user_profile(username):
    return f'Profile of {username}'
```

### RESTful 风格路由

```python
@expose('/api/users', restful=True)
class UserAPI:
    def GET(self):
        return 'List all users'

    def POST(self):
        return 'Create a new user'

    def PUT(self, id):
        return f'Update user {id}'
```

### 应用前缀

```python
# 设置应用规则
set_app_rules({
    'myapp': {'prefix': '/admin'}
})

@expose('/dashboard')
def dashboard():
    return 'Admin dashboard'
# 最终访问路径为: /admin/dashboard
```

### 模板和布局

```python
@expose('/page', template='mypage.html', layout='admin_layout.html')
def my_page():
    return {'title': 'My Page', 'content': 'Hello'}
```

## 高级功能

### 子域名支持

```python
set_app_rules({
    'api': {'subdomain': 'api'}
})

@expose('/users')
def users():
    return 'API users endpoint'
# 可通过 api.example.com/users 访问
```

### URL 路由替换

```python
set_urlroute_rules({
    '/old-path': '/new-path'
})

@expose('/old-path')
def old_handler():
    return 'This is now mapped to /new-path'
```

## 注意事项

1. 避免使用保留关键字作为路由名称（如 settings, request, response 等）
2. RESTful 风格的路由会自动根据 HTTP 方法调用对应的类方法
3. 应用前缀和子域名功能需要在应用配置中正确设置
4. 路由规则的顺序可能影响匹配结果，后添加的规则优先级更高

## 错误处理

### ReservedKeyError
当尝试使用保留关键字作为路由名称时抛出此异常。

```python
try:
    @expose('/settings')  # 'settings' 是保留关键字
    def settings():
        pass
except ReservedKeyError as e:
    print(f"Error: {e}")
```

## 最佳实践

1. 使用有意义的 URL 路径和路由名称
2. 合理组织 RESTful API 的路由结构
3. 利用应用前缀和子域名功能组织大型应用
4. 为复杂路由添加适当的文档说明
5. 使用模板和布局参数简化视图函数
