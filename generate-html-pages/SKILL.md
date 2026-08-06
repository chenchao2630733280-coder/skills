---
name: "generate-html-pages"
description: "HTML原型生成路由器:判断端类型,调度到PC管理后台(generate-html-pc-admin)或移动端(generate-html-mobile)子skill,并汇总构建报告。不直接持有端专属规范。"
---

# Generate HTML Pages — 多端静态原型生成路由器

本 Skill 是 HTML 原型生成的**统一入口与路由器**。激活后判断端类型(PC/移动/双端),调度到对应子skill生成页面,最后汇总 `build-report.json`。端专属规范(Token、壳层、组件、页面结构、交互模板)由子skill持有,本 Skill 不重复,避免单文件膨胀。

---

## 一、触发条件

当用户提出以下任一需求时激活本路由器:

1. 需要根据设计文档**生成HTML原型页面**(端未明或双端)
2. 需要将PRD/原型文档**转化为可点击的页面原型**
3. 需要为企业管理系统**制作静态演示页面**
4. 用户提供了设计文档,要求输出**可直接浏览的HTML文件**

> 用户明确指定"PC后台"或"移动端"时,可直接激活对应子skill跳过路由。

### 1.1 输入文件

- 系统PRD:定义终端类型、功能、数据和业务规则。
- 页面原型文档:定义页面清单、字段、交互和流转。
- UI设计规范(可选):定义品牌色、字体、间距、圆角及组件样式;存在时优先使用。

---

## 二、输出文件结构

```
output/site/
├── pc/                         # 由 generate-html-pc-admin 生成
│   ├── common.css              # PC端公共样式
│   ├── sidebar.js              # PC端菜单/面包屑/页签/折叠
│   └── PXX-xxx.html            # PC端业务页面
├── mobile/                     # 由 generate-html-mobile 生成
│   ├── common.css              # 移动端公共样式
│   ├── navbar.js               # 移动端导航配置
│   └── PXX-xxx.html            # 移动端业务页面
├── assets/                     # 项目授权图片、图标、字体等共享资产
└── build-report.json           # 由本路由器汇总生成,供 generate-portal 消费
```

> 单端项目省略另一端目录。**总控台 index.html 由 generate-portal 独占生成**,本 Skill 不产出。

---

## 三、端差异总览(路由决策参考)

| 维度 | PC端 | 移动端 |
|------|------|--------|
| 布局 | 侧边栏+顶栏+工作区页签 | 任务原型驱动单列布局,375px基准 |
| 导航 | 可折叠侧边栏菜单 | 顶部导航;PRD定义时生成底部Tab |
| 表格 | 横向数据表格 | 卡片列表;确需对比才用横向表格 |
| 表单 | 多列布局,分区段 | 单列布局,全屏表单页 |
| 详情 | 概览栏+多Tab | 媒体/概览→核心信息→垂直分区 |
| 弹窗 | 居中浮层 | Drawer/底部面板;复杂任务用全屏页 |
| 操作 | 工具栏按钮+操作列 | 明确按钮或底部固定操作 |

完整端差异与组件规范见对应子skill。

### 3.1 UI规范应用原则

1. 用户提供的UI规范优先;未提供时使用子skill默认Token。
2. 只生成当前页面需要的Token和组件样式,不扩写完整设计系统。
3. PC端与移动端共享品牌色和语义色,分别使用对应布局、圆角和背景规则。
4. 全项目只使用一套图标体系(优先内联SVG),禁止混用Emoji、FontAwesome和Ant Design Icons。

---

## 四、子skill路由

### 4.1 路由决策

激活后执行:
1. 读取 `output/spec/pages.json` 的 `devices` 字段,或 PRD 的 `client_type` 判断端
2. 工件和文档均无法判断时询问用户;底部Tab栏不得凭空补齐

### 4.2 路由表

| 端需求 | 调用子skill | 输出目录 |
|--------|------------|---------|
| PC管理后台 | `generate-html-pc-admin` | `output/site/pc/` |
| 移动端 | `generate-html-mobile` | `output/site/mobile/` |
| 双端 | 依次调用两个子skill | 两个目录 |
| 端未明 | 见 §4.1 询问用户后路由 | 按用户确认 |

> 子skill激活后,其SKILL.md提供完整的端专属规范(common.css、壳层、组件、sidebar.js/navbar.js、页面结构、按页面类型/原型的生成规则、端特定质量标准)。本路由器不重复这些内容。

### 4.3 子skill共享资源

