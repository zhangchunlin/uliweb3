# Intent: 补主要功能的测试覆盖盲区（test-coverage-gaps）

---
类型: intent
状态: draft
创建: 2026-09-13
---

- 作者: zhangchunlin
- 关联工单/事故: 对 test/ 目录与 uliweb 模块结构逐包比对后，识别出多个**主要功能零 test 覆盖**。

## 问题 （今天做不到什么 / 痛点）

`nosetests --with-doc test` 334 条全绿，但**覆盖面集中在 core.rules/core.html/core.js/
SimpleFrame 的 integration 路径**，若干**主要/常用功能完全没有 test case**，回归无从察觉：

- **`uliweb/core/template.py`（1789 行）——模板引擎**：`SimpleFrame._sync_render_template`
  （`SimpleFrame.py:2905`）用它渲染视图、`orm/graph.py:115` 也用它，是**主视图渲染机制**，
  但**无 `test_template.py`**，一整套语法节点（`{{ }}`/`{% block %}`/`{% extends %}/
  `{% include %}`/`{% apply %}`/`{% link %}`/`{% use %}`、`Loader`/`Template`/`_NamedBlock`/
  `_ExtendsBlock`/`_IncludeBlock`/`_ControlBlock`）只在 integration 里被间接踩到。
- **`uliweb/core/uaml.py`——UAML 标记语言**：配置/模板的简化标记解析，无 test。
- **上传/下载/文件链路**：`utils/files.py`（`save_file`/`unicode_filename`/`str_filesize`）、
  `utils/image.py`（`resize_image`/`thumbnail_image`/`crop_resize`/`test_image`）、
  `utils/filedown.py`（`FileIterable`/etag/断点续传）、`utils/storage.py`（`Storage`）、
  `utils/workers.py`（进程管理）——均无 test。
- **`contrib/auth`**：仅 `middle_auth` 被测到，`views.py`/`forms.py`/`models.py`
  （登录/注册/登出/用户模型/命令）无 test。
- 大量 contrib app（`csrf`/`secretkey`/`sequence`/`tables`/`timezone`/`flashmessage`/`clean`/
  `upload`/`recorder`/`eureka`/`rbac`/`redis_cli`）无独立 test。
- 次要工具（`timesince`/`coloredlog`/`whocallme`/`escape`/`xltools`）无 test。

## 期望结果 （更好的情况长什么样）

- 为**核心渲染引擎 `core/template.py`**补直接单元测试，覆盖主要语法节点与 `Loader`/`Template`
  主流程——这是首要目标。
- 为**上传/下载/文件/图片链路**（`files`/`image`/`filedown`/`storage`）补测试。
- 为 **`contrib/auth` 全流程**（注册/登录/登出/用户模型/中间件）补测试。
- 新增 `test_*.py` 全部并入 `nosetests --with-doc test` 全绿（OK），不跳过/不删失败测试。
- 按"价值/回归易发程度"分优先级，先补最有价值与最易回归的，次级与 contrib 项结转。

## 受影响的用户与系统

- 框架使用者：依赖模板渲染、文件上传下载、auth 的应用。
- 维护者/coding agent：后续改动这些模块时有回归护栏。
- 涉及系统/模块：`uliweb/core/template.py`、`uliweb/core/uaml.py`、`uliweb/utils/{files,image,
  filedown,storage,workers}.py`、`uliweb/contrib/auth/*`、若干 contrib app。

## 约束

- 只**新增测试文件**，**不改动生产代码**（除非测试暴露出的 bug，须另行单独评估/提交）。
- 遵循既有测试风格：`test/` 下用 doctest 或 `TestCase`，能被 `nosetests --with-doc test`
  （仓库根）发现；必要时用 `uliweb.utils.test` 的 `TestApp`/fixture 起应用级测试。
- 不引入新依赖；图片/上传测试用临时文件/内存 buffer，不依赖真实外部资源。
- 不激进重构被测试模块；不重命名对外契约。

## 开放问题

- 优先级排序：是否把 `contrib/auth` 全流程排在文件链路之前？还是模板引擎优先、其余结转？
- `core/template.py` 语法节点繁多，本轮覆盖到哪个粒度（全部节点 vs 常用节点子集）？
- `contrib` 大量应用是否本轮都补，还是仅补 `auth`、其余结转？需拍板范围。
- 是否引入覆盖率统计（如 `coverage`）作为验收依据，还是以"新增用例数 + 全绿"为准？