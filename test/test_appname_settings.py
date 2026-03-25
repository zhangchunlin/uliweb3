"""
#{appname} 设置测试

测试 settings.ini 中的 #{appname} 变量替换机制
"""
import os
import sys
import tempfile
import shutil
import unittest

# 添加项目路径
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, path)


class AppnameSettingsTest(unittest.TestCase):
    """测试 #{appname} 设置变量"""

    def setUp(self):
        """创建临时测试项目"""
        self.test_dir = tempfile.mkdtemp()
        self.apps_dir = os.path.join(self.test_dir, 'apps')
        os.makedirs(self.apps_dir)

        # 创建测试应用的 settings.ini
        self.app_name = 'testapp'
        self.app_dir = os.path.join(self.apps_dir, self.app_name)
        os.makedirs(self.app_dir)

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_appname_replacement_in_settings(self):
        """测试 #{appname} 在 settings.ini 中被正确替换"""
        from uliweb.utils.pyini import Ini

        # 创建测试应用的 settings.ini，使用 #{appname}
        settings_content = '''
[TEST]
setting1 = '#{appname}.setting1'
setting2 = '#{appname}.setting2'
app_name = '#{appname}'
'''
        settings_file = os.path.join(self.app_dir, 'settings.ini')
        with open(settings_file, 'w') as f:
            f.write(settings_content)

        # 创建 Ini 实例并加载设置
        x = Ini(lazy=True, basepath=self.apps_dir)

        # 设置预定义变量 appname
        x.set_pre_variables({'appname': self.app_name})

        # 读取设置
        x.read(settings_file)
        x.freeze()

        # 验证 #{appname} 被替换为实际的应用名
        test_section = x.get('TEST', {})
        # 获取实际值（Lazy 对象需要 .get_value() 或 str()）
        setting1 = test_section.get('setting1')
        if hasattr(setting1, 'get_value'):
            setting1 = setting1.get_value()
        setting2 = test_section.get('setting2')
        if hasattr(setting2, 'get_value'):
            setting2 = setting2.get_value()
        app_name_val = test_section.get('app_name')
        if hasattr(app_name_val, 'get_value'):
            app_name_val = app_name_val.get_value()

        self.assertEqual(setting1, f'{self.app_name}.setting1')
        self.assertEqual(setting2, f'{self.app_name}.setting2')
        self.assertEqual(app_name_val, self.app_name)

    def test_appname_with_different_apps(self):
        """测试多个应用的 #{appname} 替换"""
        from uliweb.utils.pyini import Ini

        # 创建第二个应用
        app2_name = 'anotherapp'
        app2_dir = os.path.join(self.apps_dir, app2_name)
        os.makedirs(app2_dir)

        # 应用1的 settings
        settings1_content = '''
[TEST]
value = '#{appname}.value'
'''
        with open(os.path.join(self.app_dir, 'settings.ini'), 'w') as f:
            f.write(settings1_content)

        # 应用2的 settings
        settings2_content = '''
[TEST]
value = '#{appname}.value'
'''
        with open(os.path.join(app2_dir, 'settings.ini'), 'w') as f:
            f.write(settings2_content)

        # 加载应用1的设置
        x = Ini(lazy=True, basepath=self.apps_dir)
        x.set_pre_variables({'appname': self.app_name})
        x.read(os.path.join(self.app_dir, 'settings.ini'))
        x.freeze()

        app1_value = x.get('TEST', {}).get('value')
        if hasattr(app1_value, 'get_value'):
            app1_value = app1_value.get_value()

        # 加载应用2的设置
        y = Ini(lazy=True, basepath=self.apps_dir)
        y.set_pre_variables({'appname': app2_name})
        y.read(os.path.join(app2_dir, 'settings.ini'))
        y.freeze()

        app2_value = y.get('TEST', {}).get('value')
        if hasattr(app2_value, 'get_value'):
            app2_value = app2_value.get_value()

        # 验证每个应用的 #{appname} 被正确替换
        self.assertEqual(app1_value, f'{self.app_name}.value')
        self.assertEqual(app2_value, f'{app2_name}.value')

    def test_appname_not_replaced_when_not_set(self):
        """测试未设置 appname 时 #{appname} 不会被替换"""
        from uliweb.utils.pyini import Ini

        settings_content = '''
[TEST]
value = '#{appname}.value'
'''
        settings_file = os.path.join(self.app_dir, 'settings.ini')
        with open(settings_file, 'w') as f:
            f.write(settings_content)

        # 不设置 appname
        x = Ini(lazy=True, basepath=self.apps_dir)
        # 不调用 set_pre_variables
        x.read(settings_file)
        x.freeze()

        # 验证 #{appname} 保持原样（被替换为空字符串）
        test_section = x.get('TEST', {})
        # 当 appname 未设置时，#{appname} 会被替换为空字符串
        self.assertEqual(test_section.get('value'), '.value')

    def test_set_pre_variables_method(self):
        """测试 set_pre_variables 方法"""
        from uliweb.utils.pyini import Ini

        x = Ini(lazy=True, basepath=self.apps_dir)

        # 测试设置预定义变量
        x.set_pre_variables({'appname': 'mytestapp'})
        self.assertEqual(x._pre_variables.get('appname'), 'mytestapp')

        # 更新预定义变量
        x.set_pre_variables({'appname': 'updatedapp'})
        self.assertEqual(x._pre_variables.get('appname'), 'updatedapp')

        # 添加多个变量
        x.set_pre_variables({'appname': 'test', 'version': '1.0'})
        self.assertEqual(x._pre_variables.get('appname'), 'test')
        self.assertEqual(x._pre_variables.get('version'), '1.0')


class AppnameInSimpleFrameTest(unittest.TestCase):
    """测试 SimpleFrame 中的 #{appname} 处理"""

    def test_collect_settings_returns_appname_tuple(self):
        """测试 collect_settings 返回 (appname, filepath) 元组"""
        from uliweb.core.SimpleFrame import collect_settings

        # 创建一个临时项目目录
        with tempfile.TemporaryDirectory() as tmpdir:
            apps_dir = os.path.join(tmpdir, 'apps')
            os.makedirs(apps_dir)

            # 创建一个简单的应用
            app_name = 'myapp'
            app_dir = os.path.join(apps_dir, app_name)
            os.makedirs(app_dir)

            # 创建应用的 settings.ini
            settings_file = os.path.join(app_dir, 'settings.ini')
            with open(settings_file, 'w') as f:
                f.write('[TEST]\nvalue = test\n')

            # 调用 collect_settings
            settings = collect_settings(
                tmpdir,
                include_apps=[app_name],
                settings_file='settings.ini',
                local_settings_file='local_settings.ini'
            )

            # 验证返回的设置包含 (appname, filepath) 元组
            found = False
            for item in settings:
                if isinstance(item, tuple) and len(item) == 2:
                    appname, filepath = item
                    if appname == app_name and filepath == settings_file:
                        found = True
                        break

            self.assertTrue(f"Should find (appname='{app_name}', filepath='{settings_file}') in settings", found)


if __name__ == '__main__':
    unittest.main()