| 资源 | 位置 | 说明 |
|------|------|------|
| 交互代码模板 | `references/interaction-patterns.md`(本skill) | 双端通用,子skill通过 `../generate-html-pages/references/` 引用 |
| 共享schema | `../_shared/references/schemas/` | pages/actions/navigation/overlays/components 等 |
| 共享UI规范 | `../_shared/references/` | ui-design-standards.md、pc_admin_ui_spec.md |

---

## 五、总控台 index.html(已剥离)

> **本 Skill 不生成总控台**。`output/site/index.html` 由 `generate-portal` skill 独占生成和维护,消费本 Skill 的 `build-report.json`。需要评审门户时,在本 Skill 完成后调用 `generate-portal`。

---

## 六、信息来源与映射规则

### 6.1 优先级:上游JSON工件 > 文档提取

**必须优先读取上游结构化工件**,文档仅作补充和兜底,避免重复解析和置信度丢失。

| 工件 | 路径 | 生产者 | 用途 |
|------|------|--------|------|
| `pages.json` | `output/spec/pages.json` | generate-system-prd + generate-prototype（富化） | 页面注册表(id/title/devices/archetypeId/applicableStates/actionIds) |
| `navigation.json` | `output/spec/navigation.json` | generate-prototype | 导航结构(PC侧栏、移动端Tab) |
| `actions.json` | `output/spec/actions.json` | generate-prototype | 页面动作 |
| `overlays.json` | `output/spec/overlays.json` | generate-prototype | 弹层 |
| `components.json` | `output/spec/components.json` | generate-prototype | 复用组件 |
| `permissions.json` | `output/spec/permissions.json` | generate-system-prd | 权限 |
| `business-rules.json` | `output/spec/business-rules.json` | generate-system-prd | 业务规则 |
| `state-machines.json` | `output/spec/state-machines.json` | generate-system-prd | 状态机 |
| `design-tokens.json` | `output/spec/design-tokens.json` | generate-prototype（唯一产出者；用户可在原型阶段提供项目 Token 作为输入） | 项目Token；缺失时下游用 `_shared/references/schemas/design-tokens.default.json` 兜底 |
| `pipeline-context.json` | `output/spec/pipeline-context.json` | 各上游skill | 来源置信度 |

> **不消费 `annotations.json`**：本 Skill 不读取、不绑定页面标注（不生成 `data-spec-id`/`data-page-id`）；`output/spec/annotations.json` 由 `generate-prototype` 创建，仅供 `generate-portal` 在门户层读取展示。

> 工件结构示例见 `../_shared/references/schemas/`。工件缺失时回退到PRD/原型文档提取,在 `build-report.json` 标记 `generatedByFallback: true`。

### 6.2 工件到HTML映射

字段级映射规则由子skill按端实现。通用规则:每个字段记录 `sourceLevel`(CONFIRMED/INFERRED/FALLBACK)和 `sourceRefs`,便于下游溯源。

---

## 七、生成流程

### Step 1:确认端需求
1. 从 `pages.json`(`devices`字段)或PRD `client_type` 判断PC/移动/双端
2. 无法判断时询问用户;底部Tab栏不得凭空补齐

### Step 2:读取上游工件
1. 优先读取§6.1上游JSON工件,缺失字段回退到PRD/原型文档/用户UI规范
2. 建立 `pageId → 规格` 映射表,记录 `sourceLevel` 和 `sourceRefs`

### Step 3:调度子skill生成页面
按端需求调用对应子skill:
- **PC端** → 调用 `generate-html-pc-admin`,生成 `output/site/pc/`(common.css、sidebar.js、PXX-xxx.html)
- **移动端** → 调用 `generate-html-mobile`,生成 `output/site/mobile/`(common.css、navbar.js、PXX-xxx.html)
- **双端** → 依次调用两个子skill

子skill负责:公共文件生成、逐页HTML生成(按页面类型/原型)、端内交叉校验。交互实现遵循 `../generate-html-pages/references/interaction-patterns.md`。

### Step 4:跨端校验
1. **双端对应**:同名页面在两端都存在
2. **状态标签覆盖**:`state-machines.json` 枚举值在两端都有对应样式
3. **示例数据一致性**:同一页面双端示例数据一致
4. **占位符清零**:详见§八强制约束

### Step 5:汇总构建报告
生成 `output/site/build-report.json`(结构见 `../_shared/references/schemas/html-build-report.example.json`),供 `generate-portal` 消费:
- `outputs`:合并各子skill产出的页面(`pageId`/`device`/`path`/`contentHash`/`applicableStates`/`annotationMode`)
- `checks`:链接完整性、端内一致性、双端对应、状态覆盖等校验结果
- `unstructuredItems`:文档兜底字段(`generatedByFallback: true`)
- `openIssues`:TODO(HTML注释形式)和跳过项
- 每个字段记录 `sourceLevel` 和 `sourceRefs`

