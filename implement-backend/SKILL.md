---
name: "implement-backend"
description: "Implements production backend APIs, domain services, validation, authorization, auditing, integrations, and automated tests from PRD and architecture contracts. Use when generating or completing the server side of a system."
---

# Implement Backend — 后端系统实现

本 Skill 按业务垂直切片实现后端，不只生成 Controller 空壳。每个切片应包含契约、校验、权限、业务逻辑、持久化、错误处理和测试。


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


## 前置输入

- `./output/build/architecture.json`、`task-board.json`、`traceability.json`
- `./output/spec/business-rules.json`、`permissions.json`、`data-model.json`、`pages.json`
- 已实现的数据层和当前服务端代码

没有实施规划时，先完成最小规划，不得凭页面外观直接猜 API。

## 实施顺序

### 1. API 契约优先

- 在当前项目约定位置维护 OpenAPI、GraphQL Schema、RPC IDL 或等价契约。
- 每个端点定义方法、路径、权限、请求、响应、分页、排序、错误码和幂等要求。
- DTO 与数据库实体分离，禁止直接暴露敏感字段或内部结构。
- 契约字段必须能追溯到页面字段、业务规则和数据模型。

### 2. 分层实现

按现有项目架构实现：

- 路由/Controller：协议适配、认证上下文、输入解析。
- 应用/Service：用例编排、事务和权限调用。
- 领域逻辑：状态机、计算、业务不变量。
- Repository/Client：数据库和外部系统访问。

不得把全部逻辑堆进 Controller，也不得创建没有实际用途的抽象层。

### 3. 安全与权限

- 身份认证、会话或 Token 验证必须服务端执行。
- RBAC 与数据范围权限对应 `PERM-XXX`，默认拒绝未授权操作。
- 敏感字段按角色脱敏；日志中不得输出密码、Token 和完整证件号。
- 写操作包含 CSRF/CORS/重放风险评估，按实际架构处理。
- 文件上传校验 MIME、扩展名、大小、存储路径和访问权限。

### 4. 业务可靠性

- 实现 `BR-XXX / VR-XXX / SM-XXX` 对应的校验和状态转换。
- 关键写操作考虑幂等、乐观锁、重复提交和事务失败。
- 错误响应使用统一结构和稳定错误码，不向客户端泄露堆栈。
- 外部调用设置超时、重试边界、熔断或降级；重试必须保证安全。
- 审计日志记录操作人、对象、动作、结果和关联 ID。

### 5. 测试

每个垂直切片至少实现：

- 成功路径。
- 输入校验失败。
- 未登录、无权限和数据范围越权。
- 状态不允许或并发冲突。
- Repository/外部依赖失败。

优先使用当前项目已有测试框架和容器化测试数据库。

## 输出

- 后端源码、API 契约、配置示例和测试。
- `./output/build/backend-implementation-report.md`
- 更新 `./output/build/traceability.json` 和 `task-board.json`

报告必须区分：已实现并验证、已实现但未验证、外部阻塞、明确未实现。
