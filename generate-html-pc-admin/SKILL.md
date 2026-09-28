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
- `.admin-workspace` 必须具备 `padding-top: var(--header-height)`。原因：`.workspace-tabs` 是 `position: sticky; top: var(--header-height)`，若父容器不为固定顶栏留出 padding，页签栏粘住时会被下推到顶栏之下，而它在文本流中仍只占 0~50px —— 于是 `.admin-main`（首元素通常是筛选卡）从 y≈50 开始排版，顶部约 60px 被「固定顶栏 + 粘住的页签栏」压住，表现为**查询筛选区被遮挡**。这是最容易复现、也最容易被误判为「筛选卡样式问题」的布局缺陷。
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

**强制约束：** 禁止占位符、必须实现真实交互，详见 §五 5.1 强制约束。

### Step 3：PC 端交叉校验

1. **链接完整性**：所有 href 指向的 PC 页面文件都已生成
2. **端内一致性**：PC 端内的侧栏菜单配置与页面清单一致
3. **状态标签覆盖**：`state-machines.json` 中所有状态枚举值在 PC 端都有对应样式（`.tag-xxx`）
4. **示例数据一致性**：同一页面在 PC 端的示例数据与移动端保持一致（双端输出时）
5. **占位符清零与交互完整性**：详见 §五 5.1 强制约束和 5.3 质量检查项

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
11. **BOM 易失，写回后必须复核**：部分文件写入工具（含 Agent 的 Edit/Write）会静默丢弃 BOM。凡改动过 HTML/CSS/JS，交付前应校验首字节为 `EF BB BF` 并补回；换行统一 LF，禁止 CRLF 混入。`common.css` / `sidebar.js` 这类共享文件同样要求 BOM。
12. **`contentHash` 算法**：`sha256( 去掉 BOM 后按 UTF-8 解码得到的文本再按 UTF-8 编码 )`，即与原始文件字节无关。推论：补/去 BOM 不改变哈希，但**换行符变化会改变哈希**；重算哈希时不要直接对原始字节做 sha256。
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
11. **交互可用性**：文件/图片上传可触发文件选择并显示预览或回填文件名；详情/编辑弹窗可打开并填充数据；删除等危险操作有二次确认（详见 §六 交互实现模式）
12. **图标体系统一**：全项目只使用一套图标体系，优先内联 SVG；禁止混用 Emoji、FontAwesome、Ant Design Icons 等多套图标库；菜单、消息、用户、折叠等图标均使用内联 SVG
13. **viewport 一致**：PC 端使用 `width=device-width, initial-scale=1, viewport-fit=cover`

### 5.4 增量改造与批量补丁的校验流水线（V1.x 迭代必用）

项目进入 V1.x 迭代后，改动应以**块替换**推进，不要整文件重写；每批改造后跑同一套校验，避免「修订说明写了、正文没落」的自伤。

**1. 块替换 + 断言**

- 每个待替换片段先断言 `text.count(old) == 1`，命中数不符即记为 MISS、跳过该项，最后输出 MISS 清单人工复核。禁止用正则模糊匹配改结构（会误伤同类行），正则只用于**校验**阶段计数。
- 同一片段多处出现时，用相邻唯一字段扩上下文保证唯一（如手机号、时间戳、role 值、`data-*` 属性）。
- **`region` 整体替换与片段的细粒度 `rep()` 不可作用于同一片段**：先按「起止锚点」整体替换了某函数体，再对其内部字符串做替换 → 前者已改写、后者永远 0 命中，产生**假 MISS**。划定改造区时二选一：要么整块 region 替换，要么逐片段 rep，不要混用。
- `rep_region(text, start, end, new_body)` 的实现要点：`start`/`end` 必须是该片段**首尾**的唯一锚点，且 `new_body` **自身要包含** `end` 文本（因为实现是 `text[:i] + new_body + text[j+len(end):]`），否则锚点被吃掉、后续替换连带失效。

**2. 内联脚本语法校验**

- 逐条 `node --check` 需贴临时文件且慢；改为**单个 Node 进程**内用 `vm.Script` 编译全部页面内联脚本。抽取正则：`/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g`，失败时输出 `文件#序号 + 错误信息`。

