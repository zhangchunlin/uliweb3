import pytest
from uliweb import functions
from uliweb.contrib.auth.middle_auth import AuthMiddle
from uliweb.core.SimpleFrame import AsyncDispatcher, Response


class MockUser:
    def __init__(self, username):
        self.username = username
        self.id = 123


class MockRequest:
    def __init__(self, scope=None):
        self.scope = scope or {}
        self.user = None


@pytest.mark.anyio
async def test_auth_middle_syncs_user_to_scope(monkeypatch):
    # 使用 functions 内部对象字典进行 monkeypatch，无需修改 Finder 核心类
    monkeypatch.setitem(functions._Finder__objects, "get_auth_user", lambda: MockUser("tangjn1"))
    monkeypatch.setitem(functions._Finder__objects, "update_user_session_expiry_time", lambda: None)

    auth_middle = AuthMiddle(None, None)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
    }
    req = MockRequest(scope)

    captured_scope_user_during_call = None

    async def call_next(request):
        nonlocal captured_scope_user_during_call
        captured_scope_user_during_call = request.scope.get("user")
        return "response_ok"

    res = await auth_middle.dispatch(req, call_next)

    assert res == "response_ok"
    assert req.user is not None
    assert req.user.username == "tangjn1"
    assert req.scope.get("user") is not None
    assert req.scope["user"].username == "tangjn1"
    assert captured_scope_user_during_call is not None
    assert captured_scope_user_during_call.username == "tangjn1"


@pytest.mark.anyio
async def test_call_next_propagates_scope_keys_on_success_and_error():
    dispatcher = AsyncDispatcher.__new__(AsyncDispatcher)

    # 1. 正常路径下传播 PROPAGATED_SCOPE_KEYS
    class DummyMiddlewareSuccess:
        async def dispatch(self, req, call_next):
            return await call_next(req)

    async def inner_app_success(scope, receive, send):
        scope["user"] = MockUser("inner_user")
        scope["auth"] = "inner_auth"
        scope["session"] = {"token": "123"}
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped_success = dispatcher._wrap_advanced_middleware(DummyMiddlewareSuccess(), inner_app_success)
    parent_scope = {"type": "http", "method": "GET", "path": "/"}

    async def fake_receive():
        return {"type": "http.request"}

    async def fake_send(msg):
        pass

    await wrapped_success(parent_scope, fake_receive, fake_send)

    assert parent_scope.get("user") is not None
    assert parent_scope["user"].username == "inner_user"
    assert parent_scope.get("auth") == "inner_auth"
    assert parent_scope.get("session") == {"token": "123"}

    # 2. 异常路径下 finally 块依然传播内层已变更的 scope 状态
    class DummyMiddlewareError:
        async def dispatch(self, req, call_next):
            return await call_next(req)

    async def inner_app_error(scope, receive, send):
        scope["user"] = MockUser("errored_user")
        raise RuntimeError("Inner app crashed")

    wrapped_error = dispatcher._wrap_advanced_middleware(DummyMiddlewareError(), inner_app_error)
    parent_scope_error = {"type": "http", "method": "GET", "path": "/"}

    with pytest.raises(RuntimeError):
        await wrapped_error(parent_scope_error, fake_receive, fake_send)

    assert parent_scope_error.get("user") is not None
    assert parent_scope_error["user"].username == "errored_user"
