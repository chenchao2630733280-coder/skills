---
name: "integrate-system"
description: "Integrates frontend, backend, database, authentication, permissions, files, asynchronous jobs, and external services into a runnable end-to-end system. Use after major layers exist or when mocks must be replaced with real flows."
---

# Integrate System — 系统联调与集成

本 Skill 负责把已实现的前端、后端和数据层连接成真实可运行链路，并消除契约漂移、环境配置错误和仅在 Mock 下可用的问题。


## 全局约束

遵循 `../_shared/references/engineering-constraints.md`（项目隔离/技术栈沿用/密钥/验证/追溯/增量修改等 10 条通用工程约束，唯一事实来源）。

**本 skill 特有约束**：无。


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
