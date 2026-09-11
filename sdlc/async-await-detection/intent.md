# Intent: async 忘 await 的显式报错（async-await-detection）

---
类型: intent
状态: draft
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: agent-gateway 排障（uliweb-framework-improvement-proposals.md #6）；本仓库 `user_permissions` 页 500 直接原因

## 问题

- `request.get_params()` / `get_POST()` 在 ASGI 下是 async；忘写 `await` 拿到的是 coroutine 而非 dict，下游 `.get('kw')` 崩溃或静默失败，报错点与根因无关（本次会话开头的真实 500）。

## 期望结果

- **不包代理**。利用 Python 自带的 `RuntimeWarning: coroutine '...' was never awaited`：在 **debug 模式**确保该警告可见（不被 `warnings` 过滤吞掉），让忘 await 尽早暴露。
- 文档/类型标注明确这些方法在 ASGI 下是 `async`、必须 `await`（AGENTS.md 已有，补齐到文档/类型）。

## 受影响的用户与系统

- 迁移自 sync 的视图作者。
- 相关文件：`uliweb/core/SimpleFrame.py` Request `get_params` ~L95、`get_POST` ~L66、`get_json` ~L80、`get_FILES`；`docs/zh_CN` 视图/请求章节。

## 约束

- 不破坏现有同步/已正确 await 的用法。
- 增强提示仅在 debug 模式生效，生产不启用（避免向用户暴露不必要信息）。

## 开放问题

- **是否包代理做运行时拦截** → **已定案：不做**。coroutine 对象本身不能加 `.get`，运行时拦截"coroutine 被当 dict 用"只能靠包一层代理，成本高、易误伤，放弃。
- **启用时机** → **已定案：仅 debug 模式**。生产关闭；依赖 Python 自带 never-awaited 警告 + 文档。
- 待定：如何确保 debug 模式下该 `RuntimeWarning` 可见（`warnings` 过滤器设置）。

