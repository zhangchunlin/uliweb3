# Plan：清理 uliweb/core 设计缺陷（死代码/遮蔽/异常用错）

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

- [ ] **1. fix(dispatch)：抛字符串改 Exception + anyio 提到模块顶部**
      `dispatch.py` L159/L251 `raise "..."` → `raise Exception(...)`（附有意义 message）；`import anyio` 移到文件顶部，移除循环内 import。
      验证：`pytest test/` 无回归；`python -c "import uliweb.core.dispatch"` 正常。

- [ ] **2. fix(SimpleFrame)：修正异常别名/status_code 用错**
      `jsonp`（L588-603 区域）`raise BadRequest("...")` → `raise StarletteHTTPException(status_code=400, detail="...")`；删除 `BadRequest`/`InternalServerError`/`NotFound` 误导别名或明确各自指向；清理 L727 werkzeug 过期注释。
      验证：`pytest test/`；确认 `error()`/`HTTPError` 状态码路径无回归。

- [ ] **3. fix(SimpleFrame)：get_settings 加载器改名避免遮蔽**
      L900 加载器改名（如 `load_settings_config`），更新 `uliweb/contrib/secretkey/commands.py:19` 调用；确认 L3607 访问器 `from ... import get_settings` 访问语义不变。
      验证：`python -c "from uliweb.contrib.secretkey.commands import *"` 正常；`pytest test/`。

- [ ] **4. refactor(SimpleFrame)：删 _sort_middlewares 遮蔽死代码**
      删 L1914 那份（被 L2555 遮蔽），保留 L2555。
      验证：`pytest test/`；`grep -c 'def _sort_middlewares'` = 1。

- [ ] **5. refactor(SimpleFrame)：删 redirect/json 遮蔽死版**
      删 L515 redirect、L560 json（被 L3621/L3627 遮蔽），保留生效版。
      验证：`pytest test/`；`from uliweb import redirect, json` 正常。

- [ ] **6. fix(SimpleFrame)：清理 werkzeug 残留 get_rule/get_url_adapter**
      `get_rule`（L723）改用 UliwebRouter 的 ASGI 匹配能力重写，移除 `url_map.bind(...).match()`；`get_url_adapter`（L675）去掉返回 Starlette `Router` 的 fallback 分支，统一返回 `UliwebRouter`。
      验证：`pytest test/`；`manage.py get_rule` 路径不再 AttributeError。

- [ ] **7. refactor(context)：瘦身 context.py + 更新引用/测试**
      删 `_ContextProxy`/`request_var`/`response_var`/`settings_var`/`settings_proxy`/`request_proxy`/`response_proxy`/`application_proxy`/`get_request`/`get_response`/`get_settings`；`get_application` 改为复用 SimpleFrame 的（或直接删，改 `uliweb/contrib/staticfiles/__init__.py` L19、SimpleFrame L681 引用 SimpleFrame 版本）；更新 `test/test_url_for_static.py` 去掉 `application_var.set()`（用 SimpleFrame 的 `application`/`__global__`）。
      验证：`pytest test/` 全绿；`grep -rn 'request_var\|_ContextProxy' --include=*.py .` 无生产引用。

- [ ] **8. 文档同步**：核对 `skills/uliweb-asgi-webapp/` 与 `docs/zh_CN/` 是否有引用本意图改动的 API/机制（`context.py`、`get_settings` 加载器、`redirect`/`json`、werkzeug 残留、`get_rule`/`get_url_adapter`），有则同步更新。
      验证：`grep -rnE 'context\.py|get_settings|get_rule|get_url_adapter' skills/uliweb-asgi-webapp docs/zh_CN 2>/dev/null` 人工核对。

- [ ] **9. 终检**：仓库根 `nosetests --with-doc test`（不在 test/ 内跑）全绿（以 OK 收尾）；`git status` 工作区干净。

## 验证命令
- `nosetests --with-doc test`（仓库根，不要在 test/ 内跑，避免相对路径/导入问题）
- 每步涉及的模块 `python -c "import ..."` 冒烟
