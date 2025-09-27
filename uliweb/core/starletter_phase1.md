# Uliweb 迁移到 Starlette - 阶段一：基础架构迁移详细任务清单

## 概述
阶段一主要完成 Uliweb 从 Werkzeug 到 Starlette 的基础架构迁移，包括核心 Request/Response 对象迁移、ASGI 接口实现和基本路由系统迁移。

## 详细任务清单

### 1. 核心 Request/Response 对象迁移

#### 1.1 Request 对象迁移
- [ ] 创建基于 `starlette.requests.Request` 的新 Request 类
- [ ] 实现向后兼容的 GET 属性（返回 `self.query_params`）
- [ ] 实现异步 POST 属性（使用 `await self.form()` 获取表单数据）
- [ ] 实现异步 FILES 属性（过滤上传文件）
- [ ] 实现异步 json 属性（使用 `await self.json()`）
- [ ] 保持 is_xhr 属性兼容性（检查 XMLHttpRequest 头）
- [ ] 实现 params 属性兼容性（合并 GET 和 POST 参数）

#### 1.2 Response 对象迁移
- [ ] 创建基于 `starlette.responses.Response` 的新 Response 类
- [ ] 保持现有响应方法和属性的兼容性
- [ ] 支持异步响应生成

### 2. ASGI 接口实现

#### 2.1 Dispatcher 类重构
- [ ] 将现有的 WSGI `__call__` 方法迁移到 ASGI 接口
- [ ] 支持 HTTP 请求处理（scope["type"] == "http"）
- [ ] 支持 WebSocket 请求处理（scope["type"] == "websocket"）
- [ ] 实现异步请求处理流程

#### 2.2 ASGI 应用适配器
- [ ] 创建 ASGI 3.0 兼容的应用接口
- [ ] 处理请求范围（scope）、接收（receive）和发送（send）参数
- [ ] 实现错误处理和异常捕获

### 3. 基本路由系统迁移

#### 3.1 路由适配器实现
- [ ] 创建 UliwebRouter 类来管理路由
- [ ] 实现 `add_route` 方法，将 Werkzeug 风格路由转换为 Starlette 风格
- [ ] 处理路由参数格式转换（`<name>` -> `{name}`）
- [ ] 支持多种 HTTP 方法（GET、POST、PUT、DELETE 等）

#### 3.2 路由注册机制
- [ ] 保持现有 `@expose` 装饰器接口不变
- [ ] 内部映射到 Starlette 路由系统
- [ ] 支持异步视图函数注册
- [ ] 支持 WebSocket 路由注册

#### 3.3 URL 生成和反向解析
- [ ] 实现 URL 反向解析功能
- [ ] 保持现有 URL 生成接口兼容性
- [ ] 支持带参数的 URL 生成

### 4. 依赖管理和配置

#### 4.1 依赖包安装
- [ ] 添加 starlette 依赖到项目配置
- [ ] 添加 anyio 依赖用于同步到异步转换
- [ ] 添加 aiofiles 依赖用于异步文件操作
- [ ] 添加 asgiref 依赖用于 WSGI 到 ASGI 转换
- [ ] 添加 uvicorn 或 hypercorn 作为 ASGI 服务器选项

#### 4.2 配置设置
- [ ] 添加 ASGI_MODE 配置开关（默认 False）
- [ ] 配置默认运行模式（WSGI 或 ASGI）
- [ ] 设置 ASGI 服务器配置选项（uvicorn、hypercorn、daphne）
- [ ] 配置 ASGI 主机、端口和工作进程数
- [ ] 设置相关中间件和组件配置

### 5. 基础测试验证

#### 5.1 单元测试
- [ ] 编写 Request/Response 对象迁移的单元测试
- [ ] 测试 ASGI 接口的正确性
- [ ] 验证路由系统的功能

#### 5.2 集成测试
- [ ] 测试基本的 HTTP 请求处理
- [ ] 验证路由匹配和参数解析
- [ ] 测试错误处理和异常捕获

### 6. 文档和示例

#### 6.1 使用文档
- [ ] 更新阶段一迁移的使用说明
- [ ] 提供异步视图函数编写示例
- [ ] 说明配置和启动方式
- [ ] 添加双模式运行说明文档
- [ ] 提供配置示例和最佳实践

#### 6.2 代码示例
- [ ] 提供基本的异步视图示例
- [ ] 展示路由注册的代码示例
- [ ] 演示请求处理的异步模式
- [ ] 提供双模式应用配置示例
- [ ] 展示 WebSocket 处理示例

## 技术实现要点

### 关键代码变更

1. **Request 类迁移**：
```python
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile, FormData
import json

class Request(StarletteRequest):
    """保持向后兼容的 Request 对象"""

    @property
    def GET(self):
        """兼容 GET 参数访问"""
        return self.query_params

    @property
    async def POST(self):
        """异步获取 POST 表单数据"""
        if self.method == "POST":
            form = await self.form()
            return form
        return {}

    @property
    async def FILES(self):
        """异步获取上传文件"""
        if self.method == "POST":
            form = await self.form()
            return {k: v for k, v in form.items() if isinstance(v, UploadFile)}
        return {}

    @property
    async def json(self):
        """异步获取 JSON 数据"""
        return await self.json()

    @property
    def is_xhr(self):
        """检查是否为 AJAX 请求"""
        return self.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'
```

2. **Dispatcher ASGI 接口**：
```python
class Dispatcher:
    """支持 ASGI 3.0 接口的 Dispatcher"""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive, send)
            response = await self._open(request)
            await response(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")
```

3. **路由适配器**：
```python
from starlette.routing import Route, Router, Mount
from starlette.applications import Starlette

class UliwebRouter:
    def __init__(self):
        self.routes = []
        self.url_map = {}

    def add_route(self, rule, endpoint, **kwargs):
        """转换 Werkzeug 风格路由到 Starlette 风格"""
        # 转换参数格式: <name> -> {name}
        import re
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)

        methods = kwargs.get('methods', ['GET'])
        route = Route(starlette_rule, endpoint, methods=methods)

        self.routes.append(route)
        self.url_map[endpoint] = route
        return route

# 适配现有的 expose 装饰器
def expose(rule=None, **kwargs):
    def decorator(func):
        # 自动检测函数类型并注册到路由
        app = application_var.get()
        app.router.add_route(rule, func, **kwargs)
        return func
    return decorator
```

## 验收标准

- [ ] Request/Response 对象保持向后兼容
- [ ] ASGI 接口正确处理 HTTP 和 WebSocket 请求
- [ ] 路由系统支持现有 @expose 装饰器用法
- [ ] 基本功能测试通过
- [ ] 配置开关可以控制运行模式

## 注意事项

1. 保持向后兼容性，确保现有代码不需要大量修改
2. 异步操作需要使用适当的错误处理
3. 线程安全考虑，特别是在混合同步和异步代码时
4. 性能监控，确保迁移后性能不会下降
5. 全局状态管理需要使用 contextvars 替代 threading.local
6. 确保请求上下文在异步环境中正确传递
7. 注意同步到异步转换时的阻塞操作处理

## 下一步工作

完成阶段一后，可以继续进行：
- 阶段二：功能完整性（中间件、模板、会话等）
- 阶段三：性能优化（数据库、缓存等）
- 阶段四：生态兼容（插件、第三方库等）
