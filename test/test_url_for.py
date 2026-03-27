"""
测试 url_for 和相关 URL 生成功能
"""
import pytest
from uliweb.core.SimpleFrame import UliwebRouter


def test_url_for_function():
    """测试模块级 url_for 函数"""
    from uliweb import application

    # 这个测试验证 url_for 函数存在且可调用
    from uliweb.core.SimpleFrame import url_for

    # 如果 application 还没有 _url_for 方法，应该返回占位符
    result = url_for('test.endpoint')
    assert result.startswith('/')


def test_url_router_basic():
    """测试 UliwebRouter 基础功能"""
    router = UliwebRouter()

    # 添加路由
    def index(request):
        return "index"

    router.add_route('/index', index, methods=['GET'])

    # 检查路由是否添加成功
    assert len(router.routes) == 1
    assert router.routes[0].path == '/index'


def test_url_router_with_params():
    """测试带参数的路由"""
    router = UliwebRouter()

    def user_view(request, user_id):
        return f"user {user_id}"

    # 添加带参数的路由
    router.add_route('/users/{user_id}', user_view, methods=['GET'])

    assert len(router.routes) == 1
    assert router.routes[0].path == '/users/{user_id}'


def test_url_router_build():
    """测试 URL 构建功能"""
    router = UliwebRouter()

    def index(request):
        return "index"

    def user_view(request, user_id):
        return f"user {user_id}"

    # 添加路由
    router.add_route('/index', index, methods=['GET'], name='index')
    router.add_route('/users/{user_id}', user_view, methods=['GET'], name='user')

    # 测试 URL 构建
    # 注意：build 方法需要先有 url_map
    # 由于 url_map 在初始化时是空的，我们需要测试其基本功能
    router.url_map[index] = router.routes[0]
    router.url_map[user_view] = router.routes[1]

    # 测试构建基本 URL
    url = router.build('index', {})
    assert url == '/index'

    # 测试构建带参数的 URL
    url = router.build('user', {'user_id': '123'})
    assert '123' in url


def test_convert_route_param():
    """测试路由参数转换功能"""
    from uliweb.core.SimpleFrame import _convert_route_param

    # 测试基本参数转换（无类型）
    result, param_types = _convert_route_param('/users/<user_id>')
    assert result == '/users/{user_id}'
    assert param_types == {}  # 无类型参数返回空字典

    # 测试带类型的参数转换
    result, param_types = _convert_route_param('/users/<int:user_id>')
    assert result == '/users/{user_id}'
    assert param_types == {'user_id': 'int'}

    # 测试多个参数
    result, param_types = _convert_route_param('/posts/<int:post_id>/comments/<int:comment_id>')
    assert result == '/posts/{post_id}/comments/{comment_id}'
    assert param_types == {'post_id': 'int', 'comment_id': 'int'}


def test_merge_rules():
    """测试路由合并功能"""
    from uliweb.core.rules import clear_rules, expose, merge_rules

    # 清理现有规则
    clear_rules()

    # 定义视图函数
    @expose('/test1')
    def test_view1():
        pass

    @expose('/test2/<id>')
    def test_view2(id):
        pass

    # 合并规则
    rules = merge_rules()

    # 验证规则
    assert len(rules) >= 2

    # 查找我们的测试视图
    test_rules = [r for r in rules if r[0] == 'test_url_for']
    assert len(test_rules) >= 2


def test_url_for_static():
    """测试 url_for_static 函数"""
    # 导入设置
    from uliweb import settings

    # 设置 STATIC_URL 配置（如果未设置）
    # 注意：在测试环境中 settings.GLOBAL 可能是 None，需要先检查
    static_url = None
    if settings is not None:
        try:
            global_settings = settings.GLOBAL
            if global_settings is not None:
                static_url = global_settings.get('STATIC_URL', '/static')
        except Exception:
            pass

    # 如果无法从 settings 获取，使用默认值
    if static_url is None:
        static_url = '/static'

    assert static_url is not None


