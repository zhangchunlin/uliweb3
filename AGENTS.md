# Uliweb3

<!--
AGENTS.md 放在仓库根目录，全团队共享。每个 agent 会话开始都读它。
规则：agent 同样错误犯两次 → 把纠正写进来；保持简洁（过时内容白占上下文）。
AI-native 工件链见 intent/（每个特性一个目录：intent → spec → plan → review）。
-->

## Commands
- Test: `nosetests --with-doc test`（在仓库根执行，不要在 test/ 内跑，避免相对路径/导入问题）
- 或现代 runner：`pytest test/`
- 提交前建议用 git 跟踪变更并保持工作区干净

## Git 提交约定
- **一个目的一个提交**：每次提交只做一件事，把无关改动拆成多个提交
- 提交信息用简短说明 + 可选前缀（如 `docs:`/`refactor:`/`fix:`），与仓库历史风格一致
- 提交前 `git status` / `git diff` 检查，只暂存本提交相关文件

## Verifying your work
- Test: 上面命令执行须以 `OK`（无失败/错误）结束；绝不跳过或删除失败的测试
- 有测试失败就改代码，不改测试
- 报告完成前先跑一遍并贴输出

## Conventions
- Python 3.8–3.13；基于 Starlette/ASGI，**不 reintroduce werkzeug 依赖**
- `@expose`、`settings.ini`、`url_for` 等对外契约保持向后兼容
- 所有 ASGI 相关实现集中在 `uliweb/core/SimpleFrame.py`，不新建独立 `starlette.py`

## Architecture

### 模块职责地图（单一入口）
- `uliweb/core/SimpleFrame.py`：核心分发器（单文件，3557 行）。含 `Request`/`Response`（继承 Starlette）、`UliwebRouter`（路由）、`HTTPError`/`RedirectException`/`error()`/`redirect`/`json`、模块级代理 `request`/`response`/`settings`/`application`、`AsyncDispatcher`（ASGI 分发 + 同步适配器 + 中间件栈）、`ASGIApplication`。各功能区在文件内有 `# =====` 分节标注。
- `uliweb/core/rules.py`：`@expose` 装饰器、路由注册 `add_rule`、`parse_class`（类视图方法 auto-register）、`Expose`。
- `uliweb/core/dispatch.py`：信号/回调注册与触发（`bind`/`call`/`get`/`acall`/`aget`）。
- `uliweb/utils/localproxy.py`：`LocalProxy` / `Global` 全局状态管理（request/response 用 contextvars，settings/application 用普通全局）。
- `intent/asgi-migration/`：AI-native 工件链（intent / spec / plan / review），改动时同步更新。

### 核心数据流 / 路由解析
1. 视图用 `@expose`（`rules.py`）注册；类视图方法经 `parse_class` auto-register（**HTTP 动词方法名会跳过**，见下）。
2. 启动时 `AsyncDispatcher._import_views()` 导入视图模块 → `_init_routes()` 调 `rules.merge_rules()` 汇总 → 注册进 `AsyncDispatcher.router`（`UliwebRouter`）。
3. 请求进来 → `AsyncDispatcher` 匹配 `router` 路由 → 分发到 endpoint 函数；同步函数经 `anyio.to_thread.run_sync` 在线程池执行。
4. 端到端：URL → 路由 → endpoint（字符串）→ `get_handler()` 解析为可调用视图。

## Things agents get wrong
- **Request 数据读取是异步方法，不是属性**：用 `await request.get_POST()` / `get_FILES()` / `get_json()` / `get_data()` / `get_params()`；访问同步属性 `request.POST` / `FILES` / `json` / `data` 会抛 `RuntimeError`（故意弃用引导迁移）。
- **`error()` 抛 `HTTPError`，无需 return**：视图里 `error("...")` 不要带 return；响应状态码由 `_handle_exception` 取 `errors['status']`，未传 `status` 默认 **500**。
- **`Redirect()` 抛 `RedirectException`，无需 return**：`Redirect(url)` 内部 `raise RedirectException(url)`，用法与 `error()` 一致，不要带 return。
- **`settings` 是 pyini 惰性代理**：`settings` 是 `LocalProxy(use_contextvars=False, env=__global__)` 包装的 `pyini.Ini`。用 `settings.GLOBAL.*`（来自 settings.ini）或 `settings.get_var('FUNCTIONS/...')` 读取；惰性加载，访问才读文件。
- **类视图方法 auto-register 有守卫**（`rules.py` `parse_class`）：方法名若为 HTTP 动词（get/post/put/delete/patch/head/options/trace/connect）会**跳过** auto-register；如需强制走方法名作路径段用 `__auto_expose__ = True`，禁用用 `__no_auto_expose__ = True`（类级或方法级）。HTTP 动词方法请配合模块级 `@expose` 声明路由。
- **同步视图/中间件经协程池适配执行**：同步函数由框架放入线程池（`anyio.to_thread.run_sync`）；新增同步视图无需修改即可运行。
- **contextvars→线程必须用 `copy_context().run()` 桥接**：任何新增的"同步代码在线程池执行"点（视图/中间件/回调），必须用 `contextvars.copy_context().run(...)` 把当前上下文传进线程，否则线程内读 `request`/`response` 代理会得 `None`。参考现有 `_call_function`、`_call_middleware_method`。
- **sync/async 双轨方法成对出现**：如 `_init_routes`/`_init_routes_sync`、`load_settings`/`load_settings_sync`。改其一须考虑另一条路径是否同步更新，别只改一边。
