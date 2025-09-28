"""
Uliweb - Easy Python Web Framework
"""

__version__ = '3.0.0'
__author__ = 'Limodou'
__author_email__ = 'limodou@gmail.com'
__url__ = 'https://github.com/limodou/uliweb3'
__license__ = 'BSD'


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


# 标记 ASGI 可用性
ASGI_AVAILABLE = False

# 导入管理命令需要的函数（避免循环导入）
from .core.SimpleFrame import get_apps, get_app_dir

# 尝试导入 ASGI 组件
try:
    from .core.starlette import (
        Request as ASGIRequest,
        Response as ASGIResponse,
        AsyncDispatcher,
        expose as asgi_expose,
        POST as asgi_POST,
        GET as asgi_GET,
        redirect as asgi_redirect,
        json as asgi_json,
        request as asgi_request,
        response as asgi_response,
        settings as asgi_settings,
        application as asgi_application
    )

    # 如果导入成功，标记 ASGI 可用
    ASGI_AVAILABLE = True

    # 使用 ASGI 组件
    Request = ASGIRequest
    Response = ASGIResponse
    expose = asgi_expose
    POST = asgi_POST
    GET = asgi_GET
    redirect = asgi_redirect
    json = asgi_json
    request = asgi_request
    response = asgi_response
    settings = asgi_settings
    application = asgi_application
    Dispatcher = AsyncDispatcher

except ImportError:
    # 如果 Starlette 不可用，回退到 WSGI
    from .core.SimpleFrame import (
        Request as WSGIRequest,
        Response as WsgiResponse,
        expose as wsgi_expose,
        POST as wsgi_POST,
        GET as wsgi_GET,
        redirect as wsgi_redirect,
        json as wsgi_json,
        request as wsgi_request,
        response as wsgi_response,
        settings as wsgi_settings,
        application as wsgi_application,
        Dispatcher as WSGIDispatcher
    )

    Request = WSGIRequest
    Response = WsgiResponse
    expose = wsgi_expose
    POST = wsgi_POST
    GET = wsgi_GET
    redirect = wsgi_redirect
    json = wsgi_json
    request = wsgi_request
    response = wsgi_response
    settings = wsgi_settings
    application = wsgi_application
    Dispatcher = WSGIDispatcher

# 兼容性导出
__all__ = [
    'Request', 'Response', 'Dispatcher', 'expose', 'POST', 'GET',
    'redirect', 'json', 'request', 'response', 'settings', 'application',
    'UliwebError', 'HTTPError', 'RedirectException',
    'SimpleFrame', 'dispatch', 'template', 'html', 'js', 'uaml',
    'common', 'date', 'files', 'storage', 'sorteddict',
    'form', 'orm', 'i18n', 'mail', 'ASGI_AVAILABLE',
    'get_apps', 'get_app_dir'  # 添加缺失的函数
]
