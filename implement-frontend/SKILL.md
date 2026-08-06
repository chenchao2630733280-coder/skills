---
name: "implement-frontend"
description: "Converts approved page specifications and HTML prototypes into a production frontend integrated with real application architecture, typed APIs, accessibility, validation, permissions, and tests."
---

# Implement Frontend — 前端系统实现

本 Skill 将页面规格和静态原型实现为生产级前端。原型只作为视觉与交互参考，不能直接复制其中的模拟数据、内联脚本或不安全实现。


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

- `./output/spec/pages.json`、`annotations.json`、`design-tokens.json`、`permissions.json`
- `./output/site/pc/`、`./output/site/mobile/` 或其他原型
- `./output/build/architecture.json` 和后端 API 契约
- 当前项目已有前端框架、组件库、路由、状态管理和测试配置

## 实施要求

### 1. 页面与路由

- 复用 `PXX` 页面 ID，建立路由、菜单、面包屑和父子跳转映射。
- 路由参数、查询参数和返回路径必须有类型和校验。
- 受保护页面实现认证与权限守卫；前端隐藏不能代替后端授权。
- 页面拆分遵循用户任务和复用边界，不生成单个超大组件。

### 2. 设计系统

- 将 `design-tokens.json` 映射到当前主题系统、CSS 变量或组件库 Token。
- PC 与移动端遵循原型中的布局差异，不简单等比缩放。
- 组件状态必须覆盖 normal、loading、empty、error、permissionDenied；表单额外覆盖 disabled、submitting、success。
- 保留 `data-page-id` 和关键 `data-spec-id`，方便验收和 E2E 定位。

### 3. 数据与 API

- 使用真实 API 契约生成或编写类型安全客户端。
- 统一处理认证续期、错误码、取消请求、重复请求和加载状态。
- 列表实现服务端分页、筛选、排序；不得只在前端过滤大型数据集。
- Mock 仅允许在明确的开发模式启用，生产构建必须关闭。
- 金额、日期、时区、枚举和脱敏规则与后端契约一致。

### 4. 表单和交互

- 实现 `VR-XXX` 前端即时校验，同时接受后端权威校验结果。
- 防止重复提交；保存中显示 Loading，失败后保留用户输入。
- 弹窗、Drawer、多步骤表单和子 Tab 保持草稿状态规则。
- 删除、发布、审批等高风险操作必须二次确认并展示影响。
- 所有交互闭环回到正确页面状态或明确跳转目标。

### 5. 可访问性和体验

- 使用语义化元素、关联 label、可见焦点、键盘操作和必要的 ARIA。
- 弹窗实现焦点锁定、Esc 和关闭后的焦点恢复。
- 点击区域、颜色对比、错误提示和移动端安全区符合设计规范。
- 不禁用浏览器缩放，不用颜色作为唯一状态表达。

### 6. 测试

- 为核心组件、表单规则、权限守卫和状态转换编写单元测试。
- 为 P0 页面编写路由与交互测试。
- 与 API 契约保持一致，并至少完成一个真实后端的端到端烟雾路径。

## 输出

- 前端源码、主题配置、API 客户端和测试。
- `./output/build/frontend-implementation-report.md`
- 更新 `traceability.json` 和 `task-board.json`

报告中必须列出页面覆盖率：已实现页面 / P0 页面 / 全部页面，以及未实现原因。

---

## 质量检查清单

- [ ] 页面覆盖率达 P0
- [ ] 视觉规范符合 design-tokens
- [ ] API 客户端类型完整
- [ ] 表单校验与 PRD 一致
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
