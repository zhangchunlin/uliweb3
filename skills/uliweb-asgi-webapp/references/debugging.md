# 调试与复现（Debugging & Reproduction）

Uliweb3 是**懒加载 + 纯 ASGI**，很多「看起来是业务 bug」的问题，真正根因在
**请求/响应边界**（body 解析、路由、鉴权中间件）。调试的正确姿势是：用真实请求 +
隔离环境做最小复现，拿完整堆栈说话。

## 1. ASGI 应用是懒加载的

`import asgi_handler`（或 `ASGIApplication(...)`）**不会真正初始化**应用：
settings、ORM engine、模型注册等都在**第一次真实 ASGI 请求**时才就绪。

因此，直接在一个进程里 `import asgi_handler` 后立刻 `get_model('user')` 会报
`uliweb.orm.ModelNotFound: Can't found the model ... in engine None`。

### 正确复现姿势：httpx.ASGITransport

不需要启动真实 uvicorn 进程，用 httpx 的 ASGI transport 直接在进程内触发完整启动：

```python
import asyncio
import httpx
import asgi_handler as ah

async def main():
    transport = httpx.ASGITransport(app=ah.application)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        # 第一个请求触发完整初始化（settings/models/engine 就绪）
        await client.get('/some/route')

asyncio.run(main())
```

之后同进程内即可正常使用 `get_model()` 等。base_url 用 `http://test` 即可（不走网络）。

## 2. 复现时隔离数据库，别污染真库

- 复制一份现有库（保住表结构）：`cp database.db /tmp/repro.db`
- 在**第一次查询前**覆盖连接（engine 是首次查询时才创建，覆盖太晚就连到真库了）：

```python
from uliweb import settings
settings.ORM.CONNECTION = 'sqlite:////tmp/repro.db'
```

覆盖时机：在发第一个「触发启动」的请求之前/之后都行，但**必须早于任何 get_model 查询**。
用完删掉临时库。

## 3. 认证是复现的最大拦路虎

- 如果项目把 `AUTH_DEFAULT_TYPE` 默认设为 `'ldap'`（如装了 `uliweb_lapps.auth.ldap*`），
  本地复现登录会因 LDAP 配置不可用而失败（如
  `ldap3.core.server.Server() argument after ** must be a mapping, not list`）。
- 复现/调试时切到本地认证：

```python
from uliweb import settings
settings.AUTH.AUTH_DEFAULT_TYPE = 'default'
```

- `uliweb.contrib.auth.create_user()` 返回的是 `(flag, user)` 元组，不是 user 对象：
  ```python
  flag, user = create_user(username='u', password='p', email='e@x.com')
  ```
  这类 API 细节看源码最稳（`uliweb/contrib/auth/__init__.py`）。

## 4. 分层隔离，定位问题在哪一层

从现象倒推，逐层排除，避免在错误层猜：

1. **模型层**：直接在进程内跑 `obj.save()` / `obj.transition()` 等，确认模型逻辑没问题。
2. **请求解析层**：检查 body / 参数 / 路由是否读到期望值（见 [views.md](./views.md) 的
   `get_params()` 不解析 JSON）。
3. **鉴权/中间件层**：看日志里的 `Access denied`、`RedirectException` 等。

通常真 bug 在「请求/响应边界」，而不是业务逻辑。

## 5. 改实现后必须同步更新测试 mock

修改了 request 读取方式（例如从 `get_params()` 改成 `get_json()` + 回退）后，依赖
`get_params()` 的单元测试会挂——因为测试里 mock 的 `request` 往往只有
`get_params`，没有 `get_json`。

- 给 mock 的 `request` 补上 `get_json`（返回 `None` 让它落到 form 分支），或在
  `_setup` 里统一加。
- 改完跑**全量**测试（不只单文件），确保没漏。

## 总结

真 bug 常在请求/响应边界。先做「真实请求 + 临时库 + 绕过认证」的最小复现，
用堆栈说话，改完同步补测试 mock 并跑全量测试。
