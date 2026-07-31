---
name: "integrate-system"
description: "Integrates frontend, backend, database, authentication, permissions, files, asynchronous jobs, and external services into a runnable end-to-end system. Use after major layers exist or when mocks must be replaced with real flows."
---

# Integrate System — 系统联调与集成

本 Skill 负责把已实现的前端、后端和数据层连接成真实可运行链路，并消除契约漂移、环境配置错误和仅在 Mock 下可用的问题。


## 全局安装、项目隔离与执行真实性

1. 当前项目根目录是 TRAE 当前打开的目标工作区根目录；所有相对路径均从该目录解析。
2. 禁止读取或修改当前工作区之外的其他项目、TRAE 安装目录、全局 Skill 目录和 Skill 自带 `references/`。
3. Skill 自带参考文件只读；项目实际文档写入 `./output/build/`，业务代码写入当前项目既有源码目录。
4. 修改前必须检查目录结构、包管理器、框架、版本文件、环境变量示例、现有测试和 Git 工作区状态。
5. 优先扩展现有技术栈和编码约定；未经用户明确要求，不得擅自重建项目、替换框架或删除既有功能。
6. 禁止写入真实密钥、密码、Token 或生产凭据；只允许创建安全的 `.env.example` 和占位值。
7. 每次执行后必须运行当前环境可用的 lint、类型检查、测试、构建或迁移验证；未实际运行的检查不得声称通过。
8. 遇到外部服务、凭据、网络或基础设施缺失时，完成可离线完成的部分，并在报告中记录准确阻塞项，不得伪造成功。
9. 所有实现必须可追溯到 `PXX / BR-XXX / VR-XXX / PERM-XXX / SM-XXX / SXX`；映射写入 `./output/build/traceability.json`。
10. 不覆盖无关文件；对高风险变更采用增量修改、兼容迁移和可回滚方案。


## 集成范围

根据架构和需求检查：

- Web/App 到 API 的基础地址、代理、CORS、CSRF 和 Cookie/Token 策略。
- 登录、退出、续期、超时、密码策略和账号状态。
- RBAC、菜单权限、按钮权限和数据范围权限。
- 数据库迁移、字典、种子数据和开发环境初始化。
- 文件上传、预览、下载、删除和对象访问控制。
- 邮件、短信、支付、地图、对象存储等外部集成。
- 队列、定时任务、事件、WebSocket 或通知。
- 日志、追踪 ID、健康检查和错误关联。

没有需求的能力不得为了“架构完整”强行引入。

## 执行步骤

1. 读取 API 契约并比较前后端请求、响应、枚举、错误码和空值处理。
2. 替换 P0 流程中的 Mock 数据；保留 Mock 时必须仅在显式开发开关下启用。
3. 建立本地可重复启动方式，包括数据库和必要依赖。
4. 按用户角色执行主流程、异常流程和越权流程。
5. 修复跨层问题，优先修正契约源而不是在多处打补丁。
6. 为外部服务提供适配器和可替换的本地测试实现，但不伪造生产调用成功。

## 必测端到端路径

至少包括：

- 首次初始化与登录。
- 一个 P0 核心对象的创建、查询、更新和受控删除/关闭。
- 一个状态机完整流转。
- 一个权限拒绝和一个数据范围越权拒绝。
- 一个表单校验失败和服务端业务错误。
- 一个空状态、加载失败和重试。
- 如涉及文件或异步任务，至少完成一条完整链路。

## 输出

```text
output/build/
├── integration-report.md
├── environment-matrix.md
├── contract-drift.json
└── traceability.json
```

同时更新运行脚本、开发配置和端到端烟雾测试。`contract-drift.json` 中所有 P0 不一致必须修复或标记为明确阻塞。
