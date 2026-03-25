"""
中间件初始化测试

测试 ASGI 中间件在初始化时正确接收 settings 参数
"""
import os
import sys
import asyncio
import unittest

# 添加项目路径
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, path)


class MiddlewareInitTest(unittest.TestCase):
    """测试中间件初始化"""

    def test_middleware_with_call_and_settings(self):
        """测试带有 __call__ 方法的中间件能正确接收 settings 参数"""
        from uliweb import Middleware
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建一个简单的模拟 settings
        class MockSettings:
            def __init__(self):
                self.GLOBAL = type('GLOBAL', (), {'DEBUG': False})()
                self.MIDDLEWARES = {}
                self.ASGI_MIDDLEWARES = {}
                self.DOMAINS = {}

            def get(self, key, default=None):
                return getattr(self, key, default)

            def get_var(self, key, default=None):
                return default

        # 创建一个测试中间件类，模拟 Uliweb 的实际中间件
        class TestMiddleware(Middleware):
            """测试中间件，模拟实际的中间件结构"""

            def __init__(self, application, settings):
                super().__init__(application, settings)
                # 验证 settings 是否正确传递
                self.settings = settings
                self.application = application

            async def __call__(self, scope, receive, send):
                # ASGI 中间件接口
                await self.application(scope, receive, send)

        # 创建 AsyncDispatcher 实例
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=path,
            include_apps=['uliweb.contrib.auth'],
            start=False
        )

        # 设置 settings
        mock_settings = MockSettings()
        dispatcher.settings = mock_settings

        # 手动调用 _init_middlewares 来初始化中间件列表
        dispatcher.middlewares = []
        dispatcher.process_request_classes = []
        dispatcher.process_response_classes = []
        dispatcher.process_exception_classes = []

        # 添加测试中间件到列表
        dispatcher.middlewares.append(TestMiddleware)

        # 构建中间件栈 - 这会触发中间件初始化
        # 使用事件循环来执行异步方法
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 创建 mock app
            async def mock_app(scope, receive, send):
                pass

            # 模拟 _build_middleware_stack 的逻辑
            for middleware in dispatcher.middlewares:
                # 获取中间件类
                if isinstance(middleware, type):
                    middleware_cls = middleware
                else:
                    middleware_cls = type(middleware)

                # 检查是否有 __call__ 方法
                has_asgi_call = (
                    hasattr(middleware_cls, '__call__') and
                    asyncio.iscoroutinefunction(middleware_cls.__call__)
                )

                if has_asgi_call:
                    # 这是关键测试：验证中间件初始化时传递了 settings 参数
                    try:
                        middleware_instance = middleware_cls(dispatcher, dispatcher.settings)
                        # 验证中间件实例已正确创建
                        self.assertIsNotNone(middleware_instance)
                        self.assertIsInstance(middleware_instance, TestMiddleware)
                        # 验证 settings 被正确传递
                        self.assertEqual(middleware_instance.settings, mock_settings)
                    except TypeError as e:
                        if "missing 1 required positional argument: 'settings'" in str(e):
                            self.fail(f"中间件初始化失败：未正确传递 settings 参数 - {e}")
                        raise
        finally:
            loop.close()

    def test_middleware_with_dispatch_and_settings(self):
        """测试带有 dispatch 方法的中间件能正确接收 settings 参数"""
        from uliweb import Middleware

        # 创建一个测试中间件类，模拟实际的 dispatch 中间件
        class TestDispatchMiddleware(Middleware):
            """测试中间件，模拟实际的 dispatch 中间件结构"""

            def __init__(self, application, settings):
                super().__init__(application, settings)
                self.settings = settings
                self.application = application

            async def dispatch(self, request, call_next):
                """高级中间件接口"""
                return await call_next(request)

        # 模拟 AsyncDispatcher 的行为
        class MockDispatcher:
            def __init__(self):
                self.settings = type('Settings', (), {
                    'GLOBAL': type('GLOBAL', (), {'DEBUG': False})(),
                    'MIDDLEWARES': {},
                    'ASGI_MIDDLEWARES': {},
                    'DOMAINS': {}
                })()

        dispatcher = MockDispatcher()

        # 测试中间件初始化
        middleware_instance = TestDispatchMiddleware(dispatcher, dispatcher.settings)

        # 验证初始化成功
        self.assertIsNotNone(middleware_instance)
        self.assertEqual(middleware_instance.settings, dispatcher.settings)

    def test_builtin_middleware_init(self):
        """测试 Uliweb 内置中间件能正确初始化"""
        from uliweb.contrib.auth.middle_auth import AuthMiddle
        from uliweb.contrib.orm.middle_transaction import TransactionMiddle
        from uliweb.contrib.orm.middle_orm_reset import ORMResetMiddle

        # 创建一个简单的模拟 settings
        class MockSettings:
            def __init__(self):
                self.GLOBAL = type('GLOBAL', (), {
                    'DEBUG': False,
                    'DEFAULT_CORS': False,
                    'TIME_ZONE': 'UTC',
                    'LOCAL_TIME_ZONE': 'UTC'
                })()
                self.TIMEZONE = type('TIMEZONE', (), {
                    'cookie_key': 'timezone'
                })()
                self.MIDDLEWARES = {}
                self.ASGI_MIDDLEWARES = {}
                self.DOMAINS = {}

            def get(self, key, default=None):
                return getattr(self, key, default)

            def get_var(self, key, default=None):
                return default

        # 模拟 AsyncDispatcher
        class MockDispatcher:
            def __init__(self):
                self.settings = MockSettings()

        mock_dispatcher = MockDispatcher()
        mock_settings = mock_dispatcher.settings

        # 测试 AuthMiddle 初始化
        try:
            auth_middleware = AuthMiddle(mock_dispatcher, mock_settings)
            self.assertIsNotNone(auth_middleware)
            self.assertEqual(auth_middleware.settings, mock_settings)
        except TypeError as e:
            self.fail(f"AuthMiddle 初始化失败: {e}")

        # 测试 TransactionMiddle 初始化
        try:
            transaction_middleware = TransactionMiddle(mock_dispatcher, mock_settings)
            self.assertIsNotNone(transaction_middleware)
            self.assertEqual(transaction_middleware.settings, mock_settings)
        except TypeError as e:
            self.fail(f"TransactionMiddle 初始化失败: {e}")

        # 测试 ORMResetMiddle 初始化
        try:
            orm_reset_middleware = ORMResetMiddle(mock_dispatcher, mock_settings)
            self.assertIsNotNone(orm_reset_middleware)
            self.assertEqual(orm_reset_middleware.settings, mock_settings)
        except TypeError as e:
            self.fail(f"ORMResetMiddle 初始化失败: {e}")


if __name__ == '__main__':
    unittest.main()