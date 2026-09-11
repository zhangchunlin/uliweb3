# Spec：为 uliweb 开发/调试增加面向 coding agent 的命令行工具（develop-debug-cli）

---
类型: spec
来源: intent.md（draft）
状态: approved
创建: 2026-09-11
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：coding agent 调试 uliweb 应用时，懒加载使"窥探"困难、404 排查靠猜、请求/响应边界无法不开服务器复现、异步 body 解析易踩坑、视图反查/定位不便。
- **范围取向**：只**新增** `uliweb/contrib/develop` 下的**只读调试命令**，不改 uliweb core 的分发/路由/懒加载行为。
- **验收标准**：
  - 新增命令在 `uliweb.contrib.develop` 安装后自动注册，`uliweb help` 可见。
  - `route`：给定 URL(+method)，输出命中 endpoint、视图 file:line、URL 参数、allowed methods；未全命中时输出最接近的 path 模式（供 404 排查）。
  - `urlfor`：给定 endpoint 名（+key=val 参数），输出生成的 URL。
  - `request`：进程内用 `httpx.ASGITransport(app=application)` 发真实请求，输出 status/headers/body/耗时/命中路由；顺带完成懒加载初始化。
  - `inspect`：给定 endpoint，输出源码位置、async 与否、签名、docstring、约定默认模板路径。
  - `body`：给定 raw body + content-type，展示 `get_POST()/get_json()/get_params()/get_data()/get_FILES()` 各自返回值。
  - `DEBUG` 且 `AUTO_DEVELOP` 为真时 develop 自动启用（命令可发现）；`AUTO_DEVELOP=False` 时 debug 下也不加。
  - 文档同步：`skills/uliweb-asgi-webapp` 调试 reference、`docs/zh_CN` 命令清单与 `uliweb.contrib.develop` 条目更新到位。
  - `nosetests --with-doc test`（仓库根）全绿。

- **非目标**：不改变 core 的分发/路由/懒加载行为；不拆 SimpleFrame.py；不重命名现有符号；不新增硬依赖（仅用已存在的 httpx/starlette）。

## 2. 范围与边界

- 在范围内：
  - `uliweb/contrib/develop/commands.py`（新增 5 个 Command 类）。
  - `uliweb/core/SimpleFrame.py` 的模块级 `get_apps()`（~L813）：**当 `GLOBAL.DEBUG` 且 `GLOBAL.AUTO_DEVELOP` 都为真时，自动把 `uliweb.contrib.develop` 追加进 `installed_apps`**（去重 `if not in`），与 `uliweb develop` 的 `include_apps` 注入点（L832）同构。此注入使命令发现（`manage.py collect_commands` → `get_apps`）与运行时应用加载都覆盖。
  - `uliweb/core/default_settings.ini`：新增 `GLOBAL.AUTO_DEVELOP = True`。
  - 必要时 `AGENTS.md` 补命令清单与自动启用说明；`sdlc/develop-debug-cli/` 文档链。
  - **文档同步**：`skills/uliweb-asgi-webapp/references/debugging.md`（新增命令行调试工具小节）、`docs/zh_CN/06_commands/manage_guide.md`（命令清单）、`docs/zh_CN/05_builtin_apps/uliweb_apps.md`（`uliweb.contrib.develop` 条目）。
- 在范围外：`uliweb/core` 其它内部实现改动（分发/路由/懒加载行为不变）；`uliweb develop` 命令本身（保留，二者并存）；非 develop 生产路径（DEBUG 关不注入）；其它 app 的命令。
- 关联系统：`uliweb/core/SimpleFrame.py`（`get_apps` 注入 + 只读复用 `AsyncDispatcher.get_handler`、`UliwebRouter.build`/路由表、模块级 `url_for`）；`uliweb/core/rules.py`（`merge_rules` 作路由真相源之一）；`uliweb/core/commands.py`（Command 基类）；`uliweb/manage.py`（`collect_commands` 依赖 `get_apps`）。
- 关联系统：`uliweb/core/SimpleFrame.py`（只读复用 `AsyncDispatcher.get_handler`、`UliwebRouter.build`/路由表、模块级 `url_for`）；`uliweb/core/rules.py`（`merge_rules` 作路由真相源之一）；`uliweb/core/commands.py`（Command 基类）。

## 3. 设计

- **总体方案**：在 `uliweb/contrib/develop/commands.py` 新增 5 个 `Command` 子类，全部走 `self.get_application(global_options)` 完成初始化后只读查询；异步部分用 `asyncio.run()` 包装。前提：`GLOBAL.DEBUG` 为真时 develop app 被自动启用（见 §2 / 3.0）。

