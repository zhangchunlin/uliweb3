"""
回归测试：async/sync 视图并发下 request/response 不得跨请求串扰

背景（sdlc/request-view-env-global-leak）：
框架 _call_function 会把 view env 写进视图模块的共享全局（handler.__globals__.update(env)）。
修复前 get_view_env 注入的是"每请求的 Request/Response 对象"，导致并发下 views.py.request
被各请求反复覆盖 -> async 视图 await 后读到别的请求的数据（~50% 串扰）。

修复：get_view_env / get_view_env_sync 改为注入稳定的 LocalProxy 代理（contextvar 隔离）。
本测试作为该 bug 的回归护栏，修复前应失败、修复后通过。
"""
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

import httpx
import pytest

from uliweb.utils.test_server import TestServer

VIEWS = '''
import asyncio
import time
from uliweb import expose, json, request


@expose('/asyncview')
class AsyncView:
    def __begin__(self, request):
        self.can_list_all = request.GET.get('user')
        self.owner = request.GET.get('user')

    @expose('api')
    async def api(self):
        await asyncio.sleep(0.05)
        return json({
            "can": self.can_list_all,
            "owner": self.owner,
            "cur": request.GET.get('user'),
        })


@expose('/syncview')
class SyncView:
    def __begin__(self, request):
        self.can_list_all = request.GET.get('user')
        self.owner = request.GET.get('user')

    @expose('api')
    def api(self):
        time.sleep(0.02)
        return json({
            "can": self.can_list_all,
            "owner": self.owner,
            "cur": request.GET.get('user'),
        })


@expose('/noimport')
class NoImport:
    @expose('api')
    async def api(self):
        # 故意不 from uliweb import request，纯靠框架注入模块全局
        q0 = request.GET.get('user')
        await asyncio.sleep(0.05)
        q1 = request.GET.get('user')
        return json({"start": q0, "end": q1})
'''


def create_temp_project():
    """创建临时测试项目（结构对齐 test_async_dispatcher.create_temp_project）"""
    project_dir = Path(tempfile.mkdtemp(prefix='test_view_req_'))
    apps_dir = project_dir / 'apps'
    apps_dir.mkdir()

    (apps_dir / 'settings.ini').write_text("""
[GLOBAL]
DEBUG = False
INSTALLED_APPS = [
    "testapp",
]
""")

    app_dir = apps_dir / 'testapp'
    app_dir.mkdir()
    (app_dir / '__init__.py').write_text('')
    (app_dir / 'views.py').write_text(VIEWS)

    for p in (str(project_dir), str(apps_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)

    return project_dir


def cleanup_temp_project(project_dir):
    for p in (str(project_dir), str(project_dir / 'apps')):
        try:
            sys.path.remove(p)
        except ValueError:
            pass
    shutil.rmtree(str(project_dir), ignore_errors=True)


async def _assert_no_crosstalk(base_url, path, n=16):
    """并发 n 个请求各带不同 user，断言每个响应都等于本请求的 user（串扰 = 0）"""
    async with httpx.AsyncClient() as client:

        async def one(i):
            r = await client.get(f"{base_url}{path}", params={"user": f"U{i}"})
            return i, r.json()

        results = await asyncio.gather(*(one(i) for i in range(n)))

    mismatches = [
        (i, body) for i, body in results
        if any(v != f"U{i}" for v in body.values())
    ]
    assert not mismatches, f"cross-talk detected (n={n}): {mismatches}"


def test_view_request_no_crosstalk():
    project_dir = create_temp_project()
    try:
        with TestServer(project_dir=str(project_dir), apps_dir='apps') as server:
            asyncio.run(_assert_no_crosstalk(server.base_url, '/asyncview/api'))
            asyncio.run(_assert_no_crosstalk(server.base_url, '/syncview/api'))
            asyncio.run(_assert_no_crosstalk(server.base_url, '/noimport/api'))
    finally:
        cleanup_temp_project(project_dir)


if __name__ == '__main__':
    test_view_request_no_crosstalk()