# Intent: 将 Uliweb 从 Werkzeug/WSGI 迁移到 Starlette/ASGI

<!--
intent.md 是 AI-native SDLC 流程的起点：把想法用提出者自己的话沉淀为"人类可读、机器可执行"的原型规格。
张贴本文件到 intent 存放处（最简：产品仓库下的 intent/ 目录）并提交。
文件头部的 Frontmatter 字段会进入 git 记录，作者与时间戳自动带上。
-->

---
类型: intent
状态: draft            <!-- draft → 提交给产品负责人审阅修正 -->
创建: 2026-08-28
---

- 作者: zhangchunlin（ASGI 版本作者）
- 关联工单/事故: Uliweb3 核心改造

## 问题 （今天做不到什么 / 痛点）
- 现有 Uliweb 基于 Werkzeug 的 WSGI 架构，无法使用现代 Python 的 async/await，也无法原生支持 WebSocket，在高并发与实时通信场景下性能受限、生态陈旧。
- 现有代码库大量为同步代码，直接整体迁移会导致"大爆炸式"重写，迁移风险与停机时间不可接受。

## 期望结果 （更好的情况长什么样）
- Uliweb 成为纯 ASGI 框架：支持异步处理能力、原生 WebSocket、更高并发、更好的 Python 异步生态集成。
- 现有同步代码可通过框架层"同步适配器机制"平滑过渡，无需立即重写。
- 对外接口保持兼容：`@expose` 装饰器、`settings.ini` 配置、`process_request/process_response/process_exception` 中间件接口继续可用。
- 实现集中于 `uliweb/core/SimpleFrame.py`，并通过 Uvicorn / Hypercorn / Daphne 等 ASGI 服务器运行。

## 受影响的用户与系统
- 现有 Uliweb 项目的开发者（依赖旧同步接口与配置方式）。
- 核心组件：Request/Response、Dispatcher、URL 路由、全局状态管理、中间件、模板、事件分发、命令系统、HTML/UAML、JSON 工具、Settings 配置。
- 相关文件：`uliweb/core/SimpleFrame.py`、`uliweb/core/rules.py`、`uliweb/core/context.py`、`uliweb/utils/localproxy.py`、`uliweb/__init__.py`。

## 约束
- 不新增对旧 WSGI 的长期兼容负担；最终完全移除 werkzeug 依赖。
- 保持向后兼容：`@expose`、`settings.ini`、传统中间件接口、`url_for` 等。
- 配置加载与模板渲染继续使用现有同步机制，通过协程池异步化，不引入额外异步配置系统。
- 不在 SimpleFrame.py 之外新建独立 `starlette.py` 文件。

## 开放问题
- 同步函数在线程池中执行时的线程安全与线程池容量如何合理配置（`SYNC_THREAD_POOL_SIZE`）。
- 同步/异步混合模式下请求数据预加载的内存与性能开销如何平衡。
- 各 contrib 应用（session、auth、cache、orm 等）的异步化改造优先级与排期。
