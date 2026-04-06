# 静态文件服务(Static Files)

用于向uliweb中提供静态文件的服务。通常来说，静态文件服务分两种场景，一种是开发
环境，一种是生产环境。而staticfiles主要是使用在开发环境，在生产环境中，一般先
通过:

```
uliweb exportstatic static
```

将所有静态文件导出到一个统一的静态目录下，然后通过web server的静态文件处理来统
一进行服务。但是在开发环境下，一般是使用开发服务器，因此，静态文件的处理需要使
用这个app来进行。

## 主要功能

1. 向view和模板的运行环境中注入 `url_for_static` 方法，可以方便生成静态文件的URL
2. 为了在开发服务器中也提供较好的性能，提供ASGI中间件，可以直接提供静态文件处理，
   而跳过其它应用级的app的处理。相当于一个旁路处理，会跳过如session之类的处理。
3. 在生成url_for_static的时候，可以根据配置项中的 `STATIC_VER` 来自动在静态URL后
   面添加 `?ver=xxx` 的内容。这样，当静态文件发生变化，可以统一在 settings.ini
   中修改 STATIC_VER 的值，从而使那些直接或间接使用 `url_for_static()` 方法所生成的
   URL发生变化，可以让浏览器重新从后台获取文件，避免因缓存带来的问题。

{% alert class=info %}
间接使用 `url_for_static()` 的方法如: `{{use "xxx"}}` 和 `{{link "link"}}` 的处理。
{% endalert %}

## 配置项说明

```ini
[GLOBAL]
MIDDLEWARES = ['asgi_middleware_staticfiles']
STATIC_VER = None

[asgi_middleware_staticfiles]
CLASS = 'uliweb.contrib.staticfiles.asgi_staticfiles.StaticFilesMiddleware'
STATIC_URL = '/static/'

[STATICFILES]
STATIC_FOLDER = ''
```

### 配置项详解

**GLOBAL/STATIC_VER**
- 为 None 或 "空" 值时，不输出
- 为非空值时将在静态URL后面输出 `?ver=${STATIC_VER}` 的值

**asgi_middleware_staticfiles/STATIC_URL**
- 静态URL的前缀。在Uliweb中，所有静态文件都有相同的前缀

## 使用方法

### 在模板中使用

```html
<link href="{{=url_for_static('styles/reset.css')}}" rel="stylesheet" type="text/css" />
<link href="{{=url_for_static('styles/index/style.css')}}" rel="stylesheet" type="text/css" />
<img src="{{= url_for_static('delete.gif') }}"/>
```

使用 `{{=url_for_static()}}` 来生成静态链接。

### 在 Python 代码中使用

```python
from uliweb import functions

# 获取静态文件URL
static_url = functions.url_for_static('styles/style.css')
```

## 静态域名输出

在 uliweb 的 default_settings.ini 中增加了:

```ini
[DOMAINS]
default = {'domain':'', 'display':False}
static = {'domain':'', 'display':False}
```

它定义了不同名字的域名信息。只要在你的 settings 中定义成:

```ini
[DOMAINS]
static = {'domain':'http://static.com', 'display':True}
```

这样，当使用 `url_for_static` 时，静态URL将自动添加静态域名。如果 `display` 为 False，则
缺省不输出。但是如果向 `url_for_static` 中传入 `_external=True` 时，则也会输出域名
信息。

## 版本控制

通过设置 `STATIC_VER` 可以实现静态文件版本控制：

```ini
[GLOBAL]
STATIC_VER = '1.0.0'
```

这样生成的URL会是：`/static/styles/style.css?ver=1.0.0`

当修改 STATIC_VER 的值后，所有使用 `url_for_static()` 生成的URL都会自动更新，强制浏览器重新加载静态文件。