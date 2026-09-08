# 评审：core-revisit（core 复盘：6 个真实 bug + 双轨对齐 + 死代码/注释清理）

<!--
REVIEW.md 作为本意图工件链的 Deploy 阶段工件（前序：intent.md → spec.md → plan.md → 实施提交）。
记录本次评审结论（审计轨迹），并作为后续 AI 进评审环的评审策略。
前序工件见同目录 intent.md / spec.md / plan.md。
-->

---
类型: review
来源: plan.md（实施提交历史）
状态: approved
创建: 2026-09-08
评审: zhangchunlin（技术负责人）
---

## Passes（评审跑哪些 pass）

- **Bugs**：逻辑错误、坏掉的边界情况、细微回归
- **Security**：注入风险、认证缺口、日志里的 PII、路径遍历
- **Compliance**：改动符合 spec.md / plan.md 与设计原则（一个目的一个提交、不 reintroduce werkzeug、ASGI 实现集中 SimpleFrame、对外契约 `from uliweb import`/`url_for`/`@expose` 保持兼容）

## 评审对象（build 产物）

- 实施提交已合入 `asgi` 分支，共 12 个提交：
  - `8af8b7b` `_call_dispatch` 委托 dispatch.acall；新增 `get_view_env_sync`/`_call_dispatch_sync`/`_build_view_env` 双轨
  - `947030b` `common.wraps` 改调 `application.get_view_env_sync()`
  - `a4135b8` rules.py `func.func_dict` → `getattr(func,'__dict__',{})`（Python 3 兼容）
  - `f4a1951` commands.py Command 加 `version = getattr(uliweb,'__version__','')`；`sys.ext(1)` → `sys.exit(1)`
  - `ecc8e7f` uliweb/__init__.py 删空 stub，改从 SimpleFrame 导入 HTTPError/RedirectException/UliwebError 真类
  - `5435cb1` `_match_route` 扫完全部路由再定 405/404（同路径多方法），加单测
  - `11bf774` 澄清 `_init_routes_sync` 为简化测试路径（非 `_init_routes` 等价）
  - `ab3216d` 澄清 async/sync 启动钩子顺序为有意差异，避免误导性统一
  - `ebe684a` CORS 非 OPTIONS 路径仅处理真 Response，不再改写全局代理
  - `b041a72` 删内部死代码 jsonp/ContextStorage/handle_http/use_urls/url_adapters；保留公共契约 `_merge_rules` 与 `Response.write`
  - `0da43d6` 清误导注释（starlette.py 残留、重复 `import_`、Python2 `set` 死块）
- 验收门槛（plan.md §终检）：`nosetests --with-doc test` 通过（**321 passed，OK**）。

## 评审结论

| 维度 | 结论 | 备注 |
|------|------|------|
| **Bugs** | 通过 | 修复 6 个真实 bug（wraps 双轨、func_dict、sys.ext、异常类导入、405 遮蔽、CORS 全局代理）；`_match_route` 有针对性单测覆盖 |
| **Security** | 通过 | 无新增注入/路径面；删除的 handle_http 未被引用 |
| **Compliance** | 通过 | 一个目的一个提交；未拆 SimpleFrame.py；`_merge_rules`/`Response.write` 属公共契约故保留；双轨方法同步更新 |
| 测试 | 通过 | 验收命令全绿，新增 1 条路由匹配单测 |

**审批决定：approve**。未发现 Important 级问题。

## 待跟进（结转至 Maintain 阶段，非阻塞）

1. **`_init_routes_sync` 与 `_init_routes` 仍不对等**：sync 版缺 `_import_views`/EXPOSES 覆盖/`route_param_types`/`set_app_rules`。本次按 plan 兜底策略仅补注释澄清；若将来 sync 路径被生产使用，需真正对齐或废弃。
2. **async/sync 启动钩子顺序差异**（`init()`: `_init_routes` 先 vs `prepare()`: `startup_installed` 先）：两路径各有正当理由（timezone 改 now() vs staticfiles 用 expose 注册静态路由）。未强行统一，需产品决策确认是否收敛。
3. **`_merge_rules` 与 `Response.write`（空实现）**：无仓库内引用但属 `from uliweb import`/Response 公共契约，暂保留；如需彻底清理须评估外部依赖后另立意图。
4. **`_sort_middlewares` 仍存在于 SimpleFrame**：本次未在 plan 范围内处理，后续可单独核实是否死代码。
