---
name: "generate-html-pc-admin"
description: "仅生成PC管理后台HTML原型页面(vue-admin-plus风格:深色侧栏+工作区页签)。移动端请用 generate-html-mobile;双端或端未明时由 generate-html-pages 路由器调度。"
---

# Generate HTML PC Admin — PC管理后台静态原型页面生成器

本 Skill 是 `generate-html-pages` 的 **PC 端子 Skill**，仅负责生成 `output/site/pc/` 目录下的 PC 管理后台静态 HTML 原型页面，遵循 vue-admin-plus / Element Plus 纵向布局风格（深色侧栏 `#282c34`、主色 `#1890ff`、圆角 2.5px、顶栏 60px、侧栏 266px、工作区页签栏 50px）。

> 移动端页面生成请使用 `generate-html-mobile`；双端输出或端未明时由 `generate-html-pages` 总纲路由器调度。本 Skill 不生成总控台 `index.html`（由 `generate-portal` 独占）。

---

## 一、触发条件

本 Skill 通常由 `generate-html-pages` 总纲在判定为 PC 端或双端输出时调度激活。当用户明确指定以下意图时，也可直接激活：

1. 需要根据设计文档**生成 PC 管理后台 / PC 管理端 HTML 原型页面**
2. 需要将 PRD/原型文档**转化为可点击的 PC 后台页面原型**
3. 需要为企业管理系统**制作 PC 端静态演示页面**
4. 用户提供了设计文档，要求输出**可直接浏览的 PC 后台 HTML 文件**

> 仅生成 PC 端时，输出目录直接为 `output/site/pc/`。若 PRD 同时要求移动端，应由 `generate-html-pages` 路由器协同 `generate-html-mobile` 处理，本 Skill 不越界生成移动端文件。

---

## 二、输出文件结构

```
output/site/
├── pc/                         # PC端页面（本 Skill 输出）
│   ├── common.css              # PC端公共样式
│   ├── sidebar.js              # PC端菜单、头部面包屑、工作区页签与折叠逻辑
│   ├── P01-login.html          # PC端登录页
│   ├── PXX-xxx.html            # PC端各业务页面
│   └── ...
└── build-report.json           # 构建报告（PC端页面清单、TODO、跳过项），供 generate-portal 消费
```

> **总控台 `output/site/index.html` 不由本 Skill 生成**。需要统一评审门户时，调用 `generate-portal` skill，它会消费本 Skill 的 `build-report.json`。

---

## 三、PC端规范

### 3.1 PC端 common.css

> **Token 与壳层基准**：PC 端的 CSS 变量、尺寸、颜色、圆角、阴影、DOM 骨架与 sidebar.js 行为模板**一律以 `references/pc-admin-navigation-style.md` 为唯一基准**（该文件已与 `_shared/references/pc_admin_ui_spec.md` 对齐，遵循 vue-admin-plus / Element Plus 纵向布局：深色侧栏 `#282c34`、主色 `#1890ff`、圆角 2.5px、顶栏 60px、侧栏 266px、工作区页签栏 50px）。本节不再重复 Token 定义，仅保留组件类名索引，避免双版本漂移。项目 Token 优先于默认值，但不得破坏壳层尺寸联动。

**按实际页面需要覆盖的样式模块：**

