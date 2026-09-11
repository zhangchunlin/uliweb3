# Intent: 为 uliweb 开发/调试增加面向 coding agent 的命令行工具（develop-debug-cli）

---
类型: intent
状态: draft
创建: 2026-09-11
---

- 作者: zhangchunlin
- 关联工单/事故: 面向 coding agent 的 uliweb 开发体验评审（承接 core-agent-friction 的运行期可诊断性增强）

## 问题 （今天做不到什么 / 痛点）

面向 coding agent 开发/调试 uliweb 应用时，以下环节缺乏好用的命令行入口，导致 agent 靠"黑盒试错"或人肉比对：

- **懒加载让"窥探"难**：`import asgi_handler` / `get_application()` 不会真正完成初始化（settings/路由/模型在**第一次真实 ASGI 请求**时才就绪）。想查"生效的路由、settings 值"要绕道触发一次请求。现有 `appsinfo`/`urls`/`settings`/`middlewares` 只覆盖部分。
- **404 排查全靠猜**：有 `uliweb urls` 列出路由，但没有"**给定 URL，它命中哪个 endpoint/视图、为什么 404**"的匹配命令。
- **请求/响应边界是 bug 高发区**（见 skill `debugging.md`），但没有命令能**不开服务器、进程内发真实请求**拿到完整 status/headers/body/命中路由。
- **异步 body 读取极易踩坑**：`request.POST`/`.json`/`.data` 已废弃，须 `await request.get_POST()/get_json()/get_params()`；agent 常写错，且无法直观看到同一 raw body 解析出来到底是什么。
- **视图定位/反查不便**：有 endpoint 名，但没有反向 `url_for(endpoint)`，也没有"从 endpoint 跳到源码位置 + 是否 async + 默认模板"的查看工具。

## 期望结果 （更好的情况长什么样）

- 有若干条 `uliweb` 子命令，让 agent 能在**不开服务器、不写临时脚本**的情况下完成常见调试：
  - 给定 URL+method → 命中哪个 endpoint/视图（file:line）/URL 参数/allowed methods；未命中时给出最接近的 path 模式（404 排查）。
  - 给定 endpoint 名 → 反向生成 URL。
  - 进程内发真实请求（`httpx.ASGITransport`）→ 打印 status/headers/body/耗时/命中路由，顺带触发懒加载。
  - 给定 endpoint → 源码位置、async 与否、签名、docstring、默认模板路径。
  - 给定 raw body + content-type → 展示 `get_POST()/get_json()/get_params()/get_data()/get_FILES()` 各自返回值。
- 命令自动注册、可离线运行、输出为 agent 易解析的稳定格式。
- 改动完成后同步更新文档：`skills/uliweb-asgi-webapp`（调试相关 reference）与 `docs/zh_CN`（命令清单、`uliweb.contrib.develop` 条目）的合适位置，让 agent/开发者可查。

## 受影响的用户与系统

- 未来所有参与 uliweb 应用开发/调试的 coding agent 与人类开发者。
- 相关文件：`uliweb/contrib/develop/commands.py`（新增命令）、`uliweb/core/SimpleFrame.py`（只读复用 `get_handler`/路由匹配/`url_for` + `get_apps` DEBUG 注入）、`uliweb/core/default_settings.ini`（`AUTO_DEVELOP`）、`skills/uliweb-asgi-webapp/`（调试 reference）、`docs/zh_CN/`（命令清单、builtin_apps）、`sdlc/develop-debug-cli/`（本文档链）、可选 `AGENTS.md` 补命令清单。

## 约束

- **不改** `uliweb/core` 的分发/路由/懒加载行为；命令只**读**框架内部结构，不改变行为契约。
- 命令仅在 `uliweb.contrib.develop` 被安装时自动注册，不侵入生产路径。
- 不 reintroduce werkzeug；不新增硬依赖（`httpx`/`starlette` 已是 uliweb 依赖，仅此可用）。
- 命令都复用现有 `Command`/`get_application`/`make_option` 模式；需初始化用 `self.get_application()`。
- 改动跑通 `nosetests --with-doc test`（仓库根）无回归。

## 自动启用 develop（DEBUG 判定）

- 因为手工往 `INSTALLED_APPS` 加 `uliweb.contrib.develop` 要改 settings.ini 较麻烦，改为：**当 `GLOBAL.DEBUG` 为真时，自动把 `uliweb.contrib.develop` 加入已安装应用**（与 `uliweb develop` 用 `include_apps` 注入的机制同构）。生产环境 DEBUG 默认关（`default_settings.ini` `DEBUG = False`），不受影响。
- **独立开关 `GLOBAL.AUTO_DEVELOP`（bool，默认 `True`）**：只有 `DEBUG` 且 `AUTO_DEVELOP` 都为真时才自动加；用户在 debug 下不想引入 develop app 时设 `AUTO_DEVELOP = False` 即可关闭。
- 注入点必须放在**模块级 `get_apps()`**（`SimpleFrame.py:813`）而非仅运行时，否则命令发现（`manage.py collect_commands` → `get_apps`）看不到 develop 的 `commands.py`（chicken-egg）。
- 副作用：debug 下不仅启用命令，也会注册 develop 的 `/develop/*` 网页路由——开发环境可接受，列入 spec 范围。

## 开放问题

- 命令清单是否收敛为上面 5 条，还是砍掉其中 `body`/`urlfor`（价值略低、实现略重）。
- `route` 匹配的实现：用 Starlette `Route.matches(scope)`（复用框架真实匹配）是否足够，还是需要兼容 `url_prefix`/域名（`process_domains`）后的路径。
- 输出格式：纯文本对齐还是加一个 `--json` 开关（agent 更易解析）。
- **DEBUG 自动加 develop 是否接受其副作用（同时开 `/develop/*` 网页路由）** → 默认接受，spec 阶段定案。