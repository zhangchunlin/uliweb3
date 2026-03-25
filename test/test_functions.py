"""
测试 functions 模块和 Finder 类

注意：这些测试需要使用 AsyncDispatcher 来初始化 settings
"""
import os
import sys

# 添加项目路径
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, path)

# 初始化 AsyncDispatcher 来加载 settings
from uliweb.core.SimpleFrame import AsyncDispatcher

# 创建 AsyncDispatcher 实例来初始化 settings
dispatcher = AsyncDispatcher(
    apps_dir='apps',
    project_dir=path,
    include_apps=['uliweb.contrib.staticfiles'],
    start=False
)

# 现在可以导入 settings 和 functions，它们已经被正确初始化
from uliweb import functions, settings
from uliweb.core.SimpleFrame import Finder


def test_finder_creation():
    """
    测试 Finder 类的创建
    >>> f = Finder('FUNCTIONS')
    >>> f._Finder__section
    'FUNCTIONS'
    """


def test_finder_contains():
    """
    测试 Finder 的 __contains__ 方法
    >>> f = Finder('FUNCTIONS')
    >>> 'set_var' in f
    True
    >>> 'nonexistent_function' in f
    False
    """


def test_finder_getattr():
    """
    测试 Finder 的 __getattr__ 方法
    >>> f = Finder('FUNCTIONS')
    >>> func = f.set_var
    >>> callable(func)
    True
    """


def test_finder_getattr_error():
    """
    测试 Finder 访问不存在的函数时抛出 AttributeError
    >>> f = Finder('FUNCTIONS')
    >>> try:
    ...     f.nonexistent_function
    ... except AttributeError as e:
    ...     "object has no attribute" in str(e)
    True
    """


def test_finder_setitem():
    """
    测试 Finder 的 __setitem__ 方法
    >>> f = Finder('FUNCTIONS')
    >>> def test_func():
    ...     return "test"
    >>> f['custom_func'] = test_func
    >>> f.custom_func()
    'test'
    """


def test_finder_setitem_string():
    """
    测试 Finder 的 __setitem__ 方法（字符串形式）
    >>> f = Finder('FUNCTIONS')
    >>> f['string_func'] = 'uliweb.core.SimpleFrame.set_var'
    >>> callable(f.string_func)
    True
    """


def test_functions_global_object():
    """
    测试全局 functions 对象
    >>> from uliweb import functions
    >>> 'set_var' in functions
    True
    >>> 'get_var' in functions
    True
    """


def test_functions_call():
    """
    测试通过 functions 调用函数
    >>> from uliweb import functions
    >>> func = functions.get_var
    >>> callable(func)
    True
    """


def test_functions_caching():
    """
    测试 functions 的缓存机制
    >>> from uliweb import functions
    >>> func1 = functions.set_var
    >>> func2 = functions.set_var
    >>> func1 is func2
    True
    """


def test_decorators_object():
    """
    测试全局 decorators 对象
    >>> from uliweb.core.SimpleFrame import decorators
    >>> type(decorators).__name__
    'Finder'
    """


def test_function_helper():
    """
    测试 function() 辅助函数
    >>> from uliweb.core.SimpleFrame import function
    >>> func = function('get_var')
    >>> callable(func)
    True
    """


def test_function_helper_with_args():
    """
    测试 function() 辅助函数带参数调用
    >>> from uliweb.core.SimpleFrame import function
    >>> # 获取不存在的函数应抛出异常
    >>> try:
    ...     function('nonexistent_var', 'default_value')
    ... except Exception as e:
    ...     str(e)
    "Can't find the function [nonexistent_var] in settings"
    """


def test_finder_in_settings():
    """
    测试 Finder 与 settings 的集成
    >>> f = Finder('FUNCTIONS')
    >>> 'set_var' in f
    True
    """
