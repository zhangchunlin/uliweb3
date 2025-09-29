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
import types
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

# 路由收集机制，类似 SimpleFrame.py 中的 __exposes__
__exposes__ = {}
__no_need_exposed__ = []
__url_names__ = {}

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
        # 收集路由信息，而不是直接注册
        from uliweb.utils.date import now
        from uliweb.utils._compat import ismethod, get_class

        # 获取应用名称
        def _get_appname(module_name):
            parts = module_name.split('.')
            # 找到第一个不是 'views' 的部分作为应用名
            for part in parts:
                if part != 'views' and not part.startswith('_'):
                    return part
            return parts[0] if parts else 'unknown'

        # 获取端点名称
        def _get_endpoint(func):
            if ismethod(func):
                _class = get_class(func)
                return '.'.join([_class.__module__, _class.__name__, func.__name__])
            elif callable(func):
                # 直接返回函数对象，而不是字符串端点名
                # 这样在路由匹配时可以直接调用函数
                return func
            else:
                return str(func)

        # 获取应用名和端点
        appname = _get_appname(func.__module__)
        endpoint = _get_endpoint(func)

        # 收集路由信息
        route_info = (appname, endpoint, rule, kwargs, now())
        __no_need_exposed__.append(route_info)

        # 设置函数属性，保持与 SimpleFrame.py 的兼容性
        setattr(func, '__exposed__', True)
        setattr(func, '__no_rule__', rule is None)
        if not hasattr(func, '__old_rule__'):
            setattr(func, '__old_rule__', {})
        getattr(func, '__old_rule__')[rule] = rule
        setattr(func, '__template__', kwargs.get('template'))
        setattr(func, '__layout__', kwargs.get('layout'))
        setattr(func, '__fixed_url__', rule and rule.startswith('!'))

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


