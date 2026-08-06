---
name: "generate-html-mobile"
description: "仅生成任务型移动端HTML原型页面(综合入口/内容发现/分类检索/图文列表/沉浸详情/交易/个人中心/公共账户/实时信息)。PC管理后台请用 generate-html-pc-admin;双端或端未明时由 generate-html-pages 路由器调度。"
---

# Generate HTML Mobile — 任务型移动端静态原型页面生成器

本 Skill 是 `generate-html-pages` 的**移动端子 Skill**，工作台架构拆分后专责生成 `output/site/mobile/` 下的页面。会先识别页面任务与原型，再生成综合入口、内容发现、分类检索、图文列表、沉浸详情、交易、个人中心、公共账户或实时信息页面。

> PC 管理后台原型由 `generate-html-pc-admin` 生成；双端或端未明时由 `generate-html-pages` 路由器统一调度，不要重复执行两端生成。本 Skill 只产出 `output/site/mobile/` 目录，不生成 `index.html` 总控台（由 `generate-portal` 独占）。

---

## 一、触发条件

本 Skill 通常由 `generate-html-pages` 总纲在判定为移动端/双端输出时调度；以下情况也可直接激活：

1. 用户明确指定「移动端 / 手机端 / H5 / 触屏端」需要生成 HTML 原型页面
2. 上游 `pages.json` 的 `devices` 字段或 PRD 的 `client_type` 表明仅/含移动端
3. 需要将移动端 PRD/原型文档转化为可点击的页面原型

### 1.1 输入文件

- 系统 PRD：定义移动端终端类型、功能、数据和业务规则。
- 页面原型文档：定义移动端页面清单、字段、交互和流转。
- UI 设计规范（可选）：定义品牌色、字体、间距、圆角及组件样式；存在时优先使用。
- 上游 JSON 工件（优先）：见 §七 信息来源。

---

## 二、输出文件结构

```
output/site/mobile/
├── common.css              # 移动端公共样式
├── navbar.js               # 移动端导航配置（顶部栏渲染 + 底部 Tab）
├── P01-login.html          # 移动端登录页
├── PXX-xxx.html            # 移动端各业务页面
└── ...
```

> 本 Skill 只负责 `output/site/mobile/` 目录。`output/site/pc/` 由 `generate-html-pc-admin` 负责；总控台 `output/site/index.html` 由 `generate-portal` skill 独占生成。双端场景下两端同名页面内容对应但布局不同。

---

## 三、移动端规范

生成移动端页面时，先读取 `references/mobile-product-design-standards.md`，从页面任务选择合适的移动端原型。不得把 PC 页面缩窄，也不得把分析用截图、品牌图、广告图或人物图直接复制到 Skill 或输出页面。

### 3.1 移动端设计决策

在写 HTML 前必须完成以下判断：

1. **核心任务**：用户进入本页最主要要完成什么？
2. **页面原型**：从综合入口首页、内容发现首页、分类检索、图文列表、沉浸详情、交易任务、个人中心、公共账户、实时信息中选择一个主原型。
3. **导航层级**：全局频道、局部 Tab、底部主导航最多同时保留两层。
4. **首屏焦点**：搜索、服务入口、余额、订单状态、到站时间、价格或主按钮中只设一个首要焦点。
5. **内容密度**：选择 `comfortable / standard / compact`；首页可 compact，表单和账户页优先 standard。
6. **固定区域**：判断是否需要 sticky 顶栏、底部主操作或底部主导航，并为安全区和内容留出空间。

可使用 `references/schemas/mobile-page-patterns.example.json` 记录选择结果。

### 3.2 移动端 common.css

> 完整的 CSS 变量体系、组件类名索引和默认视觉约束已抽离到 `references/mobile-tokens-and-classes.md`，生成移动端 common.css 和页面专属样式时读取该文件。

**核心约束摘要**：
- 品牌色与语义色与 PC 端 `pc-admin-navigation-style.md` 保持一致（双端共享）
- 设计基准 `375×812`，在 390-430px 验证；点击区域≥44×44px
- viewport 必须允许缩放：`width=device-width, initial-scale=1, viewport-fit=cover`
- 项目内只使用一套 SVG 图标；不得使用 Emoji 充当业务图标

