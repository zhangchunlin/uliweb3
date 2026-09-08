# Spec：修复 uliweb/core 复盘发现的问题（core-revisit）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: intent.md（approved）
状态: 待审阅        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-09-08
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：core-design-cleanup 之后复盘发现 6 个真实 bug（Python 3 兼容、sync/async 双轨没接对、异常类被空 stub 遮蔽）+ 启动钩子顺序不一致 + CORS 全局代理副作用 + 死代码/误导注释。
- **范围取向（已定案）**：**都做**——修 bug + 清死代码 + 清误导注释；保留 `from uliweb import` 兼容；一个目的一个提交。
- **验收标准**：
  - 6 个 bug 修复：Python 3.8–3.13 下不再 AttributeError/TypeError/错误状态码。
  - `_call_dispatch` 委托 dispatch（`prepare_view_env` 钩子生效）；`common.wraps` 正确处理 env。
  - `uliweb.HTTPError`/`RedirectException`/`UliwebError` 与 SimpleFrame 真类一致（`from uliweb import` 拿真类）。
  - 确证死代码删除；误导注释清理。
  - `nosetests --with-doc test`（仓库根）全绿。

## 2. 范围与边界

- 在范围内：`uliweb/core/SimpleFrame.py`、`uliweb/core/rules.py`、`uliweb/core/commands.py`、`uliweb/utils/common.py`、`uliweb/__init__.py`。
- 在范围外：不引入新依赖、不 reintroduce werkzeug、不改对外契约；`_init_routes_sync` 对齐属高风险改动，仅对齐"缺失的注册逻辑"而不过度重构。
- 关联系统：`intent/core-design-cleanup/`（前序，已完成，不回改）。

## 3. 设计

- **总体方案**：修 bug + 双轨对齐 + 异常统一 + 清死代码/注释，逐项小步提交。

- **3.1 双轨与 env**：
  - `_call_dispatch`（SimpleFrame.py:2731）改为委托 `dispatch.get`/`aget` 触发 `prepare_view_env`。
  - 新增同步 `get_view_env_sync()`（与 `get_view_env` 双轨），供 `common.wraps` 调用；`common.wraps`（common.py:281）改调同步版本，RBAC/auth 装饰器不再 TypeError。
- **3.2 Python 3 兼容**：
  - `rules.py:336` `func.func_dict` → `getattr(func, '__dict__', {})`。
  - `commands.py:132` `Command.get_version` 引用 `self.version`：为 `Command` 定义 `version` 属性（默认 `None` 或 `prog_name`）或改引用已有属性；`commands.py:351` `sys.ext(1)` → `sys.exit(1)`。
- **3.3 异常统一**：`uliweb/__init__.py` 删除空 stub，改为 `from uliweb.core.SimpleFrame import HTTPError, RedirectException, UliwebError`，保留 `from uliweb import` 兼容。
- **3.4 路由/匹配**：
  - `_match_route`：改为记录首个 `PARTIAL`，扫完所有路由无 `FULL` 再决定抛 405（有 PARTIAL）还是 404（无）。与 Starlette 语义一致。
  - `_init_routes_sync`：对齐 `_init_routes` 缺失的 EXPOSES 路由、`route_param_types`、`set_app_rules` 前缀逻辑（仅对齐，不过度重构）。
- **3.5 启动顺序**：统一 `prepare()` 与 `init()` 的 `startup_installed`/`_init_routes()` 顺序（以 asgi 路径为准）。
- **3.6 CORS**：`CORS.w` 非 OPTIONS 路径避免改写全局 `response` 代理（改用局部变量，不落到共享代理）。
- **3.7 死代码与注释**：
  - 删无引用：`_merge_rules`（L284）、`ContextStorage`（L893）、`handle_http`（L2332）、`jsonp`（L562）、`Response.write` 空实现（L225）、`use_urls`/`url_adapters`（L462-463）。
  - 清误导注释：L519-520 starlette.py 残留、L316 `import_` 重复导入、L318-321 Python 2 死块。

## 4. 约束与策略落地

- 保持对外契约；一个目的一个提交；sync/async 双轨改动两边都考虑；`copy_context().run()` 桥接规则不变。
- 死代码删除前逐个 `grep` 确认无引用。
- 每步 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- `common.wraps` await 修法 → 已定：加 `get_view_env_sync()` 双轨，`common.wraps` 调同步版（改动面最小）。
- `_init_routes_sync` 对齐属高风险：若对齐后测试/行为异常，回退到"仅补注释说明差异"并结转。
- `_match_route` 405/404 语义变更：需加/改针对性单测覆盖同路径多方法场景。
