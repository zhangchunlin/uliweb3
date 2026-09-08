# Uliweb3

<!--
AGENTS.md 放在仓库根目录，全团队共享。每个 agent 会话开始都读它。
规则：agent 同样错误犯两次 → 把纠正写进来；保持简洁（过时内容白占上下文）。
AI-native 工件链见 intent/asgi-migration/（intent → spec → plan → review）。
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
- `uliweb/core/SimpleFrame.py`：核心分发器（Request/Response、AsyncDispatcher、UliwebRouter、中间件栈、同步适配器）
- `uliweb/core/rules.py`：`@expose` 装饰器、路由注册与 `parse_class`
- `uliweb/utils/localproxy.py`：`LocalProxy` / `Global` 全局状态管理
- `intent/asgi-migration/`：AI-native 工件链（intent / spec / plan / review），改动时同步更新

## Things agents get wrong
- **Request 数据读取是异步方法，不是属性**：用 `await request.get_POST()` / `get_FILES()` / `get_json()` / `get_data()` / `get_params()`；访问同步属性 `request.POST` / `FILES` / `json` / `data` 会抛 `RuntimeError`（故意弃用引导迁移）。
- **`error()` 抛 `HTTPError`，无需 return**：视图里 `error("...")` 不要带 return；响应状态码由 `_handle_exception` 取 `errors['status']`，未传 `status` 默认 **500**。
- **类视图方法 auto-register 有守卫**（`rules.py` `parse_class`）：方法名若为 HTTP 动词（get/post/put/delete/patch/head/options/trace/connect）会**跳过** auto-register；如需强制走方法名作路径段用 `__auto_expose__ = True`，禁用用 `__no_auto_expose__ = True`（类级或方法级）。HTTP 动词方法请配合模块级 `@expose` 声明路由。
- **同步视图经协程池适配执行**：同步函数由框架放入线程池（`anyio.to_thread.run_sync`）；新增同步视图无需修改即可运行。
