# Plan：修复 uliweb/core 复盘发现的问题（core-revisit）

<!--
plan.md 由"approved 的 spec.md"驱动生成。评审通过后逐条执行，每完成一步勾选 [x] 并提交。
-->

---
类型: plan
来源: spec.md（approved）
状态: 待执行        <!-- 执行完成 → 全绿 → 提交 → 归档到 REVIEW -->
创建: 2026-09-08
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. fix(SimpleFrame)：`_call_dispatch` 委托 dispatch + 新增 `get_view_env_sync` 双轨**
      实现 `_call_dispatch`（委托 `dispatch.get`/`aget` 触发 `prepare_view_env`）；新增同步 `get_view_env_sync()` 镜像 `get_view_env`。
      验证：`python -c "import uliweb.core.SimpleFrame"`；`nosetests --with-doc test` 无回归。

- [ ] **2. fix(common)：`common.wraps` 改调 `get_view_env_sync`**
      `common.py:281` 改 `application.get_view_env_sync()`。
      验证：`nosetests --with-doc test`；RBAC/auth 相关用例不报 TypeError。

- [ ] **3. fix(rules)：`func.func_dict` → `__dict__`**
      `rules.py:336` 改 `getattr(func, '__dict__', {})`。
      验证：`nosetests --with-doc test`；类视图 subclass 分支可跑。

- [ ] **4. fix(commands)：`get_version` 定义 `self.version` + `sys.ext` 笔误**
      为 `Command` 定义 `version` 属性；`commands.py:351` `sys.ext(1)` → `sys.exit(1)`。
      验证：`python -m uliweb.core.commands --version` 不 AttributeError。

- [ ] **5. fix(uliweb/__init__)：异常类改为从 SimpleFrame 导入**
      删除空 stub，`from uliweb.core.SimpleFrame import HTTPError, RedirectException, UliwebError`；确认 `from uliweb import HTTPError` 与 `error()` 抛的类一致。
      验证：`python -c "from uliweb import HTTPError; from uliweb.core.SimpleFrame import HTTPError as R; assert HTTPError is R"`。

- [ ] **6. fix(SimpleFrame)：`_match_route` 405 延迟到扫完**
      记录首个 PARTIAL，扫完无 FULL 再决定 405/404。加针对性单测（同路径多方法）。
      验证：`nosetests --with-doc test`；新单测通过。

- [ ] **7. fix(SimpleFrame)：`_init_routes_sync` 对齐 `_init_routes`**
      补 EXPOSES 路由、`route_param_types`、`set_app_rules` 前缀逻辑（仅对齐，不过度重构）。若风险过高回退为"补注释说明差异"并结转。
      验证：`nosetests --with-doc test`；`test_url_for.py` 同步路径不回归。

- [ ] **8. fix(SimpleFrame)：统一 `prepare()`/`init()` 启动钩子顺序**
      以 asgi 路径为准统一 `startup_installed`/`_init_routes()` 顺序。
      验证：`nosetests --with-doc test`。

- [ ] **9. fix(SimpleFrame)：`CORS.w` 避免改写全局 response 代理**
      非 OPTIONS 路径用局部响应变量，不落到共享代理。
      验证：`nosetests --with-doc test`。

- [ ] **10. refactor(SimpleFrame)：删死代码**
      删 `_merge_rules`/`ContextStorage`/`handle_http`/`jsonp`/`Response.write`/`use_urls`/`url_adapters`（逐个 grep 确认无引用后删）。
      验证：`grep -rnE '_merge_rules|ContextStorage|handle_http|jsonp' --include=*.py .` 无残留（除外导出）；`nosetests --with-doc test`。

- [ ] **11. docs(SimpleFrame)：清误导注释**
      删 L519-520 starlette.py 残留、L316 重复 `import_`、L318-321 Python 2 死块。
      验证：`python -c "import uliweb.core.SimpleFrame"`；`nosetests --with-doc test`。

- [ ] **12. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净。

## 验证命令
- `nosetests --with-doc test`（仓库根，不要在 test/ 内跑）
- 各步 `python -c "import ..."` / `python -m uliweb.core.commands --version` 冒烟
