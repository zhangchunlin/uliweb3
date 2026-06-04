# coding=utf-8
"""
测试 SSE 流式响应不被中间件缓冲

验证当响应类型为 text/event-stream 时，中间件的 call_next 函数能够正确检测
并返回 None，让框架直接使用原始的 send 函数发送响应，从而实现真正的流式传输。
"""
import pytest
import tempfile
import shutil
import sys
from pathlib import Path


def cleanup_rules():
    """清理 rules.__exposes__ 和模块缓存"""
    from uliweb.core import rules
    from uliweb.core.SimpleFrame import __app_dirs__, __app_alias__

    rules.__exposes__.clear()
    rules.__url_names__.clear()
    rules.__no_need_exposed__[:] = []

    __app_dirs__.clear()
    __app_alias__.clear()

    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('testsseapp')]
    for mod in modules_to_remove:
        del sys.modules[mod]


def create_temp_project():
    """创建临时测试项目"""
    tmpdir = tempfile.mkdtemp()
    project_dir = Path(tmpdir)
    apps_dir = project_dir / 'apps'
    apps_dir.mkdir()

    # 创建 settings.ini
    settings_ini = apps_dir / 'settings.ini'
    settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testsseapp",
]
""")

    # 创建 app
    app_dir = apps_dir / 'testsseapp'
    app_dir.mkdir()

    # 创建 __init__.py
    (app_dir / '__init__.py').write_text('')

    # 添加 project_dir 到 sys.path
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    return project_dir, apps_dir, app_dir


def cleanup_temp_project(project_dir):
    """清理临时测试项目"""
    try:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))
    except ValueError:
        pass
    finally:
        shutil.rmtree(str(project_dir), ignore_errors=True)


class TestSSEStreamingDetection:
    """SSE 流式响应检测测试类"""

    def setUp(self):
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    setup_method = setUp
    teardown_method = tearDown

    def test_sse_content_type_detection(self):
        """测试 SSE Content-Type 检测"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建包含 SSE 端点的 views.py
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose
from starlette.responses import Response

@expose("/sse/stream")
async def sse_stream():
    """SSE 流式响应端点"""
    async def stream_generator():
        yield b"data: first chunk\\n\\n"
        yield b"data: second chunk\\n\\n"

    return SSEStreamResponse(stream_generator())


class SSEStreamResponse(Response):
    """模拟 SSE 流式响应"""
    def __init__(self, generator):
        self.generator = generator
        super().__init__(
            content=b"",
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"Content-Type", b"text/event-stream"],
                [b"Cache-Control", b"no-cache"],
                [b"Connection", b"keep-alive"],
            ],
        })
        async for chunk in self.generator:
            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True,
            })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 验证 SSE 路由已注册
        route_paths = [r.path for r in dispatcher.router.routes]
        assert '/sse/stream' in route_paths

    def test_call_next_returns_none_for_sse(self):
        """测试 call_next 对 SSE 响应返回 None"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 SSE 视图
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose
from starlette.responses import Response

@expose("/sse/test")
async def sse_test():
    """SSE 流式响应端点"""
    return SSEStreamResponse()


class SSEStreamResponse(Response):
    """模拟 SSE 流式响应"""
    def __init__(self):
        super().__init__(
            content=b"",
            media_type="text/event-stream",
        )

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"Content-Type", b"text/event-stream"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"data: test\\n\\n",
            "more_body": True,
        })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 模拟 ASGI 调用
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/sse/test",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def mock_send(message):
            received_messages.append(message)

        # 调用应用
        import asyncio
        asyncio.run(dispatcher(scope, mock_receive, mock_send))

        # 验证响应
        assert len(received_messages) > 0
        assert received_messages[0]["type"] == "http.response.start"
        assert received_messages[0]["status"] == 200

        # 验证 Content-Type 是 text/event-stream
        headers = dict(received_messages[0]["headers"])
        content_type = headers.get(b"Content-Type", b"").decode()
        assert "text/event-stream" in content_type

        # 验证消息体是流式发送的（多个 body 消息）
        body_messages = [m for m in received_messages if m["type"] == "http.response.body"]
        assert len(body_messages) >= 2  # 至少有一个数据块和结束消息


class TestMiddlewareStreamingPassthrough:
    """中间件流式响应透传测试类"""

    def setUp(self):
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    setup_method = setUp
    teardown_method = tearDown

    def test_middleware_with_sse_response(self):
        """测试带中间件的 SSE 响应"""
        from uliweb import Middleware
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建自定义中间件
        (self.app_dir / 'middlewares.py').write_text('''
from uliweb import Middleware

class TestMiddleware(Middleware):
    """测试中间件"""
    async def dispatch(self, request, call_next):
        # 中间件处理
        response = await call_next(request)
        return response
''')

        # 更新 settings.ini 添加中间件
        settings_ini = self.apps_dir / 'settings.ini'
        settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testsseapp",
]

[MIDDLEWARES]
test_middleware = 'testsseapp.middlewares.TestMiddleware', 100
""")

        # 创建 SSE 视图
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose
from starlette.responses import Response

