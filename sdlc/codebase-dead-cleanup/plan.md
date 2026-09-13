# Plan：清理 uliweb3 代码库的死代码与结构残留（codebase-dead-cleanup）

---
类型: plan
来源: spec.md（待审阅）
状态: 待执行
创建: 2026-09-13
审批: （待 spec approved 后执行）
---

## 改动的文件
- `uliweb/lib/colorama/`（删除整目录；保留 `__init__.py` 与 `weto/`）。
- `uliweb/core/SimpleFrame.py`（删除 `_merge_rules()` L306-333 + 别名 L275-277）。
- `uliweb/__init__.py`（删除 `_merge_rules,` 导出，L63）。
- `uliweb/manage.py`（删除冗余 sys.path 段 L51-53）。
- `.gitignore`（补 `profile/`、`profile_test/`）。
- `profile/`、`profile_test/`（删除现存空目录）。
- `sdlc/codebase-dead-cleanup/`（本目录文档链）。

## 工作顺序

1. **删 `uliweb/lib/colorama/`**
   `git rm -r uliweb/lib/colorama`。验证：无 `uliweb.lib.colorama` import；`coloredlog.py` 对
   系统 colorama 缺失优雅降级；`nosetests --with-doc test` 全绿。

2. **删 `SimpleFrame._merge_rules()` + 别名 + 导出**
   删 L275-277 别名、L306-333 函数体；`__init__.py:63` 移除 `_merge_rules,`。
   保留 `merge_rules`（L280）与导出。
   验证：`from uliweb.core import rules` 的 `merge_rules` 调用（develop/views.py、test_*）正常；`nosetests` 全绿。

3. **删 `manage.py` 冗余 sys.path 段**
   删除 L51-53 三行（现插入不存在 `lib/lib` 的 no-op；不改成 insert workpath，避免顶层遮蔽）。
   验证：`uliweb` 命令仍可正常发现命令；`weto` 经 `uliweb.lib.weto.*` 导入不受影响；`nosetests` 全绿。

4. **删空目录 + `.gitignore` 补 profile**
   `rmdir profile profile_test`（空、未跟踪、未被使用；`test_profile.py` 只 patch 常量断言 path，
   实际写入在 tmpdir）。追加 `profile/`、`profile_test/` 到 `.gitignore`。
   验证：`git status` 不再显示这两个目录；`nosetests` 全绿。

5. **终检**
   仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 干净；`uliweb help` 正常；每个改动独立提交。

## 风险与缓解
- **最可能弄坏**：误删对用户/动态加载有用的工具 → 缓解：只删确认无引用的死代码
  （`colorama/` vendored 无 import、`_merge_rules` 纯死代码、`manage.py` no-op 段）；
  `whocallme/timeit/timesince/process/test_server/escape/xlt` **明确保留**。
- **最冒险一步**：删 `_merge_rules` 及别名时漏了某处对别名的引用 → 缓解：已确认别名仅 `_merge_rules`
  使用；删后跑全量 `nosetests` + `develop/views.py` 的 `merge_rules` 冒烟。
- **`manage.py` 改动是否引入顶层遮蔽** → 缓解：不是"insert workpath"，而是**整段删除** no-op 段，
  不往 sys.path 加任何新目录；`weto` 走完整包路径 `uliweb.lib.weto.*` 不受影响。
- **`colorama/` 删除后彩色输出** → 缓解：`coloredlog.py` 对 `import colorama` 缺失优雅降级为无色，
  功能不报错；vendored 拷贝从未被 import，删除不改变任何行为。
- **放弃的做法**：不做激进重构（不拆巨型文件、不改 contrib opt-in、不动结构建议项、不删用户价值工具）。

## 证明（如何证明它工作）
- **测试**：`nosetests --with-doc test`（仓库根）全绿（OK），无回归。
- **引用扫描**：删除后 `grep -rn "lib.colorama\|_merge_rules" uliweb/ test/` 无残留引用；
  保留的 7 个 utils 工具仍可 import（`import uliweb.utils.escape`、`uliweb.utils.xlt`、
  `uliweb.utils.process`、`whocallme` 等）。
- **命令**：`uliweb help` 正常列出命令（删除 no-op sys.path 段后命令发现不受影响）。