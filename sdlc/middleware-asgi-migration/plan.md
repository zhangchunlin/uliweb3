# Plan：legacy process_* 中间件逐步废弃 + ASGI 迁移 skill（middleware-asgi-migration）

<!--
plan.md 由"approved 的 spec.md"驱动生成。评审通过后逐条执行，每完成一步勾选 [x] 并提交。
-->

---
类型: plan
来源: spec.md（approved）
状态: 待执行        <!-- 执行完成 → 全绿 → 提交 → 归档到 REVIEW -->
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [ ] **1. feat(SimpleFrame)：启动期 legacy process_* 告警**
      在 `_init_middlewares` 的分类循环（~L1729-1738）里收集检测到的 legacy 中间件（`hasattr(middleware_cls, 'process_request'/'process_response'/'process_exception')`），循环结束后对每个打一次 `logger.warning`，内容点名中间件 + "removed after uliweb 3.1" + 指向 `skills/uliweb-asgi-webapp`（references/asgi.md）。
      用 `logger.warning`（非 `DeprecationWarning`、无开关）。只走启动路径，不进请求路径。
      验证：写一个带 legacy `process_*` 中间件的测试 app，断言 `_init_middlewares` 后日志出现一次该 warning、且请求期间无新增；无 legacy 时不告警。

- [ ] **2. docs(skill)：references/asgi.md 加"从 process_* 迁移到 dispatch"小节**
      给对等 `dispatch` 写法（`process_request`→pre 短路返回；`call_next` 包 try/except 接 `process_exception`；成功后接 `process_response`）；强调"实例化时机"陷阱（legacy 每请求 new vs dispatch 构建期单例，状态从 request 读不存 self）；注明框架 3.1 前自动兼容。
      验证：渲染审阅小节完整；`SKILL.md` ~L132-133 alert 补一句废弃说明并指向该小节。

- [ ] **3. docs(AGENTS.md)：记录 process_* 废弃约定**
      加一条约定：`process_*` 为 WSGI 相位模型、3.1 后废弃；新中间件一律用 `Middleware.dispatch(request, call_next)`；迁移遵守"实例化时机"规则（状态从 request 读，不存 self）。
      验证：AGENTS.md 相关章节就位、无冗余。

- [ ] **4. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；三处改动（SimpleFrame 告警 + skill + AGENTS.md）全部落位。

## 验证命令
- `nosetests --with-doc test`（仓库根，不要在 test/ 内跑）
- 针对告警的用例：`nosetests --with-doc test` 中新增的 legacy-middleware-warning 用例
- `grep -rn "process_" uliweb/contrib test 2>/dev/null | grep -v .venv`（复核内置中间件无 process_*，确认只有外部/测试用）

## 风险与缓解
- **最可能弄坏**：误把"每请求告警"引入请求路径 → 缓解：告警只放在 `_init_middlewares`（启动期同步路径），不在 `_process_middleware`/请求路径；用日志断言测试兜底。
- **最冒险一步**：第 1 步改动 SimpleFrame 初始化 → 缓解：改动最小（收集+循环后 warning），不触碰 `_process_middleware` 语义；跑全量测试确认零回归。
- **放弃的做法**：本阶段不动 `_process_middleware`/复合适配器/硬移除——3.1 后独立特性（见 spec §5 结转），避免本阶段引入行为漂移。
