# Spec: 补主要功能的测试覆盖盲区（test-coverage-gaps）

---
类型: spec
来源: sdlc/test-coverage-gaps/intent.md
状态: 待审阅
创建: 2026-09-13
---

## 1. 需求（需求是什么）

- **业务问题**：334 条测试全绿但集中在 core.rules/html/js 与 SimpleFrame integration，多个主要
  功能（模板引擎、文件/图片/下载链路、auth）零直接覆盖，回归无从察觉。
- **用户故事 / 验收标准**：
  - Given 一个含 `{{ }}`、`{% block %}`、`{% extends %}`、`{% include %}` 的模板，When 用
    `Loader`/`Template` 渲染，Then 输出正确拼接结果。
  - Given 一个图片 buffer，When 调 `resize_image`/`thumbnail_image`，Then 返回尺寸正确的缩略图
    （width/height 匹配）。
  - Given 一个上传文件流，When 调 `save_file`，Then 文件按目标路径落盘、文件名正确编码。
  - Given 一个 URL，When 走 `contrib/auth` 注册→登录→登出流程，Then 会话正确建立与销毁。
  - 新增 `test_*.py` 并入 `nosetests --with-doc test`，**全绿（OK）**，无跳过/删改失败测试。
- **非目标**：
  - 不改动被测试模块的生产代码；测试暴露出的生产 bug 单独评估、另行提交，不混入本任务。
  - 不为每个 contrib app 补全覆盖（只按优先级补部分，见开放问题）。
  - 不引入覆盖率统计基础设施（如 coverage 阈值门禁）作为本轮验收强制项。

## 2. 范围与边界

- **在范围内**（新增测试文件）：
  - `test/test_template.py`：核心目标，覆盖 `core/template.py` **常用节点子集**与 `Loader`/`Template`。
  - `test/test_uaml.py`：`core/uaml.py` 解析。
  - `test/test_files.py`、`test/test_image.py`、`test/test_filedown.py`、`test/test_storage.py`：
    上传/下载/文件/图片/容器链路。
  - `test/test_auth.py`：`contrib/auth` 全流程（注册/登录/登出/用户模型/中间件）。
- **在范围外**：
  - `utils/workers.py`、`utils/timesince.py`/`coloredlog.py`/`whocallme.py`/`escape.py`/
    `xltools.py` 等次要工具，以及 `csrf`/`secretkey`/`sequence`/`tables`/`timezone`/
    `flashmessage`/`clean`/`upload`/`recorder`/`eureka`/`rbac`/`redis_cli` 等 contrib app
    ——**结转**，本轮不补（除非评审决定扩大范围）。
  - 生产代码改动、覆盖率门禁基础设施。
- **关联系统**：测试使用 `uliweb.utils.test` 的 `TestApp`/fixture 起应用级上下文（auth）；
  模板/文件/图片用单元级直接调用。

## 3. 设计

- **总体方案**：按"一文件一测试模块、单元级为主、auth 用应用级 fixture"，全部新增 `test/` 下
  `test_*.py`，不碰生产代码。
- **组件划分**：
  - `test_template.py`：直接实例化 `Loader`/`Template`，用内存模板目录渲染，断言各节点输出；
    覆盖 `_NamedBlock`/`_ExtendsBlock`/`_IncludeBlock`/`_ControlBlock` 常见路径与
    `ParseError` 错误路径。
  - `test_files.py`：`save_file` 落盘 + `unicode_filename`/`encode_filename` 编码 +
    `str_filesize` 格式。
  - `test_image.py`：`resize_image`/`thumbnail_image`/`image_size`/`test_image`，用内存
    PIL buffer，断言尺寸。
  - `test_filedown.py`：`FileIterable`/`FileIterator` 迭代、etag 生成、断点续传（Range）。
  - `test_storage.py`：`Storage(dict)` 增删查/默认值/属性访问。
  - `test_auth.py`：用 `TestApp` 起 auth 应用，走注册/登录/登出，断言会话与重定向。
- **错误与降级**：模板/图片解析错误断言抛出对应异常；外部资源不可用时（无 PIL）跳过图片用例
  而非失败。
- **集成点**：沿用现有 `test/test_url.py`/`test_async_dispatcher.py` 的 fixture 模式与
  `uliweb.utils.test` 用法，保证被 `nosetests --with-doc test` 发现。

## 4. 约束与策略落地

- **不新增依赖**：图片测试用 PIL 若环境缺失则 `skipUnless`，不引入新包到依赖清单。
- **不动生产代码**：本任务是纯测试补全；发现的生产 bug 单独记录/评估。
- **遵循仓库测试约定**：仓库根执行 `nosetests --with-doc test`；测试风格对齐现有 `test_*.py`
  （doctest 或 `TestCase`）。
- **需在工程介入前解决的顾虑点**：
  - 图片测试依赖 PIL 是否在环境中？→ 解决：用 `skipUnless` 守卫，缺失时跳过而非失败。
  - auth 应用级测试需要起 app 上下文与数据库 → 解决：沿用 `test_orm.py` 的内存/临时
    sqlite fixture 模式。

## 5. 开放问题与结转

- 来自 intent.md（**均已拍板**）：
  - **优先级**：模板引擎 → 文件/图片/下载链路 → auth（按建议顺序）。
  - **template.py 覆盖粒度**：**常用节点子集**（`{{ }}`/`block`/`extends`/`include`/`apply`/
    `link`/`use` + `Loader` 主流程），全节点结转。
  - **contrib 范围**：本轮**仅 auth**，其余 contrib 结转。
  - **coverage 门禁**：本轮**不引入**，以"新增用例 + 全绿"为准。
- 结转：workers/timesince/coloredlog/whocallme/escape/xltools 及大量 contrib app 补测试，
  列入后续轮次。