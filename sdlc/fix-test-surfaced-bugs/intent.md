# Intent: 修复补测试时暴露的生产缺陷（fix-test-surfaced-bugs）

---
类型: intent
状态: draft
创建: 2026-09-13
---

- 作者: zhangchunlin
- 关联工单/事故: `sdlc/test-coverage-gaps` 补测试时，为模板/图片/auth 写单元测试逐一触发以下
  生产代码缺陷。均为"测试暴露、被断言挡下"的回归盲区。

## 问题 （今天做不到什么 / 痛点）

框架几处主要功能实际是坏的，但此前 334 条测试恰好没覆盖到：

1. **`uliweb/core/template.py::_ApplyBlock.generate`（L1203-1205）**：`{{ apply X }}...{{ end }}`
   节点生成的嵌套 `def _tt_write` 内缩进错乱，**任意输入**在 `Template.__init__` 编译阶段抛
   `SyntaxError`。→ 模板 `apply` 语法完全不可用。

2. **`uliweb/utils/image.py`**：`resize_image`/`thumbnail_image`/`crop_resize` 使用
   `Image.ANTIALIAS`，该常量在 **Pillow>=10** 被移除 → 这三函数在当代 Pillow 上抛
   `AttributeError`。应改用 `Image.Resampling.LANCZOS`（Pillow>=9.1，向下兼容别名仍在）。

3. **`uliweb/contrib/auth/__init__.py::encrypt_password`（L46）**：默认 `md5=True` 分支写成
   `hashlib.md5(raw_password).hexdigest` —— 既未对 str 编码（`hashlib.md5` 需 bytes），
   又把 `.hexdigest` 当值传（漏调用）→ 抛 `TypeError`。公开 API 默认分支损坏。

## 期望结果 （更好的情况长什么样）

- `{{ apply upper }}...{{ end }}` 能正常渲染（apply 功能恢复）。
- 图片 resize/thumbnail/crop 在当代 Pillow（>=10）可用，且在旧版（<9.1）不回归。
- `encrypt_password(raw_password, md5=True)` 不再抛 TypeError，往返 `check_password` 通过。
- 三个缺陷修复后，`sdlc/test-coverage-gaps` 新增的测试里被 `skip`/注释掉的用例恢复生效，
  `nosetests --with-doc test` 全绿（OK），`SKIP` 数下降。

## 受影响的用户与系统

- 用模板 `apply` 节点渲染视图的用户。
- 用 `utils.image` 做头像/缩略图/裁剪的上传应用。
- 用 `contrib/auth` 的 `encrypt_password`/`set_password(md5=True)` 或注册/登录的应用。
- 维护者/coding agent：这三处回归从此有测试护栏。

## 约束

- 修复**行为**，不改对外签名/契约；`@expose`/`settings.ini`/`url_for` 等不动。
- 兼容 Python 3.8–3.13；图片修复须兼顾旧版 Pillow（用兼容写法，必要时版本分支）。
- 每个 bug 修复独立提交；修复须让 `sdlc/test-coverage-gaps` 里对应被跳过的用例恢复。
- 不改 `nose` 收集问题（`image.test_image` 命名，非生产缺陷，已在测试侧规避，结转）。

## 开放问题

- `encrypt_password` 的 md5 预哈希：`md5=True` 的语义是"先 md5 再 sha1"，修复时应保持该语义
  （用 `hashlib.md5(raw_password.encode()).hexdigest()`），还是直接弃用 md5 预哈希走纯 sha1？
  → 建议保持原语义，仅修正编码+调用。
- 图片：是否对 Pillow 老版本（<9.1 无 `Image.Resampling`）做兼容分支？→ 建议用
  `getattr(Image, 'Resampling', Image)` 取值，天然兼容。
- 是否把 `image.test_image` 的 nose 收集问题一并处理（改函数名/加 `__test__`）？→ 建议
  **不属本任务**，已在测试侧规避，结转。