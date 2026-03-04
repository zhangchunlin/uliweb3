def get_cache(**kwargs):
    from uliweb import settings
    from uliweb.lib.weto.cache import Cache
    from uliweb.utils.common import import_attr, application_path

    serial_cls_path = settings.get_var('CACHE/serial_cls')
    if serial_cls_path:
        serial_cls = import_attr(serial_cls_path)
        if settings.GLOBAL.PICKLE_PROTOCAL_LEVEL is not None:
            serial_cls.protocal_level = settings.GLOBAL.PICKLE_PROTOCAL_LEVEL
    else:
        serial_cls = None

    options = dict(settings.get_var('CACHE_STORAGE', {}))
    options['data_dir'] = application_path(options['data_dir'])
    args = {'storage_type':settings.get_var('CACHE/type'),
        'options':options,
        'expiry_time':settings.get_var('CACHE/expiretime'),
        'serial_cls':serial_cls}

    args.update(kwargs)
    cache = Cache(**args)
    return cache



def get_async_cache(**kwargs):
    """
    Get an async-compatible cache instance.
    
    This function returns a Cache instance that has async methods
    (aget, aset, adelete, ainc, adec, acache) for use in ASGI applications.
    
    Usage:
        from uliweb.contrib.cache import get_async_cache
        
        cache = get_async_cache()
        
        # In async view:
        value = await cache.aget('my_key')
        await cache.aset('my_key', 'value', expire=3600)
        await cache.adelete('my_key')
        
        # Or use async decorator:
        @cache.acache('my_key', expire=300)
        async def expensive_operation():
            return await do_something()
    
    :param kwargs: Additional arguments to pass to Cache constructor
    :return: Cache instance with async methods
    """
    from uliweb import settings
    from uliweb.lib.weto.cache import Cache
    from uliweb.utils.common import import_attr, application_path

    serial_cls_path = settings.get_var('CACHE/serial_cls')
    if serial_cls_path:
        serial_cls = import_attr(serial_cls_path)
        if settings.GLOBAL.PICKLE_PROTOCAL_LEVEL is not None:
            serial_cls.protocal_level = settings.GLOBAL.PICKLE_PROTOCAL_LEVEL
    else:
        serial_cls = None

    options = dict(settings.get_var('CACHE_STORAGE', {}))
    options['data_dir'] = application_path(options['data_dir'])
    args = {'storage_type': settings.get_var('CACHE/type'),
        'options': options,
        'expiry_time': settings.get_var('CACHE/expiretime'),
        'serial_cls': serial_cls}

    args.update(kwargs)
    cache = Cache(**args)
    return cache
