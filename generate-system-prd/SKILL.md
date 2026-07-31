---
name: "generate-system-prd"
description: "Generates structured PRDs for enterprise management systems, native mobile apps, mobile web, mini programs, and multi-end products. Selects terminal-specific rules for domain models, user flows, page specs, permissions, device capabilities, and non-functional requirements."
---

# Generate System PRD — 系统产品设计文档生成器

本 Skill 用于从用户需求中生成**标准化的系统产品设计文档**，覆盖产品定位、领域模型、业务流程、页面规格、权限与非功能要求。它同时支持企业管理后台、原生移动 App、移动 Web/H5、小程序、混合应用和多端协同产品，并根据终端类型切换设计规则，避免把 PC 后台的表格、弹窗和数据库设计直接套用到移动端。

---

## 一、触发条件

当用户提出以下任一需求时，立即激活本 Skill：

1. 需要生成/编写一份**系统产品设计方案**或**PRD文档**
2. 需要对现有系统进行**逆向产品文档化**
3. 需要为企业内部管理系统编写设计规格
4. 用户提供了需求描述/截图/现有系统，要求输出**结构化的产品设计文档**
5. 需要为原生 App、H5、小程序或多端产品定义用户流程、页面状态、系统权限、端能力或发布要求

---

## 参考文件（references）使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/prd-document-template.md` | **逐章生成时必读**。包含13章+附录的完整章节模板、内容要求、格式规范和页面规格书写模板（SKILL.md §三仅保留索引） |
| `references/prd-stage-boundary.md` | **必读**。定义 PRD 与原型/实施阶段的职责边界、去重规则、`output/spec/pages.json` 的权威地位与校验结论（PASS/WARN/FAIL/NOT_REVIEWED），优先级高于通用设计要求 |
| `references/brainstorming-gate.md` | 需求输入不完整、缺少脑暴结论时读取，按其中的澄清问题模板先与用户确认，再进入生成流程 |
| `references/product-design-standards.md` | 逐章生成前读取，作为通用产品设计标准补充 |
| `references/schemas/` 下本阶段工件示例（`pages.example.json`（PRD 阶段快照）、`data-model`、`business-rules`、`permissions`、`state-machines`、`validation-report`、`decision-log`、`project`） | 需要向 `output/spec/` 产出对应 JSON 工件时参考结构 |
| `../_shared/references/schemas/` 下共享示例（`pipeline-context`、`design-tokens.default`、`annotations`、`pages`（原型富化后完整结构）等） | 需要共享结构或默认 Token 时参考；**唯一事实来源**，不要在本地重建拷贝 |
| `../_shared/references/pc_admin_ui_spec.md` | **admin_web 必读**。PC 管理端权威设计规范（基于 vue-admin-plus / Element Plus），定义色彩、字号、布局尺寸、间距、圆角、阴影、组件与页面模板。第8章"页面设计规格"涉及后台端布局、筛选区、表格、表单、弹窗、卡片、状态色与文案时必须遵循，优先级高于 `_shared` 默认 Token |

---

## 二、输入规范与模式判定

### 2.1 核心输入

优先从用户描述、头脑风暴结论或已有材料中提取以下输入。缺失信息不得静默编造；可基于合理假设继续生成，但必须在文档开头列出"待确认假设"。

```yaml
Inputs:
  product_name: "产品或系统名称"
  product_goal: "要解决的问题与核心价值"
  client_type: "admin_web | native_app | mobile_web | mini_program | hybrid | multi_end"
  product_scope: "full_system | feature_prd | mvp"
  target_users: []
  core_scenarios: []
  mvp_scope: []
  business_constraints: []
```

### 2.2 移动端/多端补充输入

当 `client_type` 不是 `admin_web` 时，补充识别：

```yaml
MobileInputs:
  target_os: ["iOS", "Android"]
  target_devices: ["phone"]
  orientation: "portrait | landscape | both"
  navigation_pattern: "bottom_tabs | stack | drawer | single_flow | mixed"
  account_and_login: "登录方式、会话与游客模式"
  network_assumption: "online_only | weak_network | offline_first"
  device_capabilities: ["camera", "album", "location", "notification", "bluetooth", "biometric", "file"]
  distribution_channel: "app_store | enterprise | web | mini_program_platform"
  design_baseline: "设计稿基准宽度、字号缩放与无障碍要求"
  multi_end_relationship: "与 PC/运营后台的职责边界和数据同步关系"
```

### 2.3 终端模式判定