| 模块 | 类名 | 说明 |
|------|------|------|
| 布局 | `.admin-shell` `.admin-header` `.admin-sidebar` `.admin-workspace` `.admin-main` | 侧栏+顶栏+工作区页签栏+内容区（尺寸、色值、圆角、阴影详见 `pc-admin-navigation-style.md`） |
| 导航 | `.brand-area` `.header-main` `.header-breadcrumb` `.header-actions` `.workspace-tabs` `.workspace-tab` | 品牌区、头部面包屑、右侧账号区和工作区页签 |
| 页面 | `.page-header` `.page-title` `.card` `.card-title` `.page-surface` | 页面通用结构；主内容区不重复显示全局面包屑 |
| 筛选 | `.filter-bar` `.filter-row` `.filter-item` | 白色卡片内Grid布局，默认3列，大屏4列 |
| 按钮 | `.btn` `.btn-primary/success/warning/danger/default/text` `.btn-sm/lg` | 圆角与主色遵循 `pc-admin-navigation-style.md`；主按钮使用主色 |
| 表单 | `.input` `.select` `.textarea` `.datepicker` `.checkbox` `.radio` `.form-group` `.form-row` | 输入控件高32px（Element Plus default），聚焦使用主色边框 |
| 表格 | `table` `thead` `tbody` `.text-right/center` `.link` | 表头浅灰底 `#f5f7fa`，行高56-60px，数值使用等宽数字 |
| 分页 | `.pagination` `.page-btn` | 页码分页 |
| 标签 | `.tag` `.tag-primary/success/warning/danger/info` | 使用浅色背景胶囊徽章，禁止实心状态Tag |
| 指标卡片 | `.stat-cards` `.stat-card` `.stat-label/value/change/sub` | 多列指标卡片 |
| 进度条 | `.progress-bar` `.progress-fill` `.red/yellow/green` | 进度条 |
| 弹窗 | `.modal-overlay` `.modal` `.modal-sm/md/lg` `.modal-header/body/footer` | 居中浮层弹窗 |
| 提示 | `.alert` `.alert-warning/danger/info/success` | 消息提示 |
| Tab | `.tabs` `.tab-item` | 标签页 |
| 详情 | `.detail-row` `.detail-overview-bar` `.detail-tabs` `.detail-tab-content` | 详情页 |
| 附件 | `.upload-area` `.file-item` | 附件上传 |
| 金额 | `.amount` `.amount-positive/negative` | 金额显示 |
| 图表占位 | `.chart-placeholder` | 图表占位区 |
| 网格 | `.grid-2/3/4` | 栅格布局 |
| 提示框 | `.tip` `.tip-text` | Tooltip |
| 空状态 | `.empty-state` | 空数据提示 |

### 3.1.1 PC端默认视觉约束

> 壳层尺寸、色值、圆角、阴影、DOM 骨架、sidebar.js 行为**一律以 `references/pc-admin-navigation-style.md` 为唯一基准**（深色侧栏、主色 `#1890ff`、圆角 2.5px、顶栏 60px、侧栏 266px、页签栏 50px、阴影 `0 1px 4px rgba(0,21,41,0.08)`）。本节仅补充壳层之外的页面级约束，不重复壳层数值，避免双版本漂移。除非用户或项目 Token 明确覆盖，否则不得偏离基准。可打开 `references/examples/pc-admin-shell-demo.html` 检查壳层效果。分析用截图不得打包进 Skill。

- 页面标题18px/600，模块标题16px/600，正文与表格14px。
- 主工作区内容优先放入白色 `.page-surface` 或卡片；页面内容内边距默认 20px，小于 1440px 可降至 16px。
- 表格高频操作直接展示；删除、禁用等低频危险操作收纳到“更多”。
- 数值右对齐；日期、金额和 ID 使用等宽数字。

### 3.2 PC端 sidebar.js

**必须导出的变量和函数：**
- `ACTIVE_MENU`：当前页面菜单标识
- `PAGE_META`：当前页面标题、头部面包屑和工作区页签信息
- `SIDEBAR_MENUS`：菜单配置数组（嵌套结构：模块 → 子菜单项）
- `renderSidebar()`：渲染侧边栏到 `#sidebar-container`，自动展开当前模块并高亮
- `renderHeaderBreadcrumb()`：渲染到 `#header-breadcrumb`
- `renderWorkspaceTabs()`：至少渲染当前页签到 `#workspace-tabs`
- `bindSidebarToggle()`：绑定 `#sidebar-toggle`，同步切换侧栏、品牌区和工作区宽度

**菜单渲染要求：**
- 一级分组使用可点击按钮和右侧折叠箭头；二级菜单使用链接。
- 当前项设置 `aria-current="page"`，当前分组设置 `aria-expanded="true"`。
- 菜单文本溢出使用省略号，悬停时通过 `title` 或 Tooltip 展示完整文本。
- 折叠状态写入 `localStorage`，页面跳转后保持；没有菜单图标的纯文字项目可折叠为 0px，不保留空白窄栏。
- 禁止用 Emoji 充当菜单、消息、用户或折叠图标；统一使用内联 SVG。

### 3.3 PC端页面结构

**业务页面通用结构：**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{页面标题} - {系统名称}</title>
  <link rel="stylesheet" href="common.css">
  <style>/* 页面专属样式 */</style>
