# Spec：一个 endpoint 可映射多个 URL（exposes-multi-url）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: intent.md（approved）
状态: approved        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-09-08
---

## 1. 需求（需求是什么）

- **业务问题**（收紧自 intent.md）：`_init_routes` 的 EXPOSES 覆盖逻辑以 **endpoint** 为唯一标识——
  settings `EXPOSES` 把某个已由 `@expose('/test')` 注册的 endpoint（如 `test.views.test`）重新映射到另一 URL（如 `/`）时，
  会删除原 `@expose` 的 `/test` 路由，导致 `/test` 消失。
- **期望语义（已定案）**：
  - 一个 URL 端点只映射一个 handler（保持不变）。
  - 一个 handler 可被多个 URL 映射：`@expose('/test')` 与 EXPOSES `/` 指向同一 endpoint 时，`/test` 与 `/` **同时存在**。
  - EXPOSES 只负责**新增**路由，不再按 endpoint 删旧路由。
- **冲突裁决（已定案）**：同一 URL 被映射到两个不同 endpoint 时，**后者覆盖**前者。
- **验收标准**：
  - `@expose('/test')` + `EXPOSES ['/', 'testapp.views.test']` 后，`/test` 与 `/` 均在 `dispatcher.router.routes` 中。
  - 同一 URL 两个不同 endpoint：后注册者生效，仅保留一条路由。
  - 同一 URL + 同一 endpoint 重复注册：不产生重复路由。
  - `nosetests --with-doc test`（仓库根）全绿。

## 2. 范围与边界

- 在范围内：`uliweb/core/SimpleFrame.py` 的 `AsyncDispatcher._init_routes`（merge 循环 + 4 处 EXPOSES 覆盖逻辑：应用级 list/str、全局 list/str）。
- 在范围外：`_init_routes_sync`（简化测试路径，无 EXPOSES 覆盖逻辑，**不改**）；不引入新依赖；不 reintroduce werkzeug。
- 关联：`sdlc/core-revisit/`（`_init_routes` 的 405/404 与注释已处理，本意图只改 EXPOSES 覆盖/去重语义）。

## 3. 设计

- **总体方案**：把「endpoint → 旧路由」的 `registered_routes` 字典，改为「**path（最终 starlette 规则）→ path**」的 URL 级字典；
  注册前按 **path**（而非 endpoint）移除同 URL 旧路由，实现「同 URL 后者覆盖 / 去重」，并保留「同 endpoint 不同 URL 共存」。

- **3.1 局部闭包 `_register`**（在 `_init_routes` 内定义）：
  ```python
  registered_routes = {}   # path -> path（已注册路由的最终 starlette 规则）

  def _register(starlette_rule, endpoint, **kwargs):
      # 同 URL 后者覆盖 / 去重：移除同 path 上的旧路由
      if starlette_rule in registered_routes:
          self.router.routes = [r for r in self.router.routes if r.path != starlette_rule]
          self.router.router.routes = [r for r in self.router.router.routes if r.path != starlette_rule]
      websocket = kwargs.pop('websocket', False)
      if websocket:
          self.router.add_websocket_route(starlette_rule, endpoint, **kwargs)
      else:
          self.router.add_route(starlette_rule, endpoint, **kwargs)
      registered_routes[starlette_rule] = starlette_rule
  ```
- **3.2 merge 循环**（L1819-1858）：`@expose` 路由注册改为经 `_register(starlette_rule, endpoint, **kw)`；
  去掉原先的 `websocket = kw.pop(...)` 直接 add 与 `registered_routes[endpoint] = ...`（改由 `_register` 按 path 记录）。
  注意保留 `route_param_types`、`static_views` 逻辑不变。
- **3.3 四处 EXPOSES 覆盖块**（应用级 list/str、全局 list/str）：
  - **删除** endpoint 级覆盖（`if endpoint/name in registered_routes: remove old_rule`）。
  - 先把 `starlette_rule` 算出（`_convert_route_param`，全局块用 `full_url`），再调用 `_register(starlette_rule, endpoint, **kwargs)`。
  - 应用级 str 分支保留 `self.router.url_map[name] = self.router.routes[-1]`（供 `url_for` build）。
- **3.4 行为核对**：
  - 同 endpoint 不同 URL（`/test` + `/`）：两次注册 path 不同，互不影响，均保留 → **多 URL 成立**。
  - 同 URL 不同 endpoint：后注册的 path 命中 `registered_routes`，先者被移除 → **后者覆盖**。
  - 同 URL 同 endpoint 重复：path 命中，先者移除再 add → 仅一条（去重）。

## 4. 约束与策略落地

- 保持对外契约（`EXPOSES` 配置格式不变）；一个目的一个提交；sync/async 双轨——本改动仅 async `_init_routes`，sync 无此逻辑无需改。
- 每步 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- `registered_routes` 由 endpoint 级改为 path 级：已定案。
- 同一 URL 不同 endpoint：已定案「后者覆盖」。
- 旧 endpoint 级覆盖行为：已定案「彻底移除，不再提供兼容选项」。
- `_init_routes_sync` 无 EXPOSES 逻辑，保持简化测试路径，**不**在本意图内补齐（属 core-revisit 结转项）。
