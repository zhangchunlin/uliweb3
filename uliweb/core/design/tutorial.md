# 教程：Uliweb ASGI 中间件开发

> 本文档为《Uliweb ASGI 迁移设计》配套的**实操教程**，收录来自原 `asgi.md` 的"教程式"示例代码：内置中间件、自定义中间件开发、纯 ASGI 中间件、常用中间件示例与最佳实践。
> 相关设计与核心实现见 [`spec.md`](spec.md) §3.8；实现计划见 [`plan.md`](plan.md)。
> 目录：`uliweb/core/design/`

---

## 1. Starlette 内置中间件

Starlette 提供了一系列内置中间件，可以快速为应用添加常用功能。

### 1.1 CORSMiddleware - 跨域资源共享

```python
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette
from starlette.middleware import Middleware

app = Starlette(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "https://example.com",
                "https://www.example.com",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
            ],
            allow_origin_regex=r"https://.*\.example\.com",
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["X-Custom-Header"],
            max_age=600  # 10分钟
        )
    ]
)
```

**配置参数详解：**
- `allow_origins`: 允许的源列表，可以使用正则表达式
- `allow_methods`: 允许的 HTTP 方法
- `allow_headers`: 允许的请求头
- `allow_credentials`: 是否允许携带凭据
- `expose_headers`: 暴露给客户端的响应头
- `max_age`: 预检请求缓存时间（秒）

### 1.2 GZipMiddleware - 响应压缩

```python
from starlette.middleware.gzip import GZipMiddleware

app = Starlette(
    middleware=[
        Middleware(
            GZipMiddleware,
            minimum_size=1000,  # 只压缩大于1KB的响应
            compresslevel=6     # 压缩级别（1-9）
        )
    ]
)
```

### 1.3 HTTPSRedirectMiddleware - HTTPS 重定向

```python
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = Starlette(
    middleware=[
        Middleware(HTTPSRedirectMiddleware)
    ]
)
```

### 1.4 TrustedHostMiddleware - 可信主机验证

```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = Starlette(
    middleware=[
        Middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "example.com",
                "*.example.com",
                "localhost",
                "127.0.0.1"
            ]
        )
    ]
)
```

## 2. 自定义中间件开发（Uliweb 高级接口）

在 Uliweb 中，**推荐使用高级中间件接口**（`async def dispatch(self, request, call_next):`）。

### 2.1 基础中间件开发（请求计时）

```python
from uliweb import Middleware

class TimingMiddleware(Middleware):
    """请求计时中间件示例"""

    async def dispatch(self, request, call_next):
        import time
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        response.headers['X-Process-Time'] = str(process_time)

        return response
```

### 2.2 高级接口（带钩子）

```python
from uliweb import Middleware

class MyAdvancedMiddleware(Middleware):
    """高级中间件接口 - 仿照 Starlette 的 BaseHTTPMiddleware"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        # 初始化中间件配置

    async def dispatch(self, request, call_next):
        # 请求预处理
        await self.before_request(request)

        # 调用下一个中间件或视图函数
        response = await call_next(request)

        # 响应后处理
        response = await self.after_response(request, response)

        return response

    async def before_request(self, request):
        """请求预处理钩子"""
        pass

    async def after_response(self, request, response):
        """响应后处理钩子"""
        return response
```

### 2.3 请求日志记录

```python
from uliweb import Middleware
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api')

class LoggingMiddleware(Middleware):
    """请求日志记录中间件"""

    async def dispatch(self, request, call_next):
        import time
        start_time = time.time()
        logger.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"Request completed: {response.status_code} in {process_time:.3f}s")
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request failed: {str(e)} in {process_time:.3f}s")
            raise
```

## 3. 自定义中间件开发（底层 ASGI 接口）

对于需要更底层控制的场景，使用**底层 ASGI 中间件接口**（`async def __call__(self, scope, receive, send):`）。

### 3.1 基础结构

```python
from uliweb import Middleware
from typing import Dict, Any

class MyASGIMiddleware(Middleware):
    """底层 ASGI 中间件接口"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        # 初始化中间件配置

    async def __call__(self, scope: Dict[str, Any], receive, send):
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 请求预处理
        await self.process_request(scope)

        try:
            # 调用下一个应用
            await self.application(scope, receive, send)
        except Exception as e:
            await self.handle_exception(scope, receive, send, e)

    async def process_request(self, scope):
        """请求预处理"""
        pass

    async def handle_exception(self, scope, receive, send, exception):
        """异常处理"""
        raise exception
```

### 3.2 CORS 中间件（底层接口示例）

