####################################################################
# Author: Limodou@gmail.com
# License: BSD
####################################################################
from __future__ import print_function, absolute_import

import os, sys
import re
import types
import typing as t
import threading
import asyncio
import contextvars
from inspect import iscoroutinefunction

# 使用 Starlette 替代 Werkzeug
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse, JSONResponse
from starlette.datastructures import UploadFile
from starlette.routing import Route, Router, Mount
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.exceptions import HTTPException as BadRequest
from starlette.exceptions import HTTPException as InternalServerError
from starlette.exceptions import HTTPException as NotFound
from starlette.websockets import WebSocket as StarletteWebSocket

# 为了兼容性，创建别名
OriginalResponse = StarletteResponse

import logging
import sys

# 创建日志记录器
logger = logging.getLogger('uliweb')

from uliweb.orm import CommitAll, RollbackAll


# ==================== Request 类 ====================
# 基于 Starlette 的异步 Request
class Request(StarletteRequest):
    """基于 Starlette 的 Request 类，保持与现有 Uliweb 的兼容性"""

    @property
    def GET(self):
        """兼容 GET 参数访问"""
        return self.query_params

    @property
    def state(self):
        """获取请求状态容器"""
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
        import json as jsn
        body = await self.get_data()
        return jsn.loads(body)

    async def get_data(self):
        """异步获取原始请求体数据（bytes）

        与 WSGI 版本的 request.data 行为一致：
        - 返回原始请求体的字节数据
        - 如果请求是表单数据，读取后 body 可能为空（因为表单解析器会消费流）
        """
        return await self.body()

    async def get_params(self):
        """异步获取合并参数"""
        get_params = self.query_params
        post_params = await self.get_POST()
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

    @property
    def POST(self):
        """已弃用：同步访问 POST 数据会抛出异常"""
        raise RuntimeError(
            "POST 属性已弃用，请使用 await request.get_POST() 方法。"
        )

    @property
    def FILES(self):
        """已弃用：同步访问 FILES 数据会抛出异常"""
        raise RuntimeError(
            "FILES 属性已弃用，请使用 await request.get_FILES() 方法。"
        )

    @property
    def json(self):
        """已弃用：同步访问 JSON 数据会抛出异常"""
        raise RuntimeError(
            "json 属性已弃用，请使用 await request.get_json() 方法。"
        )

    @property
    def data(self):
        """已弃用：同步访问原始请求体数据会抛出异常

        request.data 在 WSGI 版本中返回原始请求体字节。
        在 ASGI 版本中，请使用 await request.get_data() 方法。
        """
        raise RuntimeError(
            "data 属性已弃用，请使用 await request.get_data() 方法获取原始请求体字节。"
        )

    @property
    def params(self):
        """兼容 params 属性，返回 GET 参数"""
        return self.query_params

    @property
    def values(self):
        """兼容 WSGI 模式的 values 属性，返回 GET 参数"""
        return self.query_params

    @property
    def remote_addr(self):
        """兼容 WSGI 模式的 remote_addr 属性"""
        if self.client:
            return self.client.host
        x_forwarded_for = self.headers.get("x-forwarded-for")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return self.headers.get("x-real-ip", "")

    @property
    def environ(self):
        """兼容 WSGI 模式的 environ 属性，返回 scope"""
        return self.scope


    @property
    def user(self):
        """获取当前用户

        优先从 scope['auth'] 获取用户信息（由 AuthMiddle 设置）
        如果没有，则返回 None（与 Starlette 的 AuthenticationMiddleware 兼容）
        """
        # 首先检查 scope 中是否有 auth（由 AuthMiddle 设置）
        if 'auth' in self.scope:
            return self.scope['auth']

        # 如果没有 auth，返回 None
        # 注意：Starlette 的 AuthenticationMiddleware 会检查 'user' 在 scope 中
        # 如果不存在会抛出 AssertionError
        return None

    @user.setter
    def user(self, value):
        """设置当前用户"""
        self.scope['auth'] = value

    @property
    def query_string(self):
        """获取查询字符串（兼容旧版）"""
        return self.scope.get('query_string', b'')

    @property
    def session(self):
        """获取 session 对象

        优先从 scope['session'] 获取（Starlette 兼容）
        如果没有，则返回 None
        """
        if 'session' in self.scope:
            return self.scope['session']
        return None

    @session.setter
    def session(self, value):
        """设置 session 对象"""
        self.scope['session'] = value


# ==================== Response 类 ====================
# 基于 Starlette 的 Response
class Response(StarletteResponse):
    """基于 Starlette 的 Response 类，保持与现有 Uliweb 的兼容性"""

    def write(self, value):
        """兼容 write 方法"""
        pass

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
from uliweb.utils._compat import html_escape, isresponse

# 定义错误类以避免循环导入
class UliwebError(Exception):
    """Uliweb 基础错误类"""
    pass

# from rules import Mapping, add_rule
from . import rules

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


CONTENT_TYPE_JSON = 'application/json; charset=utf-8'
CONTENT_TYPE_TEXT = 'text/plain; charset=utf-8'
from ..utils._compat import escape, string_types, callable, import_, get_class, ismethod, import_

try:
    set
except:
    from sets import Set as set

__global__ = Global()

# 使用 LocalProxy 替代 contextvars
# request 和 response 使用 LocalProxy + use_contextvars=True（每个协程独立）
# settings 和 application 使用 LocalProxy + use_contextvars=False（全局一致）
# 重要：必须使用 __global__ 作为 env，确保与 get_application() 返回的对象一致
request = LocalProxy('request', use_contextvars=True)
response = LocalProxy('response', use_contextvars=True)
settings = LocalProxy('settings', use_contextvars=False, env=__global__)
application = LocalProxy('application', use_contextvars=False, env=__global__)

# 使用 Starlette 路由替代 werkzeug.routing.Map
# 创建 UliwebRouter 实例
class UliwebRouter:
    """Uliweb 路由适配器，将 Werkzeug 风格路由转换为 Starlette 风格"""

    def __init__(self):
        self.routes = []
        self.url_map = {}
        self.router = Router()

    def add_route(self, rule, endpoint, **kwargs):
        """转换 Werkzeug 风格路由到 Starlette 风格"""
        # 使用 _convert_route_param 正确转换参数格式
        # 例如: '/static/<path:filename>' -> ('/static/{filename}', {'filename': 'path'})
        starlette_rule, param_types = _convert_route_param(rule)

        # 如果没有指定 methods，默认支持主要 HTTP 方法（与 Expose 类的默认值一致）
        methods = kwargs.get('methods', ['GET', 'POST', 'PUT'])
        name = kwargs.get('name')
        if name is None and isinstance(endpoint, str):
            name = endpoint

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
        if name is None and isinstance(endpoint, str):
            name = endpoint

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

    def bind(self, server_name=None, **kwargs):
        """返回路由绑定对象（兼容 werkzeug）"""
        return self.router

    def iter_rules(self):
        """迭代所有路由规则"""
        return iter(self.routes)

    def build(self, endpoint, values, force_external=False):
        """
        根据 endpoint 名称和参数构建 URL
        兼容 werkzeug 的 build 方法

        路径中的参数会替换到 URL 中，额外的参数会作为 query string 追加，
        例如 url_for('app.views.index', next='/login') -> '/index?next=/login'
        """
        # 首先尝试通过 endpoint 名称直接查找（字符串 endpoint）
        route = self.url_map.get(endpoint)

        if route:
            return self._build_route(route, values)

        # 如果找不到，尝试通过 route.name 查找
        for key, route in self.url_map.items():
            route_name = getattr(route, 'name', None)
            if route_name and route_name == endpoint:
                return self._build_route(route, values)

        # 如果找不到，抛出异常
        raise ValueError(f"Could not build URL for endpoint '{endpoint}'. Endpoint not found in url_map.")

    def _build_route(self, route, values):
        """构建单个路由的 URL，路径参数替换到路径中，其余参数作为 query string"""
        import re
        from urllib.parse import urlencode

        # 提取路径参数名
        path_names = set(re.findall(r'\{([^}]+)\}', route.path))

        path_params = {}
        query_params = {}
        for k, v in values.items():
            if k in path_names:
                path_params[k] = v
            else:
                query_params[k] = v

        url = None
        try:
            # 使用 Starlette 的 url_path_for 方法
            if route.name:
                url = self.router.url_path_for(route.name, **path_params).path
        except Exception:
            url = None

        # 如果上面的方法失败，直接使用路径替换参数
        if url is None:
            path = route.path
            for k, v in path_params.items():
                path = path.replace('{' + k + '}', str(v))
            url = path

        # 追加额外的参数作为 query string
        if query_params:
            url = url + '?' + urlencode(query_params)

        return url


url_map = UliwebRouter()
static_views = []
use_urls = False
url_adapters = {}
__app_dirs__ = {}
__app_alias__ = {}
_xhr_redirect_json = True

r_callback = re.compile(r'^[\w_]+$')
# Initialize pyini env
pyini.set_env({
    'env':{'_':gettext_lazy, 'gettext_lazy':gettext_lazy},
    'convertors':i18n_ini_convertor,
})
__global__.settings = pyini.Ini(lazy=True)
# 同步设置到 LocalProxy
settings.set(__global__.settings)

#User can defined decorator functions in settings DECORATORS
#and user can user @decorators.function_name in views
#and this usage need settings be initialized before decorator invoking

class Finder(object):
    def __init__(self, section):
        self.__objects = {}
        self.__section = section

    def __contains__(self, name):
        if name in self.__objects:
            return True
        try:
            if name not in settings[self.__section]:
                return False
        except (RuntimeError, KeyError):
            return False
        return True

    def __getattr__(self, name):
        if name in self.__objects:
            return self.__objects[name]
        try:
            section = settings[self.__section]
        except (RuntimeError, KeyError):
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__.__name__, name))
        if name not in section:
            raise AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__.__name__, name))
        obj = import_attr(section.get(name))
        self.__objects[name] = obj
        return obj

    def __setitem__(self, name, value):
        if isinstance(value, string_types):
            value = import_attr(value)
        self.__objects[name] = value

decorators = Finder('DECORATORS')
functions = Finder('FUNCTIONS')

# Request 和 Response 类已移至 starlette.py，避免代码重复
# 从 .starlette 导入的 Request 和 Response 类已包含所有必要的兼容方法

class HTTPError(Exception):
    def __init__(self, errorpage=None, **kwargs):
        self.errorpage = errorpage or settings.GLOBAL.ERROR_PAGE
        self.errors = kwargs

    def __str__(self):
        return repr(self.errors)

def redirect(location, code=302):
    global _xhr_redirect_json, request

    if _xhr_redirect_json and getattr(request, 'is_json', None):
        response = json({'success':False, 'redirect':location}, status=500)
    else:
        response = Response(
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
            '<title>Redirecting...</title>\n'
            '<h1>Redirecting...</h1>\n'
            '<p>You should be redirected automatically to target URL: '
            '<a href="%s">%s</a>.  If not click the link.' %
            (html_escape(location), html_escape(location)), status=code, content_type='text/html')
        response.headers['Location'] = location
    return response

