#! /usr/bin/env python
#coding=utf-8
# inspired from http://code.activestate.com/recipes/496741-object-proxying/
import contextvars


class Global(object):
    """全局对象容器类"""
    pass


# 创建全局对象容器，供所有 LocalProxy 实例共享
_globals = Global()


class LocalProxy(object):
    __slots__ = ['_env', '_obj_name', '_use_contextvars', '_var']

    def __init__(self, name, default=None, use_contextvars=False, env=None):
        # 使用传入的环境对象，或者使用默认的 _globals
        object.__setattr__(self, "_env", env if env is not None else _globals)
        object.__setattr__(self, "_obj_name", name)
        object.__setattr__(self, "_use_contextvars", use_contextvars)

        if use_contextvars:
            # 使用 contextvars（支持协程隔离）
            var = contextvars.ContextVar(name, default=default)
            object.__setattr__(self, "_var", var)
        else:
            # 初始化环境中的属性
            # 只有当 default 不是 None 时才设置，避免覆盖已有的值
            _e = self._env
            if not hasattr(_e, name) and default is not None:
                setattr(_e, name, default)
            object.__setattr__(self, "_var", None)

    def __get_instance__(self):
        if self._use_contextvars:
            return self._var.get()
        else:
            return getattr(self._env, self._obj_name, None)

    def _get_instance(self):
        """获取底层实例的公共方法"""
        return self.__get_instance__()

    def __getattr__(self, name):
        # 首先检查 LocalProxy 自身是否有这个属性
        # 这避免了在底层对象上查找 _get_instance 等内部方法
        if name in ('_env', '_obj_name', '_use_contextvars', '_var',
                    '_get_instance', '__get_instance__', 'get_value',
                    'get_var', 'set_var', 'items', 'keys', 'values', 'set'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        instance = self.__get_instance__()
        if instance is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(instance, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self.__get_instance__(), name, value)

    def __delattr__(self, name):
        delattr(self.__get_instance__(), name)

    def __bool__(self):
        return bool(self.__get_instance__())

    def __str__(self):
        return str(self.__get_instance__())

    def __repr__(self):
        return repr(self.__get_instance__())

    def __iter__(self):
        return iter(self.__get_instance__())

    def __len__(self):
        return len(self.__get_instance__())

    def __contains__(self, item):
        return item in self.__get_instance__()

    def __getitem__(self, item):
        return self.__get_instance__()[item]

    def __setitem__(self, item, value):
        self.__get_instance__()[item] = value

    def __delitem__(self, item):
        del self.__get_instance__()[item]

    def get_value(self):
        """获取 underlying 值"""
        return self.__get_instance__()

    def get_var(self, key, default=None):
        instance = self.__get_instance__()
        if instance is None:
            return default
        return getattr(instance, 'get_var', lambda k, d: d)(key, default)

    def set_var(self, key, value):
        return getattr(self.__get_instance__(), 'set_var', lambda k, v: None)(key, value)

    def items(self):
        return getattr(self.__get_instance__(), 'items', lambda: [])()

    def keys(self):
        return getattr(self.__get_instance__(), 'keys', lambda: [])()

    def values(self):
        return getattr(self.__get_instance__(), 'values', lambda: [])()

    def set(self, value):
        """设置值，返回 token（用于 contextvars 场景）"""
        if self._use_contextvars:
            return self._var.set(value)
        else:
            setattr(self._env, self._obj_name, value)
            return None

    def reset(self, token):
        """重置值（用于 contextvars 场景）"""
        if self._use_contextvars:
            self._var.reset(token)
        else:
            # 非 contextvars 模式下不支持 reset
            pass

    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__',
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__',
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__',
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__',
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__',
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__',
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__',
        '__truediv__', '__xor__', 'next',
    ]

    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""

        def make_method(name):
            def method(self, *args, **kw):
                return getattr(self.__get_instance__(), name)(*args, **kw)
            return method

        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __new__(cls, name, default=None, use_contextvars=False, env=None, klass=None):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        if klass is None:
            # 如果没有指定 klass，使用 object 作为默认
            klass = object

        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[klass]
        except KeyError:
            cache[klass] = theclass = cls._create_class_proxy(klass)
        ins = object.__new__(theclass)
        return ins