```python
from uliweb import Middleware
from starlette.responses import Response

class CORSMiddleware(Middleware):
    """CORS 中间件 - 使用底层 ASGI 接口"""

    def __init__(self, application, settings):
        super().__init__(application, settings)
        self.allow_origins = settings.get_var('CORS/allow_origins', [])
        self.allow_methods = settings.get_var('CORS/allow_methods', ['GET', 'POST', 'PUT', 'DELETE'])
        self.allow_headers = settings.get_var('CORS/allow_headers', ['*'])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        # 包装 send 函数以添加 CORS 头
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.extend([
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", ", ".join(self.allow_methods).encode()),
                    (b"access-control-allow-headers", ", ".join(self.allow_headers).encode()),
                ])
                message["headers"] = headers
            await send(message)

        # 处理预检请求
        if scope["method"] == "OPTIONS":
            await self.handle_preflight(scope, receive, send_with_cors)
        else:
            await self.application(scope, receive, send_with_cors)

    async def handle_preflight(self, scope, receive, send):
        """处理 CORS 预检请求"""
        response = Response(status_code=204)
        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
        response.headers["access-control-max-age"] = "86400"  # 24小时

        await response(scope, receive, send)
```

## 4. 纯 ASGI 中间件（直接实现协议）

```python
from starlette.types import ASGIApp, Scope, Receive, Send
from typing import Dict, Any

class ASGICustomMiddleware:
    """直接实现 ASGI 协议的中间件"""

    def __init__(self, app: ASGIApp, **kwargs):
        self.app = app
        self.config = kwargs

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 创建包装的 send 函数来拦截响应
        send_wrapper = self.create_send_wrapper(scope, send)

        # 请求预处理
        await self.process_request(scope)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            await self.handle_asgi_exception(scope, receive, send, e)

    def create_send_wrapper(self, scope: Scope, send: Send) -> Send:
        async def send_wrapper(message: Dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                await self.process_response_start(scope, message)
            elif message["type"] == "http.response.body":
                await self.process_response_body(scope, message)
            await send(message)
        return send_wrapper

    async def process_request(self, scope: Scope) -> None: pass
    async def process_response_start(self, scope, message): pass
    async def process_response_body(self, scope, message): pass
    async def handle_asgi_exception(self, scope, receive, send, exception): pass
```

## 5. 中间件配置与执行顺序

在 `settings.ini` 中配置中间件：

```ini
[MIDDLEWARES]
# 高级中间件
logging = 'myapp.middleware.LoggingMiddleware', 100
auth = 'uliweb.contrib.auth.middle_auth.AuthMiddle', 200

# 底层 ASGI 中间件
cors = 'myapp.middleware.CORSMiddleware', 50
gzip = 'myapp.middleware.GZipMiddleware', 300
```

中间件按照添加的顺序依次执行，形成处理链：

```python
class MiddlewareA(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware A: Before request")
        response = await call_next(request)
        print("Middleware A: After response")
        return response

class MiddlewareB(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware B: Before request")
        response = await call_next(request)
        print("Middleware B: After response")
        return response

class MiddlewareC(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("Middleware C: Before request")
        response = await call_next(request)
        print("Middleware C: After response")
        return response

# 执行顺序：
# A Before → B Before → C Before → 应用处理 → C After → B After → A After
```

## 6. 常用中间件示例

### 6.1 认证中间件（JWT）

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request, call_next):
        # 跳过认证的路径
        public_paths = ['/login', '/register', '/docs', '/openapi.json']
        if request.url.path in public_paths:
            return await call_next(request)

        # 检查认证头
        auth_header = request.headers.get('authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JSONResponse({'error': 'Authentication required'}, status_code=401)

        # 验证 JWT token
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse({'error': 'Token expired'}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({'error': 'Invalid token'}, status_code=401)

        response = await call_next(request)
        return response
```

### 6.2 日志记录中间件

```python
import logging
from starlette.middleware.base import BaseHTTPMiddleware
import time

logger = logging.getLogger('api')

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} - "
                f"{process_time:.3f}s - {request.method} {request.url.path}"
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - "
                f"{process_time:.3f}s - {request.method} {request.url.path}"
            )
            raise
```

### 6.3 限流中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, List

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute=60, burst_capacity=10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_identifier(self, request):
        # 多种方式识别客户端
        api_key = request.headers.get('x-api-key')
        if api_key:
            return f"api_key:{api_key}"
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        # 使用 IP 地址
        client_ip = request.client.host if request.client else 'unknown'
        return f"ip:{client_ip}"

    def _cleanup_old_requests(self, client_id, window_start):
        # 清理过期请求记录
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time >= window_start
        ]

    async def dispatch(self, request, call_next):
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        window_start = current_time - 60  # 1分钟窗口

        self._cleanup_old_requests(client_id, window_start)

        recent_requests = self.requests[client_id]
        request_count = len(recent_requests)

        # 检查是否超过限制
        if request_count >= self.requests_per_minute + self.burst_capacity:
            return JSONResponse(
                {'error': 'Rate limit exceeded', 'message': 'Too many requests'},
                status_code=429,
                headers={'Retry-After': '60'}
            )
        elif request_count >= self.requests_per_minute:
            # 计算需要等待的时间
            oldest_request = min(recent_requests)
            wait_time = 60 - (current_time - oldest_request)
            if wait_time > 0:
                return JSONResponse(
                    {
                        'error': 'Rate limit exceeded',
                        'message': f'Please wait {wait_time:.1f} seconds',
                        'retry_after': wait_time
                    },
                    status_code=429,
                    headers={'Retry-After': str(int(wait_time))}
                )

        # 记录本次请求
        self.requests[client_id].append(current_time)

        # 添加速率限制头部
        response = await call_next(request)
        response.headers.update({
            'X-RateLimit-Limit': str(self.requests_per_minute),
            'X-RateLimit-Remaining': str(self.requests_per_minute - request_count),
            'X-RateLimit-Reset': str(int(current_time + 60))
        })

        return response
```

