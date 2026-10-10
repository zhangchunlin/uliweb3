"""
测试 AsyncDispatcher 异步调度器功能

测试 AsyncDispatcher、UliwebRouter 和路由转换功能。
"""
import pytest
import tempfile
import shutil
import sys
from pathlib import Path


def cleanup_rules():
    """清理 rules.__exposes__ 和模块缓存"""
    from uliweb.core import rules
    from uliweb.core.SimpleFrame import __app_dirs__, __app_alias__

    # 清理
    rules.__exposes__.clear()
    rules.__url_names__.clear()
    rules.__no_need_exposed__[:] = []

    # 清理 __app_dirs__ 缓存（这对于测试环境至关重要）
    __app_dirs__.clear()
    __app_alias__.clear()

    # 清理模块缓存（移除之前测试可能导入的模块）
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('testapp')]
    for mod in modules_to_remove:
        del sys.modules[mod]


def create_temp_project():
    """创建临时测试项目"""
    tmpdir = tempfile.mkdtemp()
    project_dir = Path(tmpdir)
    apps_dir = project_dir / 'apps'
    apps_dir.mkdir()

    # 创建 settings.ini
    settings_ini = apps_dir / 'settings.ini'
    settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testapp",
]
""")

    # 创建 app
    app_dir = apps_dir / 'testapp'
    app_dir.mkdir()

    # 创建 __init__.py
    (app_dir / '__init__.py').write_text('')

    # 添加 project_dir 到 sys.path 以便 app 可以被导入
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))

    return project_dir, apps_dir, app_dir


def cleanup_temp_project(project_dir):
    """清理临时测试项目"""
    try:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))
    except ValueError:
        pass
    finally:
        shutil.rmtree(str(project_dir), ignore_errors=True)


class TestAsyncDispatcher:
    """AsyncDispatcher 测试类"""

    def setUp(self):
        """设置测试环境（支持 nosetests）"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境（支持 nosetests）"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    # 同时支持 pytest
    setup_method = setUp
    teardown_method = tearDown

    def test_async_dispatcher_init(self):
        """测试 AsyncDispatcher 基本初始化"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 验证初始化
        assert dispatcher.apps_dir == 'apps'
        assert dispatcher.project_dir == str(self.project_dir)
        assert not dispatcher._initialized

    def test_async_dispatcher_prepare(self):
        """测试 AsyncDispatcher prepare 方法"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 views.py
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/test")
def index():
    return "OK"
