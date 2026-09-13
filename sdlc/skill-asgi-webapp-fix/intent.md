# Intent: 修正 uliweb-asgi-webapp 技能与实际实现的偏差（skill-asgi-webapp-fix）

---
类型: intent
状态: draft
创建: 2026-09-13
---

- 作者: zhangchunlin
- 关联工单/事故: 审阅 `~/.opencode/skills/uliweb-asgi-webapp/SKILL.md` 与实际
  uliweb3 实现（`uliweb/core/SimpleFrame.py`、`uliweb/core/rules.py`、`setup.cfg`）对照发现。

## 问题 （今天做不到什么 / 痛点）

技能文档是指导创建 Uliweb3 ASGI 应用的依据，但三处与实际实现不符，照做会崩或 404：

1. **Todo 示例用 `request.POST`（SKILL.md:406）**：`request.POST` 现在是 `@property`，
   访问直接抛 `RuntimeError`（`SimpleFrame.py:144`）。示例同步视图 `def new(self)` 里
   `request.POST.get('title')` 一跑就炸；且与技能自身 L278-282 的"异步变更"警示自相矛盾。

2. **Todo 示例 `delete` 方法不会注册成路由（SKILL.md:412）**：`delete` 是 HTTP 动词，
   被 `rules.py` 的 `HTTP_METHOD_NAMES`（rules.py:36）L1 守卫默认跳过 auto-register，
   `/todo/delete/<id>` 路由不存在，模板删除链接 404。与技能自身 L274"HTTP 动词默认不自动暴露"
   说明矛盾。

3. **前置条件写 Python 3.7+（SKILL.md:45）**：`setup.cfg:22-27` 声明的支持范围是 3.8–3.13。

## 期望结果 （更好的情况长什么样）

- Todo 示例可运行：POST 读取用 `await request.get_POST()`（`new` 改 async）；
  `delete` 方法改名（如 `remove`）或加 `__auto_expose__ = True`，删除链接可达。
- 前置条件 Python 版本写 3.8+。
- 技能内容与实现一致，照文档写出的示例不崩、路由不漏。

## 受影响的用户与系统

- 依据该技能创建/维护 Uliweb3 ASGI 应用的人（含 coding agent）。
- 技能维护者。

## 约束

- 只改 `~/.opencode/skills/uliweb-asgi-webapp/SKILL.md` 与随附 references（如需）。
- 不引入对实现本身的改动（实现已正确，是文档过时）。
- 修正需与 `uliweb/core/*.py` 实际行为一致。
- 一事一提交。

## 开放问题

- Todo 示例的 `delete` 采用哪种修法：改名 `remove`（直观，符合推荐用法）还是
  `delete.__auto_expose__ = True`（保留 RESTful 风格）？→ 建议改名 `remove`，与技能推荐
  "类方法用约定自动暴露、避免写多余 @expose" 一致，也不引入 `__auto_expose__` 特例。
- `request.POST` 改 `await request.get_POST()` 后，`new` 是否必须 async？→ 是（get_POST 是
  async 方法，只能在 async 视图里 await；同步视图无法 await）。