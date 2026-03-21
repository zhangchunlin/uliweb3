import os
from starlette.responses import Response, FileResponse
from uliweb import settings
import pkg_resources


class ASGIStaticFilesMiddleware:
    """
    This ASGI middleware is for static files serving, similar to WSGI StaticFilesMiddleware
    but implemented for ASGI.
    """

    def __init__(self, app, STATIC_URL, disallow=None, cache=True,
                 cache_timeout=60 * 60 * 12):
        # app 可能是 AsyncDispatcher 或 bound method
        # 尝试获取原始的 AsyncDispatcher 对象
        if callable(app) and hasattr(app, '__self__'):
            # 这是一个 bound method，保存对原始对象的引用
            self.dispatcher = app.__self__
        else:
            self.dispatcher = app

        self.app = app
        self.url_suffix = settings.DOMAINS.static.get('url_prefix', '') + STATIC_URL.rstrip('/') + '/'
        self.cache = cache
        self.cache_timeout = cache_timeout
        self.disallow = disallow

        # 获取静态文件路径
        path = os.path.normpath(settings.STATICFILES.get('STATIC_FOLDER', ''))
        if path == '.':
            path = ''
        self.static_path = path

        # 获取项目目录和 apps 目录，用于查找 app 静态文件
        # 优先从 dispatcher 获取，其次从 app 获取
        self.project_dir = getattr(self.dispatcher, 'project_dir', None) or getattr(app, 'project_dir', None)
        self.apps_dir = getattr(self.dispatcher, 'apps_dir', 'apps') or getattr(app, 'apps_dir', 'apps')

    def is_allowed(self, filename):
        """Check if the file access is allowed"""
        if self.disallow is not None:
            from fnmatch import fnmatch
            return not fnmatch(filename, self.disallow)
        return True

    def find_static_file(self, filename, apps=None):
        """Find static file in app directories"""
        # 优先使用传入的 apps 参数，否则从 self.app (AsyncDispatcher) 获取
        if apps is None:
            apps = getattr(self.app, 'apps', None)
            if apps is None:
                # 尝试从 application proxy 获取
                from uliweb import application
                if application is not None:
                    apps = getattr(application, 'apps', None)
                if apps is None:
                    return None

        # 首先检查项目静态目录
        if self.static_path:
            fname = os.path.normpath(os.path.join(self.static_path, filename).replace('\\', '/'))
            # 使用 os.path.realpath 解析符号链接，并验证路径仍在静态目录内
            real_fname = os.path.realpath(fname)
            real_static_path = os.path.realpath(self.static_path)

            # 检查规范化后的路径是否仍在静态文件目录内
            if real_fname.startswith(real_static_path + os.sep) or real_fname == real_static_path:
                if os.path.exists(real_fname):
                    return real_fname
            # 额外检查：确保相对路径遍历不能逃逸静态目录
            elif os.path.commonpath([real_fname, real_static_path]) == real_static_path:
                if os.path.exists(real_fname):
                    return real_fname

        # 然后检查应用静态目录 - 优先检查 apps/ 目录结构（uliweb 标准结构）
        if self.project_dir and self.apps_dir:
            for p in reversed(apps):
                # 检查 apps/{app}/static/ 目录（uliweb 标准结构）
                app_static_dir = os.path.join(self.project_dir, self.apps_dir, p, 'static')
                if os.path.isdir(app_static_dir):
                    f = os.path.join(app_static_dir, filename)
                    real_f = os.path.realpath(f)
                    real_static = os.path.realpath(app_static_dir)
                    # 检查是否在 static 目录内，防止路径遍历攻击
                    if real_f.startswith(real_static + os.sep) or real_f == real_static:
                        if os.path.exists(real_f):
                            return real_f

        # 继续使用 pkg_resources 检查应用包中的静态文件
        for p in reversed(apps):
            try:
                fname = os.path.normpath(os.path.join('static', filename).replace('\\', '/'))
                if fname.startswith('static/'):
                    # 使用 pkg_resources 查找文件
                    try:
                        # 尝试获取文件路径
                        f = pkg_resources.resource_filename(p, fname)
                        if os.path.exists(f):
                            # 验证路径 - 使用 pkg_resources 返回的实际路径来计算 static 目录
                            real_f = os.path.realpath(f)
                            # 正确计算包的 static 目录路径
                            # 使用 pkg_resources.resource_filename(p, '') 获取包的实际路径
                            package_path = pkg_resources.resource_filename(p, '')
                            static_path = os.path.join(package_path, 'static')
                            real_static = os.path.realpath(static_path)
                            # 检查是否在 static 目录内
                            if real_f.startswith(real_static + os.sep) or real_f == real_static:
                                return real_f
                            # 使用 commonpath 检查
                            elif os.path.commonpath([real_f, real_static]) == real_static:
                                return real_f
                    except Exception:
                        pass
            except Exception:
                pass

        return None

    async def __call__(self, scope, receive, send):
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 获取请求路径
        # 优先使用 raw_path 以捕获可能已被服务器规范化的路径
        raw_path = scope.get('raw_path')
        if raw_path:
            if isinstance(raw_path, bytes):
                raw_path = raw_path.decode('utf-8', errors='ignore')
            # 使用 raw_path 进行检查，因为它可能包含未规范化的路径
            path = raw_path.strip('/')
        else:
            path = scope.get('path', '').strip('/')

        # 检查是否是静态文件请求
        if path.startswith(self.url_suffix.strip('/')):
            # 提取文件名
            filename = path[len(self.url_suffix.strip('/')):].strip('/')

            # 首先检查是否包含路径遍历攻击（..）
            # 包括 URL 编码的反斜杠和普通 ..
            import urllib.parse
            decoded_filename = urllib.parse.unquote(filename)

            # 检测目录遍历攻击
            # 1. 包含 ..
            # 2. 解码后包含 ..
            # 3. 解码后包含反斜杠（可能与 .. 结合形成目录遍历）
            # 4. 只包含 . 也需要检查（可能是隐藏文件，但组合起来可能是攻击）
            if ('..' in filename or '..' in decoded_filename or
                '\\' in decoded_filename or decoded_filename.startswith('.')):
                # 返回 403 Forbidden，表示检测到非法路径
                response = Response("You can not visit the file %s." % filename, status_code=403)
                await response(scope, receive, send)
                return

            # 清理路径，防止目录遍历攻击
            # 使用 os.path.normpath 进行规范化，这会将 /static/../setup.py 转换为 /setup.py
            cleaned_filename = os.path.normpath(filename).replace('\\', '/')

            # 检查清理后的路径是否包含路径遍历
            # 如果规范化后的路径与原始路径不同，说明存在路径遍历
            if '..' in cleaned_filename or cleaned_filename.startswith('.'):
                response = Response("You can not visit the file %s." % cleaned_filename, status_code=403)
                await response(scope, receive, send)
                return

            # 额外检查：验证规范化后的路径仍然在静态文件目录内
            # 这可以捕获那些被服务器规范化后的路径遍历攻击
            normalized_path = os.path.normpath(path).replace('\\', '/')
            if normalized_path.startswith(self.url_suffix.strip('/')):
                normalized_filename = normalized_path[len(self.url_suffix.strip('/')):].strip('/')
                if '..' in normalized_filename or normalized_filename.startswith('.'):
                    response = Response("You can not visit the file %s." % normalized_filename, status_code=403)
                    await response(scope, receive, send)
                    return

            # 查找静态文件 - 每次请求时动态获取 apps
            apps = getattr(self.dispatcher, 'apps', None)
            if apps is None:
                # 尝试从 application 获取
                from uliweb import application
                if application is not None:
                    apps = getattr(application, 'apps', None)
            real_filename = self.find_static_file(cleaned_filename, apps=apps)

            if real_filename:
                # 检查文件访问权限
                if not self.is_allowed(real_filename):
                    # 返回 403 Forbidden
                    response = Response("You can not visit the file %s." % real_filename, status_code=403)
                    await response(scope, receive, send)
                    return

                # 检查文件是否存在
                if os.path.exists(real_filename):
                    # 使用 FileResponse 发送文件
                    response = FileResponse(
                        real_filename,
                        headers={
                            'Cache-Control': 'public, max-age=%d' % self.cache_timeout if self.cache else 'no-cache'
                        }
                    )
                    await response(scope, receive, send)
                    return
                else:
                    # 文件不存在，返回 404
                    response = Response("Can't found the file %s" % filename, status_code=404)
                    await response(scope, receive, send)
                    return
            else:
                # 文件未找到，返回 404
                response = Response("Can't found the file %s" % filename, status_code=404)
                await response(scope, receive, send)
                return

        # 不是静态文件请求，传递给下一个应用
        await self.app(scope, receive, send)
