"""
Uliweb ASGI 测试服务器模块

提供在单元测试中启动真实 ASGI 服务器的功能，
用于测试静态文件、文件上传下载、WebSocket 等需要真实网络环境的场景。

依赖：
    - uvicorn
    - httpx (推荐用于异步测试)
    - requests (可选，用于同步测试)

用法示例：

```python
import unittest
from uliweb.utils.test_server import TestServer
import httpx

class TestStaticFiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = TestServer(
            project_dir='/path/to/project',
            apps_dir='apps'
        )
        cls.server.start()
        cls.base_url = cls.server.base_url

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_static_file(self):
        # 使用真实的 HTTP 请求测试
        response = httpx.get(f'{self.base_url}/static/test.txt')
        self.assertEqual(response.status_code, 200)
```

或使用上下文管理器：

```python
def test_static_file():
    with TestServer(project_dir='/path/to/project') as server:
        response = httpx.get(f'{server.base_url}/static/test.txt')
        assert response.status_code == 200
```
"""

import asyncio
import logging
import socket
import threading
import time
from contextlib import contextmanager

import uvicorn
from uvicorn.config import Config

logger = logging.getLogger(__name__)


class TestServer:
    """Uliweb ASGI 测试服务器

    用于在单元测试中启动真实的 ASGI 服务器，
    支持同步和异步客户端访问。

    特性：
    - 自动分配可用端口
    - 后台线程运行，不阻塞测试
    - 支持上下文管理器
    - 提供 httpx 客户端便捷方法
    """

    def __init__(
        self,
        app=None,
        project_dir: str = None,
        apps_dir: str = 'apps',
        include_apps: list = None,
        host: str = '127.0.0.1',
        port: int = 0,
        settings_file: str = 'settings.ini',
        local_settings_file: str = 'local_settings.ini',
        log_level: str = 'warning',
        **kwargs
    ):
        """
        初始化测试服务器

        Args:
            app: ASGI 应用实例。如果为 None，则根据 project_dir 创建
            project_dir: 项目目录路径
            apps_dir: apps 目录名称
            include_apps: 额外包含的应用列表
            host: 监听地址，默认为 '127.0.0.1'
            port: 监听端口。0 表示自动分配一个可用端口
            settings_file: settings 文件名
            local_settings_file: 本地 settings 文件名
            log_level: 日志级别，默认为 'warning' 减少测试输出
            **kwargs: 传递给 make_application 的其他参数
        """
        self.host = host
        self.port = port
        self.settings_file = settings_file
        self.local_settings_file = local_settings_file
        self.log_level = log_level

        self._server = None
        self._thread = None
        self._base_url = None
        self._app = app
        self._project_dir = project_dir
        self._apps_dir = apps_dir
        self._include_apps = include_apps or []
        self._kwargs = kwargs
        self._started = False

    def _create_app(self):
        """创建 ASGI 应用"""
        if self._app is not None:
            return self._app

        from uliweb.manage import make_application

        self._app = make_application(
            project_dir=self._project_dir,
            apps_dir=self._apps_dir,
            include_apps=self._include_apps,
            settings_file=self.settings_file,
            local_settings_file=self.local_settings_file,
            **self._kwargs
        )
        return self._app

    def _get_available_port(self) -> int:
        """获取一个可用的端口

        Returns:
            可用的端口号
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, 0))
            return s.getsockname()[1]

    def _wait_for_server(self, timeout: float = 10.0) -> bool:
        """等待服务器启动

        Args:
            timeout: 超时时间（秒）

        Returns:
            服务器是否成功启动
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex((self.host, self.port))
                    if result == 0:
                        return True
            except (socket.error, socket.timeout):
                pass
            time.sleep(0.1)
        return False

    def start(self, wait_time: float = 1.0):
        """启动服务器

        Args:
            wait_time: 等待服务器启动的时间（秒），已废弃，使用内部自动等待

        Raises:
            RuntimeError: 如果服务器已经启动
        """
        if self._started:
            raise RuntimeError('Server is already started')

        # 获取可用端口
        if self.port == 0:
            self.port = self._get_available_port()

        self._base_url = f'http://{self.host}:{self.port}'

        # 创建应用
        app = self._create_app()

        # 创建配置
        config = Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level=self.log_level,
            access_log=False,
            reload=False,
            workers=1,
            limit_concurrency=None,
            backlog=2048,
            ssl_keyfile=None,
            ssl_certfile=None,
        )

        self._server = uvicorn.Server(config)

        # 在后台线程中启动服务器
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name='UliwebTestServer'
        )
        self._thread.start()

        # 等待服务器启动
        if not self._wait_for_server():
            logger.warning(f'Server may not have started successfully on {self._base_url}')

        self._started = True
        logger.info(f'Test server started at {self._base_url}')

    def _run_server(self):
        """在线程中运行服务器"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._server.serve())
        except Exception as e:
            logger.error(f'Server error: {e}')
        finally:
            loop.close()

    def stop(self):
        """停止服务器

        如果服务器未启动，则什么都不做。
        """
        if not self._started:
            return

        if self._server is not None:
            self._server.should_exit = True

        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

        self._server = None
        self._started = False
        logger.info('Test server stopped')

    @property
    def base_url(self) -> str:
        """获取服务器的基础 URL

        Returns:
            服务器的基础 URL，如 'http://127.0.0.1:8000'

        Raises:
            RuntimeError: 如果服务器未启动
        """
        if not self._started:
            raise RuntimeError('Server is not started. Call start() first.')
        return self._base_url

    @property
    def url(self) -> str:
        """base_url 的别名"""
        return self.base_url

    @property
    def app(self):
        """获取 ASGI 应用实例

        Returns:
            ASGI 应用实例
        """
        return self._app

    def get_client(self, **kwargs):
        """获取同步 HTTP 客户端

        Args:
            **kwargs: 传递给 httpx.Client 的参数

        Returns:
            httpx.Client 实例
        """
        import httpx

        if not self._started:
            raise RuntimeError('Server is not started. Call start() first.')

        return httpx.Client(
            base_url=self._base_url,
            **kwargs
        )

    def get_async_client(self, **kwargs):
        """获取异步 HTTP 客户端

        Args:
            **kwargs: 传递给 httpx.AsyncClient 的参数

        Returns:
            httpx.AsyncClient 实例
        """
        import httpx

        if not self._started:
            raise RuntimeError('Server is not started. Call start() first.')

        return httpx.AsyncClient(
            base_url=self._base_url,
            **kwargs
        )

    def request(self, method: str, path: str, **kwargs):
        """发送同步 HTTP 请求的便捷方法

        Args:
            method: HTTP 方法
            path: 请求路径
            **kwargs: 传递给 httpx.Client.request 的参数

        Returns:
            httpx.Response 实例
        """
        with self.get_client() as client:
            return client.request(method, path, **kwargs)

    def get(self, path: str, **kwargs):
        """发送 GET 请求"""
        return self.request('GET', path, **kwargs)

    def post(self, path: str, **kwargs):
        """发送 POST 请求"""
        return self.request('POST', path, **kwargs)

    def put(self, path: str, **kwargs):
        """发送 PUT 请求"""
        return self.request('PUT', path, **kwargs)

    def delete(self, path: str, **kwargs):
        """发送 DELETE 请求"""
        return self.request('DELETE', path, **kwargs)

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()


@contextmanager
def test_server(project_dir: str = None, **kwargs):
    """创建测试服务器的上下文管理器

    这是一个便捷函数，用于在测试中快速创建和销毁测试服务器。

    Args:
        project_dir: 项目目录路径
        **kwargs: 传递给 TestServer 的其他参数

    Yields:
        TestServer: 测试服务器实例

    用法示例：

    ```python
    from uliweb.utils.test_server import test_server
    import httpx

    def test_static_file():
        with test_server(project_dir='/path/to/project') as server:
            response = httpx.get(f'{server.base_url}/static/test.txt')
            assert response.status_code == 200

    def test_static_file_shortcut():
        # 使用便捷方法
        with test_server(project_dir='/path/to/project') as server:
            response = server.get('/static/test.txt')
            assert response.status_code == 200
    ```

    Returns:
        TestServer: 测试服务器实例
    """
    server = TestServer(project_dir=project_dir, **kwargs)
    server.start()
    try:
        yield server
    finally:
        server.stop()