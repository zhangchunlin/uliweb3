# 测试服务器

Uliweb3 提供了 `TestServer` 类，用于在单元测试中启动真实的 ASGI 服务器。这对于测试静态文件、文件上传下载、WebSocket 等需要真实网络环境的场景非常有用。

## 依赖

```bash
pip install uvicorn httpx
```

- **uvicorn**: ASGI 服务器
- **httpx**: 推荐用于异步测试的 HTTP 客户端

## 基本用法

### 使用 unittest 风格

```python
import unittest
from uliweb.utils.test_server import TestServer
import httpx

class TestStaticFiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = TestServer(
            project_dir='/path/to/project',
            apps_dir='apps'
        )
        cls.server.start()
        cls.base_url = cls.server.base_url

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_static_file(self):
        # 使用真实的 HTTP 请求测试
        response = httpx.get(f'{self.base_url}/static/test.txt')
        self.assertEqual(response.status_code, 200)
```

### 使用上下文管理器

```python
from uliweb.utils.test_server import TestServer

def test_static_file():
    with TestServer(project_dir='/path/to/project') as server:
        response = httpx.get(f'{server.base_url}/static/test.txt')
        assert response.status_code == 200
```

### 使用便捷函数

```python
from uliweb.utils.test_server import test_server

def test_static_file():
    with test_server(project_dir='/path/to/project') as server:
        response = server.get('/static/test.txt')
        assert response.status_code == 200
```

## TestServer 类详解

### 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `app` | ASGI App | None | ASGI 应用实例。如果为 None，则根据 project_dir 创建 |
| `project_dir` | str | None | 项目目录路径 |
| `apps_dir` | str | 'apps' | apps 目录名称 |
| `include_apps` | list | None | 额外包含的应用列表 |
| `host` | str | '127.0.0.1' | 监听地址 |
| `port` | int | 0 | 监听端口。0 表示自动分配一个可用端口 |
| `settings_file` | str | 'settings.ini' | settings 文件名 |
| `local_settings_file` | str | 'local_settings.ini' | 本地 settings 文件名 |
| `log_level` | str | 'warning' | 日志级别，默认为 'warning' 减少测试输出 |

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `base_url` | str | 服务器的基础 URL，如 'http://127.0.0.1:8000' |
| `url` | str | base_url 的别名 |
| `app` | ASGI App | ASGI 应用实例 |

### 方法

#### start()

启动服务器。会自动分配可用端口（如果 port 设为 0）。

#### stop()

停止服务器。

#### get_client(**kwargs)

获取同步 HTTP 客户端（httpx.Client）。

```python
with server.get_client() as client:
    response = client.get('/static/test.txt')
```

#### get_async_client(**kwargs)

获取异步 HTTP 客户端（httpx.AsyncClient）。

```python
async with server.get_async_client() as client:
    response = await client.get('/static/test.txt')
```

#### request(method, path, **kwargs)

发送同步 HTTP 请求的便捷方法。

```python
response = server.request('GET', '/api/users')
response = server.request('POST', '/api/users', json={'name': 'test'})
```

#### get(path, **kwargs)

发送 GET 请求的便捷方法。

#### post(path, **kwargs)

发送 POST 请求的便捷方法。

#### put(path, **kwargs)

发送 PUT 请求的便捷方法。

#### delete(path, **kwargs)

发送 DELETE 请求的便捷方法。

## 使用场景

### 测试静态文件

```python
def test_static_files():
    with test_server(project_dir='/path/to/project') as server:
        # 测试静态文件
        response = server.get('/static/css/style.css')
        assert response.status_code == 200

        # 测试文件下载
        response = server.get('/downloads/file.pdf')
        assert response.status_code == 200
        assert 'Content-Disposition' in response.headers
```

### 测试文件上传

```python
def test_upload():
    with test_server(project_dir='/path/to/project') as server:
        files = {'file': ('test.txt', b'content', 'text/plain')}
        response = server.post('/upload', files=files)
        assert response.status_code == 200
```

### 测试 WebSocket

```python
import asyncio
import httpx

async def test_websocket():
    async with TestServer(project_dir='/path/to/project') as server:
        async with server.get_async_client() as client:
            async with client.websocket_connect('/ws') as ws:
                ws.send_text('hello')
                response = ws.receive_text()
                assert response == 'hello'
```

### 测试 API

