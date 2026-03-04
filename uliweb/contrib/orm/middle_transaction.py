from uliweb import Middleware
from uliweb.orm import Begin, CommitAll, RollbackAll


class TransactionMiddle(Middleware):
    ORDER = 80

    def __init__(self, application, settings):
        self.settings = settings

    async def dispatch(self, request, call_next):
        """
        异步事务中间件 - 使用 ASGI dispatch 接口

        在请求开始时开启事务，在请求结束时提交事务。
        如果发生异常，则回滚事务。
        """
        # 请求预处理 - 开启事务
        Begin()

        try:
            # 调用下一个中间件或视图函数
            response = await call_next(request)
        except Exception:
            # 发生异常 - 回滚事务
            RollbackAll()
            raise

        # 响应后处理 - 提交事务
        try:
            from uliweb import response as res
            try:
                return response
            finally:
                CommitAll()

                # add post_commit process
                if hasattr(response, 'post_commit') and response.post_commit:
                    response.post_commit()

                if response is not res and hasattr(res, 'post_commit') and res.post_commit:
                    res.post_commit()
        except Exception:
            # 提交失败 - 回滚事务
            RollbackAll()
            raise

        return response
