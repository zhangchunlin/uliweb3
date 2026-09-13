# Spec：清理 uliweb3 代码库的死代码与结构残留（codebase-dead-cleanup）

---
类型: spec
来源: intent.md（draft）
状态: 待审阅
创建: 2026-09-13
审批: （待 zhangchunlin review）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：代码库存在一批**确定冗余/死代码**与**路径残留**，
  增加理解成本、误导 coding agent；其中 `manage.py` 有真实路径 bug、`profile/` 运行残留污染工作区。
- **范围取向**：只删**已确认冗余/死**的文件，**保留对用户有价值的工具**；不做激进重构。
- **保留清单**（有价值/活代码，**不删**）：`whocallme.py`、`timeit.py`、`timesince.py`、
  `test_server.py`、`process.py`（活代码）、`escape.py`、`xlt.py`（通用/Excel 用户价值，
  避免破坏下游 `from uliweb.utils.escape/xlt import ...`）。
- **验收标准**：
  - 删除 `uliweb/lib/colorama/` 整目录（`__init__.py` 与 `weto/` 保留）。
  - 删除 `SimpleFrame._merge_rules()`（L306-333）+ 别名（L275-277）+ `__init__.py:63` 导出。
  - 删除 `manage.py:51-53` 冗余 sys.path 段（指向不存在 `lib/lib` 的 no-op）。
  - `.gitignore` 补 `profile/`、`profile_test/`，并删除这两个现存空目录（git 不跟踪空目录）。
  - `nosetests --with-doc test`（仓库根）全绿（OK）。

- **非目标**：不删 `whocallme/timeit/timesince/test_server/process/escape/xlt`（用户价值/活代码）；
  不拆 SimpleFrame.py/template.py 巨型文件；不重命名对外契约；不改 contrib opt-in apps；不删
  `utils/setup.py`、`form/template_layout.py`（可能外部触发）；不动 `manage.md` 位置 /
  `asgi/` 单文件包 / `get_commands` 重复 / 路由转换重复（仅文档化建议）。

## 2. 范围与边界

- 在范围内：`uliweb/lib/colorama/`（删）、`uliweb/core/SimpleFrame.py`（删 `_merge_rules`+别名）、
  `uliweb/__init__.py`（删 `_merge_rules` 导出）、`uliweb/manage.py`（删冗余 sys.path 段）、
  `.gitignore`（加 profile）。
- 在范围外：上述"非目标"项；`uliweb/utils/{whocallme,timeit,timesince,process,test_server,escape,xlt}.py`
  （全部保留）；`uliweb/lib/__init__.py`、`uliweb/lib/weto/`（在用）。
- 关联系统：`uliweb/core/SimpleFrame.py`（`merge_rules` compat shim L280 保留）、`uliweb/core/rules.py`
  （`merge_rules` 真相源）、`uliweb/__init__.py`（导出面）、`asgi/profile.py`（`PROFILE_DATA_DIR="./profile"` 来源）。

## 3. 设计

- **总体方案**：按"一删一改一提交"推进，每步跑 `nosetests` 无回归。只删确认无副作用的死代码。

- **3.1 删 `uliweb/lib/colorama/`**
  `git rm -r uliweb/lib/colorama`。`coloredlog.py` 用系统级 `import colorama`、对 None 优雅降级；
  无任何 `uliweb.lib.colorama` import。保留 `uliweb/lib/__init__.py` 与 `weto/`。

- **3.2 删 `SimpleFrame._merge_rules()`（L306-333）+ 别名（L275-277）+ 导出**
  - 删 `__exposes__ = rules.__exposes__`、`__no_need_exposed__ = rules.__no_need_exposed__`、
    `__url_names__ = rules.__url_names__`（仅 `_merge_rules` 使用，其它处用 `rules.__xxx__` 前缀）。
  - 删 `_merge_rules` 函数体。
  - `uliweb/__init__.py:63` 移除 `_merge_rules,`。
  - 保留 `merge_rules`（L280，compat shim）及其导出（L61）。

- **3.3 删 `manage.py:51-53` 冗余 sys.path**
  - 现插入 `.../lib/lib`（不存在）为 no-op；`weto`/`colorama` 均按完整包路径
    `uliweb.lib.weto.*` 导入、不依赖此。**整段删除 3 行**（不改成 insert workpath——那样会
    把 `uliweb/lib` 加进 sys.path，使 `win32`/`ansi`/`weto` 等顶层可导入，可能遮蔽系统同名包）。

- **3.4 `.gitignore` 补 `profile/`、`profile_test/`**：`asgi/profile.py` 默认 `PROFILE_DATA_DIR="./profile"`
  生成的运行残留不再污染工作区。

## 4. 约束与策略落地

- 删除前逐项确认 0 引用；有歧义（`setup.py`/`template_layout.py`）不删，仅记录。
- 每个删除/修改一个提交；`nosetests --with-doc test`（仓库根）全绿。
- 结构层面的"巨型文件/重复/位置"问题只写进 spec §5 建议，不动手。

## 5. 开放问题与结转

- **`whocallme/timeit/timesince/test_server`** → **保留**（用户价值，不删）；`process.py` 活代码保留。
- **`escape.py`/`xlt.py`** → **保留**（用户价值通用/Excel 工具；`xlt.py` 标记 legacy，xlrd/xlwt
  旧依赖，若确认弃用可后续单删）。
- **`ipython_extension.py`、`i18n/html_helper.py`** → 低优先候选，本次**不删**，结转人工确认。
- **`utils/setup.py`** → 保留（可能外部手工调用），仅记录。
- **结构建议（结转、不实现）**：`SimpleFrame.py`（3553 行）/`template.py`（1789 行）拆分、
  `get_commands` 三处重复、`add_websocket_route` 内联正则重复、`manage.md` 位置、`asgi/` 单文件包。
- **`profile/`、`profile_test/` 现存目录**：加入 .gitignore 后由使用者自行清理（或保留忽略）。