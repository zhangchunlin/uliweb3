# Spec：降低 uliweb 对 coding agent 的理解阻碍（agent-friction）

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

- **业务问题**（复述并收紧自 intent.md）：coding agent 开发 uliweb 时，巨型单文件、命名混淆、隐形状态流、双轨重复、多层路由间接、隐式行为陷阱与分散文档导致理解成本高、易写错代码。
- **范围取向（已定案）**：**不做激进重构**——不拆 SimpleFrame.py、不重命名现有符号；以「文档化 + 分节标注 + 删少量确证死代码」为主。
- **验收标准**：
  - AGENTS.md 提供一份**单一入口的架构地图**（模块职责 + 核心数据流 + 隐式行为规则），agent 不必跨多文件拼凑。
  - SimpleFrame.py 有**清晰的分节标注**，每个类/功能区可快速定位。
  - 命名歧义（`url_map`/`router`、类 vs 代理同名）在注释/文档中**说清楚**，不重命名。
  - 确证无引用的死代码（`DispatcherHandler`）删除。
  - `nosetests --with-doc test`（仓库根）全绿。

## 2. 范围与边界

- 在范围内：`AGENTS.md`（架构地图/隐式规则扩充）、`uliweb/core/SimpleFrame.py`（模块 docstring + 分节标注 + 命名澄清注释 + 删 `DispatcherHandler`）。
- 在范围外：拆分 SimpleFrame.py；重命名 `url_map`/`router`/`Request` 等符号；改对外契约；`docs/zh_CN` 大规模改写（架构地图以 AGENTS.md 为单一入口，若确有必要才顺带补一句链接）。
- 关联系统：`sdlc/asgi-migration/spec.md`（保持设计一致性）。

## 3. 设计

- **总体方案**：用文档化消除"看不见就猜"的认知负担；不改变行为，只改注释/文档与确证死代码。

- **3.1 AGENTS.md 扩充（单一入口架构地图）**
  - `Architecture` 一节扩为**模块职责地图**：每个文件 → 职责、关键类/函数、与其他文件的依赖。
  - 新增**核心数据流/路由解析**短述：URL → `@expose`/`rules.add_rule` → `parse_class`（HTTP 动词守卫）→ `merge_rules` → `_import_views` → `AsyncDispatcher.router`。
  - `Things agents get wrong` 补：`Redirect()` 抛 `RedirectException`（不 return）、`settings` 是 pyini 惰性代理（`settings.GLOBAL.*`/`get_var('FUNCTIONS/...')`）、**contextvars→线程必须用 `copy_context().run()` 桥接**（新增同步执行点沿用）、sync/async 双轨方法提示（改动时两边都要考虑）。
  - 保留简洁原则，避免过时内容堆积。

- **3.2 SimpleFrame.py 分节标注与命名澄清（只改注释）**
  - 文件顶部加**模块 docstring**：一句话职责总览 + 分节索引（各节行号/类名）。
  - 在每个类/功能区前加**分节 banner 注释**（`# ===== 节名 =====`）：Request/Response、异常、路由（UliwebRouter）、辅助/全局、HTTPError/redirect/error/json、AsyncDispatcher、ASGIApplication 等。
  - 命名澄清注释：在 `url_map = UliwebRouter()`、`UliwebRouter.url_map`/`.router`、`AsyncDispatcher.router` 处注释各自类型与用途；在 `request`/`response` 代理定义处注释"与 `Request`/`Response` 类的区别"。

- **3.3 删除确证死代码**
  - `DispatcherHandler`（L870 附近）：先 `grep` 确证全库无引用后删除。

## 4. 约束与策略落地

- 不拆分文件、不重命名符号、不改对外契约、不新增依赖、不 reintroduce werkzeug。
- 所有改动以注释/文档为主，行为零变更（除删确证死代码）。
- 每个改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- 来自 intent.md：拆分 → 不拆（文档化+分节）；命名 → 仅文档化；架构地图 → AGENTS.md。均已定案。
- 结转：SimpleFrame.py 是否后续真正拆分、`url_map`/`router` 是否重命名 → 留待独立评估，不在本意图。
- 备注：若 `docs/zh_CN` 中某文档明显与 AGENTS.md 架构地图冲突，顺带在 AGENTS.md 指向该文档链接（不重写）。
