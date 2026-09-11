# Spec：惰性模型初始化报错诊断（orm-lazy-init-diagnostics）

---
类型: spec
来源: intent.md（draft）
状态: approved
创建: 2026-09-09
审批: zhangchunlin（product owner，spec approved）
---

## 1. 需求（需求是什么）

- **业务问题**（复述并收紧自 intent.md）：ASGI 入口懒加载，初始化前访问 `User.c`/`filter()` 得到误导性 `AttributeError`；`settings` 各 section 初始化前读到 `None`/空，易误判配置没合并。
- **范围取向**：只增强报错/诊断，不改懒加载行为本身。
- **验收标准**：
  - Given engine 未绑定，When 访问未绑定 `Model` 的 `c`/`filter()`/`table`，Then 抛带指引异常（含"Initialize the app first (send a real request or call prepare())"）。
  - Given engine 未绑定，When `get_model()` 取模型，Then 给出诊断信息（非裸异常）。
  - Given settings 未初始化，When 访问未加载 section 属性，Then 给可开关警告（默认 debug 级）。
  - 文档补"懒加载时序"一节。
  - `nosetests --with-doc test` 全绿。

- **非目标**：不改变懒加载时序/模型绑定时机；不改变 settings 加载机制。

## 2. 范围与边界

- 在范围内：`uliweb/orm/__init__.py`（未绑定模型入口检测、`get_model` 诊断）；settings 惰性访问提示（`uliweb/core/SimpleFrame.py` `__global__.settings` ~L466 / LocalProxy ~L325）；`docs/zh_CN` 补懒加载时序。
- 在范围外：改变懒加载行为；settings 加载机制重构；其他 ORM 诊断。
- 关联系统：`sdlc/teardown-log-noise`、`sdlc/async-await-detection`（同为运行期可诊断性增强）。

## 3. 设计

- **总体方案**：在"未绑定/未初始化"的访问入口加显式、带指引的诊断，把误导性报错变成一句话可定位。

- **3.1 未绑定模型显式报错（`uliweb/orm/__init__.py`）**
  - 在 `Model` 上提供 `is_bound()`（检查 engine 是否注册/绑定）。
  - 在 `Model.__getattr__('c')`、`table`、`filter()` 等入口，未绑定时抛自定义 `Error`（或复用 `Error`），消息含模型名 + "not bound to an engine; Initialize the app first (send a real request or call prepare())."

- **3.2 `get_model()` 诊断（~L1135）**
  - 当取到的 model 未绑定/engine 为 None 时，从裸 `AttributeError` 改为带上下文诊断。

- **3.3 settings 未初始化访问提示**
  - 在 settings 惰性代理访问未加载 section 属性处，检测到"未初始化"时打 `logger.debug`（可开关，默认 debug，不默认 warning 以免误报）。

- **3.4 文档**：`docs/zh_CN` 补"懒加载时序"一节，明确首请求/`prepare()` 前访问模型与 settings 的行为边界。

## 4. 约束与策略落地

- 只增强报错/诊断，行为零变更；向后兼容。
- settings 提示可开关（settings 项），避免误报。
- 改动跑 `nosetests --with-doc test` 无回归。

## 5. 开放问题与结转

- **未绑定检测覆盖哪些入口** → **已定案：只覆盖常用几个**（`table` / `c` / `filter`），其它入口（`properties` 等）不逐一加检查。
- **settings 提示开关项名** → **已定案：`[GLOBAL] LAZY_INIT_WARN`**（bool，默认开、仅在 debug 生效）。
- 结转：`get_model` 的多 engine/未绑定细分场景在 spec/plan 阶段核对。
