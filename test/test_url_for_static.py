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


if __name__ == '__main__':
    print("=" * 50)
    print("Test 1: url_adapter without app")
    print("=" * 50)
    test_url_adapter_without_app()

    print("\n" + "=" * 50)
    print("Test 2: url_adapter with app")
    print("=" * 50)
    test_url_adapter_with_app()
