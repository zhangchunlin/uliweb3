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
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

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
        """设置测试环境"""
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()

    def tearDown(self):
        """清理测试环境"""
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])