# 调试模式与日志级别

## 调试模式说明

默认情况下，`uliweb runserver` 会以调试模式启动，这会导致 uvicorn 使用 `--log-level debug` 参数，从而输出大量日志（包括 WebSocket 相关的调试信息）。

## 关闭 debug 日志

### 方法1：启动时关闭 debug 模式

```bash
uliweb runserver --no-debug
```

### 方法2：在 settings.ini 中配置日志级别

在项目的 `settings.ini` 中添加：

```ini
[LOG]
level = 'info'
```

## 原因分析

在 `uliweb/manage.py` 的 `RunserverCommand.run_asgi` 方法中：

```python
if server == 'uvicorn':
    cmd = ['uvicorn']
    if options.reload:
        cmd.append('--reload')
    # uvicorn 不支持 --debug 选项，使用 --log-level debug 替代
    if options.debug:
        cmd.extend(['--log-level', 'debug'])
```

当使用 `uliweb runserver` 启动时：
- 默认 `options.debug = True`（参见 `make_option('--no-debug', dest='debug', action='store_false', default=True, ...)`）
- 这会导致 uvicorn 启动时添加 `--log-level debug` 参数
- uvicorn 在 debug 级别会输出大量日志，包括 WebSocket 相关的调试信息

{% alert class=info %}
**注意**：uliweb 自身的 WebSocket debug 日志（位于 `SimpleFrame.py` 中使用 `logger.debug()` 的地方）默认不会输出，因为默认日志级别是 `info`。但 uvicorn 的 `--log-level debug` 会开启 uvicorn 自己的 debug 日志，这些是 starlette/uvicorn 内部的调试信息。
{% endalert %}

## 日志配置示例

如果你想修改日志颜色，可以在 settings.ini 设置：

```ini
[LOG.COLORS]
DEBUG = 'white'
INFO = 'green'
WARNING = 'yellow'
ERROR = 'red'
CRITICAL = 'red'
```

可用颜色为：BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE。颜色值不区分大小写。