def _merge_rules():
    """合并路由规则，类似 SimpleFrame.py 中的 merge_rules 函数"""
    from itertools import chain

    s = []
    index = {}
    for v in sorted(__no_need_exposed__, key=lambda x: x[4]):  # 按时间戳排序
        appname, endpoint, url, kw, timestamp = v
        if 'name' in kw:
            url_name = kw.pop('name')
        else:
            url_name = endpoint
        __url_names__[url_name] = endpoint
        methods = [y.upper() for y in kw.get('methods', [])]
        methods.sort()

        key = url, tuple(methods), kw.get('subdomain')
        i = index.get(key, None)
        if i is not None:
            s[i] = (appname, endpoint, url, kw)
        else:
            s.append((appname, endpoint, url, kw))
            index[key] = len(s) - 1

    return s


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
        # 加载设置
        self.settings = await self._load_settings()

        # 初始化应用
        self.apps = await self._get_apps()
        self.static_views = []

        # 初始化中间件
        self.process_request_classes = []
        self.process_response_classes = []
        self.process_exception_classes = []

        # 初始化环境
        self.env = await self._prepare_env()

        # 初始化模板设置
        self.default_template = pkg.resource_filename('uliweb.core', 'default.html')

        # 处理收集到的路由信息
        await self._init_routes()

        # 标记为已初始化
        self._initialized = True

    async def _init_routes(self):
        """初始化路由，处理收集到的路由信息"""
        # 首先导入视图模块，这样 expose 装饰器才能被调用
        await self._import_views()

        # 合并路由规则
        merged_rules = _merge_rules()

        # 清空现有路由，避免重复
        self.router.routes.clear()
        self.router.router.routes.clear()

        # 注册路由到路由器
        for rule_info in merged_rules:
            appname, endpoint, url, kw = rule_info
            # 转换 Werkzeug 风格路由到 Starlette 风格
            starlette_rule = re.sub(r'<([^:>]+)(?::[^>]+)?>', r'{\1}', url)

            # 处理静态视图
            static = kw.pop('static', None)
            if static:
                self.static_views.append(endpoint)

            # 注册路由
            self.router.add_route(starlette_rule, endpoint, **kw)

    async def _import_views(self):
        """导入视图模块，触发 expose 装饰器的执行"""
        from uliweb.utils.common import myimport
        import importlib
        import sys

        # 添加项目目录到 Python 路径
        if self.project_dir not in sys.path:
            sys.path.insert(0, self.project_dir)

        # 收集所有应用的视图模块
        views_modules = []
        for app in self.apps:
            # 尝试导入 views.py
            try:
                # 应用模块路径应该是相对于项目目录的
                views_module = f"apps.{app}.views"
                myimport(views_module)
                views_modules.append(views_module)
            except ImportError:
                # 如果 views.py 不存在，尝试导入 views 目录下的模块
                try:
                    # 获取应用目录
                    app_dir = self._get_app_dir(app)
                    views_dir = os.path.join(app_dir, 'views')
                    if os.path.exists(views_dir) and os.path.isdir(views_dir):
                        # 导入 views 目录下的所有 Python 文件
                        for filename in os.listdir(views_dir):
                            if filename.endswith('.py') and not filename.startswith('_'):
                                module_name = filename[:-3]  # 去掉 .py 后缀
                                full_module = f"apps.{app}.views.{module_name}"
                                try:
                                    myimport(full_module)
                                    views_modules.append(full_module)
                                except ImportError:
                                    pass
                except Exception:
                    pass
            except Exception:
                pass

    def _get_app_dir(self, app):
        """获取应用目录"""
        from uliweb.core.SimpleFrame import get_app_dir
        return get_app_dir(app)

    async def _load_settings(self):
        """异步加载设置"""
        from uliweb.core.SimpleFrame import get_settings as get_sync_settings

        # 处理 project_dir 为 None 的情况
        project_dir = self.project_dir
        if project_dir is None:
            project_dir = os.getcwd()

        # 使用线程池执行同步的 settings 加载
        loop = asyncio.get_event_loop()
        settings = await loop.run_in_executor(
            None,
            get_sync_settings,
            project_dir,
            self.include_apps,
            self.settings_file,
            self.local_settings_file,
            self.default_settings
        )
        return settings

    async def _get_apps(self):
        """异步获取应用列表"""
        from uliweb.core.SimpleFrame import get_apps as get_sync_apps

        # 使用线程池执行同步的应用获取
        loop = asyncio.get_event_loop()
        apps = await loop.run_in_executor(
            None,
            get_sync_apps,
            self.apps_dir,
            self.include_apps,
            self.settings_file,
            self.local_settings_file
        )
        return apps

    async def _prepare_env(self):
        """异步准备环境"""
        env = {}
        env['url_for'] = self._url_for
        env['redirect'] = redirect
        env['error'] = self._error
        env['application'] = self
        env['settings'] = self.settings
        env['json'] = json
        env['json_dumps'] = json_dumps

        return env

    def _url_for(self, endpoint, **values):
        """URL 生成函数"""
        # 这里需要实现异步版本的 url_for
        # 暂时简单实现
        return f"/{endpoint}"

    def _error(self, message='', errorpage=None, **kwargs):
        """错误处理函数"""
        # 这里需要实现异步版本的 error
        # 暂时简单实现
        from starlette.responses import JSONResponse
        return JSONResponse({'error': message}, status_code=500)

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
        # 确保应用已初始化
        if not self._initialized:
            await self._async_init()

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
        """处理请求的核心方法 - 异步版本"""
        # 设置响应上下文
        response = Response()
        response_token = response_var.set(response)

        # 设置设置上下文
        settings_token = settings_var.set(self.settings)

        # 设置应用上下文
        application_token = application_var.set(self)

        try:
            # 处理 CORS 预检请求
            if self.settings.GLOBAL.DEFAULT_CORS and request.method == "OPTIONS":
                return await self._handle_cors_preflight(request)

            # 路由匹配
            rule, values = await self._match_route(request)

            # 准备请求处理
            mod, handler_cls, handler = self.prepare_request(request, rule)

            # 处理静态视图
            if rule.endpoint in self.static_views:
                response = await self.call_view(mod, handler_cls, handler, request, response, kwargs=values)
            else:
                # 处理中间件
                response = await self._process_middleware(request, response, mod, handler_cls, handler, values)

            # 处理 CORS 响应头
            if self.settings.GLOBAL.DEFAULT_CORS:
                response = await self._add_cors_headers(request, response)

            return response

        except Exception as e:
            return await self._handle_exception(request, e)
        finally:
            # 清理上下文
            response_var.reset(response_token)
            settings_var.reset(settings_token)
            application_var.reset(application_token)

    async def _match_route(self, request):
        """异步路由匹配"""
        # 使用更直接的路由匹配方法
        path = request.url.path
        method = request.method

        # 收集所有匹配的路由
        matched_routes = []

        # 遍历所有路由进行匹配
        for route in self.router.routes:
            if hasattr(route, 'path'):
                # 对于 Starlette Route 对象，使用更直接的方法
                try:
                    route_path = route.path
                    route_methods = getattr(route, 'methods', ['GET'])

                    # 检查路径是否匹配
                    path_matches = self._path_matches(route_path, path)

                    if path_matches:
                        # 检查方法是否匹配
                        if hasattr(route, 'methods'):
                            if method in route.methods:
                                # 提取路径参数
                                path_params = self._extract_path_params(route_path, path)
                                matched_routes.append((route, path_params))
                        else:
                            # 如果没有指定方法，默认匹配 GET
                            if method == 'GET':
                                path_params = self._extract_path_params(route_path, path)
                                matched_routes.append((route, path_params))
                except Exception:
                    # 如果匹配出错，继续尝试下一个路由
                    continue

        # 如果有多个匹配的路由，选择最具体的那个
        if matched_routes:
            # 按路径长度排序，最长的路径最具体
            matched_routes.sort(key=lambda x: len(x[0].path), reverse=True)
            selected_route = matched_routes[0]
            return selected_route

        # 如果没有匹配到路由，抛出 404 异常
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404)

    def _path_matches(self, route_path, request_path):
        """检查路径是否匹配"""
        # 简单的路径匹配逻辑
        if route_path == request_path:
            return True

        # 处理带参数的路径
        import re
        # 将 {param} 转换为正则表达式
        pattern = re.sub(r'\{([^}]+)\}', r'([^/]+)', route_path)
        pattern = '^' + pattern + '$'
        match = re.match(pattern, request_path)
        if match:
            return True

        # 如果正则匹配失败，尝试更简单的匹配
        # 将路径分割成部分进行比较
        route_parts = route_path.strip('/').split('/')
        request_parts = request_path.strip('/').split('/')

        if len(route_parts) != len(request_parts):
            return False

        for route_part, request_part in zip(route_parts, request_parts):
            if route_part.startswith('{') and route_part.endswith('}'):
                # 这是参数部分，可以匹配任何内容
                continue
            elif route_part != request_part:
                return False

        return True

    def _extract_path_params(self, route_path, request_path):
        """提取路径参数"""
        if route_path == request_path:
            return {}

        # 提取路径参数
        import re
        # 获取参数名
        param_names = re.findall(r'\{([^}]+)\}', route_path)
        # 构建匹配模式
        pattern = re.sub(r'\{([^}]+)\}', r'([^/]+)', route_path)
        pattern = '^' + pattern + '$'

        match = re.match(pattern, request_path)
        if match:
            params = {}
            for i, name in enumerate(param_names):
                params[name] = match.group(i + 1)
            return params

        return {}

    def prepare_request(self, request, rule):
        """准备请求处理"""
        endpoint = rule.endpoint if hasattr(rule, 'endpoint') else rule

        # 绑定 endpoint 到 request
        request.rule = rule

        # 获取处理器
        _klass, mod, handler = self.get_handler(endpoint)

        # 设置应用名称
        request.appname = ''
        for p in self.apps:
            t = p + '.'
            if handler.__module__.startswith(t):
                request.appname = p
                break

        request.function = handler.__name__
        if _klass:
            request.view_class = _klass.__class__.__name__
            handler = getattr(_klass, handler.__name__)
        else:
            request.view_class = None

        return mod, _klass, handler

    def get_handler(self, endpoint):
        """获取处理器"""
        from uliweb.utils.common import safe_import
        from uliweb.utils._compat import ismethod, get_class

        # 获取处理器
        _klass = None
        if isinstance(endpoint, str):
            mod, handler = safe_import(endpoint)
            if ismethod(handler):
                _klass = get_class(handler)()
                handler = getattr(_klass, endpoint.split('.')[-1])
        elif callable(endpoint):
            handler = endpoint
            mod = sys.modules[handler.__module__]

        return _klass, mod, handler

    async def call_view(self, mod, cls, handler, request, response=None, wrap_result=None, args=None, kwargs=None):
        """异步调用视图函数"""
        wrap = wrap_result or self.wrap_result
        env = await self.get_view_env()

        # 处理 __begin__ 和 __end__ 钩子
        if not hasattr(request, '_invokes'):
            request._invokes = {'begin': [], 'end': []}

        # 调用 __begin__
        begin_result = await self._process_begin(mod, request, response, env)
        if begin_result is not None:
            return await wrap(handler, begin_result, request, response, env)

        begin_result = await self._process_begin(cls, request, response, env)
        if begin_result is not None:
            return await wrap(handler, begin_result, request, response, env)

        # 预处理 __end__
        mod_end = await self._prepare_end(mod, request)
        cls_end = await self._prepare_end(cls, request)

        # 调用处理器
        result = await self.call_handler(handler, request, response, env, wrap, args, kwargs)

        # 调用 __end__
        if mod_end:
            end_result = await self._process_end(mod, request, response, env)
            if end_result is not None:
                return await wrap(handler, end_result, request, response, env)

        if cls_end:
            end_result = await self._process_end(cls, request, response, env)
            if end_result is not None:
                return await wrap(handler, end_result, request, response, env)

        return result

    async def _process_begin(self, mod, request, response, env):
        """处理 __begin__ 钩子"""
        if hasattr(mod, '__begin__'):
            name = '__begin__'
            _name = self._get_name(mod, name)
            if _name not in request._invokes['begin']:
                request._invokes['begin'].append(_name)
                f = getattr(mod, name)
                return await self._call_function(f, request, response, env)
        return None

    async def _prepare_end(self, mod, request):
        """预处理 __end__ 钩子"""
        if hasattr(mod, '__end__'):
            name = '__end__'
            _name = self._get_name(mod, name)
            if _name not in request._invokes['end']:
                request._invokes['end'].append(_name)
                return True
        return False

    async def _process_end(self, mod, request, response, env):
        """处理 __end__ 钩子"""
        if hasattr(mod, '__end__'):
            f = getattr(mod, '__end__')
            return await self._call_function(f, request, response, env)
        return None

    def _get_name(self, mod, name):
        """获取名称"""
        if isinstance(mod, types.ModuleType):
            return mod.__name__ + '.' + name
        else:
            return mod.__module__ + '.' + mod.__class__.__name__ + '.' + name

    async def get_view_env(self):
        """获取视图环境"""
        # 准备本地环境
        local_env = {}

        # 处理视图调用前的环境准备
        await self._call_dispatch('prepare_view_env', local_env)

        local_env['application'] = get_application()
        local_env['request'] = get_request()
        local_env['response'] = get_response()
        local_env['settings'] = get_settings()

        # 合并环境
        if hasattr(self, 'env') and self.env is not None:
            if hasattr(self.env, 'to_dict'):
                base_env = self.env.to_dict()
            else:
                base_env = dict(self.env) if hasattr(self.env, '__iter__') else {}
        else:
            base_env = {}

        env = Storage(base_env)
        env.update(local_env)
        return env

    async def _call_dispatch(self, topic, *args, **kwargs):
        """异步调用分发器"""
        # 这里需要实现异步的分发器调用
        # 暂时简单实现
        pass

    async def call_handler(self, handler, request, response, env, wrap_result=None, args=None, kwargs=None):
        """异步调用处理器"""
        wrap = wrap_result or self.wrap_result
        result = await self._call_function(handler, request, response, env, args, kwargs)
        return await wrap(handler, result, request, response, env)

    async def _call_function(self, handler, request, response, env, args=None, kwargs=None):
        """异步调用函数"""
        # 更新全局环境
        handler.__globals__.update(env)
        handler.__globals__['env'] = env

        # 准备参数
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        # 检查函数签名，确保传递正确的参数
        import inspect
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())

        # 根据函数签名构建参数
        call_args = []
        call_kwargs = {}

        for param in params:
            if param == 'request':
                call_kwargs['request'] = request
            elif param == 'response':
                call_kwargs['response'] = response
            elif param in kwargs:
                call_kwargs[param] = kwargs[param]
            elif len(args) > 0:
                call_args.append(args[0])
                args = args[1:]

        # 添加剩余的位置参数
        call_args.extend(args)
        # 添加剩余的关键字参数
        call_kwargs.update(kwargs)

        # 检查是否是协程函数
        if iscoroutinefunction(handler):
            result = await handler(*call_args, **call_kwargs)
        else:
            # 同步函数需要在线程池中执行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, handler, *call_args, **call_kwargs)

        # 处理 LocalProxy 响应
        if isinstance(result, LocalProxy) and result._obj_name == 'response':
            result = get_response()

        return result

    async def wrap_result(self, handler, result, request, response, env):
        """异步包装结果"""
        from starlette.responses import Response as StarletteResponse
        from starlette.responses import JSONResponse

        # 如果是字典，检查是否是 API 响应
        if isinstance(result, dict):
            # 检查是否是 API 视图（通过请求路径或视图名称判断）
            is_api_view = (
                request.url.path.startswith('/api/') or
                'api' in handler.__name__.lower() or
                request.headers.get('content-type', '').startswith('application/json') or
                request.is_xhr
            )

            if is_api_view:
                return JSONResponse(result)
            else:
                result = Storage(result)

                # 处理模板渲染
                if hasattr(response, 'template') and response.template:
                    tmpfile = response.template
                else:
                    args = handler.__dict__.get('__template__')
                    if not args:
                        args = {'function': request.function, 'view_class': request.view_class, 'appname': request.appname}

                    if isinstance(args, dict):
                        if request.view_class:
                            tmpfile = self.settings.GLOBAL.TEMPLATE_TEMPLATE[0] % args + self.settings.GLOBAL.TEMPLATE_SUFFIX
                        else:
                            tmpfile = self.settings.GLOBAL.TEMPLATE_TEMPLATE[1] % args + self.settings.GLOBAL.TEMPLATE_SUFFIX
                    else:
                        tmpfile = args
                    response.template = tmpfile

                # 渲染模板
                content = await self._render_template(tmpfile, result, env)
                return StarletteResponse(content, media_type='text/html')

        elif isinstance(result, str):
            return StarletteResponse(result, media_type='text/html')

        elif isinstance(result, StarletteResponse):
            return result

        else:
            return StarletteResponse(str(result), media_type='text/plain')

    async def _render_template(self, template_file, vars, env):
        """异步渲染模板"""
        # 这里需要实现异步模板渲染
        # 暂时简单实现
        return f"Template: {template_file}"

    async def _process_middleware(self, request, response, mod, handler_cls, handler, values):
        """异步处理中间件"""
        # 处理请求中间件
        for middleware in self.process_request_classes:
            middleware_instance = middleware(self, self.settings)
            if hasattr(middleware_instance, 'process_request'):
                middleware_response = await self._call_middleware_method(
                    middleware_instance.process_request, request
                )
                if middleware_response is not None:
                    return middleware_response

        # 调用视图函数
        try:
            view_response = await self.call_view(mod, handler_cls, handler, request, response, kwargs=values)
        except Exception as e:
            # 处理异常中间件
            for middleware in self.process_exception_classes:
                middleware_instance = middleware(self, self.settings)
                if hasattr(middleware_instance, 'process_exception'):
                    exception_response = await self._call_middleware_method(
                        middleware_instance.process_exception, request, e
                    )
                    if exception_response is not None:
                        return exception_response
            raise

        # 处理响应中间件
        for middleware in self.process_response_classes:
            middleware_instance = middleware(self, self.settings)
            if hasattr(middleware_instance, 'process_response'):
                view_response = await self._call_middleware_method(
                    middleware_instance.process_response, request, view_response
                )

        return view_response

    async def _call_middleware_method(self, method, *args):
        """异步调用中间件方法"""
        if iscoroutinefunction(method):
            return await method(*args)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, method, *args)

    async def _handle_cors_preflight(self, request):
        """处理 CORS 预检请求"""
        from starlette.responses import Response
        response = Response(status_code=204)
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = request.headers.get(
            'Access-Control-Request-Headers',
            'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range'
        )
        response.headers['Access-Control-Max-Age'] = str(24 * 3600)
        return response

    async def _add_cors_headers(self, request, response):
        """添加 CORS 响应头"""
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        if 'Origin' in request.headers:
            response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = request.headers.get(
            'Access-Control-Request-Headers',
            'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range'
        )
        return response

    async def _handle_exception(self, request, exception):
        """异步处理异常"""
        from starlette.exceptions import HTTPException
        from starlette.responses import JSONResponse

        if isinstance(exception, HTTPException):
            if exception.status_code == 404:
                return await self._not_found(exception)
            else:
                return JSONResponse(
                    {'error': str(exception)},
                    status_code=exception.status_code
                )
        else:
            if not self.settings.get_var('GLOBAL/DEBUG'):
                return await self._internal_error(exception)
            else:
                # 调试模式下重新抛出异常
                raise

    async def _not_found(self, exception):
        """处理 404 错误"""
        from starlette.responses import JSONResponse
        return JSONResponse(
            {'error': 'Not Found', 'message': str(exception)},
            status_code=404
        )

    async def _internal_error(self, exception):
        """处理 500 错误"""
        from starlette.responses import JSONResponse
        import logging
        logging.exception(exception)
        return JSONResponse(
            {'error': 'Internal Server Error'},
            status_code=500
        )


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
