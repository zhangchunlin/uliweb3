from uliweb import Middleware
from uliweb.orm import begin_sql_monitor, close_sql_monitor


class SQLMonitorMiddle(Middleware):
    """
    异步 SQL 监控中间件 - 使用 ASGI dispatch 接口

    将原来的 process_request, process_response, process_exception
    整合到异步 dispatch 方法中。
    """
    ORDER = 90

    def __init__(self, application, settings):
        super(SQLMonitorMiddle, self).__init__(application, settings)
        self.monitor = None

    async def dispatch(self, request, call_next):
        """
        异步调度方法 - 处理请求前后和异常的监控
        """
        # 请求预处理 - 开启 SQL 监控
        from uliweb import settings as uliweb_settings

        if 'sqlmonitor' in request.GET or uliweb_settings.ORM.SQL_MONITOR:
            self.monitor = begin_sql_monitor(
                uliweb_settings.ORM.get('SQL_MONITOR_LENGTH', 70),
                record_details=False
            )

        try:
            # 调用下一个中间件或视图函数
            response = await call_next(request)
        except Exception:
            # 异常处理 - 打印监控信息
            if 'sqlmonitor' in request.GET or uliweb_settings.ORM.SQL_MONITOR:
                if self.monitor:
                    self.monitor.print_(request.path)
                    close_sql_monitor(self.monitor)
                    self.monitor = None
            raise

        # 响应后处理 - 打印监控信息
        if 'sqlmonitor' in request.GET or uliweb_settings.ORM.SQL_MONITOR:
            if self.monitor:
                self.monitor.print_(request.path)
                close_sql_monitor(self.monitor)
                self.monitor = None

        return response
