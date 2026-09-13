#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.utils.files 的单元测试（save_file 文件 IO 落盘逻辑）。

str_filesize / encode_filename / unicode_filename 已在源码 doctest 覆盖，这里补充
save_file 的落盘、目录创建、重命名避让与流式写入行为。
"""

import os
import sys
import shutil
import tempfile
import unittest
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.utils.files import save_file, str_filesize


class SaveFileTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.dir, name)

    def test_save_writes_content(self):
        fname = self._path('sub/a.txt')
        result = save_file(fname, BytesIO(b'hello'))
        self.assertEqual(result, 'a.txt')
        with open(fname, 'rb') as f:
            self.assertEqual(f.read(), b'hello')

    def test_save_large_stream(self):
        data = b'x' * 20000  # 大于 buffer_size(4096)，验证流式循环
        fname = self._path('big.bin')
        save_file(fname, BytesIO(data))
        with open(fname, 'rb') as f:
            self.assertEqual(f.read(), data)

    def test_save_creates_nested_dirs(self):
        fname = self._path('deep/nested/dir/f.txt')
        save_file(fname, BytesIO(b'data'))
        self.assertTrue(os.path.exists(fname))

    def test_save_non_replace_renames(self):
        fname = self._path('r.txt')
        save_file(fname, BytesIO(b'1'))
        result = save_file(fname, BytesIO(b'2'))
        self.assertEqual(result, 'r(1).txt')
        with open(self._path('r(1).txt'), 'rb') as f:
            self.assertEqual(f.read(), b'2')

    def test_save_replace_overwrites(self):
        fname = self._path('o.txt')
        save_file(fname, BytesIO(b'1'))
        save_file(fname, BytesIO(b'2'), replace=True)
        with open(fname, 'rb') as f:
            self.assertEqual(f.read(), b'2')

    def test_save_requires_filelike(self):
        self.assertRaises(AssertionError, save_file, self._path('x.txt'), 'not-a-file')


class StrFilesizeTestCase(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(str_filesize(0), '0')
        self.assertEqual(str_filesize(1023), '1023')
        self.assertEqual(str_filesize(1024), '1K')
        self.assertEqual(str_filesize(1024 * 2), '2K')
        self.assertEqual(str_filesize(1024 ** 2), '1M')
        self.assertEqual(str_filesize(1024 ** 3), '1G')


if __name__ == '__main__':
    unittest.main()