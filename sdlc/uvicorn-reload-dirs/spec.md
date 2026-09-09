# Spec：uvicorn reload 监听目录去重（uvicorn-reload-dirs）

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
-->

---
类型: spec
来源: intent.md（approved）
状态: approved
创建: 2026-09-09
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：`run_asgi` 中 `project_dir`/`old_apps_dir` 在去重 set 之外单独加入，存在真重复隐患；`extra_files` 逐文件取父目录导致监听扇出/嵌套冗余。
- **范围取向（已定案）**：**只做字符串去重，不做最小根化**——保持现状监听粒度。
- **验收标准**：
  - 三个来源并进同一 `set`，统一 `os.path.abspath` 后去重，再统一生成 `--reload-dir`。
  - 生成的 `--reload-dir` 无**完全相同**的重复项（含与 project_dir/old_apps_dir 的重复）。
  - verbose 日志输出去重后的 `sorted(watched_dirs)`。
  - `nosetests --with-doc test`（仓库根）全绿。

## 2. 范围与边界

- 在范围内：`uliweb/manage.py` `run_asgi`（`--reload` 分支）。
- 在范围外：最小根化（祖先/兄弟折叠）；监听范围变更；`hypercorn`/`daphne` 分支。
- 关联系统：`uliweb develop` / `runserver --reload`（uvicorn）。

## 3. 设计

- **总体方案**：把 `project_dir`、`old_apps_dir`、`extra_files` 派生目录三来源并进**同一个 `watched_dirs` set**，`os.path.abspath` 规范化后字符串去重，循环一次性 `cmd.extend(['--reload-dir', d])`。

- **3.1 统一候选集**（manage.py `run_asgi`）
  - `project_dir = global_options.project or os.getcwd()`。
  - `for d in (project_dir, old_apps_dir): if d: watched_dirs.add(os.path.abspath(d))`。
  - `for f in extra_files: dir_path=os.path.dirname(f); if dir_path: watched_dirs.add(os.path.abspath(dir_path))`。
  - `for d in watched_dirs: cmd.extend(['--reload-dir', d])`。

- **3.2 verbose 日志**
  - `watched = [project_dir, old_apps_dir] + list(watched_dirs)` → 改为 `sorted(watched_dirs)`。

## 4. 约束与策略落地

- 不做最小根化；不改变监听粒度；不新增依赖；向后兼容。
- 改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- 来自 intent.md：是否最小根化 → **已定案不做**；兄弟折叠 → **结转**为未来可选特性（涉及监听范围变宽取舍）。
