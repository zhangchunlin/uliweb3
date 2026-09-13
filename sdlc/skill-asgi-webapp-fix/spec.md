# Spec: 修正 uliweb-asgi-webapp 技能与实际实现的偏差（skill-asgi-webapp-fix）

---
类型: spec
来源: sdlc/skill-asgi-webapp-fix/intent.md
状态: 待审阅
创建: 2026-09-13
---

## 1. 需求（需求是什么）

- **业务问题**：技能 Todo 示例 `request.POST` 会抛 `RuntimeError`、`delete` 方法路由不会
  注册导致删除链接 404；前置条件 Python 版本标注与实际不符。
- **用户故事 / 验收标准**：
  - Given 技能 Todo 示例，When 照抄运行，Then POST 读取用 `await request.get_POST()`，
    不再抛 `RuntimeError`。
  - Given 技能 Todo 示例，When 照抄运行，Then 删除方法可注册成路由（改名 `remove`），
    `/todo/remove/<id>` 删除链接可达、不 404。
  - Given 技能前置条件，When 阅读，Then Python 版本写 3.8+。
  - 技能文档与 `uliweb/core/*.py` 实际行为一致。
- **非目标**：不改动 uliweb 实现（实现已正确）；不重写技能其余内容。

## 2. 范围与边界

- **在范围内**：`~/.opencode/skills/uliweb-asgi-webapp/SKILL.md` 的 3 处修正；若引用
  references 也含相同错误则一并修；`sdlc/skill-asgi-webapp-fix/` 文档链。
- **在范围外**：uliweb 源码；技能其他章节（核对过一致）。

## 3. 设计

- **3.1 Todo 示例 POST 读取**（SKILL.md:392-417）：`new` 方法改为
  `async def new(self)`，内部 `request.POST.get('title')` →
  `(await request.get_POST()).get('title')`；模板表单 action 不变。
  （注意：async 视图的渲染/重定向不变，`url_for` 用法不变。）
- **3.2 Todo 示例 `delete` → `remove`**（SKILL.md:412, 模板 430）：方法名 `delete` 改为
  `remove`，签名 `def remove(self, id)`；模板删除链接
  `/todo/delete/{{= todo.id }}` → `/todo/remove/{{= todo.id }}`。避免 HTTP 动词
  `delete` 被 auto-register L1 守卫跳过。
- **3.3 前置条件 Python 版本**（SKILL.md:45）：`Python 3.7+` → `Python 3.8+`。

## 4. 约束与策略落地

- 仅文档改动；与实现保持一致（`request.get_POST()` 为 async、`delete` 为 HTTP 动词被跳过）。
- 不改实现，故不跑 uliweb 测试；用静态核对 + 可选冒烟验证写法可用。

## 5. 开放问题与结转

- `delete` 修法已定案：改名 `remove`（见 intent 开放问题）。
- 结转：无。