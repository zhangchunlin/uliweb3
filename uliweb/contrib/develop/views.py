#coding=utf-8
from uliweb import expose
from .menu import bind_menu
import logging
from uliweb.utils.common import pkg, is_pyfile_exist

@expose('/develop')
async def develop_index():
    return {}

@expose('/develop/appsinfo')
async def develop_appsinfo():
    from uliweb import application
    return {'apps':application.apps}

@expose('/develop/urls')
async def develop_urls():
    from uliweb import application
    from uliweb.core import rules

    # 使用 rules.merge_rules() 而不是 application.router.routes
    # 因为 router.routes 可能包含重复的路由
    merged = rules.merge_rules()
    u = []
    for rule_info in merged:
        appname, endpoint, rule, kw = rule_info
        methods = ', '.join(kw.get('methods', ['GET']))
        u.append((rule, methods, endpoint))
    u.sort()

    # 添加调试日志，用于和 commands 里的 urls 做对比
    logger = logging.getLogger('uliweb')
    logger.info("=" * 80)
    logger.info("[develop/urls] Routes from rules.merge_rules():")
    logger.info("=" * 80)
    for i, (rule, methods, endpoint) in enumerate(u, 1):
        logger.info(f"  {i:3d}. {rule:<40} [{methods:<20}] -> {endpoint}")
    logger.info("-" * 80)
    logger.info(f"Total routes: {len(u)}")

    # 打印 __url_names__ 信息
    logger.info("")
    logger.info("=" * 80)
    logger.info("[develop/urls] rules.__url_names__ content:")
    logger.info("=" * 80)
    for name, endpoint in sorted(rules.__url_names__.items()):
        logger.info(f"  {name:<40} -> {endpoint}")
    logger.info("-" * 80)
    logger.info(f"Total url_names: {len(rules.__url_names__)}")

    # 打印 __exposes__ 信息
    logger.info("")
    logger.info("=" * 80)
    logger.info("[develop/urls] rules.__exposes__ content:")
    logger.info("=" * 80)
    # __exposes__ 的键是函数对象，无法排序，直接遍历
    for func, exposes in rules.__exposes__.items():
        func_path = getattr(func, '__module__', str(func)) + '.' + getattr(func, '__name__', str(func))
        logger.info(f"  Function: {func_path}")
        for expose_info in exposes:
            logger.info(f"    {expose_info}")
    logger.info("-" * 80)
    logger.info(f"Total apps with exposes: {len(rules.__exposes__)}")

    # 打印 merged_rules 信息
    logger.info("")
    logger.info("=" * 80)
    logger.info("[develop/urls] rules.merge_rules() result:")
    logger.info("=" * 80)
    merged = rules.merge_rules()
    for i, rule_info in enumerate(merged, 1):
        logger.info(f"  {i:3d}. {rule_info}")
    logger.info("-" * 80)
    logger.info(f"Total merged rules: {len(merged)}")

    return {'urls': u}


def _get_endpoint(route):
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

@expose("/develop/global")
async def develop_globals():
    """
    返回当前应用的全局环境变量。
    在 ASGI 环境中，这些值通过 uliweb 模块获取。
    """
    from uliweb import settings, application, functions

    # 构建类似原来 env 的字典
    glo = {
        'settings': settings,
        'application': application,
        'functions': functions,
    }
    return {"glo": glo}

from uliweb.utils.pyini import Ini
import os


def _get_app(app_path, modname, apps, catalogs, app_apps, parent_module=''):
    info_ini = os.path.join(app_path, 'info.ini')
    if os.path.exists(info_ini):
        info = get_app_info(modname, app_path, info_ini)
        if parent_module:
            info['module'] = parent_module + '.' + modname
        else:
            info['module'] = modname
        if info['module'] in app_apps:
            info['selected'] = True
        else:
            info['selected'] = False

        apps[modname] = info
        d = catalogs.setdefault(info['catalog'], [])
        d.append(info)

def _get_apps(application, path, parent_module, catalogs, apps, app_apps):
    if not os.path.exists(path):
        return
    for p in os.listdir(path):
        if p in ['.svn', 'CVS'] or p.startswith('.') or p.startswith('_'):
            continue
        app_path = os.path.join(path, p)

        if not os.path.isdir(app_path):
            continue

        _get_app(app_path, p, apps, catalogs, app_apps, parent_module)

        _path = os.path.join(path, p)
        if is_pyfile_exist(_path, '__init__'):
            if parent_module:
                m = parent_module + '.' + p
            else:
                m = p
            _get_apps(application, _path, m, catalogs, apps, app_apps)

def get_apps(application, apps_dirs, app_apps):
    catalogs = {}
    apps = {}

    for path, parent_module in apps_dirs:
        _get_apps(application, path, parent_module, catalogs, apps, app_apps)

    return catalogs, apps

def get_app_info(name, app_path, info_ini):
    catalog = 'No Catalog'
    desc = ''
    title = name.capitalize()
    icon = 'app_icon.png'
    author = ''
    version = ''
    homepage = ''

    if os.path.exists(info_ini):
        ini = Ini(info_ini)
        catalog = ini.info.get('catalog', catalog) or catalog
        desc = ini.info.get('description', desc) or desc
        title = ini.info.get('title', title) or title
        icon = ini.info.get('icon', icon) or icon
        icon_file = os.path.join(app_path, 'static', icon)
        author = ini.info.get('author', author) or author
        version = ini.info.get('version', version) or version
        homepage = ini.info.get('homepage', homepage) or homepage

    return {'catalog':catalog, 'desc':desc, 'title':title, 'name':name,
            'path':app_path, 'icon':icon, 'author':author,
            'version':version, 'homepage':homepage}