# Uliweb 命令系统文档

## 概述

Uliweb 命令系统是框架的核心组件之一，负责处理命令行工具的定义、解析和执行。该系统提供了灵活的命令扩展机制，允许开发者创建自定义命令并集成到 Uliweb 的命令行工具中。

## 核心组件

### CommandError 异常类

`CommandError` 是命令执行过程中发生错误时抛出的异常类。当命令执行出现问题时，应该抛出此异常，系统会自动将其转换为友好的错误信息输出到 stderr。

```python
class CommandError(Exception):
    pass
```

### 工具函数

#### get_answer 函数

用于从标准输入获取用户回答，支持默认值和退出选项。

参数：
- `message`: 提示信息
- `answers`: 可接受的答案，默认为 'Yn'
- `default`: 默认答案，默认为 'Y'
- `quit`: 退出答案，默认为 'n'

#### get_commands 函数

从指定模块中查找所有命令类。

参数：
- `mod`: 要搜索的模块

#### get_input 函数

获取用户输入，支持默认值和选项验证。

参数：
- `prompt`: 提示信息
- `default`: 默认值
- `choices`: 可选值列表
- `option_value`: 选项值（如果提供则直接返回）

### CommandMetaclass 元类

命令类的元类，用于处理选项列表的继承。

特性：
- 自动合并父类的选项列表
- 支持选项继承控制

### Command 基础命令类

所有命令类的基类，提供了命令执行的基本框架。

#### 类属性

- `option_list`: 命令选项列表
- `help`: 命令帮助信息
- `args`: 命令参数说明
- `check_apps_dirs`: 是否检查应用目录
- `check_apps`: 是否检查应用
- `skip_options`: 是否跳过未定义选项

#### 主要方法

- `create_parser(prog_name, subcommand)`: 创建选项解析器
- `usage(subcommand)`: 生成使用说明
- `print_help(prog_name, subcommand)`: 打印帮助信息
- `get_apps(global_options, include_apps)`: 获取应用列表
- `get_application(global_options, default_settings)`: 获取应用实例
- `run_from_argv(prog, subcommand, global_options, argv)`: 从命令行参数运行
- `execute(args, options, global_options)`: 执行命令
- `handle(options, global_options, *args)`: 处理命令逻辑（需子类实现）

### NewFormatter 格式化器

自定义帮助信息格式化器，用于格式化全局选项的显示。

### NewOptionParser 选项解析器

自定义选项解析器，支持跳过未定义选项并将其保留在参数中。

### CommandManager 命令管理器

负责管理所有命令的执行流程。

#### 类属性

- `usage_info`: 使用信息模板

#### 主要方法

- `get_commands(global_options)`: 获取命令列表
- `print_help_info(global_options)`: 打印帮助信息
- `fetch_command(global_options, subcommand)`: 获取指定命令
- `execute(callback)`: 执行命令
- `do_command(args, global_options)`: 处理命令执行

### ApplicationCommandManager 应用命令管理器

应用级别的命令管理器，定义了常用的全局选项。

#### 选项列表

- `--help`: 显示帮助信息
- `-v, --verbose`: 详细输出模式
- `-s, --settings`: 设置文件名
- `-y, --yes`: 自动确认提示
- `-L, --local_settings`: 本地设置文件名
- `--project`: 项目目录
- `--pythonpath`: Python 路径
- `--version`: 显示版本信息
- `-E`: 环境变量定义

### execute_command_line 函数

命令行执行入口函数。

参数：
- `argv`: 命令行参数
- `commands`: 命令字典
- `prog_name`: 程序名称
- `callback`: 回调函数

## 使用示例

### 创建自定义命令

要创建自定义命令，需要继承 `Command` 类并实现 `handle` 方法：

```python
from uliweb.core.commands import Command

class MyCommand(Command):
    name = 'mycommand'
    help = '这是一个示例命令'
    args = '<arg1> <arg2>'
    option_list = (
        make_option('-f', '--file', dest='filename', help='输入文件名'),
        make_option('-d', '--debug', action='store_true', help='调试模式'),
    )

    def handle(self, options, global_options, *args):
        # 实现命令逻辑
        if options.debug:
            print("调试模式开启")

        if options.filename:
            print(f"处理文件: {options.filename}")

        for arg in args:
            print(f"参数: {arg}")
```

### 注册命令

命令可以通过模块自动发现机制注册，或手动添加到命令管理器中。

#### 自动发现机制

