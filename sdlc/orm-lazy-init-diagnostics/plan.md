# Plan：惰性模型初始化报错诊断（orm-lazy-init-diagnostics）

---
类型: plan
来源: spec.md（approved）
状态: 待执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. feat(orm)：未绑定 Model 入口显式报错**
      在 `Model`（`uliweb/orm/__init__.py:4020`）加 `is_bound()`；在常用入口 `table`/`c`/`filter()`（`Model.table` property、`Model.filter` ~L4795、metaclass 的 `table`/`c` 访问）未绑定时抛 `Error`，消息含模型名 + "not bound to an engine; Initialize the app first (send a real request or call prepare())."
      只覆盖 `table`/`c`/`filter` 三个入口（spec §5 定案），其它（`properties` 等）不加。
      验证：写用例——未绑定访问 `Model.table`/`c`/`filter()` 抛带指引异常；绑定后正常；`nosetests` 全绿。

- [ ] **2. feat(orm)：`get_model()` 未绑定诊断（~L1135）**
      `get_model` 取到未绑定/engine 为 None 的模型时，把裸 `AttributeError` 换成带上下文诊断（含指引）。
      验证：`get_model` 未绑定路径用例 + `nosetests` 全绿。

- [ ] **3. feat(SimpleFrame)：settings 惰性访问提示（`LAZY_INIT_WARN`）**
      在 settings 惰性代理访问未加载 section 处（`__global__.settings` ~L466 / LocalProxy ~L325 包装），命中时若 `settings.GLOBAL.LAZY_INIT_WARN`（bool，默认 True）且 debug，打 `logger.debug`；只提示、不改加载行为。
      验证：默认开、debug 下访问未初始化 section 有 debug 日志；关掉开关/生产不提示；`nosetests` 全绿。

- [ ] **4. docs(zh_CN)：补"懒加载时序"一节**
      说明首请求/`prepare()` 前访问模型与 settings 的行为边界，指向新诊断。
      验证：渲染审阅小节完整。

- [ ] **5. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；4 处改动落位。

## 验证命令
- `nosetests --with-doc test`（仓库根，不要在 test/ 内跑）
- 未绑定报错用例：`nosetests --with-doc test` 中新增用例

## 风险与缓解
- **最可能弄坏**：`table`/`c`/`filter` 是热路径入口，误报"未绑定"→ 缓解：只在 engine 确实未注册时触发，且用明确指引消息；用绑定后正常路径用例兜底。
- **最冒险一步**：第 3 步动 settings 惰性代理 → 缓解：只加读取判断 + debug 日志，不改变加载行为；`LAZY_INIT_WARN` 可关。
- **放弃的做法**：不逐一给 `properties` 等全部入口加检查（spec §5 已定案只覆盖常用三个）。
