# Spec: 清理本次新增测试中的不合理用例（test-cleanup）

---
类型: spec
来源: sdlc/test-cleanup/intent.md
状态: 待审阅
创建: 2026-09-13
---

## 1. 需求（需求是什么）

- **业务问题**：`test/test_image.py`、`test_auth.py`、`test_filedown.py` 存在明显不合理的
  用例写法：重复定义、过时 docstring、别扭 API、冗余断言、过宽异常断言、名不副实。
- **用户故事 / 验收标准**：
  - Given `test_image.py`，When 审阅，Then 每个测试方法只定义一次（删除重复的
    `test_test_image_suffix`/`test_test_image_strong`）。
  - Given `test_auth.py`，When 审阅，Then docstring 与实际覆盖一致（说明已测 md5=True）；
    `__import__('hashlib')` 改为 `import hashlib`；删除冗余的
    `test_encrypt_md5_false_prefix_sha1`（已被 `test_encrypt_check_roundtrip` 覆盖）。
  - Given `test_filedown.py`，When 审阅，Then `assertRaises(Exception)` 改为匹配
    `"can't be empty"` 消息；`test_iterator_equality_of_content` 改名为
    `test_empty_range`。
  - `nosetests --with-doc test` 全绿（OK）；清理后用例总数不高于清理前（删除重复定义
    后应下降）。
- **非目标**：不改 `uliweb/` 生产代码、不改测试意图与覆盖范围、不改其余测试文件。

## 2. 范围与边界

- **在范围内**：`test/test_image.py`、`test/test_auth.py`、`test/test_filedown.py` 三文件的
  上述 6 项清理；`sdlc/test-cleanup/` 文档链。
- **在范围外**：其他测试文件；生产代码；测试框架本身（nose 收集等）。

## 3. 设计

- **3.1 `test_image.py` 去重**：删除 L108-122 处的第二份 `test_test_image_suffix`/
  `test_test_image_strong`（保留 L60-74 第一份；或反之，保留靠前更符合阅读习惯）。
  注意保留 `test_thumbnail_*`、`test_resize_*` 等其余用例。
- **3.2 `test_auth.py` docstring**：L8-10 更新为"md5=True 走 md5 算法、md5=False 走 sha1，
  均测往返"。
- **3.3 `test_auth.py` hashlib**：L38/L43 的 `__import__('hashlib')` 改为模块顶部
  `import hashlib`，正文直接 `hashlib.sha1(...)`/`hashlib.md5(...)`。
- **3.4 `test_auth.py` 去冗余**：删除 `test_encrypt_md5_false_prefix_sha1`（前缀断言已被
  `test_encrypt_check_roundtrip` 覆盖）。
- **3.5 `test_filedown.py` 具体异常**：`test_xsendfile_requires_headers` 的
  `assertRaises(Exception)` 改为 `assertRaisesRegex(Exception, "can't be empty", ...)`。
- **3.6 `test_filedown.py` 改名**：`test_iterator_equality_of_content` → `test_empty_range`。

## 4. 约束与策略落地

- 仅测试代码改动；不改生产行为。
- 每处清理不影响其余测试意图；跑全量确认全绿。

## 5. 开放问题与结转

- 无。