**3. 纯数据模块可脱离浏览器断言**

- 抽到 `pc/<domain>.js` 的无 DOM 依赖模块，可在 Node 中用 `vm.runInContext(src, { window: {} })` 加载，直接对派生逻辑做真值断言（路径推导、防环、上限拦截、完整性统计）。这是无浏览器环境下最有效的验证手段。
- 断言要核对**语义方向**：形如 `canBeParentOf(parentId, selfId)` 的命名容易把期望值写反；断言失败先复核参数语义，再改实现。
- **区分「定义」与「导出」**：`var DeptTree = {…}` + `window.DeptTree = DeptTree;` 是 **定义 1 次 + 导出 1 次**，用 `\bDeptTree\s*=` 计数会得到 2 而误报「重复定义」。断言应写作 `(?:var|let|const)\s+DeptTree\s*=` 计数 == 1 且 `window\.DeptTree\s*=\s*DeptTree` 计数 == 1。

**4. 表格列数自洽须剔除 `<script>` 段**

- 行由 JS 模板串注入的表格（`tbody` 为空、行由 `rowHtml()` 拼接）不能只数静态 `<tr>`；须同时断言 `rowHtml` 中单元格片段数 == 表头 `<th>` 数。

**5. 改页面后的同步清单**

| 工件 | 需同步字段 |
|------|-----------|
| `output/spec/pages.json` | `pages` 新增条目；`navigation.<端>.modules[].pageIds` 与菜单顺序一致；`openVerifications` 编号；决策记录中已过期口径 |
| `output/spec/annotations.json` | 新功能对应的 `specs[]` 条目（`id` 全局唯一，新号顺延）；消费页 `pageId` 条目；`updatedBy` 追加批次标记；`sourceRefs` 上游文档**升到最新版本号**；新增 `spec id` 必须被 `pages.json` 的 `specIds` 引用（双向闭合断言） |
| `output/site/build-report.json` | `site.<端>.pages` 页数；`site.pc.shared` 共享文件清单；`outputs` 条目；**改动过的每个 HTML 都要重算 `contentHash`**；`checks[].detail` 中**硬编码的计数**（「N 个 HTML」「N 段内联 script」「N 个部门维度页面」）；`openIssues` 新增编号 |
| `output/site/pc/sidebar.js` | 菜单二级项（顺序需与 pages.json 的 `pageIds` 一致） |
| 方案 / 改造文档 | 执行批次状态表；存量缺陷清单（新发现即登记编号）；**收口时把状态行改为「✅ 全部批次已执行完成」、基线版本号与页数升到最新、并把验收结论表落进文档** |
| 页面原型文档 | 文档版本号；最近修订；上游依据版本；页面总览表的**行与计数**；对应章节的字段 / 筛选 / 标注表；板块 C 组件表；板块 E 流转与数据流向 |

**6. 开放验证编号以最新 PRD 为准**

- spec 工件与最新一版 PRD 出现 `PV-xx` 同号不同义时，**以 PRD 为准**：把 spec 中的旧项顺延为新号，并同步所有引用该号的 `checks` / `openIssues` 文案。

**7. 共享脚本单一真源**

- 跨页共用的业务数据或组件（如部门树）抽到 `pc/<domain>.js`，与 `common.css` / `sidebar.js` 同层级；由 owner 页与消费页共同引入，且**必须在 `sidebar.js` 之前**引入（共享模块在运行期调用 `sidebar.js` 挂载的 `showToast` / `svgIcon` / `escapeHtml`）。
- 数据只定义一次，消费页不得硬编码副本；新增共享文件后同步 `build-report.json` 的 `site.pc.shared`。

**8. 字段命名分层是本项目既定约定（断言口径必须跟着分层走）**

| 层 | 命名风格 | 示例 |
|---|---|---|
| PRD / `pages.json` / PRD 数据表 | `snake_case` | `match_dim` / `dept_scope` / `submitter_ids` |
| 页面 JS 数据层（对象键、变量） | `camelCase` | `matchDim` / `deptScope` / `submitters` |
| 列表行内承载（`data-*`） | `kebab-case` | `data-match-dim` / `data-dept-scope` |