</head>
<body>
  <script>
    var ACTIVE_MENU = '{menu-id}';
    var PAGE_META = {
      title: '{页面标题}',
      breadcrumbs: ['{一级模块}', '{页面标题}'],
      tab: { id: '{menu-id}', label: '{页面标题}', href: location.pathname.split('/').pop() }
    };
  </script>

  <div class="admin-shell">
    <aside class="admin-sidebar" aria-label="主菜单">
      <a class="brand-area" href="P02-dashboard.html">
        <span class="brand-logo" aria-hidden="true"><!-- SVG --></span>
        <span class="brand-name">{系统名称}</span>
      </a>
      <nav id="sidebar-container"></nav>
    </aside>

    <section class="admin-workspace">
      <header class="admin-header">
        <div class="header-main">
          <button class="header-icon-btn" id="sidebar-toggle" type="button" aria-label="折叠菜单">
            <span data-icon="menu" aria-hidden="true"></span>
          </button>
          <div class="header-breadcrumb" id="header-breadcrumb"></div>
          <div class="header-actions">
            <button class="header-icon-btn" type="button" aria-label="搜索">
              <span data-icon="search" aria-hidden="true"></span>
            </button>
            <button class="header-icon-btn msg-badge" type="button" aria-label="消息">
              <span data-icon="bell" aria-hidden="true"></span><span class="dot"></span>
            </button>
            <button class="header-icon-btn" type="button" aria-label="全屏">
              <span data-icon="fullscreen" aria-hidden="true"></span>
            </button>
            <button class="user-trigger" type="button">
              <span>{用户名}</span><span data-icon="chevron-down" aria-hidden="true"></span>
            </button>
          </div>
        </div>
      </header>

      <div class="workspace-tabs">
        <div class="workspace-tabs-list" id="workspace-tabs"></div>
        <button class="workspace-apps-btn" type="button" aria-label="应用入口">
          <span data-icon="grid" aria-hidden="true"></span>
        </button>
      </div>
      <main class="admin-main">
        <div class="page-surface">
          <!-- 页面筛选、指标、表格、表单或图表 -->
        </div>
      </main>
    </section>
  </div>

  <script src="sidebar.js"></script>
