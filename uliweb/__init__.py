"""
Uliweb - Easy Python Web Framework
"""

__version__ = '3.0.0'
__author__ = 'Limodou'
__author_email__ = 'limodou@gmail.com'
__url__ = 'https://github.com/limodou/uliweb3'
__license__ = 'BSD'

# 导入管理命令需要的函数（避免循环导入）
from .core.SimpleFrame import get_apps, get_app_dir, functions, is_in_web, error, Finder, decorators
from .core.js import json_dumps


# 首先定义错误类，避免循环导入
class UliwebError(Exception):
    """Uliweb 基础错误类"""
    pass


class HTTPError(Exception):
    """HTTP 错误类"""
    pass


class RedirectException(Exception):
    """重定向异常类"""
    pass


class Middleware(object):
    """Uliweb 中间件基类 - 支持 ASGI 两种接口"""
    ORDER = 500  # 默认优先级

    def __init__(self, application, settings):
        self.application = application
        self.settings = settings

    async def __call__(self, scope, receive, send):
        """
        底层 ASGI 中间件接口。
        所有中间件逻辑（修改 scope/包装 receive/包装 send/异常处理）
        都应该在这个方法内实现。
        """
        await self.application(scope, receive, send)

    async def dispatch(self, request, call_next):
        """
        高级中间件接口 - 仿照 Starlette 的 BaseHTTPMiddleware。
        :param request: 请求对象
        :param call_next: 调用下一个中间件或视图函数的异步函数
        :return: 响应对象
        """
        # 调用下一个中间件或视图函数
        response = await call_next(request)
        return response


# 标记 ASGI 可用性
ASGI_AVAILABLE = False

# 尝试导入 ASGI 组件
try:
    # 直接从 SimpleFrame.py 导入所有 ASGI 组件
    from .core.SimpleFrame import (
        Request,
        Response,
        expose,
        POST,
        GET,
        redirect,
        Redirect,
        json,
        url_for,
        merge_rules,
        _convert_route_param,
        _merge_rules,
        context_middleware,
        get_request,
        get_response,
        get_settings,
        get_application,
        request,
        response,
        settings,
        application,
    )
    # 如果导入成功，标记 ASGI 可用
    ASGI_AVAILABLE = True

    # 从 SimpleFrame.py 导入 AsyncDispatcher（已从 starlette.py 迁移）
    from .core.SimpleFrame import AsyncDispatcher, ASGIApplication
    Dispatcher = AsyncDispatcher

except ImportError:
    # Uliweb3 需要 Starlette，不再支持 WSGI 回退
    raise ImportError(
        "Uliweb3 需要 Starlette。请运行: pip install starlette"
    )

# 向后兼容：导出 models 对象（来自 uliweb.contrib.orm）
# 旧版代码使用：from uliweb import models; model = models.xxx
# 新版代码使用：from uliweb import get_model; model = get_model('xxx')
from .contrib.orm import models

# 兼容性导出
__all__ = [
    'Request', 'Response', 'Dispatcher', 'expose', 'POST', 'GET',
    'redirect', 'Redirect', 'json', 'request', 'response', 'settings', 'application',
    'UliwebError', 'HTTPError', 'RedirectException', 'Middleware',
    'SimpleFrame', 'dispatch', 'template', 'html', 'js', 'uaml',
    'common', 'date', 'files', 'storage', 'sorteddict',
    'form', 'orm', 'i18n', 'mail', 'ASGI_AVAILABLE',
    'get_apps', 'get_app_dir', 'functions', 'Finder', 'decorators', 'url_for', 'json_dumps',
    'is_in_web', 'error', 'models'
]
