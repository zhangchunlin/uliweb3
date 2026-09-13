# Intent: 清理本次新增测试中的不合理用例（test-cleanup）

---
类型: intent
状态: draft
创建: 2026-09-13
---

- 作者: zhangchunlin
- 关联工单/事故: `sdlc/test-coverage-gaps` / `sdlc/fix-test-surfaced-bugs` 新增的测试文件。

## 问题 （今天做不到什么 / 痛点）

`test/test_image.py`、`test_auth.py`、`test_filedown.py` 里存在明显不合理的用例写法，
会误导维护者或产生虚假的通过：

1. **`test_image.py` 方法重复定义**：`test_test_image_suffix` / `test_test_image_strong`
   各定义两次（复制粘贴残留），前者是死代码（后者覆盖前者）。
2. **`test_auth.py` docstring 过时**：说"仅测 md5=False 路径"，实际已测 md5=True。
3. **`test_auth.py` 用 `__import__('hashlib')`**：别扭、与文件其余部分不一致。
4. **`test_auth.py` `test_encrypt_md5_false_prefix_sha1` 冗余**：与
   `test_encrypt_check_roundtrip` 重复断言 `sha1$` 前缀。
5. **`test_filedown.py` `assertRaises(Exception)` 过宽**：任何异常都通过，须匹配具体消息。
6. **`test_filedown.py` `test_iterator_equality_of_content` 名不副实**：实际测空 range，
   名字误导。

## 期望结果 （更好的情况长什么样）

- 每个测试只定义一次、名字与实际断言一致。
- docstring 与实际覆盖一致，无冗余重复断言。
- 异常断言具体（匹配消息）而非裸 `Exception`。
- 清理后 `nosetests --with-doc test` 全绿（OK），用例数不因重复定义而虚增。

## 受影响的用户与系统

- 维护者/coding agent：阅读与维护 `test/` 时不被误导、不被死代码干扰。
- 后续基于这些测试改生产代码的人。

## 约束

- **只改测试代码**，不动 `uliweb/` 生产代码与行为。
- 不改变测试意图与覆盖范围，只修不合理写法。
- 清理后全量测试全绿；如有重复定义导致用例数虚增，修复后用例数下降。
- 一事一提交。

## 开放问题

- 无。