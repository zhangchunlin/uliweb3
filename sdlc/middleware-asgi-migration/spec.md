# Spec：legacy process_* 中间件逐步废弃 + ASGI 迁移 skill（middleware-asgi-migration）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: intent.md（draft，开放问题已由产品负责人就地定案）
状态: approved        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-09-09
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：`process_request/process_response/process_exception` 是 WSGI 时代相位模型，与 ASGI 流式/异步/双向模型阻抗失配；框架内置中间件已全部迁到 `dispatch`，但 legacy 生命周期机制（`_process_middleware`、`process_*_classes`、`has_traditional` 分支）仍存在且零内部使用。外部老应用仍可能用 `process_*`，当前无废弃信号、无迁移指引。

- **验收标准**（Given/When/Then，可核对）：
  - **Given** `MIDDLEWARES` 配置含 legacy `process_*` 中间件，**When** 应用初始化，**Then** 启动期对每个该中间件输出**一次** `logger.warning`（点名中间件、提示 3.1 后废弃、指向迁移 skill）；请求期间**零**告警。
  - **Given** legacy `process_*` 中间件，**When** 发请求，**Then** 行为与告警加入前**完全一致**（现有测试全绿）。
  - **Given** 无 legacy `process_*` 中间件，**When** 应用初始化，**Then** 无任何告警输出。
  - **Given** 迁移者打开 skill `references/asgi.md`，**Then** 能找到"从 `process_*` 迁移到 `dispatch`"一节，含对等写法与"实例化时机"陷阱说明。
  - `nosetests --with-doc test`（仓库根）全绿。

- **非目标**（明确不做，防范围蔓延）：
  - **本阶段不重构** `_process_middleware` / 不引入"复合 legacy 适配器" / 不做硬移除——这些是 3.1 之后的事（见 §5 结转），本阶段保持行为零变更。
  - 不做可静默/关闭开关（产品负责人已定案不需要）。
  - 不改 `process_*` 的执行语义；不重命名符号；不新增依赖；不 reintroduce werkzeug。

## 2. 范围与边界

- **在范围内**：`uliweb/core/SimpleFrame.py`（`_init_middlewares` 识别 legacy 中间件并启动期告警，~L1729-1738）；`skills/uliweb-asgi-webapp/references/asgi.md`（新增迁移小节）+ `SKILL.md`（更新 ~L132-133 的 process_* 支持说明）；`AGENTS.md`（记录 process_* 废弃约定）。
- **在范围外**：`_process_middleware` 生命周期重构；复合 legacy 适配器；3.1 后硬移除；对 `docs/zh_CN` 的大规模改写。
- **关联系统**：`sdlc/core-agent-friction/`（中间件双轨/生命周期冗余的复盘来源）；`sdlc/asgi-migration/`（ASGI 迁移总纲）；`skills/uliweb-asgi-webapp/references/asgi.md`（中间件迁移已有内容）。

## 3. 设计

- **总体方案**：本阶段是**纯增量、零行为变更**——在初始化期加"一次性告警"作为废弃信号，并用 skill 提供迁移指引；把"收敛到单一生命周期"延后到 3.1 后的独立特性。

- **3.1 启动期告警（SimpleFrame.py）**
  - 在 `_init_middlewares` 的分类循环（~L1729-1738）里，当检测到 `hasattr(middleware_cls, 'process_request'/'process_response'/'process_exception')` 时，记录该中间件名。
  - 循环结束后，对每个记录的 legacy 中间件输出一次 `logger.warning`，形如：
    `Middleware '<name>' uses deprecated process_* (WSGI-phase) hooks; they will be removed after uliweb 3.1. Migrate to ASGI `dispatch(request, call_next)` — see skills/uliweb-asgi-webapp (references/asgi.md).`
  - 用 `logger.warning`（不是 `DeprecationWarning`，避免被用户代码吞掉；也不做开关）。
  - 该告警只发生在启动/初始化路径，不进入请求路径 → 天然满足"绝不每请求告警"。

- **3.2 skill 迁移指引（skills/uliweb-asgi-webapp）**
  - `references/asgi.md` 中间件章节新增"从 `process_*` 迁移到 `dispatch`"：
    - 给出对等写法（`process_request`→pre 短路返回；`call_next` 包 `try/except` 接 `process_exception`；成功后接 `process_response`）。
    - 强调**实例化时机陷阱**：legacy 每请求 new 实例、dispatch 是构建期单例，老中间件若在 `self` 存每请求状态，须改为从 `request` 读取。
    - 注明框架在 3.1 前自动兼容（保留 `process_*` 行为），3.1 后将废弃。
  - `SKILL.md` ~L132-133 的 alert 块补一句废弃说明，指向该迁移小节。

- **3.3 AGENTS.md 约定**
  - 在相关约定处补一条：`process_*` 中间件为 WSGI 相位模型，3.1 后废弃；新中间件一律用 `Middleware.dispatch(request, call_next)`；编码 agent 迁移时遵守"实例化时机"规则（状态从 request 读，不存 self）。

## 4. 约束与策略落地

- 行为零变更（除新增启动期告警）；不重构 `_process_middleware`；不新增依赖；不 reintroduce werkzeug；向后兼容。
- 告警只在启动期、每个 legacy 中间件一次；不影响请求路径性能。
- sync/async 双轨约束：本改动只在 `_init_middlewares`（同步路径），若涉及 async 对应点须同步（AGENTS.md 约定）。
- 每个改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- 来自 intent.md：废弃时间窗 → **已定案**（3.1 后）；DeprecationWarning 开关 → **已定案**（不需要）；迁移 skill 写法 → **已定案**（对等写法 + 实例化陷阱）。
- **结转（3.1 后独立特性）**：`_process_middleware` 生命周期收敛为"复合 legacy 适配器"洋葱中间件并最终硬移除 `process_*`；届时在 spec 中逐条复核短路/顺序/异常/实例化语义再动刀（有 §3.1 告警作迁移信号，3.1 后可安全移除）。
