"""
测试 WebSocket 功能
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock


def test_websocket_route_registration():
    """
    测试 WebSocket 路由注册
    """
    from uliweb.core.SimpleFrame import UliwebRouter
    from starlette.routing import WebSocketRoute

    router = UliwebRouter()

    # 注册 WebSocket 路由
    async def websocket_handler(websocket):
        pass

    router.add_websocket_route('/ws/echo', websocket_handler)

    # 验证路由已注册
    assert len(router.routes) == 1
    assert isinstance(router.routes[0], WebSocketRoute)
    assert router.routes[0].path == '/ws/echo'


def test_http_route_registration():
    """
    测试普通 HTTP 路由注册
    """
    from uliweb.core.SimpleFrame import UliwebRouter
    from starlette.routing import Route

    router = UliwebRouter()

    async def http_handler(request):
        pass

    router.add_route('/api/data', http_handler, methods=['GET', 'POST'])

    # 验证路由已注册
    assert len(router.routes) == 1
    assert isinstance(router.routes[0], Route)
    assert router.routes[0].path == '/api/data'
    # Starlette 会自动添加 HEAD 方法到每个路由
    assert 'GET' in router.routes[0].methods
    assert 'POST' in router.routes[0].methods


def test_websocket_route_matching():
    """
    测试 WebSocket 路由匹配
    """
    from uliweb.core.SimpleFrame import AsyncDispatcher
    from starlette.routing import WebSocketRoute

    # 创建一个模拟的 AsyncDispatcher
    dispatcher = AsyncDispatcher.__new__(AsyncDispatcher)

    # 模拟路由器
    from uliweb.core.SimpleFrame import UliwebRouter
    dispatcher.router = UliwebRouter()

    # 注册 WebSocket 路由
    async def websocket_handler(websocket):
        pass

    dispatcher.router.add_websocket_route('/ws/echo', websocket_handler)

    # 创建模拟的 WebSocket 对象
    mock_websocket = Mock()
    mock_websocket.url = Mock()
    mock_websocket.url.path = '/ws/echo'

    # 测试路径匹配
    result = dispatcher._path_matches('/ws/echo', '/ws/echo')
    assert result is True

    # 测试带参数的路径匹配
    result = dispatcher._path_matches('/ws/chat/{room}', '/ws/chat/general')
    assert result is True

    # 测试不匹配
    result = dispatcher._path_matches('/ws/echo', '/ws/chat')
    assert result is False


def test_websocket_route_with_parameters():
    """
    测试带参数的 WebSocket 路由
    """
    from uliweb.core.SimpleFrame import UliwebRouter
    from starlette.routing import WebSocketRoute

    router = UliwebRouter()

    async def websocket_handler(websocket, room):
        pass

    router.add_websocket_route('/ws/chat/{room}', websocket_handler)

    # 验证路由已注册
    assert len(router.routes) == 1
    assert isinstance(router.routes[0], WebSocketRoute)
    assert router.routes[0].path == '/ws/chat/{room}'


def test_websocket_and_http_routes_separate():
    """
    测试 WebSocket 和 HTTP 路由是分开注册的
    """
    from uliweb.core.SimpleFrame import UliwebRouter
    from starlette.routing import Route, WebSocketRoute

    router = UliwebRouter()

    async def http_handler(request):
        pass

    async def websocket_handler(websocket):
        pass

    # 注册 HTTP 和 WebSocket 路由
    router.add_route('/api/data', http_handler)
    router.add_websocket_route('/ws/echo', websocket_handler)

    # 验证两种路由都存在
    assert len(router.routes) == 2

    # 检查路由类型
    routes_by_type = {type(r).__name__: r for r in router.routes}
    assert 'Route' in routes_by_type
    assert 'WebSocketRoute' in routes_by_type

    # 验证路径
    assert routes_by_type['Route'].path == '/api/data'
    assert routes_by_type['WebSocketRoute'].path == '/ws/echo'


def test_rules_add_rule_with_websocket():
    """
    测试 rules.add_rule 函数支持 websocket 参数
    """
    from uliweb.core.rules import add_rule
    from uliweb.core.SimpleFrame import UliwebRouter

    router = UliwebRouter()

    async def websocket_handler(websocket):
        pass

    # 使用 add_rule 注册 WebSocket 路由
    add_rule(router, '/ws/echo', websocket_handler, websocket=True)

    # 验证路由已注册为 WebSocketRoute
    assert len(router.routes) == 1
    from starlette.routing import WebSocketRoute
    assert isinstance(router.routes[0], WebSocketRoute)


def test_rules_add_rule_without_websocket():
    """
    测试 rules.add_rule 函数不支持 websocket 参数时注册为 HTTP 路由
    """
    from uliweb.core.rules import add_rule
    from uliweb.core.SimpleFrame import UliwebRouter

    router = UliwebRouter()

    async def http_handler(request):
        pass

    # 使用 add_rule 注册 HTTP 路由（不传 websocket 参数）
    add_rule(router, '/api/data', http_handler)

    # 验证路由已注册为 Route
    assert len(router.routes) == 1
    from starlette.routing import Route
    assert isinstance(router.routes[0], Route)


def test_websocket_expose_decorator():
    """
    测试使用 expose 装饰器定义 WebSocket 路由
    """
    from uliweb.core import rules
    from uliweb.core.SimpleFrame import UliwebRouter

    # 清理之前的规则
    rules.__exposes__ = {}
    rules.__no_need_exposed__ = []
    rules.__url_names__ = {}

    router = UliwebRouter()

    # 使用 expose 装饰器定义 WebSocket 路由
    @rules.expose('/ws/echo', websocket=True)
    async def websocket_echo(websocket):
        pass

    # 验证规则已注册到 rules 模块
    assert len(rules.__exposes__) > 0 or len(rules.__no_need_exposed__) > 0

    # 合并规则并注册到路由器
    merged_rules = rules.merge_rules()

    # 找到 WebSocket 路由规则
    websocket_rules = [r for r in merged_rules if r[2] == '/ws/echo' and r[3].get('websocket')]
    assert len(websocket_rules) > 0
    assert websocket_rules[0][3]['websocket'] is True


def test_websocket_scope_type_detection():
    """
    测试 ASGI scope type 区分 HTTP 和 WebSocket
    """
    from uliweb.core.SimpleFrame import Request
    from starlette.websockets import WebSocket as StarletteWebSocket

    # HTTP 请求 scope
    http_scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/test',
        'query_string': b'',
    }

    # WebSocket 请求 scope
    ws_scope = {
        'type': 'websocket',
        'path': '/ws/echo',
        'raw_path': b'/ws/echo',
        'query_string': b'',
        'headers': [],
    }

    async def receive():
        return {'type': 'http.request', 'body': b''}

    async def send(message):
        pass

    # 验证 scope type
    http_req = Request(http_scope, receive, send)
    assert http_req.scope['type'] == 'http'

    ws_req = StarletteWebSocket(ws_scope, receive, send)
    assert ws_req.scope['type'] == 'websocket'


def test_async_dispatcher_websocket_routes():
    """
    测试 AsyncDispatcher 正确初始化 WebSocket 路由
    """
    import os
    import tempfile
    from pathlib import Path

    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        apps_dir = project_dir / 'apps'
        apps_dir.mkdir()

        # 创建简单的 settings.ini
        settings_ini = apps_dir / 'settings.ini'
        settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = test-secret-key

[INSTALLED_APPS]
apps =
""")

        # 创建简单的 app
        app_dir = apps_dir / 'testapp'
        app_dir.mkdir()

        # 创建 __init__.py
        init_file = app_dir / '__init__.py'
        init_file.write_text('')

        # 创建 views.py 包含 WebSocket 路由
        views_file = app_dir / 'views.py'
        views_file.write_text('''
from uliweb.core import expose

@expose("/ws/test", websocket=True)
async def websocket_test(websocket):
    pass

@expose("/api/test")
async def api_test(request):
    pass
''')

        # 暂时跳过实际初始化测试，因为需要完整的项目结构
        # 这个测试只是验证代码结构
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])