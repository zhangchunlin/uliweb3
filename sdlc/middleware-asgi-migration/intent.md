# Intent: legacy process_* 中间件逐步废弃，沉淀 ASGI 迁移 skill（middleware-asgi-migration）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 sdlc/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: draft            <!-- draft → 审阅通过 → approved -->
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: 承接 `sdlc/core-agent-friction/` 与 `sdlc/core-revisit/` 中关于中间件双轨/生命周期冗余的复盘结论

## 问题 （今天做不到什么 / 痛点）

- `process_request / process_response / process_exception` 是 **WSGI 时代的相位（phase）中间件模型**，与 ASGI 的流式/异步/双向模型阻抗失配（详见 `sdlc/core-agent-friction/` 复盘：响应需整体缓冲 `capture_send`、不覆盖 WebSocket/lifespan/SSE、顺序语义依赖反序 insert(0)）。
- 框架内部已无任何内置中间件使用 `process_*`（全部迁移到 `dispatch(request, call_next)`），但该 legacy 生命周期机制（`_process_middleware`、`process_*_classes` 列表、`has_traditional` 分支）仍然存在，成为"第二套请求生命周期"冗余。
- 外部/老应用仍可能使用 `process_*` 中间件；当前既无迁移指引、也无废弃信号，导致这些中间件无限期以 legacy 方式运行，框架无法推进到单一 ASGI 中间件模型。

## 期望结果 （更好的情况长什么样）

- **保留兼容**：`process_*` 中间件在过渡期内**行为完全不变**地继续工作（不破坏老外部应用）。
- **启动期一次告警**：`_init_middlewares` 识别到 legacy `process_*` 中间件时，**仅在启动/初始化时打印一次**提醒（`logger.warning`），提示"此中间件将废弃（3.1 之后），请迁移到 ASGI `dispatch` 方式"；**绝不每请求告警**，也不提供可静默开关。
- **skill 迁移指引**：在 `skills/uliweb-asgi-webapp/`（`references/asgi.md` 中间件章节）沉淀"从 `process_*` 迁移到 `dispatch`"的指导，编码**语义保持**的迁移步骤（而非机械改名），供 coding agent 批量迁移。
- **明确的废弃时间窗**：**3.1 版本之后废弃** `process_*` 中间件模型（届时升级为硬移除/强制迁移），避免"保留一段时间"无限期挂起。3.1 及之前保留兼容，仅在启动期打印一次迁移提醒。
- 框架内部收敛为单一 ASGI 中间件生命周期（legacy 只以兼容 shim 形式存在）。

## 受影响的用户与系统

- 使用 `MIDDLEWARES`（旧称 `WSGI_MIDDLEWARES`）配置 `process_*` 自定义中间件的外部/老应用。
- 相关代码：`uliweb/core/SimpleFrame.py`（`_init_middlewares` ~L1710-1738 的分类逻辑、`_process_middleware` ~L2886、`_build_middleware_stack` 的 `has_traditional` 分支 ~L2972-3002、`_call_middleware_method`）。
- 相关 skill：`skills/uliweb-asgi-webapp/references/asgi.md`（中间件迁移章节）。

## 约束

- 过渡期内 `process_*` 行为**零变更**；只新增告警与文档，不重构其执行语义。
- 告警只在启动期触发一次，不得刷日志/不得影响每请求性能。
- 保持对外契约向后兼容；不引入新依赖；不 reintroduce werkzeug。
- sync/async 双轨改动须两条路径都考虑（AGENTS.md 约定）。
- 改动需跑通 `nosetests --with-doc test`（仓库根）。

## 开放问题

- **废弃时间窗** → **已定案**：3.1 版本之后废弃 `process_*` 中间件模型（届时硬移除）；3.1 及之前保留兼容 + 启动期一次迁移提醒。
- 迁移 skill 内容（已明确，非难点）：单个 `process_*` 中间件的对等 `dispatch` 写法可直接给出（`process_request`→pre 短路返回、`call_next` 包 `try/except` 接 `process_exception`、成功后接 `process_response`）；**框架用"复合 legacy 适配器"在最内层代保多中间件整体顺序/短路语义，用户无需手写**。真正要在 skill 里强调的唯一坑：**实例化时机**——legacy 每请求 new 实例、dispatch 是构建期单例，老中间件若在 `self` 上存每请求状态，迁移时须改为从 `request` 读取。
- **DeprecationWarning 开关/环境变量** → **已定案：不需要提供**。不做可静默/可关闭的开关；启动期迁移提醒始终输出（用 `logger.warning` 而非 `DeprecationWarning`，避免被用户代码吞掉）。