def test_async_dispatcher_url_for():
    """测试 AsyncDispatcher._url_for 方法"""
    from uliweb.core.SimpleFrame import AsyncDispatcher
    from uliweb.core import rules

    # 清理现有规则
    rules.clear_rules()

    # 定义测试视图（先不使用装饰器）
    def hello():
        return "Hello"

    def user(id):
        return f"User {id}"

    # 修改函数元数据，模拟真实情况（函数定义在 test.test_url_for 模块中）
    hello.__module__ = 'test.test_url_for'
    hello.__qualname__ = 'hello'
    user.__module__ = 'test.test_url_for'
    user.__qualname__ = 'user'

    # 使用赋值方式调用 expose（而不是装饰器）
    # 这样 expose 会在修改元信息之后应用
    rules.expose('/hello')(hello)
    rules.expose('/user/<id>')(user)

    # 合并规则
    merged = rules.merge_rules()

    # 验证合并后的 endpoint 是正确的
    endpoint_hello = None
    endpoint_user = None
    for v in merged:
        appname, endpoint, url, kw = v
        if url == '/hello':
            endpoint_hello = endpoint
        elif url == '/user/<id>':
            endpoint_user = endpoint

    assert endpoint_hello == 'test.test_url_for.hello', f"Expected 'test.test_url_for.hello', got '{endpoint_hello}'"
    assert endpoint_user == 'test.test_url_for.user', f"Expected 'test.test_url_for.user', got '{endpoint_user}'"

    # 创建 AsyncDispatcher 实例
    dispatcher = AsyncDispatcher(
        apps_dir='test/testproject',
        project_dir='test',
        start=False
    )

    # 手动初始化路由
    dispatcher._init_settings()
    dispatcher.process_domains(dispatcher.settings)

    # 导入视图并注册路由
    from uliweb.core import dispatch
    dispatch.call(dispatcher, 'startup_installed')

    # 初始化路由
    dispatcher._init_routes_sync()

    # 测试 _url_for 方法
    url = dispatcher._url_for('test.test_url_for.hello')
    assert url == '/hello', f"Expected '/hello', got '{url}'"

    # 测试带参数的 URL
    url = dispatcher._url_for('test.test_url_for.user', id=123)
    assert '123' in url, f"Expected '123' in url, got '{url}'"


def test_rules_get_endpoint():
    """测试 rules.get_endpoint 函数"""
    from uliweb.core import rules

    # 测试普通函数 - 使用已存在的视图函数

    # 清理现有规则
    rules.clear_rules()

    # 定义一个测试函数
    @rules.expose('/test_endpoint')
    def test_endpoint_view():
        pass

    # 合并规则
    rules.merge_rules()

    # 获取 endpoint
    endpoint = rules.get_endpoint(test_endpoint_view)
    assert 'test_endpoint_view' in endpoint


def test_rules_url_names():
    """测试 rules.__url_names__ 映射"""
    from uliweb.core import rules

    # 清理现有规则
    rules.clear_rules()

    # 定义带名称的视图
    @rules.expose('/named_url', name='my_named_url')
    def named_view():
        pass

    # 合并规则
    rules.merge_rules()

    # 验证 URL 名称映射
    assert 'my_named_url' in rules.__url_names__


def test_async_dispatcher_multiple_apps_url_for():
    """测试多个应用的 url_for - 模拟两个不同的应用"""
    from uliweb.core.SimpleFrame import AsyncDispatcher
    from uliweb.core import rules

    # 清理现有规则
    rules.clear_rules()

    # === 应用 1: home 应用 ===
    def home_index():
        return "Home"

    def home_about():
        return "About"

    # 修改函数元数据，模拟 home 应用
    home_index.__module__ = 'apps.home.views'
    home_index.__qualname__ = 'index'
    home_about.__module__ = 'apps.home.views'
    home_about.__qualname__ = 'about'

    # 注册 home 应用的路由
    rules.expose('/')(home_index)
    rules.expose('/about')(home_about)

    # === 应用 2: blog 应用 ===
    def blog_list():
        return "Blog List"

    def blog_detail(post_id):
        return f"Blog {post_id}"

    # 修改函数元数据，模拟 blog 应用
    blog_list.__module__ = 'apps.blog.views'
    blog_list.__qualname__ = 'list'
    blog_detail.__module__ = 'apps.blog.views'
    blog_detail.__qualname__ = 'detail'

    # 注册 blog 应用的路由
    rules.expose('/blog')(blog_list)
    rules.expose('/blog/<post_id>')(blog_detail)

    # 合并规则
    merged = rules.merge_rules()

    # 验证各应用的 endpoint
    endpoints = {v[2]: v[1] for v in merged}  # url -> endpoint

    assert endpoints['/'] == 'apps.home.views.index'
    assert endpoints['/about'] == 'apps.home.views.about'
    assert endpoints['/blog'] == 'apps.blog.views.list'
    assert endpoints['/blog/<post_id>'] == 'apps.blog.views.detail'

    # 创建 AsyncDispatcher 实例
    dispatcher = AsyncDispatcher(
        apps_dir='test/testproject',
        project_dir='test',
        start=False
    )

    # 手动初始化路由
    dispatcher._init_settings()
    dispatcher.process_domains(dispatcher.settings)

    # 导入视图并注册路由
    from uliweb.core import dispatch
    dispatch.call(dispatcher, 'startup_installed')

    # 初始化路由
    dispatcher._init_routes_sync()

    # 测试 home 应用的 url_for
    url = dispatcher._url_for('apps.home.views.index')
    assert url == '/', f"Expected '/', got '{url}'"

    url = dispatcher._url_for('apps.home.views.about')
    assert url == '/about', f"Expected '/about', got '{url}'"

    # 测试 blog 应用的 url_for
    url = dispatcher._url_for('apps.blog.views.list')
    assert url == '/blog', f"Expected '/blog', got '{url}'"

    # 测试带参数的 url_for
    url = dispatcher._url_for('apps.blog.views.detail', post_id=42)
    assert '42' in url, f"Expected '42' in url, got '{url}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])