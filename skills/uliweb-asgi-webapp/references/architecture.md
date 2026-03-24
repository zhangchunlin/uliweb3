# Uliweb 体系结构和机制

## 组织结构

Uliweb 认为一个项目是由不同的模块组成，所以采用了类似于Django App的方式来进行项目的组织，它们都统一放在 apps 目录下。同时 Uliweb 的App可以是任何符合Uliweb要求的Python包（使用uliweb makeapp appname创建即可），并且可以是独立的Python模块放在非apps的地方，只要可以导入就可以了。Uliweb 的 app 的组织重点考虑了功能及开发的独立性、复用性和配置化，每个 app 可以有自己独立的：

- settings.ini - 配置文件
- templates目录 - 模板文件
- static目录 - 静态文件
- views文件 - 视图代码

这种组织方式使得Uliweb的App重用更为方便。

apps的结构为：

```
apps/
    .gitignore
    __init__.py
    settings.ini
    local_settings.ini
    app1/
        __init__.py
        settings.ini
        templates/
        static/
    app2/
        __init__.py
        settings.ini
        templates/
        static/
```

项目根目录下还有：
- asgi_handler.py - ASGI 启动文件，用于部署到 ASGI 服务器
- setup.py - 用于安装项目为可复用模块

## App管理

一个项目可以由一个App或多个App组成，而且每个App的结构不一定要求完整，因此一个App可以：

- 只有一个settings.ini - 配置初始化工作
- 只有templates - 提供公共模板
- 只有static - 提供公共静态文件
- 其它内容

Uliweb在启动时对于apps下的App有两种处理策略：

1. 认为全部App都是有效的
2. 根据 `apps/settings.ini` 和 `apps/local_settings.ini` 中的配置项 `INSTALLED_APPS` 来决定哪些App是有效的

Uliweb在启动时会根据有效的App来导入它们自己的settings.ini文件，并将其中配置项进行合并最终形成一个完整的 `settings` 变量供App来使用。

## Settings处理

Uliweb会按以下顺序来处理 settings.ini 文件：

1. uliweb/core/default_settings.ini - 初始的settings信息
2. 按定义的顺序导入每个App下的 settings.ini 信息
3. 导入 apps/settings.ini 信息
4. 导入 apps/local_settings.ini 信息

如果出现同名配置项，则对于不可变数据类型，后定义的项将覆盖前面定义的值。如果是可变数据类型，则将进行数据合并。

## MVT框架

Uliweb 采用 MVT 的框架模式：

- **Model**: 基于 SqlAlchemy 封装的 ORM
- **View**: 函数或类的方式，通过向函数注入对象来实现
- **Template**: 自动映射，当view函数返回dict时自动查找模板并处理

### View函数

在Uliweb中，一个view函数可以简单地定义为：

```python
@expose('/')
def index():
    return {}
```

每个view函数都应与一个或多个URL定义相匹配。

### Template模板

当view函数返回一个dict变量时，会自动查找模板并进行处理。缺省模板文件名与view函数名一样，但扩展名为.html。

## URL处理

Uliweb支持两种URL的定义方式：

1. 将URL定义在每个view模块中，通过expose来定义
2. 在settings.ini中的[EXPOSES]中进行定义

URL的格式采用Starlette的routing模块处理方式。可以定义参数，可以反向生成URL。

- expose - 用来将URL与view方法进行映射
- url_for - 用来根据view方法反向生成URL

## 扩展处理

Uliweb提供了多种扩展的能力：

- plugin扩展 - 预设了一些调用点，可以在settings.ini中配置
- middleware扩展 - 与Django的机制类似
- views模块的初始化处理 - 定义__begin__函数作为入口
