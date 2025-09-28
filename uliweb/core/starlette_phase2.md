# Uliweb 迁移到 Starlette - 阶段二：功能完整性迁移详细任务清单

## 概述
阶段二主要完成 Uliweb 从 Werkzeug 到 Starlette 的功能完整性迁移，包括中间件系统迁移、模板系统适配、会话管理、事件分发系统、命令系统等核心功能的异步化改造。

## 详细任务清单

### 1. 中间件系统迁移

#### 1.1 ASGI 中间件适配器实现
- [ ] 创建 `ASGIMiddlewareAdapter` 类，支持 ASGI 3.0 接口
- [ ] 实现请求处理中间件链（process_request）
- [ ] 实现响应处理中间件链（process_response）
- [ ] 实现异常处理中间件链（process_exception）
- [ ] 支持同步和异步中间件的混合使用
- [ ] 保持中间件执行顺序的兼容性

#### 1.2 核心中间件迁移
- [ ] 会话中间件（SessionMiddleware）异步化
- [ ] 认证中间件（AuthMiddleware）异步化
- [ ] CSRF 中间件（CSRFMiddleware）异步化
- [ ] 国际化中间件（I18nMiddleware）异步化
- [ ] 静态文件中间件（StaticFilesMiddleware）适配
- [ ] 错误处理中间件（ErrorMiddleware）异步化

#### 1.3 中间件兼容性处理
- [ ] 同步中间件到异步的自动包装
- [ ] 中间件配置的向后兼容
- [ ] 中间件执行上下文的正确传递

### 2. 模板系统异步化

#### 2.1 异步模板加载器
- [ ] 创建 `AsyncTemplateLoader` 类，支持异步模板加载
- [ ] 实现异步模板文件查找和读取
- [ ] 支持模板缓存机制
- [ ] 异步处理模板布局（layout）系统
- [ ] 支持默认模板回退机制

#### 2.2 异步模板渲染
- [ ] 实现 `AsyncTemplate` 类，支持异步渲染
- [ ] 异步模板变量处理和上下文传递
- [ ] 支持模板继承和包含的异步处理
- [ ] 模板标签和过滤器的异步兼容

#### 2.3 模板引擎适配
- [ ] Uliweb 原生模板引擎异步化
- [ ] 模板配置的向后兼容
- [ ] 模板查找路径的异步处理

### 3. 会话管理迁移

#### 3.1 异步会话存储后端
- [ ] 基于内存的会话存储异步化
- [ ] Redis 会话存储异步支持
- [ ] 数据库会话存储异步支持
- [ ] 文件系统会话存储异步支持
- [ ] Cookie 会话存储适配

#### 3.2 会话操作异步化
- [ ] 异步会话创建和初始化
- [ ] 异步会话读取和写入
- [ ] 异步会话销毁和清理
- [ ] 会话过期处理的异步支持

#### 3.3 会话安全性
- [ ] 异步会话加密和解密
- [ ] 会话ID生成的异步安全处理
- [ ] 会话劫持防护的异步实现

### 4. 事件分发系统异步化

#### 4.1 异步事件绑定
- [ ] 支持异步事件处理函数注册
- [ ] 保持现有 `@bind` 装饰器接口
- [ ] 事件优先级处理的异步支持

#### 4.2 异步事件触发
- [ ] 实现 `acall` 异步事件调用函数
- [ ] 支持同步和异步事件处理器的混合调用
- [ ] 事件执行上下文的异步传递

#### 4.3 核心事件异步化
- [ ] 应用启动事件（'init'）异步处理
- [ ] 请求开始事件（'begin_request'）异步处理
- [ ] 请求结束事件（'end_request'）异步处理
- [ ] 模板渲染事件异步处理

### 5. 命令系统迁移

#### 5.1 异步命令基类
- [x] 创建 `AsyncCommand` 基类，支持异步命令处理
- [x] 实现 `handle_async` 异步处理方法
- [x] 同步到异步的自动适配器

#### 5.2 核心命令迁移
- [x] `makeapp` 命令异步化
- [x] `runserver` 命令支持 ASGI 服务器
- [x] `shell` 命令的异步环境支持
- [x] `test` 命令的异步测试支持
- [x] `makeproject` 命令异步化
- [x] `makemodule` 命令异步化
- [x] `support` 命令异步化
- [x] `config` 命令异步化
- [x] `exportstatic` 命令异步化
- [x] `export` 命令异步化
- [x] `call` 命令异步化
- [x] `install` 命令异步化
- [x] `makecmd` 命令异步化
- [x] `find` 命令异步化
- [x] `validatetemplate` 命令异步化

#### 5.3 命令中间件系统
- [x] 异步命令预处理中间件
- [x] 异步命令后处理中间件
- [x] 命令执行上下文的异步管理

