#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.utils.filedown 的单元测试。

覆盖 FileIterable/FileIterator（迭代、Range 断点续传、chunk 边界）、
_generate_etag 确定性、_opener 及 filedown 的 fileobj 与 x-sendfile 路径。
"""

import os
import sys
import asyncio
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.utils.filedown import (
    FileIterable, FileIterator, _generate_etag, _opener, filedown,
)

DATA = bytes(range(256)) * 10  # 2560 bytes


class FileIterableTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, 'data.bin')
        with open(self.path, 'wb') as f:
            f.write(DATA)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_iter_full_content(self):
        it = FileIterable(self.path)
        self.assertEqual(b''.join(it), DATA)

    def test_range_subset(self):
        it = FileIterable(self.path, start=10, stop=20)
        self.assertEqual(b''.join(it), DATA[10:20])

    def test_range_to_end(self):
        it = FileIterable(self.path, start=len(DATA) - 5)
        self.assertEqual(b''.join(it), DATA[len(DATA) - 5:])

    def test_app_iter_range(self):
        it = FileIterable(self.path)
        ranged = it.app_iter_range(0, 100)
        self.assertIsInstance(ranged, FileIterable)
        self.assertEqual(b''.join(ranged), DATA[:100])

    def test_iterator_equality_of_content(self):
        it = FileIterable(self.path, start=0, stop=0)
        self.assertEqual(b''.join(it), b'')

    def test_etag_deterministic(self):
        from datetime import datetime
        import time
        mtime = datetime(2020, 1, 1, 12, 0, 0)
        e1 = _generate_etag(mtime, 1234, 'file.bin')
        e2 = _generate_etag(mtime, 1234, 'file.bin')
        self.assertEqual(e1, e2)
        self.assertNotEqual(e1, _generate_etag(mtime, 9999, 'file.bin'))
        self.assertIn('wzsdm-', e1)

    def test_opener(self):
        f, mtime, size = _opener(self.path)
        try:
            self.assertEqual(size, len(DATA))
        finally:
            f.close()

    def test_opener_missing_raises_404(self):
        from starlette.exceptions import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            _opener(os.path.join(self.dir, 'missing.bin'))
        self.assertEqual(ctx.exception.status_code, 404)


class FiledownTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, 'report.txt')
        with open(self.path, 'wb') as f:
            f.write(b'hello report')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_fileobj_download(self):
        from uliweb.utils.filedown import _opener
        f, mtime, size = _opener(self.path)
        try:
            resp = asyncio.run(filedown({}, 'report.txt', fileobj=(f, mtime, size),
                                        action='download', real_filename=self.path))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.body, b'hello report')
            self.assertIn('Content-Disposition', resp.headers)
            self.assertIn('attachment', resp.headers['Content-Disposition'])
            self.assertEqual(resp.headers['Content-Length'], str(len(b'hello report')))
        finally:
            f.close()

    def test_fileobj_inline(self):
        from uliweb.utils.filedown import _opener
        f, mtime, size = _opener(self.path)
        try:
            resp = asyncio.run(filedown({}, 'report.txt', fileobj=(f, mtime, size),
                                        action='inline', real_filename=self.path))
            self.assertIn('inline', resp.headers['Content-Disposition'])
        finally:
            f.close()

    def test_fileobj_etag_and_cache(self):
        from uliweb.utils.filedown import _opener
        f, mtime, size = _opener(self.path)
        try:
            resp = asyncio.run(filedown({}, 'report.txt', fileobj=(f, mtime, size),
                                        cache=True, real_filename=self.path))
            self.assertIn('ETag', resp.headers)
            self.assertIn('Last-Modified', resp.headers)
        finally:
            f.close()

    def test_xsendfile_requires_headers(self):
        with self.assertRaises(Exception):
            asyncio.run(filedown({}, 'report.txt', x_sendfile=True))

    def test_xsendfile(self):
        resp = asyncio.run(filedown({}, 'report.txt', x_sendfile=True,
                                    x_header_name='X-Sendfile', x_filename='/real/report.txt'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['X-Sendfile'], '/real/report.txt')


if __name__ == '__main__':
    unittest.main()