### 3.3 移动端 navbar.js

> 完整的函数签名规范和 TAB_BAR_ITEMS 数据结构模板已抽离到 `references/mobile-navbar-template.md`，生成移动端 navbar.js 时读取该文件。

**导出函数清单**：`ACTIVE_TAB` / `MOBILE_PAGE_META` / `TAB_BAR_ITEMS` / `renderMobileHeader()` / `renderTabBar()` / `bindLocalTabs()` / `bindContextPopover()` / `syncSafeAreaSpacing()`

> 底部主导航不是默认必选项。二级页、详情页、全屏表单和结算页通常隐藏它；辅助入口优先放在页面内、Drawer或底部面板。

### 3.4 移动端页面结构

> 完整的业务页面通用 HTML 结构模板和结构约束已抽离到 `references/mobile-page-skeleton.md`，生成移动端 HTML 页面时读取该文件。

**结构约束摘要**：
- 一级首页可使用上下文头部；二级列表和普通详情使用返回顶部栏
- 底部主导航只出现在一级页面；固定主操作存在时判断是否隐藏底部主导航
- 登录页使用全屏表单，不使用主导航
- 禁止 `maximum-scale=1` 和 `user-scalable=no`

### 3.5 移动端按页面原型生成

> 9 种移动端原型 + 表单页的详细生成规则已抽离到 `references/mobile-archetype-specs.md`，按页面 archetypeId 选择对应原型并读取该文件对应章节。

| 原型 | archetypeId | 核心结构 |
|------|-------------|---------|
| 综合入口首页 | service-home | 上下文头部→搜索/运营位→服务宫格→专题卡→内容列表→底部主导航 |
| 内容发现首页 | content-home | 搜索→主题运营位→快捷分类→推荐卡/横向滚动→新闻列表 |
| 分类检索页 | category-search | 返回/搜索栏→横向一级分类→排序筛选→左侧二级分类+右侧结果 |
| 图文列表页 | media-list | 顶部栏→局部Tab/筛选→图文列表→加载更多 |
| 沉浸详情页 | detail | 媒体区→核心信息→评分/标签/位置→纵向详情分区→固定主操作 |
| 交易原型(购物车+订单) | cart/orders | 购物车:商家分组→商品条目→结算栏；订单:状态Tab→订单卡列表 |
| 个人中心 | profile | 渐变头部→头像身份→状态快捷卡→分组菜单→底部主导航 |
| 公共账户 | public-account | 机构身份→账户概览→核心办理按钮→信息卡/查询宫格 |
| 实时信息 | realtime | 场景化头部→搜索→最近对象→实时列表→行内展开详情 |
| 表单与办理页 | form | 返回+标题→分组单列表单→说明/附件→底部固定操作 |

### 3.6 移动端状态与动效

- 首屏数据页使用结构匹配的骨架屏。
- 列表加载更多使用局部 loading，不默认全屏遮罩。
- 分类展开层、Drawer和底部面板使用180-240ms缓动，并支持 `prefers-reduced-motion`。
- 根据业务实现 `normal/loading/empty/error/offline/permissionDenied/disabled/soldOut` 等适用状态。
- 成功操作使用轻提示；高风险操作使用确认对话框并说明影响。
- 金额、数量、实时状态更新应有可感知反馈，必要时使用 `aria-live`。

### 3.7 移动端资源规则

1. 分析用截图不复制、不裁切、不压缩、不打包。
2. 不复刻截图中的品牌Logo、专属插画、商品图、人物图、广告图和原文案。
3. 用户明确提供并授权用于最终项目的资产可进入项目输出目录。
4. 缺少资产时使用本地SVG、CSS渐变、几何图形、文字排版和中性占位。
5. 示例页面不依赖外部CDN或远程图片。
6. 可打开 `references/examples/mobile-pattern-demo.html` 检查抽象后的移动端设计语言。

---

## 四、移动端生成流程

