"""
Uliweb Starlette 集成模块
提供从 Werkzeug 到 Starlette 的迁移支持
"""

from __future__ import print_function, absolute_import

import os
import sys
import re
import contextvars
import asyncio
from inspect import iscoroutinefunction
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile, FormData
from starlette.routing import Route, Router, Mount
from starlette.applications import Starlette
import json as jsn

from . import template
from .js import json_dumps
from . import dispatch
from uliweb.utils.storage import Storage
from uliweb.utils.common import (pkg, log, import_attr,
    myimport, wraps, norm_path)
import uliweb.utils.pyini as pyini
from uliweb.i18n import gettext_lazy, i18n_ini_convertor
from uliweb.utils.localproxy import LocalProxy, Global
from uliweb import UliwebError
from uliweb.utils._compat import html_escape, isresponse

# 使用 contextvars 替代 threading.local
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')
settings_var = contextvars.ContextVar('settings')
application_var = contextvars.ContextVar('application')

# 初始化 pyini 环境
pyini.set_env({
    'env':{'_':gettext_lazy, 'gettext_lazy':gettext_lazy},
    'convertors':i18n_ini_convertor,
})

class Request(StarletteRequest):
    """基于 Starlette 的 Request 类，保持与现有 Uliweb 的兼容性"""

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

    @property
    def params(self):
        """兼容 params 属性，合并 GET 和 POST 参数"""
        # 注意：在异步环境中需要特殊处理
        return self.query_params


class Response(StarletteResponse):
    """基于 Starlette 的 Response 类，保持与现有 Uliweb 的兼容性"""

    def write(self, value):
        """兼容 write 方法"""
        # 在异步环境中，write 方法需要特殊处理
        # 这里暂时保持接口兼容性
        pass


class UliwebRouter:
    """Uliweb 路由适配器，将 Werkzeug 风格路由转换为 Starlette 风格"""

    def __init__(self):
        self.routes = []
        self.url_map = {}
        self.router = Router()

    def add_route(self, rule, endpoint, **kwargs):
        """转换 Werkzeug 风格路由到 Starlette 风格"""
        # 转换参数格式: <name> -> {name}
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)

        methods = kwargs.get('methods', ['GET'])
        name = kwargs.get('name')

        # 创建 Starlette 路由
        route = Route(starlette_rule, endpoint, methods=methods, name=name)

        self.routes.append(route)
        self.url_map[endpoint] = route
        self.router.routes.append(route)

        return route

    def add_websocket_route(self, rule, endpoint, **kwargs):
        """添加 WebSocket 路由"""
        starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', rule)
        name = kwargs.get('name')

        from starlette.routing import WebSocketRoute
        route = WebSocketRoute(starlette_rule, endpoint, name=name)

        self.routes.append(route)
        self.url_map[endpoint] = route
        self.router.routes.append(route)

        return route

    def mount(self, path, app, name=None):
        """挂载子应用"""
        mount = Mount(path, app=app, name=name)
        self.router.routes.append(mount)
        return mount


def expose(rule=None, **kwargs):
    """适配现有的 expose 装饰器"""
    def decorator(func):
        # 自动检测函数类型并注册到路由
        app = application_var.get(None)
        if app and hasattr(app, 'router'):
            if kwargs.get('websocket', False):
                app.router.add_websocket_route(rule, func, **kwargs)
            else:
                app.router.add_route(rule, func, **kwargs)
        return func
    return decorator


def POST(rule, **kw):
    """POST 方法装饰器"""
    kw['methods'] = ['POST']
    return expose(rule, **kw)


def GET(rule, **kw):
    """GET 方法装饰器"""
    kw['methods'] = ['GET']
    return expose(rule, **kw)


