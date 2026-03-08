"""
Uliweb ASGI Profile 中间件
用于对 ASGI 应用进行性能分析和优化

这个模块提供了从 WSGI 迁移到 ASGI 的性能分析中间件。
迁移说明：uliweb/core/asgi.md
"""

import os
import cProfile
import pstats
import io

PROFILE_DATA_DIR = "./profile"


class ASGIProfileMiddleware:
    """
    ASGI 性能分析中间件，对 ASGI 应用进行性能分析并生成报告。

    这是原来 WSGI ProfileApplication 的 ASGI 版本。
    """

    def __init__(self, app, profile_dir=None):
        self.app = app
        self.path = profile_dir or PROFILE_DATA_DIR
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            os.chmod(self.path, 0o755)

    async def __call__(self, scope, receive, send):
        """
        ASGI 接口实现

        :param scope: ASGI scope 字典
        :param receive: 接收消息的异步函数
        :param send: 发送消息的异步函数
        """
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 生成分析文件名
        path_info = scope.get('path', '/')
        profname = "%s.prof" % path_info.strip("/").replace('/', '.')
        profname = os.path.join(self.path, profname)

        # 创建性能分析器
        profiler = cProfile.Profile()

        # 包装 send 函数来捕获响应
        response_started = False
        response_body = []

        original_send = send

        async def profiled_send(message):
            nonlocal response_started, response_body
            if message["type"] == "http.response.start":
                response_started = True
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_body.append(body)
            await original_send(message)

        # 运行性能分析
        try:
            # 执行应用并收集性能数据
            profiler.enable()
            await self.app(scope, receive, profiled_send)
            profiler.disable()
        except Exception:
            profiler.disable()
            raise

        # 生成性能统计
        stats = pstats.Stats(profiler)
        stats.strip_dirs()
        stats.sort_stats('cumulative')

        # 输出到字符串
        s = io.StringIO()
        stats.print_stats()
        stats_str = s.getvalue()

        # 生成 HTML 报告
        from uliweb.utils.textconvert import text2html
        html_content = text2html(stats_str)

        # 保存分析数据
        stats.dump_stats(profname)

        # 保存 HTML 报告
        outputfile = profname + '.html'
        with open(outputfile, 'wb') as f:
            if isinstance(html_content, str):
                html_content = html_content.encode('utf-8')
            f.write(html_content)

        # 注意：这里只是分析，不修改响应内容
        # 实际使用中，可以通过修改响应来显示性能数据


class ProfileApplication:
    """
    保留兼容性：WSGI ProfileApplication 的别名

    为了向后兼容，保留原来的类名。
    在 ASGI 环境中使用时，会自动使用 ASGIProfileMiddleware。
    """

    def __new__(self, app, profile_dir=None):
        """
        兼容原来的 ProfileApplication 用法。
        在 ASGI 环境中实际返回 ASGIProfileMiddleware 实例。
        """
        return ASGIProfileMiddleware(app, profile_dir)
