"""
测试 url_for_static 函数

这个测试用例用于验证 url_for_static 生成正确的 URL。
"""
import pytest
import asyncio
import os
import sys

# 设置项目路径
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)


def test_url_adapter_with_app():
    """测试有 AsyncDispatcher 应用时的 url_adapter"""
    from uliweb.core.SimpleFrame import get_url_adapter
    from uliweb.core.SimpleFrame import AsyncDispatcher

    # 创建 AsyncDispatcher 实例（不自动启动）
    app = AsyncDispatcher(
        apps_dir='apps',
        project_dir=project_dir,
        start=False  # 不自动启动
    )

    # 设置到 contextvars 中
    from uliweb.core.context import application_var
    application_var.set(app)

    # 获取 'static' domain 的 adapter
    adapter = get_url_adapter('static')

    print(f"adapter type: {type(adapter)}")
    print(f"adapter: {adapter}")
    print(f"has build method: {hasattr(adapter, 'build')}")

    # 清理
    application_var.set(None)

    # 验证返回的是 AsyncDispatcher 的 router
    assert hasattr(adapter, 'build'), "Adapter should have build method"
    print("Test passed: get_url_adapter returns router with build method")


def test_url_adapter_without_app():
    """测试没有 AsyncDispatcher 应用时的 url_adapter"""
    from uliweb.core.SimpleFrame import get_url_adapter

    # 确保没有 application 在 contextvars 中
    from uliweb.core.context import application_var
    application_var.set(None)

    # 获取 'static' domain 的 adapter
    adapter = get_url_adapter('static')

    print(f"adapter type: {type(adapter)}")
    print(f"adapter: {adapter}")
    print(f"has build method: {hasattr(adapter, 'build')}")


def test_url_for_static():
    """测试 url_for_static 函数"""
    from uliweb.contrib.staticfiles import url_for_static
    from uliweb.core.SimpleFrame import AsyncDispatcher

    # 创建应用实例并调用 prepare() 加载 settings
    # 使用 test/testproject 目录
    test_project_dir = os.path.join(project_dir, 'test', 'testproject')
    app = AsyncDispatcher(
        apps_dir='apps',
        project_dir=test_project_dir,
        start=False
    )
    app.prepare()

    # 设置到全局和 contextvars 中
    from uliweb.core.SimpleFrame import __global__
    __global__.application = app

    from uliweb.core.context import application_var
    application_var.set(app)

    # 测试基本 URL 生成
    url = url_for_static('css/style.css')
    print(f"url_for_static('css/style.css') = {url}")
    assert url == '/static/css/style.css', f"Expected '/static/css/style.css', got '{url}'"

    # 测试带参数的 URL（当 STATIC_VER 为 None 时，ver 参数会被忽略）
    url = url_for_static('js/app.js', ver='1.0.0')
    print(f"url_for_static('js/app.js', ver='1.0.0') = {url}")
    # 由于 STATIC_VER 为 None，ver 参数会被忽略，但自定义参数会添加到查询字符串
    assert 'js/app.js' in url, f"Expected URL to contain 'js/app.js', got '{url}'"

    # 测试绝对路径（以 / 开头）
    url = url_for_static('/images/logo.png')
    print(f"url_for_static('/images/logo.png') = {url}")
    assert url == '/images/logo.png', f"Expected '/images/logo.png', got '{url}'"

    # 测试带域名的 URL
    url = url_for_static('css/style.css', _external=True)
    print(f"url_for_static('css/style.css', _external=True) = {url}")
    # 由于 domain 为空，_external=True 也不会添加域名
    assert 'css/style.css' in url, f"Expected URL to contain 'css/style.css', got '{url}'"

    # 清理
    application_var.set(None)
    __global__.application = None

    print("Test passed: url_for_static works correctly!")


if __name__ == '__main__':
    print("=" * 50)
    print("Test 1: url_adapter without app")
    print("=" * 50)
    test_url_adapter_without_app()

    print("\n" + "=" * 50)
    print("Test 2: url_adapter with app")
    print("=" * 50)
    test_url_adapter_with_app()

    print("\n" + "=" * 50)
    print("Test 3: url_for_static")
    print("=" * 50)
    test_url_for_static()
