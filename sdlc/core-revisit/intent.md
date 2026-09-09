# Intent: 修复 uliweb/core 复盘发现的问题（core-revisit）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 sdlc/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: draft            <!-- draft → 审阅通过 → approved -->
创建: 2026-09-08
---

- 作者: zhangchunlin
- 关联工单/事故: core-design-cleanup 之后的复盘评审（承接 `sdlc/core-design-cleanup/`）

## 问题 （今天做不到什么 / 痛点）

core-design-cleanup 之后重新审视 `uliweb/core`，发现一批新的明显问题，其中 6 个是实际会触发的 bug：

- **Python 3 兼容坏点**：
  - `rules.py:336` `parse_class` subclass 分支用 `func.func_dict`（Python 2 专属，Python 3 应为 `__dict__`）→ 走该分支 `AttributeError`。
  - `commands.py:132` `get_version` 引用未定义的 `self.version` → `uliweb --version` `AttributeError`；`commands.py:351` `sys.ext(1)` 笔误（应 `sys.exit`）。
- **sync/async 双轨没接对**：
  - `utils/common.py:281` `common.wraps` 同步调用 async `get_view_env()` 不加 await → 装饰 RBAC/auth 视图时请求 `TypeError`。
  - `SimpleFrame.py:2731` `_call_dispatch` 是 `pass` 空壳 → `prepare_view_env` 分发钩子永不触发。
  - `SimpleFrame.py:2463-2468` `_match_route` 遇首个 `PARTIAL` 就抛 405，不继续扫描 FULL 匹配 → 同路径后注册的合法方法被遮蔽。
  - `SimpleFrame.py:1249 vs 1867` `_init_routes_sync` 已与 `_init_routes` 漂移（缺 EXPOSES/route_param_types/set_app_rules），但注释声称等价。
- **异常类被空 stub 遮蔽**：`uliweb/__init__.py:22-29` 的 `HTTPError`/`RedirectException`/`UliwebError` 是空类，与 SimpleFrame 真正被 raise/捕获的类不同 → `from uliweb import HTTPError` 拿到错类。
- **启动钩子顺序不一致**：sync `prepare()` 与 async `init()` 的 `startup_installed`/`_init_routes()` 调用顺序相反。
- **CORS 全局代理副作用**：`SimpleFrame.py:589-632` `CORS.w` 非 OPTIONS 路径可能改写共享 `response` 代理或 NameError。
- **死代码残留**：`_merge_rules`（L284）、`ContextStorage`（L893）、`handle_http`（L2332）、`jsonp`（L562）、`Response.write` 空实现（L225）、`use_urls`/`url_adapters`（L462-463）。
- **误导注释**：`SimpleFrame.py:519-520` 仍提"已移至 starlette.py"（与 AGENTS.md 矛盾）；L316 `import_` 重复导入；L318-321 Python 2 死兼容块。

## 期望结果 （更好的情况长什么样）

- 6 个真实 bug 修复，Python 3.8–3.13 下不再触发 AttributeError/TypeError/错误状态码。
- sync/async 双轨一致：`_call_dispatch` 委托 dispatch；`_match_route` 扫完全部路由再定 405/404；`common.wraps` 正确 await；`_init_routes_sync` 与 `_init_routes` 对齐。
- `uliweb.HTTPError`/`RedirectException`/`UliwebError` 与 SimpleFrame 的为同一类（`from uliweb import` 拿到真类）。
- 删除确证死代码，清理误导注释。
- `nosetests --with-doc test`（仓库根）全绿。

## 受影响的用户与系统

- 使用 `uliweb --version`、RBAC/auth 装饰视图、类视图 subclass、`from uliweb import HTTPError` 的代码。
- 相关文件：`uliweb/core/SimpleFrame.py`、`uliweb/core/rules.py`、`uliweb/core/commands.py`、`uliweb/utils/common.py`、`uliweb/__init__.py`。

## 约束

- 保持对外契约向后兼容；不引入新依赖；不 reintroduce werkzeug。
- sync/async 双轨改动须两条路径都考虑（AGENTS.md 约定）。
- 上下文真相源 = SimpleFrame LocalProxy；contextvars→线程用 `copy_context().run()` 桥接。
- 改动需跑通 `nosetests --with-doc test`。

## 开放问题

- **修复范围** → 已定案：**都做**——修 6 个 bug + 清死代码 + 清误导注释；死代码删除前逐个确认无引用。
- **异常类统一方式** → 已定案：**保留 `from uliweb import HTTPError/RedirectException/UliwebError` 兼容**，`uliweb/__init__.py` 改为从 `uliweb.core.SimpleFrame` 导入真类。
- **`common.wraps` 的 await 修法** → 待实现阶段定：`get_view_env` 改同步 vs `wraps` 改异步装饰器，需先看 RBAC/auth 调用方形态，倾向改动面最小的方案。
- **优先级/拆提交粒度** → 已定案：按「一个目的一个提交」：双轨一致性、异常统一、commands 修复、死代码清理、注释清理。
