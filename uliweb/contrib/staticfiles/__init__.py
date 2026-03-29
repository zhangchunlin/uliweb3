from uliweb.core.SimpleFrame import expose


def startup_installed(sender):
    static_url = sender.settings.GLOBAL.get('STATIC_URL')
    if not static_url:
        return
    url = static_url.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(static)


def prepare_default_env(sender, env):
    env['url_for_static'] = url_for_static


def url_for_static(filename=None, **kwargs):
    from uliweb import settings
    from uliweb.core.SimpleFrame import get_url_adapter, __global__, application as sf_application
    from uliweb.core.context import get_application
    from uliweb.utils._compat import import_

    urlparse, urlunparse, urljoin, urlencode = import_('urllib.parse',
        ['urlparse', 'urlunparse', 'urljoin', 'urlencode'])

    # 优先使用 get_application()，如果返回 None 则使用 SimpleFrame 中的 application
    application = get_application()
    if application is None:
        application = sf_application.get_value()
    # 最后尝试 __global__.application
    if application is None:
        application = __global__.application

    domain = application.domains.get('static', {}) if application else {}

    # add STATIC_VER support
    ver = settings.GLOBAL.STATIC_VER
    if ver:
        kwargs['ver'] = ver

    # process external flag
    external = kwargs.pop('_external', False)
    if not external:
        external = domain.get('display', False)

    # process url prefix with '/'
    if filename.startswith('/'):
        if filename.endswith('/'):
            filename = filename[:-1]
        if kwargs:
            filename += '?' + urlencode(kwargs)
        if external:
            return urljoin(domain.get('domain', ''), filename)
        return filename

    # process url has already domain info
    r = urlparse(filename)
    if r.scheme or r.netloc:
        x = list(r)
        if kwargs:
            x[4] = urlencode(kwargs)
            return urlunparse(x)
        else:
            return filename

    kwargs['filename'] = filename
    url_adapter = get_url_adapter('static')
    result = url_adapter.build('uliweb.contrib.staticfiles.static',
                             kwargs, force_external=external)
    return result


def static(filename):
    pass

