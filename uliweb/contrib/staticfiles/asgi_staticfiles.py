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

    def is_allowed(self, filename):
        """Check if the file access is allowed"""
        if self.disallow is not None:
            from fnmatch import fnmatch
            return not fnmatch(filename, self.disallow)
        return True

    def find_static_file(self, filename):
        """Find static file in app directories"""
        from uliweb import application

        # 首先检查项目静态目录
        if self.static_path:
            fname = os.path.normpath(os.path.join(self.static_path, filename).replace('\\', '/'))
            if fname.startswith(self.static_path) and os.path.exists(fname):
                return fname

        # 然后检查应用静态目录
        for p in reversed(application.apps):
            try:
                fname = os.path.normpath(os.path.join('static', filename).replace('\\', '/'))
                if fname.startswith('static/'):
                    # 使用 pkg_resources 查找文件
                    try:
                        # 尝试获取文件路径
                        f = pkg_resources.resource_filename(p, fname)
                        if os.path.exists(f):
                            return f
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
            cleaned_filename = '/'.join([x for x in filename.split('/') if x and x != '..'])

            # 查找静态文件
            real_filename = self.find_static_file(cleaned_filename)

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
