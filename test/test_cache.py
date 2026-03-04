import time, sys, os
path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, path)
from uliweb import manage, functions

cdir = None


def setup():
    global cdir
    cdir = os.getcwd()


def teardown():
    import shutil
    if cdir:
        os.chdir(cdir)
    if os.path.exists('TestProject'):
        shutil.rmtree('TestProject', ignore_errors=True)


def test_file():
    """
    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> cache = functions.get_cache()
    >>> cache.get('name', None)
    >>> def set_name():
    ...     return 'test'
    >>> cache.get('name', creator=set_name)
    'test'
    >>> cache.get('name')
    'test'
    >>> cache.get('hello', 'default')
    'default'
    >>> cache['test'] = 'ooo'
    >>> cache['test']
    'ooo'
    >>> del cache['test']
    >>> cache.setdefault('a', set_name)
    'test'
    >>> cache['a']
    'test'
    >>> cache.inc('count')
    1
    >>> cache.dec('count')
    0
    >>> cache.inc('count')
    1
    >>> cache.get('count')
    1
    >>> cache.set('count', 2)
    True
    >>> cache.inc('count', 2)
    4
    >>> teardown()
    """

def test_redis():
    """
    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> cache = functions.get_cache(storage_type='redis', options={'connection_pool':{'host':'localhost', 'port':6379}})
    >>> cache.get('name', None)
    >>> def set_name():
    ...     return 'test'
    >>> cache.get('name', creator=set_name)
    'test'
    >>> cache.get('name')
    'test'
    >>> cache.get('hello', 'default')
    'default'
    >>> cache['test'] = 'ooo'
    >>> cache['test']
    'ooo'
    >>> del cache['test']
    >>> cache.setdefault('a', set_name)
    'test'
    >>> cache['a']
    'test'
    >>> cache.inc('count')
    1
    >>> cache.dec('count')
    0
    >>> cache.inc('count')
    1
    >>> cache.get('count')
    1
    >>> cache.set('count', 2)
    True
    >>> cache.inc('count', 2)
    4
    >>> cache.set('a', 1.0)
    True
    >>> cache.get('a')
    1.0
    >>> cache.delete('name')
    True
    >>> cache.delete('count')
    True
    >>> cache.delete('a')
    True
    >>> teardown()
    """

def test_async_cache_file():
    """
    Test async cache methods for file storage.

    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> import asyncio
    >>>
    >>> async def test_async_cache():
    ...     cache = functions.get_cache()
    ...
    ...     # Test async get - aget
    ...     result = await cache.aget('async_name', 'default')
    ...     assert result == 'default', f"Expected 'default', got {result}"
    ...
    ...     # Test async set - aset
    ...     await cache.aset('async_name', 'test_value')
    ...     result = await cache.aget('async_name')
    ...     assert result == 'test_value', f"Expected 'test_value', got {result}"
    ...
    ...     # Test async get with creator
    ...     def set_name():
    ...         return 'creator_value'
    ...     result = await cache.aget('async_creator', creator=set_name)
    ...     assert result == 'creator_value', f"Expected 'creator_value', got {result}"
    ...
    ...     # Test aget after creator sets value
    ...     result = await cache.aget('async_creator')
    ...     assert result == 'creator_value', f"Expected 'creator_value', got {result}"
    ...
    ...     # Test async delete - adelete
    ...     await cache.adelete('async_name')
    ...     result = await cache.aget('async_name', 'deleted')
    ...     assert result == 'deleted', f"Expected 'deleted', got {result}"
    ...
    ...     # Test async increment - ainc
    ...     await cache.aset('async_count', 10)
    ...     result = await cache.ainc('async_count')
    ...     assert result == 11, f"Expected 11, got {result}"
    ...     result = await cache.ainc('async_count', 2)
    ...     assert result == 13, f"Expected 13, got {result}"
    ...
    ...     # Test async decrement - adec
    ...     # file storage dec uses min(0, value-step), so won't go below 0
    ...     result = await cache.adec('async_count')
    ...     assert result == 12, f"Expected 12, got {result}"
    ...     result = await cache.adec('async_count', 10)
    ...     # 12 - 10 = 2, but min(0, 2) = 2 (no negative yet)
    ...     assert result == 2, f"Expected 2, got {result}"
    ...     # Try to decrement below zero
    ...     result = await cache.adec('async_count', 5)
    ...     # 2 - 5 = -3, but min(0, -3) = 0
    ...     assert result == 0, f"Expected 0 (capped), got {result}"
    ...
    ...     # Test acache decorator
    ...     call_count = [0]
    ...
    ...     @cache.acache('async_test_key', expire=300)
    ...     async def expensive_operation():
    ...         call_count[0] += 1
    ...         return 'computed_value'
    ...
    ...     # First call - should compute
    ...     result = await expensive_operation()
    ...     assert result == 'computed_value', f"Expected 'computed_value', got {result}"
    ...     assert call_count[0] == 1, f"Expected call_count 1, got {call_count[0]}"
    ...
    ...     # Second call - should use cache
    ...     result = await expensive_operation()
    ...     assert result == 'computed_value', f"Expected 'computed_value', got {result}"
    ...     assert call_count[0] == 1, f"Expected call_count 1 (cached), got {call_count[0]}"
    ...
    ...     # Delete the cache and call again
    ...     await cache.adelete('async_test_key')
    ...     result = await expensive_operation()
    ...     assert result == 'computed_value', f"Expected 'computed_value', got {result}"
    ...     assert call_count[0] == 2, f"Expected call_count 2, got {call_count[0]}"
    ...
    ...     return True
    ...
    >>> result = asyncio.run(test_async_cache())
    >>> assert result == True
    >>> teardown()
    """

