# Plan：一个 endpoint 可映射多个 URL（exposes-multi-url）

<!--
plan.md 由"approved 的 spec.md"驱动生成。评审通过后逐条执行，每完成一步勾选 [x] 并提交。
-->

---
类型: plan
来源: spec.md（approved）
状态: 已完成        <!-- 执行完成 → 全绿 → 提交 → 归档到 REVIEW -->
创建: 2026-09-08
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [x] **1. fix(SimpleFrame)：`_init_routes` 改为 URL 级去重/覆盖（一个 endpoint 可多个 URL）+ 单测**
  在 `_init_routes` 内：
  1. `registered_routes` 由 `endpoint -> (rule, endpoint)` 改为 `path -> path`。
  2. 新增局部闭包 `_register(starlette_rule, endpoint, **kwargs)`：同 path 命中则先移除该 path 上的旧路由（`self.router.routes` 与 `self.router.router.routes`），再 `add_route`/`add_websocket_route`（`websocket` 从 kwargs 取出），最后记 `registered_routes[starlette_rule] = starlette_rule`。
  3. merge 循环（L1819-1858）：`@expose` 路由改走 `_register(starlette_rule, endpoint, **kw)`；去掉原 `websocket = kw.pop(...)`+直接 add 与 `registered_routes[endpoint]=...`；保留 `route_param_types`、`static_views`。
  4. 4 处 EXPOSES 块（应用级 list/str、全局 list/str）：删除 `if endpoint/name in registered_routes: remove old_rule` 的 endpoint 级覆盖；先算 `starlette_rule`（全局块用 `full_url`），再 `_register(starlette_rule, endpoint, **kwargs)`；应用级 str 分支保留 `self.router.url_map[name] = self.router.routes[-1]`。
  5. 加单测（`test/test_async_dispatcher.py`）：
     - `@expose('/test')` + `EXPOSES ['/', 'testapp.views.test']` → `/test` 与 `/` 均在 routes。
     - 同一 URL 两个不同 endpoint → 后注册者生效（仅一条）。
     - 同一 URL + 同一 endpoint 重复 → 不重复。
  验证：`python -c "import uliweb.core.SimpleFrame"`；手动场景脚本（同 spec §1 验收）；`nosetests --with-doc test` 全绿。

- [x] **2. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；归档 `intent/exposes-multi-url/REVIEW.md`。
