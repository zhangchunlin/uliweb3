#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import tempfile
import shutil

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestASGIStaticFiles(unittest.TestCase):
    """测试 ASGI 静态文件中间件"""

    @classmethod
    def setUpClass(cls):
        """创建测试环境

        按照 uliweb 标准目录结构：
        project_dir/
            apps/
                settings.ini
            home/           # app 目录
                __init__.py
                static/      # 静态文件在 app 目录下，不是 apps/home/static
                    ...
            static/         # 项目级静态目录
                ...
        """
        from uliweb import manage
        from uliweb.core.SimpleFrame import get_app_dir, __app_dirs__

        cls.test_dir = tempfile.mkdtemp()
        cls.project_dir = os.path.join(cls.test_dir, 'TestStaticProject')
        os.makedirs(cls.project_dir)

        # 创建 apps 目录和 settings.ini
        apps_dir = os.path.join(cls.project_dir, 'apps')
        os.makedirs(apps_dir)

        # 创建 __init__.py
        with open(os.path.join(apps_dir, '__init__.py'), 'w') as f:
            f.write('')

        # 创建 settings.ini，配置 INSTALLED_APPS 和 STATICFILES
        with open(os.path.join(apps_dir, 'settings.ini'), 'w') as f:
            f.write("""[GLOBAL]
DEBUG = False
DEBUG_CONSOLE = False
DEBUG_TEMPLATE = False

INSTALLED_APPS = [
    'uliweb.contrib.staticfiles',
    'home',
]

[STATICFILES]
STATIC_FOLDER = 'static'

[DOMAINS]
static = {'domain': '', 'display': False, 'url_prefix': ''}
""")

        # 创建 home app 目录（按照 uliweb 标准，app 在项目根目录下）
        home_dir = os.path.join(cls.project_dir, 'home')
        os.makedirs(home_dir)

        # 创建 __init__.py 使其成为 Python 包
        with open(os.path.join(home_dir, '__init__.py'), 'w') as f:
            f.write('')

        # 创建 app 级的静态文件目录（home/static/）
        cls.app_static_dir = os.path.join(home_dir, 'static')
        os.makedirs(cls.app_static_dir)

        # 创建 app 静态文件测试
        cls.app_test_file = os.path.join(cls.app_static_dir, 'app_test.txt')
        with open(cls.app_test_file, 'w') as f:
            f.write('App Hello, World!')

        # 创建项目级静态文件目录
        cls.static_dir = os.path.join(cls.project_dir, 'static')
        os.makedirs(cls.static_dir)

        # 创建项目级测试文件
        cls.test_file = os.path.join(cls.static_dir, 'test.txt')
        with open(cls.test_file, 'w') as f:
            f.write('Hello, World!')

        # 创建子目录和文件
        cls.sub_dir = os.path.join(cls.static_dir, 'sub')
        os.makedirs(cls.sub_dir)
        cls.sub_file = os.path.join(cls.sub_dir, 'nested.txt')
        with open(cls.sub_file, 'w') as f:
            f.write('Nested file')

        # 创建隐藏文件
        cls.hidden_file = os.path.join(cls.static_dir, '.hidden')
        with open(cls.hidden_file, 'w') as f:
            f.write('Hidden file')

        # 切换到项目目录
        cls.old_cwd = os.getcwd()
        os.chdir(cls.project_dir)

        # 注册 home app 的路径，以便 get_app_dir 能找到它
        __app_dirs__['home'] = home_dir

        # 使用 make_application
        cls.app = manage.make_application(
            project_dir=cls.project_dir,
            debug=False,
            debug_console=False,
            start=True,
            reuse=False
        )

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        os.chdir(cls.old_cwd)
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def get_async_client(self):
        """创建异步 HTTP 客户端"""
        import httpx
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://testserver')

    def test_static_file_served(self):
        """测试静态文件正常服务"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/test.txt')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'Hello, World!')

        asyncio.run(run_test())

    def test_static_file_not_found(self):
        """测试静态文件不存在返回 404"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/notexists.txt')
                self.assertEqual(response.status_code, 404)

        asyncio.run(run_test())

    def test_path_traversal_attack(self):
        """测试路径遍历攻击防护"""
        import asyncio

        # 直接创建中间件实例进行测试
        from uliweb.contrib.staticfiles.asgi_staticfiles import ASGIStaticFilesMiddleware
        from starlette.responses import Response

        # 创建一个简单的 app 用于传递
        async def dummy_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 404, "headers": []})
            await send({"type": "http.response.body", "body": b"Not Found"})

        # 创建中间件实例
        middleware = ASGIStaticFilesMiddleware(
            dummy_app,
            STATIC_URL='/static/',
            disallow=None,
            cache=True,
            cache_timeout=60 * 60 * 12
        )

        async def run_test():
            # 模拟 scope - 包含路径遍历的原始请求
            scope = {
                'type': 'http',
                'method': 'GET',
                'path': '/static/../setup.py',
                'raw_path': b'/static/../setup.py',
                'query_string': b'',
                'headers': [(b'host', b'testserver')],
            }

            messages = []
            async def send(msg):
                messages.append(msg)

            # 调用中间件
            await middleware(scope, None, send)

            # 验证返回 403
            start_msg = [m for m in messages if m['type'] == 'http.response.start'][0]
            self.assertEqual(start_msg['status'], 403)

        asyncio.run(run_test())

    def test_encoded_path_traversal(self):
        """测试编码的路径遍历攻击"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/..%2f..%2fsetup.py')
                self.assertEqual(response.status_code, 403)

        asyncio.run(run_test())

    def test_backslash_traversal(self):
        """测试反斜杠路径遍历攻击"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/..%5Csetup.py')
                self.assertEqual(response.status_code, 403)

        asyncio.run(run_test())

    def test_hidden_file_access(self):
        """测试隐藏文件访问（以 . 开头的文件）"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/.hidden')
                self.assertIn(response.status_code, [403, 404])

        asyncio.run(run_test())

    def test_subdirectory_file(self):
        """测试子目录文件访问"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/sub/nested.txt')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'Nested file')

        asyncio.run(run_test())

    def test_cache_header(self):
        """测试缓存头"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                response = await client.get('/static/test.txt')
                self.assertEqual(response.status_code, 200)
                # 检查是否有 Cache-Control 头
                self.assertIn('Cache-Control', response.headers)

        asyncio.run(run_test())

    def test_app_static_file_served(self):
        """测试 app 目录下的静态文件能够正常访问（uliweb 标准结构）"""
        import asyncio

        async def run_test():
            async with self.get_async_client() as client:
                # 访问 app (home) 下的静态文件
                response = await client.get('/static/app_test.txt')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'App Hello, World!')

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
