#coding=utf-8
from uliweb import expose
from .menu import bind_menu
from uliweb.utils.common import log
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
    from uliweb.core.SimpleFrame import url_map

    u = []
    for r in url_map.iter_rules():
        if r.methods:
            methods = ' '.join(list(r.methods))
        else:
            methods = ''
        u.append((r.rule, methods, r.endpoint))
    u.sort()

    return {'urls':u}

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