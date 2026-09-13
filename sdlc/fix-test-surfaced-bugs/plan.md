# Plan: 修复补测试时暴露的生产缺陷（fix-test-surfaced-bugs）

---
类型: plan
来源: sdlc/fix-test-surfaced-bugs/spec.md
状态: approved
创建: 2026-09-13
审批: 待评审通过
---

## 改动的文件
- `uliweb/core/template.py`（修改）：`_ApplyBlock.generate` 缩进修复。
- `uliweb/utils/image.py`（修改）：`Image.ANTIALIAS` → 兼容 `RESAMPLE` 常量。
- `uliweb/contrib/auth/__init__.py`（修改）：`encrypt_password` md5 分支编码+调用修正。
- `test/test_template.py`（修改）：恢复 `test_apply`（含 apply 失败路径）。
- `test/test_image.py`（修改）：去掉 resize/thumbnail/crop 的 `skipUnless(HAVE_ANTIALIAS)` 守卫，
  恢复 4 个用例。
- `sdlc/fix-test-surfaced-bugs/`（本目录文档链）。

## 工作顺序

1. **修 `template.py` apply 缩进**
   重写 `_ApplyBlock.generate` 内 `_tt_write` 生成块为规范缩进（`if escape:`/`else:` 各一行、
   删除多余 `_tt_append(t)`/`pass`）。
   验证：`test_template.py` 恢复 `test_apply`（`{{ apply upper }}abc{{ end }}`→`ABC`）+ 补
   `apply` 带变量体；`nosetests --with-doc test` 全绿。

2. **修 `image.py` ANTIALIAS**
   模块级 `RESAMPLE = getattr(Image, 'Resampling', Image).LANCZOS`；`resize_image`/
   `thumbnail_image`/`crop_resize` 用 `RESAMPLE` 替换 `Image.ANTIALIAS`。
   验证：`test_image.py` 去掉 4 个 `skipUnless` 守卫后全绿；`nosetests` 全绿、SKIP 下降。

3. **修 `auth.encrypt_password` md5 分支**
   `md5=True` 改为 `algo='md5'` + `get_hexdigest('md5', salt, raw_password)`（原"先 md5 再 sha1"
   无法被 `check_password` 验证，见 spec §3.3 定案）；`md5=False` 维持 `sha1`。
   验证：`test_auth.py` 补 `md5=True` 往返用例（前缀 `md5$`）；`nosetests` 全绿。

4. **终检**
   `nosetests --with-doc test` 全绿（OK），`SKIP` 数从 4 降到 ≤1；`git status` 只含上述文件；
   每个 bug 独立提交。

## 风险与缓解
- **最可能弄坏**：apply 缩进重写引入新的缩进错误 → 缓解：以 `test_apply`（普通体+变量体）做
  编译与渲染双重断言；参照 `_ControlBlock`/`_ApplyBlock` 既有 indent 用法。
- **最冒险一步**：Pillow 兼容取值在老版不可用 → 缓解：`getattr(Image,'Resampling',Image)` 老版回落
  到 `Image.LANCZOS`（Pillow>=7 存在），且用 `skipUnless(HAVE_PIL)` 兜底环境无 PIL。
- **md5 语义改变**：担心 `md5=True` 从"预 md5"改成别的 → 缓解：仅加 `.encode()` 与 `()`
  调用，不改"先 md5 再 sha1"语义；用 `check_password` 往返验证。
- **放弃的做法**：不重写 apply 解析/不引入 Pillow 版本分支 if/else（用兼容取值即可）、
  不处理 `image.test_image` 命名（结转）。

## 证明（如何证明它工作）
- **测试**：`nosetests --with-doc test`（仓库根）全绿（OK）；`SKIP` 数从 4 降至 ≤1。
- **行为**：
  - `{{ apply upper }}abc{{ end }}` → `ABC`。
  - `resize_image`/`thumbnail_image`/`crop_resize` 在 PIL 12.2 下正常（4 个用例恢复）。
  - `encrypt_password(pw, md5=True)` 往返 `check_password` 为 True。
- **范围**：`git status` 仅上述 5 个改动文件；工作区干净。