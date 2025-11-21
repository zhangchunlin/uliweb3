from __future__ import print_function, absolute_import, unicode_literals
import os
import sys
import uliweb
from ._compat import callable, string_types, integer_types

lib_path = os.path.join(uliweb.__path__[0], 'lib')
sys.path.insert(0, lib_path)


def get_app(project_path='.', settings_file='settings.ini', local_settings_file='local_settings.ini'):
    from uliweb.manage import make_simple_application

    app = make_simple_application(
        project_dir=project_path,
        settings_file=settings_file,
        local_settings_file=local_settings_file
    )
    return app


def client(project_path='.', settings_file='settings.ini', local_settings_file='local_settings.ini'):
    from starlette.testclient import TestClient
    from uliweb.core.starlette import ASGIApplication

    # 创建 ASGI 应用
    app = ASGIApplication(project_dir=project_path)

    # 创建测试客户端
    c = TestClient(app)
    c.app = app

    # 添加 test_url 方法
    setattr(TestClient, 'test_url', test_url)

    return c


def client_from_application(app):
    from starlette.testclient import TestClient

    # 创建测试客户端
    c = TestClient(app)
    c.app = app

    # 添加 test_url 方法
    setattr(TestClient, 'test_url', test_url)

    return c


def BlankRequest(url, **kwargs):
    from uliweb.core.starlette import Request
    from urllib.parse import urlparse

    # 解析 URL 以提取路径和查询字符串
    parsed_url = urlparse(url)
    path = parsed_url.path
    query_string = parsed_url.query.encode('utf-8') if parsed_url.query else b''

    # 创建 ASGI scope
    scope = {
        'type': 'http',
        'method': kwargs.get('method', 'GET'),
        'path': path,
        'query_string': kwargs.get('query_string', query_string),
        'headers': kwargs.get('headers', []),
    }

    # 创建 mock receive 和 send 函数
    async def receive():
        return {'type': 'http.request', 'body': kwargs.get('body', b''), 'more_body': False}

    async def send(message):
        pass

    # 创建请求对象
    return Request(scope, receive, send)


def test_url(self, url, data=None, method='get', ok_test=(200, 304, 302), log=True, counter=None):
    """
    Test if an url is ok
    ok_test can be tuple: it should be status_code list
        callable: then return true will be ok
    """
    if data is None:
        data = {}
    func = getattr(self, method.lower())

    # 根据 HTTP 方法不同，使用不同的参数传递方式
    if method.lower() == 'get':
        r = func(url, params=data)
    else:
        r = func(url, data=data)

    result = False
    if isinstance(ok_test, (list, tuple)):
        result = r.status_code in ok_test
    # int,long will be treated as status code
    elif isinstance(ok_test, integer_types):
        result = r.status_code == ok_test
    # str,unicode will be treated as text
    elif isinstance(ok_test, string_types):
        # 对于 Starlette，需要使用 text 属性而不是 data
        result = ok_test in r.text
    elif callable(ok_test):
        # 对于 Starlette，需要使用 text 属性而不是 data
        result = ok_test(url, data, method, r.status_code, r.text)

    if counter:
        counter.add(result)

    flag = 'OK' if result else 'Failed'
    log_func = None
    if callable(log):
        log_func = log
    elif log is True:
        log_func = log_to_file(sys.stdout)
    elif isinstance(log, string_types):
        log_func = log_to_file(log)
    if log_func:
        log_func(url, data, method, ok_test, result, r)
    return result


def default_log(url, data, method, ok_test, result, response):
    print('Testing %s...%s' % (url, 'OK' if result else 'Failed'))


def log_to_file(logfile, response_text=False):
    if isinstance(logfile, string_types):
        log = open(logfile, 'a')
    else:
        log = logfile

    def _log(url, data, method, ok_test, result, response):
        flag = 'OK' if result else 'Failed'
        log.write('Testing %s...%s\n' % (url, flag))
        if not result:
            log.write('    ok_test = %s\n' % ok_test)
            log.write('    Response code=%d\n' % response.status_code)
            if response_text:
                log.write('----------------- Response Text -----------------\n')
                # 对于 Starlette，需要使用 text 属性而不是 data
                log.write(response.text)
                log.write('================= Response Text =================\n')

    return _log


class Counter(object):
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0

    def add(self, passed=True):
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.total += 1
