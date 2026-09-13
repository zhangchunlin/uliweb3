#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""core.template 模板引擎的单元测试（常用节点子集）。

标签语法：语句用 {{ ... }}（Python 语句，if/for/else 需带冒号），输出用 {{<< expr }}。
覆盖：{{<< }} 输出、{{ if/for }} 控制流、{{ block }}、{{ extends }}、{{ include }}、
{{ apply }}、{{ link }}、{{ BEGIN_TAG/END_TAG }}、Loader 主流程与 ParseError。
"""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.core import template


def render(text, vars=None, name='<string>', loader=None):
    """构造 Template 并渲染，返回字符串结果。"""
    t = template.Template(text, name=name, loader=loader)
    return t.generate(vars or {})


class TemplateRenderTestCase(unittest.TestCase):
    """纯字符串模板（无需 loader）的基础渲染测试。"""

    def test_plain_text(self):
        self.assertEqual(render('hello'), 'hello')

    def test_variable_output(self):
        self.assertEqual(render('hello {{<< name }}', {'name': 'world'}), 'hello world')

    def test_missing_variable_raises(self):
        # 未定义变量直接引用会抛 NameError（需用 defined() 显式兜底）
        self.assertRaises(NameError, lambda: render('a{{<< undef }}b', {}))

    def test_expression_arithmetic(self):
        self.assertEqual(render('{{<< 1+2 }}'), '3')

    def test_expression_method(self):
        self.assertEqual(render('{{<< name.upper() }}', {'name': 'abc'}), 'ABC')

    def test_if_true(self):
        tpl = '{{ if ok: }}yes{{ end }}'
        self.assertEqual(render(tpl, {'ok': True}), 'yes')
        self.assertEqual(render(tpl, {'ok': False}), '')

    def test_if_else(self):
        tpl = '{{ if ok: }}yes{{ else: }}no{{ end }}'
        self.assertEqual(render(tpl, {'ok': True}), 'yes')
        self.assertEqual(render(tpl, {'ok': False}), 'no')

    def test_for_loop(self):
        tpl = '{{ for x in items: }}[{{<< x }}]{{ end }}'
        self.assertEqual(render(tpl, {'items': [1, 2, 3]}), '[1][2][3]')

    def test_begin_end_tag(self):
        self.assertEqual(render('{{ BEGIN_TAG }}x{{ END_TAG }}'), '{{x}}')

    def test_apply(self):
        # apply 需要一个接受 bytes 的可调用对象（内部 buffer 为 bytes，escape 走 _tt_utf8）。
        # 修复前 _ApplyBlock.generate 缩进错乱对任意输入抛 SyntaxError。
        tpl = '{{ apply upper }}{{<< name }}{{ end }}'
        self.assertEqual(render(tpl, {'name': 'tom', 'upper': bytes.upper}), 'TOM')

    def test_apply_plain_text(self):
        tpl = '{{ apply upper }}abc{{ end }}'
        self.assertEqual(render(tpl, {'upper': bytes.upper}), 'ABC')


class TemplateParseErrorTestCase(unittest.TestCase):
    def test_extra_end(self):
        self.assertRaises(template.ParseError, lambda: render('{{ end }}'))

    def test_block_missing_name(self):
        self.assertRaises(template.ParseError, lambda: render('{{ block }}{{ end }}'))

    def test_apply_missing_method(self):
        self.assertRaises(template.ParseError, lambda: render('{{ apply }}x{{ end }}'))


class TemplateLoaderTestCase(unittest.TestCase):
    """Loader + 文件加载 + block/extends/include 主流程测试。"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.loader = template.Loader([self.dir])

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _write(self, name, content):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_load_and_render(self):
        self._write('page.html', 'hi {{<< name }}')
        t = self.loader.load('page.html')
        self.assertEqual(t.generate({'name': 'tom'}), 'hi tom')

    def test_load_missing_raises(self):
        self.assertRaises(template.ParseError, self.loader.load, 'nope.html')

    def test_load_caching(self):
        self._write('c.html', 'v1')
        t1 = self.loader.load('c.html')
        t2 = self.loader.load('c.html')
        self.assertIs(t1, t2)

    def test_block(self):
        self._write('base.html', 'A{{ block body }}base{{ end }}B')
        t = self.loader.load('base.html')
        self.assertEqual(t.generate(), 'AbaseB')

    def test_extends(self):
        self._write('base.html', 'head[{{ block content }}base{{ end }}]tail')
        self._write('child.html', '{{ extends "base.html" }}{{ block content }}child{{ end }}')
        t = self.loader.load('child.html')
        self.assertEqual(t.generate(), 'head[child]tail')

    def test_include(self):
        self._write('part.html', '{{<< x }}')
        self._write('page.html', 'A{{ include "part.html" }}B')
        t = self.loader.load('page.html')
        self.assertEqual(t.generate({'x': 7}), 'A7B')


if __name__ == '__main__':
    unittest.main()