---

## 八、交互与质量规范(通用)

本章为双端通用约束。端专属规范(壳层、组件、页面结构、原型生成规则)见子skill。

### 8.1 强制约束与通用性边界

**禁止占位符:**
- 禁用文案:"开发中""功能开发中""敬请期待""暂未开放""待开发""Coming Soon""TODO""暂未实现"
- 原型文档定义的交互函数(如 `handleUpload`、`handleSave`、`openEditModal`)**必须实现完整前端逻辑**,不得仅Toast"开发中"
- 功能模糊时按 `references/interaction-patterns.md` 通用模式实现最小可用交互;无法实现时用HTML注释 `<!-- TODO: ... -->` 说明,禁止可见区域展示占位文案
- 每个HTML文件生成后自检占位符

**通用性边界:**
- 仅当原型文档/`actions.json` 定义交互函数或操作按钮时才需实现交互。纯展示页面(关于我们、静态公告)无需强制CRUD
- 参考代码是模式片段,需按项目实际字段名、选择器、弹窗ID替换 `{占位符}`
- 若项目已有 `common.css`/`sidebar.js`/`navbar.js` 提供基础函数(如 `showToast`、`openModal`),页面中**不得重复定义**

### 8.2 通用HTML编码规范

1. 文件编码UTF-8(含BOM);`<html lang="zh-CN">`;缩进2空格
2. 金额 `¥1,234,567.89`;日期 `YYYY-MM-DD`;百分比 `XX.X%`
3. 自动计算字段灰色背景只读;必填标记红色星号 `*`
4. PC端引入 `common.css`+`sidebar.js`;移动端引入 `common.css`+`navbar.js`
5. viewport: `width=device-width, initial-scale=1, viewport-fit=cover`;移动端禁止 `maximum-scale=1` 和 `user-scalable=no`
6. 移动端触摸区域≥44×44px
7. 图标:全项目一套SVG体系,禁止Emoji和混用FontAwesome/Ant Design Icons

### 8.3 交互实现模式(代码模板)

> 完整代码模板在 `references/interaction-patterns.md`,双端通用。子skill按需读取并按项目实际字段替换 `{占位符}`。

| 场景 | interaction-patterns.md 章节 | 强制约束摘要 |
|------|------------------------------|------------|
| Toast/Modal/确认/escapeHtml | §1 | 弹窗用 `classList` 操作 `.show` 类;**禁止**弹窗HTML写 `style="display:none"`;**禁止**JS操作 `style.display` |
| 文件与图片上传 | §2 | 完整选择+校验+回填/预览;删除/移除二次确认;不得仅Toast |
| 弹窗与操作(详情/编辑/删除/状态切换/导出) | §3 | 弹窗从行读取数据回填;危险操作 `confirmAction` 二次确认;禁止直接 `showToast('已删除')` |
| 列表CRUD与排序(卡片/表格变体) | §4 | 真实DOM增删改;排序卡片单列横向布局;表格独立序号列和排序列;操作后刷新序号 |

### 8.4 通用质量标准

1. **可浏览性**:页面可直接浏览器打开,布局正确
2. **可导航性**:链接可点击跳转,导航正常
3. **端适配**:双端布局各自符合平台习惯
4. **视觉还原**:符合用户UI规范,双端Token一致
5. **数据真实感**:示例数据合理,金额格式正确
6. **交互可用**:弹窗可开关,Tab可切换,表单可输入
7. **图标一致性**:一套图标体系,不混用
8. **资源合规**:分析截图不进入Skill或输出;仅用授权资产或本地SVG/CSS/中性占位
9. **零占位符**:无"开发中"等文案(详见8.1)
10. **viewport一致**:双端 `viewport-fit=cover`,移动端允许缩放
11. **产物自评**:本 skill 产出后,按 skill-auditor 执行后评测模式自查 build-report.json 字段完整性(可选)

---

## 九、参考文件使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/interaction-patterns.md` | 需要交互代码模板时(双端通用,子skill共享) |
| `../_shared/references/schemas/html-build-report.example.json` | 生成 build-report.json 时 |
| `../_shared/references/schemas/` 下其他示例 | 需要与上游工件对齐字段时 |
| `../generate-html-pc-admin/SKILL.md` | PC端生成规范(由子skill持有,路由后由子skill加载) |
| `../generate-html-mobile/SKILL.md` | 移动端生成规范(由子skill持有,路由后由子skill加载) |
