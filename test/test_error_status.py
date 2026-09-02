"""
测试 error() 的 status 参数在 ASGI 下的语义修正

背景：ASGI 迁移中 error() 的 status 参数曾失效（_error 硬编码 500，
_handle_exception 对 HTTPError 硬编码 403）。本测试验证：
- 视图 error(msg, status=400/403) 返回对应状态码
- error(msg) 未传 status 默认 500
- 抛 HTTPError 被 _handle_exception 捕获时按 errors['status'] 返回（默认 403）
"""
import asyncio
import sys
import tempfile
import shutil
from pathlib import Path

from uliweb.core import rules
from uliweb.core.SimpleFrame import __app_dirs__, __app_alias__


def cleanup_rules():
    rules.__exposes__.clear()
    rules.__url_names__.clear()
    rules.__no_need_exposed__[:] = []
    __app_dirs__.clear()
    __app_alias__.clear()
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('testerr')]
    for mod in modules_to_remove:
        del sys.modules[mod]


def create_temp_project():
    tmpdir = tempfile.mkdtemp()
    project_dir = Path(tmpdir)
    apps_dir = project_dir / 'apps'
    apps_dir.mkdir()

    settings_ini = apps_dir / 'settings.ini'
    settings_ini.write_text("""
[GLOBAL]
DEBUG = True
SECRET_KEY = "test-secret-key"
INSTALLED_APPS = [
    "testerr",
]
""")

    app_dir = apps_dir / 'testerr'
    app_dir.mkdir()
    (app_dir / '__init__.py').write_text('')
    (app_dir / 'views.py').write_text('''
from uliweb import expose, error
from uliweb.core.SimpleFrame import HTTPError

@expose("/err/400")
def err_400():
    error("bad request", status=400)

@expose("/err/403")
def err_403():
    error("forbidden", status=403)

@expose("/err/404")
def err_404():
    error("not found", status=404)

@expose("/err/default")
def err_default():
    error("server error")

@expose("/err/raise")
def err_raise():
    raise HTTPError(errorpage='error.html', message="no access", status=401)
''')

    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    return project_dir, apps_dir, app_dir


def cleanup_temp_project(project_dir):
    try:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))
    except ValueError:
        pass
    finally:
        shutil.rmtree(str(project_dir), ignore_errors=True)


def make_request(dispatcher, path):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [],
        "root_path": "",
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
    }

    received = []

    async def mock_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def mock_send(message):
        received.append(message)

    asyncio.run(dispatcher(scope, mock_receive, mock_send))
    return received


def get_status(received):
    for message in received:
        if message["type"] == "http.response.start":
            return message["status"]
    return None


class TestErrorStatus:
    def setUp(self):
        cleanup_rules()
        self.project_dir, self.apps_dir, self.app_dir = create_temp_project()
        from uliweb.core.SimpleFrame import AsyncDispatcher
        self.dispatcher = AsyncDispatcher(
            apps_dir='apps',
            project_dir=str(self.project_dir),
            start=False
        )
        self.dispatcher.apps = ['testerr']
        self.dispatcher.prepare()

    def tearDown(self):
        cleanup_rules()
        cleanup_temp_project(self.project_dir)

    setup_method = setUp
    teardown_method = tearDown

    def test_error_status_400(self):
        received = make_request(self.dispatcher, '/err/400')
        assert get_status(received) == 400

    def test_error_status_403(self):
        received = make_request(self.dispatcher, '/err/403')
        assert get_status(received) == 403

    def test_error_status_404(self):
        received = make_request(self.dispatcher, '/err/404')
        assert get_status(received) == 404

    def test_error_default_status_500(self):
        received = make_request(self.dispatcher, '/err/default')
        assert get_status(received) == 500

    def test_http_error_status_from_errors(self):
        received = make_request(self.dispatcher, '/err/raise')
        assert get_status(received) == 401
