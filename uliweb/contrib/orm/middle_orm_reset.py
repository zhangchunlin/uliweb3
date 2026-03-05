from uliweb import Middleware
from uliweb.orm import set_dispatch_send, set_echo


class ORMResetMiddle(Middleware):
    """
    异步 ORM 重置中间件 - 使用 ASGI dispatch 接口

    将原来的 process_request 方法整合到异步 dispatch 方法中。
    """
    ORDER = 70

    async def dispatch(self, request, call_next):
        """
        异步调度方法 - 处理请求预处理
        """
        # 请求预处理 - 重置 ORM 状态
        set_echo(False)
        set_dispatch_send(True)

        # 调用下一个中间件或视图函数
        response = await call_next(request)
        return response
