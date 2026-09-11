# Spec：async 忘 await 的显式报错（async-await-detection）

---
类型: spec
来源: intent.md（draft，开放问题已就地定案）
状态: approved
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：`request.get_params()`/`get_POST()` 等 ASGI 下是 async，忘 `await` 拿到 coroutine 被当 dict 用导致下游 `.get()` 崩溃或静默失败，报错点与根因无关。
- **范围取向（已定案）**：**不包代理**做运行时拦截；利用 Python 自带 `RuntimeWarning: coroutine was never awaited`；增强提示**仅 debug 模式**。
- **验收标准**：
  - Given debug 模式 + 视图里忘 `await request.get_params()`，When 运行，Then `coroutine '...' was never awaited` 的 RuntimeWarning **可见**（不被 `warnings` 过滤吞掉）。
  - Given 生产模式（非 debug），When 同上，Then 不额外暴露警告/信息给用户。
  - 文档/类型标注明确这些方法在 ASGI 下是 `async`、必须 `await`。
  - `nosetests --with-doc test` 全绿。

- **非目标**：不做运行时"coroutine 被当 dict"拦截；不包代理；不改 `get_*` 返回值类型/接口。

## 2. 范围与边界

- 在范围内：debug 模式下 `warnings` 过滤配置（确保 never-awaited 警告可见）；`request.get_*` 的 docstring/类型标注；`docs/zh_CN` 视图/请求章节。
- 在范围外：包代理；运行时拦截；改 `get_*` 接口形态。
- 关联系统：`sdlc/orm-lazy-init-diagnostics`（同为运行期可诊断性增强）。

## 3. 设计

- **总体方案**：零运行时包装成本——让 Python 自带的 "coroutine was never awaited" 警告在 debug 下可见，辅以文档/类型标注。

- **3.1 debug 模式暴露 never-awaited 警告**
  - 在框架初始化/`prepare()`（debug 时）配置 `warnings.filterwarnings('always', category=RuntimeWarning, message='coroutine .* was never awaited')`，确保该警告不被默认过滤吞掉。
  - 仅在 `DEBUG`/debug 模式生效；生产不配置。

- **3.2 文档与类型标注**
  - `Request.get_params/get_POST/get_json/get_FILES` 的 docstring 明确标注 "async，必须 `await`"。
  - `docs/zh_CN` 视图/请求章节补"忘 await 的排查"（报错形态 + 依赖自带警告）。

## 4. 约束与策略落地

- 不包代理、不改接口、零运行时包装成本。
- 仅在 debug 模式启用，生产不暴露。
- 改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- **`warnings.filterwarnings` 挂载点** → **已定案：settings 加载处**（`load_settings`/`_load_settings` ~L1040-1158；最早执行、DEBUG 已知、双轨成对）。
- **filter 匹配范围宽窄** → **已定案：窄**（`message='coroutine .*Request\.get_.* was never awaited'`，只暴露 request 忘 await，聚焦本意、少噪音；改前缀需跟随）。
- 结转：若 debug 下自带警告仍不够显眼，未来再评估轻量增强（不做代理前提下）。