@expose("/sse/middleware")
async def sse_with_middleware():
    """带中间件的 SSE 端点"""
    return SSEStreamResponse()


class SSEStreamResponse(Response):
    """模拟 SSE 流式响应"""
    def __init__(self):
        super().__init__(
            content=b"",
            media_type="text/event-stream",
        )

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"Content-Type", b"text/event-stream"],
            ],
        })
        # 模拟流式发送多个数据块
        for i in range(3):
            await send({
                "type": "http.response.body",
                "body": f"data: chunk {i}\\n\\n".encode(),
                "more_body": True,
            })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 模拟 ASGI 调用
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/sse/middleware",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def mock_send(message):
            received_messages.append(message)

        # 调用应用
        import asyncio
        asyncio.run(dispatcher(scope, mock_receive, mock_send))

        # 验证响应
        assert len(received_messages) > 0
        assert received_messages[0]["type"] == "http.response.start"

        # 验证 Content-Type 是 text/event-stream
        headers = dict(received_messages[0]["headers"])
        content_type = headers.get(b"Content-Type", b"").decode()
        assert "text/event-stream" in content_type

        # 验证消息体是流式发送的（应该有多个数据块）
        body_messages = [m for m in received_messages if m["type"] == "http.response.body"]
        # 应该有 4 个 body 消息：3 个数据块 + 1 个结束空消息
        assert len(body_messages) == 4

        # 验证数据块内容
        for i in range(3):
            assert f"chunk {i}".encode() in body_messages[i]["body"]


class TestNonStreamingResponse:
    """非流式响应测试类"""

    def setUp(self):
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    setup_method = setUp
    teardown_method = tearDown

    def test_html_response_not_streaming(self):
        """测试 HTML 响应不被识别为流式响应"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 HTML 视图
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/html/page")
async def html_page():
    """HTML 页面端点"""
    return "<html><body>Hello World</body></html>"
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 模拟 ASGI 调用
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/html/page",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def mock_send(message):
            received_messages.append(message)

        # 调用应用
        import asyncio
        asyncio.run(dispatcher(scope, mock_receive, mock_send))

        # 验证响应
        assert len(received_messages) > 0
        assert received_messages[0]["type"] == "http.response.start"

        # 验证响应状态
        assert received_messages[0]["status"] == 200

        # 验证消息体存在
        body_messages = [m for m in received_messages if m["type"] == "http.response.body"]
        assert len(body_messages) >= 1

        # 验证 HTML 内容
        body = body_messages[0].get("body", b"").decode()
        assert "Hello World" in body


class TestSSEResponseNotDuplicated:
    """SSE 响应不重复发送测试类

    验证修复：当 SSE 响应通过 call_next 发送后，不会再次发送响应。
    这解决了 "Unexpected ASGI message 'http.response.start' sent, after response already completed" 错误。
    """

    def setUp(self):
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    setup_method = setUp
    teardown_method = tearDown

    def test_sse_response_sent_only_once(self):
        """测试 SSE 响应只被发送一次，不会重复发送"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建自定义中间件（模拟 SessionMiddleware 的行为）
        (self.app_dir / 'middlewares.py').write_text('''
from uliweb import Middleware

class TestMiddleware(Middleware):
    """测试中间件，模拟 SessionMiddleware 的行为"""
    async def dispatch(self, request, call_next):
        # 中间件调用 call_next
        response = await call_next(request)
        return response
''')

        # 更新 settings.ini 添加中间件
        settings_ini = self.apps_dir / 'settings.ini'
        settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testsseapp",
]

[MIDDLEWARES]
test_middleware = 'testsseapp.middlewares.TestMiddleware', 100
""")

        # 创建 SSE 视图（模拟 chatbot 的欢迎消息）
        (self.app_dir / 'views.py').write_text("""
from uliweb import expose
from starlette.responses import Response

@expose("/sse/welcome")
async def sse_welcome():
    \"\"\"SSE 欢迎消息端点\"\"\"
    return SSEWelcomeResponse()


