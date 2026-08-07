---
name: "generate-portal"
description: "Generates the project demo portal (index.html) with three-pane navigation, cross-device iframe preview, and PRD-driven annotations. Use when HTML prototype pages exist under output/site/ and a unified review portal is needed."
---

# generate-portal — 原型演示与标注总控台

你是一名专注于工程化与体验设计的前端架构师，同时具备严谨的产品文档（PRD）编写与需求拆解能力。
我们正在 `output/site/` 目录下构建一个 HTML 原型库。为了方便团队评审，你需要编写一个独立的 **"原型演示与标注总控台" (Demo Portal)**。

- **输出文件**：`output/site/index.html`
- **所有权**：`output/site/index.html` 由本 Skill **独占生成和维护**。`generate-html-pages` 不再生成总控台；若已存在旧版总控台，以本 Skill 输出覆盖。
- **文件要求**：必须是一个**独立**的 HTML 文件（CSS/JS 内联），不依赖任何后端服务。
- **视觉要求**：不强制任何特定 CSS 框架、图标库或固定配色。视觉 Token 遵循 `../_shared/references/ui-design-standards.md` 与项目 `output/spec/design-tokens.json`（存在时优先）；图标使用内联 SVG，禁止混用 Emoji 与多套图标库；默认不依赖外部 CDN。
- **核心功能**：采用**三栏布局**，集成页面导航、Iframe 预览和动态产品标注功能。

## 一、定位与触发条件

当 `output/site/` 下已存在由 `generate-html-pages` 生成的原型页面，需要生成或更新统一评审门户时使用本 Skill。重复执行时应增量更新 `projectMap` 与标注数据，不改变门户的交互结构。

## 二、输入

* `{系统名称}-产品设计方案-V{版本号}.md`（由 `generate-system-prd` 生成，用于读取系统名称、模块结构、页面清单、路由、数据模型与业务规则）
* `{系统名称}-页面原型文档.md`（由 `generate-prototype` 生成，用于读取页面布局、字段、交互、校验、弹窗与页面流转规格）
* `output/spec/annotations.json`（可选，由 `generate-prototype` 创建和维护；存在时作为标注的权威来源）
* `output/site/build-report.json`（可选，由 `generate-html-pages` 生成；存在时作为页面清单、双端对应、TODO 和跳过项的权威来源，避免重复扫描目录）
* `output/site/` 下已生成的页面文件（由 `generate-html-pages` 生成；支持 `pc/*.html`、`mobile/*.html` 或单端根目录 `*.html`，排除 `index.html`）

> 不依赖固定的旧文件名；应以用户实际提供的文件名和现有目录结构为准。`build-report.json` 存在时优先消费其 `outputs` 字段构建 `projectMap`，缺失时回退到目录扫描。

## 三、参考文件使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/annotation-standards.md` | **必读**。定义 `annotations.json` 与门户的映射（含 `pageId` 分组与可选 `selector` 定位）、降级模式与安全规则，优先级高于本文件中的任何视觉描述 |
| `../_shared/references/ui-design-standards.md` | 生成门户视觉样式前读取；项目 Token 优先于该默认值 |
| `../_shared/references/schemas/annotations.example.json` | 需要解析或校验 `annotations.json` 结构时参考 |
| `references/schemas/portal-build-report.example.json` | 需要输出构建报告时参考（本阶段特有） |
| `../_shared/references/schemas/html-build-report.example.json` | 需要解析 `generate-html-pages` 产出的 `build-report.json` 时参考 |
| `../_shared/references/schemas/` 下其他共享示例 | 需要与上游工件（pages/actions/navigation 等）对齐字段时按需参考 |

## 四、标注契约