class RedirectException(Exception):
    """
    This is an exception, which can be raised in view function
    """
    def __init__(self, location, code=302):
        self.response = redirect(location, code)

    def get_response(self):
        return self.response

def Redirect(url):
    raise RedirectException(url)

def error(message='', errorpage=None, request=None, appname=None, **kwargs):
    kwargs.setdefault('message', message)
    if request:
        kwargs.setdefault('link', functions.request_url())
    raise HTTPError(errorpage, **kwargs)

def function(fname, *args, **kwargs):
    func = settings.get_var('FUNCTIONS/'+fname)
    if func:
        if args or kwargs:
            return import_attr(func)(*args, **kwargs)
        else:
            return import_attr(func)
    else:
        raise UliwebError("Can't find the function [%s] in settings" % fname)

def json(data, **json_kwargs):
    def set_content_type():
        from uliweb import request

    if 'content_type' not in json_kwargs:
            if request and 'Accept' in request.headers:
                Accept = request.headers['Accept']
                if Accept == '*/*':
                    json_kwargs['content_type'] = CONTENT_TYPE_JSON
                else:
                    if 'application/json' in [x.strip() for x in request.headers['Accept'].split(',')]:
                        json_kwargs['content_type'] = CONTENT_TYPE_JSON
                    else:
                        json_kwargs['content_type'] = CONTENT_TYPE_TEXT
            else:
                json_kwargs['content_type'] = CONTENT_TYPE_TEXT

    if callable(data):
        @wraps(data)
        def f(*arg, **kwargs):
            set_content_type()
            ret = data(*arg, **kwargs)
            return Response(json_dumps(ret), **json_kwargs)
        return f
    else:
        set_content_type()
        return Response(json_dumps(data), **json_kwargs)

def jsonp(data, **json_kwargs):
    """
    jsonp is callback key name
    """
    from uliweb import request

    if 'jsonp' in json_kwargs:
        cb = json_kwargs.pop('jsonp')
    else:
        cb = 'callback'

    begin = str(request.GET.get(cb))
    if not begin:
        raise BadRequest("Can't found %s parameter in request's query_string" % cb)
    if not r_callback.match(begin):
        raise BadRequest("The callback name is not right, it can be alphabetic, number and underscore only")

    if callable(data):
        @wraps(data)
        def f(*arg, **kwargs):
            ret = data(*arg, **kwargs)
            return Response(begin + '(' + json_dumps(ret) + ');', **json_kwargs)
        return f
    else:
        return Response(begin + '(' + json_dumps(data) + ');', **json_kwargs)


def CORS(func=None, res=None):
    """
    CORS support
    """

    def w(r=None):
        from uliweb import request, response

        if request.method == 'OPTIONS':
            response = Response(status=204)
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range')

            response.headers['Access-Control-Max-Age'] = 24*3600
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Length'] = 0
            return response
        elif request.method in ('GET', 'POST'):
            if isinstance(r, Response) or isinstance(r, OriginalResponse):
                response = r
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            if 'Origin' in request.headers:
                response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range')
            if response.headers.get('Access-Control-Expose-Headers'):
                h = set(response.headers['Access-Control-Expose-Headers'].split(',') + ['Content-Length', 'Content-Range'])
                response.headers['Access-Control-Expose-Headers'] = ','.join(h)
            return response

    if callable(func):
        @wraps(func)
        def f(*arg, **kwargs):
            if request.method == 'OPTIONS':
                return w()
            ret = func(*arg, **kwargs)
            w(ret)
            return ret

        return f
    else:
        return w(res)

def expose(rule=None, **kwargs):
    e = rules.Expose(rule, **kwargs)
    if e.parse_level == 1:
        return rule
    else:
        return e

def POST(rule, **kw):
    kw['methods'] = ['POST']
    return expose(rule, **kw)

def GET(rule, **kw):
    kw['methods'] = ['GET']
    return expose(rule, **kw)

def get_url_adapter(_domain_name):
    """
    Fetch a domain url_adapter object, and bind it to according domain
    使用 Starlette 路由替代 werkzeug，不需要 wsgi_decoding_dance
    """
    # 使用 get_application() 来获取 application，如果为 None 则使用 __global__.application
    from .context import get_application
    _app = get_application()

    # 如果 application 中的 application 为 None，尝试使用 __global__.application
    if _app is None:
        # 尝试从 __global__ 获取
        _app = getattr(__global__, 'application', None)

    # 如果有 AsyncDispatcher 实例，使用它的 router
    if _app and hasattr(_app, 'router'):
        # 返回 AsyncDispatcher 的 router，它有 build 方法
        return _app.router

    # 否则使用全局的 url_map（WSGI 模式）
    domain = _app.domains.get(_domain_name, {}) if _app else {}
    server_name = None

    if domain.get('domain', ''):
        server_name = domain['domain']

    # 使用 Starlette 路由的简单 bind 方法
    # 不再依赖 werkzeug 的 bind_to_environ
    try:
        # 尝试从 request 获取 scope 信息 (ASGI 环境)
        if hasattr(request, 'scope') and request.scope:
            scope = request.scope
            env = {
                'url_scheme': scope.get('scheme', 'http'),
                'default_method': scope.get('method', 'GET'),
                'script_name': scope.get('root_path', ''),
                'path_info': scope.get('path', '/'),
                'query_args': scope.get('query_string', b'').decode('utf-8'),
            }
            adapter = url_map.bind(server_name, **env) if server_name else url_map
        else:
            adapter = url_map.bind(server_name) if server_name else url_map
    except:
        # 如果获取失败，使用默认的 adapter
        adapter = url_map.bind(server_name) if server_name else url_map

    return adapter

def get_rule(url):
    """
    获取 URL 的路由规则信息。
    使用 bind 替代 bind_to_environ，避免依赖 werkzeug.test.EnvironBuilder。
    NotFound 异常已在本文件顶部从 werkzeug.exceptions 导入。
    """
    # 使用 bind 替代 bind_to_environ
    url_adapter = url_map.bind('localhost')
    result = {}
    try:
        rule, values = url_adapter.match(url, return_rule=True)
        result['rule'] = rule.rule
        result['endpoint'] = rule.endpoint
        result['doc'] = ''
        mod, handler_cls, func = application.get_handler(rule.endpoint)
        if func.__doc__:
            result['doc'] = func.__doc__.strip()
    except NotFound:
        pass
    return result

def url_for(endpoint, **values):
    """URL 生成函数 - 统一实现

    在 ASGI 模式下调用 application._url_for 方法
    """
    from uliweb import application

    if hasattr(application, '_url_for'):
        return application._url_for(endpoint, **values)
    else:
        raise ValueError("url_for requires application to be initialized")

def get_app_dir(app):
    """
    Get an app's directory
    """
    path = __app_dirs__.get(app)
    if path is not None:
        return path
    else:
        p = app.split('.')
        try:
            path = pkg.resource_filename(p[0], '')
        except ImportError as e:
            log.error("Can't import app %s" % app)
            log.exception(e)
            path = ''
        if len(p) > 1:
            path = os.path.join(path, *p[1:])

        __app_dirs__[app] = path
        return path

def get_app_depends(app, existed_apps=None, installed_apps=None):
    installed_apps = installed_apps or []
    if existed_apps is None:
        s = set()
    else:
        s = existed_apps

    if app in s:
        return

    if isinstance(app, (tuple, list)):
        app, name = app
        __app_alias__[name+'.'] = app + '.'

    configfile = os.path.join(get_app_dir(app), 'config.ini')
    if os.path.exists(configfile):
        x = pyini.Ini(configfile)
        apps = x.get_var('DEPENDS/REQUIRED_APPS', [])
        for i in apps:
            if i not in s and i not in installed_apps:
                for j in get_app_depends(i, s, installed_apps):
                    yield j
    s.add(app)
    yield app

def set_var(key, value):
    """
    Default set_var function
    """
    from uliweb import settings

    settings.set_var(key, value)

def get_var(key, default=None):
    """
    Default get_var function
    """
    from uliweb import settings

    return settings.get_var(key, default)

def get_local_cache(key, creator=None):
    # 使用 request.scope['state'] 来存储本地缓存
    req = request.get_value()
    if req and hasattr(req, 'scope'):
        if 'local_cache' not in req.scope:
            req.scope['local_cache'] = {}
        cache = req.scope['local_cache']
    else:
        # 如果没有请求对象，使用全局字典
        if not hasattr(get_local_cache, '_cache'):
            get_local_cache._cache = {}
        cache = get_local_cache._cache

    value = cache.get(key)
    if value:
        return value
    if callable(creator):
        value = creator()
    else:
        value = creator
    if value:
        cache[key] = value
    return value

def get_apps(apps_dir, include_apps=None, settings_file='settings.ini', local_settings_file='local_settings.ini'):
    include_apps = include_apps or []
    inifile = norm_path(os.path.join(apps_dir, settings_file))
    apps = []
    visited = set()
    installed_apps = []
    if not os.path.exists(apps_dir):
        return apps
    if os.path.exists(inifile):
        x = pyini.Ini(inifile, basepath=apps_dir)
        if x:
            installed_apps.extend(x.GLOBAL.get('INSTALLED_APPS', []))

    local_inifile = norm_path(os.path.join(apps_dir, local_settings_file))
    if os.path.exists(local_inifile):
        x = pyini.Ini(local_inifile, basepath=apps_dir)
        if x and x.get('GLOBAL'):
            installed_apps.extend(x.GLOBAL.get('INSTALLED_APPS', []))

    installed_apps.extend(include_apps)

    for app in installed_apps:
        apps.extend(list(get_app_depends(app, visited, installed_apps)))

    if not apps and os.path.exists(apps_dir):
        for p in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, p)) and p not in ['.svn', 'CVS', '.git'] and not p.startswith('.') and not p.startswith('_'):
                apps.append(p)

    return apps

def collect_settings(project_dir, include_apps=None, settings_file='settings.ini',
local_settings_file='local_settings.ini'):

    apps_dir = os.path.join(project_dir, 'apps')
    apps = get_apps(apps_dir, include_apps=include_apps, settings_file=settings_file, local_settings_file=local_settings_file)
    settings_file = os.path.join(apps_dir, settings_file)
    local_settings_file = os.path.join(apps_dir, local_settings_file)
    settings = []
    inifile = pkg.resource_filename('uliweb.core', 'default_settings.ini')
    # default_settings.ini 不需要 appname
    settings.append((None, inifile))
    for p in apps:
        path = get_app_dir(p)
        #deal with settings
        inifile = os.path.join(get_app_dir(p), 'settings.ini')
        if os.path.exists(inifile):
            # 返回 (appname, filepath) 元组
            settings.append((p, inifile))

    if os.path.exists(settings_file):
        # 项目级 settings.ini 也不需要 appname
        settings.append((None, settings_file))

    if os.path.exists(local_settings_file):
        settings.append((None, local_settings_file))
    return settings

