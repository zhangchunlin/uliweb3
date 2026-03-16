#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest
from uliweb.utils.test import client, client_from_application, BlankRequest, Counter

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUliwebUtilsModified(unittest.TestCase):

    def test_client_creation(self):
        """测试客户端创建功能"""
        # 测试使用默认参数创建客户端
        c = client()
        self.assertIsNotNone(c)
        self.assertTrue(hasattr(c, 'app'))
        self.assertTrue(hasattr(c, 'test_url'))

    def test_client_from_application(self):
        """测试从应用创建客户端功能"""
        from uliweb.core.SimpleFrame import ASGIApplication
        app = ASGIApplication()
        c = client_from_application(app)
        self.assertIsNotNone(c)
        self.assertTrue(hasattr(c, 'app'))
        self.assertTrue(hasattr(c, 'test_url'))

    def test_blank_request(self):
        """测试空白请求创建功能"""
        req = BlankRequest('/test')
        self.assertIsNotNone(req)
        self.assertEqual(req.method, 'GET')
        self.assertEqual(req.url.path, '/test')

    def test_blank_request_with_params(self):
        """测试带参数的空白请求创建功能"""
        req = BlankRequest('/test', method='POST', body=b'test data')
        self.assertIsNotNone(req)
        self.assertEqual(req.method, 'POST')

    def test_counter(self):
        """测试计数器功能"""
        counter = Counter()
        self.assertEqual(counter.total, 0)
        self.assertEqual(counter.passed, 0)
        self.assertEqual(counter.failed, 0)

        counter.add(True)
        self.assertEqual(counter.total, 1)
        self.assertEqual(counter.passed, 1)
        self.assertEqual(counter.failed, 0)

        counter.add(False)
        self.assertEqual(counter.total, 2)
        self.assertEqual(counter.passed, 1)
        self.assertEqual(counter.failed, 1)


if __name__ == '__main__':
    unittest.main()