### Step 1：确认移动端页面清单与原型

1. 端需求已由 `generate-html-pages` 总纲判定为移动端/双端；本 Skill 聚焦移动端页面。
2. 优先从 `pages.json`（`devices` 字段）确认含移动端的页面清单。
3. 仅在工件和文档均无法判断底部 Tab 配置时询问用户；底部 Tab 栏不得凭空补齐。

### Step 2：读取上游工件与文档

1. **优先读取上游 JSON 工件**（见 §七）：`pages.json`、`navigation.json`、`actions.json`、`overlays.json`、`components.json`、`permissions.json`、`state-machines.json`、`design-tokens.json`、`pipeline-context.json`（不读取 `annotations.json`）
2. 工件缺失的字段回退到 PRD、页面原型文档和用户提供的 UI 设计规范提取
3. 建立 `pageId → 规格` 映射表，记录每个字段的 `sourceLevel`（CONFIRMED/INFERRED/FALLBACK）和 `sourceRefs`
4. 对每个移动端页面记录核心任务、页面原型（archetypeId）、导航层级、内容密度和固定区域

### Step 3：生成移动端公共文件

按移动端输出到 `output/site/mobile/`：

1. **移动端 common.css**：按 `design-tokens.json` 生成 Token；缺失项使用移动端默认 Token（基准见 `references/mobile-tokens-and-classes.md`）
2. **移动端 navbar.js**：根据 `navigation.json` 生成底部 Tab 配置（`TAB_BAR_ITEMS`）和导航渲染函数（详见 `references/mobile-navbar-template.md`）

> 不生成 `index.html`。总控台由 `generate-portal` skill 独占输出。

### Step 4：逐页生成移动端 HTML

1. 按 `pages.json` 页面清单逐页生成移动端 HTML
2. 移动端先按 `archetypeId` 选择页面原型，再生成对应 HTML 结构（详见 `references/mobile-archetype-specs.md`）；页面骨架模板见 `references/mobile-page-skeleton.md`
3. 双端场景下移动端与 PC 端同名页面内容对应但布局不同
4. 从 `annotations.json`/`overlays.json`/`actions.json` 提取字段、筛选、卡片列、弹窗（移动端优先 Drawer，复杂任务使用全屏页）、操作，填充示例数据
5. 所有跳转链接指向移动端内的正确页面文件
6. 按 `permissions.json` 的 `validation` 字段控制字段显隐和操作可用性

**强制约束：** 禁止占位符、必须实现真实交互，详见 §五 强制约束。

### Step 5：移动端交叉校验

1. **链接完整性**：所有移动端 href 指向的文件都已生成
2. **端内一致性**：移动端导航配置（`TAB_BAR_ITEMS`）与页面清单一致
3. **状态标签覆盖**：`state-machines.json` 中所有状态枚举值在移动端都有对应样式（`.m-tag-xxx`）
4. **示例数据一致性**：双端场景下同一页面在移动端和 PC 端的示例数据一致
5. **占位符清零与交互完整性**：详见 §五 质量标准

### Step 6：输出构建报告

向 `output/site/build-report.json`（结构见 `../_shared/references/schemas/html-build-report.example.json`）写入移动端部分，供 `generate-portal` 消费：

- `outputs`：每个移动端页面文件的 `pageId`、`device:mobile`、`path`、`contentHash`、`applicableStates`、`annotationMode`
- `checks`：链接完整性、端内一致性、状态覆盖等移动端校验结果
- `unstructuredItems`：从文档兜底提取的字段（`generatedByFallback: true`）
- `openIssues`：未实现的 TODO（HTML 注释形式）、跳过项及原因
- 每个字段记录 `sourceLevel` 和 `sourceRefs`，便于下游溯源

> 双端场景下 `build-report.json` 由 `generate-html-pages` 总纲合并 PC/移动两部分；单移动端场景由本 Skill 直接写入。

---

## 五、移动端质量标准

### 5.1 强制约束与通用性边界

**禁止占位符：**

