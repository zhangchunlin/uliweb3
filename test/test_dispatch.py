#coding=utf-8
"""
测试 uliweb.core.dispatch 模块的异步事件调用功能

这个测试文件验证 dispatch 模块的异步调用函数 acall 和 aget
是否正确支持异步事件处理函数。

根据 asgi.md 4.7 节的说明，事件分发系统需要支持异步化。
"""
import os
import sys

# 设置路径
path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, path)


def test_dispatch_acall_and_aget_exist():
    """
    测试 dispatch 模块的异步函数是否存在

    验证 acall 和 aget 异步函数已正确添加到 dispatch 模块。

    >>> from uliweb.core import dispatch

    >>> # 验证 acall 和 aget 存在于 __all__ 中
    >>> 'acall' in dispatch.__all__
    True
    >>> 'aget' in dispatch.__all__
    True

    >>> # 验证 acall 和 aget 是可调用的
    >>> callable(dispatch.acall)
    True
    >>> callable(dispatch.aget)
    True

    >>> # 验证它们是协程函数
    >>> import inspect
    >>> inspect.iscoroutinefunction(dispatch.acall)
    True
    >>> inspect.iscoroutinefunction(dispatch.aget)
    True
    """
    pass


def test_dispatch_async_acall():
    """
    测试异步 acall 函数的基本功能

    验证 acall 能够正确调用同步和异步事件处理函数。

    >>> import asyncio
    >>> from uliweb.core import dispatch

    >>> # 测试同步处理函数
    >>> @dispatch.bind('test_async_acall_sync')
    ... def sync_handler(sender):
    ...     return "sync"

    >>> async def test_sync():
    ...     await dispatch.acall(None, 'test_async_acall_sync')
    ...     dispatch.unbind('test_async_acall_sync', sync_handler)
    ...     return True

    >>> asyncio.run(test_sync())
    True

    >>> # 测试异步处理函数
    >>> @dispatch.bind('test_async_acall_async')
    ... async def async_handler(sender):
    ...     return "async"

    >>> async def test_async():
    ...     await dispatch.acall(None, 'test_async_acall_async')
    ...     dispatch.unbind('test_async_acall_async', async_handler)
    ...     return True

    >>> asyncio.run(test_async())
    True

    >>> # 测试混合同步和异步处理函数
    >>> @dispatch.bind('test_async_acall_mixed')
    ... def sync_handler2(sender):
    ...     return "sync"

    >>> @dispatch.bind('test_async_acall_mixed')
    ... async def async_handler2(sender):
    ...     return "async"

    >>> async def test_mixed():
    ...     await dispatch.acall(None, 'test_async_acall_mixed')
    ...     dispatch.unbind('test_async_acall_mixed', sync_handler2)
    ...     dispatch.unbind('test_async_acall_mixed', async_handler2)
    ...     return True

    >>> asyncio.run(test_mixed())
    True

    >>> # 测试不存在的 topic
    >>> async def test_nonexistent():
    ...     # 不应该抛出异常
    ...     await dispatch.acall(None, 'nonexistent_topic')
    ...     return True

    >>> asyncio.run(test_nonexistent())
    True
    """
    pass


def test_dispatch_async_aget():
    """
    测试异步 aget 函数的基本功能

    验证 aget 能够正确调用事件处理函数并在第一个非 None 返回值时停止。

    >>> import asyncio
    >>> from uliweb.core import dispatch

    >>> # 测试获取返回值
    >>> @dispatch.bind('test_async_aget_return')
    ... async def handler_with_return(sender):
    ...     return "返回值"

    >>> async def test_return():
    ...     result = await dispatch.aget(None, 'test_async_aget_return')
    ...     dispatch.unbind('test_async_aget_return', handler_with_return)
    ...     return result == "返回值"

    >>> asyncio.run(test_return())
    True

    >>> # 测试第一个非 None 返回值会停止调用后续处理函数
    >>> call_count = 0

    >>> @dispatch.bind('test_async_aget_stop')
    ... async def first_handler(sender):
    ...     global call_count
    ...     call_count += 1
    ...     return "第一个"

    >>> @dispatch.bind('test_async_aget_stop')
    ... async def second_handler(sender):
    ...     global call_count
    ...     call_count += 1
    ...     return "第二个"

    >>> async def test_stop():
    ...     global call_count
    ...     call_count = 0
    ...     result = await dispatch.aget(None, 'test_async_aget_stop')
    ...     dispatch.unbind('test_async_aget_stop', first_handler)
    ...     dispatch.unbind('test_async_aget_stop', second_handler)
    ...     # 第一个处理函数返回非 None 值，后续处理函数不应被调用
    ...     return result == "第一个" and call_count == 1

    >>> asyncio.run(test_stop())
    True

    >>> # 测试所有处理函数都返回 None
    >>> @dispatch.bind('test_async_aget_none')
    ... async def handler_return_none(sender):
    ...     return None

    >>> async def test_none():
    ...     result = await dispatch.aget(None, 'test_async_aget_none')
    ...     dispatch.unbind('test_async_aget_none', handler_return_none)
    ...     return result is None

    >>> asyncio.run(test_none())
    True
    """
    pass


def test_dispatch_async_with_anyio():
    """
    测试 acall 和 aget 使用 anyio 线程池运行同步函数

    验证同步处理函数在异步环境中能正确在线程池中运行。

    >>> import asyncio
    >>> import threading
    >>> from uliweb.core import dispatch

    >>> # 测试同步函数在正确的线程中运行
    >>> thread_ids = []

    >>> @dispatch.bind('test_async_thread')
    ... def sync_in_thread(sender):
    ...     thread_ids.append(threading.current_thread().ident)
    ...     return None

    >>> async def test_thread():
    ...     thread_ids.clear()
    ...     main_thread = threading.current_thread().ident
    ...     await dispatch.acall(None, 'test_async_thread')
    ...     dispatch.unbind('test_async_thread', sync_in_thread)
    ...     # 同步函数应该在线程池中运行，而不是在主线程
    ...     return thread_ids[0] != main_thread if thread_ids else False

    >>> asyncio.run(test_thread())
    True
    """
    pass


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