- `admin_web`：采用后台导航、复杂筛选、表格、批量操作和 RBAC 规则。布局、色彩、字号、间距、圆角、组件与页面模板必须遵循 `../_shared/references/pc_admin_ui_spec.md`（基于 vue-admin-plus / Element Plus 的 PC 管理端权威设计规范）。
- `native_app` / `hybrid`：重点定义端能力、系统权限、生命周期、弱网、版本升级和应用商店约束。
- `mobile_web`：重点定义浏览器兼容、响应式、登录态、分享与 WebView 限制。
- `mini_program`：重点定义平台能力、分包/体积、授权、审核和平台跳转限制。
- `multi_end`：必须先给出"端职责矩阵"，明确哪些能力属于用户移动端、业务后台和公共服务端。
- 未明确终端时，先根据使用场景推断；无法可靠推断时按 `multi_end` 输出并显式标注假设。

### 2.4 文档深度

- `full_system`：生成完整 13 章和附录。
- `feature_prd`：保留 13 章标题，但与当前功能无关的章节写明"不适用及原因"，不得虚构大量后台表结构。
- `mvp`：优先保证用户闭环、关键状态、异常路径、埋点和验收标准，二期能力只保留摘要。

---

## 三、文档结构规范（13章 + 附录）

> 完整章节模板抽离到 `references/prd-document-template.md`，逐章生成时读取对应章节。本节仅保留章节索引和端专属约束摘要，避免 SKILL.md 膨胀。

| 章 | 标题 | template 对应 | 端专属约束摘要 |
|----|------|--------------|---------------|
| 1 | 产品总体设计 | §1 | 1.5 终端与使用场景（移动端/多端必填）：OS/设备/使用环境/与PC职责边界 |
| 2 | 产品架构设计 | §2 | 2.4 导航与信息架构（移动端/多端必填）；2.5 多端职责矩阵（multi_end 必填）；后台/移动端分层架构不同 |
| 3 | 核心领域与数据设计 | §3 | A.服务端数据表定义 / B.客户端数据契约（按范围选择）；金额禁浮点 |
| 4 | 关键业务流程设计 | §4 | 移动端流程需描述前后台切换/锁屏恢复/弱网重试；端能力需四条授权路径 |
| 5 | 特殊业务场景设计 | §5 | 移动端特殊场景（弱网/权限拒绝/Deep Link失效等）；多端冲突场景 |
| 6 | 报表与统计体系设计 | §6 | 移动端展示约束：优先卡片/趋势图，不直接缩放PC宽表格 |
| 7 | 权限体系设计 | §7 | 7.3 系统权限与隐私授权（移动端必填）：区分业务/系统/隐私权限 |
| 8 | 页面设计规格 | §8 | **admin_web 必须遵循 `../_shared/references/pc_admin_ui_spec.md`**（布局/色彩/字号/间距·圆角·阴影/组件/反馈/页面模板）；移动端用移动端模板，禁止套用PC宽表格/hover/右键 |
| 9 | 非功能性需求设计 | §9 | 移动端额外覆盖：启动/稳定性/网络/资源/兼容/隐私/可访问性/发布 |
| 10 | 数据完整性校验规则 | §10 | 10.4 移动端必须覆盖：重复点击/页面销毁/登录过期/离线提交/跨端冲突等 |
| 11 | 系统设置与基础配置 | §11 | 11.4 移动端发布与远程配置（移动端/多端必填）：版本/Feature Flag/推送/渠道 |
| 12 | MVP版本功能清单 | §12 | 无端差异 |
| 13 | 二期规划 | §13 | 无端差异 |
| 附录A | 完整表关系图 | §附录A | ASCII字符画 |
| 附录B | 状态机汇总 | §附录B | 统一编号 SM-XXX |

**第8章 admin_web 关键约束摘要**（详细以 `../_shared/references/pc_admin_ui_spec.md` 为准）：
- 布局：纵向布局，侧栏266px/折叠64px、顶栏60px、标签页栏50px、内容区间距20px
- 色彩：主色 `#1890ff`、功能色 成功`#13ce66`/警告`#ffba00`/危险`#ff6700`/错误`#ff4d4f`、页面背景`#f6f8f9`、深色菜单`#282c34`
- 字号：基准14px，主标题18px，卡片标题16px，看板核心数字22px
- 间距/圆角/阴影：4px基数，基准20px，圆角2.5px，阴影`0 1px 4px rgba(0,21,41,0.08)`，控件高32px
- 组件：主操作每视图区最多1个primary；查询表单一行3-4项；表格表头`#f5f7fa`；弹窗≤6字段用VabDialog(520-640px)，多字段用抽屉(600-800px)
- 反馈：写操作三态(loading→提示→更新)；破坏性操作必须ElMessageBox二次确认；按钮2-4字动宾短语
- 页面模板：列表页"查询卡片+表格卡片"两段式；表单页主标题+表单卡片+吸底操作栏；详情页el-descriptions+Tabs关联数据；看板页统计卡片行+图表区+明细表格
> 以上为快速预览，生成§8时必须读取 references/prd-document-template.md §8 获取完整页面规格清单(15项)和书写模板(后台版/移动端版)。

