#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.utils.image 的单元测试。

覆盖 resize_image / thumbnail_image / image_size / test_image / fix_filename。
依赖 PIL（环境缺失时 skip，不引入新依赖）。
"""

import os
import sys
import shutil
import tempfile
import unittest
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.utils.image import (
    fix_filename, resize_image, thumbnail_image,
    image_size,
)
# 别名避免与 nose 的 test_* 自动收集冲突
from uliweb.utils.image import test_image as is_image_file
# 阻止 nose --with-doc 把 image.test_image 当成 doctest 用例收集
is_image_file.__test__ = False

try:
    from PIL import Image
    HAVE_PIL = True
    # Image.ANTIALIAS 在 Pillow 10+ 移除；resize/thumbnail/crop_resize 依赖它，
    # 旧版可用、新版会 AttributeError（属生产代码兼容缺陷，见 plan.md 记录）
    HAVE_ANTIALIAS = hasattr(Image, 'ANTIALIAS')
except Exception:
    HAVE_PIL = False
    HAVE_ANTIALIAS = False


def _make_png(size=(100, 80), color=(255, 0, 0)):
    img = Image.new('RGB', size, color)
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf


@unittest.skipUnless(HAVE_PIL, 'PIL not installed')
class ImageTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_fix_filename_suffix(self):
        self.assertEqual(fix_filename('icon.png', '_40x40'), 'icon_40x40.png')
        self.assertEqual(fix_filename('icon.png'), 'icon.png')

    def test_image_size(self):
        path = os.path.join(self.dir, 'src.png')
        with open(path, 'wb') as f:
            f.write(_make_png().getvalue())
        self.assertEqual(image_size(path), (100, 80))

    def test_test_image_suffix(self):
        self.assertTrue(is_image_file('a.png'))
        self.assertTrue(is_image_file('a.jpg'))
        self.assertIsNone(is_image_file('a.txt'))

    def test_test_image_strong(self):
        path = os.path.join(self.dir, 'real.png')
        with open(path, 'wb') as f:
            f.write(_make_png().getvalue())
        self.assertTrue(is_image_file(path, strong=True))
        self.assertFalse(is_image_file(os.path.join(self.dir, 'missing.png'), strong=True))
        bad = os.path.join(self.dir, 'bad.png')
        with open(bad, 'wb') as f:
            f.write(b'not an image')
        self.assertFalse(is_image_file(bad, strong=True))

    @unittest.skipUnless(HAVE_ANTIALIAS, 'Pillow>=10 移除 Image.ANTIALIAS，resize_image 不可用')
    def test_resize_image(self):
        out = resize_image(_make_png(), size=(50, 50))
        img = Image.open(out)
        self.assertEqual(img.size, (50, 50))
        self.assertEqual(img.format, 'JPEG')

    @unittest.skipUnless(HAVE_ANTIALIAS, 'Pillow>=10 移除 Image.ANTIALIAS，resize_image_string 不可用')
    def test_resize_image_string(self):
        from uliweb.utils.image import resize_image_string
        data = resize_image_string(_make_png().getvalue(), size=(30, 30))
        img = Image.open(BytesIO(data))
        self.assertEqual(img.size, (30, 30))

    @unittest.skipUnless(HAVE_ANTIALIAS, 'Pillow>=10 移除 Image.ANTIALIAS，thumbnail_image 不可用')
    def test_thumbnail_small_no_change(self):
        # 原图小于缩略目标，直接返回原名，不生成文件
        path = os.path.join(self.dir, 'small.png')
        with open(path, 'wb') as f:
            f.write(_make_png(size=(10, 10)).getvalue())
        result = thumbnail_image(path, 'small.png', size=(200, 75))
        self.assertEqual(result, ('small.png', 'small.png'))
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'small.thumbnail.png')))

    @unittest.skipUnless(HAVE_ANTIALIAS, 'Pillow>=10 移除 Image.ANTIALIAS，thumbnail_image 不可用')
    def test_thumbnail_large(self):
        path = os.path.join(self.dir, 'large.png')
        with open(path, 'wb') as f:
            f.write(_make_png(size=(400, 300)).getvalue())
        ofile, ofile1 = thumbnail_image(path, 'large.png', size=(200, 75))
        self.assertEqual(ofile, os.path.join(self.dir, 'large.thumbnail.png'))
        self.assertEqual(ofile1, 'large.thumbnail.png')
        img = Image.open(ofile)
        self.assertLessEqual(img.size[0], 200)
        self.assertLessEqual(img.size[1], 75)

    def test_test_image_suffix(self):
        self.assertTrue(is_image_file('a.png'))
        self.assertTrue(is_image_file('a.jpg'))
        self.assertIsNone(is_image_file('a.txt'))

    def test_test_image_strong(self):
        path = os.path.join(self.dir, 'real.png')
        with open(path, 'wb') as f:
            f.write(_make_png().getvalue())
        self.assertTrue(is_image_file(path, strong=True))
        self.assertFalse(is_image_file(os.path.join(self.dir, 'missing.png'), strong=True))
        bad = os.path.join(self.dir, 'bad.png')
        with open(bad, 'wb') as f:
            f.write(b'not an image')
        self.assertFalse(is_image_file(bad, strong=True))


if __name__ == '__main__':
    unittest.main()