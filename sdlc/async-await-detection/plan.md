# Plan：async 忘 await 的显式报错（async-await-detection）

---
类型: plan
来源: spec.md（approved）
状态: 待执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序（每个 [x] 一个提交，一个目的一个提交）

- [x] **1. feat(SimpleFrame)：settings 加载处挂 debug 期 warnings 过滤**
      在 `load_settings`（~L1040）与 `load_settings_sync` 两条路径（spec §5 定案挂载点），若 `DEBUG`：`warnings.filterwarnings('always', RuntimeWarning, message='coroutine .*Request\.get_.* was never awaited')`（窄匹配，spec §5 定案）。
      双轨都要挂（async/sync）。
      验证：debug 下忘 `await request.get_params()` 时该 RuntimeWarning 可见；非 debug 不挂；`nosetests` 全绿。

- [x] **2. docs(zh_CN) + `Request.get_*` docstring/类型标注**
      在 `Request.get_params/get_POST/get_json/get_FILES`（~L66-95）docstring 标注 "async，必须 `await`"；`docs/zh_CN` 视图/请求章节补"忘 await 排查"（报错形态 + 依赖 debug 期自带警告）。
      验证：渲染审阅 docstring 与文档完整。

- [x] **3. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净；2 处改动落位。

## 验证命令
- `nosetests --with-doc test`（仓库根）

## 风险与缓解
- **最可能弄坏**：`filterwarnings` 全局副作用影响其它警告 → 缓解：仅 debug 期挂、窄匹配 `Request.get_.*`，生产不挂。
- **最冒险一步**：第 1 步动 settings 加载双轨 → 缓解：改动仅一行 filterwarnings 调用，两处成对；跑全量测试确认零回归。
- **放弃的做法**：不包代理、不做运行时"coroutine 被当 dict"拦截（spec §1/§3 定案），避免运行时包装成本与接口变更。
