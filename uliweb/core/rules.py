from __future__ import print_function, absolute_import, unicode_literals
import os
import re
import inspect
from uliweb.utils.common import log
from uliweb.utils.sorteddict import SortedDict
import copy
from ..utils._compat import string_types, iterkeys, get_class, ismethod


class ReservedKeyError(Exception):
    pass


__exposes__ = SortedDict()
__no_need_exposed__ = []
__class_methods__ = {}
__app_rules__ = {}
__url_route_rules__ = []
__url_names__ = {}
static_views = []

reserved_keys = ['settings', 'redirect', 'application', 'request', 'response', 'error',
    'json']

def merge_rules():
    from itertools import chain

    s = []
    index = {}
    for v in sorted(__no_need_exposed__ + list(chain(*__exposes__.values())), key=lambda x:x[4]):
        appname, endpoint, url, kw, timestamp = v
        if 'name' in kw:
            url_name = kw.pop('name')
        else:
            url_name = endpoint
        __url_names__[url_name] = endpoint
        methods = [y.upper() for y in kw.get('methods', [])]
        methods.sort()

        key = url, tuple(methods), kw.get('subdomain')
        i = index.get(key, None)
        if i is not None:
            s[i] = appname, endpoint, url, kw
        else:
            s.append((appname, endpoint, url, kw))
            index[key] = len(s)-1

    return s


def get_func(f):
    if inspect.ismethod(f):
        return f.__func__
    else:
        return f


def get_function_path(f):
    if hasattr(f, '__qualname__'):
        return f.__module__ + '.' + f.__qualname__
    elif getattr(f, '__self__', None):
        return f.__module__ + '.' + f.__self__.__name__ + '.' + f.__name__
    elif getattr(f, 'im_class', None):
        return f.__module__ + '.' + f.im_class.__name__ + '.' + f.__name__
    else:
        return f.__module__ + '.' + f.__name__


def get_classname(f):
    if hasattr(f, '__qualname__'):
        return f.__qualname__.rsplit('.', 1)[0]
    elif getattr(f, '__self__', None):
        return f.__self__.__name__
    elif getattr(f, 'im_class', None):
        return f.im_class.__name__


def clear_rules():
    global __exposes__, __no_need_exposed__, __url_names__
    __exposes__ = {}
    __no_need_exposed__ = []
    __url_names__ = {}

def set_app_rules(rules=None):
    global __app_rules__
    __app_rules__ = {}
    __app_rules__.update(rules or {})

def set_urlroute_rules(rules=None):
    """
    rules should be (pattern, replace)

    e.g.: ('/admin', '/demo')
    """
    global __url_route_rules__
    __url_route_rules__ = []
    for k, v in (rules or {}).values():
        __url_route_rules__.append((re.compile(k), v))

def get_endpoint(f):
    if ismethod(f):
        _class = get_class(f)
        if _class is not None:
            endpoint = '.'.join([_class.__module__, _class.__name__, f.__name__])
        else:
            # 如果无法获取类，尝试使用 __qualname__ 或其他方式
            endpoint = get_function_path(f)
    elif inspect.isfunction(f):
        endpoint = '.'.join([f.__module__, f.__name__])
    else:
        endpoint = f
    return endpoint

def get_template_args(appname, f):
    viewname, clsname = '', ''
    if ismethod(f):
        _class = get_class(f)
        clsname = _class.__name__
        viewname = f.__name__
    else:
        viewname = f.__name__
    return {'appname':appname, 'view_class':clsname, 'function':viewname}

def expose(rule=None, **kwargs):
    e = Expose(rule, **kwargs)
    if e.parse_level == 1:
        return rule
    else:
        return e


def add_rule(map, url, endpoint, **kw):
    """将路由规则添加到路由映射中

    这个函数用于 WSGI 版本的 Dispatcher.init_urls 方法
    支持 websocket 参数来注册 WebSocket 路由
    """
    # 获取 websocket 参数
    websocket = kw.pop('websocket', False)

    # 根据是否有 websocket 参数来选择路由方法
    if hasattr(map, 'add_websocket_route') and websocket:
        map.add_websocket_route(url, endpoint, **kw)
    else:
        map.add_route(url, endpoint, **kw)