- 禁用文案包括但不限于："开发中"、"功能开发中"、"敬请期待"、"暂未开放"、"待开发"、"Coming Soon"、"TODO"、"暂未实现"。
- 原型文档中定义的所有交互函数（如 `handleUpload`、`handleSave`、`openDetailModal`、`openEditModal` 等）**必须实现完整的前端交互逻辑**，不得仅弹 Toast 提示"开发中"。
- 若原型文档对某功能的描述模糊或缺细节，应**按 §六 交互实现模式的通用模式实现最小可用交互**，而非使用占位符。仍无法实现时，在 HTML 注释 `<!-- TODO: ... -->` 中说明，禁止在用户可见区域展示"开发中"文案。
- 生成每个 HTML 文件后，必须自检该文件中是否存在上述禁用占位符文案；存在则立即修复后再进入下一文件。

**通用性边界（重要）：**

- **仅当原型文档定义了交互函数或操作按钮时，才需要按 §六 实现交互**。纯展示页面（如关于我们、公司介绍、静态公告）无需强制添加 CRUD 或排序功能。
- §六 的参考代码是**模式片段**，不是可直接复制粘贴的完整实现。生成代码时必须按项目实际的字段名、选择器、弹窗 ID 等替换 `{占位符}`。
- 若项目已有 `common.css`/`navbar.js` 提供了基础函数（如 `showToast`、`openModal`），页面中**不得重复定义**，直接调用即可。

### 5.2 移动端 HTML 编码规范

1. 文件编码：UTF-8（含BOM）
2. 语言：`<html lang="zh-CN">`
3. 缩进：2空格
4. 金额格式：`¥1,234,567.89`，移动端 `.m-amount`
5. 日期格式：`YYYY-MM-DD`
6. 百分比格式：`XX.X%`
7. 自动计算字段：灰色背景只读
8. 必填标记：红色星号 `*`
9. 移动端引入 `common.css` + `navbar.js`
10. 移动端 viewport：`width=device-width, initial-scale=1, viewport-fit=cover`，不得禁止缩放
11. 移动端触摸区域：最小 44×44px

### 5.3 移动端质量标准

1. **可浏览性**：所有页面可直接在浏览器打开，布局正确
2. **可导航性**：所有链接可点击跳转，导航正常工作
3. **端适配**：移动端布局符合移动平台习惯，375px 基准并在 390-430px 验证
4. **视觉还原**：优先符合用户UI规范，并保持移动端 Token 一致
5. **数据真实感**：示例数据合理，金额格式正确
6. **交互可用**：弹窗可打开关闭，Tab可切换，表单可输入
7. **移动端体验**：页面原型与任务匹配；点击区域≥44px；固定底栏不遮挡内容；允许浏览器缩放
8. **图标体系统一**：全项目只使用一套图标体系，优先内联 SVG；禁止混用 Emoji、FontAwesome、Ant Design Icons 等多套图标库；菜单、消息、用户、折叠等图标均使用内联 SVG
9. **资源合规**：分析用截图只用于提炼规则，不复制、不裁切、不压缩、不打包进 Skill 或输出页面；不复刻截图中的品牌 Logo、专属插画、商品图、人物图、广告图和原文案；仅使用项目授权资产，缺失时使用本地 SVG、CSS 渐变、几何图形或中性占位
10. **viewport 一致**：移动端使用 `width=device-width, initial-scale=1, viewport-fit=cover`；禁止 `maximum-scale=1` 和 `user-scalable=no`，必须允许浏览器缩放
11. **零占位符**：所有 HTML 文件中不得出现"开发中"、"敬请期待"等占位文案（详见 5.1）
12. **交互可用性**：文件/图片上传可触发文件选择并显示预览或回填文件名；详情/编辑弹窗可打开并填充数据；删除等危险操作有二次确认（详见 §六）

---

## 六、交互实现模式（索引）

> 以下交互场景的完整代码模板和检查点已抽离到 `../generate-html-pages/references/interaction-patterns.md`，本节仅保留索引和强制约束。生成代码时按需读取该文件，并按项目实际字段名、选择器、弹窗 ID 替换 `{占位符}`。