- **3.0 自动启用 develop（DEBUG 判定）**
  - 新增 settings 项 `GLOBAL.AUTO_DEVELOP`（bool，**默认 `True`**），写入 `uliweb/core/default_settings.ini`。
  - 在模块级 `get_apps()`（`SimpleFrame.py:813`）：解析 settings ini 时读取 `GLOBAL.DEBUG` 与 `GLOBAL.AUTO_DEVELOP`（`x.GLOBAL.get('AUTO_DEVELOP', True)` 兜底默认）；仅当 `DEBUG` 且 `AUTO_DEVELOP` 都为真、且 `uliweb.contrib.develop` 不在 `installed_apps` 时追加。
  - 因为 `get_apps()` 只读项目/local settings ini（不读 default_settings.ini），默认值在 `get_apps` 内兜底为 `True`；`AUTO_DEVELOP = False` 时即使 DEBUG 也不自动加。
  - `-EDEBUG=True`/`-EAUTO_DEVELOP` 环境注入不在 `get_apps` 覆盖范围（可接受边缘情况）。
  - 副作用：debug 下同时注册 develop 的 `/develop/*` 网页路由（`views.py`）——开发环境可接受，`AUTO_DEVELOP=False` 可整体关闭，计入验收。

- **3.1 `route`（URL 匹配 / 404 排查）**
  - 输入：`<path>`（必选）、`--method`（默认 GET）。
  - 用 `application.router.routes`（Starlette `Route` 列表），构造 `scope={'type':'http','method':..., 'path':..., 'query_string':..., 'root_path':''}`，逐条 `route.matches(scope)`。
  - `Match.FULL`：打印命中 route 的 path/methods/endpoint、`child_scope['path_params']`、经 `application.get_handler(endpoint)` 得视图 `(mod, handler)` 的 file:line。
  - `Match.PARTIAL` / 无命中：列出 path 模式最接近者，提示方法不匹配或 pattern 不匹配（404 排查）。

- **3.2 `urlfor`（反向 URL）**
  - 输入：`<endpoint>`（必选）+ 任意 `key=value` 位置参数。
  - 调 `url_for(endpoint, **values)`（SimpleFrame 模块级，转发到 `application._url_for`），打印结果；`ValueError` 时给出可用 endpoint 提示。

- **3.3 `request`（进程内真实请求）**
  - 输入：`<path>`（必选）、`--method`（默认 GET）、`--data`（表单）、`--json`（JSON body）、`--header`（可多个）、`--follow`。
  - `application` 本身是 ASGI callable，直接 `httpx.ASGITransport(app=application)` + `httpx.AsyncClient(transport=..., base_url='http://test')` 发请求（同 skill `debugging.md` 姿势）。
  - 打印 status、关键 headers、body、`time` 耗时、命中路由；请求天然触发懒加载初始化。

- **3.4 `inspect`（视图源码/元信息）**
  - 输入：`<endpoint>`（函数或 `module.Class.method` 字符串）。
  - 用 `application.get_handler(endpoint)` 得 `(klass, mod, handler)`；`inspect.getsourcelines`/`getfile` 得 file:line；`iscoroutinefunction`/`isasyncgenfunction` 判 async；`signature`、`docstring`；按 `TEMPLATE_TEMPLATE`（default_settings 的 `('%(view_class)s/%(function)s', '%(function)s')`）推算约定默认模板路径。

- **3.5 `body`（异步解析调试）**
  - 输入：`<content-type>`、`<raw-body>`、`--method`（默认 POST）。
  - 构造最小 Starlette `Request` scope + body，依次 `await` `get_data()/get_POST()/get_FILES()/get_json()/get_params()`，打印各自返回值或解析异常，直观点破"同一 body 在不同读取方式下是什么"。

## 4. 约束与策略落地

- 只读框架内部结构、**不改变行为契约**；`request`/`body` 仅构造请求，不改 `application` 状态。
- 不新增硬依赖：`httpx`、`starlette` 均为 uliweb 既有依赖。
- 命令自动注册依赖 `uliweb.contrib.develop` 在 INSTALLED_APPS（或 `uliweb develop`），不侵入生产。
- 改动跑 `nosetests --with-doc test`（仓库根）无回归；输出格式稳定、agent 可解析。

## 5. 开放问题与结转

- **命令清单** → 待审阅：默认全 5 条；若想收敛，可砍 `body`/`urlfor`（价值略低）。
- **DEBUG 自动加 develop 的副作用（同时开 `/develop/*` 网页路由）** → 已定案：接受；debug 为开发环境，注入点是 `get_apps` 使命令与运行时都覆盖；新增 `GLOBAL.AUTO_DEVELOP`（默认 True）作独立开关，`False` 时 debug 下也不加 develop；`uliweb develop` 保留并存。
- **`route` 是否兼容 url_prefix/域名** → 待审阅：`_init_routes` 会用 `process_domains` 的 `url_prefix` 拼接出最终 `starlette_rule`，因此 `application.router.routes` 里已是拼好的最终 path，直接匹配即可；域名多前缀场景在实现时核对。
- **输出格式** → 待审阅：默认纯文本对齐 + `--json` 开关（agent 更易解析）。
- 结转：实现时确认 `httpx.ASGITransport` 对 `AsyncDispatcher` 的兼容（首请求即触发完整初始化，符合 skill `debugging.md`）。