"""
Uliweb 上下文变量模块

根据 asgi.md 文档的设计方案：
- settings 和 application 使用普通全局变量（整个应用生命周期内保持一致）
- request 和 response 使用 contextvars（每个协程独立隔离）

使用新的 LocalProxy 实现（来自 uliweb/utils/localproxy.py）
"""

from uliweb.utils.localproxy import LocalProxy

# request 和 response 使用 contextvars（每个协程独立隔离）
import contextvars
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')

# settings 和 application 使用普通全局变量
# 定义为 LocalProxy，use_contextvars=False 表示使用 __global__ 获取值
# 这样可以在不同模块间共享
settings_var = LocalProxy('settings', use_contextvars=False)
application_var = LocalProxy('application', use_contextvars=False)


def get_request():
    """获取当前请求对象"""
    return request_var.get(None)


def get_response():
    """获取当前响应对象"""
    return response_var.get(None)


def get_settings():
    """获取当前设置对象"""
    return settings_var.get_value()


def get_application():
    """获取当前应用对象"""
    # 直接从 SimpleFrame 导入 application，确保使用同一个 Global 对象
    from uliweb.core.SimpleFrame import application
    return application.get_value()


# 创建全局代理对象
# settings 和 application 使用 LocalProxy（普通全局变量）
settings_proxy = settings_var
application_proxy = application_var

# request 和 response 使用 contextvars 包装
class _ContextProxy:
    """request/response 代理类，使用 contextvars"""

    def __init__(self, var, default=None):
        self._var = var
        self._default = default

    def _get_instance(self):
        return self._var.get(self._default)

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get_instance(), name, value)

    def __delattr__(self, name):
        delattr(self._get_instance(), name)

    def __bool__(self):
        return bool(self._get_instance())

    def __str__(self):
        return str(self._get_instance())

    def __repr__(self):
        return repr(self._get_instance())

    def __iter__(self):
        return iter(self._get_instance())

    def __len__(self):
        return len(self._get_instance())

    def __contains__(self, item):
        return item in self._get_instance()

    def __getitem__(self, item):
        return self._get_instance()[item]

    def __setitem__(self, item, value):
        self._get_instance()[item] = value

    def __delitem__(self, item):
        del self._get_instance()[item]

    def get(self, key, default=None):
        return self._get_instance().get(key, default)

    def get_var(self, key, default=None):
        return getattr(self._get_instance(), 'get_var', lambda k, d: d)(key, default)

    def set_var(self, key, value):
        return getattr(self._get_instance(), 'set_var', lambda k, v: None)(key, value)

    def items(self):
        return getattr(self._get_instance(), 'items', lambda: [])()

    def keys(self):
        return getattr(self._get_instance(), 'keys', lambda: [])()

    def values(self):
        return getattr(self._get_instance(), 'values', lambda: [])()


request_proxy = _ContextProxy(request_var, None)
response_proxy = _ContextProxy(response_var, None)


__all__ = [
    'request_var',
    'response_var',
    'settings_var',
    'application_var',
    'get_request',
    'get_response',
    'get_settings',
    'get_application',
    'settings_proxy',
    'request_proxy',
    'response_proxy',
    'application_proxy',
]
