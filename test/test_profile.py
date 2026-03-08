"""
测试 uliweb/asgi/profile 模块
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestASGIProfileMiddleware:
    """测试 ASGIProfileMiddleware 类"""

    def test_import(self):
        """测试模块导入"""
        from uliweb.asgi.profile import ASGIProfileMiddleware, ProfileApplication
        assert ASGIProfileMiddleware is not None
        assert ProfileApplication is not None

    def test_asgi_profile_middleware_init(self):
        """测试 ASGIProfileMiddleware 初始化"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        # 创建一个 mock app
        mock_app = MagicMock()

        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = ASGIProfileMiddleware(mock_app, profile_dir=tmpdir)

            assert middleware.app is mock_app
            assert middleware.path == tmpdir
            assert os.path.exists(tmpdir)

    def test_default_profile_dir(self):
        """测试默认 profile 目录"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        mock_app = MagicMock()

        # 不指定 profile_dir，使用默认目录
        with patch('uliweb.asgi.profile.PROFILE_DATA_DIR', './profile_test'):
            middleware = ASGIProfileMiddleware(mock_app)
            assert middleware.path == './profile_test'

    def test_profile_application_compat(self):
        """测试 ProfileApplication 兼容性"""
        from uliweb.asgi.profile import ProfileApplication, ASGIProfileMiddleware

        mock_app = MagicMock()

        # ProfileApplication 应该返回 ASGIProfileMiddleware 实例
        result = ProfileApplication(mock_app, profile_dir='/tmp/test')
        assert isinstance(result, ASGIProfileMiddleware)
        assert result.app is mock_app

    @pytest.mark.asyncio
    async def test_non_http_request_passthrough(self):
        """测试非 HTTP 请求直接传递"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        mock_app = AsyncMock()
        mock_send = AsyncMock()

        middleware = ASGIProfileMiddleware(mock_app)

        # WebSocket 请求类型
        scope = {
            'type': 'websocket',
            'path': '/test',
        }

        await middleware(scope, None, mock_send)

        # 应该直接传递给 app，不做性能分析
        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_request_profiling(self):
        """测试 HTTP 请求性能分析"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        mock_app = AsyncMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = ASGIProfileMiddleware(mock_app, profile_dir=tmpdir)

            # 创建 mock scope 和 send
            scope = {
                'type': 'http',
                'path': '/test/path',
            }
            mock_receive = AsyncMock()
            mock_send = AsyncMock()

            # 执行请求
            await middleware(scope, mock_receive, mock_send)

            # 验证 app 被调用
            mock_app.assert_called_once()

            # 验证生成了性能分析文件
            files = os.listdir(tmpdir)
            assert len(files) > 0
            # 应该有 .prof 文件
            prof_files = [f for f in files if f.endswith('.prof')]
            assert len(prof_files) > 0

    @pytest.mark.asyncio
    async def test_profile_filename_generation(self):
        """测试性能分析文件名生成"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        mock_app = AsyncMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            middleware = ASGIProfileMiddleware(mock_app, profile_dir=tmpdir)

            # 测试不同路径
            test_cases = [
                ('/test', 'test.prof'),
                ('/user/profile', 'user.profile.prof'),
                ('/api/v1/users/123', 'api.v1.users.123.prof'),
            ]

            for path, expected_filename in test_cases:
                scope = {
                    'type': 'http',
                    'path': path,
                }
                mock_receive = AsyncMock()
                mock_send = AsyncMock()

                await middleware(scope, mock_receive, mock_send)

                # 检查文件名
                files = os.listdir(tmpdir)
                assert expected_filename in files

    def test_profile_data_dir_constant(self):
        """测试 PROFILE_DATA_DIR 常量"""
        from uliweb.asgi.profile import PROFILE_DATA_DIR
        assert PROFILE_DATA_DIR == "./profile"


class TestProfileApplicationIntegration:
    """测试 ProfileApplication 集成"""

    def test_import_from_uliweb_asgi(self):
        """测试从 uliweb.asgi 导入"""
        from uliweb.asgi.profile import ASGIProfileMiddleware
        assert callable(ASGIProfileMiddleware)

    def test_middleware_creates_directory(self):
        """测试中间件创建目录"""
        from uliweb.asgi.profile import ASGIProfileMiddleware

        mock_app = MagicMock()

        # 使用不存在的目录
        test_dir = tempfile.mktemp()
        try:
            ASGIProfileMiddleware(mock_app, profile_dir=test_dir)
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
