"""
Uliweb 上下文变量模块
提供统一的 contextvars 支持，用于在异步和同步环境中存储请求相关的全局变量
"""

import contextvars


# 请求上下文变量
request_var = contextvars.ContextVar('request')
response_var = contextvars.ContextVar('response')
settings_var = contextvars.ContextVar('settings')
application_var = contextvars.ContextVar('application')


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


class GlobalSettingsProxy:
    """
    全局 settings 代理类
    只从 contextvars 获取 settings，不再回退到 __global__
    """

    def __init__(self):
        self._var = settings_var

    def _get_instance(self):
        """获取 settings 实例"""
        # 优先从 contextvars 获取
        result = self._var.get(None)
        if result is None:
            # 回退到 __global__，用于线程池等场景
            try:
                from uliweb.core.SimpleFrame import __global__
                result = getattr(__global__, 'settings', None)
            except ImportError:
                pass
        if result is None:
            raise RuntimeError("settings not initialized. Please ensure AsyncDispatcher or Dispatcher has been created.")
        return result

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
        return self._get_instance().get_var(key, default)

    def set_var(self, key, value):
        return self._get_instance().set_var(key, value)

    def items(self):
        return self._get_instance().items()

    def keys(self):
        return self._get_instance().keys()

    def values(self):
        return self._get_instance().values()

    def __getstate__(self):
        return {}

    def __setstate__(self, state):
        pass


class ContextProxy:
    """
    一个简单的代理类，用于将 contextvars 包装成类似普通对象的方式
    """

    def __init__(self, var, default=None):
        self._var = var
        self._default = default

    def _get_instance(self):
        """获取当前 contextvars 中存储的对象"""
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
        return self._get_instance().get_var(key, default)

    def set_var(self, key, value):
        return self._get_instance().set_var(key, value)

    def items(self):
        return self._get_instance().items()

    def keys(self):
        return self._get_instance().keys()

    def values(self):
        return self._get_instance().values()

    def __getstate__(self):
        return {'_var': self._var, '_default': self._default}

    def __setstate__(self, state):
        object.__setattr__(self, '_var', state['_var'])
        object.__setattr__(self, '_default', state['_default'])


# 创建使用 contextvars 的全局代理对象
# 对于 settings，使用特殊的 GlobalSettingsProxy，它会回退到 __global__.settings
settings_proxy = GlobalSettingsProxy()
request_proxy = ContextProxy(request_var, None)
response_proxy = ContextProxy(response_var, None)
application_proxy = ContextProxy(application_var, None)


__all__ = [
    'request_var',
    'response_var',
    'settings_var',
    'application_var',
    'get_request',
    'get_response',
    'get_settings',
    'get_application',
    'ContextProxy',
    'settings_proxy',
    'request_proxy',
    'response_proxy',
    'application_proxy',
]
