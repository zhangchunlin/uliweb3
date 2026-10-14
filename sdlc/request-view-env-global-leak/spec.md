# Spec：async 视图下 `request`/`response` 跨请求串扰的修复

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: sdlc/request-view-env-global-leak/intent.md
状态: 已实现        <!-- 审阅通过后 → approved，触发 plan mode；实现完成 → 已实现 -->
创建: 2026-10-14
---

## 1. 需求（需求是什么）

- 业务问题（复述并收紧自 intent.md）
  - Uliweb3 异步视图在并发下，视图内 `request`/`response` 会读到其它请求的数据（跨请求串扰），已用 `TestServer` + 多并发 + async `await` 稳定复现。
- 用户故事 / 验收标准（Given/When/Then，量化可核对）
  - Given 一个 async 视图，`__begin__` 按 `request.GET['user']` 计算 `self.can_list_all`，视图在 `await asyncio.sleep(0.2)` 后返回该值；
    When 以 N（≥8）个并发请求、各自带不同 `user` 参数请求；
    Then 每个响应返回的 `can_list_all`/`owner` 必须与本请求 `user` 一致，跨请求串扰为 0。
  - Given 同一视图在 `await` 之后读 `request.GET`；
    When 并发请求；
    Then `await` 前后读到的 `request` 必须是同一个（同任务内 `request` id 不变）。
- 非目标（明确不做，防范围蔓延）
  - 不改 `self` 每请求实例化模型（该模型本身正确）。
  - 不重构 `LocalProxy`/contextvar 隔离机制本身。
  - 不改 `settings`/`application` 的常驻注入（如安全则保留；仅评估，不强制收敛）。

## 1.5 根因与证据（为什么需要这么改）

> 本节是本 spec 设计的**输入依据**，评审时需与设计对得上。依据来源：Uliweb3 源码逐行核验 + `TestServer` 并发复现（复现工程后续纳入 `test/` 回归）。

- 根因（已定位，SimpleFrame.py）：
  1. `_call_function` 执行 `handler.__globals__.update(env)`（:2684），把 `env` 写进**视图模块的全局命名空间**。
  2. `get_view_env` 构建 `env` 时注入 `local_env['request'] = get_request()`（:2629）、`local_env['response'] = get_response()`（:2630）—— 即**当前 Request/Response 对象**。
  3. 合起来：每次请求都把视图模块的**共享模块级全局** `views.py.request` 覆盖成当前 Request 实例；`views.py.request` 是所有请求共享的，并发下互相覆盖 → async 视图 `await` 之后读 `request` 拿到的是别的请求的数据。
- 证据链（复现/对照）：
  - 视图内 `request` 不是 `LocalProxy`，而是被框架重绑定的共享模块全局：访问 `request._var` 抛 `'Request' object has no attribute '_var'`。
  - 同一 asyncio 任务里，`request` 在 `await asyncio.sleep(0.3)` 前后从本请求对象变成另一请求对象（`U0 → U1`）。
  - 对照：视图内自建的一个 `ContextVar`（不经过框架全局注入）正确隔离 → 佐证是框架的全局覆盖、而非任务/contextvar 隔离本身失效。
  - 对照：同一 harness 用原生 Starlette 跑，并发下 `request` 完全隔离。
  - 修复对照：仅从 `get_view_env` 移除 `request`/`response` 注入后，并发串扰由 ~50% 降至 0（详见 plan.md 证明）。

## 2. 范围与边界

- 在范围内：
  - `uliweb/core/SimpleFrame.py` 的 `get_view_env`（async 双轨）
  - `uliweb/core/SimpleFrame.py` 的 `get_view_env_sync`（sync 双轨）
  - `uliweb/core/SimpleFrame.py` 的 `_call_function` 对 `handler.__globals__` 的注入行为（:2684/:2685）
- 在范围外：
  - 中间件、路由、`expose`、`LocalProxy` 实现本身（不触碰）
  - gerritboard 应用层代码（本修复是框架层；应用层可用同一修复原理规避，但不在本 spec 改 gerritboard）