''')

        # 创建 AsyncDispatcher（不自动启动）
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 手动设置 apps 列表（因为测试环境中 get_apps 可能返回空列表）
        # 需要在 prepare() 之前设置，因为 prepare() 会重新加载 apps
        dispatcher.apps = ['testapp']

        # 调用 prepare
        dispatcher.prepare()

        # 验证路由已注册
        assert len(dispatcher.router.routes) > 0
        route_paths = [r.path for r in dispatcher.router.routes]
        assert '/test' in route_paths

    def test_async_dispatcher_settings(self):
        """测试 AsyncDispatcher 设置加载"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 调用 prepare
        dispatcher.prepare()

        # 验证 settings 已加载
        assert hasattr(dispatcher, 'settings')
        assert dispatcher.settings is not None
        assert dispatcher.settings.GLOBAL.DEBUG is True

    def test_async_dispatcher_router(self):
        """测试 UliwebRouter 功能"""
        from uliweb.core.SimpleFrame import UliwebRouter
        from starlette.routing import Route, WebSocketRoute

        # 创建 UliwebRouter
        router = UliwebRouter()

        # 添加 HTTP 路由
        async def http_handler():
            pass

        router.add_route('/http', http_handler, methods=['GET', 'POST'])

        # 验证 HTTP 路由
        assert len(router.routes) == 1
        assert isinstance(router.routes[0], Route)
        assert router.routes[0].path == '/http'

        # 添加 WebSocket 路由
        async def ws_handler():
            pass

        router.add_websocket_route('/ws', ws_handler)

        # 验证 WebSocket 路由
        assert len(router.routes) == 2
        ws_routes = [r for r in router.routes if isinstance(r, WebSocketRoute)]
        assert len(ws_routes) == 1
        assert ws_routes[0].path == '/ws'


class TestUliwebRouter:
    """UliwebRouter 测试类"""

    def test_add_route_basic(self):
        """测试基本路由添加"""
        from uliweb.core.SimpleFrame import UliwebRouter
        from starlette.routing import Route

        router = UliwebRouter()

        async def handler():
            pass

        router.add_route('/test', handler)

        assert len(router.routes) == 1
        assert isinstance(router.routes[0], Route)
        assert router.routes[0].path == '/test'

    def test_add_websocket_route(self):
        """测试 WebSocket 路由"""
        from uliweb.core.SimpleFrame import UliwebRouter
        from starlette.routing import WebSocketRoute

        router = UliwebRouter()

        async def handler():
            pass

        router.add_websocket_route('/ws', handler)

        assert len(router.routes) == 1
        assert isinstance(router.routes[0], WebSocketRoute)
        assert router.routes[0].path == '/ws'

    def test_mount(self):
        """测试挂载子应用"""
        from uliweb.core.SimpleFrame import UliwebRouter
        from starlette.routing import Mount

        router = UliwebRouter()

        # 创建子应用
        sub_router = UliwebRouter()

        async def sub_handler():
            pass

        sub_router.add_route('/hello', sub_handler)

        # 挂载子应用
        router.mount('/api', sub_router)

        # 验证挂载
        assert len(router.router.routes) == 1
        assert isinstance(router.router.routes[0], Mount)
        assert router.router.routes[0].path == '/api'

    def test_build_url(self):
        """测试 URL 构建"""
        from uliweb.core.SimpleFrame import UliwebRouter

        router = UliwebRouter()

        async def handler():
            pass

        router.add_route('/user/{id}', handler, name='user_detail')

        # 测试 URL 构建
        url = router.build('user_detail', {'id': 123})
        assert url == '/user/123'


class TestRouteConversion:
    """路由转换测试类"""

    def test_convert_route_param_simple(self):
        """测试简单参数转换"""
        from uliweb.core.SimpleFrame import _convert_route_param

        # 测试简单参数 - 默认类型为 str
        rule, param_types = _convert_route_param('/user/<id>')
        assert rule == '/user/{id}'
        # 简单参数不指定类型时，param_types 为空字典
        assert param_types == {}

    def test_convert_route_param_typed(self):
        """测试带类型的参数转换"""
        from uliweb.core.SimpleFrame import _convert_route_param

        # 测试带类型的参数
        rule, param_types = _convert_route_param('/user/<int:id>')
        assert rule == '/user/{id}'
        assert param_types == {'id': 'int'}

    def test_convert_route_param_multiple(self):
        """测试多个参数转换"""
        from uliweb.core.SimpleFrame import _convert_route_param

        # 测试多个参数
        rule, param_types = _convert_route_param('/post/<int:post_id>/comment/<int:comment_id>')
        assert rule == '/post/{post_id}/comment/{comment_id}'
        assert param_types == {'post_id': 'int', 'comment_id': 'int'}

    def test_convert_route_param_no_change(self):
        """测试无参数的路由"""
        from uliweb.core.SimpleFrame import _convert_route_param

        # 测试无参数的路由
        rule, param_types = _convert_route_param('/api/data')
        assert rule == '/api/data'
        assert param_types == {}


class TestViewsImport:
    """视图导入测试类"""

    def setUp(self):
        """设置测试环境（支持 nosetests）"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境（支持 nosetests）"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    # 同时支持 pytest
    setup_method = setUp
    teardown_method = tearDown

    def test_views_extra_import(self):
        """测试 views_*.py 文件导入"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 views.py
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/main")
def main():
    return "OK"
''')

        # 创建 views_extra.py
        (self.app_dir / 'views_extra.py').write_text('''
from uliweb import expose

@expose("/extra")
def extra():
    return "OK"
''')

        # 创建 views_api.py
        (self.app_dir / 'views_api.py').write_text('''
from uliweb import expose

@expose("/api")
def api():
    return "OK"
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 手动设置 apps 列表（因为测试环境中 get_apps 可能返回空列表）
        dispatcher.apps = ['testapp']

        # 调用 prepare
        dispatcher.prepare()

        # 验证所有视图文件都被导入
        route_paths = [r.path for r in dispatcher.router.routes]
        assert '/main' in route_paths, "views.py should be imported"
        assert '/extra' in route_paths, "views_extra.py should be imported"
        assert '/api' in route_paths, "views_api.py should be imported"

        # 验证路由名称格式
        route_names = [r.name for r in dispatcher.router.routes]
        assert 'testapp.views.main' in route_names
        assert 'testapp.views_extra.extra' in route_names
        assert 'testapp.views_api.api' in route_names

    def test_multiple_apps(self):
        """测试多应用支持"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建第二个 app
        app2_dir = self.apps_dir / 'testapp2'
        app2_dir.mkdir()
        (app2_dir / '__init__.py').write_text('')

        # 创建 views.py
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/app1")
def app1_index():
    return "OK"
''')

        (app2_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/app2")
def app2_index():
    return "OK"
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 手动设置 apps 列表
        dispatcher.apps = ['testapp', 'testapp2']

        # 调用 prepare
        dispatcher.prepare()

        # 验证两个应用的路由都被注册
        route_paths = [r.path for r in dispatcher.router.routes]
        assert '/app1' in route_paths
        assert '/app2' in route_paths

    def test_route_with_parameters(self):
        """测试带参数的路由"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        # 创建 views.py
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/user/<id>")
def user_detail(id):
    return "OK"

@expose("/post/<int:post_id>/comment/<int:comment_id>")
def comment(post_id, comment_id):
    return "OK"
''')

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 手动设置 apps 列表
        dispatcher.apps = ['testapp']

        # 调用 prepare
        dispatcher.prepare()

        # 验证路由已注册
        route_paths = [r.path for r in dispatcher.router.routes]
        assert '/user/{id}' in route_paths
        assert '/post/{post_id}/comment/{comment_id}' in route_paths

        # 验证参数类型
        # 简单参数 <id> 没有指定类型，所以 param_types 为空
        assert dispatcher.route_param_types.get('/user/{id}') == {}
        # 带类型的参数
        assert dispatcher.route_param_types.get('/post/{post_id}/comment/{comment_id}') == {'post_id': 'int', 'comment_id': 'int'}

    def test_async_dispatcher_sync_handler_transaction_commit(self):
        """测试 AsyncDispatcher 自动对成功的同步视图提交 ORM 事务"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 定义简单的同步视图函数
        mock_called = []
        def sync_handler(*args, **kwargs):
            mock_called.append(True)
            return "sync_handler_success"

        # Mock parameters
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_env = {}

        # Patch CommitAll, RollbackAll 和 ResetAll
        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit_all, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback_all, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset_all:
             
            # 运行同步视图调度
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    dispatcher._call_function(
                        handler=sync_handler,
                        request=mock_request,
                        response=mock_response,
                        env=mock_env,
                        args=[],
                        kwargs={}
                    )
                )
            finally:
                loop.close()

            # 验证结果
            assert result == "sync_handler_success"
            assert len(mock_called) == 1
            mock_commit_all.assert_called_once()
            mock_rollback_all.assert_not_called()
            mock_reset_all.assert_called_once()

    def test_async_dispatcher_sync_handler_transaction_rollback(self):
        """测试 AsyncDispatcher 对失败的同步视图执行自动 ORM 事务回滚及连接重置"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        # 创建 AsyncDispatcher
        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        # 定义会引发异常的同步视图函数
        class CustomTestException(Exception):
            pass

        def sync_handler(*args, **kwargs):
            raise CustomTestException("View Error")

        # Mock parameters
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_env = {}

        # Patch CommitAll, RollbackAll 和 ResetAll
        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit_all, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback_all, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset_all:
             
            # 运行并断言异常抛出
            loop = asyncio.new_event_loop()
            try:
                with pytest.raises(CustomTestException):
                    loop.run_until_complete(
                        dispatcher._call_function(
                            handler=sync_handler,
                            request=mock_request,
                            response=mock_response,
                            env=mock_env,
                            args=[],
                            kwargs={}
                        )
                    )
            finally:
                loop.close()

            # 验证结果
            mock_commit_all.assert_not_called()
            mock_rollback_all.assert_called_once()
            mock_reset_all.assert_called_once()

    def test_async_dispatcher_sync_middleware_commit_and_reset(self):
        """测试 AsyncDispatcher 对同步中间件执行后自动 CommitAll 和 ResetAll 释放连接"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        mock_called = []
        def sync_middleware_process_request(req):
            mock_called.append(True)
            return None

        mock_request = MagicMock()

        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit_all, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback_all, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset_all:

            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(
                    dispatcher._call_middleware_method(sync_middleware_process_request, mock_request)
                )
            finally:
                loop.close()

            assert res is None
            assert len(mock_called) == 1
            mock_commit_all.assert_called_once()
            mock_rollback_all.assert_not_called()
            mock_reset_all.assert_called_once()

    def test_async_dispatcher_sync_middleware_rollback_and_reset(self):
        """测试 AsyncDispatcher 对出错的同步中间件自动 RollbackAll 和 ResetAll 释放连接"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        class MiddlewareError(Exception):
            pass

        def sync_middleware_fail(req):
            raise MiddlewareError("Middleware DB error")

        mock_request = MagicMock()

        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit_all, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback_all, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset_all:

            loop = asyncio.new_event_loop()
            try:
                with pytest.raises(MiddlewareError):
                    loop.run_until_complete(
                        dispatcher._call_middleware_method(sync_middleware_fail, mock_request)
                    )
            finally:
                loop.close()

            mock_commit_all.assert_not_called()
            mock_rollback_all.assert_called_once()
            mock_reset_all.assert_called_once()

    def test_async_dispatcher_sync_middleware_commit_failure_handled(self):
        """测试同步中间件在 CommitAll 失败时记录错误并回滚，但不中断返回结果（对齐 spec 2.1）"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        def sync_middleware_ok(req):
            return "SUCCESS_RESULT"

        mock_request = MagicMock()

        with patch('uliweb.core.SimpleFrame.CommitAll', side_effect=Exception("DB Commit Failure")) as mock_commit_all, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback_all, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset_all:

            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(
                    dispatcher._call_middleware_method(sync_middleware_ok, mock_request)
                )
            finally:
                loop.close()

            assert res == "SUCCESS_RESULT"
            mock_commit_all.assert_called_once()
            mock_rollback_all.assert_called_once()
            mock_reset_all.assert_called_once()

    def test_match_route_same_path_multiple_methods(self):
        """测试同路径多方法时，方法不匹配的路由不遮蔽匹配的路由"""
        import asyncio
        from starlette.exceptions import HTTPException
        from uliweb.core.SimpleFrame import AsyncDispatcher, Request

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher.apps = ['testapp']

        async def view_get(request):
            return "GET"

        async def view_post(request):
            return "POST"

        # 先注册 POST，后注册 GET（旧逻辑下 POST 的 PARTIAL 会遮蔽 GET 的 FULL）
        dispatcher.router.add_route("/thing", view_post, methods=["POST"], name="post_thing")
        dispatcher.router.add_route("/thing", view_get, methods=["GET"], name="get_thing")

        def make_req(method):
            scope = {
                "type": "http", "method": method, "path": "/thing",
                "path_params": {}, "query_string": b"", "headers": [],
                "scheme": "http", "server": ("test", 80), "client": None,
            }
            return Request(scope)

        async def run():
            # GET 应 FULL 匹配到 GET 路由，而非被前面的 POST PARTIAL 遮蔽
            route, params = await dispatcher._match_route(make_req("GET"))
            assert route.name == "get_thing"
            # DELETE 无任何路由允许 → 405
            with pytest.raises(HTTPException) as exc_info:
                await dispatcher._match_route(make_req("DELETE"))
            assert exc_info.value.status_code == 405

        asyncio.run(run())

    def test_exposes_same_endpoint_multiple_urls(self):
        """测试同一 endpoint 可被多个 URL 映射（@expose 与 EXPOSES 共存）"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        (self.apps_dir / 'settings.ini').write_text('''
[GLOBAL]
DEBUG = True
INSTALLED_APPS = ["testapp"]

[EXPOSES]
root = "/", "testapp.views.test"
''')
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/test")
def test():
    return "OK"
''')

        dispatcher = AsyncDispatcher(
            apps_dir='apps', project_dir=str(self.project_dir), start=False)
        dispatcher.apps = ['testapp']
        dispatcher.prepare()

        paths = [r.path for r in dispatcher.router.routes]
        # 同一 endpoint 的 /test 与 / 应同时存在
        assert '/test' in paths
        assert '/' in paths

    def test_exposes_same_url_different_endpoint_later_wins(self):
        """测试同一 URL 映射到两个不同 endpoint：后者覆盖，仅保留一条路由"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        (self.apps_dir / 'settings.ini').write_text('''