1. **所有权**：`annotations.json` 由 `generate-prototype` 创建和维护；本 Skill **只读取和展示，不写回标注**。
2. **标注映射**：`annotations.json` 中每个 SXX 标注记录所属 `pageId`（PXX），本 Skill 按 `pageId` 分组并与 `output/site/` 下 `PXX-*.html` 文件匹配。`generate-html-pages` 不绑定 `data-spec-id`/`data-page-id`，DOM 级定位通过 `annotations.json` 中可选的 `selector` 字段在 iframe 内查询（缺失时仅页面级跳转）。缺少标注时门户降级运行，**不得伪造 SXX**。
3. **标注数量与内容**：按真实功能区域生成，不固定为四个；每个标注使用 `display / interaction / data / exceptions` 四个语义维度，只填写适用内容，不适用字段省略或置 `null`，不得填充"无""同上"等模板文字。
4. **降级模式**：
   - 无标注：展示页面与规格说明，隐藏角标或显示"暂无标注"说明；
   - 无 HTML：展示经过清洗的 Markdown 规格，不伪造页面截图或角标；
   - 部分 HTML：已生成页面正常预览，缺失页面显示明确状态；
   - `file://`、跨域或不受信任的 HTML：关闭角标 DOM 定位并明确说明，必要时使用严格 sandbox 隔离预览。
5. **安全**：标注文案、文件路径和 Markdown 必须转义或白名单清洗；不使用未清洗的 `innerHTML` 注入业务内容；不在标注中展示真实敏感数据、密钥或访问令牌。

## 五、布局要求

实现全屏三栏无缝布局（具体尺寸与色值以项目 Token 为准，以下为默认建议）：

### 1. 左侧：导航栏 (Sidebar) - 默认宽度 260px

* **内容**：
  * 顶部：项目标题（使用系统名称）。
  * 列表：按"端"和"模块"分组的折叠菜单（动态生成）。
* **交互**：点击菜单项时，高亮当前项，并触发中间预览区和右侧标注区的状态更新。

### 2. 中间：预览区 (Viewport) - 自适应宽度

* **顶部工具栏**：
  * 显示当前正在预览的页面标题和相对路径。
  * **设备切换器**：提供 [ 手机 ] / [ PC ] 切换按钮（使用内联 SVG 图标）。
* **Iframe 容器**：
  * `<iframe id="preview-frame">` 用于加载目标页面。
  * **手机模式**：iframe 尺寸强制为 `375px * 812px`，居中显示，带有类似手机的阴影或边框。
  * **PC 模式**：iframe 尺寸铺满 `100% * 100%`。

### 3. 右侧：标注面板 (Specs Panel) - 默认宽度 340px

* **头部**：固定标题 "开发标注 (Dev Specs)"。
* **内容区**：根据左侧选中的页面，动态渲染对应的标注内容（严格遵循下方的"标注撰写规范"）。
* 角标与右侧标注支持双向定位和键盘访问；角标不得遮挡关键文字，密集区域可使用引线或包含框。

---

## 六、生成流程

### 1. 动态目录结构构建 (Dynamic Directory Construction)

读取产品设计方案中的"功能模块清单/页面清单与路由"和页面原型文档中的"页面总览"，并结合 `output/site/` 下实际存在的 HTML 页面路径，转换为前端 JS 内部的 JSON 数据源 (`projectMap`)。

* **优先消费构建报告**：`output/site/build-report.json` 存在时，优先从其 `outputs` 字段（含 `pageId`/`device`/`path`/`applicableStates`）构建 `projectMap`，避免重复扫描目录；缺失时回退到目录扫描。
* **数据结构要求**：按"业务模块 → 页面"组织；同一页面可同时包含 `pcFile` 和 `mobileFile`。
* **端侧标识**：路径位于 `pc/` 时标记为 "PC"，位于 `mobile/` 时标记为 "Mobile"；单端页面位于 `output/site/` 根目录时，根据用户的端需求和原型文档判断。
* **路径约束**：只写入实际存在的 HTML 相对路径，排除 `output/site/index.html`，不得虚构页面文件。
* **名称映射**：优先使用页面编号（如 `P01`）匹配产品设计方案、页面原型文档和 HTML 文件；编号缺失时再使用页面名称与文件名匹配。

### 2. 基于 PRD 映射的精准标注 (PRD-Mapped Annotation Strategy)

在生成每个页面对象中的标注数据时，**严禁**使用通用的"列表/表单"占位符。必须执行以下映射逻辑：

1. **识别页面**：从 HTML 文件名提取页面编号（如 `P03`），并与产品设计方案的"页面清单与路由"及页面原型文档的"页面总览/各页面规格"建立映射。
2. **检索逻辑**：以页面编号为主键，读取该页面在两份文档中的字段来源、业务规则、交互、校验、状态、异常与跳转信息；不得仅凭文件夹名称猜测。
3. **标注来源**：`output/spec/annotations.json` 存在时以它为权威来源直接渲染；不存在时才根据文档生成内联标注，并在门户中注明"标注来自文档解析，未经过原型阶段声明"。
4. **生成内容**：标注必须反映该页面的特定业务细节；文档未提供的信息应明确标注"文档未定义"，不得编造通用占位规则。