| 小节 | 场景 | interaction-patterns.md 对应章节 | 强制约束摘要 |
|------|------|--------------------------------|------------|
| §1 | Toast / Modal / 确认 / escapeHtml 基础函数 | §1 | 弹窗必须用 `classList` 操作 `.show` 类；**禁止**弹窗 HTML 写 `style="display:none"`；**禁止** JS 直接操作 `style.display` |
| §2 | 文件与图片上传 | §2 | 必须实现文件选择+校验+回填/预览完整逻辑；删除/移除需二次确认；不得仅 Toast |
| §3 | 弹窗与操作（详情/编辑/删除/状态切换/导出） | §3 | 详情/编辑弹窗必须从行读取数据回填；删除等危险操作必须 `confirmAction` 二次确认；禁止直接 `showToast('已删除')` |
| §4 | 列表 CRUD 与排序（卡片/表格变体） | §4 | 必须实现真实 DOM 增删改，禁止仅 Toast；**涉及排序的卡片列表必须用单列横向布局**；**表格必须有独立序号列和排序列**；排序/新增/删除后必须刷新序号 |

> 移动端弹窗优先使用 Drawer/底部面板，复杂任务使用全屏页；居中浮层 Modal 仅在确需阻断时使用。

**通用性边界：** 仅当原型文档/`actions.json` 定义了交互函数或操作按钮时，才需要按上述模式实现交互。纯展示页面无需强制添加 CRUD 或排序。若项目已有 `common.css`/`navbar.js` 提供基础函数，页面中**不得重复定义**，直接调用即可。

---

## 七、信息来源与映射规则

### 7.1 优先级：上游 JSON 工件 > 文档提取

本 Skill 处于流水线中游，上游 `generate-system-prd` 和 `generate-prototype` 已产出结构化 JSON 工件。**必须优先读取这些工件**，文档仅作补充和兜底，以避免重复解析和置信度丢失。

**上游工件清单（按优先级）：**

| 工件 | 路径 | 生产者 | 移动端用途 |
|------|------|--------|------|
| `pages.json` | `output/spec/pages.json` | generate-system-prd | 页面注册表（id/title/moduleId/type/route/devices/coreTask/archetypeId/applicableStates/actionIds/specIds） |
| `navigation.json` | `output/spec/navigation.json` | generate-prototype | 移动端底部 Tab 配置 |
| `actions.json` | `output/spec/actions.json` | generate-prototype | 页面动作（按钮、提交、跳转） |
| `overlays.json` | `output/spec/overlays.json` | generate-prototype | 弹层（Drawer/Sheet/全屏页） |
| `components.json` | `output/spec/components.json` | generate-prototype | 复用组件 |
| `permissions.json` | `output/spec/permissions.json` | generate-system-prd | 权限定义 |
| `business-rules.json` | `output/spec/business-rules.json` | generate-system-prd | 业务规则（状态机、校验） |
| `state-machines.json` | `output/spec/state-machines.json` | generate-system-prd | 状态枚举与流转（移动端 `.m-tag-xxx`） |
| `design-tokens.json` | `output/spec/design-tokens.json` | generate-prototype（唯一产出者；用户可在原型阶段提供项目 Token 作为输入） | 项目 UI Token；缺失时用 `_shared/references/schemas/design-tokens.default.json` 兜底 |
| `pipeline-context.json` | `output/spec/pipeline-context.json` | 各上游 skill | 字段来源与置信度标记 |

> **不消费 `annotations.json`**：本 Skill 不读取、不绑定页面标注（不生成 `data-spec-id`/`data-page-id`）；`output/spec/annotations.json` 由 `generate-prototype` 创建，仅供 `generate-portal` 在门户层读取展示。
>
> 工件结构示例见 `../_shared/references/schemas/`。工件缺失时回退到 PRD/原型文档提取，并在 `build-report.json` 中标记 `generatedByFallback: true`。

### 7.2 工件到移动端 HTML 的映射规则

