#! /usr/bin/env python
#coding=utf-8

import urllib
from uliweb import Middleware, settings
from pendulum import timezone
from pendulum.tz.zoneinfo.exceptions import InvalidTimezone

class TimezoneMiddleware(Middleware):
    def __init__(self, application, settings):
        self._time_zone = settings.GLOBAL.TIME_ZONE
        self._local_time_zone = settings.GLOBAL.LOCAL_TIME_ZONE
        if self._time_zone and not self._local_time_zone:
            self._local_time_zone = self._time_zone
        self._cookie_key = settings.TIMEZONE.cookie_key

    async def dispatch(self, request, call_next):
        # 请求预处理
        if self._time_zone:
            tz = None
            tzinfo = None
            if request.user:
                tz = request.user.timezone
            if not tz and request.cookies:
                v = request.cookies.get(self._cookie_key)
                if v:
                    tz = urllib.parse.unquote(v)
            if not tz:
                tz = self._local_time_zone
            if tz:
                try:
                    tzinfo = timezone(tz)
                except InvalidTimezone:
                    tz = settings.GLOBAL.LOCAL_TIME_ZONE
                    tzinfo = timezone(tz)
            request.tz = tz
            request.tzinfo = tzinfo

        # 调用下一个中间件或视图函数
        response = await call_next(request)

        # Timezone中间件没有响应后处理逻辑
        return response
