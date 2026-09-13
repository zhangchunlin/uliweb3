#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.utils.storage 的单元测试。

覆盖 Storage(dict) 的字典/属性双访问、默认 None、删除与序列化。
"""

import os
import sys
import pickle
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.utils.storage import Storage


class StorageTestCase(unittest.TestCase):
    def test_dict_and_attr_access(self):
        o = Storage(a=1)
        self.assertEqual(o.a, 1)
        self.assertEqual(o['a'], 1)

    def test_attr_set_syncs_dict(self):
        o = Storage()
        o.a = 2
        self.assertEqual(o['a'], 2)
        o['b'] = 3
        self.assertEqual(o.b, 3)

    def test_missing_attr_returns_none(self):
        o = Storage()
        self.assertIsNone(o.nonexistent)

    def test_delete_attr(self):
        o = Storage(a=1)
        del o.a
        self.assertIsNone(o.a)
        self.assertNotIn('a', o)

    def test_delete_missing_raises_attribute_error(self):
        o = Storage()
        self.assertRaises(AttributeError, delattr, o, 'nope')

    def test_repr(self):
        o = Storage(a=1)
        self.assertTrue(repr(o).startswith('<Storage '))

    def test_pickle_roundtrip(self):
        o = Storage(a=1, b='x')
        restored = pickle.loads(pickle.dumps(o))
        self.assertEqual(restored, o)
        self.assertEqual(restored.b, 'x')


if __name__ == '__main__':
    unittest.main()