class Expose(object):
    def __init__(self, rule=None, restful=False, replace=False, template=None,
                 layout=None, websocket=False, **kwargs):
        self.restful = restful
        self.replace = replace
        self.template = template
        self.layout = layout
        self.websocket = websocket  # 新增：WebSocket 路由标志

        # 如果没有指定 methods，默认支持主要 HTTP 方法
        if 'methods' not in kwargs:
            kwargs['methods'] = ['GET', 'POST', 'PUT']

        if inspect.isfunction(rule) or inspect.isclass(rule):
            self.parse_level = 1
            self.rule = None
            # 保留 kwargs 中的 methods 字段
            self.kwargs = kwargs
            self.parse(rule)
        else:
            self.parse_level = 2
            self.rule = rule
            self.kwargs = kwargs

    def _get_app_prefix(self, appname):
        if appname in __app_rules__:
            d = __app_rules__[appname]
            if not d:
                return
            if isinstance(d, str):
                return d
            else:
                return d.get('prefix')

    def _get_app_subdomin(self, appname):
        if appname in __app_rules__:
            d = __app_rules__[appname]
            if not d:
                return
            if isinstance(d, str):
                return
            else:
                return d.get('subdomain')

    def _fix_url(self, appname, rule, prefix=None):
        """
        修复 URL 规则，添加应用前缀
        只处理 app_prefix 的拼接
        """
        app_prefix = self._get_app_prefix(appname)

        # 只处理 app_prefix
        if rule.startswith('/') and app_prefix:
            url = app_prefix.rstrip('/') + '/' + rule.lstrip('/')
        else:
            url = rule

        if url.startswith('!'):
            url = url[1:]

        if len(url) > 1:
            url = url.rstrip('/')
        return url

    def _fix_route(self, rule):
        for k, v in __url_route_rules__:
            if k.match(rule):
                return k.sub(v, rule)
        return rule

    def _fix_kwargs(self, appname, v):
        _subdomain = self._get_app_subdomin(appname)
        if _subdomain is None:
            _subdomain = self.kwargs.get('subdomain')
        if _subdomain is None:
            return
        if _subdomain:
            v['subdomain'] = _subdomain
        else:
            v.pop('subdomain', None)

    def _get_path(self, f):
        m = f.__module__.split('.')
        s = []
        for i in m:
            if not i.startswith('views'):
                s.append(i)
        appname = '.'.join(s)
        return appname, '/'.join(s)

    def parse(self, f):
        if inspect.isfunction(f) or ismethod(f):
            func, result = self.parse_function(f)
            a = __exposes__.setdefault(func, [])
            a.append(result)
        else:
            self.parse_class(f)

    def parse_class(self, f):
        from uliweb.utils.date import now
        appname, path = self._get_path(f)
        clsname = f.__name__
        if self.rule:
            prefix = self.rule
        else:
            prefix = '/' + '/'.join([path, clsname])
        f.__exposed_url__ = prefix
        for name in dir(f):
            func = getattr(f, name)
            if (ismethod(func) or inspect.isfunction(func)) and not name.startswith('_'):
                if hasattr(func, '__exposed__') and func.__exposed__:
                    new_endpoint = '.'.join([func.__module__, f.__name__, name])
                    f_func = get_func(func)
                    if f_func in __exposes__:
                        for v in __exposes__.pop(f_func):
                            #__no_rule__ used to distinct if the view function has used
                            #expose to decorator, if not then __no_rule__ will be True
                            #then it'll use default url route regular to make url
                            if func.__no_rule__:
                                # 调用 _get_url 获取相对路径，然后拼接 prefix
                                relative_rule = self._get_url(appname, prefix, func)
                                rule = prefix.rstrip('/') + '/' + relative_rule.lstrip('/')
                                rule = self._fix_url(appname, rule, prefix=None)
                            else:
                                #check if the func has already rule
                                _old = func.__old_rule__.get(v[2])
                                #if keep, then it'll skip app prefix
                                if _old.startswith('!'):
                                    rule = _old[1:]
                                    if not rule.startswith('/'):
                                        raise ValueError("The rule of <!rule> definition should be start with '!/'")

                                else:
                                    # 当 _old 是绝对路径时，直接使用 _old，不拼接 prefix
                                    if _old.startswith('/'):
                                        rule = _old
                                    elif not _old:
                                        # 如果 _old 为空字符串，直接使用 prefix 作为规则
                                        rule = prefix
                                    else:
                                        # 使用 rstrip 和 lstrip 避免双斜杠
                                        rule = prefix.rstrip('/') + '/' + _old.lstrip('/')
                                    rule = self._fix_url(appname, rule, prefix=None)

                                func.__old_rule__['clsname'] = clsname
                                #save processed data
                                x = list(v)
                                x[1] = new_endpoint
                                x[2] = rule
                                setattr(func, '__saved_rule__', x)

                                #add subdomain process
                                self._fix_kwargs(appname, v[3])

                            rule = self._fix_route(rule)
                            __no_need_exposed__.append((v[0], new_endpoint, rule, v[3], now()))
                    else:
                        #maybe is subclass
                        v = copy.deepcopy(func.func_dict.get('__saved_rule__'))
                        if getattr(func, '__fixed_url__'):
                            rule = v[2]
                        else:
                            rule = self._get_url(appname, prefix, func)
                        rule = self._fix_route(rule)
                        if v and new_endpoint != v[1]:
                            if self.replace:
                                v[3]['name'] = v[3].get('name') or v[1]
                                setattr(func, '__template__', {'function':func.__name__, 'view_class':func.__old_rule__['clsname'], 'appname':appname})
                            else:
                                v[2] = rule
                            v[1] = new_endpoint
                            v[4] = now()
                            setattr(func, '__saved_rule__', v)

                            #add subdomain process
                            self._fix_kwargs(appname, v[3])
                            __no_need_exposed__.append(v)
                else:
                    # 调用 _get_url 获取相对路径，然后拼接 prefix
                    relative_rule = self._get_url(appname, prefix, func)
                    rule = prefix.rstrip('/') + '/' + relative_rule.lstrip('/')
                    rule = self._fix_url(appname, rule, prefix=None)
                    rule = self._fix_route(rule)
                    endpoint = '.'.join([f.__module__, clsname, func.__name__])
                    #process inherit kwargs from class
                    #add subdomain process
                    kw = self.kwargs.copy()
                    self._fix_kwargs(appname, kw)
                    x = appname, endpoint, rule, kw, now()
                    __no_need_exposed__.append(x)
                    setattr(func, '__exposed__', True)
                    setattr(func, '__saved_rule__', list(x))
                    setattr(func, '__old_rule__', {'rule':rule, 'clsname':clsname})
                    setattr(func, '__template__', None)
                    setattr(func, '__layout__', None)
                    setattr(func, '__fixed_url__', False)

    def _get_url(self, appname, prefix, f):
        """
        生成相对路径，不处理 prefix 拼接
        """
        args = list(inspect.signature(f).parameters)
        if args:
            if ismethod(f):
                args = args[1:]
            args = ['<%s>' % x for x in args]
        if f.__name__ in reserved_keys:
            raise ReservedKeyError('The name "%s" is a reversed key, so please change another one' % f.__name__)

        # 如果 self.rule 不为 None（类有 @expose('/xxx') 装饰器），使用 self.rule 作为基础规则
        if self.rule is not None:
            # 如果 self.rule 是空字符串 ''，返回空字符串（让 parse_class 处理）
            if self.rule == '':
                return ''
            else:
                # 只返回方法名，不包含 self.rule
                rule = f.__name__
                if args:
                    rule = rule + '/' + '/'.join(args)
        else:
            # self.rule is None 的情况：类有 @expose 装饰器（不带参数）
            # 构建相对路径（不包含 prefix）
            if self.restful:
                rule = '/'.join([f.__name__] + args[:1] + args[1:])
            else:
                rule = '/'.join([f.__name__] + args)

        return rule

    def parse_function(self, f):
        from uliweb.utils.date import now
        args = list(inspect.signature(f).parameters)
        if args:
            args = ['<%s>' % x for x in args]
        if f.__name__ in reserved_keys:
            raise ReservedKeyError('The name "%s" is a reversed key, so please change another one' % f.__name__)
        appname, path = self._get_path(f)
        if self.rule is None:
            if self.restful:
                rule = '/' + '/'.join([path] + args[:1] + [f.__name__] + args[1:])
            else:
                rule = '/' + '/'.join([path, f.__name__] + args)
        else:
            self.rule = self._fix_route(self.rule)
            rule = self.rule
        fixed_url = rule.startswith('!')
        rule = self._fix_url(appname, rule)
        endpoint = get_function_path(f)
        clsname = get_classname(f)
        setattr(f, '__exposed__', True)
        setattr(f, '__no_rule__', (self.parse_level == 1) or (self.parse_level == 2 and (self.rule is None)))
        if not hasattr(f, '__old_rule__'):
            setattr(f, '__old_rule__', {})

        getattr(f, '__old_rule__')[rule] = self.rule
        getattr(f, '__old_rule__')['clsname'] = clsname
        setattr(f, '__template__', self.template)
        setattr(f, '__layout__', self.layout)
        setattr(f, '__fixed_url__', fixed_url)

        kw = self.kwargs.copy()
        # 添加 WebSocket 标志到 kw 中
        if self.websocket:
            kw['websocket'] = True
        self._fix_kwargs(appname, kw)
        return f, (appname, endpoint, rule, kw, now())

    def __call__(self, f):
        from uliweb.utils.common import safe_import

        if isinstance(f, string_types):
            try:
                _, f = safe_import(f)
            except:
                log.error('Import error: rule=%s' % f)
                raise
        self.parse(f)
        return f