class AsyncDispatcher:
    """支持 ASGI 3.0 接口的异步 Dispatcher"""

    def __init__(self, apps_dir='apps', project_dir=None, include_apps=None,
                 start=True, default_settings=None, settings_file='settings.ini',
                 local_settings_file='local_settings.ini', **kwargs):

        self.apps_dir = apps_dir
        self.project_dir = project_dir
        self.include_apps = include_apps or []
        self.default_settings = default_settings or {}
        self.settings_file = settings_file
        self.local_settings_file = local_settings_file
        self.router = UliwebRouter()
        self._initialized = False

        if start:
            # 异步初始化
            asyncio.create_task(self._async_init())

    async def _async_init(self):
        """异步初始化方法"""
        if not self._initialized:
            await self.init()
            self._initialized = True

    async def init(self):
        """初始化 ASGI 应用"""
        # 这里需要实现配置加载、应用初始化等逻辑
        # 暂时保持简单实现
        pass

    async def __call__(self, scope, receive, send):
        """ASGI 3.0 接口实现"""
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
        else:
            raise ValueError(f"Unsupported scope type: {scope['type']}")

    async def handle_http(self, scope, receive, send):
        """处理 HTTP 请求"""
        request = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request_var.set(request)

        try:
            # 处理请求
            response = await self._open(request)
            await response(scope, receive, send)
        finally:
            # 清理上下文
            request_var.reset(request_token)

    async def handle_websocket(self, scope, receive, send):
        """处理 WebSocket 请求"""
        from starlette.websockets import WebSocket
        websocket = WebSocket(scope, receive, send)

        # 设置 WebSocket 上下文
        websocket_token = request_var.set(websocket)

        try:
            await websocket.accept()
            # 这里可以添加 WebSocket 处理逻辑
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                # 处理消息
                await self._handle_websocket_message(websocket, message)
        finally:
            request_var.reset(websocket_token)

    async def _handle_websocket_message(self, websocket, message):
        """处理 WebSocket 消息"""
        # 默认实现：回显消息
        if message["type"] == "websocket.receive":
            await websocket.send_text(f"Echo: {message.get('text', '')}")

    async def _open(self, request):
        """处理请求的核心方法"""
        # 这里需要实现路由匹配、视图调用等逻辑
        # 暂时返回一个简单的响应
        from starlette.responses import JSONResponse
        return JSONResponse({"message": "Hello from ASGI Uliweb"})


class ASGIApplication:
    """纯 ASGI 应用处理器"""

    def __init__(self, project_dir=None):
        self.project_dir = project_dir
        self.asgi_app = None
        self._initialized = False

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            # 处理 project_dir 为 None 的情况
            if self.project_dir is None:
                # 尝试获取当前工作目录作为默认项目目录
                self.project_dir = os.getcwd()

            # 创建 ASGI Dispatcher
            self.asgi_app = AsyncDispatcher(
                apps_dir=os.path.join(self.project_dir, 'apps'),
                project_dir=self.project_dir
            )
            self._initialized = True

    async def __call__(self, scope, receive, send):
        """ASGI 接口"""
        self._initialize()
        await self.asgi_app(scope, receive, send)


# 上下文管理中间件
async def context_middleware(app):
    """管理请求上下文的中间件"""
    async def middleware(scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive, send)
            token = request_var.set(request)
            try:
                response = await app(scope, receive, send)
                return response
            finally:
                request_var.reset(token)
        else:
            return await app(scope, receive, send)
    return middleware


# 全局代理对象，保持与现有代码的兼容性
def get_request():
    """获取当前请求对象"""
    return request_var.get(None)

def get_response():
    """获取当前响应对象"""
    return response_var.get(None)

def get_settings():
    """获取当前设置对象"""
    return settings_var.get(None)

def get_application():
    """获取当前应用对象"""
    return application_var.get(None)


# 创建全局代理对象
# 使用与 SimpleFrame.py 相同的 LocalProxy 格式
request = LocalProxy(get_request, 'request', Request)
response = LocalProxy(get_response, 'response', Response)
settings = LocalProxy(get_settings, 'settings', pyini.Ini)
application = LocalProxy(get_application, 'application', ASGIApplication)


# 兼容性函数
def redirect(location, code=302):
    """重定向函数"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=location, status_code=code)


def json(data, **kwargs):
    """JSON 响应函数"""
    from starlette.responses import JSONResponse
    return JSONResponse(data, **kwargs)


# 导出主要类和方法
__all__ = [
    'Request',
    'Response',
    'UliwebRouter',
    'AsyncDispatcher',
    'ASGIApplication',
    'expose',
    'POST',
    'GET',
    'context_middleware',
    'redirect',
    'json'
]
