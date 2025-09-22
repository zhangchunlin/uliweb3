# SimpleFrame.py 文档

## 概述

SimpleFrame.py 是 Uliweb 框架的核心模块，提供了 Web 应用程序的基本构建块。它包括请求/响应处理、URL 路由、模板渲染、中间件支持和应用程序分发功能。

## 主要组件

### 1. 全局对象

该模块定义了几个在整个应用程序中可访问的全局对象：

- `request`：当前请求对象（LocalProxy 到 Request）
- `response`：当前响应对象（LocalProxy 到 Response）
- `settings`：应用程序设置（LocalProxy 到 pyini.Ini）
- `application`：主应用程序分发器（LocalProxy 到 Dispatcher）

### 2. 核心类

#### Request
扩展 `werkzeug.Request`，增加以下属性：
- `GET`, `POST`, `params`, `FILES`：访问请求数据
- `json`：解析请求体中 JSON 数据的属性
- `is_xhr`：检测 XMLHttpRequests 的属性

#### Response
扩展 `werkzeug.Response`，增加：
- `write(value)`：向响应流写入内容的方法

#### Finder
用于访问设置中定义的对象的工具类：
- `decorators`：访问设置中定义的装饰器函数
- `functions`：访问设置中定义的工具函数

#### Dispatcher
主应用程序类，处理：
- 应用程序初始化和配置
- URL 路由和请求分发
- 中间件处理
- 模板渲染
- 错误处理

#### ContextStorage
用于维护具有全局和局部作用域的上下文变量的存储类。

### 3. 异常类

#### HTTPError
用于 HTTP 错误的自定义异常，支持自定义错误页面。

#### RedirectException
用于在视图函数中触发 HTTP 重定向的异常。

### 4. 装饰器和工具

#### @expose
用于将函数暴露为带有路由规则的 URL 端点的装饰器。

#### @GET, @POST
用于暴露具有特定 HTTP 方法的函数的便捷装饰器。

#### @json
用于自动将函数结果序列化为 JSON 响应的装饰器。

#### @jsonp
支持回调处理的 JSONP 装饰器。

#### @CORS
支持跨域资源共享的装饰器。

### 5. URL 处理函数

#### url_for(endpoint, **values)
为端点生成 URL，支持：
- 特定域的 URL
- URL 格式化
- 外部 URL

#### get_url_adapter(_domain_name)
获取特定域的 URL 适配器。

#### get_rule(url)
获取 URL 的路由规则信息。

### 6. 应用程序管理函数

#### get_apps(apps_dir, ...)
收集和解析应用程序依赖。

#### get_settings(project_dir, ...)
从多个源收集和合并设置。

#### collect_settings(project_dir, ...)
从应用程序收集所有设置文件。

### 7. 响应工具

#### redirect(location, code=302)
创建重定向响应，特殊处理 XHR 请求。

#### error(message='', errorpage=None, ...)
抛出自定义错误消息的 HTTPError 异常。

#### function(fname, *args, **kwargs)
调用设置中定义的函数。

## 分发器功能

Dispatcher 类是框架的核心，具有以下关键方法：

### 初始化
- `__init__`：使用配置设置应用程序
- `init`：初始化所有应用程序组件
- `install_settings`：处理和安装应用程序设置
- `install_apps`：加载和初始化应用程序
- `init_urls`：设置 URL 路由规则

### 请求处理
- `__call__`：请求处理的 WSGI 入口点
- `_open`：主请求处理方法
- `prepare_request`：准备请求上下文
- `call_view`：在适当上下文中执行视图函数
- `wrap_result`：处理视图函数结果

### 中间件支持
- `install_middlewares`：安装和排序中间件类
- `_sort_middlewares`：按顺序排序中间件
- `_get_middlewares_classes`：分类中间件方法

### 模板处理
- `template`：使用上下文渲染模板
- `render`：从模板创建响应对象
- `install_template_loader`：设置模板加载系统

### 错误处理
- `not_found`：处理 404 错误
- `internal_error`：处理 500 错误
- `_page_not_found`：在调试模式下生成详细的 404 页面

## 配置

该模块使用分层配置方法：
1. 来自 `default_settings.ini` 的默认设置
2. 来自 `settings.ini` 文件的应用程序设置
3. 来自项目级配置的项目设置
4. 来自 `local_settings.ini` 的本地设置

## 线程安全

该模块使用 Werkzeug 的 `Local` 和 `LocalManager` 来确保请求/响应对象和其他上下文相关数据的线程安全。

## 集成点

- **Werkzeug**：请求/响应对象和 URL 路由的基础
- **pyini**：配置管理
- **模板系统**：渲染和布局支持
- **分发系统**：事件处理和钩子
