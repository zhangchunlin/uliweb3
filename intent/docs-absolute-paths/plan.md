# Plan: 清理文档中的机器专属绝对路径

<!--
plan.md 由工程师在 plan mode 里基于已批准的 spec.md 生成；审阅满意后提交。
要求：一个从没看过这段对话的工程师也能仅凭计划实现。
实现偏离计划时，在同一个提交里更新 plan.md。
-->

---
类型: plan
来源: spec.md / intent.md
状态: approved        <!-- 审阅通过后 → approved -->
创建: 2026-09-08
审批: zhangchunlin
---

## 改动的文件

- `test/README.md`（修改）：L15、L25 `cd ~/project/asgi_knowbot/.venv/src/uliweb3/test` + `../bin/...` → 改为仓库根规范命令 `nosetests --with-doc test` / `pytest test/`（因 `../bin/` 依赖 venv 位置，改用 AGENTS.md 的仓库根命令更可移植）。
- `docs/zh_CN/06_commands/manage_guide.md`（修改）：L306-408 `/Users/limodou/...` → 去作者名的通用占位路径（保持示例语义）。
- `docs/zh_CN/05_builtin_apps/app/recorder.md`（修改）：L116 `/home/uliweb/project/blog` → 通用项目根占位。
- `docs/zh_CN/09_articles/articles/nginx_cfg.md`（修改）：L16、L20 `/home/xxx/xxx/...` → 核对并统一为占位风格。
- `AGENTS.md`（可选，修改）：若统一占位约定值得固化，追加一条约定。

## 工作顺序

1. 处理 `test/README.md` 的 `cd` 路径（最直接影响使用者）。
2. 处理 `manage_guide.md` 的一大批 `/Users/limodou/...`（量最大）。
3. 处理 `recorder.md`、`nginx_cfg.md` 单点路径。
4. （可选）把占位约定写入 `AGENTS.md`。
5. 跑 `pytest test/` 确认无回归（理论上纯文档改动无影响，做冒烟确认）。

## 风险与缓解

- 最可能弄坏什么：`manage_guide.md` 里 `/Users/limodou/...` 出现在**编译后代码片段**（`_tt_...` 行号注释）中，需保持代码语义只改路径部分，不破坏片段结构 → 只替换路径串，不动其余内容。
- 哪一步最冒险：无（纯文档，风险极低）。
- 放弃了的其他做法及原因：不引入脚本批量替换（一次性手工 + 逐个审阅更可控）。

## 证明（如何证明它工作）

- **验收**：`grep -rnE '(/Users/|/home/|~/)[A-Za-z0-9_./-]' test/README.md docs/zh_CN` 不再命中作者机器专属路径（`/home/xxx` 占位除外）。
- **测试**：`pytest test/` 全绿（文档改动不应影响，作冒烟确认）。
- **审查**：逐个 diff 审阅路径替换，确认语义/示例意图不变。
