# Intent: 惰性模型初始化报错诊断（orm-lazy-init-diagnostics）

---
类型: intent
状态: draft
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: agent-gateway 排障（uliweb-framework-improvement-proposals.md #1）

## 问题

- ASGI 入口懒加载，初始化前访问模型 `User.c` / `filter()` 得到误导性 `AttributeError: type object 'User' has no attribute 'c'`，与真正的业务属性缺失无法区分。
- `settings` 各 section 在初始化前读到 `None`/空对象，易误判"配置没合并"。

## 期望结果

- 未绑定模型入口（`Model.__getattr__('c')`、`filter()` 等）检测 engine 未绑定，抛带指引异常：`Model '<name>' is not bound to an engine. Initialize the app first (send a real request or call prepare()).`
- `get_model()` 在 engine=None 时给出诊断（当前是裸异常）。
- settings 未加载 section 访问时给出 `settings not initialized; app not started yet` 类提示（可开关）。
- 文档补"懒加载时序"一节。

## 受影响的用户与系统

- 所有在 `prepare()`/首请求前访问模型或 settings 的代码/用户。
- 相关文件：`uliweb/orm/__init__.py`（`get_model` ~L1135、`Model` ~L4020、`get_tablename` ~L244）；`uliweb/core/SimpleFrame.py`（settings 惰性 LocalProxy/pyini）。

## 约束

- 只增强报错/诊断，不改变功能行为；向后兼容。
- settings 提示需可开关，避免误报。

## 开放问题

- 报错/提示是否默认开启、如何开关（settings 项还是环境变量）。
- settings 惰性代理与 pyini 的结合点在哪一层加提示最合适。
