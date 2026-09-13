# Plan: 修正 uliweb-asgi-webapp 技能与实际实现的偏差（skill-asgi-webapp-fix）

---
类型: plan
来源: sdlc/skill-asgi-webapp-fix/spec.md
状态: approved
创建: 2026-09-13
审批: 待评审通过
---

## 改动的文件
- `~/.opencode/skills/uliweb-asgi-webapp/SKILL.md`（修改）：3 处修正。
- `sdlc/skill-asgi-webapp-fix/`（本目录文档链）。

## 工作顺序

1. **修 Todo 示例 `new` 的 POST 读取**（SKILL.md:392-417）
   `def new(self):` → `async def new(self):`；`request.POST.get('title')` →
   `(await request.get_POST()).get('title')`。
   验证：与 `SimpleFrame.py` 的 `get_POST`（async 方法）签名一致；代码无 `request.POST`。

2. **修 Todo 示例 `delete` → `remove`**（SKILL.md:412、模板 430）
   方法 `def delete(self, id)` → `def remove(self, id)`；模板删除链接
   `/todo/delete/...` → `/todo/remove/...`；注释/正文相应同步。
   验证：方法名 `remove` 不在 `rules.HTTP_METHOD_NAMES` 内，会被 auto-register。

3. **修前置条件 Python 版本**（SKILL.md:45）
   `Python 3.7+` → `Python 3.8+`。
   验证：与 `setup.cfg:22-27`（3.8–3.13）一致。

4. **终检**：全文 grep 无 `request.POST`（Todo 里）、无 `/todo/delete`、无 `3.7`；
   `git status` 只含 SKILL.md 与 sdlc 文档；单次提交。

## 风险与缓解
- **最可能弄错**：async 视图里重定向/渲染写法 → 缓解：`url_for`/`redirect` 用法不变，
  仅新增 `await`；核对现有 async 视图约定。
- **最冒险一步**：`remove` 改名后模板 action 是否漏改 → 缓解：同步改方法名与模板链接，
  终检 grep `/todo/delete` 确保归零。
- **放弃的做法**：不采用 `delete.__auto_expose__ = True`（引入特例、与推荐用法不符）；
  不改实现。

## 证明（如何证明它工作）
- **静态核对**：SKILL.md 不再含 `request.POST`、`/todo/delete`、`Python 3.7`。
- **一致性**：与 `SimpleFrame.py:67 get_POST`、`rules.py:36 HTTP_METHOD_NAMES`、
  `setup.cfg:22` 对齐。
- **范围**：`git status` 仅 SKILL.md + sdlc 文档；工作区干净。