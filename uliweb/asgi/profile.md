# ASGI Profile 中间件

`profile.py` 提供了一个 ASGI 性能分析中间件，用于对 Uliweb 应用进行性能分析和优化。

**重要更新**：本模块已从 WSGI 迁移到 ASGI。详细信息请参考 [ASGI 迁移设计文档](../../design/spec.md)。

## 概述

`ASGIProfileMiddleware` 类是一个 ASGI 中间件，使用 Python 的 `cProfile` 模块对 ASGI 应用进行性能分析，生成详细的性能报告。

## 导入模块

```python
from uliweb.asgi.profile import ASGIProfileMiddleware
```

或者使用兼容性导入：

```python
from uliweb.asgi.profile import ProfileApplication
```

## 常量定义

```python
PROFILE_DATA_DIR = "./profile"
```

- `PROFILE_DATA_DIR`: 性能分析数据存储目录，默认为当前目录下的 `profile` 文件夹

## ASGIProfileMiddleware 类

### 初始化方法

```python
def __init__(self, app, profile_dir=None):
```

**参数:**
- `app`: 要包装的 ASGI 应用实例
- `profile_dir`: 性能分析数据存储目录（可选）

**功能:**
- 设置性能分析数据存储路径
- 如果目录不存在，创建目录并设置权限 (0o755)
- 保存原始应用实例

### 调用方法

```python
async def __call__(self, scope, receive, send):
```

**参数:**
- `scope`: ASGI scope 字典
- `receive`: 接收消息的异步函数
- `send`: 发送消息的异步函数

**处理流程:**

1. **检查请求类型:**
   ```python
   if scope["type"] != "http":
       await self.app(scope, receive, send)
       return
   ```
   - 只处理 HTTP 请求，其他类型直接传递

2. **生成分析文件名:**
   ```python
   path_info = scope.get('path', '/')
   profname = "%s.prof" % path_info.strip("/").replace('/', '.')
   profname = os.path.join(self.path, profname)
   ```
   - 基于请求路径生成唯一的分析文件名
   - 将路径中的 `/` 替换为 `.`，避免文件路径问题

3. **创建性能分析器:**
   ```python
   profiler = cProfile.Profile()
   ```

4. **包装 send 函数:**
   ```python
   async def profiled_send(message):
       nonlocal response_started, response_body
       if message["type"] == "http.response.start":
           response_started = True
       elif message["type"] == "http.response.body":
           body = message.get("body", b"")
           if body:
               response_body.append(body)
       await original_send(message)
   ```
   - 捕获响应消息以进行分析

5. **执行性能分析:**
   ```python
   try:
       profiler.enable()
       await self.app(scope, receive, profiled_send)
       profiler.disable()
   except Exception:
       profiler.disable()
       raise
   ```
   - 启用分析器并执行原始应用
   - 捕获异常时确保正确禁用分析器

6. **生成性能报告:**
   ```python
   stats = pstats.Stats(profiler)
   stats.strip_dirs()
   stats.sort_stats('cumulative')

   s = io.StringIO()
   stats.print_stats()
   stats_str = s.getvalue()

   from uliweb.utils.textconvert import text2html
   html_content = text2html(stats_str)
   ```
   - 使用 pstats 进行性能统计分析
   - 将文本转换为 HTML 格式

7. **保存分析结果:**
   ```python
   stats.dump_stats(profname)
   outputfile = profname + '.html'
   with open(outputfile, 'wb') as f:
       if isinstance(html_content, str):
           html_content = html_content.encode('utf-8')
       f.write(html_content)
   ```
   - 保存 .prof 原始数据文件
   - 保存 .html 格式的 HTML 报告

## 使用示例

### 使用 ASGIProfileMiddleware

```python
from uliweb.asgi.profile import ASGIProfileMiddleware
from uliweb import application

# 包装你的 ASGI 应用
app = ASGIProfileMiddleware(application)
```

### 使用 ProfileApplication（兼容）

```python
from uliweb.asgi.profile import ProfileApplication
from uliweb import application

# 兼容原来的用法，实际返回 ASGIProfileMiddleware 实例
app = ProfileApplication(application)
```

### 在 Uvicorn 中使用

```bash
uvicorn main:app --factory
```

其中 `main.py`:

```python
from uliweb.asgi.profile import ASGIProfileMiddleware
from uliweb import application

app = ASGIProfileMiddleware(application)
```

## 输出文件

性能分析会生成两种文件：

1. **`.prof` 文件**: 原始性能分析数据文件（使用 pstats.dump_stats）
2. **`.html` 文件**: 格式化的 HTML 性能报告

文件命名基于请求路径，例如：
- 请求 `/user/profile` → `user.profile.prof` 和 `user.profile.prof.html`

## 注意事项

1. **性能开销**: 性能分析会带来一定的性能开销，不建议在生产环境中使用
2. **目录权限**: 确保应用有权限在 `PROFILE_DATA_DIR` 目录下创建文件和文件夹
3. **ASGI 兼容**: 本模块仅支持 ASGI，如需 WSGI 版本请参考历史版本
4. **异步支持**: 完全支持异步应用，使用 `await` 进行异步调用

## 迁移说明

本模块已从 WSGI 迁移到 ASGI：

| 特性 | WSGI 版本 | ASGI 版本 |
|------|----------|----------|
| 接口 | `__call__(environ, start_response)` | `async __call__(scope, receive, send)` |
| 分析器 | hotshot | cProfile |
| 请求处理 | 同步 | 异步 |
| 兼容性 | ProfileApplication | ProfileApplication / ASGIProfileMiddleware |

**迁移自**: 原有的 WSGI ProfileApplication 类
**迁移到**: ASGIProfileMiddleware 类
**参考文档**: [ASGI 迁移设计文档](../../design/spec.md)

## 相关模块

- `cProfile`: Python 内置性能分析器
- `pstats`: 性能统计数据分析模块
- `uliweb.utils.textconvert`: Uliweb 文本转换工具
- [ASGI 迁移设计文档](../../design/spec.md): ASGI 迁移指南

这个性能分析工具可以帮助开发者识别应用中的性能瓶颈，优化代码执行效率。