def test_async_cache_methods_exist():
    """
    Test that async cache methods exist on Cache instance.

    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> cache = functions.get_cache()
    >>>
    >>> # Check async methods exist
    >>> assert hasattr(cache, 'aget'), "Cache should have 'aget' method"
    >>> assert hasattr(cache, 'aset'), "Cache should have 'aset' method"
    >>> assert hasattr(cache, 'adelete'), "Cache should have 'adelete' method"
    >>> assert hasattr(cache, 'ainc'), "Cache should have 'ainc' method"
    >>> assert hasattr(cache, 'adec'), "Cache should have 'adec' method"
    >>> assert hasattr(cache, 'acache'), "Cache should have 'acache' method"
    >>>
    >>> # Check they are callable
    >>> assert callable(cache.aget), "'aget' should be callable"
    >>> assert callable(cache.aset), "'aset' should be callable"
    >>> assert callable(cache.adelete), "'adelete' should be callable"
    >>> assert callable(cache.ainc), "'ainc' should be callable"
    >>> assert callable(cache.adec), "'adec' should be callable"
    >>> assert callable(cache.acache), "'acache' should be callable"
    >>>
    >>> teardown()
    """

def test_get_async_cache():
    """
    Test get_async_cache function returns cache with async methods.

    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> from uliweb.contrib.cache import get_async_cache
    >>>
    >>> cache = get_async_cache()
    >>>
    >>> # Check it's a Cache instance
    >>> from uliweb.lib.weto.cache import Cache
    >>> assert isinstance(cache, Cache), "get_async_cache should return Cache instance"
    >>>
    >>> # Check async methods exist
    >>> assert hasattr(cache, 'aget')
    >>> assert hasattr(cache, 'aset')
    >>> assert hasattr(cache, 'adelete')
    >>>
    >>> teardown()
    """

def test_async_cache_with_expire():
    """
    Test async cache methods with expire parameter.

    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> import asyncio
    >>>
    >>> async def test_expire():
    ...     cache = functions.get_cache()
    ...
    ...     # Set with short expire time
    ...     await cache.aset('expire_key', 'expire_value', expire=1)
    ...
    ...     # Should exist immediately
    ...     result = await cache.aget('expire_key')
    ...     assert result == 'expire_value', f"Expected 'expire_value', got {result}"
    ...
    ...     return True
    ...
    >>> result = asyncio.run(test_expire())
    >>> assert result == True
    >>> teardown()
    """

def test_async_cache_set_with_callable():
    """
    Test async cache aset method with callable value.

    >>> manage.call('uliweb makeproject -y TestProject')
    >>> os.chdir('TestProject')
    >>> path = os.getcwd()
    >>> app = manage.make_simple_application(project_dir=path, include_apps=['uliweb.contrib.cache'])
    >>> import asyncio
    >>>
    >>> async def test_callable():
    ...     cache = functions.get_cache()
    ...
    ...     # Set with callable value
    ...     def compute_value():
    ...         return 'computed'
    ...
    ...     await cache.aset('callable_key', compute_value)
    ...     result = await cache.aget('callable_key')
    ...     assert result == 'computed', f"Expected 'computed', got {result}"
    ...
    ...     return True
    ...
    >>> result = asyncio.run(test_callable())
    >>> assert result == True
    >>> teardown()
    """
