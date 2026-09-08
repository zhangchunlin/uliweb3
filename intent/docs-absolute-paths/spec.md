# Spec：清理文档中的机器专属绝对路径

<!--
spec.md 由"接受了的 intent.md"驱动生成。产品负责人审阅、就地解决顾虑点并签字后，把它与 intent.md 一并提交。
本文件同时作为"需求"与"设计"，取代传统两阶段分离。
-->

---
类型: spec
来源: intent.md
状态: approved        <!-- 审阅通过后 → approved，触发 Stage 3 plan mode -->
创建: 2026-09-08
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：通用文档里的机器/作者专属绝对路径（如 `~/project/asgi_knowbot/.venv/src/uliweb3/test`、`/Users/limodou/...`、`/home/uliweb/...`）导致文档在非作者机器上不可移植，照做即失效。
- **验收标准**：
  - 给定一个全新克隆的仓库，读者按 `test/README.md` 的命令可在任意路径执行测试，不再出现 `~/project/asgi_knowbot/...` 这类硬编码路径。
  - 给定 `docs/zh_CN/06_commands/manage_guide.md`、`docs/zh_CN/05_builtin_apps/app/recorder.md`、`docs/zh_CN/09_articles/articles/nginx_cfg.md`，其中的机器专属路径已替换为相对路径或通用占位符。
- **非目标**（明确不做，防范围蔓延）：不改任何代码/测试行为；不改 `intent/asgi-migration/` 工件链语义；不处理系统级路径（`/etc`）与通用临时文件占位（`/tmp`）。

## 2. 范围与边界

- 在范围内：上面 4 个文件的绝对路径清理。
- 在范围外：`skills/` 下文档（本次不动）、`svg_mimetype_config.md` 的系统路径、`asgi-migration` 工件链。
- 关联系统：`docs/`、`test/README.md`；如需统一占位约定，可能同步更新 `AGENTS.md`。

## 3. 设计

- **总体方案**：把机器专属绝对路径统一替换为**相对路径**或**通用占位符**，保留原文档结构与示例意图。
- **替换约定**（统一采用，避免风格分裂）：
  - 仓库内操作路径 → 相对路径（如 `test/README.md` 的 `cd` 改为 `cd test`，相对仓库根）。
  - 需要显式体现"项目根"时 → `${PROJECT_ROOT}` 占位。
  - 作者机器示例路径（`/Users/limodou/...`、`/home/xxx/...`）→ 若为示意，用 `<...>` 或 `xxx` 占位；若整段是演示输出，保留语义但去掉作者名。
- **逐文件方案**：
  - `test/README.md`：L15、L25 `cd ~/project/asgi_knowbot/.venv/src/uliweb3/test` → 相对仓库根的 `cd test`。
  - `manage_guide.md`：L306-408 的 `/Users/limodou/...` → 去掉作者名，改为通用占位路径（保持作为示例的语义）。
  - `recorder.md`：L116 `/home/uliweb/project/blog` → 通用项目根占位。
  - `nginx_cfg.md`：L16、L20 `/home/xxx/xxx/...` → 已是 `xxx` 占位，仅确认风格统一即可。

## 4. 约束与策略落地

- 只改文档，不改代码/测试行为。
- 不碰 `intent/asgi-migration/` 已有工件。
- 顾虑点：占位风格需统一 → 已定案：相对路径优先，其次 `${PROJECT_ROOT}`，示意示例用 `<...>`/`xxx`。

## 5. 开放问题与结转

- 来自 intent.md 的开放问题（占位风格约定）：本轮已定案（见 §3 替换约定）；是否把该约定写入 `AGENTS.md` 结转至实现阶段一并处理。
