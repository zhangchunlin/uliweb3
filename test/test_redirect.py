"""
测试 Uliweb ASGI 版本的 redirect 功能
"""
from starlette.responses import RedirectResponse


def test_redirect_function_exists():
    """
    测试 redirect 函数是否存在并可导入
    """
    from uliweb.core.SimpleFrame import redirect

    assert callable(redirect)


def test_redirect_default_status_code():
    """
    测试 redirect 默认使用 302 状态码
    """
    from uliweb.core.SimpleFrame import redirect

    response = redirect('/test')

    # 验证返回的是 RedirectResponse
    assert isinstance(response, RedirectResponse)

    # 验证默认状态码是 302
    assert response.status_code == 302

    # 验证 Location 头
    assert response.headers['location'] == '/test'


def test_redirect_custom_location():
    """
    测试 redirect 可以自定义跳转地址
    """
    from uliweb.core.SimpleFrame import redirect

    response = redirect('/custom/path')

    assert isinstance(response, RedirectResponse)
    assert response.headers['location'] == '/custom/path'


def test_redirect_custom_status_code():
    """
    测试 redirect 可以自定义状态码
    """
    from uliweb.core.SimpleFrame import redirect

    # 测试 301 永久重定向
    response_301 = redirect('/test', code=301)
    assert response_301.status_code == 301

    # 测试 302 临时重定向
    response_302 = redirect('/test', code=302)
    assert response_302.status_code == 302

    # 测试 307 临时重定向
    response_307 = redirect('/test', code=307)
    assert response_307.status_code == 307

    # 测试 308 永久重定向
    response_308 = redirect('/test', code=308)
    assert response_308.status_code == 308


def test_redirect_with_absolute_url():
    """
    测试 redirect 可以使用绝对 URL
    """
    from uliweb.core.SimpleFrame import redirect

    response = redirect('https://example.com/path')

    assert isinstance(response, RedirectResponse)
    assert response.headers['location'] == 'https://example.com/path'


def test_redirect_with_query_string():
    """
    测试 redirect 可以包含查询字符串
    """
    from uliweb.core.SimpleFrame import redirect

    response = redirect('/test?foo=bar&baz=qux')

    assert isinstance(response, RedirectResponse)
    assert response.headers['location'] == '/test?foo=bar&baz=qux'


def test_redirect_in_view_context():
    """
    测试在视图上下文中使用 redirect
    """
    from uliweb import redirect

    # 从 uliweb 导入 redirect 函数
    response = redirect('/home')

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 302
    assert response.headers['location'] == '/home'


def test_redirect_response_headers():
    """
    测试 redirect 响应的 headers
    """
    from uliweb.core.SimpleFrame import redirect

    response = redirect('/test')

    # 验证 Location 头存在
    assert 'location' in response.headers

    # 验证没有 Content-Type（重定向响应通常不需要）
    # Starlette RedirectResponse 默认设置 Content-Type


def test_redirect_multiple_calls():
    """
    测试多次调用 redirect 函数返回独立的响应对象
    """
    from uliweb.core.SimpleFrame import redirect

    response1 = redirect('/path1')
    response2 = redirect('/path2')

    # 验证返回的是不同的对象
    assert response1 is not response2

    # 验证各自的 location 正确
    assert response1.headers['location'] == '/path1'
    assert response2.headers['location'] == '/path2'


def test_redirect_exception_get_response():
    """
    测试 RedirectException 的 get_response 方法返回正确的重定向响应
    """
    from uliweb.core.SimpleFrame import RedirectException

    # 创建 RedirectException
    exception = RedirectException('/login')

    # 获取响应
    response = exception.get_response()

    # 验证是 RedirectResponse
    from starlette.responses import RedirectResponse
    assert isinstance(response, RedirectResponse)

    # 验证状态码是 302
    assert response.status_code == 302

    # 離证 Location 头
    assert response.headers['location'] == '/login'