**第8章 页面规格书写模板**（后台/移动端模板详见 template §8）：含页面类型、筛选字段、工具栏、表格列、操作、弹窗、交互函数、业务说明等字段。

---

## 四、生成流程

当用户触发本 Skill 时，按以下步骤执行：

### Step 1：需求收集与确认

需求输入不完整或未经脑暴确认时，先按 `references/brainstorming-gate.md` 的澄清问题模板与用户确认，再继续本步骤。

向用户确认以下信息（如用户已提供则跳过）：

1. **产品名称和定位**：产品叫什么？解决什么问题？
2. **终端类型与范围**：后台、原生 App、H5、小程序、混合应用还是多端？是完整系统还是单一功能？
3. **核心业务域和用户任务**：涉及哪些领域？用户最常完成的任务是什么？
4. **目标用户与使用环境**：角色、设备、地点、频率、网络环境和注意力条件。
5. **移动端能力**（如适用）：相机、定位、通知、生物识别、文件、蓝牙等。
6. **登录、权限和隐私**：账号体系、游客模式、业务权限、系统权限和隐私约束。
7. **多端职责**（如适用）：移动端、PC 后台和服务端分别承担什么能力？
8. **特殊场景**：弱网、离线、系统中断、跨端冲突等是否需要处理？
9. **MVP范围**：一期必须形成的用户闭环是什么？
10. **统计与埋点需求**：需要哪些业务指标、产品行为指标、报表或看板？

### Step 2：逐章生成

按照 `references/prd-document-template.md` 的章节模板，**从第1章到附录依次生成**。每章生成时读取 template 对应章节，并：

1. 基于用户需求和业务逻辑推导内容
2. 严格遵循各章节的内容规范和格式要求
3. 数据模型必须完整定义所有字段（含类型、约束、说明）
4. 页面规格必须精确到每个字段、操作、状态、反馈和异常恢复；移动端不得只描述静态页面
5. 根据 `client_type` 应用对应规则：后台强调表格和批量操作，移动端强调任务闭环、状态、手势、权限、弱网和端能力
6. 状态机必须使用ASCII箭头绘制
7. 所有表格使用Markdown表格格式
8. 报表/统计体系根据业务需要灵活组织，不套用固定模板

### Step 3：交叉校验

文档生成后，执行以下校验：

1. **数据模型一致性**：第3章的表关系与附录A的表关系图一致
2. **状态机完整性**：第3章各表的状态流转与附录B的状态机汇总一致
3. **页面引用一致性**：第8章页面中引用的跳转目标与第2章页面清单一致
4. **指标口径一致性**：第6章指标公式与第3章数据模型字段对应
5. **权限覆盖完整性**：第7章权限矩阵覆盖第8章所有页面的操作
6. **校验规则覆盖**：第10章校验规则覆盖第4章业务流程中的所有约束
7. **端类型一致性**：页面模式、导航、权限和非功能要求与 `client_type` 一致
8. **状态覆盖完整性**：移动端每个核心页面均覆盖加载、空、失败、离线和权限受限状态
9. **多端职责一致性**：`multi_end` 模式下，第2章职责矩阵与流程、页面及权限设计一致
10. **可验收性**：核心移动任务有明确埋点和 Given/When/Then 验收标准

---

## 五、质量标准

生成的文档必须达到以下标准：

1. **完整性**：13章 + 附录全部生成，无遗漏章节
2. **精确性**：数据表字段定义精确到类型和长度，枚举值全部列出
3. **一致性**：同一概念在不同章节的命名和定义完全一致
4. **可执行性**：开发团队可直接依据文档进行开发，无需二次确认
5. **可追溯性**：所有业务规则有编号，所有校验规则有编号
6. **ASCII图表**：架构图、流程图、状态机均使用ASCII字符画，不依赖外部工具
7. **终端适配性**：不得把 PC 表格、悬浮交互或固定宽度弹窗直接套用到移动端
8. **状态完整性**：移动端核心页面必须具备正常、加载、空、异常、弱网和权限受限设计
9. **可测试性**：关键流程、端能力、异常恢复和升级策略均有可执行验收条件

---

## 六、关键设计模式参考

以下是企业管理系统常见的设计模式，生成文档时应**根据业务需要主动评估是否适用**：

### 6.1 数据模型模式
- **顶层实体锚定**：确定一个核心实体作为顶层锚点，所有数据最终归属
- **统一归集表**：多来源数据统一沉淀到一张归集表，确保计算口径唯一
- **多对多中间表**：关联关系使用独立中间表
- **版本机制**：需要历史追踪的数据使用版本链
- **乐观锁**：业务表包含version字段防止并发冲突
- **逻辑删除**：关键业务数据不物理删除，使用is_deleted标记

