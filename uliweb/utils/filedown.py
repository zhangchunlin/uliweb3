# coding=utf8

import os
from time import time, mktime
from datetime import datetime
from zlib import adler32
import mimetypes
from email.utils import formatdate
from starlette.responses import Response, FileResponse
from starlette.exceptions import HTTPException
from ._compat import import_, b

quote = import_('urllib.parse', ['quote'])


def _opener(filename):
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found")
    return (
        open(filename, 'rb'),
        datetime.utcfromtimestamp(os.path.getmtime(filename)),
        int(os.path.getsize(filename))
    )

def _generate_etag(mtime, file_size, real_filename):
    return 'wzsdm-%d-%s-%s' % (
        mktime(mtime.timetuple()),
        file_size,
        adler32(b(real_filename)) & 0xffffffff
    )

def _get_download_filename(request_or_env, filename):
    """获取下载文件名

    Args:
        request_or_env: request 对象或 environ 字典（兼容旧代码）
        filename: 文件名
    """
    from uliweb.utils.common import safe_str
    from ua_parser import user_agent_parser

    # werkzeug.useragents was remove from werkzeug 2.1 using ua-parser replace it.
    # link https://github.com/pallets/werkzeug/issues/2078

    # 支持 request 对象或 environ 字典
    if hasattr(request_or_env, 'headers'):
        # request 对象（ASGI）
        http_user_agent = request_or_env.headers.get('user-agent', '')
    else:
        # environ 字典（WSGI 兼容）
        http_user_agent = request_or_env.get('HTTP_USER_AGENT', '')

    http_user_agent = user_agent_parser.Parse(http_user_agent)
    ua_browser = http_user_agent.get("user_agent", {}).get("family","").lower()

    fname = safe_str(filename, 'utf8')
    if ua_browser == 'msie':
        result = 'filename=' + quote(fname)
    elif ua_browser == 'safari':
        result = 'filename=' + fname
    else:
        result = "filename*=UTF-8''" + quote(fname)
    return result

# copy from http://docs.webob.org/en/latest/file-example.html
class FileIterable(object):
    def __init__(self, filename, start=None, stop=None):
        self.filename = filename
        self.start = start
        self.stop = stop

    def __iter__(self):
        return FileIterator(self.filename, self.start, self.stop)

    def app_iter_range(self, start, stop):
        return self.__class__(self.filename, start, stop)


class FileIterator(object):
    chunk_size = 4096

    def __init__(self, filename, start, stop):
        self.filename = filename
        self.fileobj = open(self.filename, 'rb')
        if start:
            self.fileobj.seek(start)
        if stop is not None:
            self.length = stop - start
        else:
            self.length = None

    def __iter__(self):
        return self

    def next(self):
        if self.length is not None and self.length <= 0:
            raise StopIteration
        chunk = self.fileobj.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        if self.length is not None:
            self.length -= len(chunk)
            if self.length < 0:
                # Chop off the extra:
                chunk = chunk[:self.length]
        return chunk

    __next__ = next  # py3 compat

async def filedown(environ, filename, cache=True, cache_timeout=None,
                   action=None, real_filename=None, x_sendfile=False,
                   x_header_name=None, x_filename=None, fileobj=None,
                   default_mimetype='application/octet-stream'):
    """
    @param filename: is used for display in download
    @param real_filename: if used for the real file location
    @param x_urlfile: is only used in x-sendfile, and be set to x-sendfile header
    @param fileobj: if provided, then returned as file content
    @type fileobj: (fobj, mtime, size)

    filedown now support web server controlled download, you should set
    xsendfile=True, and add x_header, for example:

    nginx
        ('X-Accel-Redirect', '/path/to/local_url')
    apache
        ('X-Sendfile', '/path/to/local_url')
    """
    from .common import safe_str

    # 如果提供了 fileobj，使用自定义实现
    if fileobj:
        # 处理自定义文件对象
        f, mtime, file_size = fileobj
        headers = []

        # 获取 MIME 类型
        guessed_type = mimetypes.guess_type(filename)
        mime_type = guessed_type[0] or default_mimetype
        headers.append(('Content-Type', mime_type))

        # 处理文件名
        d_filename = _get_download_filename(environ, os.path.basename(filename))
        if action == 'download':
            headers.append(('Content-Disposition', 'attachment; %s' % d_filename))
            headers.append(('Access-Control-Expose-Headers', 'Content-Disposition'))
        elif action == 'inline':
            headers.append(('Content-Disposition', 'inline; %s' % d_filename))
            headers.append(('Access-Control-Expose-Headers', 'Content-Disposition'))

        # 处理缓存
        if cache:
            etag = _generate_etag(mtime, file_size, real_filename or filename)
            headers.append(('ETag', '"%s"' % etag))
            headers.append(('Last-Modified', formatdate(mktime(mtime.timetuple()), usegmt=True)))
            if cache_timeout:
                headers.append(('Cache-Control', 'max-age=%d, public' % cache_timeout))
                headers.append(('Expires', formatdate(time() + cache_timeout, usegmt=True)))
        else:
            headers.append(('Cache-Control', 'public'))
            headers.append(('Last-Modified', formatdate(mktime(mtime.timetuple()), usegmt=True)))

        # 添加文件大小
        headers.append(('Content-Length', str(file_size)))

        # 返回响应
        return Response(f.read(), status_code=200, headers=dict(headers))

    # 如果启用了 x-sendfile，使用自定义实现
    if x_sendfile:
        if not x_header_name or not x_filename:
            raise Exception("x_header_name or x_filename can't be empty")

        # 获取 MIME 类型
        guessed_type = mimetypes.guess_type(filename)
        mime_type = guessed_type[0] or default_mimetype

        # 构建响应头
        headers = []
        headers.append(('Content-Type', mime_type))

        # 处理文件名
        d_filename = _get_download_filename(environ, os.path.basename(filename))
        if action == 'download':
            headers.append(('Content-Disposition', 'attachment; %s' % d_filename))
            headers.append(('Access-Control-Expose-Headers', 'Content-Disposition'))
        elif action == 'inline':
            headers.append(('Content-Disposition', 'inline; %s' % d_filename))
            headers.append(('Access-Control-Expose-Headers', 'Content-Disposition'))

        # 添加 x-sendfile 头
        headers.append((x_header_name, safe_str(x_filename)))

        # 返回响应
        return Response('', status_code=200, headers=dict(headers))

    # 否则使用 Starlette 的 FileResponse
    real_filename = real_filename or filename

    # 确定内容处置类型
    content_disposition_type = 'attachment' if action == 'download' else 'inline'
    if action is None:
        content_disposition_type = 'attachment'  # 默认为下载

    # 处理文件名
    basename = os.path.basename(filename)

    # 创建 FileResponse
    response = FileResponse(
        path=real_filename,
        filename=basename,
        content_disposition_type=content_disposition_type
    )

    # 处理缓存设置
    if cache and cache_timeout:
        # FileResponse 会自动处理 ETag 和 Last-Modified
        response.headers['Cache-Control'] = f'max-age={cache_timeout}, public'
        response.headers['Expires'] = formatdate(time() + cache_timeout, usegmt=True)
    elif not cache:
        response.headers['Cache-Control'] = 'public'

    # 添加 Access-Control-Expose-Headers
    if action in ('download', 'inline'):
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

    return response
