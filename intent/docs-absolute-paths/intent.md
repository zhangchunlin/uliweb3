# Intent: 清理文档中的机器专属绝对路径

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 intent/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: approved         <!-- draft → 审阅通过 → approved -->
创建: 2026-09-08
---

- 作者: zhangchunlin
- 关联工单/事故: 文档可移植性整理

## 问题 （今天做不到什么 / 痛点）
- 仓库的通用文档里散落着**机器/作者专属的绝对路径**（如 `~/project/asgi_knowbot/.venv/src/uliweb3/test`、`/Users/limodou/...`、`/home/uliweb/...`），换一台机器或另一个开发者照文档操作就会失效。
- 最典型的是 `test/README.md` 里的 `cd ~/project/asgi_knowbot/.venv/src/uliweb3/test` 这类硬编码路径。

## 期望结果 （更好的情况长什么样）
- 通用文档不再出现机器专属的绝对路径；改用**相对路径**或可移植占位符（如 `${PROJECT_ROOT}`、`<project_root>`、`xxx` 占位）。
- 读者在任意克隆位置都能照文档直接操作。

## 受影响的用户与系统
- 所有阅读项目文档的开发者（新人、跨机器协作）。
- 涉及文件：`test/README.md`、`docs/zh_CN/06_commands/manage_guide.md`、`docs/zh_CN/05_builtin_apps/app/recorder.md`、`docs/zh_CN/09_articles/articles/nginx_cfg.md`。

## 约束
- 只改文档，不改任何代码/测试行为。
- 不改 `intent/asgi-migration/` 下已有工件链的语义（除非其中也含绝对路径）。
- 系统级路径（如 `/etc`）与临时文件占位（如 `/tmp/...`）属通用写法，不在本次范围。

## 开放问题
- 具体采用哪种占位风格（相对路径 / `${PROJECT_ROOT}` / `<...>`）需要定一个统一约定，并可能写进 AGENTS.md。
