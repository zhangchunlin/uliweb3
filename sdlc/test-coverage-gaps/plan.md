# Plan: 补主要功能的测试覆盖盲区（test-coverage-gaps）

---
类型: plan
来源: sdlc/test-coverage-gaps/spec.md
状态: approved
创建: 2026-09-13
审批: 待评审通过
---

> 前置：spec 经评审批准后按本计划执行。所有改动**只新增 test/ 下测试文件**，不碰生产代码。

## 改动的文件（全部为新增）
- `test/test_template.py`：`core/template.py` 常用节点 + `Loader`/`Template` 主流程 + 错误路径。
- `test/test_files.py`：`save_file`/`unicode_filename`/`encode_filename`/`str_filesize`。
- `test/test_image.py`：`fix_filename`/`image_size`/`test_image`；resize/thumbnail/crop 依赖
  `Image.ANTIALIAS`（Pillow>=10 移除，生产 bug），`skipUnless` 守卫。
- `test/test_filedown.py`：`FileIterable`/`FileIterator`/etag/断点续传 + `filedown`(async) 各路径。
- `test/test_storage.py`：`Storage(dict)` 容器行为。
- `test/test_auth.py`：`contrib/auth` 纯密码函数 + `User` 模型 set/check_password +
  `default_authenticate`（sqlite 内存库）。
- `test/test_uaml.py`：`core/uaml.py` 解析。
- （可选结转项，不并入本轮）`workers`/`timesince`/`coloredlog` 及大量 contrib app。

## 实际执行范围（相对 spec 的调整）
- **auth**：按 plan 风险提示收敛为"纯密码函数 + User 模型"单元测试，未做完整 HTTP
  注册/登录/登出流程（需起 app+DB+server，脆弱、风险高）；中间件/HTTP 流程结转。
- **template**：覆盖常用节点子集；`apply` 因生产 bug 无法测（已记录）。

## 工作顺序

1. **`test_template.py`（首要）**
   用内存模板目录 + `Loader`/`Template` 渲染，断言 `{{ }}`、`{% block %}`、`{% extends %}`、
   `{% include %}`、`{% apply %}`、`{% link %}`、`{% use %}` 输出；补 `ParseError` 与
   变量/过滤器/控制流路径。验证：新增用例全过，`nosetests --with-doc test` 全绿。

2. **`test_files.py` + `test_image.py` + `test_storage.py`**
   `save_file` 落盘、编码、`str_filesize`；图片用 PIL 内存 buffer 断言尺寸（PIL 缺失
   `skipUnless`）；`Storage` 字典行为。验证：全绿。

3. **`test_filedown.py`**
   `FileIterable`/`FileIterator` 迭代内容、etag 由 mtime+size 生成、Range 断点续传。
   验证：全绿。

4. **`test_auth.py`（应用级）**
   沿用 `test_orm.py` 内存 sqlite fixture + `TestApp`，走注册→登录→登出，断言会话建立/销毁
   与重定向。验证：全绿。

5. **`test_uaml.py`**
   `uaml` 常用标记解析输出。验证：全绿。

6. **终检**
   仓库根 `nosetests --with-doc test` 全绿（OK）；`git status` 只含新增 test 文件；
   若测试暴露生产 bug，单独记录、另行提交（不混入本任务）。每个测试文件独立提交。

## 风险与缓解
- **最可能弄坏**：测试写得过于宽松（只测 happy path）而漏关键断言 → 缓解：对每个节点断言
  精确输出，而非仅"不抛异常"。
- **最冒险一步**：`test_auth.py` 需要起完整 app + 数据库，fixture 若不对会连带污染其它测试 →
  缓解：严格沿用 `test_orm.py`/`test_async_dispatcher.py` 已验证的 fixture 模式，用内存 sqlite，
  测试间隔离。
- **模板节点繁多导致范围膨胀** → 缓解：只覆盖 spec 拍板的"常用节点子集"，全节点结转。
- **PIL/外部资源缺失** → 缓解：图片用例 `skipUnless` 守卫，缺失跳过而非失败。
- **放弃的做法**：本轮不引入 coverage 门禁、不改生产代码、不补全部 contrib app（结转）。

## 证明（如何证明它工作）
- **测试**：`nosetests --with-doc test`（仓库根）全绿（OK）；新增各 `test_*.py` 独立跑通。
- **覆盖**：模板常用节点、文件/图片/下载 API、auth 密码与用户模型均有显式断言（非仅 happy path）。
- **范围**：`git status` 仅新增 test 文件；生产代码零改动。

## 测试暴露的生产缺陷（未在本任务内修，另行评估）
补测试过程中发现以下生产 bug（均按约束不在此任务改生产代码）：
1. **`core/template.py::_ApplyBlock.generate`（L1203-1205）**：`{{ apply }}` 节点生成的
   `_tt_write` 内缩进错乱，对任意输入编译抛 `SyntaxError`。apply 节点实际不可用。
2. **`utils/image.py`（resize_image/thumbnail_image/crop_resize）**：使用 `Image.ANTIALIAS`，
   在 Pillow>=10 被移除 → `AttributeError`；本环境 PIL 12.2 触发，相关用例 `skipUnless` 跳过。
3. **`contrib/auth::encrypt_password`（L46）**：默认 `md5=True` 分支 `hashlib.md5(raw_password).hexdigest`
   未对 str 编码且未调用 `hexdigest()` → `TypeError`。框架内部 `create_user` 走 `set_password(md5=False)`
   不受影响；但公开 API 默认分支损坏。
4. **nose `--with-doc` 收集陷阱**：`uliweb/utils/image.py` 导出公开函数 `test_image`（名含 `test`），
   任一测试 import 该模块即被 nose 当作 doctest 收集。已在 `test_image.py` 用
   `is_image_file.__test__ = False` 规避（属测试侧 workaround，非生产 bug）。