### 6. HTML 和 UAML 工具迁移

#### 6.1 异步 HTML 生成
- [ ] `AsyncHTMLGenerator` 类实现
- [ ] 异步 HTML 标签生成
- [ ] 异步表单生成工具
- [ ] 异步表格生成工具

#### 6.2 异步 UAML 处理
- [ ] UAML 到 HTML 的异步转换
- [ ] 异步 UAML 解析器
- [ ] UAML 模板的异步渲染

### 7. JSON 编码工具迁移

#### 7.1 异步 JSON 编码器
- [ ] `AsyncJSONEncoder` 类实现
- [ ] 异步 JSON 序列化函数
- [ ] 异步 JSON 反序列化函数
- [ ] 自定义对象序列化的异步支持

### 8. 文件操作异步化

#### 8.1 异步文件上传处理
- [ ] 异步文件上传解析
- [ ] 异步文件保存和处理
- [ ] 上传文件验证的异步支持

#### 8.2 异步文件下载
- [ ] 异步文件流式下载
- [ ] 大文件处理的异步优化
- [ ] 文件下载进度的异步监控

### 9. 静态文件服务迁移

#### 9.1 异步静态文件服务
- [ ] 基于 Starlette 的静态文件服务
- [ ] 异步文件查找和读取
- [ ] 静态文件缓存的异步管理

#### 9.2 静态文件优化
- [ ] 异步文件压缩和预处理
- [ ] 静态文件版本控制的异步支持
- [ ] CDN 集成的异步处理

### 10. 配置和依赖管理

#### 10.1 依赖包更新
- [ ] 确认所有依赖包的异步兼容性
- [ ] 添加必要的异步依赖包（starlette、anyio、aiofiles、uvicorn等）
- [ ] 更新项目配置和需求文件
- [ ] 验证依赖包版本兼容性

#### 10.2 Settings 配置系统适配
- [ ] 实现异步配置文件的动态加载和热重载
- [ ] 支持现有 settings.ini 配置格式的异步解析
- [ ] 实现配置项的异步验证和类型转换
- [ ] 支持配置变更的异步事件通知
- [ ] 保持与现有配置加载逻辑的兼容性

#### 10.3 中间件配置迁移
- [ ] 从 WSGI_MIDDLEWARES 配置迁移到 ASGI 中间件配置
- [ ] 实现中间件配置的自动转换和兼容性处理
- [ ] 支持异步中间件的配置参数验证
- [ ] 保持现有中间件配置的向后兼容性

#### 10.4 数据库和缓存配置
- [ ] 异步数据库连接池配置适配
- [ ] 异步缓存后端配置支持
- [ ] 数据库连接字符串的异步解析
- [ ] 缓存配置的异步验证和初始化

## 技术实现要点

### 关键代码变更

#### 1. 异步中间件适配器
```python
class ASGIMiddlewareAdapter:
    def __init__(self, app, middleware_classes):
        self.app = app
        self.middleware_classes = middleware_classes
        self._sort_middlewares()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # 处理请求中间件
        response = None
        for middleware_cls in self.middleware_classes:
            middleware = middleware_cls()
            if hasattr(middleware, 'process_request'):
                if asyncio.iscoroutinefunction(middleware.process_request):
                    response = await middleware.process_request(request)
                else:
                    response = middleware.process_request(request)
                if response is not None:
                    break

        # 处理视图
        if response is None:
            try:
                response = await self.app(scope, receive, send)
            except Exception as e:
                # 处理异常中间件
                for middleware_cls in reversed(self.middleware_classes):
                    middleware = middleware_cls()
                    if hasattr(middleware, 'process_exception'):
                        if asyncio.iscoroutinefunction(middleware.process_exception):
                            response = await middleware.process_exception(request, e)
                        else:
                            response = middleware.process_exception(request, e)
                        if response is not None:
                            break
                if response is None:
                    raise

        # 处理响应中间件
        for middleware_cls in reversed(self.middleware_classes):
            middleware = middleware_cls()
            if hasattr(middleware, 'process_response'):
                if asyncio.iscoroutinefunction(middleware.process_response):
                    response = await middleware.process_response(request, response)
                else:
                    response = middleware.process_response(request, response)

        await response(scope, receive, send)
```

