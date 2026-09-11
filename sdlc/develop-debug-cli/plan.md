# Plan：为 uliweb 开发/调试增加面向 coding agent 的命令行工具（develop-debug-cli）

---
类型: plan
来源: spec.md（待审阅）
状态: 待执行
创建: 2026-09-11
审批: （待 spec approved 后执行）
---

## 改动的文件
- `uliweb/core/SimpleFrame.py`（修改）：模块级 `get_apps()`（~L813）在 `GLOBAL.DEBUG` 且 `GLOBAL.AUTO_DEVELOP` 都为真时自动追加 `uliweb.contrib.develop`（去重）。
- `uliweb/core/default_settings.ini`（修改）：新增 `[GLOBAL] AUTO_DEVELOP = True`。
- `uliweb/contrib/develop/commands.py`（修改）：新增 5 个 `Command` 子类。
- `skills/uliweb-asgi-webapp/references/debugging.md`（修改）：补"命令行调试工具"一节，说明 `route`/`urlfor`/`request`/`inspect`/`body` 及 DEBUG+AUTO_DEVELOP 自动启用。
- `docs/zh_CN/06_commands/manage_guide.md`（修改）：命令清单补 develop 新增命令。
- `docs/zh_CN/05_builtin_apps/uliweb_apps.md`（修改）：补 `uliweb.contrib.develop` 条目（调试工具 + 自动启用开关）。
- `AGENTS.md`（可选，修改）：补命令清单与"DEBUG + AUTO_DEVELOP 自动启用 develop"说明。
- `sdlc/develop-debug-cli/`（本目录文档链）。

## 工作顺序

0. **[x] `get_apps` DEBUG+AUTO_DEVELOP 自动注入（前置，chicken-egg 关键）**
   在模块级 `get_apps()`（`SimpleFrame.py:813`）：解析 settings ini 时读 `GLOBAL.DEBUG` 与 `GLOBAL.AUTO_DEVELOP`（`x.GLOBAL.get('AUTO_DEVELOP', True)` 兜底），`DEBUG` 且 `AUTO_DEVELOP` 都为真且不在 `installed_apps` 则追加（`if not in` 去重）；`default_settings.ini` 补 `AUTO_DEVELOP = True`。验证：DEBUG 开+默认开关 → 命令可发现、应用被加载；DEBUG 关 → 不注入；DEBUG 开但 `AUTO_DEVELOP=False` → 不注入；已在 INSTALLED_APPS 不重复。

1. **命令骨架 + 复用现有模式**
   在 `uliweb/contrib/develop/commands.py` 追加命令；统一 `check_apps_dirs = True`、`self.get_application(global_options)` 初始化后只读查询；新增辅助函数（打印格式化、endpoint→file:line、--json 序列化）。

2. **`route`（URL 匹配）**
   构造 `scope`，对 `application.router.routes` 逐条 `route.matches(scope)`；FULL → 打印命中详情 + `get_handler` 视图 file:line + `path_params`；未命中 → 列最接近 path 模式与 methods（404 排查）。

3. **`urlfor`（反向 URL）**
   `url_for(endpoint, **values)`，捕获 `ValueError` 给可用 endpoint 提示。

4. **`request`（进程内真实请求）**
   `httpx.ASGITransport(app=application)` + `AsyncClient(base_url='http://test')`；支持 `--method/--data/--json/--header/--follow`；`asyncio.run()` 包装；打印 status/headers/body/耗时/命中路由。

5. **[x] `inspect`（视图源码/元信息）**
   `application.get_handler(endpoint)` → `inspect` 取 file:line/签名/docstring、判 async；按 `TEMPLATE_TEMPLATE` 推算约定默认模板。

6. **[x] `body`（异步解析调试）**
   构造最小 `Request` scope + body，`await` 各 getter 打印返回值/异常。

7. **[x] 文档同步（skills + docs/zh_CN）**
   - `skills/uliweb-asgi-webapp/references/debugging.md`：新增"命令行调试工具"小节，逐个说明 `route`/`urlfor`/`request`/`inspect`/`body` 的用法与"DEBUG+AUTO_DEVELOP 自动启用 develop"。
   - `docs/zh_CN/06_commands/manage_guide.md`：命令清单补 develop 新增命令。
   - `docs/zh_CN/05_builtin_apps/uliweb_apps.md`：补 `uliweb.contrib.develop` 条目。
   - `AGENTS.md` 补命令清单与自动启用说明。
   验证：渲染/审阅小节完整、命令名与实现一致。

8. **终检**
   仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 干净；`uliweb help` 可见新命令；用 `uliweb route/urlfor/inspect` 各冒烟一次。

## 风险与缓解
- **最可能弄坏**：`get_apps` 注入 DEBUG+AUTO_DEVELOP 判定影响命令发现/应用列表 → 缓解：只在两开关都为真时注入、`if not in` 去重、DEBUG 默认 False、AUTO_DEVELOP 默认 True；用开/关各组合冒烟一次。
- **最冒险一步**：第 0 步动 core 的 `get_apps`（命令发现 + 应用加载共享入口）→ 缓解：改动最小（仅追加判定），跑全量 `nosetests --with-doc test`。
- **次冒险**：第 5 步 `request` 走真实 ASGI 分发，可能触发副作用/连库 → 缓解：`base_url='http://test'` 隔离；文档提示默认不传 auth 以绕认证；不污染真库由使用者负责。
- **放弃的做法**：不新增硬依赖（不用 requests/aiohttp）；不拆分 SimpleFrame.py；`uliweb develop` 保留、不重复发明（二者并存）。

## 证明（如何证明它工作）
- **测试**：`nosetests --with-doc test`（仓库根）全绿（OK），无回归。
- **DEBUG 自动注入**：DEBUG 开+默认开关 → `uliweb help` 可见新命令；DEBUG 关 → 不可见、不注入；DEBUG 开但 `AUTO_DEVELOP=False` → 不注入；已在 INSTALLED_APPS 不重复。
- **命令冒烟**：`uliweb route /some/path`、`uliweb urlfor <endpoint> key=val`、`uliweb inspect <endpoint>` 输出符合预期且 agent 可解析。