def get_settings(project_dir, include_apps=None, settings_file='settings.ini',
    local_settings_file='local_settings.ini', default_settings=None):

    default_settings = default_settings or {}
    settings = collect_settings(project_dir, include_apps, settings_file,
        local_settings_file)

    x = pyini.Ini(lazy=True, basepath=os.path.join(project_dir, 'apps'))
    for item in settings:
        # 新格式: (appname, filepath)
        # 旧格式: filepath (字符串)
        if isinstance(item, tuple):
            appname, filepath = item
        else:
            # 兼容旧格式（字符串路径）
            appname = None
            filepath = item

        if 'default_settings.ini' in filepath:
            x.read(filepath)
        else:
            # 使用 collect_settings 返回的 appname
            # 如果 appname 为 None，则从路径中提取
            if appname is None:
                appname = os.path.basename(os.path.dirname(filepath))
            x.set_pre_variables({'appname': appname})
            x.read(filepath)
    d = dict([(k, repr(v)) for k, v in default_settings.items()])
    x.update(d or {})
    x.freeze()

    #process FILESYSTEM_ENCODING
    if not x.GLOBAL.FILESYSTEM_ENCODING:
        x.GLOBAL.FILESYSTEM_ENCODING = sys.getfilesystemencoding() or x.GLOBAL.DEFAULT_ENCODING
    return x

def is_in_web():
    # 使用 request.get_value() 来判断是否在 web 环境中
    return request.get_value() is not None

class DispatcherHandler(object):
    def __init__(self, application):
        self.application = application

class ContextStorage(object):
    """
    Used to save increament vars
    """

    __variables__ = {}

    def __init__(self, args={}):
        self.__class__.__variables__ = args
        self._vars = {}

    def __getattr__(self, key):
        try:
            return self['_vars'][key]
        except KeyError as e:
            try:
                return self[key]
            except KeyError as e:
                return None

    def copy(self):
        n = ContextStorage(self.__variables__)
        n._vars = self._vars.copy()
        return n

    def to_dict(self):
        d = self._vars.copy()
        d.update(self.__variables__)
        return d

    def __getitem__(self, key):
        try:
            return self._vars[key]
        except KeyError as e:
            return self.__variables__[key]

    def __setitem__(self, key, value):
        self._vars[key] = value

    def update(self, arg):
        self._vars.update(arg)

    def items(self):
        keys = set()
        for k, v in self._vars.items():
            keys.add(k)
            yield k, v

        for k, v in self.__variables__.items():
            if k not in keys:
                yield k, v

    def __repr__(self):
        return '<ContextStorage ' + repr(self.__variables__) + ' ' + repr(self._vars) + ' >'