#### 2. 异步模板加载器
```python
class AsyncTemplateLoader:
    def __init__(self, template_dirs, **kwargs):
        self.template_dirs = template_dirs
        self.template_cache = {}
        self.file_encoding = kwargs.get('encoding', 'utf-8')

    async def load_async(self, filename, layout=None, default_template=None):
        """异步加载模板"""
        cache_key = f"{filename}:{layout}:{default_template}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        # 异步查找模板文件
        template_path = await self._find_template_async(filename)
        if not template_path and default_template:
            template_path = await self._find_template_async(default_template)

        if not template_path:
            raise TemplateNotFound(f"Template {filename} not found")

        # 异步读取模板内容
        async with aiofiles.open(template_path, 'r', encoding=self.file_encoding) as f:
            content = await f.read()

        # 处理布局
        if layout:
            layout_content = await self._load_layout_async(layout)
            content = self._apply_layout(content, layout_content)

        template = AsyncTemplate(content, template_path)
        self.template_cache[cache_key] = template
        return template

    async def _find_template_async(self, filename):
        """异步查找模板文件"""
        for template_dir in self.template_dirs:
            template_path = os.path.join(template_dir, filename)
            if await self._file_exists_async(template_path):
                return template_path
        return None

    async def _file_exists_async(self, path):
        """异步检查文件是否存在"""
        try:
            await anyio.to_thread.run_sync(os.path.exists, path)
            return True
        except:
            return False
```

#### 3. 异步事件分发系统
```python
from uliweb.core.dispatch import bind, call, get, _receivers, import_attr
import asyncio
import anyio

# 支持异步处理函数
@bind('init')
async def async_init_handler(sender):
    await some_async_operation()

# 异步调用版本
async def acall(sender, topic, *args, **kwargs):
    """异步调用事件处理函数"""
    if topic not in _receivers:
        return

    results = []
    for nice, receiver in sorted(_receivers[topic], key=lambda x: x[0]):
        func = receiver['func'] or import_attr(receiver['func_name'])

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(sender, *args, **kwargs)
            else:
                result = await anyio.to_thread.run_sync(func, sender, *args, **kwargs)
            results.append(result)
        except Exception as e:
            # 处理异常，但不中断其他处理器
            logging.error(f"Error in event handler {func.__name__}: {e}")
            results.append(e)

    return results
```

#### 4. 异步命令处理
```python
class AsyncCommand(Command):
    async def handle_async(self, options, global_options, *args):
        """异步命令处理逻辑"""
        # 异步执行命令核心逻辑
        pass

    def handle(self, options, global_options, *args):
        """同步到异步的适配器"""
        import asyncio
        return asyncio.run(self.handle_async(options, global_options, *args))

# 异步命令中间件
class AsyncCommandMiddleware:
    async def process_command(self, command, options, global_options, args):
        """异步命令中间件"""
        # 预处理
        processed_options = await self.preprocess(options)

        # 执行命令
        result = await command.handle_async(processed_options, global_options, *args)

        # 后处理
        final_result = await self.postprocess(result)
        return final_result
```

#### 5. 异步配置加载器
```python
class AsyncSettingsLoader:
    def __init__(self, project_dir, apps_dir):
        self.project_dir = project_dir
        self.apps_dir = apps_dir
        self.settings_cache = {}

    async def load_settings_async(self, settings_file='settings.ini',
                                 local_settings_file='local_settings.ini',
                                 default_settings=None):
        """异步加载配置"""
        cache_key = f"{settings_file}:{local_settings_file}"

        if cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        # 异步收集配置文件路径
        settings_paths = await self._collect_settings_paths_async(
            settings_file, local_settings_file
        )

        # 异步读取和解析配置
        settings = pyini.Ini(lazy=True, basepath=self.apps_dir)
        for path in settings_paths:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
                settings.read_string(content, path)

        # 应用默认配置
        if default_settings:
            settings.update(default_settings)

        self.settings_cache[cache_key] = settings
        return settings

    async def _collect_settings_paths_async(self, settings_file, local_settings_file):
        """异步收集配置文件路径"""
        paths = []

        # 项目级配置
        project_settings = os.path.join(self.project_dir, settings_file)
        if await self._file_exists_async(project_settings):
            paths.append(project_settings)

        # 本地配置
        local_settings = os.path.join(self.project_dir, local_settings_file)
        if await self._file_exists_async(local_settings):
            paths.append(local_settings)

        # 应用配置
        apps = await self._get_apps_async()
        for app in apps:
            app_settings = os.path.join(self.apps_dir, app, settings_file)
            if await self._file_exists_async(app_settings):
                paths.append(app_settings)

        return paths

    async def _file_exists_async(self, path):
        """异步检查文件是否存在"""
        return await anyio.to_thread.run_sync(os.path.exists, path)
```

