# Intent: 清理 uliweb3 代码库的死代码与结构残留（codebase-dead-cleanup）

---
类型: intent
状态: draft
创建: 2026-09-13
---

- 作者: zhangchunlin
- 关联工单/事故: 面向文件结构的全面扫描（首次产出清单，待深挖确认后收敛范围）

## 问题 （今天做不到什么 / 痛点）

代码库存在一批**确定无引用/死代码**与**明显结构残留**，增加理解成本、误导 coding agent（与
`sdlc/core-agent-friction` 同源的可读性问题）：

- **`uliweb/utils/` 冗余模块**：`escape.py`（`escape` 实际来自 `utils/_compat.py`，此文件重复）、
  `xlt.py`（Excel2003 时代残留，live 孪生 `xltools.py`）。
- **`uliweb/core/SimpleFrame.py::_merge_rules()`（L306-333）**：与 `rules.py::merge_rules()`
  逐行重复且**从未被调用**，却被 `__init__.py` 导出 → 死重复代码。
- **`uliweb/lib/colorama/`（整目录）**：vendored 但从未被 import（`coloredlog.py` 用系统级
  `colorama`，对 None 优雅降级）；纯死代码。
- **`uliweb/manage.py:51-53` 冗余 sys.path**：插入不存在路径（`lib/lib`）为 no-op，且
  `weto`/`colorama` 均按完整包路径 `uliweb.lib.weto.*` 导入、不依赖它 → 整段可删。
- **根目录运行残留**：`profile/`、`profile_test/`（`asgi/profile.py` 生成）未进 `.gitignore`。

## 期望结果 （更好的情况长什么样）

- 删除确定冗余/死的文件与代码（`lib/colorama/`、`SimpleFrame._merge_rules`、`manage.py` 冗余
  sys.path 段），`nosetests --with-doc test` 全绿、无回归。
- **保留**所有对使用框架的用户有价值的工具：`whocallme.py`/`timeit.py`/`timesince.py`/
  `test_server.py`/`process.py`（其中 `process.py` 实被 `workers.py` 依赖，是活代码）；
  `escape.py`/`xlt.py`（通用/Excel 工具，用户价值，避免破坏下游 import）。
- `profile/`、`profile_test/` 加入 `.gitignore`（运行残留不再污染工作区）。
- 为结构层面的"巨型单文件/职责重叠/重复实现"给出**分级建议**（是否拆分/是否只文档化），但不激进重构。

## 受影响的用户与系统

- 所有阅读/修改 uliweb 的 coding agent 与开发者（消除误导性死文件，降低定位成本）。
- 相关文件：`uliweb/utils/*`（删）、`uliweb/lib/colorama/`（删）、`uliweb/core/SimpleFrame.py`
  （删 `_merge_rules` 及导出）、`uliweb/__init__.py`（改导出）、`uliweb/manage.py`（改路径）、
  `.gitignore`（加 profile）。

## 约束

- **不做激进重构**：不拆 SimpleFrame.py/template.py 巨型文件（只给分级建议）；不重命名对外
  契约；不 reintroduce werkzeug。
- 删除前**逐一确认 0 引用**（含动态/字符串加载，如 settings、`import_attr`、commands 注册）；
  有歧义的保留。
- 每个删除/修改一个提交；跑通 `nosetests --with-doc test`（仓库根）无回归。

## 开放问题（深挖后已定案）

- **`process.py`** → **保留（活代码）**：`uliweb/utils/workers.py:15` 用相对导入
  `from .process import pid_exists, wait_pid` 依赖它，`workers.py` 又被
  `contrib/orm/load_table_file.py` 使用。扫描漏了相对导入，误报为死。
- **`escape.py`** → **保留（用户价值）**：通用 Web 工具模块（`linkify`/`ObjectDict`/`url_escape`/
  `to_unicode`…，在 `template.py` 各有复制品）。内部无 import，但删了可能破坏下游
  `from uliweb.utils.escape import ...`。
- **`xlt.py`** → **保留（标记 legacy）**：Excel 导出工具（xlrd/xlwt 旧依赖），live 孪生
  `xltools.py`；删了可能破坏下游 `from uliweb.utils.xlt import ExcelWriter`。除非确认 xlrd/xlwt
  已弃用，否则不删。
- **`test_server.py`** → **保留（用户价值）**：用户侧测试工具（`TestServer`/`test_server()`，
  启动真实 uvicorn 测静态/上传/WebSocket），被 skill `test_server.md` 文档化。
- **`timesince.py`** → **保留**：Django 风格相对时间 + i18n + doctest，模板/展示常用。
- **`whocallme.py`** → **保留**：调试装饰器/`print_frame` 打印调用栈。
- **`timeit.py`** → **保留（弱价值）**：极简计时 contextmanager，通用小工具。
- **`setup.py`**（utils 内）→ 独立 setuptools 辅助脚本，0 import，可能外部手工调用 → **保留**，仅记录。
- **`ipython_extension.py`** → 仅 `manage.py:1207` 一行注释提及，未接线 → 低优先，**可删但需确认无人在用**。
- **`i18n/html_helper.py`** → 0 引用 → 低优先，**可删但需人工确认**。
- **`form/template_layout.py`** → 可能经 settings `FORM_LAYOUT_CLASSES` 触发 → **保留**。
- **`SimpleFrame` 别名（L275-277 `__exposes__/__no_need_exposed__/__url_names__`）** → 仅 `_merge_rules` 使用，其它处用 `rules.__xxx__` 前缀 → 随 `_merge_rules` 一起删。
- **结构层面（拆分/重复/位置）** → 只文档化、给分级建议，**不激进重构**。
- **contrib opt-in apps（eureka/sequence/rbac 等）** → 按 settings/commands 动态加载，**非死文件，排除**。