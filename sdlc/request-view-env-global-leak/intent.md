# Intent: 修复 async 视图下 `request`/`response` 被视图模块全局覆盖导致的跨请求数据串扰

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 sdlc/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: approved            <!-- draft → 产品负责人审阅修正 → approved -->
创建: 2026-10-14
---

- 作者: zhangchunlin
- 关联工单/事故: gerritboard Change 13596（WSGI→ASGI 迁移评审）暴露；已用 `TestServer` + 并发请求稳定复现

## 问题 （今天做不到什么 / 痛点）

- 在 Uliweb3 的**异步视图**中，视图内 `request`（或 `response`）读到的数据可能属于**另一个并发请求**，导致鉴权判定、查询参数、当前用户等跨请求错乱。
- 复现：并发请求同一视图，`__begin__` 里按 `request` 计算 `self.can_list_all` 会拿到别人请求的值（如普通用户得到 `can_list_all=True`），async 视图 `await` 之后读 `request` 更会稳定读到"最后一个请求"。
- 根因已定位（SimpleFrame.py）：`_call_function` 的 `handler.__globals__.update(env)`（:2684）把 `get_view_env` 注入的 per-request `request`/`response` 对象（:2629/:2630）**写进视图模块的共享模块级全局** `views.py.request`，每次请求覆盖它 → 并发下互相覆盖。`get_view_env_sync`（:2645/:2646）同病。
- 影响面：所有在 async/同步视图里通过 `request`/`response` 访问请求数据的代码，在并发场景下都可能读到别人请求的数据。

## 期望结果 （更好的情况长什么样）

- 每个请求在视图里读到的 `request`/`response` 严格是本请求的，与其它并发请求完全隔离。
- 视图里 `request` 保持为 contextvar 隔离的 `LocalProxy`（`from uliweb import request` 的既有用法），而非被覆盖成的"共享模块全局 Request 实例"。
- 并发压力测试（`TestServer` + 多并发 + async `await`）下，跨请求串扰为 0。
- 保持向后兼容：依赖 `request` 全局变量（未声明为函数参数）的既有视图继续可用；声明 `request` 为参数的视图仍显式传入。

## 受影响的用户与系统

- 所有 Uliweb3 异步 / 同步视图开发者（尤其并发 API、鉴权、中间件访问请求数据的场景）。
- 核心组件：`uliweb/core/SimpleFrame.py` 的 `get_view_env`、`get_view_env_sync`、`_call_function`。
- 相关文件：`uliweb/core/SimpleFrame.py`（改）、`uliweb/utils/localproxy.py`（只读，复用其 contextvar 隔离能力）。

## 约束

- 改动集中在 `uliweb/core/SimpleFrame.py`，不新增独立文件。
- 不 reintroduce werkzeug；保持 `LocalProxy` contextvar 隔离机制，不改成普通全局。
- 保持 `@expose`、`settings.ini`、`request`/`response`/`settings`/`application` 等对外契约向后兼容。
- **sync/async 双轨必须同步修改**（`get_view_env` / `get_view_env_sync`），只改一边会留下双轨不一致。
- 本 feature 仅修框架串扰 bug，不改变 `self` 每请求实例化的现有模型（该模型本身没问题）。

## 开放问题

- `handler.__globals__['env'] = env`（:2685）把含 `request` 的 `env` 也写入模块全局，是否一并收敛/隔离（涉及视图访问 `env.request` 的兼容性）。
- `get_view_env` 注入的 `settings`/`application` 是常驻单例（非 per-request），保留注入是否安全、是否可顺带评估。
- 是否需要为本修复补一条 Uliweb3 回归测试（进入现有测试套件，`pytest test/`），以及是否要把复现工程纳入 `tests/`。