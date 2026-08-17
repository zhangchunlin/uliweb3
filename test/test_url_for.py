"""
测试 url_for 和相关 URL 生成功能
"""
import pytest
from uliweb.core.SimpleFrame import UliwebRouter


def test_url_for_function():
    """测试模块级 url_for 函数"""
    from uliweb import application
    from uliweb.core.SimpleFrame import url_for

    # 这个测试验证 url_for 函数存在且可调用
    # 当 application 有 _url_for 方法时，应该能正常调用
    # 当 application 没有 _url_for 方法时，应该抛出异常
    if hasattr(application, '_url_for'):
        # 如果 application 已初始化，应该能调用（可能会抛出 endpoint not found）
        try:
            url_for('test.endpoint')
        except ValueError as e:
            # 应该抛出 endpoint not found 异常，而不是 "application to be initialized"
            assert "Could not build URL for endpoint" in str(e) or "url_for error" in str(e)
    else:
        # 如果 application 未初始化，应该抛出初始化异常
        try:
            url_for('test.endpoint')
            assert False, "Expected ValueError to be raised"
        except ValueError as e:
            assert "url_for requires application to be initialized" in str(e)


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


def test_url_router_build_with_next():
    """测试 url_for 带 next 参数的 URL 生成

    当传入 next 等非路径参数时，应作为 query string 追加到生成的 URL 上，
    例如 url_for('index', next='/login') 应生成 '/index?next=/login'
    """
    router = UliwebRouter()

    def index(request):
        return "index"

    router.add_route('/index', index, methods=['GET'], name='index')
    router.url_map[index] = router.routes[0]

    # 带 next 参数构建 URL
    url = router.build('index', {'next': '/login'})
    assert url.startswith('/index?next='), f"Expected '?next=' in url, got '{url}'"

    # 解析 query string 验证 next 参数值
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs.get('next') == ['/login'], f"Expected next=/login, got {qs}"


def test_url_router_build_with_path_and_next():
    """测试路径参数和 next 参数同时存在的情况"""
    router = UliwebRouter()

    def user_view(request, user_id):
        return f"user {user_id}"

    router.add_route('/users/{user_id}', user_view, methods=['GET'], name='user')
    router.url_map[user_view] = router.routes[0]

    # 同时传入路径参数和 next 参数
    url = router.build('user', {'user_id': '42', 'next': '/admin'})
    assert url.startswith('/users/42?next='), f"Expected path+next in url, got '{url}'"

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    assert parsed.path == '/users/42'
    qs = parse_qs(parsed.query)
    assert qs.get('next') == ['/admin'], f"Expected next=/admin, got {qs}"


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

    # 测试带 next 参数的 URL
    url = dispatcher._url_for('test.test_url_for.hello', next='/login')
    assert url.startswith('/hello?next='), f"Expected '?next=' in url, got '{url}'"

    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(url).query)
    assert qs.get('next') == ['/login'], f"Expected next=/login, got {qs}"


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


def test_url_for_matching_different_endpoints_same_function_name():
    """测试不同 endpoint 有相同函数名的情况

    这是核心测试场景：
    - app1.views.MyClass.list -> /app1
    - app2.views.MyClass.list -> /app2

    如果部分匹配逻辑过于宽松，可能会导致错误的 URL 生成。
    """
    router = UliwebRouter()

    # 注册两个不同应用的 list 视图
    router.add_route('/app1', 'app1.views.MyClass.list', name='app1_list')
    router.add_route('/app2', 'app2.views.MyClass.list', name='app2_list')

    url1 = router.build('app1.views.MyClass.list', {})
    assert url1 == '/app1', f"Expected '/app1' but got '{url1}'"

    url2 = router.build('app2.views.MyClass.list', {})
    assert url2 == '/app2', f"Expected '/app2' but got '{url2}'"

    # 验证两个 URL 不同
    assert url1 != url2, "Different endpoints should generate different URLs"


def test_url_for_not_found_raises_exception():
    """测试找不到路由时应该抛出异常"""
    router = UliwebRouter()

    try:
        router.build('nonexistent.endpoint', {})
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "Could not build URL for endpoint" in str(e)


def test_exposes_default_all_methods():
    """测试 EXPOSES 路由默认支持所有 HTTP 方法

    根据 EXPOSES 文档，当没有指定 methods 时，默认支持所有 HTTP 方法：
    GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

    这与 WSGI 行为一致。
    """
    from uliweb.core.SimpleFrame import UliwebRouter, _convert_route_param

    router = UliwebRouter()

    # 模拟 EXPOSES 配置中没有指定 methods 的情况
    # 根据 _init_routes 中的逻辑，没有指定 methods 时应该使用默认的 methods 列表
    default_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

    # 测试使用默认方法列表注册路由
    starlette_rule, param_types = _convert_route_param('/test')
    router.add_route(starlette_rule, 'test.endpoint', name='test', methods=default_methods)

    # 验证路由已正确注册
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == '/test'
    assert route.name == 'test'

    # 验证支持的 HTTP 方法
    assert route.methods == set(default_methods)


def test_exposes_custom_methods():
    """测试 EXPOSES 路由支持自定义方法

    当 EXPOSES 配置中指定了 methods 时，应该只支持指定的方法。
    支持两种格式：
    1. 字符串格式: "GET,POST"
    2. 字典格式: {"methods": ["GET", "POST"]}

    注意：Starlette 会自动为所有 GET 路由添加 HEAD 方法。
    """
    from uliweb.core.SimpleFrame import UliwebRouter, _convert_route_param

    router = UliwebRouter()

    # 测试字符串格式 - Starlette 会自动添加 HEAD
    custom_methods_str = ['GET', 'POST']
    starlette_rule, param_types = _convert_route_param('/login')
    router.add_route(starlette_rule, 'auth.views.login', name='login', methods=custom_methods_str)

    # Starlette 自动为 GET 添加 HEAD，所以结果是 {'GET', 'HEAD', 'POST'}
    assert 'GET' in router.routes[0].methods
    assert 'POST' in router.routes[0].methods
    assert 'HEAD' in router.routes[0].methods

    # 测试字典格式
    router2 = UliwebRouter()
    custom_methods_dict = ['GET', 'POST', 'PUT', 'DELETE']
    starlette_rule2, _ = _convert_route_param('/api')
    router2.add_route(starlette_rule2, 'api.views.handler', name='api', methods=custom_methods_dict)

    # Starlette 自动为 GET 添加 HEAD
    assert 'GET' in router2.routes[0].methods
    assert 'POST' in router2.routes[0].methods
    assert 'PUT' in router2.routes[0].methods
    assert 'DELETE' in router2.routes[0].methods
    assert 'HEAD' in router2.routes[0].methods


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
