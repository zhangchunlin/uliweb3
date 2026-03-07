"""
ASGI Handler for Uliweb3

This is the ASGI entry point for Uliweb3 applications.
Use with ASGI servers like: uvicorn, hypercorn, daphne.

Example:
    uvicorn asgi_handler:application --reload
    hypercorn asgi_handler:application --bind 0.0.0.0:8000
    daphne -b 0.0.0.0 -p 8000 asgi_handler:application
"""
import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from uliweb.core.starlette import ASGIApplication

# 使用纯 ASGI 处理程序
application = ASGIApplication(project_dir=path)
