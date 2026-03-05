from uliweb import Middleware, error
from uliweb.orm import NotFound


class ORMNotfoundMiddle(Middleware):
    """
    异步 ORM NotFound 处理中间件 - 使用 ASGI dispatch 接口

    将原来的 process_exception 方法整合到异步 dispatch 方法中。
    """
    ORDER = 110

    def __init__(self, application, settings):
        pass

    async def dispatch(self, request, call_next):
        """
        异步调度方法 - 处理请求和异常
        """
        try:
            # 调用下一个中间件或视图函数
            response = await call_next(request)
            return response
        except Exception as e:
            # 异常处理 - 检查是否为 NotFound 异常
            if isinstance(e, NotFound):
                error("%s(%s) can't be found" % (e.model.__name__, e.id))
            raise