#### 6. 中间件配置迁移器
```python
class MiddlewareConfigMigrator:
    def __init__(self, settings):
        self.settings = settings

    async def migrate_wsgi_to_asgi(self):
        """将 WSGI 中间件配置迁移到 ASGI 中间件配置"""
        wsgi_middlewares = self.settings.get('WSGI_MIDDLEWARES', {})
        asgi_middlewares = {}

        for name, config in wsgi_middlewares.items():
            if not config:
                continue

            # 解析 WSGI 中间件配置
            middleware_cls, order, kwargs = self._parse_wsgi_middleware(config)

            # 转换为 ASGI 中间件配置
            asgi_config = await self._convert_to_asgi(middleware_cls, order, kwargs)
            asgi_middlewares[name] = asgi_config

        # 更新配置
        self.settings['MIDDLEWARES'] = asgi_middlewares
        return asgi_middlewares

    def _parse_wsgi_middleware(self, config):
        """解析 WSGI 中间件配置"""
        if isinstance(config, (list, tuple)):
            if len(config) == 1:
                return config[0], 500, {}
            elif len(config) == 2:
                if isinstance(config[1], int):
                    return config[0], config[1], {}
                else:
                    return config[0], 500, config[1]
            else:
                return config[0], config[1], config[2]
        else:
            return config, 500, {}

    async def _convert_to_asgi(self, middleware_cls, order, kwargs):
        """将 WSGI 中间件转换为 ASGI 中间件配置"""
        # 检查是否已经是 ASGI 中间件
        if await self._is_asgi_middleware(middleware_cls):
            return [middleware_cls, order, kwargs]
        else:
            # 创建 ASGI 包装器
            asgi_wrapper = await self._create_asgi_wrapper(middleware_cls)
            return [asgi_wrapper, order, kwargs]

    async def _is_asgi_middleware(self, middleware_cls):
        """检查中间件是否已经是 ASGI 中间件"""
        try:
            cls = import_attr(middleware_cls)
            # 检查是否支持 ASGI 接口
            return hasattr(cls, '__call__') and asyncio.iscoroutinefunction(cls.__call__)
        except:
            return False

    async def _create_asgi_wrapper(self, wsgi_middleware_cls):
        """创建 ASGI 包装器"""
        class ASGIWrapper:
            def __init__(self, app):
                self.app = app
                self.wsgi_middleware = import_attr(wsgi_middleware_cls)(app)

            async def __call__(self, scope, receive, send):
                if scope["type"] != "http":
                    await self.app(scope, receive, send)
                    return

                # 将 ASGI 请求转换为 WSGI 环境
                environ = await self._scope_to_environ(scope, receive)

                # 使用 WSGI 中间件处理
                def start_response(status, headers, exc_info=None):
                    # 处理响应头
                    pass

                # 在线程中运行 WSGI 中间件
                response = await anyio.to_thread.run_sync(
                    lambda: self.wsgi_middleware(environ, start_response)
                )

                # 发送响应
                await self._send_response(response, send)

        return f"{__name__}.ASGIWrapper"
```

## 验收标准

- [ ] 所有中间件支持异步处理
- [ ] 模板系统完全异步化，支持异步渲染
- [ ] 会话管理系统支持异步存储后端
- [ ] 事件分发系统支持异步处理器
- [x] 命令系统支持异步执行
- [ ] HTML/UAML 工具支持异步生成
- [ ] JSON 编码工具支持异步操作
- [ ] 文件操作完全异步化
- [ ] 静态文件服务基于 Starlette 实现
- [ ] 所有功能测试通过，性能不低于同步版本

## 注意事项

1. **线程安全**: 在异步环境中正确处理共享资源访问
2. **错误处理**: 为所有异步操作添加适当的错误处理和重试机制
3. **性能监控**: 监控异步化后的性能变化，确保没有性能回归
4. **内存管理**: 注意异步操作中的内存使用，避免内存泄漏
5. **超时处理**: 为异步操作设置合理的超时时间
6. **上下文保持**: 确保异步操作中请求上下文的正确传递
7. **兼容性**: 保持与现有同步代码的兼容性，提供同步到异步的自动转换

## 测试策略

### 单元测试
- [ ] 为每个异步组件编写单元测试
- [ ] 测试异步异常处理
- [ ] 测试并发场景下的行为

### 集成测试
- [ ] 测试中间件链的异步执行
- [ ] 测试模板异步渲染的正确性
- [ ] 测试会话异步操作的完整性

### 性能测试
- [ ] 对比异步和同步版本的性能
- [ ] 测试高并发场景下的稳定性
- [ ] 监控内存使用和资源消耗

## 下一步工作

完成阶段二后，可以继续进行：
- 阶段三：性能优化（数据库异步驱动、缓存优化、WebSocket支持）
- 阶段四：生态兼容（插件系统适配、第三方库集成、文档完善）

通过阶段二的完整实施，Uliweb 将具备完整的异步处理能力，为后续的性能优化和生态扩展奠定坚实基础。