- 关联系统：视图模块（`apps/**/views.py`）、`uliweb/__init__.py` 导出的 `request`/`response` 代理。

## 3. 设计

- 总体方案（一句话架构决策）
  - **把注入到视图模块全局的 `request`/`response` 的值，从"每个请求的 Request/Response 对象"改为"稳定的 `LocalProxy` 代理对象"**。代理是恒定单例、通过 contextvar 取当前请求，因此写进共享全局是幂等的、不会互相覆盖；视图内 `request` 因此走 contextvar 隔离，并发正确。
  - 同时覆盖两种视图：显式 `from uliweb import request` 的视图（用同一代理，无影响）；**不 import `request`、纯靠框架注入全局**的视图（照样能用 `request`，且并发隔离正确）。
- 组件/模块划分
  - `get_view_env`（:2620）：把 `local_env['request'] = get_request()`（:2629）改为注入 `request` 代理本身；`local_env['response'] = get_response()`（:2630）同理改为注入 `response` 代理。
  - `get_view_env_sync`（:2638）：同样改 :2645/:2646 两行为注入代理。
  - `_call_function`（:2679）：`:2685 handler.__globals__['env'] = env` 因 `env` 内 `request`/`response` 已变为稳定代理，不再造成串扰，**无需特殊处理**（保留以兼容 `env.*` 用法）。
- 数据与接口
  - 对外行为不变：`request.GET`、`request.user`、`await request.get_params()` 等通过 `LocalProxy` 照常工作，且并发隔离正确。
  - 兼容性：显式 `from uliweb import request` 的视图不受影响；**不 import、纯靠框架注入全局的视图**因注入值改为稳定代理而同样可用且正确——两类写法均被覆盖，不再有"受影响写法"。
- 错误与降级
  - 无新增异常面；修复只是移除错误的全局写入，不引入新路径。

## 4. 约束与策略落地

- 安全 / 并发：修复后并发隔离是安全底线，验收以串扰为 0 为准。
- 向后兼容：`@expose`、`settings.ini`、`request`/`response` 全局用法、参数注入均保持可用。
- **双轨同步**：`get_view_env` 与 `get_view_env_sync` 必须同步修改（AGENTS.md 明确要求），否则 sync/async 行为不一致。
- 需要在工程介入前解决掉的顾虑点（逐一列出并给出解决状态）：
  1. 修复后"不 import `request`、仅靠框架注入全局"的视图是否仍可用？→ **解决**：注入值改为稳定 `LocalProxy` 代理后，此类视图仍能 `request.GET` 且并发正确（已实测，见 plan 证明）。
  2. `env` 全局（:2685）是否需处理？→ **无需**：`env` 内 `request`/`response` 已变为稳定代理，写入全局幂等、不再串扰；保留以兼容 `env.*` 用法。

## 5. 开放问题与结转

- 来自 intent.md 的开放问题 → 本轮回答状态：
  1. `handler.__globals__['env'] = env`（:2685）是否收敛 → **已闭合**：`env` 内 `request`/`response` 改为稳定代理后无需处理，保留以兼容 `env.*` 用法；回归测试覆盖"视图读 `env` 全局"的兼容。
  2. `settings`/`application` 常驻注入是否顺带评估 → 不在本 feature 范围，仅记录。
  3. 是否补框架回归测试并纳入 `test/` → **已决策：纳入**。新增 `test/test_view_request_concurrency.py`，把复现固化为并发串扰回归（见 plan.md 证明）。
- 结转事项：无阻塞性存量迁移事项（"不 import 仅靠注入"的写法已被新方案一并覆盖）。

---

### 附：生成本 spec 的提示词（供固化）

```
请阅读附件 intent.md，为把它整合进我们现有代码库产出"需求与设计 spec"。
应用你手头可用的 skills，使计划符合我们的品牌规范、安全策略与 UX 标准。
把 spec 完整写成 spec.md，准备交给工程团队。请清晰描述任何顾虑点，
特别是你无法同时满足相互矛盾策略的地方。
```