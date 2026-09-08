# Intent: 一个 endpoint 可映射多个 URL（exposes-multi-url）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 intent/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: approved          <!-- draft → 审阅通过 → approved -->
创建: 2026-09-08
---

- 作者: zhangchunlin
- 关联工单/事故: 承接 `intent/core-revisit/`（`_init_routes` EXPOSES 覆盖逻辑的既定行为被确认后，决定改为期望语义）

## 问题 （今天做不到什么 / 痛点）

`_init_routes` 的 EXPOSES 覆盖逻辑（`uliweb/core/SimpleFrame.py:1946-1952` 等）以 **endpoint** 作为唯一标识：
当 settings 的 `EXPOSES` 把某个已由 `@expose('/test')` 注册的 endpoint（如 `test.views.test`）重新映射到另一 URL（如 `/`）时，
会按旧 `@expose` 的 URL 把原路由**删除**，导致 `/test` 消失、只剩 `/`。

这违背了期望的映射语义：**一个 URL 只能映射到一个方法/函数路径（handler）**（天然成立），
但**一个方法/函数路径应该可以被多个 URL 映射**。当前实现把「同一 endpoint 只能有一个路由」强加给了用户。

## 期望结果 （更好的情况长什么样）

- 一个 URL 端点仍只对应一个 handler（该约束保持不变）。
- 一个 handler 可被多个 URL 映射：`@expose('/test')` 注册 `test.views.test` 后，
  再在 settings `EXPOSES` 里把 `/` 映射到 `test.views.test`，则 `/test` 与 `/` **同时存在**，都指向同一 handler。
- 移除「同一 endpoint 被 EXPOSES 覆盖时删旧路由」的逻辑；EXPOSES 的映射只负责**新增**路由。
- `nosetests --with-doc test`（仓库根）全绿。

## 受影响的用户与系统

- 使用 settings `EXPOSES`（应用级与全局）把 URL 映射到视图 endpoint 的用户。
- 相关文件：`uliweb/core/SimpleFrame.py`（`_init_routes` 的 EXPOSES 处理，含应用级 ~L1874-1879 与全局 ~L1946-1952、~L1984-1990 多处同类覆盖逻辑）。
- `registered_routes`（以 endpoint 为 key）在去重/覆盖中的角色需要重新审视。

## 约束

- 保持对外契约向后兼容；不引入新依赖；不 reintroduce werkzeug。
- 一个 URL → 一个 handler 的语义保持不变；同一 URL 被多个 endpoint 冲突映射时的行为需明确（倾向保留先注册者或报错，见开放问题）。
- sync/async 双轨改动须两条路径都考虑（AGENTS.md 约定）。
- 改动需跑通 `nosetests --with-doc test`。

## 开放问题（已定案）

- **`registered_routes` 的去重/覆盖用途还要不要** → **已定案**：把「endpoint → 路由」字典改为「**url → 路由**」字典。不再按 endpoint 删旧路由（实现「一个 endpoint 可多个 URL」）；url 字典用于 URL 级去重（同一 url+handler 不重复注册）并支撑下面的「后者覆盖」。
- **同一 URL 被映射到两个不同 endpoint 时** → **已定案**：**后者覆盖**前者（后注册的路由替换先注册的）。
- **是否保留「EXPOSES 覆盖同名 endpoint 的旧路由」作为兼容选项** → **已定案**：彻底改为「EXPOSES 只新增」，不保留旧的 endpoint 级覆盖行为。
