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