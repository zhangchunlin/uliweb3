# Plan：降低 uliweb 对 coding agent 的理解阻碍（agent-friction）

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

- [ ] **1. docs(AGENTS.md)：扩充架构地图与隐式行为规则**
      扩 `Architecture` 为模块职责地图；加"核心数据流/路由解析"短述；`Things agents get wrong` 补 `Redirect()` 抛异常、settings 惰性代理、`copy_context().run()` 桥接规则、sync/async 双轨提示。
      验证：审阅渲染后的 AGENTS.md 章节完整、无冗余。

- [ ] **2. refactor(SimpleFrame)：删 DispatcherHandler 死代码**
      先 `grep -rn 'DispatcherHandler'` 确证无引用，再删除 `class DispatcherHandler`（L870 附近）。
      验证：`grep -rn 'DispatcherHandler' --include=*.py .` 无命中；`nosetests --with-doc test` 无回归。

- [ ] **3. docs(SimpleFrame)：模块 docstring + 分节标注 + 命名澄清**
      文件顶部加模块 docstring（职责总览 + 分节索引）；各功能区前加分节 banner；`url_map`/`router`/类-代理同名处加澄清注释。只改注释。
      验证：`grep -nE '^# =====' uliweb/core/SimpleFrame.py` 列出各节；`nosetests --with-doc test` 无回归。

- [ ] **4. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；AGENTS.md 与 SimpleFrame 分节标注就位。

## 验证命令
- `nosetests --with-doc test`（仓库根，不要在 test/ 内跑）
- `grep -rn 'DispatcherHandler' --include=*.py .`（确证已删）
- `grep -nE '^# =====' uliweb/core/SimpleFrame.py`（确证分节标注）
