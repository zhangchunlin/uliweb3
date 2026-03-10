#coding=utf-8
import os
import sys
from .common import log
from ._compat import u

def save_file(fname, fobj, replace=False, buffer_size=4096):
    assert hasattr(fobj, 'read'), "fobj parameter should be a file-like object"
    path = os.path.dirname(fname)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception as e:
            log.exception(e)
            raise Exception("Can't create %s directory" % path)

    if not replace:
        ff, ext = os.path.splitext(fname)
        i = 1
        while os.path.exists(fname):
            fname = ff+'('+str(i)+')'+ext
            i += 1

    out = open(fname, 'wb')
    try:
        while 1:
            text = fobj.read(buffer_size)
            if text:
                out.write(text)
            else:
                break
        return os.path.basename(fname)
    finally:
        out.close()

def unicode_filename(filename, encoding=None):
    encoding = encoding or sys.getfilesystemencoding()
    return u(filename, encoding)

def encode_filename(filename, from_encoding='utf-8', to_encoding=None):
    """
    >>> # Test with actual unicode string, convert UTF-8 to GBK
    >>> f = '中国.doc'
    >>> result = encode_filename(f, 'utf-8', 'gbk')
    >>> result == b'\\xd6\\xd0\\xb9\\xfa.doc'
    True
    >>> # Test GBK to UTF-8 conversion
    >>> result = encode_filename(b'\\xd6\\xd0\\xb9\\xfa.doc', 'gbk', 'utf-8')
    >>> result == b'\\xe4\\xb8\\xad\\xe5\\x9b\\xbd.doc'
    True
    >>> # Test GBK to GBK conversion
    >>> result = encode_filename(b'\\xd6\\xd0\\xb9\\xfa.doc', 'gbk', 'gbk')
    >>> result == b'\\xd6\\xd0\\xb9\\xfa.doc'
    True

    """
    import sys
    to_encoding = to_encoding or sys.getfilesystemencoding()
    from_encoding = from_encoding or sys.getfilesystemencoding()
    filename = unicode_filename(filename, from_encoding)
    if to_encoding:
        return filename.encode(to_encoding)
    else:
        return filename

def str_filesize(size):
    """
    >>> print(str_filesize(0))
    0
    >>> print(str_filesize(1023))
    1023
    >>> print(str_filesize(1024))
    1K
    >>> print(str_filesize(1024*2))
    2K
    >>> print(str_filesize(1024**2-1))
    1023K
    >>> print(str_filesize(1024**2))
    1M
    """
    import bisect

    d = [(1024-1,'K'), (1024**2-1,'M'), (1024**3-1,'G'), (1024**4-1,'T')]
    s = [x[0] for x in d]

    index = bisect.bisect_left(s, size) - 1
    if index == -1:
        return str(size)
    else:
        b, u = d[index]
    return str(int(size // (b+1))) + u
