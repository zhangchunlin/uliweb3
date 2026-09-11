# Plan：NullPool 惰性 Result 跨查询诊断（nullpool-lazy-result-diagnostics）

---
类型: plan
来源: spec.md（approved）
状态: 待执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. feat(orm)：`Result` 加 `_consumed` 标志 + 惰性跨查询警告**
      `Result.__init__`（~L2649）置 `_consumed=False`；`__iter__`（~L2991）迭代到末尾（无更多行）时置 `True`；在发起新查询/`filter()`（~L2789）/`connect` 入口，若本 `Result` 已运行但 `_consumed` 仍为 False，打 debug/警告级日志：`A lazy Result on connection X is still open while a new query started; materialize with list() first.`
      简单保守非破坏性（spec §5 定案）：纯日志、不改惰性语义、不做复杂状态机。
      验证：复现场景（惰性迭代未耗尽又开新查询）断言该日志出现；迭代到末尾后不再误报；`nosetests` 全绿。

- [ ] **2. feat(orm)：新增 `Result.list()` 方法（spec §5 定案）**
      `.list()`：立即物化并返回真 list（内部迭代到耗尽并置 `_consumed=True`），文档标注 `all()` 是惰性（返回 self）。
      验证：`.list()` 返回真 list 且 `_consumed` 置位；与 `all()` 语义对照用例；`nosetests` 全绿。

- [ ] **3. feat(orm)：连接/会话层 acquire/release/close 调用栈（debug，可选项）**
      在 `get_session`（~L558）/连接关闭处，debug 级记录调用栈；关闭时如有活动游标打高优先级日志。若实现成本偏高或影响性能，收敛为 debug 开关（spec §5 结转）。
      验证：debug 下连接生命周期栈可见；默认不影响性能；`nosetests` 全绿。

- [ ] **4. tests：真库 + async 复现**
      用真 SQLite（NullPool + async）覆盖"惰性未迭代完又开新查询 → 警告"与"`.list()` 物化"。
      验证：新增用例在 `nosetests --with-doc test` 全绿。

- [ ] **5. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；改动落位。

## 验证命令
- `nosetests --with-doc test`（仓库根）

## 风险与缓解
- **最可能弄坏**：`_consumed` 标志在 `Result` 复用/连接共享时误判 → 缓解：只在"本 Result 已运行且未耗尽"时警告，纯日志不改变行为；迭代到末尾即清除误报。
- **最冒险一步**：第 1/2 步动 `Result` 核心 → 缓解：改动最小（标志 + 日志 + 新增方法），`all()` 行为不变；真库用例兜底。
- **放弃的做法**：不改惰性 `Result`/连接语义、不拖性能主线（spec §1）；`__del__` 关闭行为保持不变。
