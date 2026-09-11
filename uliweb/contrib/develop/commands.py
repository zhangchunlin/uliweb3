# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

import os
import json
import asyncio
import inspect
import logging
from optparse import make_option

from uliweb.core.commands import Command


class AppsInfoCommand(Command):
    name = 'appsinfo'
    help = 'Display information about installed apps.'
    check_apps_dirs = True

    def handle(self, options, global_options, *args):
        from uliweb import application

        # 确保应用已初始化
        self.get_application(global_options)

        apps = application.apps
        print("\n=== Installed Apps ===")
        print("Total: %d apps" % len(apps))
        for app in apps:
            print("  - %s" % app)
        print()


class UrlsCommand(Command):
    name = 'urls'
    help = 'Display all registered URL routes.'
    check_apps_dirs = True
    option_list = (
        make_option('-p', '--pattern', dest='pattern', default='',
                    help='Filter URLs by pattern (supports wildcards).'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import application

        # 确保应用已初始化
        self.get_application(global_options)

        router = application.router
        urls = []
        for r in router.routes:
            rule = r.path if hasattr(r, 'path') else str(r)
            methods = ', '.join(r.methods) if hasattr(r, 'methods') and r.methods else 'GET'
            # 获取 endpoint 的完整路径
            endpoint = self._get_endpoint(r)
            urls.append((rule, methods, endpoint))

        urls.sort()

        # 过滤模式
        if options.pattern:
            import fnmatch
            urls = [u for u in urls if fnmatch.fnmatch(u[0], options.pattern)]

        print("\n=== Registered URLs ===")
        print("Total: %d routes" % len(urls))
        print()
        print("%-50s %-15s %s" % ("URL", "Methods", "Endpoint"))
        print("-" * 80)
        for rule, methods, endpoint in urls:
            print("%-50s %-15s %s" % (rule, methods, endpoint))
        print()

    def _get_endpoint(self, route):
        """获取 endpoint 的完整路径"""
        # 获取 endpoint 属性（优先）
        endpoint = getattr(route, 'endpoint', None)
        if endpoint:
            # 如果 endpoint 是字符串，直接返回
            if isinstance(endpoint, str):
                return endpoint
            # 如果 endpoint 是函数，获取其完整路径
            if callable(endpoint):
                if hasattr(endpoint, '__module__') and hasattr(endpoint, '__qualname__'):
                    return endpoint.__module__ + '.' + endpoint.__qualname__
                elif hasattr(endpoint, '__name__'):
                    return endpoint.__name__
            return str(endpoint)

        # 备用：获取 name
        if hasattr(route, 'name') and route.name:
            return route.name

        return ''


class SettingsCommand(Command):
    name = 'settings'
    help = 'Display global settings and configuration.'
    check_apps_dirs = True
    option_list = (
        make_option('-s', '--section', dest='section', default='',
                    help='Display specific section (e.g., GLOBAL, MIDDLEWARES).'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import settings

        # 确保应用已初始化
        self.get_application(global_options)

        print("\n=== Global Settings ===")
        print()

        if options.section:
            # 显示特定 section
            section_name = options.section.upper()
            if hasattr(settings, section_name):
                section = getattr(settings, section_name)
                print("[%s]" % section_name)
                for key in dir(section):
                    if not key.startswith('_'):
                        try:
                            value = getattr(section, key)
                            if not callable(value):
                                print("  %s = %s" % (key, value))
                        except Exception:
                            pass
            else:
                print("Section [%s] not found!" % section_name)
        else:
            # 显示所有 section
            for section_name in dir(settings):
                if not section_name.startswith('_'):
                    section = getattr(settings, section_name, None)
                    if section and not callable(section):
                        print("[%s]" % section_name)
                        for key in dir(section):
                            if not key.startswith('_'):
                                try:
                                    value = getattr(section, key)
                                    if not callable(value):
                                        print("  %s = %s" % (key, value))
                                except Exception:
                                    pass
                        print()


class MiddlewaresCommand(Command):
    name = 'middlewares'
    help = 'Display all registered middlewares.'
    check_apps_dirs = True

    def handle(self, options, global_options, *args):
        from uliweb import application

        # 确保应用已初始化
        self.get_application(global_options)

        print("\n=== Registered Middlewares ===")

        # 获取中间件实例列表
        middlewares = getattr(application, 'middlewares', [])
        if not middlewares:
            print("No middlewares registered.")
            return

        print("Total: %d middlewares" % len(middlewares))
        print()

        for i, middleware in enumerate(middlewares, 1):
            middleware_name = middleware.__class__.__name__
            middleware_module = middleware.__class__.__module__
            print("  %d. %s (%s)" % (i, middleware_name, middleware_module))
            # 显示中间件属性（排除私有属性）
            attrs = [a for a in dir(middleware) if not a.startswith('_') and not callable(getattr(middleware, a))]
            if attrs:
                for attr in attrs[:5]:  # 最多显示5个属性
                    try:
                        value = getattr(middleware, attr)
                        if len(str(value)) > 50:
                            value = str(value)[:50] + '...'
                        print("     - %s = %s" % (attr, value))
                    except Exception:
                        pass
        print()


# =====================================================================
# 面向 coding agent 的调试命令行工具
# 全部为只读：只查询框架内部结构，不改变行为契约。
# 前提：GLOBAL.DEBUG 且 GLOBAL.AUTO_DEVELOP 为真时 develop 自动启用。
# =====================================================================

def _safe(v):
    """把任意值转成可打印/可 JSON 化的对象。"""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _safe(x) for k, x in v.items()}
    if hasattr(v, 'items'):
        return {str(k): _safe(x) for k, x in v.items()}
    return str(v)


def _print_json(obj):
    print(json.dumps(_safe(obj), ensure_ascii=False, indent=2, default=str))


def _view_location(application, endpoint):
    """由 endpoint 解析出视图的 (klass, mod, handler) 及 file:line。"""
    _klass = None
    mod = None
    handler = None
    try:
        _klass, mod, handler = application.get_handler(endpoint)
    except Exception as e:
        return None, None, None, '(%s)' % e
    loc = ''
    try:
        loc = "%s:%d" % (inspect.getsourcefile(handler), inspect.getsourcelines(handler)[1])
    except (TypeError, OSError):
        loc = getattr(handler, '__module__', '') + '.' + getattr(handler, '__name__', '')
    return _klass, mod, handler, loc


class RouteCommand(Command):
    """匹配一个 URL 到 endpoint，用于 404 排查与路由定位。"""
    name = 'route'
    help = 'Match a URL path to a registered endpoint (for 404 debugging).'
    args = '<path>'
    check_apps_dirs = True
    option_list = (
        make_option('--method', dest='method', default='GET',
                    help='HTTP method (default GET).'),
        make_option('--json', dest='json', action='store_true', default=False,
                    help='Output as JSON.'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import application
        from starlette.routing import Match

        self.get_application(global_options)

        if not args:
            print("Error: path is required. Usage: uliweb route <path> [--method METHOD]")
            return
        path = args[0]
        method = (options.method or 'GET').upper()
        # 分离 query string
        if '?' in path:
            path, qs = path.split('?', 1)
        else:
            qs = ''

        scope = {
            'type': 'http',
            'method': method,
            'path': path,
            'query_string': qs.encode(),
            'root_path': '',
            'headers': [],
            'scheme': 'http',
            'server': ('test', 80),
            'client': ('test', 80),
        }

        full = []
        partial = []  # path 匹配但 method 不匹配
        for r in application.router.routes:
            route_path = getattr(r, 'path', str(r))
            try:
                match, child = r.matches(scope)
            except Exception:
                continue
            if match == Match.FULL:
                params = dict(child.get('path_params', {}))
                _klass, mod, handler, loc = _view_location(application, getattr(r, 'endpoint', ''))
                full.append({
                    'path': route_path,
                    'methods': sorted(getattr(r, 'methods', None) or ['*']),
                    'endpoint': getattr(r, 'endpoint', ''),
                    'view': loc,
                    'params': params,
                })
            elif match == Match.PARTIAL:
                partial.append(route_path)

        if options.json:
            _print_json({'url': path, 'method': method,
                         'matched': full, 'method_mismatch': partial,
                         'total_routes': len(application.router.routes)})
            return

        print("\n=== Route Match: %s %s ===" % (method, path))
        if full:
            for f in full:
                print("  MATCHED: %s" % f['path'])
                print("    endpoint : %s" % f['endpoint'])
                print("    view     : %s" % f['view'])
                print("    methods  : %s" % ', '.join(f['methods']))
                print("    params   : %s" % (f['params'] or '{}'))
        else:
            print("  NO FULL MATCH")
            if partial:
                print("  Method mismatch (path matches, method not allowed):")
                for p in partial:
                    print("    - %s" % p)
        print("  (total %d routes)" % len(application.router.routes))
        print()


class UrlForCommand(Command):
    """反向 URL：给定 endpoint 名生成 URL。"""
    name = 'urlfor'
    help = 'Reverse URL lookup: generate a URL from an endpoint name.'
    args = '<endpoint> [key=value ...]'
    check_apps_dirs = True
    option_list = (
        make_option('--json', dest='json', action='store_true', default=False,
                    help='Output as JSON.'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import url_for

        self.get_application(global_options)

        if not args:
            print("Error: endpoint is required. Usage: uliweb urlfor <endpoint> [key=value ...]")
            return

        endpoint = args[0]
        values = {}
        for a in args[1:]:
            if '=' in a:
                k, v = a.split('=', 1)
                values[k] = v

        try:
            url = url_for(endpoint, **values)
        except Exception as e:
            if options.json:
                _print_json({'endpoint': endpoint, 'error': str(e)})
            else:
                print("\n=== URL For: %s ===" % endpoint)
                print("  ERROR: %s" % e)
                print("  Hint: run `uliweb urls` to list registered endpoints.")
            return

        if options.json:
            _print_json({'endpoint': endpoint, 'url': url, 'values': values})
        else:
            print("\n=== URL For: %s ===" % endpoint)
            print("  url : %s" % url)
            if values:
                print("  args: %s" % values)
            print()


class RequestCommand(Command):
    """进程内发真实 ASGI 请求，触发懒加载并打印完整响应。"""
    name = 'request'
    help = 'Fire an in-process ASGI request and print the response (triggers lazy init).'
    args = '<path>'
    check_apps_dirs = True
    option_list = (
        make_option('--method', dest='method', default='GET',
                    help='HTTP method (default GET).'),
        make_option('--data', dest='data', default='',
                    help='Form body (a=1&b=2).'),
        make_option('--json', dest='json_data', default=None,
                    help='JSON body string.'),
        make_option('--header', dest='headers', default=[], action='append',
                    help='Extra header, e.g. --header "X-Token: abc" (repeatable).'),
        make_option('--follow', dest='follow', action='store_true', default=False,
                    help='Follow redirects.'),
        make_option('--out', dest='out', default='',
                    help='Print as JSON instead of aligned text.'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import application
        from uliweb.core.SimpleFrame import url_for

        # 压掉 httpx 的请求 INFO 日志，保持输出干净
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)

        self.get_application(global_options)

        if not args:
            print("Error: path is required. Usage: uliweb request <path> [options]")
            return
        path = args[0]
        method = (options.method or 'GET').upper()

        headers = []
        for h in options.headers or []:
            if ':' in h:
                k, v = h.split(':', 1)
                headers.append((k.strip(), v.strip()))

        async def _run():
            import time
            import httpx
            transport = httpx.ASGITransport(app=application)
            async with httpx.AsyncClient(transport=transport, base_url='http://test',
                                         follow_redirects=options.follow) as client:
                kwargs = {'method': method, 'url': path, 'headers': headers}
                if options.json_data is not None:
                    kwargs['json'] = json.loads(options.json_data)
                elif options.data:
                    kwargs['data'] = options.data
                start = time.monotonic()
                resp = await client.request(**kwargs)
                elapsed = time.monotonic() - start
                return resp, elapsed

        resp, elapsed = asyncio.run(_run())

        result = {
            'status': resp.status_code,
            'elapsed': round(elapsed, 4),
            'url': str(resp.url),
            'headers': dict(resp.headers),
            'body': resp.text,
        }
        # 命中路由
        try:
            from starlette.routing import Match
            scope = {'type': 'http', 'method': method, 'path': path.split('?')[0],
                     'query_string': (path.split('?')[1] if '?' in path else '').encode(),
                     'root_path': '', 'headers': [], 'scheme': 'http',
                     'server': ('test', 80), 'client': ('test', 80)}
            for r in application.router.routes:
                m, child = r.matches(scope)
                if m == Match.FULL:
                    result['route'] = {'path': getattr(r, 'path', ''),
                                       'endpoint': getattr(r, 'endpoint', ''),
                                       'params': dict(child.get('path_params', {}))}
                    break
        except Exception:
            pass

        if options.out == 'json':
            _print_json(result)
            return

        print("\n=== Request: %s %s ===" % (method, path))
        print("  status : %s" % result['status'])
        print("  time   : %.4fs" % result['elapsed'])
        if result.get('route'):
            rt = result['route']
            print("  route  : %s -> %s %s" % (rt['path'], rt['endpoint'], rt['params'] or ''))
        print("  headers:")
        for k, v in (dict(resp.headers).items()):
            print("    %s: %s" % (k, v))
        print("  body:")
        print("    %s" % (resp.text[:2000] + ('...' if len(resp.text) > 2000 else '')))
        print()


class InspectCommand(Command):
    """查看视图源码位置、async 与否、签名、默认模板。"""
    name = 'inspect'
    help = 'Inspect a view endpoint: source location, async-ness, signature, template.'
    args = '<endpoint>'
    check_apps_dirs = True
    option_list = (
        make_option('--json', dest='json', action='store_true', default=False,
                    help='Output as JSON.'),
    )

    def handle(self, options, global_options, *args):
        from uliweb import application
        from uliweb.core.SimpleFrame import settings
        from inspect import iscoroutinefunction, isasyncgenfunction

        self.get_application(global_options)

        if not args:
            print("Error: endpoint is required. Usage: uliweb inspect <endpoint>")
            return
        endpoint = args[0]

        _klass, mod, handler, loc = _view_location(application, endpoint)
        if handler is None or str(loc).startswith('('):
            if options.json:
                _print_json({'endpoint': endpoint, 'error': str(loc)})
            else:
                print("\n=== Inspect: %s ===" % endpoint)
                print("  ERROR: cannot resolve endpoint: %s" % loc)
            return

        info = {
            'endpoint': endpoint,
            'file': None,
            'line': None,
            'async': iscoroutinefunction(handler) or isasyncgenfunction(handler),
            'class': bool(_klass),
        }
        try:
            info['file'], info['line'] = inspect.getsourcefile(handler), inspect.getsourcelines(handler)[1]
        except (TypeError, OSError):
            pass
        try:
            sig = inspect.signature(handler)
            info['signature'] = str(sig)
        except (TypeError, ValueError):
            info['signature'] = ''
        try:
            doc = inspect.getdoc(handler)
            info['doc'] = doc.split('\n')[0] if doc else ''
        except Exception:
            info['doc'] = ''

        # 约定默认模板：函数视图 templates/<fn>.html；类视图 templates/<Class>/<method>.html
        try:
            if _klass:
                info['template'] = 'templates/%s/%s%s' % (
                    _klass.__class__.__name__, handler.__name__,
                    settings.GLOBAL.get('TEMPLATE_SUFFIX', '.html'))
            else:
                info['template'] = 'templates/%s%s' % (
                    handler.__name__, settings.GLOBAL.get('TEMPLATE_SUFFIX', '.html'))
        except Exception:
            info['template'] = ''

        if options.json:
            _print_json(info)
            return

        print("\n=== Inspect: %s ===" % endpoint)
        print("  file     : %s" % info['file'])
        print("  line     : %s" % info['line'])
        print("  async    : %s" % info['async'])
        print("  signature: %s" % info['signature'])
        print("  doc      : %s" % info['doc'])
        print("  template : %s" % info['template'])
        print()


class BodyParseCommand(Command):
    """调试异步 body 解析：展示同一 raw body 下各 getter 的返回值。"""
    name = 'body'
    help = 'Show how a raw request body parses via get_POST/get_json/get_params/etc.'
    args = '<content-type> <raw-body>'
    check_apps_dirs = True
    option_list = (
        make_option('--method', dest='method', default='POST',
                    help='HTTP method (default POST).'),
        make_option('--json', dest='json', action='store_true', default=False,
                    help='Output as JSON.'),
    )

    def _make_request(self, method, content_type, raw_body):
        from uliweb.core.SimpleFrame import Request
        body = raw_body.encode('utf-8')
        scope = {
            'type': 'http',
            'method': method.upper(),
            'path': '/',
            'query_string': b'',
            'root_path': '',
            'headers': [
                (b'content-type', content_type.encode('latin-1', 'replace')),
                (b'content-length', str(len(body)).encode()),
            ],
            'scheme': 'http',
            'server': ('test', 80),
            'client': ('test', 80),
        }
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return Request(scope, receive, None)

    def handle(self, options, global_options, *args):
        if not args:
            print("Error: content-type and raw body required. "
                  "Usage: uliweb body <content-type> '<raw-body>'")
            return
        content_type = args[0]
        raw_body = ' '.join(args[1:]) if len(args) > 1 else ''
        method = (options.method or 'POST').upper()

        request = self._make_request(method, content_type, raw_body)

        async def _run():
            out = {}
            for name in ('get_data', 'get_POST', 'get_FILES', 'get_json', 'get_params'):
                try:
                    val = await getattr(request, name)()
                    out[name] = _safe(val)
                except Exception as e:
                    out[name] = {'error': type(e).__name__ + ': ' + str(e)}
            return out

        out = asyncio.run(_run())

        if options.json:
            _print_json({'method': method, 'content_type': content_type,
                         'body': raw_body, 'result': out})
            return

        print("\n=== Body Parse: %s %s ===" % (method, content_type))
        print("  body : %s" % raw_body)
        for name in ('get_data', 'get_POST', 'get_FILES', 'get_json', 'get_params'):
            print("  %-12s: %s" % (name, json.dumps(out[name], ensure_ascii=False, default=str)))
        print()
