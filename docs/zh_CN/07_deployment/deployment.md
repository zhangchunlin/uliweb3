# 部署指南

Uliweb3 是一个纯 ASGI 框架，需要使用 ASGI 服务器进行部署。不再支持 WSGI 部署方式。

## ASGI 服务器

Uliweb3 支持多种 ASGI 服务器：

### Uvicorn（推荐）

Uvicorn 是一个高性能的 ASGI 服务器实现，基于 uvloop。

安装：
```
pip install uvicorn
```

运行应用：
```
uvicorn uliweb.manage:application --host 0.0.0.0 --port 8000
```

或者使用 Python 模块方式：
```
python -m uvicorn uliweb.manage:application --host 0.0.0.0 --port 8000
```

### Hypercorn

Hypercorn 是一个支持 HTTP/2 的 ASGI 服务器。

安装：
```
pip install hypercorn
```

运行应用：
```
hypercorn uliweb.manage:application --bind 0.0.0.0:8000
```

### Daphne

Django 官方推荐的 ASGI 服务器，也支持 Uliweb。

安装：
```
pip install daphne
```

运行应用：
```
daphne uliweb.manage:application
```

## 使用 Uliweb3 项目部署

### 创建应用入口

在项目根目录创建 `app.py`：

```python
import os
from uliweb import ASGIApplication

# 获取项目目录
project_dir = os.path.dirname(os.path.abspath(__file__))

# 创建 ASGI 应用
application = ASGIApplication(
    apps_dir=os.path.join(project_dir, 'apps'),
    project_dir=project_dir
)
```

### 使用 Gunicorn 部署

Gunicorn 可以配合 Uvicorn worker 使用：

```
gunicorn app:application -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 使用 systemd 管理服务

创建 `/etc/systemd/system/uliweb.service`：

```ini
[Unit]
Description=Uliweb Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app:application --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

启动服务：
```
sudo systemctl start uliweb
sudo systemctl enable uliweb
```

## Nginx + ASGI 服务器

推荐使用 Nginx 作为反向代理：

```
server {
    listen 80;
    server_name example.com;

    # 静态文件
    location /static/ {
        alias /path/to/your/project/static/;
    }

    # 媒体文件
    location /media/ {
        alias /path/to/your/project/media/;
    }

    # ASGI 代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 86400;
    }
}
```

## 静态文件配置

在 `settings.ini` 中配置静态文件：

```ini
[STATICFILES]
DIRS = ['static']
```

或者使用命令导出静态文件：

```
uliweb collectstatic /your/static/path
```

## 生产环境最佳实践

1. **使用虚拟环境**：创建隔离的 Python 环境
2. **启用调试=False**：在生产环境关闭调试模式
3. **配置日志**：设置适当的日志级别
4. **使用进程管理器**：如 systemd、supervisor 或容器编排
5. **启用 HTTPS**：使用 TLS/SSL 证书
6. **配置健康检查**：对于容器化部署

## 部署到云平台

### Render

创建 `render.yaml`：

```yaml
services:
  - type: web
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:application -w 4 -k uvicorn.workers.UvicornWorker
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
```

### Railway

创建 `railway.json`：

```json
{
  "$schema": "https://railway.app/schema.json",
  "build": {
    "builder": "NIXPACKS_PYTHON"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:application", "--host", "0.0.0.0", "--port", "8000"]
```

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./static:/app/static
    environment:
      - DEBUG=False
```

## 迁移注意事项

如果你是从 Uliweb 旧版本迁移：

1. **不再使用 WSGI**：所有 WSGI 相关的配置和部署方式都已废弃
2. **需要 ASGI 服务器**：使用 Uvicorn、Hypercorn 或 Daphne
3. **异步支持**：充分利用 async/await 特性
4. **Request/Response 变化**：POST、FILES、json、values 需要使用异步方法访问
