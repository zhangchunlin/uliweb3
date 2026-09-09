# Intent: uvicorn reload 监听目录去重（uvicorn-reload-dirs）

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 sdlc/ 目录）并提交。
-->

---
类型: intent
状态: approved
创建: 2026-09-09
---

- 作者: zhangchunlin
- 关联工单/事故: `uliweb develop`（uvicorn --reload）监听目录输出膨胀

## 问题 （今天做不到什么 / 痛点）

- `uliweb/manage.py` 的 `run_asgi` 为 uvicorn `--reload` 拼 `--reload-dir`：`project_dir`、`old_apps_dir` 在 `watched_dirs` **set 之外**单独 `cmd.extend` 加入（不参与去重），存在"某文件父目录恰好等于 project_dir/old_apps_dir 时真重复"的隐患。
- `extra_files` 派生目录逐文件取 `os.path.dirname` 加入，导致监听目录**扇出/嵌套冗余**（如 app 内子包目录被其父目录覆盖仍被单独监听）。

## 期望结果 （更好的情况长什么样）

- 三个来源（project_dir / old_apps_dir / extra_files 目录）**并进同一集合**做字符串去重后统一生成 `--reload-dir`。
- 消除 project_dir 在 set 之外的"真重复"隐患。
- **不做最小根化**：不折叠祖先/兄弟目录（保留现状的监听粒度，仅去完全相同项）。

## 受影响的用户与系统

- 使用 `uliweb develop` / `uliweb runserver --reload`（uvicorn）的开发者。
- 相关文件：`uliweb/manage.py`（`run_asgi` ~L876-940）。

## 约束

- 不做最小根化（不折叠祖先/兄弟）；保持现状监听粒度。
- 不改变除"去重"外的行为；不新增依赖。
- `nosetests --with-doc test`（仓库根）全绿。

## 开放问题

- **是否做最小根化/兄弟折叠** → **已定案：本意图不做**；"折叠到共同祖先以大幅减少监听数"留作未来可选特性（涉及监听范围变宽取舍）。