### 6.4 请求验证中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import List
import re

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """请求验证中间件示例"""

    def __init__(self, app, required_headers=None, allowed_methods=None):
        super().__init__(app)
        self.required_headers = required_headers or ['user-agent', 'accept']
        self.allowed_methods = allowed_methods or [
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'
        ]
        self.content_type_pattern = re.compile(r'^application/(json|xml|x-www-form-urlencoded)')

    async def dispatch(self, request, call_next):
        validation_result = await self.before_request(request)
        if validation_result is not None:
            return validation_result
        return await call_next(request)

    async def before_request(self, request):
        # 1. 验证 HTTP 方法
        if request.method not in self.allowed_methods:
            return JSONResponse({'error': f'Method {request.method} not allowed'}, status_code=405)

        # 2. 验证必需的请求头
        missing_headers = [h for h in self.required_headers if h not in request.headers]
        if missing_headers:
            return JSONResponse(
                {'error': 'Missing required headers', 'missing_headers': missing_headers},
                status_code=400
            )

        # 3. 验证内容类型（对于有请求体的方法）
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('content-type', '').lower()
            if not content_type:
                return JSONResponse({'error': 'Content-Type header is required'}, status_code=400)
            if not self.content_type_pattern.match(content_type):
                return JSONResponse(
                    {'error': 'Unsupported Content-Type'},
                    status_code=415
                )

        return None
```

### 6.5 响应格式化中间件

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import json
import time

class ResponseFormatterMiddleware(BaseHTTPMiddleware):
    """响应格式化中间件示例"""

    def __init__(self, app, include_timestamp=True, include_request_id=True,
                 success_status_codes=None):
        super().__init__(app)
        self.include_timestamp = include_timestamp
        self.include_request_id = include_request_id
        self.success_status_codes = success_status_codes or [200, 201, 202, 204]

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return await self.after_response(request, response)

    async def after_response(self, request, response):
        if not self.should_format_response(request, response):
            return response

        try:
            content = await self.get_response_content(response)
            data = json.loads(content.decode('utf-8')) if content else None
            formatted = {
                'success': response.status_code in self.success_status_codes,
                'status_code': response.status_code,
                'data': data,
                'meta': {
                    'version': '1.0',
                    'endpoint': str(request.url.path),
                    'method': request.method
                }
            }
            if self.include_timestamp:
                formatted['timestamp'] = time.time()
            if (self.include_request_id and hasattr(request.state, 'request_id')):
                formatted['request_id'] = request.state.request_id
            return JSONResponse(content=formatted, status_code=response.status_code)
        except Exception as e:
            return response

    def should_format_response(self, request, response):
        if response.status_code not in self.success_status_codes:
            return False
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' not in content_type:
            return False
        if response.headers.get('x-formatted') == 'true':
            return False
        return True
```

## 7. 中间件开发最佳实践

### 7.1 选择合适的中间件类型

- **高级接口（`dispatch`）**：适用于大多数 HTTP 请求处理场景。
- **底层 ASGI 接口（`__call__`）**：需要处理 WebSocket、自定义协议或需要更精细控制时。

### 7.2 性能优化

```python
class OptimizedMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # 预编译正则表达式
        self.pattern = re.compile(r'pattern')
        # 缓存计算结果
        self.cache = {}

    async def dispatch(self, request, call_next):
        # 快速路径：跳过不必要的处理
        if self.should_skip(request):
            return await call_next(request)

        # 使用缓存
        cache_key = self.get_cache_key(request)
        if cache_key in self.cache:
            return self.cache[cache_key]

        response = await call_next(request)
        result = await self.process_response(request, response)
        self.cache[cache_key] = result
        return result
```

### 7.3 错误处理

```python
async def dispatch(self, request, call_next):
    try:
        response = await call_next(request)
        return await self.after_response(request, response)
    except SpecificException as e:
        return await self.handle_specific_error(request, e)
    except Exception as e:
        logger.error(f"Unexpected error in middleware: {e}")
        raise
```

### 7.4 状态管理（request.state）

```python
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        user = await self.authenticate(request)
        if user:
            request.state.user = user  # 存储到 request.state
        response = await call_next(request)
        return response

class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        user = getattr(request.state, 'user', None)  # 从 request.state 读取
        if not user:
            return JSONResponse({'error': 'Unauthorized'}, status_code=401)
        if not self.check_permission(user, request.url.path):
            return JSONResponse({'error': 'Forbidden'}, status_code=403)
        response = await call_next(request)
        return response
```
