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
import logging
from inspect import iscoroutinefunction
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.datastructures import UploadFile, FormData
from starlette.routing import Route, Router, Mount
from starlette.applications import Starlette
import json as jsn

# 创建日志记录器
logger = logging.getLogger('uliweb')

from . import template
from .js import json_dumps
from . import dispatch
from uliweb.utils.storage import Storage
from uliweb.utils.common import (pkg, log, import_attr,
    myimport, wraps, norm_path)
import uliweb.utils.pyini as pyini
from uliweb.i18n import gettext_lazy, i18n_ini_convertor
from uliweb.utils.localproxy import LocalProxy, Global
# 避免循环导入，直接从 SimpleFrame 导入或定义错误类
try:
    from .SimpleFrame import UliwebError
except ImportError:
    # 如果 SimpleFrame 还未加载，定义一个临时错误类
    class UliwebError(Exception):
        """Uliweb 基础错误类"""
        pass

# Middleware 不再需要，因为已迁移到 ASGI 中间件系统
Middleware = None

from uliweb.utils._compat import html_escape, isresponse

# 使用共享的 contextvars
from .context import request_var, response_var, settings_var, application_var

# 初始化 pyini 环境
pyini.set_env({
    'env':{'_':gettext_lazy, 'gettext_lazy':gettext_lazy},
    'convertors':i18n_ini_convertor,
})

# 导入 rules 模块，使用统一的路由收集机制
from . import rules
from uliweb.utils.sorteddict import SortedDict

# 将 rules 模块的接口导出到当前模块
__exposes__ = rules.__exposes__
__no_need_exposed__ = rules.__no_need_exposed__
__url_names__ = rules.__url_names__

# 兼容其他模块直接访问 merge_rules 的需求
def merge_rules():
    """合并路由规则"""
    return rules.merge_rules()


def _convert_route_param(rule):
    """正确转换路由参数，处理 <type:name> 格式

    返回: (转换后的规则, 参数类型字典)
    例如: '/api/users/<int:user_id>' -> ('/api/users/{user_id}', {'user_id': 'int'})
    """
    param_types = {}

    def replacer(m):
        param = m.group(1)
        if ':' in param:
            param_type, param_name = param.split(':', 1)
            param_types[param_name] = param_type
            return '{' + param_name + '}'
        else:
            return '{' + param + '}'

    converted_rule = re.sub(r'<([^>]+)>', replacer, rule)
    return converted_rule, param_types


