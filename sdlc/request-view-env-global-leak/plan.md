# Plan: 修复 async 视图下 `request`/`response` 跨请求串扰

<!--
plan.md 由工程师在 coding agent 的 plan mode 里基于已批准的 spec.md 生成；审阅满意后提交。
要求：一个从没看过这段对话的工程师也能仅凭计划实现。
实现偏离计划时，在同一个提交里更新 plan.md。
-->

---
类型: plan
来源: sdlc/request-view-env-global-leak/spec.md
状态: 已实现          <!-- 审阅通过后 → approved，进入实现；实现完成 → 已实现 -->
创建: 2026-10-14
审批: <待产品负责人签字>
---

## 背景（根因，来自已验证的复现）

`_call_function`（`uliweb/core/SimpleFrame.py:2684`）执行 `handler.__globals__.update(env)`；`get_view_env`（:2629-2630）把 `local_env['request']=get_request()`、`local_env['response']=get_response()` 注入 `env`。于是每个请求都把视图模块的**共享模块级全局** `views.py.request` 覆盖成当前 Request 实例。并发下互相覆盖 → async 视图 `await` 之后读到别的请求的 `request`。

已用 `TestServer` 验证两条路径：
- 直接移除该注入：并发下 `request` 稳定、`self.can_list_all`/owner 100% 正确（修复前 ~50% 串扰）。
- **改进方案（采用）**：把注入值从"每请求 Request 对象"改为"稳定 `LocalProxy` 代理"——实测连"不 import request、纯靠框架注入"的视图也并发正确（8 并发串扰 = 0），且 `env` 全局（:2685）随之无需特殊处理。

## 改动的文件

- `uliweb/core/SimpleFrame.py`（修改）
  - `get_view_env`（:2620）：把 `local_env['request'] = get_request()`（:2629）改为注入 `request` 代理本身；`local_env['response'] = get_response()`（:2630）同理注入 `response` 代理。
  - `get_view_env_sync`（:2638）：把 `local_env['request'] = get_request()`（:2645）/ `local_env['response'] = get_response()`（:2646）同样改为注入代理。
  - `_call_function`（:2679）：`:2685 handler.__globals__['env'] = env` **无需改动**（`env` 内 `request`/`response` 已为稳定代理，写全局幂等、不串扰）。
- `test/test_view_request_concurrency.py`（新增）：把 `/tmp/uliweb_repro` 复现工程固化为**框架回归测试**（`TestServer` + 并发 async/sync 视图 + "不 import" 视图），见"证明"。

## 工作顺序

1. **改 async 轨注入**：`get_view_env` 里把 `get_request()`/`get_response()` 换成对应 `LocalProxy` 代理对象（`request`/`response`），保留 `application`/`settings` 注入。
2. **改 sync 轨注入**：`get_view_env_sync` 与第 1 步对称。
3. **确认 `env` 全局兼容**：验证 `handler.__globals__['env'] = env`（:2685）下，视图读 `env.request`/`env.response` 仍正确（应为同一代理，行为不变）；无需额外改动。
4. **新增回归测试**：新建 `test/test_view_request_concurrency.py`（见"证明"），纳入 `test/` 随 `pytest test/` 跑。
5. **回归验证**：跑 `pytest test/`（AGENTS.md 约定：根目录执行，须以 OK 结束）。

## 风险与缓解

- 最可能弄坏：依赖"模块全局 `request` 被框架填成当前 Request"的存量视图（罕见、本身是 bug 源）。
  - 缓解：本仓库无此类用法；若外部存在，属迁移事项（spec §5 结转），不作为阻塞。改为显式 `from uliweb import request` 即可。
- 最冒险步骤：第 2 步改 `env` 全局注入，可能影响用 `env.request`/`env.response` 的视图。
  - 缓解：先 grep 仓库内 `env.request`/`env.response` 用法，确认无依赖后再收敛；有则保留兼容分支。
- 双轨不同步风险：漏改 `get_view_env_sync` 会导致 sync/async 行为不一致。
  - 缓解：两处对称修改，回归测试同时覆盖 async 视图与 sync 视图。
- 放弃了的其他做法及原因：
  - 在 `_call_function` 里用 `copy_context().run` 包住全局写入 → 不能解决"共享模块全局被多次覆盖"，且引入额外上下文复杂度。
  - 让 `request` 全局仍指向 Request 但每次请求改回 LocalProxy → 治标不治本，仍需每次覆盖，串扰窗口仍在。

## 证明（如何证明它工作）

- 回归测试 `test/test_view_request_concurrency.py`（新增，量化可核对）：
  - 测试基建：临时项目（`tempfile` + 写 `settings.ini` + app views.py，参考 `test/test_async_dispatcher.py` 的 `create_temp_project` 约定），`TestServer` 起真实服务器，`httpx.AsyncClient` + `asyncio.gather` 并发。
  - async 视图并发串扰：视图 `__begin__` 按 `request.GET['user']` 算 `self.can_list_all`，`api` 在 `await asyncio.sleep(0.05)` 后返回 `self.can_list_all`/`owner` + `await` 后读的 `request`；N=16 并发各带不同 `user`；断言每个响应都与本请求 `user` 一致（错误 = 0）。
  - sync 视图并发串扰：同一断言但同步视图，覆盖双轨（`get_view_env_sync`）。
  - "不 import request、纯靠框架注入全局"的视图：视图代码**不** `from uliweb import request`，仍断言并发正确（覆盖方案对被放弃写法的兼容；已实测 8 并发串扰 = 0）。
  - 该测试在修复前失败（串扰 > 0）、修复后通过 —— 作为本 bug 的回归护栏。
- 全量回归：`pytest test/` 以 OK 结束（无失败/错误）。
- 复现工程（/tmp/uliweb_repro，实现期临时自证，不入库）：修复前 `repro_changes.py` 每轮 ~50% 错；修复后 100% 正确。