| HTML内容 | 首选工件 | 文档兜底来源 | 移动端提取规则 |
|---------|---------|------------|---------|
| 系统名称/Logo | `design-tokens.json` | PRD 产品定位 | 直接使用 |
| Tab栏菜单 | `navigation.json` | PRD 功能模块清单 | 构建移动端 `TAB_BAR_ITEMS` |
| 页面文件名 | `pages.json`（id+title） | PRD 页面清单 | 编号+名称生成 |
| CSS色值 | `design-tokens.json` | 原型文档设计规范 | 用户UI规范优先；缺失项使用本Skill默认移动端Token |
| 移动端页面原型 | `pages.json`（archetypeId/coreTask） | 原型文档页面结构 | 选择 service-home、content-home、category-search、media-list、detail、cart/orders、profile、public-account 或 realtime |
| 状态标签 | `state-machines.json` | PRD 状态枚举 | 移动端 `.m-tag-xxx` |
| 筛选条件 | `annotations.json`（display） | 原型文档页面规格 | 移动端精简入口+Drawer/上下文展开层 |
| 卡片字段 | `annotations.json`（display） | 原型文档页面规格 | 移动端卡片字段 |
| 表单字段 | `annotations.json`（display/interaction） | 原型文档页面规格 | 移动端单列 |
| 概览指标 | `annotations.json`（display） | 原型文档页面规格 | 移动端2列网格 |
| 弹窗 | `overlays.json` | 原型文档页面规格 | 移动端优先 Drawer，复杂任务使用全屏页 |
| 按钮与操作 | `actions.json` | 原型文档页面规格 | 按 actionIntents 实现交互，参见 §六 |
| 权限控制 | `permissions.json` | PRD 权限矩阵 | 按 validation 字段控制字段显隐和操作可用性 |
| 返回按钮 | `pages.json`（moduleId/level） | 原型文档页面流转 | 移动端返回按钮 |
| 跳转链接 | `actions.json`（targetType=route） | 原型文档页面流转 | 移动端端内跳转 |
| 图片与运营素材 | `design-tokens.json`（资产引用） | PRD 品牌/内容资产说明 | 仅使用明确授权的项目资产；缺失时使用本地SVG、CSS渐变或中性占位，不打包分析截图 |

> 章节编号不固定，根据PRD实际结构定位对应内容。每个字段在 `build-report.json` 中记录 `sourceLevel`（CONFIRMED/INFERRED/FALLBACK）和 `sourceRefs`，便于下游溯源。

---

## 八、参考文件使用指引

| 文件 | 相对路径 | 用途 |
|------|------|------|
| 移动端产品设计规范 | `references/mobile-product-design-standards.md` | 移动端原型选择与设计基准（必读） |
| 移动端视觉Token与组件类名 | `references/mobile-tokens-and-classes.md` | CSS变量体系+组件类名索引+默认视觉约束（生成common.css时读取） |
| 移动端navbar.js模板 | `references/mobile-navbar-template.md` | 函数签名规范+TAB_BAR_ITEMS数据结构（生成navbar.js时读取） |
| 移动端页面骨架模板 | `references/mobile-page-skeleton.md` | 业务页面通用HTML结构+结构约束（生成HTML时读取） |
| 移动端页面原型生成规则 | `references/mobile-archetype-specs.md` | 9种原型+表单页详细生成规则（按archetypeId按需读取） |
| 移动端页面原型示例 | `references/schemas/mobile-page-patterns.example.json` | 记录 archetype 选择结果的数据结构 |
| 移动端原型演示 | `references/examples/mobile-pattern-demo.html` | 检查抽象后的移动端设计语言 |
| 交互实现模式 | `../generate-html-pages/references/interaction-patterns.md` | Toast/Modal/上传/CRUD/排序代码模板（跨端共享） |
| HTML构建报告示例 | `../_shared/references/schemas/html-build-report.example.json` | `build-report.json` 结构定义 |
| 工件结构示例 | `../_shared/references/schemas/` | 上游 JSON 工件结构示例 |
| PC端导航样式 | `../generate-html-pc-admin/references/pc-admin-navigation-style.md` | 双端共享品牌色/语义色基准（只读参考） |
