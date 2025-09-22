# Uliweb 管理命令

`manage.py` 脚本是管理 Uliweb 项目的命令行接口。它提供了各种命令用于创建应用、项目、模块以及执行其他开发任务。

## 使用方法

```bash
python manage.py <command> [options] [args]
```

## 全局选项

- `-h, --help`: 显示帮助信息
- `--version`: 显示版本信息
- `-v, --verbose`: 启用详细输出
- `-y, --yes`: 对所有提示回答是
- `--settings`: 指定设置文件（默认：settings.ini）
- `--local-settings`: 指定本地设置文件（默认：local_settings.ini）
- `--apps-dir`: 指定应用目录（默认：apps）

## 命令

### makeapp

根据应用名称参数创建新应用。

**用法:**
```bash
python manage.py makeapp [options] appname
```

**选项:**
- `--simple`: 创建最简结构的应用文件夹

### makepkg

创建新的 Python 包目录。

**用法:**
```bash
python manage.py makepkg <pkgname1, pkgname2, ...>
```

### makeproject

根据项目名称创建新的项目目录。

**用法:**
```bash
python manage.py makeproject project_name
```

### makemodule

根据模块名称创建新的 Uliweb 模块目录。

**用法:**
```bash
python manage.py makemodule module_name
```

### support

为现有项目添加特殊支持，例如：tornado、gevent、gevent-socketio。

**用法:**
```bash
python manage.py support supported_type
```

### config

输出不同支持的配置信息，例如：nginx、uwsgi 等。

**用法:**
```bash
python manage.py config supported_type
```

### exportstatic

将所有已安装应用的静态目录导出到输出目录。

**用法:**
```bash
python manage.py exportstatic [options] output_directory [app1, app2, ...]
```

**选项:**
- `-c, --check`: 检查输出文件或目录是否有冲突

### export

将所有已安装的应用或指定模块的源文件导出到输出目录。

**用法:**
```bash
python manage.py export [options] [module1 module2]
```

**选项:**
- `-d`: 导出文件的输出目录

### call

根据命令参数为每个已安装的应用调用 <exefile>.py。

**用法:**
```bash
python manage.py call [options] exefile
```

**选项:**
- `-a`: 应用名称。如果不提供，则在整个项目中搜索 exefile
- `--without-application`: 是否先创建应用，默认为 False
- `--gevent`: 在执行脚本前应用 gevent monkey patch

### install

安装 [appname,...] 在 requirements.txt 中列出的额外模块。

**用法:**
```bash
python manage.py install [appname]
```

### makecmd

在应用或当前目录中创建 commands.py。

**用法:**
```bash
python manage.py makecmd appname
```

### runserver

启动新的开发服务器。也可以在没有完整项目的情况下启动应用。

**用法:**
```bash
python manage.py runserver [options] [appname appname ...]
```

**选项:**
- `-h`: 主机名或 IP（默认：localhost）
- `-p`: 端口号（默认：8000）
- `--no-reload`: 是否自动重新加载开发服务器（默认：True）
- `--no-debug`: 是否自动启用调试模式（默认：True）
- `--nocolor`: 禁用彩色日志信息（默认：False）
- `--thread`: 是否使用线程服务器模式（默认：False）
- `--processes`: 启动的进程数（默认：1）
- `--ssl`: 使用 SSL 访问 http
- `--ssl-key`: SSL 私钥文件名（默认：ssl.key）
- `--ssl-cert`: SSL 证书文件名（默认：ssl.cert）
- `--tornado`: 使用 tornado 启动 uliweb 服务器
- `--gevent`: 使用 gevent 启动 uliweb 服务器
- `--gevent-socketio`: 使用 gevent-socketio 启动 uliweb 服务器
- `--coverage`: 使用 coverage 启动 uliweb 服务器
- `--trace-print`: 跟踪打印语句

### develop

启动包含 develop 应用的开发服务器。

**用法:**
```bash
python manage.py develop [options] [appname appname ...]
```

（选项与 runserver 相同）

### staticize

将网站静态化为静态网页。

**用法:**
```bash
python manage.py staticize [options] output_directory
```

**选项:**
- `-l`: 网站语言，默认无语言指定

### shell

创建新的交互式 Python shell 环境。

**用法:**
```bash
python manage.py shell [options] <filename>
```

**选项:**
- `-I`: 不使用 ipython
- `-n, --notebook`: 启动 ipython notebook
- `-m, --module`: 启动 shell 时执行的模块名称

### find

在 uliweb 中查找对象，例如：视图、模板、静态文件等。

**用法:**
```bash
python manage.py find [options]
```

**选项:**
- `-t, --template`: 根据模板文件名查找模板文件路径
- `-u, --url`: 根据 URL 查找视图函数路径
- `-U, --search-url`: 根据 URL 模式搜索 URL
- `-c, --static`: 根据静态文件名查找静态文件路径
- `-m, --model`: 根据模型名称查找模型定义
- `-o, --option`: 查找在哪个 settings.ini 中定义的 ini 选项
- `--tree`: 查找模板调用树，应与 -t 选项一起使用
- `--blocks`: 显示模板中定义的块，仅在搜索模板时可用
- `--with-filename`: 显示模板中定义的块及其模板文件名
- `--source`: 输出模板生成的 Python 源代码
- `--comment`: 输出模板生成的 Python 源代码并为每行输出注释

### validatetemplate

验证模板文件语法。

**用法:**
```bash
python manage.py validatetemplate [appname] [-f tempaltefile]
```

**选项:**
- `-f`: 要验证的模板文件名