### 6.2 业务流程模式
- **录入即生效**：简化流程，录入直接生效（后续可加审批）
- **状态机管控**：实体状态流转通过状态机约束，不可随意跳转
- **冲销/撤销机制**：错误数据通过冲销/撤销处理，保留操作轨迹
- **关联约束**：下游操作受上游状态约束（如未完成A不可做B）
- **分摊/分配机制**：共享资源通过分摊关系归属到多个目标

### 6.3 页面设计模式

**后台模式：**
- 列表页：筛选 + 工具栏 + 表格 + 分页。
- 表单页：多区块 + 动态行 + 自动计算 + 保存草稿/提交。
- 详情页：概览栏 + 多Tab + 操作按钮。
- 仪表盘/报表页：筛选 + 指标卡片 + 图表 + 下钻 + 导出。
- 弹窗：modal-sm/md/lg 或自定义宽度。

**移动端模式：**
- 任务首页：清晰主行动 + 最近任务/待办 + 状态摘要。
- 列表/信息流：搜索/轻筛选 + 卡片列表 + 下拉刷新 + 上拉加载。
- 分步表单：单屏聚焦、即时校验、自动保存草稿、退出恢复。
- 详情页：摘要优先、渐进披露、底部主操作，避免堆叠大量 Tab。
- 选择器：Bottom Sheet、全屏选择、系统选择器，避免宽大桌面弹窗。
- 反馈：骨架屏、Toast、Inline Error、结果页；关键失败必须提供恢复动作。
- 导航：Bottom Tab + Stack 为主，避免层级过深和不可预测的跨 Tab 返回。

### 6.4 统计指标模式
- **口径统一**：所有指标统一定义计算公式，禁止各模块自行计算
- **多套指标**：根据业务需要定义已实现/预计/预算等多套指标
- **统计口径标注**：每个指标明确统计时间维度
- **组织级汇总规则**：明确下级组织汇总到上级时的去重/合并规则

---

## 七、输出格式

- 文件格式：Markdown (.md)
- 文件命名：`{产品名称}-{端类型}-产品设计方案-V{版本号}.md`
- 输出目录：默认写入 `output/docs/`（用户指定其他位置时从其指定）
- 表格：全部使用Markdown表格
- 图表：全部使用ASCII字符画
- 代码块：状态机、流程图、校验规则使用代码块包裹
- 版本标记：新增字段/表使用 ★NEW 标记，变更使用版本号标注
- 文档开头必须标明：`client_type`、`product_scope`、目标 OS/设备、关键假设和不在范围内的终端
- `multi_end` 模式需额外输出"多端职责矩阵"和"端差异清单"

### 编号体系（供实施追溯使用）

| 编号 | 含义 | 产生章节 |
|------|------|---------|
| `PXX` | 页面编号；双端同名页面共用，以"所属端"字段区分 | 第2章页面清单、第8章页面规格 |
| `BR-XXX` | 业务规则（校验、互斥、约束） | 第4章关键规则、第5章特殊场景 |
| `VXX / SXX / CXX / EXX` | 校验规则子类（录入/状态/一致性/异常）；实施追溯时统一映射为 `VR-XXX` 序列 | 第10章 |
| `PERM-XXX` | 功能权限与系统权限条目 | 第7章 |
| `SM-XXX` | 状态机 | 第3章、附录B |
| `TXX` | 数据表/逻辑实体 | 第3章 |
| `SXX` | 页面标注 | **不在 PRD 生成**，由 `generate-prototype` 在 `annotations.json` 中声明 |

下游阶段使用的 ID 前缀（在对应 schema 示例中可见，追溯时直接引用，PRD 不生成）：

| 编号 | 含义 | 产生阶段 |
|------|------|---------|
| `ACT-XXX` | 页面动作 | `generate-prototype`（`actions.json`） |
| `OV-XXX` | 弹层/浮层 | `generate-prototype`（`overlays.json`） |
| `CMP-XXX` | 复用组件 | `generate-prototype`（`components.json`） |
| `CMD-XXX` | 命令（动作意图目标） | `generate-prototype` |
| `CHK-XXX` | 交叉校验项 | 各阶段校验（`validation-report.json`） |
| `TBD-XXX` | 待决项 | 各阶段（`decision-log.json`） |
| 原型 ID（如 `PC-DETAIL`） | 页面原型分类 | `generate-prototype`（`page-archetypes.json`） |

### JSON 工件（可选输出）

当后续阶段需要机器可读输入时，除 Markdown 文档外，可按 `references/schemas/`（本阶段工件）与 `../_shared/references/schemas/`（共享结构）下的示例向 `output/spec/` 产出：`pages.json`（页面身份与路由的权威来源）、`data-model.json`、`business-rules.json`、`permissions.json`、`state-machines.json`、`pipeline-context.json`。Markdown 文档与 JSON 工件内容必须一致；冲突时以 JSON 工件为权威来源。