- **禁止拿 `snake_case` 去 grep 页面 HTML 做存在性断言**：它可能只出现在注释里（注释里写「snake_case ↔ camelCase 映射」是推荐做法），会让断言**假通过**。
- 断言应指向该层真实承载：数据层查 `camelCase` 键或 `data-*` 属性；跨页字段可追溯性则断言**映射注释**是否存在。
- 同一页面同时出现驼峰与蛇形时，蛇形应**只在注释**，用于标注与上游字段的对应关系。

**9. 文案断言以页面实际字面为准**

- spec / report / 校验脚本中的文案必须与页面**逐字一致**：常见偏差如「末级会签」vs 页面「末级**允许**会签」、「按指定人」vs 页面「按指定**提报人**」。写断言前先 `grep` 页面取真实字面，别凭记忆或凭设计稿措辞。

**10. `annotations.json` 的 `selector` 是逻辑名，不是真实 DOM 类**

- 该工件的 `selector`（如 `.slot-list__sold-mode`）属**规划层命名**，由 `generate-portal` 的注释层解析，通常在页面 HTML 中并不存在对应 class。**不要**把它当作「选择器失效」来修，也不要用它做回归判据。
- 判断是否回归的正确姿势：看该批改动**是否触碰了对应页面**；未触碰页面出现同类现象即为历史既定形态。

**11. 批次收口校验脚本（建议固化为 `.<batch>_verify.py`）**

每批改造执行完毕后，跑一套**全站级**校验并把结果落日志（`.log_<batch>_verify.txt`）。建议 8 组：

1. **编码与换行**：`output/**` 全量 `.html/.css/.js/.json/.md` 必须 UTF-8 with BOM + LF（BOM 缺失 / 出现 CRLF 即 FAIL）。
2. **JSON 可解析**：`pages.json` / `build-report.json` / `annotations.json` / `design-tokens.json` 一律用 **`utf-8-sig`** 读（带 BOM 时 `utf-8` 会抛 `Unexpected UTF-8 BOM`）。
3. **contentHash 一致性**：遍历 `build-report.outputs[]`，按 `sha256(去 BOM 后的 UTF-8 文本)` 重算并逐条比对，捕捉「改了页面忘了 rehash」。
4. **跨页链接完整性**：抽取全部 `href="*.html"` / `location.href='*.html'`，校验目标文件存在。
5. **禁用词 / 旧枚举全站复扫**：把本批要消灭的旧口径（旧枚举、旧字段名、stub 文案、占位文案）列成 `BAN` 表，按 `词 → 原因` 输出命中文件与次数；同时断言新权威枚举在目标页**命中率**（如 `T18` 五枚举 5/5）。
   - **扫描必须带上下文白名单**：文档里「**禁止出现**「未命中按免审处理」的表述」是**合规写法**，简单 `in` 判断会把合规文案误报为违规；命中后要回看邻近 120 字，含「禁止 / 不得 / 不应」则放行（PRD 侧）；而纯页面（P32/P33 等）应**直接禁**，不给白名单。
   - **警惕同形异义词**：原型文档的「插播**免审批**」（BR-029，插播不建审核任务）与「未命中按**免审**处理」（X1 违规口径）字形相近但语义无关，**不可一并禁**，`BAN` 表要写全词而非半词。
6. **表格列数自洽**（剔除 `<script>` 段）；行由 JS 注入的表格需另按 §5.4-4 断言模板片段数。
   - **同一校验要覆盖文档侧的 markdown 表格**：`.md` 表格表头少一列（如方案文档表头 4 列 / 数据行 5 列）在页面上无影响、但渲染会错位，属静默漏列。做法：找「`|` 行 + 紧随 `|[\s:|-]+|` 分隔行」为表头，逐个数据行比对 `|` 数量。本项目基线：PRD 92 个 / 改造方案 22 个 / 原型文档 110 个表格，全部列数自洽。
