from uliweb import Middleware, functions

class AuthMiddle(Middleware):
    ORDER = 100

    async def dispatch(self, request, call_next):
        # 请求预处理
        request.user = functions.get_auth_user()

        # 调用下一个中间件或视图函数
        response = await call_next(request)

        # 响应后处理
        functions.update_user_session_expiry_time()

        return response
