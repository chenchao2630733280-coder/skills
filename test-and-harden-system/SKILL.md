---
name: "test-and-harden-system"
description: "Runs and improves unit, integration, end-to-end, security, accessibility, performance, lint, type, and build checks; fixes blocking defects and produces evidence-based acceptance reports."
---

# Test and Harden System — 测试、验收与加固

本 Skill 用证据验证系统是否满足 PRD 和工程质量要求。它必须实际运行可用检查，不允许仅生成测试清单后声称系统通过。


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


## 测试策略

### 1. 建立验收矩阵

以 `PXX / BR-XXX / VR-XXX / PERM-XXX / SM-XXX` 为行，记录：

- 实现文件。
- 测试类型和测试文件。
- 自动或人工验收步骤。
- 最近执行结果。
- 未覆盖原因和风险等级。

### 2. 自动化检查

按项目能力执行：

- 格式化和 lint。
- 静态分析和类型检查。
- 单元测试。
- 数据库和服务集成测试。
- API 契约测试。
- 浏览器端到端测试。
- 生产构建。

先运行现有命令；没有脚本时才补充合理脚本。

### 3. 安全加固

检查并修复适用项：

- 认证绕过、默认允许、对象级越权和数据范围越权。
- SQL/命令/模板注入、XSS、CSRF、SSRF 和开放重定向。
- 文件上传、路径遍历和敏感文件暴露。
- 密钥提交、敏感日志、错误堆栈泄露。
- 依赖漏洞；无法联网获取最新漏洞库时明确说明限制。
- 速率限制、暴力尝试和关键操作审计。

### 4. 可用性与可访问性

- 键盘导航、焦点、语义标签、表单错误和颜色对比。
- loading、empty、error、permissionDenied 和离线/超时反馈。
- 移动端触控、视口、安全区和缩放。

### 5. 性能烟雾

- 检查明显 N+1、无限查询、大包体、重复请求和阻塞渲染。
- 对 P0 API 和页面记录基础响应或加载指标。
- 没有真实数据规模时只做烟雾基线，不虚构容量结论。

## 缺陷修复循环

1. 运行检查并保存失败证据。
2. 按阻塞、严重、一般排序。
3. 修复根因并增加回归测试。
4. 重跑受影响检查和完整阻塞门禁。
5. 外部阻塞无法解决时，给出复现步骤、影响和所需条件。

## 输出

```text
output/build/
├── acceptance-matrix.json
├── test-report.md
├── security-review.md
├── performance-smoke.md
└── release-blockers.json
```

报告必须包含实际命令、退出状态、测试数量、失败项和未运行原因。只有 `release-blockers.json` 中没有阻塞项，才可标记“可进入发布准备”。