### 3. 状态联动 (State Linkage)

* 点击左侧菜单 ->
* (1) 中间 Iframe 加载目标页面路径。
* (2) **自动视图切换**：目标路径位于 `mobile/` 时切为手机视图，位于 `pc/` 时切为 PC 视图；根目录单端页面使用其在 `projectMap` 中声明的端类型。
* (3) 右侧渲染对应的标注数据；若 `annotations.json` 中该标注含 `selector` 字段，在 iframe 内定位元素并叠加角标，否则仅页面级展示。

---

## 七、标注撰写规范

撰写标注内容时，按以下**四个语义维度**组织，只填写适用维度，避免开发与测试遗漏：

### 维度 1: 展示逻辑 (display)

*描述"页面加载出来时"用户看到的内容及其来源。*

* **字段来源**：读取自哪个后台模块/表？或是前端写死？
* **默认状态**：初始选中的选项？开关默认状态？默认提示语（Placeholder）？
* **显示格式**：文本截断（省略号/换行/展开收起）？数值处理（千分位、保留小数）？时间格式？脱敏处理（138****1234）？
* **条件显隐**：什么情况下隐藏？什么情况下置灰不可点？

### 维度 2: 交互逻辑 (interaction)

*描述"用户操作后"系统发生的反应。*

* **触发方式**：单击、双击、长按、滑动、下拉刷新。
* **跳转与反馈**：打开新页面？唤起 Toast/Modal/ActionSheet？按钮文字变化（"关注"变"已关注"）？Loading 动画？
* **前置校验**：执行操作前是否校验登录状态或表单必填项？

### 维度 3: 数据规则与极值 (data)

* **排序规则**：创建时间倒序？销量高到低？置顶逻辑？
* **分页/加载**：一次性加载还是分页加载？每页多少条 (Pagesize)？
* **极限情况**：输入最大字数？最多添加几个标签/商品？
* **空状态 (Empty State)**：列表无数据时显示什么（缺省图+文案）？部分字段为空时显示什么（隐藏还是显示"--"）？

### 维度 4: 特殊场景 (exceptions)

* **网络/缓存/账号**：网络失败重试机制？数据本地缓存策略？VIP vs 普通用户视图差异？

### 📌 标注案例参考：

> **预订须知模块**
>
> * **展示**：读取后台【产品库】-【预订规则】字段；富文本前端解析；配置 N>0 时显示"提前 N 天购票"。
> * **交互**：默认展示前 3 行。点击"展开"向下推开展示全部；点击"收起"恢复默认。
> * **数据**：固定日期类型显示 `YYYY.MM.DD 至 YYYY.MM.DD`。
> * **异常**：若未配置则前端直接隐藏；"随时退"与"不可退"冲突时优先展示"不可退"。

---

## 八、标注渲染结构

每个标注逻辑点渲染为语义化 HTML 结构，包含：序号角标、模块名标题，以及按 `展示 / 交互 / 数据 / 异常` 分行的内容区。具体要求：

1. 使用语义化标签（`<section>`、`<h4>`、`<p>`），样式类名与颜色值来自项目 Token，不硬编码特定框架的配色类。
2. 异常维度使用可区分但不过度依赖颜色的表达（图标 + 文字），图标使用内联 SVG。
3. 所有动态文本通过 `textContent` 或经白名单清洗后注入，遵循"标注契约"第 5 条安全规则。

---

## 九、行动指令

当收到执行该 Skill 的命令时：

1. 先读取 `references/annotation-standards.md`，再按 Inputs 读取上游文档与 `output/site/` 目录。
2. 输出 `output/site/index.html` 的完整源代码：完整的 HTML5 结构、内联 CSS（Token 化）、内联 JavaScript 逻辑、内联 SVG 图标。
3. 代码中硬编码一份基于上下文自动生成的 `projectMap` 数据作为演示和测试基础；`projectMap` 中的页面路径必须是 `output/site/` 下真实存在的文件，标注内容必须以特定 PRD 逻辑书写，不得虚构页面或占位规则。