</body>
</html>
```

**结构约束：**
- 全局面包屑放在固定顶栏，不在 `.admin-main` 内重复一套面包屑。
- `.brand-area`、`.admin-sidebar` 必须共享 `--sidebar-width`，折叠时同步变化。
- `.admin-workspace` 左边距必须跟随 `--sidebar-width`；禁止使用多个互不一致的硬编码宽度。
- 工作区页签栏属于全局壳层，每个 PC 业务页都应存在；登录页除外。
- 登录页保持全屏居中卡片布局，不使用主框架。

### 3.4 PC端按页面类型的生成规则

#### 列表页
1. 顶栏面包屑 + 工作区页签 → 页面标题/筛选区(横向) → 工具栏 → 数据表格(3-5行) → 分页 → 弹窗

#### 表单页
1. 顶栏面包屑 + 工作区页签 → 页面标题 → 多区块表单(多列布局) → 动态行区域 → 底部操作

#### 详情页
1. 顶栏面包屑 + 工作区页签 → 返回链接+标题+状态+操作 → 概览指标栏 → 多Tab内容区

#### 仪表盘
1. 页面标题+筛选器 → 分组指标卡片 → 图表区 → 风险/待办列表

#### 报表页
1. 页面标题+筛选器 → 统计表格(含多行表头) → 明细弹窗

---

## 四、PC端生成流程

> 以下为本 Skill 从 `generate-html-pages` 总纲流程中抽取的 PC 相关步骤。完整流水线（含端判定、双端对应校验）由总纲协调，本 Skill 聚焦 PC 端产出。

### Step 1：生成 PC 公共文件

按端生成到 `output/site/pc/`：

1. **PC端 common.css**：按 `design-tokens.json` 生成 Token；缺失项使用 PC 端默认 Token（基准见 `references/pc-admin-navigation-style.md`）
2. **PC端 sidebar.js**：根据 `navigation.json` 生成侧边栏配置和渲染函数

> 不再生成 `index.html`。总控台由 `generate-portal` skill 独占输出。

### Step 2：逐页生成 PC HTML

1. 按 `pages.json` 页清单逐页生成 PC HTML
2. PC端按页面类型（列表/表单/详情/仪表盘/报表）选结构
3. 从 `overlays.json` / `actions.json` / `pages.json`（`actionIds`/`applicableStates`）提取字段、筛选、表格列、弹窗、操作，填充示例数据（**不读取 `annotations.json`**，标注仅供 `generate-portal` 展示）
4. 所有跳转链接指向 PC 端内的正确页面文件
5. 按 `permissions.json` 的 `validation` 字段控制字段显隐和操作可用性

**强制约束：** 禁止占位符、必须实现真实交互，详见 §六 9.1 强制约束。

### Step 3：PC 端交叉校验

1. **链接完整性**：所有 href 指向的 PC 页面文件都已生成
2. **端内一致性**：PC 端内的侧栏菜单配置与页面清单一致
3. **状态标签覆盖**：`state-machines.json` 中所有状态枚举值在 PC 端都有对应样式（`.tag-xxx`）
4. **示例数据一致性**：同一页面在 PC 端的示例数据与移动端保持一致（双端输出时）
5. **占位符清零与交互完整性**：详见 §六 9.1 强制约束和 9.7 质量标准

### Step 4：输出构建报告

向 `output/site/build-report.json` 写入 PC 部分（结构见 `../_shared/references/schemas/html-build-report.example.json`），供 `generate-portal` 消费：

- `outputs`：每个 PC 页面文件的 `pageId`、`device: "pc"`、`path`、`contentHash`、`applicableStates`、`annotationMode`
- `checks`：链接完整性、端内一致性、状态覆盖等校验结果
- `unstructuredItems`：从文档兜底提取的字段（`generatedByFallback: true`）
- `openIssues`：未实现的 TODO（HTML 注释形式）、跳过项及原因
- 每个字段记录 `sourceLevel` 和 `sourceRefs`，便于下游溯源

> 双端场景下 build-report.json 由 generate-html-pages 总纲合并 PC/移动两部分；单 PC 场景由本 Skill 直接写入。

---

## 五、PC端质量标准

### 5.1 强制约束与通用性边界（搬入自原 §9.1）

**禁止占位符：**

- 禁用文案包括但不限于："开发中"、"功能开发中"、"敬请期待"、"暂未开放"、"待开发"、"Coming Soon"、"TODO"、"暂未实现"。
- 原型文档中定义的所有交互函数（如 `handleUpload`、`handleSave`、`openDetailModal`、`openEditModal` 等）**必须实现完整的前端交互逻辑**，不得仅弹 Toast 提示"开发中"。
- 若原型文档对某功能的描述模糊或缺细节，应**按本章对应小节的通用模式实现最小可用交互**，而非使用占位符。仍无法实现时，在 HTML 注释 `<!-- TODO: ... -->` 中说明，禁止在用户可见区域展示"开发中"文案。
- 生成每个 HTML 文件后，必须自检该文件中是否存在上述禁用占位符文案；存在则立即修复后再进入下一文件。

**通用性边界（重要）：**

- **仅当原型文档定义了交互函数或操作按钮时，才需要按本章实现交互**。纯展示页面（如关于我们、公司介绍、静态公告）无需强制添加 CRUD 或排序功能。
- 本章的参考代码是**模式片段**，不是可直接复制粘贴的完整实现。生成代码时必须按项目实际的字段名、选择器、弹窗 ID 等替换 `{占位符}`。
- 若项目已有 `common.css` / `sidebar.js` 提供了基础函数（如 `showToast`、`openModal`），页面中**不得重复定义**，直接调用即可。

### 5.2 PC 相关 HTML 编码规范（搬入自原 §9.2）

1. 文件编码：UTF-8（含BOM）
2. 语言：`<html lang="zh-CN">`
3. 缩进：2空格
4. 金额格式：`¥1,234,567.89`，PC端使用 `.amount`
5. 日期格式：`YYYY-MM-DD`
6. 百分比格式：`XX.X%`
7. 自动计算字段：灰色背景只读
8. 必填标记：红色星号 `*`
9. PC端引入 `common.css` + `sidebar.js`
10. viewport：`width=device-width, initial-scale=1, viewport-fit=cover`

### 5.3 PC 质量检查项（从原 §9.7 抽取 PC 相关）

1. **可浏览性**：所有 PC 页面可直接在浏览器打开，布局正确
2. **可导航性**：所有链接可点击跳转，侧栏与工作区页签导航正常
3. **端适配**：PC 端布局符合桌面后台习惯（侧栏+顶栏+页签栏+内容区）
4. **视觉还原**：优先符合用户 UI 规范，并保持 PC Token 一致
5. **数据真实感**：示例数据合理，金额格式正确
6. **交互可用**：弹窗可打开关闭，Tab 可切换，表单可输入
7. **图标一致性**：全项目只使用一套图标体系，不混用 Emoji 和不同图标库
8. **PC壳层一致性**：品牌区、侧栏、顶栏面包屑、工作区页签在所有 PC 业务页保持同一尺寸、层级和交互
9. **资源合规**：分析用截图不进入 Skill 或输出；仅使用项目授权资产、本地 SVG、CSS 图形或中性占位
10. **零占位符**：所有 HTML 文件中不得出现"开发中"、"敬请期待"等占位文案（详见 5.1）
11. **交互可用性**：文件/图片上传可触发文件选择并显示预览或回填文件名；详情/编辑弹窗可打开并填充数据；删除等危险操作有二次确认（详见 §六 9.4~9.6）
12. **图标体系统一**：全项目只使用一套图标体系，优先内联 SVG；禁止混用 Emoji、FontAwesome、Ant Design Icons 等多套图标库；菜单、消息、用户、折叠等图标均使用内联 SVG
13. **viewport 一致**：PC 端使用 `width=device-width, initial-scale=1, viewport-fit=cover`

---

## 六、交互实现模式

> 以下交互场景的完整代码模板和检查点已抽离到 `../generate-html-pages/references/interaction-patterns.md`，本节仅保留索引和强制约束。生成代码时按需读取该文件，并按项目实际字段名、选择器、弹窗 ID 替换 `{占位符}`。

| 小节 | 场景 | interaction-patterns.md 对应章节 | 强制约束摘要 |
|------|------|--------------------------------|------------|
| §1 | Toast / Modal / 确认 / escapeHtml 基础函数 | §1 | 弹窗必须用 `classList` 操作 `.show` 类；**禁止**弹窗 HTML 写 `style="display:none"`；**禁止** JS 直接操作 `style.display` |
| §2 | 文件与图片上传 | §2 | 必须实现文件选择+校验+回填/预览完整逻辑；删除/移除需二次确认；不得仅 Toast |
| §3 | 弹窗与操作（详情/编辑/删除/状态切换/导出） | §3 | 详情/编辑弹窗必须从行读取数据回填；删除等危险操作必须 `confirmAction` 二次确认；禁止直接 `showToast('已删除')` |
| §4 | 列表 CRUD 与排序（卡片/表格变体） | §4 | 必须实现真实 DOM 增删改，禁止仅 Toast；**涉及排序的卡片列表必须用单列横向布局**；**表格必须有独立序号列和排序列**；排序/新增/删除后必须刷新序号 |

**通用性边界：** 仅当原型文档/`actions.json` 定义了交互函数或操作按钮时，才需要按上述模式实现交互。纯展示页面无需强制添加 CRUD 或排序。若项目已有 `common.css` / `sidebar.js` 提供基础函数，页面中**不得重复定义**，直接调用即可。

---

## 七、参考文件使用指引

| 参考文件 | 路径（相对本 Skill 根目录） | 用途 |
|---------|---------------------------|------|
| PC 壳层与导航基准 | `references/pc-admin-navigation-style.md` | PC 端 Token、尺寸、色值、圆角、阴影、DOM 骨架与 sidebar.js 行为的唯一基准 |
| PC 壳层示例 | `references/examples/pc-admin-shell-demo.html` | 检查 PC 壳层（侧栏+顶栏+页签栏+内容区）效果 |
| 交互实现模式 | `../generate-html-pages/references/interaction-patterns.md` | Toast/Modal/上传/弹窗/CRUD/排序的完整代码模板与检查点 |
| PC 后台 UI 规范 | `../_shared/references/pc_admin_ui_spec.md` | PC 管理后台共享 UI 规范（与导航基准对齐） |
| 上游工件结构示例 | `../_shared/references/schemas/` | `pages.json` / `navigation.json` / `annotations.json` 等上游 JSON 工件结构示例 |
| 构建报告结构示例 | `../_shared/references/schemas/html-build-report.example.json` | `output/site/build-report.json` 结构示例 |
| 设计 Token 工件 | `output/spec/design-tokens.json` | 项目 UI Token（优先于默认 Token） |
