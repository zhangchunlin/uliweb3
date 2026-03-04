#coding=utf-8
"""
测试 uliweb.contrib.orm.middle_transaction 模块的异步 dispatch 接口

这个测试文件验证事务中间件是否正确使用 ASGI 的 dispatch 接口
来替代旧的同步 process_request/process_response/process_exception 接口。
"""
import os
import sys
from uliweb.utils._compat import text_type

# 设置路径
path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, path)

# 导入必要的模块
from uliweb.orm import *
import uliweb.orm
uliweb.orm.__auto_create__ = True
uliweb.orm.__nullable__ = True
uliweb.orm.__server_default__ = False


def test_transaction_middleware_dispatch():
    """
    测试事务中间件的异步 dispatch 接口

    验证 middle_transaction.TransactionMiddle 使用异步 dispatch 方法
    而不是旧的同步 process_request/process_response/process_exception 方法。

    >>> from uliweb.contrib.orm.middle_transaction import TransactionMiddle
    >>> from uliweb import Middleware

    >>> # 验证 TransactionMiddle 是 Middleware 的子类
    >>> issubclass(TransactionMiddle, Middleware)
    True

    >>> # 验证存在 dispatch 方法
    >>> middleware = TransactionMiddle(None, {})
    >>> hasattr(middleware, 'dispatch')
    True

    >>> # 验证 dispatch 是异步方法
    >>> import inspect
    >>> inspect.iscoroutinefunction(middleware.dispatch)
    True

    >>> # 验证旧的同步方法不存在（已废弃）
    >>> hasattr(middleware, 'process_request')
    False
    >>> hasattr(middleware, 'process_response')
    False
    >>> hasattr(middleware, 'process_exception')
    False
    """
    pass


def test_transaction_middleware_async_functionality():
    """
    测试事务中间件的异步功能

    验证异步 dispatch 方法能正确处理正常请求和异常情况。

    >>> import asyncio
    >>> from unittest.mock import Mock, AsyncMock
    >>> from uliweb.contrib.orm.middle_transaction import TransactionMiddle
    >>> from uliweb.orm import get_connection

    >>> # 创建内存数据库
    >>> db = get_connection('sqlite://')
    >>> db.metadata.drop_all()

    >>> # 测试正常提交流程
    >>> async def test_normal_commit():
    ...     middleware = TransactionMiddle(None, {})
    ...
    ...     # 模拟 call_next 返回正常响应
    ...     mock_response = Mock()
    ...     mock_response.post_commit = False
    ...
    ...     async def mock_call_next(request):
    ...         return mock_response
    ...
    ...     result = await middleware.dispatch({}, mock_call_next)
    ...     return result is mock_response

    >>> # 测试异常回滚流程
    >>> async def test_exception_rollback():
    ...     middleware = TransactionMiddle(None, {})
    ...
    ...     # 模拟 call_next 抛出异常
    ...     async def mock_call_next_with_exception(request):
    ...         raise ValueError("Test exception")
    ...
    ...     try:
    ...         await middleware.dispatch({}, mock_call_next_with_exception)
    ...     except ValueError:
    ...         return True
    ...     return False

    >>> # 执行测试
    >>> asyncio.run(test_normal_commit())
    True
    >>> asyncio.run(test_exception_rollback())
    True
    """
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