```python
def test_api():
    with test_server(project_dir='/path/to/project') as server:
        # GET 请求
        response = server.get('/api/users')
        assert response.status_code == 200
        data = response.json()

        # POST 请求
        response = server.post('/api/users', json={'name': 'test'})
        assert response.status_code == 201
```

## 完整示例

```python
import unittest
from uliweb.utils.test_server import test_server

class TestMyApp(unittest.TestCase):

    def test_index(self):
        with test_server(project_dir='/path/to/project') as server:
            response = server.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Hello', response.text)

    def test_api_users(self):
        with test_server(project_dir='/path/to/project') as server:
            # 获取用户列表
            response = server.get('/api/users')
            self.assertEqual(response.status_code, 200)

            # 创建用户
            response = server.post('/api/users', json={
                'username': 'testuser',
                'email': 'test@example.com'
            })
            self.assertEqual(response.status_code, 201)

    def test_static_assets(self):
        with test_server(project_dir='/path/to/project') as server:
            response = server.get('/static/css/main.css')
            self.assertEqual(response.status_code, 200)
            self.assertIn('text/css', response.headers.get('content-type', ''))

if __name__ == '__main__':
    unittest.main()
```

## 运行测试

```bash
# 运行特定测试文件
python -m pytest tests/test_myapp.py -v

# 运行特定测试用例
python -m pytest tests/test_myapp.py::TestMyApp::test_index -v

# 运行所有测试
python -m pytest tests/ -v
```

## 在测试中获取 Settings

在测试代码中获取 settings 有多种方式：

### 方式 1：通过 make_application 获取

使用 `uliweb.manage` 中的 `make_application` 或 `make_simple_application` 函数创建应用后，即可导入 settings：

```python
import os
import sys
from uliweb import settings
from uliweb.manage import make_application

# 创建应用
path = os.path.dirname(os.path.abspath(__file__))
app = make_application(project_dir=path, include_apps=['myapp'])

# 现在可以正常使用 settings
print(settings.GLOBAL.DEBUG)
print(settings.get_var('GLOBAL/DEBUG'))
```

### 方式 2：通过 TestServer 获取

使用 TestServer 时，可以通过 `server.app` 属性获取应用实例，然后访问 settings：

```python
from uliweb.utils.test_server import TestServer

with TestServer(project_dir='/path/to/project') as server:
    # 通过 app 获取 settings
    app_settings = server.app.settings
    print(app_settings.GLOBAL.DEBUG)

    # 或者直接导入 settings（需要在应用创建之后）
    from uliweb import settings
    print(settings.GLOBAL.DEBUG)
```

### 方式 3：使用 make_simple_application（推荐用于测试）

`make_simple_application` 创建一个轻量级的应用，适合测试场景：

```python
from uliweb import settings
from uliweb.manage import make_simple_application

app = make_simple_application(
    project_dir='/path/to/project',
    include_apps=['uliweb.contrib.staticfiles', 'myapp']
)

# 访问 settings
debug = settings.GLOBAL.DEBUG
```

### 方式 4：直接创建 AsyncDispatcher

如果需要更精细的控制，可以直接创建 AsyncDispatcher：

```python
from uliweb.core.SimpleFrame import AsyncDispatcher
from uliweb import settings

# 创建 dispatcher
dispatcher = AsyncDispatcher(
    apps_dir='apps',
    project_dir='/path/to/project',
    include_apps=['myapp'],
    start=False
)

# 初始化后即可使用 settings
print(settings.GLOBAL.DEBUG)
```

### 完整示例：结合 TestServer 和 Settings

```python
import unittest
from uliweb.utils.test_server import TestServer
from uliweb import settings

class TestMyApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = TestServer(
            project_dir='/path/to/project',
            include_apps=['myapp']
        )
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_settings_access(self):
        """测试在测试服务器中访问 settings"""
        # 方法1：通过 server.app 访问
        app_settings = self.server.app.settings

        # 方法2：直接导入 settings
        from uliweb import settings

        # 验证 settings 正常工作
        debug = settings.GLOBAL.DEBUG
        self.assertIsNotNone(debug)

    def test_api_with_settings(self):
        """测试 API 并使用 settings 配置"""
        # 根据 settings 配置决定测试行为
        if settings.GLOBAL.DEBUG:
            # Debug 模式下使用测试数据
            pass

        response = self.server.get('/api/users')
        self.assertEqual(response.status_code, 200)