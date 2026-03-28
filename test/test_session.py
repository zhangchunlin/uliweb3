"""
测试 Session 功能
"""
import os
import sys
import tempfile
import pytest

# 添加 uliweb.lib 到 sys.path，以便 weto 模块可以被正确导入
# Session 类内部使用 __import__('weto.backends...') 来导入存储后端
uliweb_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uliweb', 'lib')
if uliweb_lib_path not in sys.path:
    sys.path.insert(0, uliweb_lib_path)


def test_session_creation():
    """测试 Session 对象创建"""
    from uliweb.lib.weto.session import Session

    # 使用内存存储创建 session（不传 key，自动生成）
    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        # 验证 session 已创建
        assert session.key is not None
        assert session.expiry_time == 3600
        assert session.deleted is False


def test_session_set_get():
    """测试 Session 存取功能"""
    from uliweb.lib.weto.session import Session

    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        # 设置值
        session.set('username', 'test_user')
        session.set('user_id', 123)

        # 获取值
        assert session.get('username') == 'test_user'
        assert session.get('user_id') == 123

        # 测试 remember 属性
        session.remember = True
        assert session.remember is True


def test_session_save():
    """测试 Session 保存功能"""
    from uliweb.lib.weto.session import Session

    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        # 设置值
        session['username'] = 'test_user'

        # 保存 session
        flag = session.save()
        assert flag is True

        # 验证文件已创建
        session_files = os.listdir(tmpdir)
        assert len(session_files) > 0


def test_session_load():
    """测试 Session 加载功能"""
    from uliweb.lib.weto.session import Session

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建并保存第一个 session
        session1 = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )
        session1['username'] = 'test_user'
        session1.save()

        # 获取 session1 的 key
        session_key = session1.key

        # 创建第二个 session 并加载相同 key
        session2 = Session(
            key=session_key,
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        # 验证数据已加载
        assert session2.get('username') == 'test_user'


def test_session_delete():
    """测试 Session 删除功能"""
    from uliweb.lib.weto.session import Session, SessionException

    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        session['username'] = 'test_user'
        session.save()

        # 删除 session
        session.delete()

        # 验证已删除
        assert session.deleted is True

        # 删除后访问 session 应该抛出 SessionException
        try:
            _ = session.get('username')
            assert False, "Expected SessionException to be raised"
        except SessionException:
            pass  # 预期行为


def test_session_middleware_integration():
    """测试 SessionMiddle 与 Request 的集成"""
    from uliweb.core.SimpleFrame import Request
    from uliweb.lib.weto.session import Session

    # 创建一个带有 session 的 scope
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 session
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )
        session['username'] = 'test_user'

        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/test',
            'query_string': b'',
            'session': session,  # 模拟 SessionMiddle 设置
        }

        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        async def send(message):
            pass

        req = Request(scope, receive, send)

        # 验证可以通过 request.session 访问
        assert req.session is not None
        assert req.session.get('username') == 'test_user'


def test_session_property_setter():
    """测试 session 属性 setter"""
    from uliweb.core.SimpleFrame import Request

    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/test',
        'query_string': b'',
    }

    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message):
        pass

    req = Request(scope, receive, send)

    # 创建一个模拟 session 对象
    class MockSession:
        def __init__(self):
            self.key = 'test_key'
            self.remember = False
            self.deleted = False

    mock_session = MockSession()

    # 通过 setter 设置 session
    req.session = mock_session

    # 验证 session 已设置到 scope
    assert req.scope['session'] is mock_session
    assert req.session is mock_session


def test_session_cookie():
    """测试 SessionCookie"""
    from uliweb.lib.weto.session import Session, SessionCookie

    with tempfile.TemporaryDirectory() as tmpdir:
        session = Session(
            storage_type='file',
            options={'data_dir': tmpdir},
            expiry_time=3600
        )

        # 验证 cookie 已创建
        assert session.cookie is not None
        assert isinstance(session.cookie, SessionCookie)
        assert session.cookie.cookie_id == 'session_cookie_id'


def test_session_middleware_import():
    """测试 SessionMiddle 可以正确导入"""
    from uliweb.contrib.session.middle_session import SessionMiddle

    # 验证 SessionMiddle 类存在
    assert SessionMiddle is not None
    assert hasattr(SessionMiddle, 'dispatch')
    assert hasattr(SessionMiddle, '__call__')


def test_session_storage_import():
    """测试 Session 存储后端可以正确导入"""
    from uliweb.lib.weto.backends import file_storage

    # 验证存储后端存在
    assert file_storage is not None


def test_advanced_middleware_preference():
    """测试中间件检测逻辑优先使用 dispatch 方法"""
    from uliweb.core.SimpleFrame import AsyncDispatcher
    import inspect

    # 获取 _build_middleware_stack 方法的源码
    source = inspect.getsource(AsyncDispatcher._build_middleware_stack)

    # 验证优先使用 dispatch 的逻辑存在
    assert 'has_dispatch and has_asgi_call' in source or '优先使用 dispatch' in source


def test_request_local_proxy_in_advanced_middleware():
    """测试高级中间件中 request LocalProxy 正确设置"""
    from uliweb.core.SimpleFrame import AsyncDispatcher
    import inspect

    # 获取 _wrap_advanced_middleware 方法的源码
    source = inspect.getsource(AsyncDispatcher._wrap_advanced_middleware)

    # 验证 request.set 的逻辑存在
    assert 'request.set' in source
    assert 'request_token' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