class AsyncDispatcher:
    """支持 ASGI 3.0 接口的异步 Dispatcher

    采用完全延迟加载设计：
    - __init__ 中不进行任何 settings 加载或事件循环创建
    - 初始化延迟到第一次请求时进行
    - 这种设计简化了代码，自动适配所有运行上下文（Jupyter、pytest、uvicorn 等）

    如果需要在初始化时同步访问 settings（如某些中间件），可以调用 prepare() 方法进行预加载。
    """

    def __init__(self, apps_dir='apps', project_dir=None, include_apps=None,
                 start=True, default_settings=None, settings_file='settings.ini',
                 local_settings_file='local_settings.ini', **kwargs):

        # 将项目目录和 apps 目录添加到 sys.path
        # 当 apps 目录在 sys.path 中时，导入的模块 __module__ 是没有 apps. 前缀的
        # 例如：from home.views import index -> index.__module__ = 'home.views'
        # 这样 endpoint 就是 'home.views.index' 而不是 'apps.home.views.index'
        if project_dir:
            if project_dir not in sys.path:
                sys.path.insert(0, project_dir)
            # 将 apps 目录添加到 sys.path，以便模块可以被正确导入
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

        # 初始化标记
        self._initialized = False
        self._settings_loaded = False  # 标记 settings 是否已加载
        self._middleware_stack = None
        # 存储路由的参数类型信息：{route_path: {param_name: param_type}}
        self.route_param_types = {}
        # 存储静态视图列表
        self.static_views = []

        # 预先设置 application 到 __global__ 和 LocalProxy
        __global__.application = self
        application.set(self)

        # 重置 dispatch 绑定，确保每次创建新的 Dispatcher 时清理之前的绑定
        # 这对于测试环境非常重要，因为同一个进程中可能创建多个 Dispatcher 实例
        dispatch.reset()

        # 无论 start 是 True 还是 False，都同步加载 settings
        # 这样确保在请求前 settings 已经被初始化
        # 与 WSGI 版本的 Dispatcher 行为一致
        self._init_settings()

    def prepare(self):
        """手动初始化应用（用于命令行工具等场景）

        当 start=False 时，需要手动调用此方法来完成初始化
        """
        # 保存用户预先设置的 apps 值（如果有）
        # 这允许测试或其他场景中手动指定 apps 列表
        user_defined_apps = getattr(self, '_user_defined_apps', None)

        # 确保 settings 已加载
        if not self._settings_loaded:
            self._init_settings()

        # 如果用户预先设置了 apps，恢复它
        # 这必须在 _init_settings() 之后执行，因为 _init_settings() 会覆盖 self.apps
        if user_defined_apps is not None:
            self.apps = user_defined_apps

        # 设置 debug 模式（如果未设置）
        if not hasattr(self, 'debug'):
            self.debug = self.settings.GLOBAL.get('DEBUG', False)

        # 确保模板加载器已初始化
        if not hasattr(self, 'template_loader') or self.template_loader is None:
            self.get_template_dirs()
            self.install_template_loader()

        # 确保日志已设置
        if not hasattr(self, '_log_initialized') or not self._log_initialized:
            self.set_log()
            self._log_initialized = True

        # 导入视图模块，触发 expose 装饰器执行
        # 这会注册所有路由
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果有事件循环在运行，使用 run_in_executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                logger.info("prepare: Using ThreadPoolExecutor with running event loop")
                future = executor.submit(asyncio.run, self._import_views())
                try:
                    future.result()
                    logger.info("prepare: _import_views completed successfully")
                except Exception as e:
                    logger.error(f"prepare: _import_views failed with error: {e}")
                    raise
        except RuntimeError:
            # 没有事件循环在运行
            logger.info("prepare: No running event loop, creating new one")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._import_views())
                logger.info("prepare: _import_views completed successfully")
            except Exception as e:
                logger.error(f"prepare: _import_views failed with error: {e}")
                raise
            finally:
                loop.close()

        # 调用 startup_installed 钩子
        # 必须在 _init_routes() 之前调用，因为 startup_installed 会注册路由到 __exposes__
        # 然后 _init_routes() 会根据 __exposes__ 注册路由
        # 这与 WSGI 版本的调用顺序一致：startup_installed -> init_urls
        dispatch.call(self, 'startup_installed')

        # 调用 after_init_settings 钩子
        dispatch.call(self, 'after_init_settings')

        # 调用 after_init_apps 钩子，在所有 App 安装完成后调用
        # 这会触发 uliweb.contrib.orm.after_init_apps 来初始化数据库引擎
        dispatch.call(self, 'after_init_apps')

        # 导入视图模块后再初始化路由
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._init_routes())
                future.result()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._init_routes())
            finally:
                loop.close()

        return self

    @property
    def apps(self):
        """获取 apps 列表"""
        return getattr(self, '_apps', [])

    @apps.setter
    def apps(self, value):
        """设置 apps 列表，同时保存用户定义的 apps 值"""
        self._apps = value
        # 标记用户定义的 apps，以便在 prepare() 中恢复
        self._user_defined_apps = value

    def _init_settings(self):
        """同步初始化 settings"""
        import asyncio
        import concurrent.futures

        # 检查是否已经有事件循环在运行
        try:
            loop = asyncio.get_running_loop()
            # 如果已经有事件循环在运行，使用 run_in_executor 执行同步代码
            def load_settings_sync():
                return self._load_settings_sync()

            # 使用线程池执行同步加载
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(load_settings_sync)
                loaded_settings, apps = future.result()

            # 设置结果 - 必须在调用 dispatch.call 之前完成
            self.settings = loaded_settings
            __global__.settings = loaded_settings
            # 修复：设置 LocalProxy 的值为实际的 pyini.Ini 对象
            # 注意：这里使用模块级的 settings (LocalProxy)，而不是局部变量 loaded_settings
            settings.set(self.settings)
            self._settings_loaded = True

            # 如果用户没有预先设置 apps，则使用从 settings 加载的 apps
            # 这允许测试或其他场景中手动指定 apps 列表
            if getattr(self, '_user_defined_apps', None) is None:
                self._apps = apps

            # 初始化 dispatch 绑定（必须在调用 startup_installed 之前）
            self.install_binds()

            # 注意：不要在这里调用 _init_routes_sync() 和 startup_installed
            # 因为视图还没导入，路由还没注册
            # 这些操作会在 prepare() 方法中完成

            return
        except RuntimeError:
            # 没有事件循环在运行，可以使用 new_event_loop
            pass

        # 创建新的事件循环来执行异步初始化
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 执行异步初始化
            loop.run_until_complete(self._load_settings_and_apps())

            # 初始化 dispatch 绑定（必须在调用 startup_installed 之前）
            self.install_binds()

            # 注意：不要在这里调用 _init_routes_sync() 和 startup_installed
            # 因为视图还没导入，路由还没注册
            # 这些操作会在 prepare() 方法中完成
        finally:
            loop.close()

    def _load_settings_sync(self):
        """同步加载 settings（在线程池中执行）"""
        # 复用 _load_settings() 的内部逻辑，但以同步方式执行
        # 直接调用 load_settings 内部函数（不通过 run_in_executor）
        project_dir = self.project_dir
        if project_dir is None:
            project_dir = os.getcwd()

        # 定义内部函数，复用 _load_settings 中的逻辑
        def load_settings():
            from uliweb.core.SimpleFrame import collect_settings
            import uliweb.utils.pyini as pyini

            settings = collect_settings(
                project_dir,
                self.include_apps,
                self.settings_file,
                self.local_settings_file
            )
            x = pyini.Ini(lazy=True, basepath=os.path.join(project_dir, 'apps'))
            for item in settings:
                # 新格式: (appname, filepath)
                # 旧格式: filepath (字符串)
                if isinstance(item, tuple):
                    appname, filepath = item
                else:
                    # 兼容旧格式（字符串路径）
                    appname = None
                    filepath = item

                if 'default_settings.ini' in filepath:
                    x.read(filepath)
                else:
                    # 使用 collect_settings 返回的 appname
                    # 如果 appname 为 None，则从路径中提取
                    if appname is None:
                        appname = os.path.basename(os.path.dirname(filepath))
                    x.set_pre_variables({'appname': appname})
                    x.read(filepath)
            d = dict([(k, repr(v)) for k, v in self.default_settings.items()])
            x.update(d or {})
            x.freeze()
            if not x.GLOBAL.FILESYSTEM_ENCODING:
                x.GLOBAL.FILESYSTEM_ENCODING = sys.getfilesystemencoding() or x.GLOBAL.DEFAULT_ENCODING
            return x

        # 执行 settings 加载
        settings = load_settings()

        # 获取 apps 列表
        from uliweb.core.SimpleFrame import get_apps as get_sync_apps
        # 如果 apps_dir 是绝对路径，直接使用；否则拼接 project_dir
        if os.path.isabs(self.apps_dir):
            apps_dir_full = self.apps_dir
        else:
            apps_dir_full = os.path.join(self.project_dir, self.apps_dir) if self.project_dir else self.apps_dir
        apps = get_sync_apps(apps_dir_full, self.include_apps, self.settings_file, self.local_settings_file)

        return settings, apps

    async def _load_settings_and_apps(self):
        """加载 settings 和 apps"""
        # 加载 settings
        self.settings = await self._load_settings()

        # 加载 apps
        self.apps = await self._get_apps()

        # 安装 settings 到 __global__
        __global__.settings = self.settings

        # 同时设置到 LocalProxy - 修复：使用 self.settings 而不是 settings
        settings.set(self.settings)

        # 标记 settings 已加载
        self._settings_loaded = True

    def _init_routes_sync(self):
        """同步初始化路由"""
        # 设置域名
        self.domains = {}
        if hasattr(self.settings, 'DOMAINS') and self.settings.DOMAINS:
            from uliweb.utils._compat import import_
            urlparse = import_('urllib.parse', 'urlparse')
            for k, v in self.settings.DOMAINS.items():
                _domain = urlparse(v['domain'])
                self.domains[k] = {'domain': v.get('domain'), 'domain_parse': _domain,
                    'host': _domain.netloc or v.get('domain'),
                    'scheme': _domain.scheme or 'http', 'display': v.get('display', False),
                    'url_prefix': v.get('url_prefix', '')}

        # 使用 rules.merge_rules() 获取所有路由规则
        # 然后使用 rules.add_rule 注册路由
        # rules.add_rule 已经支持 websocket 参数
        for v in rules.merge_rules():
            appname, endpoint, url, kw = v
            static = kw.pop('static', None)
            if static:
                domain_name = 'static'
            else:
                domain_name = 'default'
            domain = self.domains.get(domain_name, {})
            url_prefix = domain.get('url_prefix', '')
            _url = url_prefix + url

            if static:
                self.static_views.append(endpoint)

            # 使用 rules.add_rule 注册路由
            # 这个函数支持 websocket 参数
            rules.add_rule(self.router, _url, endpoint, **kw)

    async def _async_init(self):
        """异步初始化方法"""
        if not self._initialized:
            await self.init()
            # 注意：init() 方法已经调用了 _init_routes()，不需要重复调用
            self._initialized = True

    async def init(self):
        """初始化 ASGI 应用"""
        # 加载设置
        self.settings = await self._load_settings()

        # 将 settings 重新设置到 LocalProxy 中
        # 因为在 __init__ 中可能设置为 None，现在需要更新为实际加载的值
        settings.set(self.settings)
        application.set(self)
        # 同时设置到 __global__，用于线程池等场景
        # 参考 WSGI 中 settings 和 application 使用 Global 的设计
        __global__.settings = self.settings
        __global__.application = self

        # 初始化应用
        self.apps = await self._get_apps()
        self.static_views = []

        # 处理域名配置
        self.process_domains(self.settings)

        # 获取 debug 模式配置
        self.debug = self.settings.GLOBAL.get('DEBUG', False)

        # 初始化中间件
        self.process_request_classes = []
        self.process_response_classes = []
        self.process_exception_classes = []

        # 初始化中间件列表
        self.middlewares = []

        # 初始化中间件配置
        self._init_middlewares()

        # 初始化模板目录和模板加载器
        self.get_template_dirs()
        self.install_template_loader()
        # 初始化日志系统
        # 初始化 dispatch 绑定（必须在调用 startup_installed 之前）
        self.install_binds()
        self.set_log()

        # 初始化 URL
        # 必须在 startup_installed 之前调用，因为 timezone 模块的 startup_installed
        # 会修改 now() 函数的行为，导致 timezone-aware 和 naive datetime 无法比较
        await self._init_routes()

        # 调用 startup_installed 钩子，这会触发 uliweb.contrib.template 的初始化
        # 并将 _tag_use 等函数添加到 template.default_namespace
        dispatch.call(self, 'startup_installed')
        # 调用 after_init_settings 钩子，在设置加载完成后调用
        dispatch.call(self, 'after_init_settings')

        # 调用 after_init_apps 钩子，在所有 App 安装完成后调用
        dispatch.call(self, 'after_init_apps')

        # 准备模板环境并调用 prepare_default_env
        env = await self._prepare_env()

        dispatch.call(self, 'prepare_default_env', env)

        # 保存 env 到 self.env，以便后续 get_view_env() 可以访问
        self.env = env

        # 调用 startup 钩子，所有初始化工作完成后执行
        dispatch.call(self, 'startup')

    def get_template_dirs(self):
        """
        获取模板目录，使用与同步 Dispatcher 相同的逻辑
        """
        def if_not_empty(dir):
            if not os.path.exists(dir):
                return
            for root, dirs, files in os.walk(dir):
                if dirs:
                    return True
                for f in files:
                    if f != 'readme.txt':
                        return True

        template_dirs = [os.path.join(self.project_dir, x) for x in self.settings.GLOBAL.TEMPLATE_DIRS or []]
        taglibs_dirs = []
        for p in reversed(self.apps):
            app_path = get_app_dir(p)
            path = os.path.join(app_path, 'templates')
            if if_not_empty(path):
                template_dirs.append(path)

            path = os.path.join(app_path, 'taglibs')
            if if_not_empty(path):
                taglibs_dirs.append(path)

        self.template_dirs = template_dirs
        self.taglibs_dirs = taglibs_dirs

    def install_template_loader(self):
        """
        安装模板加载器
        """
        Loader = import_attr(self.settings.get_var('TEMPLATE_PROCESSOR/loader'))
        args = self.settings.get_var('TEMPLATE')

        if self.debug:
            args['check_modified_time'] = True
            args['log'] = log
            args['debug'] = self.settings.get_var('GLOBAL/DEBUG_TEMPLATE', False)
        self.template_loader = Loader(self.template_dirs, **args)


    def install_binds(self):
        """处理 DISPATCH hooks"""
        #BINDS format
        #func = topic              #bind_name will be the same with function
        #bind_name = topic, func
        #bind_name = topic, func, {args}
        d = self.settings.get('BINDS', {})
        for bind_name, args in d.items():
            if not args:
                continue
            is_wrong = False
            if isinstance(args, (tuple, list)):
                if len(args) == 2:
                    dispatch.bind(args[0])(args[1])
                elif len(args) == 3:
                    if not isinstance(args[2], dict):
                        is_wrong = True
                    else:
                        dispatch.bind(args[0], **args[2])(args[1])
                else:
                    is_wrong = True
            elif isinstance(args, string_types):
                dispatch.bind(args)(bind_name)
            else:
                is_wrong = True
            if is_wrong:
                log.error('BINDS definition should be "function=topic" or "bind_name=topic, function" or "bind_name=topic, function, {"args":value1,...}"')
                raise UliwebError('BINDS definition [%s=%r] is not right' % (bind_name, args))

    def set_log(self):
        """设置日志"""
        import logging

        s = self.settings

        def _get_level(level):
            return getattr(logging, level.upper())

        #get basic configuration
        config = {}
        for k, v in s.LOG.items():
            if k in ['format', 'datefmt', 'filename', 'filemode']:
                config[k] = v

        if s.get_var('LOG/level'):
            config['level'] = _get_level(s.get_var('LOG/level'))
        logging.basicConfig(**config)

        if config.get('filename'):
            Handler = 'logging.FileHandler'
            if config.get('filemode'):
                _args =(config.get('filename'), config.get('filemode'))
            else:
                _args = (config.get('filename'),)
        else:
            Handler = 'logging.StreamHandler'
            _args = ()

        #process formatters
        formatters = {}
        for f, v in s.get_var('LOG.Formatters', {}).items():
            formatters[f] = logging.Formatter(v)

        #process handlers
        handlers = {}
        for h, v in s.get_var('LOG.Handlers', {}).items():
            handler_cls = v.get('class', Handler)
            handler_args = v.get('args', _args)
            handler_kwargs = v.get('kwargs', {})

            handler = import_attr(handler_cls)(*handler_args, **handler_kwargs)
            if v.get('level'):
                handler.setLevel(_get_level(v.get('level')))

            format = v.get('format')
            if format in formatters:
                handler.setFormatter(formatters[format])
            elif format:
                fmt = logging.Formatter(format)
                handler.setFormatter(fmt)

            handlers[h] = handler

        #process loggers
        for logger_name, v in s.get_var('LOG.Loggers', {}).items():
            if logger_name == 'ROOT':
                log = logging.getLogger('')
                log.handlers = []
            else:
                log = logging.getLogger(logger_name)

            if v.get('level'):
                log.setLevel(_get_level(v.get('level')))
            if 'propagate' in v:
                log.propagate = v.get('propagate')
            if 'handlers' in v:
                for h in v['handlers']:
                    if h in handlers:
                        log.addHandler(handlers[h])

    def process_domains(self, settings):
        """处理域名配置"""
        from uliweb.utils._compat import import_
        urlparse = import_('urllib.parse', 'urlparse')

        self.domains = {}

        # 新增：将 DOMAINS 配置转换为 __app_rules__
        # 这样 rules._fix_url 方法才能正确处理 app 前缀
        app_rules = {}

        for k, v in settings.DOMAINS.items():
            # 配置格式: {'url_prefix': '/knowbot', 'domain': '', 'display': False}
            domain_url = v.get('domain', '')
            url_prefix = v.get('url_prefix', '')
            display = v.get('display', False)

            # 解析域名
            try:
                _domain = urlparse(domain_url) if domain_url else None
            except Exception:
                _domain = None

            self.domains[k] = {
                'domain': domain_url,
                'domain_parse': _domain,
                'host': _domain.netloc if _domain else '',
                'scheme': _domain.scheme if _domain else 'http',
                'display': display,
                'url_prefix': url_prefix
            }

            # 将 url_prefix 添加到 app_rules
            # 这里的 key 使用域名名称（如 'default'）
            if url_prefix:
                app_rules[k] = url_prefix

        # 调用 set_app_rules 设置全局的 __app_rules__
        # 这样 _fix_url 方法就能正确生成 URL（如 /knowbot/dexpert/ws）
        if app_rules:
            rules.set_app_rules(app_rules)

    async def _handle_request(self, scope, receive, send):
        """处理请求的核心逻辑"""
        from starlette.exceptions import HTTPException
        from starlette.websockets import WebSocket

        # 根据 scope type 判断是 HTTP、WebSocket 还是 lifespan
        scope_type = scope.get("type", "unknown")
        if scope_type == "lifespan":
            return await self._handle_lifespan_request(scope, receive, send)
        elif scope_type == "websocket":
            return await self._handle_websocket_request(scope, receive, send)
        elif scope_type != "http":
            # 不是 HTTP 或 WebSocket，跳过处理
            logger.warning(f"_handle_request: Unsupported scope type: {scope_type}, skipping")
            return

        # 确保应用已初始化（处理首次请求时 settings 未加载的问题）
        if not self._initialized:
            await self._async_init()

        # 使用 req 作为局部变量名，避免遮蔽全局的 request (LocalProxy)
        req = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request.set(req)

        try:
            # 路由匹配
            rule, values = await self._match_route(req)
            mod, handler_cls, handler = self.prepare_request(req, rule)

            # 处理请求
            res = await self._open(req)

            # 检查是否是 SSE 流式响应（通过 scope 标记判断）
            # 如果是 SSE，中间件已经直接发送了响应，不需要再次发送
            if scope.get('_sse_streaming'):
                logger.debug(f"[_handle_request] SSE streaming mode, response already sent by middleware")
                return

            # 非 SSE 响应，需要手动发送
            await res(scope, receive, send)
        except (HTTPException, RuntimeError) as exc:
            # 处理 HTTP 异常（如 404）
            res = await self._handle_exception(req, exc)
            await res(scope, receive, send)
        finally:
            # 清理上下文
            request.reset(request_token)

    async def _handle_lifespan_request(self, scope, receive, send):
        """处理 ASGI lifespan 事件

        ASGI lifespan 协议：
        1. 服务器发送 'startup' 事件，应用执行初始化
        2. 应用发送 'startup.complete' 或 'startup.failed' 事件
        3. 服务器发送 'shutdown' 事件，应用执行清理
        4. 应用发送 'shutdown.complete' 事件
        """
        # 确保应用已初始化
        if not self._initialized:
            await self._async_init()

        # 接收 lifespan 事件
        message = await receive()

        if message["type"] == "lifespan.startup":
            # 执行启动逻辑
            try:
                # 调用 startup 钩子
                dispatch.call(self, 'startup')

                # 发送启动成功事件
                await send({"type": "lifespan.startup.complete"})
            except Exception as e:
                # 启动失败
                logger.error(f"Lifespan startup failed: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await send({
                    "type": "lifespan.startup.failed",
                    "message": str(e)
                })
        elif message["type"] == "lifespan.shutdown":
            # 执行关闭逻辑
            try:
                # 调用 shutdown 钩子
                dispatch.call(self, 'shutdown')

                # 发送关闭完成事件
                await send({"type": "lifespan.shutdown.complete"})
            except Exception as e:
                logger.error(f"Lifespan shutdown failed: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # 即使关闭失败，也发送完成事件
                await send({"type": "lifespan.shutdown.complete"})

    async def _handle_websocket_request(self, scope, receive, send):
        """处理 WebSocket 请求的核心逻辑"""
        from starlette.exceptions import HTTPException
        from starlette.websockets import WebSocket as StarletteWebSocket

        # 确保应用已初始化（与 HTTP 请求一致）
        if not self._initialized:
            await self._async_init()

        websocket = StarletteWebSocket(scope, receive, send)

        # 设置 WebSocket 上下文
        websocket_token = request.set(websocket)

        # 设置 settings 和 application 上下文（与 _open 方法一致）
        # 重要：使用初始化后的 self.settings
        settings_token = settings.set(self.settings)
        application_token = application.set(self)

        try:
            # 路由匹配
            matched_rule, values = await self._match_websocket_route(websocket)

            # 将 rule 对象绑定到 websocket，以便 _open_websocket 可以访问
            websocket.rule = matched_rule

            # 准备请求处理
            mod, handler_cls, handler = self.prepare_request(websocket, matched_rule)

            # 将 handler 和 handler_cls 保存到 websocket 对象上，以便 _open_websocket 可以访问
            websocket._handler = handler
            websocket._handler_cls = handler_cls

            # 调用视图处理 WebSocket
            await self._open_websocket(websocket)
        except (HTTPException, RuntimeError) as exc:
            # 处理异常
            await self._handle_websocket_exception(websocket, exc)
        finally:
            # 清理上下文
            # settings 和 application 使用 LocalProxy（普通全局变量），不需要 reset
            # request 和 response 使用 contextvars，需要 reset
            request.reset(websocket_token)

    async def _match_websocket_route(self, websocket):
        """匹配 WebSocket 路由"""
        from starlette.routing import WebSocketRoute

        path = websocket.url.path

        logger.debug(f"[WebSocket] _match_websocket_route called with path={path}")

        # 遍历所有路由进行匹配
        for route in self.router.routes:
            # 只处理 WebSocketRoute 对象
            if not isinstance(route, WebSocketRoute):
                continue
            try:
                route_path = route.path
                logger.debug(f"[WebSocket] Checking route: {route_path}")

                # 检查路径是否匹配
                matches = self._path_matches(route_path, path)
                logger.debug(f"[WebSocket] _path_matches({route_path}, {path}) = {matches}")

                if matches:
                    # 提取路径参数
                    path_params = self._extract_path_params(route_path, path)
                    logger.debug(f"[WebSocket] Matched route: {route_path}, params: {path_params}")
                    return route, path_params
            except Exception as e:
                logger.debug(f"[WebSocket] Error matching route {route_path}: {e}")
                continue

        # 如果没有找到匹配的路由，抛出 404 错误
        logger.debug(f"[WebSocket] No matching route found for path={path}")
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="WebSocket route not found")

    async def _open_websocket(self, websocket):
        """处理 WebSocket 连接的打开和消息循环"""
        from starlette.responses import JSONResponse
        import logging

        # 获取已通过 prepare_request 准备的 handler
        # 注意：在 _handle_websocket_request 中已经调用了 prepare_request
        # 并将 handler 设置到了 websocket 上
        handler = getattr(websocket, '_handler', None)
        handler_cls = getattr(websocket, '_handler_cls', None)
        rule = getattr(websocket, 'rule', None)

        # Debug log: 记录 WebSocket 连接信息
        logger.debug(f"[WebSocket] _open_websocket called. handler={handler}, handler_cls={handler_cls}, rule={rule}")
        logger.debug(f"[WebSocket] websocket.url={websocket.url}, websocket.scope type={websocket.scope.get('type')}")

        if handler:
            # 检查 handler 是否是协程函数
            if iscoroutinefunction(handler):
                # handler 已经是 bound method（已绑定 handler_cls），只需要传递 websocket
                try:
                    logger.debug(f"[WebSocket] Calling handler: {handler}, websocket: {websocket}")
                    await handler(websocket)
                except TypeError:
                    logger.debug(f"[WebSocket] First call failed with TypeError, trying ASGI style")
                    try:
                        # 尝试 ASGI 风格 (scope, receive, send)
                        await handler(websocket.scope, websocket._receive, websocket._send)
                    except Exception as e:
                        logger.debug(f"[WebSocket] ASGI style also failed: {e}")
                        # 使用默认处理
                        await self.handle_websocket(websocket.scope, websocket._receive, websocket._send)
            else:
                # 同步函数需要在协程池中执行
                import functools
                from contextvars import copy_context
                loop = asyncio.get_event_loop()
                ctx = copy_context()

                try:
                    partial_handler = functools.partial(handler, websocket)
                    await loop.run_in_executor(None, ctx.run, partial_handler)
                except TypeError:
                    # 尝试 ASGI 风格
                    try:
                        partial_handler = functools.partial(handler, websocket.scope, websocket._receive, websocket._send)
                        await loop.run_in_executor(None, ctx.run, partial_handler)
                    except Exception:
                        await self.handle_websocket(websocket.scope, websocket._receive, websocket._send)
        else:
            # 如果没有准备好的 handler，使用默认的 WebSocket 处理
            logger.debug(f"[WebSocket] No handler found, using default handle_websocket")
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
            except Exception as e:
                # 如果中间件导入失败，跳过
                import logging
                logging.getLogger('uliweb').warning(f"Failed to import middleware {middleware_path}: {e}")
                continue

        # 按顺序排序
        m.sort(key=lambda x: x[0])

        return [x[1] for x in m]

    async def _init_routes(self):
        """初始化路由，处理收集到的路由信息"""
        # 首先处理域名配置
        # 这与 _init_routes_sync 方法保持一致
        self.process_domains(self.settings)

        # 首先导入视图模块，这样 expose 装饰器才能被调用
        await self._import_views()

        # 合并路由规则 - 使用 rules.merge_rules() 而不是 _merge_rules()
        # 因为 rules.merge_rules() 会保留 websocket 参数
        merged_rules = rules.merge_rules()

        # 构建已注册路由的集合（用于去重和覆盖）
        # key: endpoint - 用于判断端点是否重复
        # value: (url, route_info) - 存储路由信息，支持后续覆盖
        # 这与 WSGI 版本的机制一致：endpoint 是端点的唯一标识
        # 后来的定义可以覆盖前面的
        registered_routes = {}

        # 检查是否已经有路由，如果有则跳过重复注册
        # 因为 _init_routes_sync 已经正确注册了路由
        existing_route_paths = set(r.path for r in self.router.routes)

        # 注册路由到路由器（仅当没有路由时）
        if not existing_route_paths:
            for rule_info in merged_rules:
                appname, endpoint, url, kw = rule_info

                # 处理静态视图标记
                static = kw.get('static', False)

                # 获取域名配置，静态路由使用 'static' 域名，其他使用 'default' 域名
                # 这与 WSGI 版本的 init_urls 方法保持一致
                if static:
                    domain_name = 'static'
                else:
                    domain_name = 'default'
                domain = self.domains.get(domain_name, {})
                url_prefix = domain.get('url_prefix', '')

                # 拼接 url_prefix
                _url = url_prefix + url

                # 转换 Werkzeug 风格路由到 Starlette 风格，返回 (转换后的规则, 参数类型字典)
                starlette_rule, param_types = _convert_route_param(_url)

                # 存储参数类型信息（即使是空字典也要存储，以支持简单参数如 /user/<id>）
                self.route_param_types[starlette_rule] = param_types

                # 处理静态视图 - 已经从 kw 中获取了 static，不需要再 pop
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

                # 记录已注册的路由（用于后续 EXPOSES 覆盖）
                registered_routes[endpoint] = (starlette_rule, endpoint)

        # 处理每个应用的 EXPOSES 路由（来自 settings.ini 的路由定义）
        # 这个处理不应该被跳过，因为 _init_routes_sync 可能没有处理 EXPOSES
        # 添加覆盖逻辑：如果 endpoint 已经通过 @expose 注册过，EXPOSES 可以覆盖
        for app_name in self.apps:
            # 使用应用的简短名称（如 'UPLOAD'）而不是完整路径（如 'ULIWEB.CONTRIB.UPLOAD'）
            app_short_name = app_name.split('.')[-1].upper()
            app_settings = self.settings.get(app_short_name, {})
            if hasattr(app_settings, 'EXPOSES') and app_settings.EXPOSES:
                for name, route_info in app_settings.EXPOSES.items():
                    if isinstance(route_info, (list, tuple)) and len(route_info) >= 2:
                        url, endpoint = route_info[:2]

                        # 覆盖逻辑：如果 endpoint 已经注册过，先移除旧的路由
                        # 后来的 EXPOSES 定义可以覆盖之前的 @expose 定义
                        if endpoint in registered_routes:
                            old_rule, old_endpoint = registered_routes[endpoint]
                            # 移除旧路由
                            self.router.routes = [r for r in self.router.routes if r.path != old_rule]
                            self.router.router.routes = [r for r in self.router.router.routes if r.path != old_rule]
                            logger.debug(f"Override EXPOSES route {url} -> {endpoint}, overriding previous @expose route")
                        # 转换 Werkzeug 风格路由到 Starlette 风格
                        starlette_rule, param_types = _convert_route_param(url)
                        # 存储参数类型信息
                        if param_types:
                            self.route_param_types[starlette_rule] = param_types

                        # 处理额外参数（methods, websocket 等）
                        # 根据 EXPOSES 文档，默认支持所有 HTTP 方法
                        kwargs = {}
                        if len(route_info) >= 3:
                            extra = route_info[2]
                            if isinstance(extra, dict):
                                # 第三参数是字典，包含 methods, websocket 等
                                kwargs['methods'] = extra.get('methods')
                                kwargs['websocket'] = extra.get('websocket')
                            elif isinstance(extra, str):
                                # 第三参数是字符串，可能是 "GET,POST" 格式
                                kwargs['methods'] = [m.strip().upper() for m in extra.split(',')]

                        # 如果没有指定 methods，默认支持所有 HTTP 方法
                        # 根据 EXPOSES 文档，这与 WSGI 行为一致
                        if not kwargs.get('methods'):
                            kwargs['methods'] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

                        # 处理 WebSocket 路由
                        websocket = kwargs.get('websocket')
                        if websocket:
                            self.router.add_websocket_route(starlette_rule, endpoint, name=name)
                        else:
                            self.router.add_route(starlette_rule, endpoint, name=name, methods=kwargs['methods'])
                    elif isinstance(route_info, str):
                        # 如果只有 URL，使用 name 作为 endpoint，同时作为 name 参数
                        url = route_info
                        # 先转换路由规则
                        starlette_rule, param_types = _convert_route_param(url)
                        # 存储参数类型信息
                        if param_types:
                            self.route_param_types[starlette_rule] = param_types

                        # 覆盖逻辑：如果 name 已经注册过，先移除旧的路由
                        if name in registered_routes:
                            old_rule, old_endpoint = registered_routes[name]
                            # 移除旧路由
                            self.router.routes = [r for r in self.router.routes if r.path != old_rule]
                            self.router.router.routes = [r for r in self.router.router.routes if r.path != old_rule]
                            logger.debug(f"Override EXPOSES route {url} -> {name}, overriding previous registration")

                        # 注册路由，使用 name 同时作为 endpoint 和路由名称
                        # 根据 EXPOSES 文档，默认支持所有 HTTP 方法
                        self.router.add_route(starlette_rule, name, name=name,
                            methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
                        # 同步更新 url_map，确保 build 方法能找到正确的路由
                        self.router.url_map[name] = self.router.routes[-1]
                        # 更新 registered_routes
                        registered_routes[name] = (starlette_rule, name)

        # 处理全局 EXPOSES 路由（来自 settings.ini 的路由定义）
        if hasattr(self.settings, 'EXPOSES') and self.settings.EXPOSES:
            # 获取 url_prefix
            default_domain = self.domains.get('default', {})
            url_prefix = default_domain.get('url_prefix', '')

            for name, route_info in self.settings.EXPOSES.items():
                if isinstance(route_info, (list, tuple)) and len(route_info) >= 2:
                    url, endpoint = route_info[:2]

                    # 覆盖逻辑：如果 endpoint 已经注册过，先移除旧的路由
                    if endpoint in registered_routes:
                        old_rule, old_endpoint = registered_routes[endpoint]
                        # 移除旧路由
                        self.router.routes = [r for r in self.router.routes if r.path != old_rule]
                        self.router.router.routes = [r for r in self.router.router.routes if r.path != old_rule]
                        logger.debug(f"Override global EXPOSES route {url} -> {endpoint}, overriding previous registration")
                    # 添加 url_prefix
                    full_url = url_prefix + url
                    # 转换 Werkzeug 风格路由到 Starlette 风格
                    starlette_rule, param_types = _convert_route_param(full_url)
                    # 存储参数类型信息
                    if param_types:
                        self.route_param_types[starlette_rule] = param_types

                    # 处理额外参数（methods, websocket 等）
                    kwargs = {}
                    if len(route_info) >= 3:
                        extra = route_info[2]
                        if isinstance(extra, dict):
                            kwargs['methods'] = extra.get('methods')
                            kwargs['websocket'] = extra.get('websocket')
                        elif isinstance(extra, str):
                            kwargs['methods'] = [m.strip().upper() for m in extra.split(',')]

                    # 如果没有指定 methods，默认支持所有 HTTP 方法
                    if not kwargs.get('methods'):
                        kwargs['methods'] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

                    # 处理 WebSocket 路由
                    websocket = kwargs.get('websocket')
                    if websocket:
                        self.router.add_websocket_route(starlette_rule, endpoint, name=name)
                    else:
                        self.router.add_route(starlette_rule, endpoint, name=name, methods=kwargs['methods'])
                elif isinstance(route_info, str):
                    # 如果只有 URL，使用 name 作为 endpoint
                    url = route_info
                    # 覆盖逻辑：如果 name 已经注册过，先移除旧的路由
                    if name in registered_routes:
                        old_rule, old_endpoint = registered_routes[name]
                        # 移除旧路由
                        self.router.routes = [r for r in self.router.routes if r.path != old_rule]
                        self.router.router.routes = [r for r in self.router.router.routes if r.path != old_rule]
                        logger.debug(f"Override global EXPOSES route {url} -> {name}, overriding previous registration")

                    starlette_rule, param_types = _convert_route_param(url)
                    # 存储参数类型信息
                    if param_types:
                        self.route_param_types[starlette_rule] = param_types
                    # 注册路由
                    # 根据 EXPOSES 文档，默认支持所有 HTTP 方法
                    self.router.add_route(starlette_rule, name, name=name,
                        methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])

    async def _import_views(self):
        """导入视图模块，触发 expose 装饰器的执行"""
        from uliweb.utils.common import myimport
        import importlib
        import sys

        # 添加项目目录和 apps 目录到 Python 路径
        # 当 apps 目录在 sys.path 中时，导入的模块 __module__ 是没有 apps. 前缀的
        # 例如：from home.views import index -> index.__module__ = 'home.views'
        # 这样 endpoint 就是 'home.views.index' 而不是 'apps.home.views.index'
        if self.project_dir:
            if self.project_dir not in sys.path:
                sys.path.insert(0, self.project_dir)
            apps_path = os.path.join(self.project_dir, self.apps_dir)
            if apps_path not in sys.path:
                sys.path.insert(0, apps_path)

        # 收集所有应用的视图模块
        views_modules = []
        for app in self.apps:
            # 获取应用目录
            app_dir = self._get_app_dir(app)

            # 导入应用目录下的 views*.py 文件（包括 views.py 和 views_xxx.py）
            if os.path.exists(app_dir) and os.path.isdir(app_dir):
                for filename in os.listdir(app_dir):
                    if filename.startswith("views") and filename.endswith(".py"):
                        module_name = filename[:-3]  # 去掉 .py 后缀
                        full_module = f"{app}.{module_name}"
                        try:
                            myimport(full_module)
                            views_modules.append(full_module)
                        except ImportError as e:
                            # 导入失败时抛出异常，使调试服务器退出
                            import traceback
                            raise ImportError(
                                f"Failed to import view module '{full_module}': {e}\n"
                                f"This may be caused by missing dependencies or syntax errors.\n"
                                f"Traceback:\n{traceback.format_exc()}"
                            ) from e
                        except SyntaxError as e:
                            # 语法错误也抛出异常
                            import traceback
                            raise SyntaxError(
                                f"Syntax error in view module '{full_module}': {e}\n"
                                f"Traceback:\n{traceback.format_exc()}"
                            ) from e

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

    def _get_app_dir(self, app):
        """获取应用目录"""
        from uliweb.core.SimpleFrame import get_app_dir
        return get_app_dir(app)

    async def _load_settings(self):
        """异步加载设置"""
        # 处理 project_dir 为 None 的情况
        project_dir = self.project_dir
        if project_dir is None:
            project_dir = os.getcwd()

        # 使用协程池执行同步的 settings 加载
        # 直接调用 collect_settings 和 pyini.Ini，避免 get_settings 导入问题
        from uliweb.core.SimpleFrame import collect_settings
        import uliweb.utils.pyini as pyini

        def load_settings():
            settings = collect_settings(
                project_dir,
                self.include_apps,
                self.settings_file,
                self.local_settings_file
            )
            x = pyini.Ini(lazy=True, basepath=os.path.join(project_dir, 'apps'))
            for item in settings:
                # 新格式: (appname, filepath)
                # 旧格式: filepath (字符串)
                if isinstance(item, tuple):
                    appname, filepath = item
                else:
                    # 兼容旧格式（字符串路径）
                    appname = None
                    filepath = item

                # 判断是否是默认设置文件
                if 'default_settings.ini' in filepath:
                    x.read(filepath)
                else:
                    # 使用 collect_settings 返回的 appname
                    # 如果 appname 为 None，则从路径中提取
                    if appname is None:
                        appname = os.path.basename(os.path.dirname(filepath))
                    x.set_pre_variables({'appname': appname})
                    x.read(filepath)
            d = dict([(k, repr(v)) for k, v in self.default_settings.items()])
            x.update(d or {})
            x.freeze()
            # process FILESYSTEM_ENCODING
            if not x.GLOBAL.FILESYSTEM_ENCODING:
                x.GLOBAL.FILESYSTEM_ENCODING = sys.getfilesystemencoding() or x.GLOBAL.DEFAULT_ENCODING
            return x

        loop = asyncio.get_event_loop()
        settings = await loop.run_in_executor(
            None,
            load_settings
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
        env['functions'] = functions

        return env

    def _url_for(self, endpoint, **values):
        """URL 生成函数 - 异步版本

        参考模块级 url_for 函数的实现：
        1. rules.get_endpoint(endpoint) - 获取端点
        2. 处理应用别名 __app_alias__
        3. 处理 URL 命名 __url_names__
        4. adapter.build(endpoint, values, force_external=_external) - 构建 URL
        """
        from . import rules

        # 1. 获取端点 - 如果传入的是函数，先获取其 endpoint
        point = rules.get_endpoint(endpoint)

        # 2. 处理应用别名
        for k, v in __app_alias__.items():
            if point.startswith(k):
                point = v + point[len(k):]
                break

        # 3. 处理 URL 命名 - 如果 point 在 __url_names__ 中，转换为实际的 endpoint
        if point in rules.__url_names__:
            point = rules.__url_names__[point]

        # 4. 处理域名相关参数
        _domain_name = values.pop('_domain_name', 'default')
        _external = values.pop('_external', False)

        # 获取域名配置
        domain = self.domains.get(_domain_name, {})
        if not _external:
            _external = domain.get('display', False)

        # 5. 使用 UliwebRouter 的 build 方法构建 URL
        try:
            url = self.router.build(point, values, force_external=_external)

            # 如果需要外部 URL，添加域名
            if _external and domain.get('domain'):
                from urllib.parse import urljoin
                url = urljoin(domain.get('domain'), url)

            return url
        except Exception as e:
            # 如果构建失败，抛出异常
            raise ValueError(f"url_for error for {endpoint} (point={point}): {e}")

    def _error(self, message='', errorpage=None, **kwargs):
        """错误处理函数"""
        # 这里需要实现异步版本的 error
        # 暂时简单实现
        from starlette.responses import JSONResponse
        # 确保 message 是字符串类型，避免 LazyString 等无法 JSON 序列化的类型
        if hasattr(message, '__str__'):
            message = str(message)
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

        # 使用 req 作为局部变量名，避免遮蔽全局的 request (LocalProxy)
        req = Request(scope, receive, send)

        # 设置请求上下文
        request_token = request.set(req)

        try:
            # 处理请求
            response = await self._open(req)
            await response(scope, receive, send)
        finally:
            # 清理上下文
            request.reset(request_token)

    async def handle_websocket(self, scope, receive, send):
        """处理 WebSocket 请求"""
        from starlette.websockets import WebSocket
        websocket = WebSocket(scope, receive, send)

        # 设置 WebSocket 上下文
        websocket_token = request.set(websocket)

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
            request.reset(websocket_token)

    async def _handle_websocket_message(self, websocket, message):
        """处理 WebSocket 消息"""
        # 默认实现：回显消息
        if message["type"] == "websocket.receive":
            await websocket.send_text(f"Echo: {message.get('text', '')}")

    async def _open(self, req):
        """处理请求的核心方法 - 异步版本"""
        # 使用 res 作为局部变量名，避免遮蔽全局的 response (LocalProxy)
        res = Response()
        response_token = response.set(res)

        # 设置 request 上下文（如果还没有设置的话）
        # 注意：handle_http 和 _handle_request 已经在调用 _open 之前设置了 request
        # 这里不再重复设置，避免覆盖已有的 context

        # 设置设置上下文
        settings_token = settings.set(self.settings)

        # 设置应用上下文
        application_token = application.set(self)

        try:
            # 处理 CORS 预检请求
            if self.settings.GLOBAL.DEFAULT_CORS and req.method == "OPTIONS":
                return await self._handle_cors_preflight(req)

            # 路由匹配
            rule, values = await self._match_route(req)

            # 准备请求处理
            mod, handler_cls, handler = self.prepare_request(req, rule)

            # 处理静态视图
            if rule.endpoint in self.static_views:
                res = await self.call_view(mod, handler_cls, handler, req, res, kwargs=values)
            else:
                # 处理中间件
                res = await self._process_middleware(req, res, mod, handler_cls, handler, values)

            # 处理 CORS 响应头
            if self.settings.GLOBAL.DEFAULT_CORS:
                res = await self._add_cors_headers(req, res)

            return res

        except Exception as e:
            return await self._handle_exception(req, e)
        finally:
            # 清理上下文
            # settings 和 application 使用 LocalProxy（普通全局变量），不需要 reset
            # request 和 response 使用 contextvars，需要 reset
            response.reset(response_token)

    async def _match_route(self, request):
        """异步路由匹配 - 使用 Starlette Router 的内置匹配功能"""
        from starlette.exceptions import HTTPException
        from starlette.routing import Match

        # 获取请求的 scope
        scope = request.scope

        # 遍历所有路由，使用 Starlette 的 route.matches 方法进行匹配
        # Starlette Router 已经预编译了正则表达式，性能更好
        for route in self.router.router.routes:
            # 只处理 Route 对象，跳过 Mount 对象
            if not isinstance(route, Route):
                continue

            match, child_scope = route.matches(scope)

            if match == Match.FULL:
                # 完全匹配，提取路径参数
                path_params = child_scope.get('path_params', {})

                # 根据 route_param_types 进行类型转换
                # Starlette 返回的是字符串，需要转换为正确的类型
                route_path = route.path
                param_types = self.route_param_types.get(route_path, {})

                converted_params = {}
                for name, value in path_params.items():
                    param_type = param_types.get(name)
                    if param_type == 'int':
                        converted_params[name] = int(value)
                    elif param_type == 'float':
                        converted_params[name] = float(value)
                    else:
                        converted_params[name] = value

                return route, converted_params
            elif match == Match.PARTIAL:
                # 部分匹配（方法不匹配），可能是 GET/POST 等方法不匹配
                # 对于这种情况，我们应该返回 405 Method Not Allowed
                # 而不是 404 Not Found
                # 返回 405 错误
                raise HTTPException(status_code=405, detail=f"Method {scope.get('method')} not allowed for {scope.get('path')}")

        # 如果没有匹配到路由，抛出 404 异常
        raise HTTPException(status_code=404)

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
            except Exception as e:
                # 如果中间件导入失败，跳过
                import logging
                logging.getLogger('uliweb').warning(f"Failed to import middleware {middleware_path}: {e}")
                continue

        # 按顺序排序
        m.sort(key=lambda x: x[0])

        return [x[1] for x in m]

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
        # 使用 __global__.settings 而不是 get_settings()
        # 因为 get_settings() 使用 settings.get(None)，而 settings 的 _env 是 _globals
        # 这会导致在请求处理时 settings 变成 None
        local_env['settings'] = __global__.settings

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
        logger.debug(f"[_call_function] START - handler: {handler}")

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
            logger.debug(f"[_call_function] handler is coroutine function, awaiting...")
            result = await handler(*call_args, **call_kwargs)
            logger.debug(f"[_call_function] after await, result type: {type(result)}, result: {result}")
        else:
            # 同步函数需要在协程池中执行
            # run_in_executor 只接受位置参数，使用 functools.partial 绑定参数
            import functools
            from contextvars import copy_context
            loop = asyncio.get_event_loop()

            # 获取当前 contextvars 上下文
            ctx = copy_context()

            logger.debug(f"[_call_function] handler is sync function, using run_in_executor")
            if call_kwargs:
                # 使用 partial 绑定关键字参数，不再额外传递位置参数
                partial_handler = functools.partial(handler, **call_kwargs)
                # 使用 copy_context 确保 contextvars 在线程中正确传播
                result = await loop.run_in_executor(None, ctx.run, partial_handler)
            else:
                # 使用 copy_context 确保 contextvars 在线程中正确传播
                result = await loop.run_in_executor(None, ctx.run, handler, *call_args)

            logger.debug(f"[_call_function] after run_in_executor, result type: {type(result)}, result: {result}")

            # 检查结果是否是异步生成器或异步迭代器
            # 如果是，需要在异步上下文中保持原样返回，而不是等待它
            # 注意：这里不能直接用 inspect.isasyncgenerator(result) 判断，
            # 因为 result 可能是被 copy_context.run() 包装后的结果
            # 我们需要检查它是否具有 __aiter__ 方法
            if hasattr(result, '__aiter__'):
                # 这是一个异步生成器或异步迭代器
                # 返回它而不是等待它，让调用者自己处理迭代
                logger.debug(f"[_call_function] Detected async generator/iterator: {type(result)}, returning as-is")
                return result

        # 处理 LocalProxy 响应
        if isinstance(result, LocalProxy) and result._obj_name == 'response':
            result = get_response()

        logger.debug(f"[_call_function] END - returning result type: {type(result)}")
        return result

    async def wrap_result(self, handler, result, request, response, env):
        """异步包装结果"""
        from starlette.responses import Response as StarletteResponse
        from starlette.responses import JSONResponse
        from starlette.responses import StreamingResponse

        logger.debug(f"[wrap_result] START - result type: {type(result)}, result: {result}")
        logger.debug(f"[wrap_result] result has __aiter__: {hasattr(result, '__aiter__')}")

        # 检查结果是否是 SSEStreamResponse（已格式化的 SSE 数据）
        # 如果是，直接返回，不使用 StreamingResponse 包装
        # 因为 SSEStreamResponse 已经生成了完整的 SSE 格式数据（data: {...}\n\n）
        from starlette.responses import Response as StarletteResponse_
        if isinstance(result, StarletteResponse_):
            # 检查是否是 SSE 流式响应（media_type 为 text/event-stream）
            media_type = getattr(result, 'media_type', '') or ''
            logger.debug(f"[wrap_result] Result is StarletteResponse, media_type={media_type}")
            if 'text/event-stream' in media_type:
                logger.debug(f"[wrap_result] Detected SSEStreamResponse, returning as-is")
                return result

        # 检查结果是否是异步生成器或异步迭代器
        # 如果是，需要使用 StreamingResponse 来处理
        if hasattr(result, '__aiter__'):
            # 这是一个异步生成器或异步迭代器
            # 检查 media_type，如果已经有 response 对象，使用它的 media_type
            media_type = getattr(response, 'media_type', 'text/plain')
            logger.debug(f"[wrap_result] Detected async generator, using StreamingResponse with media_type={media_type}")
            return StreamingResponse(result, media_type=media_type)

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
        # 使用 copy_context 确保 contextvars 在线程池中正确传播
        from contextvars import copy_context
        ctx = copy_context()
        content = await loop.run_in_executor(
            None,
            ctx.run,
            self._sync_render_template,
            template_file, vars, env
        )

        return content

    def _sync_render_template(self, template_file, vars, env):
        """同步渲染模板（在协程池中执行）"""
        # 获取模板目录
        template_dirs = getattr(self, 'template_dirs', [])

        # 尝试从各个模板目录中查找模板文件
        for template_dir in template_dirs:
            template_path = os.path.join(template_dir, template_file)
            if os.path.exists(template_path):
                # 找到模板文件，使用 AsyncDispatcher 的 template_loader 进行渲染
                try:
                    # 使用已初始化的 template_loader，它包含了 taglibs 配置
                    loader = self.template_loader

                    if loader is None:
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

                # 如果同时有 dispatch 和 __call__，优先使用 dispatch（高级中间件）
                # 因为 SessionMiddle 等需要使用 dispatch 方法来访问 request 对象
                if has_dispatch and has_asgi_call:
                    # 优先使用 dispatch，忽略 __call__
                    has_asgi_call = False

                if has_asgi_call:
                    # ASGI 中间件：直接包装
                    # 需要传递 self 作为 app 参数，以及 settings
                    if isinstance(middleware, type):
                        middleware_instance = middleware(self, self.settings)
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

            # 创建请求对象，使用 req 避免与全局 request 冲突
            req = Request(scope, receive, send)

            # 设置全局 request LocalProxy
            # 这样中间件中的 functions.get_auth_user() 等函数可以访问 request.session
            request_token = request.set(req)

            # 标记响应是否已经被发送
            response_sent = False

            # 创建 call_next 函数
            async def call_next(req):
                # 创建一个缓冲区来捕获响应
                response_body = b""
                response_status = None
                response_headers = []
                is_streaming = False  # 标记是否为流式响应
                start_sent = False  # 标记 start 消息是否已发送

                # 创建自定义的 send 函数来捕获响应
                async def capture_send(message):
                    nonlocal response_body, response_status, response_headers, is_streaming, start_sent

                    # 检查是否已经标记为 SSE 流式响应完成
                    if scope.get('_sse_completed'):
                        logger.debug(f"[Middleware] SSE streaming already completed, ignoring message: {message.get('type')}")
                        return

                    if message["type"] == "http.response.start":
                        response_status = message["status"]
                        response_headers = list(message.get("headers", []))  # 确保是可变的列表
                        # 检查是否为流式响应（text/event-stream）
                        for header in response_headers:
                            if len(header) == 2:
                                key, value = header
                                if isinstance(key, bytes):
                                    key = key.decode('latin-1').lower()
                                else:
                                    key = key.lower()
                                if key == 'content-type':
                                    if isinstance(value, bytes):
                                        value = value.decode('latin-1').lower()
                                    elif isinstance(value, str):
                                        value = value.lower()
                                    else:
                                        value = str(value).lower()
                                    # 检查是否为 SSE 流式响应
                                    if 'text/event-stream' in value:
                                        is_streaming = True
                        # 对于 SSE 响应，立即发送 start 消息并标记
                        if is_streaming:
                            scope['_sse_streaming'] = True
                            await send(message)
                            start_sent = True
                            return
                        # 非 SSE 响应，缓冲 start 消息
                        start_sent = True
                    elif message["type"] == "http.response.body":
                        body_chunk = message.get("body", b"")
                        # 如果是 SSE 流式响应，直接传递消息，不缓冲数据
                        if is_streaming:
                            await send(message)
                            # 如果是最后一个 chunk，标记 SSE 完成
                            if not message.get("more_body", True):
                                scope['_sse_completed'] = True
                            return
                        response_body += body_chunk
                        # 如果是最后一个 chunk，创建响应对象
                        if not message.get("more_body", False):
                            pass  # 后续处理

                logger.debug(f"[Middleware] Before call_next, is_streaming={is_streaming}")

                # 创建新的 scope，可能需要修改
                new_scope = scope.copy()
                # 调用下一个应用
                try:
                    await next_app(new_scope, receive, capture_send)

                    logger.debug(f"[Middleware] After call_next, is_streaming={is_streaming}, response_body_size={len(response_body)}")

                    # If streaming response, return None directly so framework handles it
                    if is_streaming:
                        logger.debug(f"[Middleware] Returning None for streaming response")
                        return None

                    # Create response object
                    from starlette.responses import Response as StarletteResponse

                    # Convert headers, converting bytes to string
                    converted_headers = {}
                    if response_headers:
                        for header in response_headers:
                            if len(header) == 2:
                                key, value = header
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
                    # Re-raise if inner app raised exception
                    raise e

            # Dispatch middleware
            request_success = False
            try:
                response = await middleware.dispatch(req, call_next)
                # Check if response was sent via call_next (e.g., SSE streaming)
                if scope.get('_sse_streaming'):
                    logger.debug(f"[Middleware] SSE streaming response already sent via call_next, skipping response")
                    request_success = True
                    return None
                # Send response
                if response is not None:
                    await response(scope, receive, send)
                    request_success = True
                    return response
                else:
                    new_scope = scope.copy()
                    response = await next_app(new_scope, receive, send)
                    request_success = True
                    return response
            except Exception as e:
                # Log detailed exception stack and roll back the transaction
                logger.error(f"[ASGI Middleware Error] Exception occurred during request processing: {e}", exc_info=True)
                try:
                    RollbackAll()
                except Exception as rollback_err:
                    logger.error(f"[ASGI Middleware Error] RollbackAll failed: {rollback_err}", exc_info=True)
                raise e
            finally:
                # Commit ORM database transaction only on success path to prevent persisting invalid data
                if request_success:
                    try:
                        CommitAll()
                    except Exception as commit_err:
                        logger.error(f"[ASGI Middleware Error] CommitAll failed: {commit_err}", exc_info=True)
                # Clean up request context
                request.reset(request_token)

        return app

    def _wrap_asgi_middleware(self, middleware, next_app):
        """包装底层 ASGI 中间件"""
        # 设置中间件的 application 属性指向下一个应用
        middleware.application = next_app

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
            # 使用 copy_context 确保 contextvars 在线程池中正确传播
            from contextvars import copy_context
            ctx = copy_context()
            return await loop.run_in_executor(None, ctx.run, method, *args)

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
        from starlette.responses import JSONResponse, RedirectResponse
        import traceback

        # 首先检查是否是 RedirectException（重定向异常）
        # RedirectException 有 get_response() 方法可以返回重定向响应
        if isinstance(exception, RedirectException):
            return exception.get_response()

        # 检查是否是 uliweb 的 HTTPError（自定义错误类）
        # 需要在检查 StarletteHTTPException 之前进行，因为 HTTPError 可能是自定义类
        if hasattr(exception, 'errorpage') and hasattr(exception, 'errors'):
            # 这是 uliweb 的 HTTPError
            # 检查 errors 中是否有 message
            message = exception.errors.get('message', str(exception))

            # 检查是否是重定向错误（errorpage 不为 None 且不是默认错误页）
            errorpage = exception.errorpage
            if errorpage and errorpage != 'error.html':
                # 重定向到错误页面
                return RedirectResponse(url=errorpage, status_code=302)
            else:
                # 返回错误信息
                return JSONResponse(
                    {'error': message},
                    status_code=403
                )

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
            # 始终记录错误日志（包括 500 错误），即使 DEBUG=False
            logger.error("Request error: %s\n%s", exception, traceback.format_exc())

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

    def __init__(self, project_dir=None, include_apps=None):
        self.project_dir = project_dir
        self.include_apps = include_apps or []
        # 不在这里初始化，延迟到 __call__ 时初始化

    def _initialize(self):
        """初始化 ASGI 应用"""
        if not self._initialized:
            logger.info("ASGIApplication._initialize: Starting initialization...")

            # 处理 project_dir 为 None 的情况
            if self.project_dir is None:
                # 尝试从环境变量获取项目目录
                self.project_dir = os.environ.get('PROJECT_DIR', os.getcwd())
                logger.info(f"ASGIApplication._initialize: Using project_dir from env: {self.project_dir}")

            # 从环境变量获取 include_apps
            include_apps_env = os.environ.get('INCLUDE_APPS', '')
            if include_apps_env:
                include_apps = [app.strip() for app in include_apps_env.split(',') if app.strip()]
            else:
                include_apps = self.include_apps

            logger.info(f"ASGIApplication._initialize: Creating AsyncDispatcher with project_dir={self.project_dir}")

            # 创建 ASGI Dispatcher
            # 注意：apps_dir 只需要传递 'apps'，而不是完整路径
            # 因为 AsyncDispatcher 会将 project_dir 和 apps_dir 拼接
            try:
                asgi_app = AsyncDispatcher(
                    apps_dir='apps',
                    project_dir=self.project_dir,
                    include_apps=include_apps
                )
                logger.info("ASGIApplication._initialize: AsyncDispatcher created, calling prepare()...")
            except Exception as e:
                logger.error(f"ASGIApplication._initialize: Failed to create AsyncDispatcher: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

            # 调用 prepare() 方法确保视图模块被导入，路由被正确注册
            try:
                asgi_app.prepare()
                logger.info("ASGIApplication._initialize: prepare() completed successfully")
            except Exception as e:
                logger.error(f"ASGIApplication._initialize: prepare() failed: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

            # 保存实例
            ASGIApplication._instance_asgi_app = asgi_app

            self._initialized = True
            logger.info("ASGIApplication._initialize: Initialization completed")

    async def __call__(self, scope, receive, send):
        """ASGI 接口"""
        try:
            self._initialize()
            await ASGIApplication._instance_asgi_app(scope, receive, send)
        except Exception as e:
            logger.error(f"ASGIApplication.__call__: Exception caught: {e}")
            import traceback
            logger.error(f"ASGIApplication.__call__: Traceback:\n{traceback.format_exc()}")
            raise

# 上下文管理中间件
async def context_middleware(app):
    """管理请求上下文的中间件"""
    async def middleware(scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive, send)
            token = request.set(request)
            try:
                response = await app(scope, receive, send)
                return response
            finally:
                request.reset(token)
        else:
            return await app(scope, receive, send)
    return middleware


# 全局辅助函数
def get_request():
    """获取当前请求对象"""
    return request.get_value()

def get_response():
    """获取当前响应对象"""
    return response.get_value()

def get_settings():
    """获取当前设置对象"""
    return settings.get_value()

def get_application():
    """获取当前应用对象"""
    return application


# 不再需要从 context.py 导入，因为已经在模块顶部定义了
# request, response, settings, application


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
    from starlette.responses import Response
    from .js import json_dumps

    # 处理 status 参数，转换为 status_code
    if 'status' in kwargs:
        kwargs['status_code'] = kwargs.pop('status')

    # 处理 content_type
    content_type = kwargs.pop('content_type', 'application/json')

    # 使用 json_dumps 处理 LazyString 等特殊类型
    # json_dumps 内部使用 JSONEncoder 的 default=simple_value
    content = json_dumps(data)

    return Response(content, media_type=content_type, **kwargs)


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