7. **共享脚本引入顺序**：共享模块页必须早于 `sidebar.js`。
8. **单一真源**：共享数据只定义一次 + 无副本（注意 §5.4-3 的「定义 / 导出」区分）。

最后再叠加两项既有校验：`vm.Script` 编译全部内联脚本（段数需与 `build-report` 的「N 段」文案一致）、纯数据模块的 `vm.runInContext` 真值断言。

**12. 标签必须以字典为唯一权威（词序变体是最隐蔽的不一致）**

- 状态 / 档位 / 匹配方式的展示文案，若页面内已有字典（`TIER_TEXT` / `MATCH_DIM_TEXT` / `ATYPE_TEXT` / 状态映射表），则**正文与提示文案必须与字典值逐字一致**。
- 典型隐蔽偏差：字典 `TIER_TEXT.EXACT = '① 精确部门'`，而顶部提示写「① 按部门精确」—— 肉眼读着都对，但**词序不一**已违反「字典为唯一权威」。新增文案后应**反向 grep 字典值**，并顺手把变体列入 `BAN` 表。
- 断言写法：`assert '按部门精确' not in page`（禁变体）+ `assert page.count('精确部门') == 期望值`（正例计数），两者配合才能同时防「漏」与「变异」。

**13. 改造方案的「验收清单」要固化为独立闸门脚本**

- 方案 / 改造文档末尾常有一张「验收清单」（如 13 条），它是**承诺**；若不落成脚本，收口时只能靠人肉回忆。做法：`.<plan>_acceptance.py` 按条逐项断言，输出 `FAILS` 计数并以 `exit(1)` 阻断。
- **验收条目的措辞常是概述，与实物字面不同**（如清单写「仅用于个别例外」提示，实物是「按人例外档只承载个别约定」）——断言要指向**实物字面或等价语义**，并在脚本注释里记录这个映射，避免后人照抄清单措辞写出假 FAIL。
- 闸门脚本与收口脚本**分开**：收口校验（8~13 组）保证工程合规，验收清单保证**需求承诺兑现**，两者都要跑。
- **遇 FAIL 先回读实物原文，再改断言**：本类项目已多次出现「产物正确、断言写错」（正则把「按部门精确」当成「精确部门」、把 `deptId:` 引用型字段当成部门节点计数）。改断言前务必确认实物。

**14. 主数据置换作业流程（换部门 / 换资源位 / 换人员名册等「一改全动」类改动）**

主数据被消费在多处，替换不是「改一个数组」，而是**一条链**。固定七步：

1. **先分类，再替换 —— 分辨「实体名」与「模块名 / 角色名」**
   - 同一个词可能既是主数据实体又是 UI 模块名。典型：`审核中心` 在本项目既是部门实体，又是左侧菜单模块名（`sidebar.js` 的模块、各页 `breadcrumbs`、`pages.json` 的 `moduleId`、原型文档「模块四：」）——**后者必须保护**，不能跟着替换。
   - 同理，角色名（`ROLE_MEMBERS` 里的业务职能名）与部门名是**两个命名空间**，换部门时**不动角色**。
   - 做法：替换前先跑一遍「名词 → 出现文件 × 次数」分布扫描，人工给每个文件打标（实体 / 模块 / 无关）。
2. **设计新数据（层级、编码、负责人、演示态）**，用 `AskUserQuestion` 确认不可推断项（如用户只给扁平名单时，树的层级编组方式、白名单归属、是否保留「停用 / 缺负责人」演示样本）。
3. **写块替换补丁脚本，先 `--dry` 统计命中数，再实跑**（见下「三个必备技巧」）。
4. **残留复扫**：把旧实体名整表列成 `OLD` 表，遍历 `output/**`（含 `docs/`）复扫，要求 0 命中；并复扫外观可见字面（列表单元格文案、`placeholder`、JS 注释里的举例、`data-name` 可见单元）。
5. **自洽性回归（最易漏、最致命）**：主数据之间存在**约束关系**，换了 A 必须同步 B。例：排期单的「申请部门」必须落在其明细资源位对应白名单内 —— 若把某单申请部门映射到一个不在白名单的部门，页面数据就自相矛盾。做法：把「跨页一致的单号 / 主键 → 应有归属」列成断言表，逐条校验。
6. **`contentHash` 全量重算 + 复核**（见 §5.4-3）。
7. **跑三支闸门**：收口校验 + 验收清单 + 主数据专项校验（新建 `.<domain>_swap.py`，断言「旧名零残留 / 新名齐备 / 树形与演示态 / 约束自洽 / 消费页单一真源」）。

