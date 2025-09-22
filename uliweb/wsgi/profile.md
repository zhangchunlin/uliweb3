# ProfileApplication - 性能分析中间件

`profile.py` 提供了一个 WSGI 性能分析中间件，用于对 Uliweb 应用进行性能分析和优化。

## 概述

`ProfileApplication` 类是一个 WSGI 中间件，它使用 Python 的 `hotshot` 模块对 WSGI 应用进行性能分析，生成详细的性能报告。

## 导入模块

```python
import os, sys
import hotshot
import hotshot.stats
from six.moves import cStringIO
```

## 常量定义

```python
PROFILE_DATA_DIR = "./profile"
```

- `PROFILE_DATA_DIR`: 性能分析数据存储目录，默认为当前目录下的 `profile` 文件夹

## ProfileApplication 类

### 初始化方法

```python
def __init__(self, app):
    self.path = path = PROFILE_DATA_DIR
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, 493)
    self.app = app
```

**参数:**
- `app`: 要包装的 WSGI 应用实例

**功能:**
- 设置性能分析数据存储路径
- 如果目录不存在，创建目录并设置权限 (493 对应八进制 755，即 rwxr-xr-x)
- 保存原始应用实例

### 调用方法

```python
def __call__(self, environ, start_response):
```

**参数:**
- `environ`: WSGI 环境变量字典
- `start_response`: WSGI 开始响应回调函数

**处理流程:**

1. **生成分析文件名:**
   ```python
   profname = "%s.prof" % (environ['PATH_INFO'].strip("/").replace('/', '.'))
   profname = os.path.join(self.path, profname)
   ```
   - 基于请求路径生成唯一的分析文件名
   - 将路径中的 `/` 替换为 `.`，避免文件路径问题

2. **创建性能分析器:**
   ```python
   prof = hotshot.Profile(profname)
   ```

3. **执行性能分析:**
   ```python
   ret = prof.runcall(self.app, environ, start_response)
   prof.close()
   ```
   - 使用 `runcall` 方法执行原始应用并收集性能数据
   - 完成后关闭分析器

4. **生成性能报告:**
   ```python
   out = StringIO()
   old_stdout = sys.stdout
   sys.stdout = out

   stats = hotshot.stats.load(profname)
   #stats.strip_dirs()
   stats.sort_stats('time', 'calls')
   stats.print_stats()

   sys.stdout = old_stdout
   stats_str = out.getvalue()
   ```
   - 重定向标准输出到 StringIO 对象
   - 加载性能统计数据
   - 按执行时间和调用次数排序
   - 打印统计信息到缓冲区

5. **生成 HTML 报告:**
   ```python
   from uliweb.utils.textconvert import text2html
   text = text2html(stats_str)
   outputfile = profname + '.html'
   file(outputfile, 'wb').write(text)
   ```
   - 使用 `text2html` 将文本统计信息转换为 HTML 格式
   - 保存为 `.html` 文件

6. **返回结果:**
   ```python
   return ret
   ```
   - 返回原始应用的响应结果

## 使用示例

```python
from uliweb.wsgi.profile import ProfileApplication

# 包装你的 WSGI 应用
app = ProfileApplication(original_app)
```

## 输出文件

性能分析会生成两种文件：

1. **`.prof` 文件**: 原始性能分析数据文件
2. **`.html` 文件**: 格式化的 HTML 性能报告

文件命名基于请求路径，例如：
- 请求 `/user/profile` → `user.profile.prof` 和 `user.profile.prof.html`

## 注意事项

1. **性能开销**: 性能分析会带来一定的性能开销，不建议在生产环境中使用
2. **目录权限**: 确保应用有权限在 `PROFILE_DATA_DIR` 目录下创建文件和文件夹
3. **依赖**: 需要 `hotshot` 模块支持（Python 标准库的一部分）

## 相关模块

- `hotshot`: Python 高性能分析器模块
- `hotshot.stats`: 性能统计数据分析模块
- `uliweb.utils.textconvert`: Uliweb 文本转换工具

这个性能分析工具可以帮助开发者识别应用中的性能瓶颈，优化代码执行效率。
