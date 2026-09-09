# Plan：uvicorn reload 监听目录去重（uvicorn-reload-dirs）

<!--
plan.md 由"approved 的 spec.md"驱动生成。
备注：本变更在补齐工件链前已先行实现并提交（3c62706），本 plan 如实记录并勾选已执行步骤。
-->

---
类型: plan
来源: spec.md（approved）
状态: 已执行
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 执行顺序

- [x] **1. refactor(manage)：三来源并入同一 set 字符串去重**
      `run_asgi` 的 `--reload` 分支：`project_dir`/`old_apps_dir`/`extra_files` 目录并入同一 `watched_dirs` set，`os.path.abspath` 规范化后去重，统一生成 `--reload-dir`；不做最小根化。
      验证：`--reload-dir` 无完全相同重复；verbose 日志 `sorted(watched_dirs)`。

- [x] **2. 终检**：仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 工作区干净。

## 验证命令
- `nosetests --with-doc test`（仓库根）

## 风险与缓解
- **最可能弄坏**：误改监听粒度 → 缓解：只做字符串去重，不折叠祖先/兄弟；`abspath` 仅用于规范化精确去重。
- **放弃的做法**：最小根化/兄弟折叠（减少监听数）→ 因涉及监听范围变宽，留作未来可选特性。
