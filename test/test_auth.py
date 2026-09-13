#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.contrib.auth 的单元测试。

覆盖纯密码函数（get_hexdigest / encrypt_password / check_password）与 User 模型
的 set_password/check_password（sqlite 内存库）。

注：encrypt_password 的 md5=True 默认分支存在生产 bug（template 无关）——
hashlib.md5(raw_password).hexdigest 未对 str 编码且未调用 hexdigest()，会抛
TypeError（见 plan.md 记录）。此处仅测可用的 md5=False 路径。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uliweb.orm
uliweb.orm.__auto_create__ = True
uliweb.orm.__nullable__ = True
uliweb.orm.__server_default__ = False

from uliweb.orm import get_connection, get_model

get_connection('sqlite://')

from uliweb.contrib.auth import (
    get_hexdigest, encrypt_password, check_password, default_authenticate,
)
import uliweb.contrib.auth.models  # noqa: F401  注册 User 模型


class PasswordFuncTestCase(unittest.TestCase):
    def test_get_hexdigest_sha1(self):
        self.assertEqual(
            get_hexdigest('sha1', 'salt', 'pw'),
            __import__('hashlib').sha1(b'saltpw').hexdigest())

    def test_get_hexdigest_md5(self):
        self.assertEqual(
            get_hexdigest('md5', 'salt', 'pw'),
            __import__('hashlib').md5(b'saltpw').hexdigest())

    def test_get_hexdigest_unknown_raises(self):
        self.assertRaises(ValueError, get_hexdigest, 'unknown', 'salt', 'pw')

    def test_encrypt_check_roundtrip(self):
        enc = encrypt_password('secret', md5=False)
        self.assertTrue(enc.startswith('sha1$'))
        self.assertEqual(len(enc.split('$')), 3)
        self.assertTrue(check_password('secret', enc))

    def test_encrypt_md5_true_roundtrip(self):
        # 默认 md5=True。修复前 hashlib.md5(raw_password).hexdigest 未编码 str 且未调用，
        # 抛 TypeError；且"先 md5 再 sha1"无法被 check_password 验证。
        # 定案：md5=True 直接走 md5 算法，check_password 按 algo 分支匹配，往返成立。
        enc = encrypt_password('secret', md5=True)
        self.assertTrue(enc.startswith('md5$'))
        self.assertEqual(len(enc.split('$')), 3)
        self.assertTrue(check_password('secret', enc))
        self.assertFalse(check_password('wrong', enc))

    def test_encrypt_md5_false_prefix_sha1(self):
        enc = encrypt_password('secret', md5=False)
        self.assertTrue(enc.startswith('sha1$'))

    def test_check_wrong_password(self):
        enc = encrypt_password('secret', md5=False)
        self.assertFalse(check_password('wrong', enc))

    def test_check_malformed(self):
        self.assertFalse(check_password('secret', 'not-a-hash'))


class UserModelTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        User = get_model('user')
        cls.user = User(username='admin', password='', active=True)
        cls.user.set_password('secret')
        cls.user.save()

    def test_set_and_check_password(self):
        self.assertTrue(self.user.check_password('secret'))
        self.assertFalse(self.user.check_password('wrong'))

    def test_password_stored_hashed(self):
        # 落库的是 sha1$salt$hash 形式，非明文
        self.assertTrue(self.user.password.startswith('sha1$'))
        self.assertNotEqual(self.user.password, 'secret')

    def test_default_authenticate_ok(self):
        flag, user = default_authenticate('admin', 'secret')
        self.assertTrue(flag)
        self.assertIsNotNone(user)

    def test_default_authenticate_bad_password(self):
        flag, d = default_authenticate('admin', 'wrong')
        self.assertFalse(flag)
        self.assertIn('password', d)

    def test_default_authenticate_missing_user(self):
        flag, d = default_authenticate('nobody', 'secret')
        self.assertFalse(flag)


if __name__ == '__main__':
    unittest.main()