def test_redirect_exception_custom_status_code():
    """
    测试 RedirectException 可以自定义状态码
    """
    from uliweb.core.SimpleFrame import RedirectException

    # 测试 301 永久重定向
    exception_301 = RedirectException('/home', code=301)
    response_301 = exception_301.get_response()
    assert response_301.status_code == 301

    # 测试 307 临时重定向
    exception_307 = RedirectException('/home', code=307)
    response_307 = exception_307.get_response()
    assert response_307.status_code == 307


def test_handle_exception_with_redirect_exception():
    """
    测试 _handle_exception 方法正确处理 RedirectException
    模拟生产环境中 __begin__ 钩子抛出 RedirectException 的场景
    """
    import asyncio
    from uliweb.core.SimpleFrame import RedirectException, AsyncDispatcher

    # 创建一个模拟的 Dispatcher 实例
    # 使用最小化配置，不加载完整的 settings
    dispatcher = AsyncDispatcher(
        apps_dir='apps',
        project_dir=None,
        start=False
    )

    # 手动设置必要的属性
    dispatcher.settings = type('MockSettings', (), {
        'GLOBAL': type('MockGlobal', (), {
            'DEBUG': False,
            'DEFAULT_CORS': False
        })(),
        'get_var': lambda self, key, default=None: False
    })()

    # 创建模拟的 Request 对象
    from starlette.requests import Request
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/protected',
        'query_string': b'',
        'headers': [],
        'server': ('localhost', 8000),
        'scheme': 'http',
        'root_path': '',
    }

    async def test_async():
        # 创建 Request 对象
        request = Request(scope)

        # 创建 RedirectException（模拟 __begin__ 中抛出的异常）
        exception = RedirectException('/login')

        # 调用 _handle_exception 方法
        response = await dispatcher._handle_exception(request, exception)

        # 验证返回的是重定向响应
        from starlette.responses import RedirectResponse
        assert isinstance(response, RedirectResponse)

        # 验证状态码是 302
        assert response.status_code == 302

        # 验证 Location 头指向 /login
        assert response.headers['location'] == '/login'

        return response

    # 运行异步测试
    response = asyncio.run(test_async())

    # 再次验证（同步验证）
    assert response.status_code == 302
    assert response.headers['location'] == '/login'


def test_redirect_exception_in_begin_hook_simulation():
    """
    测试模拟 __begin__ 钩子抛出 RedirectException 的完整流程
    """
    import asyncio
    from uliweb.core.SimpleFrame import RedirectException, AsyncDispatcher, Request

    # 创建最小化的 Dispatcher
    dispatcher = AsyncDispatcher(
        apps_dir='apps',
        project_dir=None,
        start=False
    )

    # 设置必要的属性
    dispatcher.settings = type('MockSettings', (), {
        'GLOBAL': type('MockGlobal', (), {
            'DEBUG': False,
            'DEFAULT_CORS': False,
            'ERROR_PAGE': 'error.html'
        })(),
        'get_var': lambda self, key, default=None: False
    })()

    dispatcher._initialized = True

    # 创建模拟请求
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/protected/resource',
        'query_string': b'',
        'headers': [],
        'server': ('localhost', 8000),
        'scheme': 'http',
        'root_path': '',
    }

    async def test_flow():
        request = Request(scope)

        # 模拟 __begin__ 钩子中检查访问权限并抛出 RedirectException
        # 这模拟了生产环境中的场景：
        # functions.check_access() -> raise RedirectException(get_login_url())
        login_url = '/login?next=/protected/resource'
        exception = RedirectException(login_url)

        # 通过 _handle_exception 处理异常
        response = await dispatcher._handle_exception(request, exception)

        return response

    # 运行测试
    response = asyncio.run(test_flow())

    # 验证重定向响应正确
    from starlette.responses import RedirectResponse
    assert isinstance(response, RedirectResponse)
    assert response.status_code == 302
    assert '/login' in response.headers['location']