Uliweb 会自动从 `commands.py` 文件中发现命令类：

```python
# 在应用的 commands.py 文件中
from uliweb.core.commands import Command

class MyAppCommand(Command):
    name = 'myapp'
    help = '应用特定命令'

    def handle(self, options, global_options, *args):
        print("执行应用命令")
```

#### 手动注册

也可以通过回调函数手动注册命令：

```python
def get_commands(global_options):
    from mymodule import MyCommand
    return {
        'mycommand': MyCommand,
        'othercommand': OtherCommand,
    }

# 在命令行执行时
execute_command_line(commands=get_commands)
```

### 命令行使用示例

```bash
# 显示帮助信息
uliweb help

# 显示特定命令帮助
uliweb help mycommand

# 执行自定义命令
uliweb mycommand -f test.txt arg1 arg2

# 使用全局选项
uliweb --project /path/to/project mycommand --debug
```

## 内部工作机制

### 命令执行流程

1. **参数解析**：`ApplicationCommandManager` 解析全局选项
2. **环境设置**：处理 Python 路径、环境变量等设置
3. **命令查找**：根据子命令名称查找对应的命令类
4. **命令执行**：创建命令实例并执行 `run_from_argv` 方法
5. **选项解析**：命令类解析特定选项
6. **逻辑处理**：调用 `handle` 方法执行具体逻辑

### 选项继承机制

通过 `CommandMetaclass` 元类实现选项列表的自动继承：

```python
class BaseCommand(Command):
    option_list = (
        make_option('--base', help='基础选项'),
    )

class DerivedCommand(BaseCommand):
    option_list = (
        make_option('--derived', help='派生选项'),
    )
    # 自动继承 BaseCommand 的选项列表
```

## 高级用法

### 创建子命令管理器

可以创建多层级的命令结构：

```python
class MyCommandManager(CommandManager):
    usage_info = "%prog [options] <subcommand> [args]"

    def __init__(self, argv=None, commands=None, prog_name=None, global_options=None):
        commands = {
            'sub1': SubCommand1,
            'sub2': SubCommand2,
        }
        super(MyCommandManager, self).__init__(argv, commands, prog_name, global_options)
```

### 自定义选项处理

重写选项解析逻辑：

```python
class CustomCommand(Command):
    skip_options = True  # 跳过未定义选项

    def handle(self, options, global_options, *args):
        # args 中包含所有未解析的参数
        print(f"未解析参数: {args}")
```

### 应用环境集成

在命令中访问 Uliweb 应用环境：

```python
class AppAwareCommand(Command):
    def handle(self, options, global_options, *args):
        # 获取应用实例
        app = self.get_application(global_options)

        # 访问应用配置
        debug = app.settings.DEBUG
        print(f"调试模式: {debug}")

        # 访问数据库等资源
        from uliweb import orm
        users = orm.User.all()
```

## 扩展机制

Uliweb 命令系统支持以下扩展方式：

1. **继承 Command 类**：创建新的命令类
2. **自定义选项**：通过 `option_list` 属性添加命令选项
3. **重写方法**：根据需要重写基类方法
4. **命令组合**：通过 CommandManager 组织多个子命令
5. **元类扩展**：使用 CommandMetaclass 控制选项继承行为

## 最佳实践

### 错误处理

```python
def handle(self, options, global_options, *args):
    try:
        # 业务逻辑
        if not args:
            raise CommandError("必须提供参数")
    except Exception as e:
        # 记录详细错误信息
        log.exception(e)
        raise CommandError(f"命令执行失败: {str(e)}")
```

### 用户交互

```python
def handle(self, options, global_options, *args):
    if not options.yes:
        answer = get_answer("确认执行此操作?", default='N')
        if answer != 'Y':
            print("操作已取消")
            return

    # 安全执行操作
```

### 配置管理

```python
def handle(self, options, global_options, *args):
    # 使用项目配置
    project_dir = global_options.project
    settings_file = global_options.settings

    # 加载特定配置
    config = load_config(project_dir, settings_file)
```

## 常见问题

### 选项冲突

避免选项名称冲突，特别是短选项（单字母选项）。

### 路径处理

正确处理相对路径和绝对路径，使用 `os.path` 模块进行路径操作。

### 环境变量

使用 `-E` 选项设置环境变量时，确保格式正确：`-EKEY=VALUE`。

## 参考资源

- Uliweb 官方文档
- Python optparse 模块文档
- 现有命令实现（如 `uliweb/contrib/auth/commands.py`）