**替换脚本三个必备技巧**

- **数值型 id 映射必须单趟正则替换**：顺序 `str.replace` 会链式碰撞（`2→5` 之后再 `5→3`，会把刚写入的 5 也改掉）。用 `re.sub` + dict 在**一趟**内完成。
- **同文案多行按出现顺序替换**：多条数据行文案完全相同时（如两条待办都写「申请部门：运营中心」），只能用「第 N 次出现」分别落位，或用更大的唯一上下文包住整行。
- **命中数不确定就先 dry-run 打印真实计数**，再据此写 `expect` 断言；不要凭猜测写死计数（本项目 dry-run 曾抓出「预置 2 处、实际 1 处」）。

**注意层级深度会限制演示能力**：若原型演示依赖「N 级上溯」，把主数据树压浅后**原先的深层示例会不可达**（例：3 级树里 L3 只能上溯到 L2，`上溯 2 级` 示例失效）。替换时要回读依赖深度的演示文案，改成可达的等价案例并留痕，或补足层级。

**15. 层级调整作业流程（上提 / 平级 / 下沉 / 改父节点 —— 比「改名」更容易漏）**

改名可以用「旧名整表 + 全站 grep 零残留」兜住，**改层级兜不住**：部门名一个字没变，但路径字符串、派生集合全变了，旧名扫描 0 命中却仍有 7 处不一致。因此改层级要单独走一遍：

1. **一级只改 `parentId`，`path` / `level` 交给派生的 `rebuild()`**，不要手写路径。
2. **反查「全路径字符串」**：列表页/详情页的 `title="集团总部 / A / B"` Tooltip 是**拼接出来的路径文本**，按旧部门名 grep 不到。做法：扫 `集团总部 / ` 前缀，或扫 `/ ` 分割层数是否与 `level` 相符。
3. **检查 `include_sub` 类白名单 / 范围的展开集变化**：子节点被上提后自动**退出**上级的展开集，同时新子节点**进入**。改完必须回读展开结果（如「仅 [A, B] → [A, C, D]」），这是最容易静默漂移的一处。
4. **检查 `refFlow` 之类的「被引用」标记**：新落入某范围 `includeSub` 内的节点应置位，否则「缺负责人告警」等完整性校验会漏报。
5. **检查范围锚点式演示是否还可达**：审核流 / 规则以某部门为范围锚点时，该部门若被上提或下沉，「精确命中」与「上溯命中」两档演示可能一个变成另一个、或直接失效。**保持「有子部门的锚点」才能同时演示两档**；锚点若变成叶子节点，就得换锚点或补子部门。
6. **同步改了流 / 规则的「演示数据行」**：流定义改完只算一半 —— 命中校验表、裁决表（`CONFLICT_ROWS` / `CONFLICT_DECIDE_ROWS` 之类）里把它们当字面量又写了一遍，必须一并改，否则留下自相矛盾的演示表。
7. **同步「数量口径」的每一处字面量**：报告文件里的「N 个部门 / M 级层级」、工具栏 `<span id="...">共 N 个</span>` 静态占位（运行时会重算，但静态串也要改，闸门需单独断言）。
8. **顺手检查跨页编码命名空间**：同类实体（如审核流）在多页各有一份编号表时，容易出现「同码不同义」的历史漂移。改主数据是发现它的好时机 —— **先确认哪一页是权威（通常是配置主页面），把其余页对齐**；若成本较高则**明确记为待办，不要半改**。

**块替换的 new 串不要带行首缩进**：region 定位到 `var X = [` 这类 token 时，行首原有缩进仍留在 `t[:i]` 里；new 串若再以缩进开头，结果就会多缩一级。new 串应从被定位的 token 本身开始写。

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
