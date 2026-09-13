#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""uliweb.core.uaml 的单元测试。

UAML：缩进式标记 → HTML。覆盖 tag/id/class/属性、嵌套、注释、verbatim、{{{...}}} 块。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uliweb.core.uaml import Parser


class UamlParserTestCase(unittest.TestCase):
    def _run(self, text):
        return Parser(text).run()

    def test_simple_tag(self):
        self.assertEqual(self._run('p'), '<p></p>')

    def test_tag_with_id_and_class(self):
        out = self._run('div#main.red')
        self.assertIn('id="main"', out)
        self.assertIn('class="red"', out)
        self.assertTrue(out.startswith('<div'))

    def test_tag_with_attribute(self):
        out = self._run('input name=field1')
        self.assertIn('name="field1"', out)

    def test_nested_tags(self):
        out = self._run('div\n    p Hello')
        self.assertIn('<div>', out)
        self.assertIn('<p Hello></p>', out)
        self.assertTrue(out.rstrip().endswith('</div>'))

    def test_comment(self):
        out = self._run('div\n    // note')
        self.assertIn('<!--  note -->', out)

    def test_verbatim(self):
        out = self._run('div\n    | raw text')
        self.assertIn(' raw text', out)

    def test_verbatim_block(self):
        text = '{{{\n<script>\nvar x;\n</script>\n}}}'
        out = self._run(text)
        self.assertIn('<script>', out)
        self.assertIn('var x;', out)
        self.assertIn('</script>', out)

    def test_default_div_when_no_tag(self):
        out = self._run('.content')
        self.assertTrue(out.startswith('<div'))
        self.assertIn('class="content"', out)


if __name__ == '__main__':
    unittest.main()