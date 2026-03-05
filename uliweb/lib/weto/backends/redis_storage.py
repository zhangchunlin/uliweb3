from .base import BaseStorage, KeyError
import redis
from redis import asyncio as aioredis
from uliweb.utils._compat import integer_types

# Connection pool format should be: (options, connection object)
__connection_pool__ = None
__async_connection_pool__ = None


class Storage(BaseStorage):
    """
    Redis storage that supports both sync and async operations.
    Uses redis-py for sync and aioredis for async operations.
    """

    def __init__(self, cache_manager, options):
        """
        options =
            unix_socket_path = '/tmp/redis.sock'
            or
            connection_pool = {'host':'localhost', 'port':6379, 'db':0}
        """
        BaseStorage.__init__(self, cache_manager, options)
        self._sync_client = None
        self._async_client = None

    def _get_sync_client(self):
        """Get or create sync Redis client"""
        if self._sync_client is None:
            options = self.options
            if 'unix_socket_path' in options:
                self._sync_client = redis.Redis(
                    unix_socket_path=options['unix_socket_path']
                )
            else:
                global __connection_pool__

                if not __connection_pool__ or __connection_pool__[0] != options['connection_pool']:
                    d = {'host': 'localhost', 'port': 6379}
                    d.update(options['connection_pool'])
                    __connection_pool__ = (d, redis.ConnectionPool(**d))
                self._sync_client = redis.Redis(
                    connection_pool=__connection_pool__[1]
                )
        return self._sync_client

    async def _get_async_client(self):
        """Get or create async Redis client"""
        if self._async_client is None:
            options = self.options
            if 'unix_socket_path' in options:
                self._async_client = aioredis.Redis(
                    unix_socket_path=options['unix_socket_path']
                )
            else:
                global __async_connection_pool__

                if not __async_connection_pool__ or __async_connection_pool__[0] != options['connection_pool']:
                    d = {'host': 'localhost', 'port': 6379}
                    d.update(options['connection_pool'])
                    __async_connection_pool__ = (d, aioredis.ConnectionPool(**d))
                self._async_client = aioredis.Redis(
                    connection_pool=__async_connection_pool__[1]
                )
        return self._async_client

    # ============= Synchronous Methods =============

    def get(self, key):
        """Get value from Redis (sync)"""
        client = self._get_sync_client()
        v = client.get(key)
        if v is not None:
            if not v.isdigit():
                return self._load(v)
            else:
                return int(v)
        else:
            raise KeyError("Cache key [%s] not found" % key)

    def set(self, key, value, expiry_time):
        """Set value to Redis (sync)"""
        if not isinstance(value, integer_types):
            v = self._dump(value)
        else:
            v = value
        client = self._get_sync_client()
        r = client.setex(name=key, value=v, time=expiry_time)
        return r

    def delete(self, key):
        """Delete key from Redis (sync)"""
        client = self._get_sync_client()
        client.delete(key)
        return True

    def inc(self, key, step, expiry_time):
        """Increment value (sync)"""
        client = self._get_sync_client()
        pipe = client.pipeline()
        r = pipe.incr(key, step).expire(key, expiry_time).execute()
        return r[0]

    def dec(self, key, step, expiry_time):
        """Decrement value (sync)"""
        client = self._get_sync_client()
        pipe = client.pipeline()
        r = pipe.decr(key, step).expire(key, expiry_time).execute()
        return r[0]

    # ============= Asynchronous Methods =============

    async def aget(self, key):
        """Async get value from Redis"""
        client = await self._get_async_client()
        v = await client.get(key)
        if v is not None:
            if not v.isdigit():
                return self._load(v)
            else:
                return int(v)
        else:
            raise KeyError("Cache key [%s] not found" % key)

    async def aset(self, key, value, expiry_time):
        """Async set value to Redis"""
        if not isinstance(value, integer_types):
            v = self._dump(value)
        else:
            v = value
        client = await self._get_async_client()
        r = await client.setex(name=key, value=v, time=expiry_time)
        return r

    async def adelete(self, key):
        """Async delete key from Redis"""
        client = await self._get_async_client()
        await client.delete(key)
        return True

    async def ainc(self, key, step, expiry_time):
        """Async increment value"""
        client = await self._get_async_client()
        pipe = client.pipeline()
        r = await pipe.incr(key, step).expire(key, expiry_time).execute()
        return r[0]

    async def adec(self, key, step, expiry_time):
        """Async decrement value"""
        client = await self._get_async_client()
        pipe = client.pipeline()
        r = await pipe.decr(key, step).expire(key, expiry_time).execute()
        return r[0]

    async def close(self):
        """Close async connection"""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
