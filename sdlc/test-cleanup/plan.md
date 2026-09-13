# Plan: 清理本次新增测试中的不合理用例（test-cleanup）

---
类型: plan
来源: sdlc/test-cleanup/spec.md
状态: approved
创建: 2026-09-13
审批: 待评审通过
---

## 改动的文件
- `test/test_image.py`（修改）：删重复的 `test_test_image_suffix`/`test_test_image_strong`。
- `test/test_auth.py`（修改）：docstring 更新、`import hashlib`、删冗余前缀测试。
- `test/test_filedown.py`（修改）：`assertRaisesRegex`、改名 `test_empty_range`。
- `sdlc/test-cleanup/`（本目录文档链）。

## 工作顺序

1. **`test_image.py` 去重**：删除第二份 `test_test_image_suffix`（L108）与
   `test_test_image_strong`（L113）及其空行，保留靠前的一份；确认 `test_thumbnail_*`/
   `test_resize_*` 完好。
   验证：`nosetests --with-doc test/test_image.py` 全绿。

2. **`test_auth.py` 三处**：
   - docstring L8-10 改为说明 md5=True/md5=False 均测往返。
   - L38/L43 的 `__import__('hashlib')` → 顶部 `import hashlib`，正文用 `hashlib.xxx`。
   - 删 `test_encrypt_md5_false_prefix_sha1`。
   验证：`nosetests --with-doc test/test_auth.py` 全绿。

3. **`test_filedown.py` 两处**：
   - `test_xsendfile_requires_headers` 的 `assertRaises(Exception)` →
     `assertRaisesRegex(Exception, "can't be empty", asyncio.run(...))`。
   - `test_iterator_equality_of_content` → `test_empty_range`。
   验证：`nosetests --with-doc test/test_filedown.py` 全绿。

4. **终检**：`nosetests --with-doc test` 全绿（OK）；用例总数 ≤ 清理前（去重后下降）；
   `git status` 只含上述文件；单次提交。

## 风险与缓解
- **最可能弄坏**：去重时误删非重复用例（如 thumbnail/resize）→ 缓解：按 spec §3.1 精确
  定位 L108-122，改后跑 `test_image.py` 全量核对。
- **最冒险一步**：改名/去冗余是否改变覆盖 → 缓解：去冗余前确认前缀断言已在
  `test_encrypt_check_roundtrip` 内；改名不改逻辑。
- **放弃的做法**：不重构测试框架；不引入新依赖；不触碰生产代码。

## 证明（如何证明它工作）
- **测试**：`nosetests --with-doc test`（仓库根）全绿（OK）。
- **数量**：修复后总用例数比修复前下降（去重掉 2 个虚增，去冗余掉 1 个）。
- **范围**：`git status` 仅 3 个测试文件 + 本目录文档；工作区干净。