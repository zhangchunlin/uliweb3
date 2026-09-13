# Spec: 修复补测试时暴露的生产缺陷（fix-test-surfaced-bugs）

---
类型: spec
来源: sdlc/fix-test-surfaced-bugs/intent.md
状态: 待审阅
创建: 2026-09-13
---

## 1. 需求（需求是什么）

- **业务问题**：模板 `apply`、图片 resize/thumbnail/crop、`encrypt_password(md5=True)` 三处
  生产代码损坏，`sdlc/test-coverage-gaps` 补测试时被断言挡下。
- **用户故事 / 验收标准**：
  - Given 模板含 `{{ apply upper }}abc{{ end }}`，When 渲染，Then 输出 `ABC`（不再 SyntaxError）。
  - Given 一个 100x80 的 PIL 图，When 调 `resize_image(buf, (50,50))`/`thumbnail_image`/
    `crop_resize`，Then 在 Pillow>=10 返回尺寸正确的结果（不再 AttributeError）。
  - Given 明文密码，When 调 `encrypt_password(pw, md5=True)`，Then 返回 `sha1$salt$hash`
    且 `check_password(pw, enc)` 为 True（不再 TypeError）。
  - `sdlc/test-coverage-gaps` 里被 `skip`/注释的对应用例恢复生效；`nosetests --with-doc test`
    全绿（OK），`SKIP` 数下降（≥3）。
- **非目标**：
  - 不处理 `image.test_image` 的 nose 收集命名问题（非生产缺陷，已在测试侧规避，结转）。
  - 不改 `apply`/图片/auth 的对外签名与行为语义（只修正坏掉的部分）。
  - 不为本次修复引入新依赖。

## 2. 范围与边界

- **在范围内**：
  - `uliweb/core/template.py`：修 `_ApplyBlock.generate`（L1203-1205）缩进。
  - `uliweb/utils/image.py`：`resize_image`/`thumbnail_image`/`crop_resize` 的
    `Image.ANTIALIAS` → 兼容取值（`Image.Resampling.LANCZOS`，旧版回落）。
  - `uliweb/contrib/auth/__init__.py`：`encrypt_password` L46 md5 分支编码+调用修正。
  - 对应恢复/新增测试用例于 `test/test_template.py`、`test/test_image.py`。
- **在范围外**：`image.test_image` 命名/nose 收集；其他 contrib app；结构重构。
- **关联系统**：`sdlc/test-coverage-gaps`（本任务的测试用例来源）、Pillow 版本兼容。

## 3. 设计

- **总体方案**：三个独立最小修复，各配测试，独立提交。修复遵循"保持语义、只修坏处"。

- **3.1 `template.py` apply 缩进**：`_ApplyBlock.generate` 生成的 `_tt_write` 内
  `if escape:` / `else:` 分支的写行缩进错乱（多余 `_tt_append(t)`+`pass` 处于错误缩进）。
  改为生成规范 Python：`if escape: _tt_append(xhtml_escape(t))` 与
  `else: _tt_append(t)` 两行各占一行、缩进正确，删去多余的 `_tt_append(t)`/`pass` 垃圾行。
  验证：`{{ apply upper }}abc{{ end }}` 渲染为 `ABC`。

- **3.2 `image.py` ANTIALIAS**：将 `Image.ANTIALIAS` 替换为兼容取值
  `getattr(Image, 'Resampling', Image).LANCZOS`（Pillow>=9.1 有 `Resampling`，老版本回落
  用 `Image.LANCZOS`/`Image.ANTIALIAS`）。统一封装模块级常量 `RESAMPLE`。
  验证：当代 Pillow 下 resize/thumbnail/crop 正常；`test_image.py` 的 4 个 skip 用例恢复。

- **3.3 `auth.encrypt_password` md5**：`md5=True` 从"先 md5 预哈希再 sha1"（无法被
  `check_password` 验证——`check_password` 不做预哈希，`algo$salt$hash` 格式也无标记可区分，
  且 `md5=True` 一直抛 TypeError、从未产出可用哈希、无存量数据）改为**直接使用 md5 算法**：
  `algo='md5'` + `get_hexdigest('md5', salt, raw_password)`；`md5=False` 维持 `sha1`。
  这样 `check_password` 按 `algo` 分支自然匹配，往返成立。
  验证：`encrypt_password(pw, md5=True)` 前缀为 `md5$`、往返 `check_password` True；
  `md5=False` 前缀 `sha1$`、往返不受影响。

- **错误与降级**：图片老版 Pillow 回落为 `Image.LANCZOS`；不引入版本异常路径。

## 4. 约束与策略落地

- **行为不变**：只修坏处，不改签名/返回结构。
- **兼容**：Python 3.8–3.13；Pillow 老新版本均可用。
- **测试护栏**：每修一处即恢复/新增对应用例，保证 `nosetests --with-doc test` 全绿、
  `SKIP` 下降。
- **需在工程介入前解决的顾虑点**：
  - md5 语义：plan 原定"先 md5 再 sha1"无法被 `check_password` 验证（`check_password` 不预哈希、
    格式无标记可区分），已定案改为 **md5=True 直接走 md5 算法**（`md5=False` 走 sha1 不变）。
    → 已定案（见 §3.3）。
  - Pillow 兼容写法 `getattr(Image,'Resampling',Image)` 是否可接受 → 已定案（能同时满足新旧版）。

## 5. 开放问题与结转

- 来自 intent.md：三个开放问题均已定案（保持 md5 语义 / 兼容回落 / 不处理 nose 命名）。
- 结转：`image.test_image` 的 nose 收集命名问题（测试侧已规避）；auth 完整 HTTP 流程测试
  （`test-coverage-gaps` 已结转）；其余 contrib app 测试补全。