[GLOBAL]
DEBUG = True
INSTALLED_APPS = ["testapp"]

[EXPOSES]
t = "/test", "testapp.views.b"
''')
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/test")
def a():
    return "A"

def b():
    return "B"
''')

        dispatcher = AsyncDispatcher(
            apps_dir='apps', project_dir=str(self.project_dir), start=False)
        dispatcher.apps = ['testapp']
        dispatcher.prepare()

        test_routes = [r for r in dispatcher.router.routes if r.path == '/test']
        assert len(test_routes) == 1
        assert getattr(test_routes[0], 'endpoint', None) == 'testapp.views.b'

    def test_exposes_same_url_same_endpoint_no_duplicate(self):
        """测试同一 URL 映射到同一 endpoint：去重，仅一条路由"""
        from uliweb.core.SimpleFrame import AsyncDispatcher

        (self.apps_dir / 'settings.ini').write_text('''
[GLOBAL]
DEBUG = True
INSTALLED_APPS = ["testapp"]

[EXPOSES]
t = "/test", "testapp.views.test"
''')
        (self.app_dir / 'views.py').write_text('''
from uliweb import expose

@expose("/test")
def test():
    return "OK"
''')

        dispatcher = AsyncDispatcher(
            apps_dir='apps', project_dir=str(self.project_dir), start=False)
        dispatcher.apps = ['testapp']
        dispatcher.prepare()

        test_routes = [r for r in dispatcher.router.routes if r.path == '/test']
        assert len(test_routes) == 1

    def test_sqlite_pool_args_filtered(self):
        """测试 NamedEngine._create 对 sqlite 连接字符串自动过滤 QueuePool 参数"""
        from uliweb.orm import get_connection
        engine = get_connection(
            'sqlite:///:memory:',
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=300,
            pool_pre_ping=True
        )
        assert engine is not None

    def test_async_dispatcher_main_middleware_commit_failure_rollback(self):
        """测试主请求链在 CommitAll 抛错时触发 RollbackAll 并最终 ResetAll"""
        from unittest.mock import patch, MagicMock, AsyncMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        mock_middleware = MagicMock()
        mock_middleware.dispatch = AsyncMock(return_value=None)

        async def dummy_next_app(scope, receive, send):
            pass

        app = dispatcher._wrap_advanced_middleware(mock_middleware, dummy_next_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
        }

        with patch('uliweb.core.SimpleFrame.CommitAll', side_effect=RuntimeError("Commit failed")) as mock_commit, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(app(scope, AsyncMock(), AsyncMock()))
            finally:
                loop.close()

            mock_commit.assert_called_once()
            mock_rollback.assert_called_once()
            mock_reset.assert_called_once()

    def test_coroutine_handler_orm_commit_and_reset(self):
        """测试异步协程视图执行成功时自动触发 CommitAll 与 ResetAll"""
        from unittest.mock import patch, AsyncMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        async def dummy_coro_handler():
            return "ok"

        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(dispatcher.call_handler(dummy_coro_handler, None, None, {}))
            finally:
                loop.close()

            assert getattr(res, 'body', None) == b"ok" or res == "ok"
            mock_commit.assert_called_once()
            mock_rollback.assert_not_called()
            mock_reset.assert_called_once()

    def test_coroutine_handler_orm_error_rollback_and_reset(self):
        """测试异步协程视图抛出异常时自动触发 RollbackAll 与 ResetAll"""
        from unittest.mock import patch
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )

        async def error_coro_handler():
            raise ValueError("coroutine error")

        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit, \
             patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback, \
             patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

            loop = asyncio.new_event_loop()
            try:
                with pytest.raises(ValueError):
                    loop.run_until_complete(dispatcher.call_handler(error_coro_handler, None, None, {}))
            finally:
                loop.close()

            mock_commit.assert_not_called()
            mock_rollback.assert_called_once()
            mock_reset.assert_called_once()

    def test_async_dispatcher_call_always_calls_reset_all(self):
        """测试 AsyncDispatcher.__call__ 在请求结束时无条件执行 ResetAll"""
        from unittest.mock import patch, AsyncMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        dispatcher._initialized = True
        dispatcher._build_middleware_stack = AsyncMock()
        mock_app = AsyncMock()
        dispatcher._build_middleware_stack.return_value = mock_app

        scope = {"type": "http", "method": "GET", "path": "/test"}

        with patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(dispatcher(scope, AsyncMock(), AsyncMock()))
            finally:
                loop.close()

            mock_reset.assert_called_once()

    def test_to_thread_calls_rollback_and_reset_all(self):
        """测试 to_thread 工具函数在工作线程中保证事务回滚与连接释放"""
        from unittest.mock import patch
        from uliweb.core.SimpleFrame import to_thread, AsyncDispatcher
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback,                  patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

                def sync_ok(x, y=10):
                    return x + y

                async def test_ok():
                    res = await to_thread(sync_ok, 5, y=20)
                    assert res == 25

                loop.run_until_complete(test_ok())
                assert mock_rollback.call_count == 0
                assert mock_reset.call_count == 1

            with patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback,                  patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

                def sync_fail():
                    raise ValueError("test_err")

                async def test_fail():
                    try:
                        await to_thread(sync_fail)
                    except ValueError as e:
                        assert str(e) == "test_err"

                loop.run_until_complete(test_fail())
                assert mock_rollback.call_count == 1
                assert mock_reset.call_count == 1

            # 测试 dispatcher.to_thread 代理调用
            dispatcher = AsyncDispatcher(apps_dir='apps', project_dir=str(self.project_dir), start=False)
            async def test_dispatcher():
                res = await dispatcher.to_thread(lambda: "disp_ok")
                assert res == "disp_ok"
            loop.run_until_complete(test_dispatcher())
            dispatcher.close()
        finally:
            loop.close()

    def test_to_thread_contextvars_propagation(self):
        """测试 to_thread 正常继承与传递 ContextVar 上下文变量"""
        from contextvars import ContextVar
        import asyncio
        from uliweb.core.SimpleFrame import to_thread

        test_var: ContextVar[str] = ContextVar('test_var', default='default_val')
        test_var.set('caller_val')

        def worker():
            return test_var.get()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            val = loop.run_until_complete(to_thread(worker))
            assert val == 'caller_val'
        finally:
            loop.close()

    def test_to_thread_no_implicit_commit(self):
        """测试 to_thread 执行正常任务时不会静默隐式触发 CommitAll（事务提交由业务主动控制）"""
        from unittest.mock import patch
        import asyncio
        from uliweb.core.SimpleFrame import to_thread

        with patch('uliweb.core.SimpleFrame.CommitAll') as mock_commit,              patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:
            def sync_readonly():
                return "readonly_result"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(to_thread(sync_readonly))
                assert res == "readonly_result"
                assert mock_commit.call_count == 0
                assert mock_reset.call_count == 1
            finally:
                loop.close()

    def test_websocket_sync_handler_resets_connection(self):
        """测试同步 WebSocket handler 执行时通过 _sync_ws_wrapper 自动管理异常回滚并释放数据库连接"""
        from unittest.mock import patch, MagicMock
        from uliweb.core.SimpleFrame import AsyncDispatcher
        import asyncio

        dispatcher = AsyncDispatcher(apps_dir='apps', project_dir=str(self.project_dir), start=False)

        mock_ws = MagicMock()
        mock_ws.url = 'ws://localhost/ws'
        mock_ws.scope = {'type': 'websocket'}

        # 模拟同步 WebSocket 处理器正常处理
        def sync_ws_view(ws):
            return "ws_processed"

        mock_ws._handler = sync_ws_view
        mock_ws._handler_cls = None
        mock_ws.rule = None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback,                  patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

                loop.run_until_complete(dispatcher._open_websocket(mock_ws))
                assert mock_rollback.call_count == 0
                assert mock_reset.call_count >= 1

            # 模拟同步 WebSocket 处理器抛出异常
            def sync_ws_error(ws):
                raise RuntimeError("ws error")

            mock_ws._handler = sync_ws_error
            with patch('uliweb.core.SimpleFrame.RollbackAll') as mock_rollback,                  patch('uliweb.core.SimpleFrame.ResetAll') as mock_reset:

                try:
                    loop.run_until_complete(dispatcher._open_websocket(mock_ws))
                except RuntimeError:
                    pass
                assert mock_rollback.call_count == 1
                assert mock_reset.call_count >= 1
        finally:
            dispatcher.close()
            loop.close()

    def test_import_to_thread_from_uliweb(self):
        """测试从顶级 uliweb 模块直接导入 to_thread"""
        from uliweb import to_thread as uliweb_to_thread
        from uliweb.core.SimpleFrame import to_thread as frame_to_thread

        assert uliweb_to_thread is frame_to_thread


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
