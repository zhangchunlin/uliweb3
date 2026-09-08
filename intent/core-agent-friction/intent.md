# Intent: 降低 uliweb 对 coding agent 的理解阻碍（agent-friction）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 intent/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: draft            <!-- draft → 审阅通过 → approved -->
创建: 2026-09-08
---

- 作者: zhangchunlin
- 关联工单/事故: uliweb 设计评审（core-design-cleanup 之后的一轮面向"可读性/可理解性"的评审）

## 问题 （今天做不到什么 / 痛点）

面向 coding agent 开发 uliweb 时，以下设计点会显著增加理解成本、诱发错误改动：

- **巨型单文件 + 命名混淆**：
  - `uliweb/core/SimpleFrame.py` 3557 行，容纳 10 个类 + 大量模块函数/全局，概念边界（Request/Response、路由、分发、异常、全局状态、中间件）无拆分，定位一次改动要扫几千行。
  - 类与代理**同名**：`class Request`/`class Response` 与全小写 `request`/`response`/`settings`/`application`（LocalProxy 全局代理，L313-316）同名，阅读时代理与对象难分。
  - "路由容器"有 4 种含义：模块全局 `url_map = UliwebRouter()`（L440）、`UliwebRouter.url_map`（dict，L325）、`UliwebRouter.router`（Starlette Router，L326）、`AsyncDispatcher.router`（UliwebRouter，L963）。agent 难以判断某 `router`/`url_map` 指向谁、有无 `build()`/`match()`。
  - **死代码残留**：`DispatcherHandler`（L870）定义后从未被使用，agent 会误以为是活跃组件。

- **隐形状态流**：`request`/`response` 通过 LocalProxy/Global/contextvars 隐式传递，数据不经过函数签名，agent 无法用调用图追踪；线程边界还需理解 `copy_context().run()` 桥接（L1809/2918/3285/3399 等）。

- **import 时副作用**：模块顶层 import 时就执行 `url_map = UliwebRouter()`、`pyini.set_env(...)`、`__global__.settings = pyini.Ini(...)`、`settings.set(...)`（L440-458），改动需小心 import 顺序与全局共享。

- **sync/async 双轨重复**：`_init_routes`/`_init_routes_sync`（L1226/1844）、`_init_settings` 内 `load_settings_sync`/`load_settings`（L1100/1158）、`_import_views`；中间件 `_call_middleware_method`（L3285）靠 `iscoroutinefunction` 分流。agent 需判断执行上下文走哪条路径，改动易漏一边。

- **路由注册链条长**：`@expose` → `rules.add_rule` → `parse_class`（HTTP 动词守卫）→ `merge_rules` → `_import_views` → `AsyncDispatcher.router`，endpoint 字符串多层传递，追踪"URL→函数"要跨多文件。

- **隐式行为陷阱**：`error()` 抛 `HTTPError`（不 return）、`Redirect()` 抛 `RedirectException`、同步视图/中间件自动进线程池、`settings` 是 pyini 惰性代理（`settings.GLOBAL.*`/`get_var('FUNCTIONS/...')`）。部分已进 AGENTS.md，其余无文档。

- **工具链与文档分散**：`nosetests --with-doc test` 须仓库根跑；行为契约散落在 AGENTS.md、`intent/asgi-migration/spec.md`、skills、`docs/zh_CN`，无单一架构职责地图。全代码库无类型标注。

## 期望结果 （更好的情况长什么样）

- coding agent 能在不依赖运行时黑盒探查的前提下，快速定位"一个 URL/路由对应哪个函数、request 从哪来、同步 vs 异步走哪条路径"。
- 消除误导性死代码（如 `DispatcherHandler`）与命名歧义（路由容器、类/代理同名）。
- 有一份**架构职责边界地图**（模块地图）与**隐式行为规则清单**（`error()`/`Redirect()`/同步适配器/`copy_context` 桥接/settings 惰性代理），集中放一处并同步 AGENTS.md。
- 对改动最多的文件（SimpleFrame.py）给出拆分或至少清晰分节标注，降低定位成本。
- 测试运行方式与工具链约束在文档中一处可查。

## 受影响的用户与系统

- 未来所有参与 uliweb 开发的 coding agent（读 AGENTS.md/架构文档 → 定位代码 → 改动）。
- 相关文件：`uliweb/core/SimpleFrame.py`、`uliweb/core/rules.py`、`AGENTS.md`、`docs/`、`skills/uliweb-asgi-webapp/`、`intent/asgi-migration/spec.md`。

## 约束

- 面向"文档/命名/结构标注"的改进为主，**不做激进的重构**（不拆文件、不改对外契约、不引入新依赖、不 reintroduce werkzeug）。
- 若涉及删死代码（如 `DispatcherHandler`），先确认无引用再删，且跑通 `nosetests --with-doc test`。
- 文档集中放置，避免再度分散；与已批准的 asgi-migration 设计一致。

## 开放问题

- **是否允许拆分 SimpleFrame.py**：激进拆分 vs 仅文档化职责边界 + 分节标注。倾向后者（风险低），拆文件留作后续。
- **命名去歧义的范围**：仅文档说明（改注释/文档） vs 实际重命名（如 `url_map`/`router`）。重命名改动面大，倾向先文档化，重命名单独评估。
- **架构地图放哪**：AGENTS.md 顶部 vs `docs/zh_CN` 独立架构文档 + AGENTS.md 链接。待定。
