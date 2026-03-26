# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals

from uliweb.core.commands import Command
from optparse import make_option


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