class Request(StarletteRequest):
    """基于 Starlette 的 Request 类，保持与现有 Uliweb 的兼容性"""

    @property
    def GET(self):
        """兼容 GET 参数访问"""
        return self.query_params

    @property
    def state(self):
        """获取请求状态容器

        支持 scope['state'] 状态管理，这是 ASGI 架构的核心特性。
        允许中间件和应用程序在请求处理过程中存储和共享状态数据。

        使用示例：

        ```python
        # 在中间件中设置状态
        request.state.user = current_user

        # 在后续处理中获取状态
        current_user = request.state.user
        ```

        :return: 请求状态字典
        """
        # 初始化 state 容器（如果不存在）
        if 'state' not in self.scope:
            self.scope['state'] = {}
        return self.scope['state']

    async def get_POST(self):
        """异步获取 POST 表单数据"""
        if self.method == "POST":
            form = await self.form()
            return form
        return {}

    async def get_FILES(self):
        """异步获取上传文件"""
        if self.method == "POST":
            form = await self.form()
            return {k: v for k, v in form.items() if isinstance(v, UploadFile)}
        return {}

    async def get_json(self):
        """异步获取 JSON 数据"""
        return await super().json()

    async def get_params(self):
        """异步获取合并参数（强制异步方法，避免阻塞）"""
        # 由于 POST 数据需要异步读取，params 必须也是异步方法
        get_params = self.query_params
        post_params = await self.get_POST()

        # 合并 GET 和 POST 参数
        merged_params = {}
        merged_params.update(get_params)
        merged_params.update(post_params)
        return merged_params

    @property
    def is_xhr(self):
        """检查是否为 AJAX 请求"""
        return self.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'

    @property
    def path(self):
        """获取请求路径"""
        return self.url.path

    @property
    def method(self):
        """获取请求方法"""
        return self.scope.get("method", "")

    # 向后兼容的同步属性（标记为已弃用）
    @property
    def POST(self):
        """已弃用：同步访问 POST 数据会抛出异常"""
        raise RuntimeError(
            "POST 属性已弃用，请使用 await request.get_POST() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def FILES(self):
        """已弃用：同步访问 FILES 数据会抛出异常"""
        raise RuntimeError(
            "FILES 属性已弃用，请使用 await request.get_FILES() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def json(self):
        """已弃用：同步访问 JSON 数据会抛出异常"""
        raise RuntimeError(
            "json 属性已弃用，请使用 await request.get_json() 方法。"
            "同步代码可以使用同步适配器机制。"
        )

    @property
    def params(self):
        """兼容 params 属性，返回 GET 参数

        注意：由于 POST 数据需要异步读取，此属性仅返回 GET (query) 参数。
        如需合并 GET 和 POST 参数，请在异步视图函数中：

        ```python
        @expose('/api/data')
        async def async_view():
            get_params = dict(request.query_params)
            post_params = dict(await request.get_POST())
            all_params = {**get_params, **post_params}
            return all_params
        ```
        """
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
    """适配现有的 expose 装饰器

    使用 rules 模块的 Expose 类来处理 URL 规则
    """
    # 使用 rules 模块的 Expose 类来处理规则
    # 这会调用 parse 方法，将路由信息添加到 __no_need_exposed__
    e = rules.Expose(rule, **kwargs)

    # Expose 类会返回：
    # - 如果 parse_level==1 (直接装饰函数)，返回原始函数
    # - 如果 parse_level==2 (有 rule)，返回装饰后的函数

    def decorator(func):
        # 调用 Expose 的 parse 方法来处理函数
        e.parse(func)

        # 设置函数属性，保持与 SimpleFrame.py 的兼容性
        setattr(func, '__exposed__', True)
        setattr(func, '__no_rule__', e.parse_level == 1 or (e.parse_level == 2 and (rule is None)))
        if not hasattr(func, '__old_rule__'):
            setattr(func, '__old_rule__', {})
        getattr(func, '__old_rule__')[rule] = rule
        setattr(func, '__template__', e.template)
        setattr(func, '__layout__', e.layout)
        setattr(func, '__fixed_url__', rule and rule.startswith('!') if rule else False)

        return func

    # 根据 parse_level 返回不同的结果
    if e.parse_level == 1:
        # 没有 rule，直接返回函数
        return lambda f: e.parse(f) or f
    else:
        # 有 rule，返回装饰器
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
    # 同时遍历 __no_need_exposed__ 和 __exposes__
    all_rules = __no_need_exposed__ + list(chain(*__exposes__.values()))
    for v in sorted(all_rules, key=lambda x: x[4]):  # 按时间戳排序
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

        # 将项目目录和 apps 目录添加到 sys.path
        # 这样 pkg_resources 能找到本地的应用模块
        if project_dir:
            if project_dir not in sys.path:
                sys.path.insert(0, project_dir)
            # 将 apps 目录添加到 sys.path，以便 apps.home 这样的模块可以被找到
            apps_path = os.path.join(project_dir, apps_dir)
            if apps_path not in sys.path:
                sys.path.insert(0, apps_path)

        self.apps_dir = apps_dir
        self.project_dir = project_dir
        self.include_apps = include_apps or []
        self.default_settings = default_settings or {}
        self.settings_file = settings_file
        self.local_settings_file = local_settings_file
        self.router = UliwebRouter()
        self._initialized = False
        self._middleware_stack = None
        # 存储路由的参数类型信息：{route_path: {param_name: param_type}}
        self.route_param_types = {}

        # 无论 start 是 True 还是 False，都需要加载 settings
        # 这样在命令行环境中（如测试）也可以使用 functions 等
        # 注意：这里不能在已有事件循环的情况下创建新事件循环
        # 需要延迟加载或在第一次请求时加载
        try:
            import asyncio

            # 检查是否已经有运行中的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 如果已经有运行中的事件循环，延迟加载 settings
                # 在 _async_init 中会重新加载
                self.settings = None
            except RuntimeError:
                # 没有运行中的事件循环，可以安全创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # 同步加载 settings
                self.settings = loop.run_until_complete(self._load_settings())
                # 同步加载 apps 列表，以便 ASGI 中间件可以在初始化时访问
                # 这解决了静态文件等中间件在初始化时需要访问 apps 的问题
                # 注意：必须在 loop.close() 之前调用
                try:
                    self.apps = loop.run_until_complete(self._get_apps())
                except Exception:
                    self.apps = []
                loop.close()

            # 总是将 settings 设置到 contextvars 中，即使为 None
            # 这样可以避免 settings proxy 访问时出错
            settings_token = settings_var.set(self.settings)
            # 同时设置 application 到 contextvars
            application_token = application_var.set(self)
        except Exception as e:
            # 如果加载失败，记录错误
            import logging
            logging.getLogger('uliweb').warning(f"Failed to load settings during init: {e}")
            # 创建一个空的 settings 对象以避免后续错误
            from uliweb.utils.pyini import Ini
            self.settings = Ini()

        if start:
            # 异步初始化将在第一次请求时进行
            pass

    async def _async_init(self):
        """异步初始化方法"""
        if not self._initialized:
            await self.init()
            # 初始化路由
            await self._init_routes()
            self._initialized = True

    async def init(self):
        """初始化 ASGI 应用"""
        # 加载设置
        self.settings = await self._load_settings()

        # 将 settings 重新设置到 contextvars 中
        # 因为在 __init__ 中可能设置为 None，现在需要更新为实际加载的值
        settings_var.set(self.settings)
        application_var.set(self)

        # 初始化应用
        self.apps = await self._get_apps()
        self.static_views = []

        # 初始化中间件
        self.process_request_classes = []
        self.process_response_classes = []
        self.process_exception_classes = []

        # 初始化中间件列表
        self.middlewares = []

        # 初始化中间件配置
        self._init_middlewares()

    async def _handle_request(self, scope, receive, send):
        """处理请求的核心逻辑"""
        from starlette.exceptions import HTTPException
        from starlette.websockets import WebSocket

        # 根据 scope type 判断是 HTTP 还是 WebSocket
        if scope["type"] == "websocket":
            return await self._handle_websocket_request(scope, receive, send)

        request = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request_var.set(request)

        try:
            # 路由匹配
            rule, values = await self._match_route(request)
            mod, handler_cls, handler = self.prepare_request(request, rule)

            # 处理请求
            response = await self._open(request)
            await response(scope, receive, send)
        except (HTTPException, RuntimeError) as exc:
            # 处理 HTTP 异常（如 404）
            response = await self._handle_exception(request, exc)
            await response(scope, receive, send)
        finally:
            # 清理上下文
            request_var.reset(request_token)

    async def _handle_websocket_request(self, scope, receive, send):
        """处理 WebSocket 请求的核心逻辑"""
        from starlette.exceptions import HTTPException
        from starlette.websockets import WebSocket as StarletteWebSocket

        logger.warning(f"[Core WebSocket] _handle_websocket_request called, path: {scope.get('path', 'unknown')}")
        logger.warning(f"[Core WebSocket] scope: {scope}")

        websocket = StarletteWebSocket(scope, receive, send)

        # 设置 WebSocket 上下文
        websocket_token = request_var.set(websocket)

        try:
            # 路由匹配
            logger.warning(f"[Core WebSocket] Starting route matching for: {websocket.url.path}")
            route, values = await self._match_websocket_route(websocket)
            logger.warning(f"[Core WebSocket] Route matched: {route}, values: {values}")

            # 将 route 对象绑定到 websocket，以便 _open_websocket 可以访问
            websocket.rule = route

            # 准备请求处理
            mod, handler_cls, handler = self.prepare_request(websocket, route)

            # 调用视图处理 WebSocket
            await self._open_websocket(websocket)
        except (HTTPException, RuntimeError) as exc:
            # 处理异常
            await self._handle_websocket_exception(websocket, exc)
        finally:
            # 清理上下文
            request_var.reset(websocket_token)

    async def _match_websocket_route(self, websocket):
        """匹配 WebSocket 路由"""
        from starlette.routing import WebSocketRoute

        path = websocket.url.path

        # 遍历所有路由进行匹配
        for route in self.router.routes:
            # 只处理 WebSocketRoute 对象
            if not isinstance(route, WebSocketRoute):
                continue
            try:
                route_path = route.path

                # 检查路径是否匹配
                if self._path_matches(route_path, path):
                    # 提取路径参数
                    path_params = self._extract_path_params(route_path, path)
                    return route, path_params
            except Exception:
                continue

        # 如果没有找到匹配的路由，抛出 404 错误
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="WebSocket route not found")

    async def _open_websocket(self, websocket):
        """处理 WebSocket 连接的打开和消息循环"""
        from starlette.responses import JSONResponse

        # 从 route 获取 endpoint (处理函数)
        rule = getattr(websocket, 'rule', None)
        if rule and hasattr(rule, 'endpoint'):
            endpoint = rule.endpoint

            # 检查 endpoint 是否是协程函数
            if iscoroutinefunction(endpoint):
                # 尝试不同的调用方式
                try:
                    # 方式1: 直接传递 websocket 对象
                    await endpoint(websocket)
                except TypeError:
                    try:
                        # 方式2: ASGI 风格 (scope, receive, send)
                        await endpoint(websocket.scope, websocket._receive, websocket._send)
                    except Exception:
                        # 方式3: 使用默认处理
                        await self.handle_websocket(websocket.scope, websocket._receive, websocket._send)
            else:
                # 同步函数需要在协程池中执行
                import functools
                from contextvars import copy_context
                loop = asyncio.get_event_loop()
                ctx = copy_context()

                try:
                    partial_handler = functools.partial(endpoint, websocket)
                    await loop.run_in_executor(None, ctx.run, partial_handler)
                except TypeError:
                    # 尝试 ASGI 风格
                    try:
                        partial_handler = functools.partial(endpoint, websocket.scope, websocket._receive, websocket._send)
                        await loop.run_in_executor(None, ctx.run, partial_handler)
                    except Exception:
                        await self.handle_websocket(websocket.scope, websocket._receive, websocket._send)
        else:
            # 如果没有设置 handler，使用默认的 WebSocket 处理
            await self.handle_websocket(websocket.scope, websocket._receive, websocket._send)

    async def _handle_websocket_exception(self, websocket, exc):
        """处理 WebSocket 异常"""
        from starlette.websockets import WebSocketClose

        try:
            await websocket.close(code=1011, reason=str(exc))
        except Exception:
            pass

    def _init_middlewares(self):
        """初始化中间件配置"""
        # 从设置中加载中间件配置
        middleware_configs = self.settings.get('MIDDLEWARES', {})

        # 按顺序排序中间件
        sorted_middleware_configs = self._sort_middlewares(middleware_configs.values())

        # 初始化中间件列表
        self.middlewares = []
        self.process_request_classes = []
        self.process_response_classes = []
        self.process_exception_classes = []

        # 处理每个中间件配置
        for middleware_cls in sorted_middleware_configs:
            # 添加到中间件列表
            self.middlewares.append(middleware_cls)

            # 检查中间件方法并分类
            if hasattr(middleware_cls, 'process_request'):
                self.process_request_classes.append(middleware_cls)

            # 注意：响应和异常中间件需要逆序处理
            if hasattr(middleware_cls, 'process_response'):
                self.process_response_classes.insert(0, middleware_cls)

            if hasattr(middleware_cls, 'process_exception'):
                self.process_exception_classes.insert(0, middleware_cls)

        # 处理 ASGI 中间件
        asgi_middlewares = self.settings.get('ASGI_MIDDLEWARES', {})
        for name, middleware_config in asgi_middlewares.items():
            if isinstance(middleware_config, (list, tuple)) and len(middleware_config) >= 2:
                middleware_path, options = middleware_config[:2]
                try:
                    middleware_cls = import_attr(middleware_path)
                    # 创建中间件实例
                    # ASGI 中间件通常只需要一个 app 参数，配置通过关键字参数传递
                    if isinstance(options, dict):
                        middleware_instance = middleware_cls(self, **options)
                    else:
                        middleware_instance = middleware_cls(self)
                    # 将 ASGI 中间件添加到中间件链中
                    self.middlewares.append(middleware_instance)
                except Exception as e:
                    # 如果中间件初始化失败，跳过
                    import logging
                    logging.getLogger('uliweb').warning(f"Failed to initialize ASGI middleware {name}: {e}")
                    pass
            elif isinstance(middleware_config, str):
                # 处理简单的中间件路径配置
                try:
                    middleware_cls = import_attr(middleware_config)
                    # 创建中间件实例，传递应用实例
                    middleware_instance = middleware_cls(self)
                    # 将 ASGI 中间件添加到中间件链中
                    self.middlewares.append(middleware_instance)
                except Exception as e:
                    # 如果中间件初始化失败，跳过
                    import logging
                    logging.getLogger('uliweb').warning(f"Failed to initialize ASGI middleware {name}: {e}")
                    pass
            elif isinstance(middleware_config, dict):
                # 处理字典格式的中间件配置
                try:
                    middleware_path = middleware_config.get('middleware') or middleware_config.get('class')
                    options = middleware_config.get('options', {})
                    if middleware_path:
                        middleware_cls = import_attr(middleware_path)
                        # 创建中间件实例
                        if isinstance(options, dict):
                            middleware_instance = middleware_cls(self, **options)
                        else:
                            middleware_instance = middleware_cls(self)
                        # 将 ASGI 中间件添加到中间件链中
                        self.middlewares.append(middleware_instance)
                except Exception as e:
                    # 如果中间件初始化失败，跳过
                    import logging
                    logging.getLogger('uliweb').warning(f"Failed to initialize ASGI middleware {name}: {e}")
                    pass

    def _sort_middlewares(self, middlewares):
        """对中间件进行排序"""
        m = []
        for v in middlewares:
            if not v:
                continue

            order = None
            if isinstance(v, (list, tuple)):
                if len(v) > 2:
                    # 跳过格式不正确的中间件配置
                    continue
                middleware_path = v[0]
                if len(v) == 2:
                    order = v[1]
            else:
                middleware_path = v

            try:
                cls = import_attr(middleware_path)

                if order is None:
                    order = getattr(cls, 'ORDER', 500)
                m.append((order, cls))
            except Exception:
                # 如果中间件导入失败，跳过
                continue

        # 按顺序排序
        m.sort(key=lambda x: x[0])

        return [x[1] for x in m]

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
            # 转换 Werkzeug 风格路由到 Starlette 风格，返回 (转换后的规则, 参数类型字典)
            starlette_rule, param_types = _convert_route_param(url)

            # 存储参数类型信息
            if param_types:
                self.route_param_types[starlette_rule] = param_types

            # 处理静态视图
            static = kw.pop('static', None)
            if static:
                self.static_views.append(endpoint)

            # 处理 WebSocket 路由
            websocket = kw.pop('websocket', False)
            if websocket:
                # 注册 WebSocket 路由
                self.router.add_websocket_route(starlette_rule, endpoint, **kw)
            else:
                # 注册普通 HTTP 路由
                self.router.add_route(starlette_rule, endpoint, **kw)

        # 处理每个应用的 EXPOSES 路由（来自 settings.ini 的路由定义）
        for app_name in self.apps:
            app_settings = self.settings.get(app_name.upper(), {})
            if hasattr(app_settings, 'EXPOSES') and app_settings.EXPOSES:
                for name, route_info in app_settings.EXPOSES.items():
                    if isinstance(route_info, (list, tuple)) and len(route_info) >= 2:
                        url, endpoint = route_info[:2]
                        # 转换 Werkzeug 风格路由到 Starlette 风格
                        starlette_rule, param_types = _convert_route_param(url)
                        # 存储参数类型信息
                        if param_types:
                            self.route_param_types[starlette_rule] = param_types
                        # 处理 WebSocket 路由
                        websocket = len(route_info) >= 3 and route_info[2] is True
                        if websocket:
                            self.router.add_websocket_route(starlette_rule, endpoint, name=name)
                        else:
                            self.router.add_route(starlette_rule, endpoint, name=name)
                    elif isinstance(route_info, str):
                        # 如果只有 URL，使用 name 作为 endpoint
                        url = route_info
                        starlette_rule, param_types = _convert_route_param(url)
                        # 存储参数类型信息
                        if param_types:
                            self.route_param_types[starlette_rule] = param_types
                        # 注册路由
                        self.router.add_route(starlette_rule, name, name=name)

        # 处理全局 EXPOSES 路由（来自 settings.ini 的路由定义）
        if hasattr(self.settings, 'EXPOSES') and self.settings.EXPOSES:
            for name, route_info in self.settings.EXPOSES.items():
                if isinstance(route_info, (list, tuple)) and len(route_info) >= 2:
                    url, endpoint = route_info[:2]
                    # 转换 Werkzeug 风格路由到 Starlette 风格
                    starlette_rule, param_types = _convert_route_param(url)
                    # 存储参数类型信息
                    if param_types:
                        self.route_param_types[starlette_rule] = param_types
                    # 处理 WebSocket 路由
                    websocket = len(route_info) >= 3 and route_info[2] is True
                    if websocket:
                        self.router.add_websocket_route(starlette_rule, endpoint, name=name)
                    else:
                        self.router.add_route(starlette_rule, endpoint, name=name)
                elif isinstance(route_info, str):
                    # 如果只有 URL，使用 name 作为 endpoint
                    url = route_info
                    starlette_rule, param_types = _convert_route_param(url)
                    # 存储参数类型信息
                    if param_types:
                        self.route_param_types[starlette_rule] = param_types
                    # 注册路由
                    self.router.add_route(starlette_rule, name, name=name)

    async def _import_views(self):
        """导入视图模块，触发 expose 装饰器的执行"""
        from uliweb.utils.common import myimport
        import importlib
        import sys

        # 添加项目目录到 Python 路径
        if self.project_dir and self.project_dir not in sys.path:
            sys.path.insert(0, self.project_dir)
        # 添加 apps 目录到 Python 路径
        apps_path = os.path.join(self.project_dir, 'apps') if self.project_dir else None
        if apps_path and apps_path not in sys.path:
            sys.path.insert(0, apps_path)

        # 调试输出
        logger.debug(f"sys.path = {sys.path[:5]}...")
        logger.debug(f"self.apps = {self.apps}")
        logger.debug(f"project_dir = {self.project_dir}")
        logger.debug(f"apps_path = {apps_path}")

        # 收集所有应用的视图模块
        views_modules = []
        for app in self.apps:
            # 检查是否有 apps 目录
            has_apps_dir = self.project_dir and os.path.exists(os.path.join(self.project_dir, 'apps'))
            logger.debug(f"Processing app: {app}, has_apps_dir: {has_apps_dir}")

            # 尝试导入 views.py
            try:
                # 根据是否有 apps 目录来确定模块路径
                if has_apps_dir and not app.startswith('uliweb.contrib.'):
                    views_module = f"apps.{app}.views"
                else:
                    views_module = f"{app}.views"

                logger.debug(f"Trying to import: {views_module}")

                # 尝试直接导入模块
                try:
                    myimport(views_module)
                    views_modules.append(views_module)
                    logger.debug(f"Successfully imported: {views_module}")
                except ImportError as e1:
                    logger.debug(f"Failed to import {views_module}: {e1}")
                    # 如果失败，尝试直接导入应用模块
                    try:
                        myimport(app)
                        views_modules.append(app)
                        logger.debug(f"Successfully imported app: {app}")
                    except ImportError as e2:
                        logger.debug(f"Failed to import app {app}: {e2}")
                        # 再次尝试 views 模块
                        pass
            except ImportError as e:
                logger.debug(f"Error importing views for {app}: {e}")
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
                                # 根据是否有 apps 目录来确定模块路径
                                if has_apps_dir and not app.startswith('uliweb.contrib.'):
                                    full_module = f"apps.{app}.views.{module_name}"
                                else:
                                    full_module = f"{app}.views.{module_name}"
                                try:
                                    myimport(full_module)
                                    views_modules.append(full_module)
                                except ImportError:
                                    pass
                except Exception as e:
                    pass
            except Exception as e:
                pass

        # 导入 contrib 应用的模块
        for app in self.apps:
            if app.startswith('uliweb.contrib.'):
                try:
                    # 导入 contrib 应用的 __init__.py 文件，这会触发路由注册
                    myimport(app)
                    # 触发 BINDS 机制
                    await self._trigger_binds(app)
                except ImportError as e:
                    pass

    async def _trigger_binds(self, app_name):
        """触发 BINDS 机制"""
        # 获取应用设置
        app_settings = self.settings.get(app_name.upper(), {})
        binds = app_settings.get('BINDS', {})

        # 触发 startup_installed 和 prepare_default_env 等绑定函数
        for bind_name, bind_info in binds.items():
            if isinstance(bind_info, (list, tuple)) and len(bind_info) >= 2:
                func_name, module_path = bind_info[:2]
                try:
                    # 导入并调用绑定函数
                    func = import_attr(module_path)
                    if func:
                        # 创建一个模拟的 sender 对象
                        class MockSender:
                            def __init__(self, settings):
                                self.settings = settings

                        sender = MockSender(self.settings)

                        # 调用函数
                        if asyncio.iscoroutinefunction(func):
                            await func(sender)
                        else:
                            func(sender)
                except Exception as e:
                    # 忽略绑定函数执行中的错误
                    pass

        # 特殊处理静态文件和上传模块的路由注册
        if app_name == 'uliweb.contrib.staticfiles':
            # 注册静态文件路由
            from uliweb.core.SimpleFrame import expose
            static_url = self.settings.GLOBAL.get('STATIC_URL', '/static')
            if static_url:
                url = static_url.rstrip('/')
                # 直接注册静态文件路由
                def static_handler(filename):
                    pass
                expose('%s/<path:filename>' % url, static=True)(static_handler)

        elif app_name == 'uliweb.contrib.upload':
            # 注册上传文件路由
            from uliweb.core.SimpleFrame import expose
            # 直接注册上传文件路由
            def file_serving(filename):
                from uliweb.contrib.upload import file_serving as upload_file_serving
                return upload_file_serving(filename)
            expose('/uploads/<path:filename>', name='uliweb.contrib.upload.file_serving')(file_serving)

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

        # 使用协程池执行同步的 settings 加载
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

        # 使用协程池执行同步的应用获取
        # 注意：需要传递完整的 apps 目录路径
        loop = asyncio.get_event_loop()

        # 构建完整的 apps 目录路径
        if self.project_dir:
            apps_dir_full = os.path.join(self.project_dir, self.apps_dir)
        else:
            apps_dir_full = self.apps_dir

        apps = await loop.run_in_executor(
            None,
            get_sync_apps,
            apps_dir_full,
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
        # 确保应用已初始化
        if not self._initialized:
            await self._async_init()

        # 构建中间件调用链
        app = await self._build_middleware_stack()

        # 处理请求
        await app(scope, receive, send)

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
            # 只处理 Route 对象，跳过 Mount 对象
            # Route 有 'methods' 属性，Mount 没有
            if not isinstance(route, Route):
                continue
            try:
                route_path = route.path

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

        # 提取路径参数 - 支持 Starlette 的两种格式：
        # {param} - 普通路径参数
        # {path:filename} - 捕获剩余路径部分
        # 也支持 Uliweb 风格: {int:user_id}, {str:name}
        import re
        # 获取参数名和类型 - 包括 {param} 和 {type:param} 格式
        param_patterns = re.findall(r'\{(?:([^:}]+):)?([^}]+)\}', route_path)

        # 构建匹配模式（去掉类型信息）
        pattern = re.sub(r'\{(?:[^:}]+:)?([^}]+)\}', r'([^/]+)', route_path)
        pattern = '^' + pattern + '$'

        match = re.match(pattern, request_path)
        if match:
            params = {}
            # 优先使用 route_param_types 中存储的类型信息
            param_types = self.route_param_types.get(route_path, {})

            for i, (param_type, name) in enumerate(param_patterns):
                value = match.group(i + 1)

                # 优先从 route_param_types 获取类型信息
                if name in param_types:
                    param_type = param_types[name]

                # 根据类型进行转换
                if param_type == 'int':
                    params[name] = int(value)
                elif param_type == 'float':
                    params[name] = float(value)
                elif param_type == 'str' or param_type is None:
                    params[name] = value
                else:
                    # 对于其他类型，保留字符串
                    params[name] = value
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
            # 同步函数需要在协程池中执行
            # run_in_executor 只接受位置参数，使用 functools.partial 绑定参数
            import functools
            from contextvars import copy_context
            loop = asyncio.get_event_loop()

            # 获取当前 contextvars 上下文
            ctx = copy_context()

            if call_kwargs:
                # 使用 partial 绑定关键字参数，不再额外传递位置参数
                partial_handler = functools.partial(handler, **call_kwargs)
                # 使用 copy_context 确保 contextvars 在线程中正确传播
                result = await loop.run_in_executor(None, ctx.run, partial_handler)
            else:
                # 使用 copy_context 确保 contextvars 在线程中正确传播
                result = await loop.run_in_executor(None, ctx.run, handler, *call_args)

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
        # 使用协程池执行同步的模板渲染
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            self._sync_render_template,
            template_file, vars, env
        )

        return content

    def _sync_render_template(self, template_file, vars, env):
        """同步渲染模板（在协程池中执行）"""
        # 获取模板目录
        template_dirs = []

        # 首先尝试直接查找模板文件
        # 检查应用级模板目录
        apps_template_dir = os.path.join(self.project_dir, 'apps', 'templates')
        if os.path.exists(apps_template_dir):
            template_dirs.append(apps_template_dir)

        # 检查项目级模板目录
        project_template_dir = os.path.join(self.project_dir, 'templates')
        if os.path.exists(project_template_dir):
            template_dirs.append(project_template_dir)

        # 添加应用级模板目录（相对于项目目录）
        for app in self.apps:
            # 应用级模板目录
            app_template_dir = os.path.join(self.project_dir, 'apps', app, 'templates')
            if os.path.exists(app_template_dir):
                template_dirs.append(app_template_dir)

            # 应用视图级模板目录
            app_views_template_dir = os.path.join(self.project_dir, 'apps', app, 'views', 'templates')
            if os.path.exists(app_views_template_dir):
                template_dirs.append(app_views_template_dir)

        # 如果模板目录为空，尝试使用 SimpleFrame 的方式获取模板目录
        if not template_dirs:
            from uliweb.core.SimpleFrame import Dispatcher
            try:
                # 创建一个临时的 Dispatcher 来获取模板目录
                temp_dispatcher = Dispatcher(
                    apps_dir=self.apps_dir,
                    project_dir=self.project_dir,
                    start=False
                )
                template_dirs = temp_dispatcher.template_dirs
            except Exception:
                pass

        # 如果仍然为空，尝试直接搜索项目目录下的模板
        if not template_dirs:
            # 直接搜索项目目录下的所有 templates 目录
            for root, dirs, files in os.walk(self.project_dir):
                if 'templates' in dirs:
                    template_dir = os.path.join(root, 'templates')
                    if os.path.exists(template_dir):
                        template_dirs.append(template_dir)

        # 尝试从各个模板目录中查找模板文件
        for template_dir in template_dirs:
            template_path = os.path.join(template_dir, template_file)
            if os.path.exists(template_path):
                # 找到模板文件，使用 uliweb 的模板系统进行渲染
                try:
                    # 创建模板加载器
                    from uliweb.core.template import Loader
                    loader = Loader(template_dirs)

                    # 加载并渲染模板
                    template_obj = loader.load(template_file)

                    # 确保 vars 是字典格式
                    if isinstance(vars, dict):
                        template_vars = vars
                    else:
                        template_vars = dict(vars) if hasattr(vars, '__iter__') else {}

                    # 确保 env 是字典格式
                    if isinstance(env, dict):
                        template_env = env
                    else:
                        template_env = dict(env) if hasattr(env, '__iter__') else {}

                    content = template_obj.generate(template_vars, template_env)
                    return content
                except Exception as e:
                    # 如果模板渲染失败，返回错误信息
                    import traceback
                    error_msg = f"Template rendering error: {str(e)}\n{traceback.format_exc()}"
                    return error_msg

        # 如果找不到模板文件，返回错误信息
        error_msg = f"Template not found: {template_file}. Searched in: {template_dirs}"
        return error_msg

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

    async def _build_middleware_stack(self):
        """构建中间件调用链"""
        # 如果已经构建过中间件栈，直接返回缓存的版本
        if self._middleware_stack is not None:
            return self._middleware_stack

        # 从内到外包装应用，形成中间件链
        # 确保 _handle_request 是 async function
        if asyncio.iscoroutinefunction(self._handle_request):
            app = self._handle_request
        else:
            # 如果 _handle_request 是 bound method，转换为 async function
            async def async_handle_request(scope, receive, send):
                return await self._handle_request(scope, receive, send)
            app = async_handle_request

        # 按逆序添加中间件（确保按配置顺序执行）
        for middleware in reversed(self.middlewares):
            try:
                # 检查中间件类型并分别处理
                # middleware 可能是类（未实例化）或实例

                # 获取中间件类
                if isinstance(middleware, type):
                    middleware_cls = middleware
                else:
                    middleware_cls = type(middleware)

                # 1. ASGI 中间件（有自定义的 __call__ 方法）
                # ASGI 中间件应该有 async def __call__(self, scope, receive, send)
                # 检查实例的 __call__ 方法是否为协程函数
                if not isinstance(middleware, type):
                    has_asgi_call = (
                        hasattr(middleware, '__call__') and
                        iscoroutinefunction(middleware.__call__)
                    )
                else:
                    # 对于类，检查类的 __call__ 是否为协程函数
                    has_asgi_call = (
                        hasattr(middleware_cls, '__call__') and
                        iscoroutinefunction(middleware_cls.__call__)
                    )

                # 2. 高级中间件（有 dispatch 方法）
                has_dispatch = (
                    hasattr(middleware_cls, 'dispatch') and
                    callable(getattr(middleware_cls, 'dispatch', None))
                )

                # 3. 传统中间件（有 process_* 方法）
                has_traditional = (
                    hasattr(middleware_cls, 'process_request') or
                    hasattr(middleware_cls, 'process_response') or
                    hasattr(middleware_cls, 'process_exception')
                )

                if has_asgi_call:
                    # ASGI 中间件：直接包装
                    # 需要传递 self 作为 app 参数，因为 ASGI 中间件通常只需要一个 app 参数
                    if isinstance(middleware, type):
                        middleware_instance = middleware(self)
                    else:
                        middleware_instance = middleware
                    app = self._wrap_asgi_middleware(middleware_instance, app)
                elif has_dispatch:
                    # 高级中间件
                    if isinstance(middleware, type):
                        middleware_instance = middleware(self, self.settings)
                    else:
                        middleware_instance = middleware
                    app = self._wrap_advanced_middleware(middleware_instance, app)
                elif has_traditional:
                    # 传统中间件，在 _process_middleware 中处理
                    continue
                else:
                    # 不是有效的中间件，尝试创建实例
                    try:
                        if isinstance(middleware, type):
                            middleware_instance = middleware(self, self.settings)
                        else:
                            middleware_instance = middleware
                        app = self._wrap_asgi_middleware(middleware_instance, app)
                    except Exception:
                        continue
            except Exception as e:
                # 如果中间件初始化失败，跳过
                import logging
                logging.getLogger('uliweb').warning(f"Failed to process middleware {middleware}: {e}")
                continue

        # 缓存构建好的中间件栈
        self._middleware_stack = app
        return app

    def _wrap_advanced_middleware(self, middleware, next_app):
        """包装高级中间件"""
        async def app(scope, receive, send):
            # 只处理 HTTP 请求
            if scope["type"] != "http":
                await next_app(scope, receive, send)
                return

            # 创建请求对象
            request = Request(scope, receive, send)

            # 创建 call_next 函数
            async def call_next(request):
                # 创建一个缓冲区来捕获响应
                response_body = b""
                response_status = None
                response_headers = []

                # 创建自定义的 send 函数来捕获响应
                async def capture_send(message):
                    nonlocal response_body, response_status, response_headers
                    if message["type"] == "http.response.start":
                        response_status = message["status"]
                        response_headers = list(message.get("headers", []))  # 确保是可变的列表
                    elif message["type"] == "http.response.body":
                        body_chunk = message.get("body", b"")
                        response_body += body_chunk
                        # 如果是最后一个 chunk，创建响应对象
                        if not message.get("more_body", False):
                            pass

                # 创建新的 scope，可能需要修改
                new_scope = scope.copy()
                # 调用下一个应用
                try:
                    await next_app(new_scope, receive, capture_send)

                    # 创建响应对象
                    from starlette.responses import Response as StarletteResponse

                    # 转换响应头，将字节类型转换为字符串类型
                    converted_headers = {}
                    if response_headers:
                        for header in response_headers:
                            if len(header) == 2:
                                key, value = header
                                # 将字节类型转换为字符串
                                if isinstance(key, bytes):
                                    key = key.decode('latin-1')
                                if isinstance(value, bytes):
                                    value = value.decode('latin-1')
                                converted_headers[key] = value

                    response = StarletteResponse(
                        content=response_body,
                        status_code=response_status or 200,
                        headers=converted_headers if converted_headers else None
                    )
                    return response
                except Exception as e:
                    # 如果下一个应用抛出异常，重新抛出
                    raise e

            # 调用中间件
            try:
                response = await middleware.dispatch(request, call_next)
                # 发送响应
                if response is not None:
                    await response(scope, receive, send)
                    return response
                else:
                    # 如果中间件返回 None，调用下一个应用
                    response = await next_app(scope, receive, send)
                    return response
            except Exception as e:
                # 如果中间件抛出异常，重新抛出
                raise e

        return app

    def _wrap_asgi_middleware(self, middleware, next_app):
        """包装底层 ASGI 中间件"""
        # 设置中间件的 app 属性指向下一个应用
        middleware.app = next_app

        async def app(scope, receive, send):
            # 调用中间件
            try:
                await middleware(scope, receive, send)
            except Exception as e:
                raise

        return app

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
        # 处理文件不存在等 RuntimeError
        elif isinstance(exception, RuntimeError) and "File at path" in str(exception):
            return JSONResponse({"error": str(exception)}, status_code=404)
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
        return JSONResponse(
            {'error': 'Internal Server Error'},
            status_code=500
        )



class ASGIApplication:
    """纯 ASGI 应用处理器（单例模式）"""

    # 类级别变量用于存储单例实例
    _instance = None
    _instance_project_dir = None
    _instance_asgi_app = None

    def __new__(cls, project_dir=None):
        # 单例模式：只创建一次实例
        if cls._instance is None or cls._instance_project_dir != project_dir:
            cls._instance = super(ASGIApplication, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance_project_dir = project_dir
        return cls._instance

    def __init__(self, project_dir=None):
        self.project_dir = project_dir
        # 不在这里初始化，延迟到 __call__ 时初始化

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            # 处理 project_dir 为 None 的情况
            if self.project_dir is None:
                # 尝试获取当前工作目录作为默认项目目录
                self.project_dir = os.getcwd()

            # 创建 ASGI Dispatcher
            # 注意：apps_dir 只需要传递 'apps'，而不是完整路径
            # 因为 AsyncDispatcher 会将 project_dir 和 apps_dir 拼接
            ASGIApplication._instance_asgi_app = AsyncDispatcher(
                apps_dir='apps',
                project_dir=self.project_dir
            )
            self._initialized = True

    async def __call__(self, scope, receive, send):
        """ASGI 接口"""
        self._initialize()
        await ASGIApplication._instance_asgi_app(scope, receive, send)

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
# 直接使用 context.py 中的代理，避免额外的 LocalProxy 层
from .context import settings_proxy, request_proxy, response_proxy, application_proxy

request = request_proxy
response = response_proxy
settings = settings_proxy
application = application_proxy

# 为了兼容性，保留 get_request 等函数（可选）
_get_request = get_request
_get_response = get_response
_get_settings = get_settings
_get_application = get_application


# 兼容性函数
def redirect(location, code=302):
    """重定向函数"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=location, status_code=code)


def json(data, **kwargs):
    """JSON 响应函数

    支持的 kwargs 参数:
        - status: HTTP 状态码 (别名 for status_code)
        - status_code: HTTP 状态码
        - 其他参数传递给 JSONResponse
    """
    from starlette.responses import JSONResponse

    # 处理 status 参数，转换为 status_code
    if 'status' in kwargs:
        kwargs['status_code'] = kwargs.pop('status')

    return JSONResponse(data, **kwargs)


def url_for(endpoint, **values):
    """URL 生成函数"""
    from uliweb import application
    if hasattr(application, '_url_for'):
        return application._url_for(endpoint, **values)
    else:
        # 简单实现
        return f"/{endpoint}"


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
    'json',
    'url_for'
]