class SSEWelcomeResponse(Response):
    \"\"\"模拟 SSE 欢迎消息响应\"\"\"
    def __init__(self):
        super().__init__(
            content=b"",
            media_type="text/event-stream",
        )

    async def __call__(self, scope, receive, send):
        # 发送 HTTP 响应开始
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"Content-Type", b"text/event-stream"],
                [b"Cache-Control", b"no-cache"],
                [b"Connection", b"keep-alive"],
            ],
        })
        # 发送欢迎消息
        await send({
            "type": "http.response.body",
            "body": b'data: {\"type\": \"welcome\", \"message\": \"Hello!\"}\\n\\n',
            "more_body": True,
        })
        # 发送结束消息
        await send({
            "type": "http.response.body",
            "body": b'data: [DONE]\\n\\n',
            "more_body": False,
        })
""")

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 模拟 ASGI 调用
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/sse/welcome",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def mock_send(message):
            received_messages.append(message)

        # 调用应用
        import asyncio
        asyncio.run(dispatcher(scope, mock_receive, mock_send))

        # 验证响应只被发送一次
        start_messages = [m for m in received_messages if m["type"] == "http.response.start"]
        assert len(start_messages) == 1, f"Expected 1 start message, got {len(start_messages)}"

        # 验证 Content-Type 是 text/event-stream
        headers = dict(start_messages[0]["headers"])
        content_type = headers.get(b"Content-Type", b"").decode()
        assert "text/event-stream" in content_type

        # 验证消息体是流式发送的
        body_messages = [m for m in received_messages if m["type"] == "http.response.body"]
        assert len(body_messages) == 2, f"Expected 2 body messages, got {len(body_messages)}"

        # 验证数据内容
        assert b"welcome" in body_messages[0]["body"]
        assert b"[DONE]" in body_messages[1]["body"]

        # 验证没有重复发送的错误
        # 如果响应被重复发送，会抛出异常或收到多个 start 消息
        print(f"Total messages received: {len(received_messages)}")
        print(f"Message types: {[m['type'] for m in received_messages]}")

    def test_sse_with_multiple_middlewares(self):
        """测试多层中间件下 SSE 响应只被发送一次"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建多个自定义中间件
        (self.app_dir / 'middlewares.py').write_text('''
from uliweb import Middleware

class Middleware1(Middleware):
    """第一个测试中间件"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return response

class Middleware2(Middleware):
    """第二个测试中间件"""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        return response
''')

        # 更新 settings.ini 添加多个中间件
        settings_ini = self.apps_dir / 'settings.ini'
        settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testsseapp",
]

[MIDDLEWARES]
middleware1 = 'testsseapp.middlewares.Middleware1', 100
middleware2 = 'testsseapp.middlewares.Middleware2', 200
""")

        # 创建 SSE 视图
        (self.app_dir / 'views.py').write_text("""
from uliweb import expose
from starlette.responses import Response

@expose("/sse/multi")
async def sse_multi():
    \"\"\"多层中间件下的 SSE 端点\"\"\"
    return SSEMultiResponse()


class SSEMultiResponse(Response):
    \"\"\"模拟 SSE 响应\"\"\"
    def __init__(self):
        super().__init__(
            content=b"",
            media_type="text/event-stream",
        )

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"Content-Type", b"text/event-stream"],
            ],
        })
        # 发送多个数据块
        for i in range(3):
            await send({
                "type": "http.response.body",
                "body": f"data: chunk {i}\\n\\n".encode(),
                "more_body": True,
            })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
""")

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testsseapp']
        dispatcher.prepare()

        # 模拟 ASGI 调用
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/sse/multi",
            "query_string": b"",
            "headers": [],
            "root_path": "",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def mock_send(message):
            received_messages.append(message)

        # 调用应用
        import asyncio
        asyncio.run(dispatcher(scope, mock_receive, mock_send))

        # 验证响应只被发送一次
        start_messages = [m for m in received_messages if m["type"] == "http.response.start"]
        assert len(start_messages) == 1, f"Expected 1 start message with multiple middlewares, got {len(start_messages)}"

        # 验证消息体是流式发送的
        body_messages = [m for m in received_messages if m["type"] == "http.response.body"]
        assert len(body_messages) == 4, f"Expected 4 body messages (3 chunks + 1 empty), got {len(body_messages)}"

        # 验证数据块内容
        for i in range(3):
            assert f"chunk {i}".encode() in body_messages[i]["body"]

        print(f"Multiple middlewares - Total messages: {len(received_messages)}")
        print(f"Message types: {[m['type'] for m in received_messages]}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
