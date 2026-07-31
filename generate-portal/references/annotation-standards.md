# 原型门户标注规范

本规范定义 `annotations.json` 与评审门户之间的稳定映射。`generate-html-pages` 不生成、不绑定任何标注属性（`data-spec-id`/`data-page-id`），标注的读取、定位与展示全部由 `generate-portal` 在门户层完成。本规范不规定 Tailwind、FontAwesome、固定蓝色或任何项目专属视觉。

## 1. 所有权

- `annotations.json` 由 `generate-prototype` 创建和维护。
- `generate-html-pages` 不读取、不绑定标注（不生成 `data-spec-id`/`data-page-id`），只产出纯静态页面。
- `generate-portal` 读取 `annotations.json` 与 `output/site/` 下 HTML，在门户层完成标注分组、定位与展示；不写回标注。
- 缺少标注时允许 HTML 和门户降级运行，不得伪造 `SXX`。

## 2. 标注数量

- 标注按真实功能区域生成，不固定为四个，也不要求所有页面数量一致。
- 简单组件可只有 1 个标注；复杂页面可有多个。
- 不为纯装饰元素、每个按钮或每个字段机械生成标注。

## 3. 标注内容

每个标注使用四个语义维度，但只填写适用内容：

1. `display`：来源、默认值、格式、显示/隐藏条件；
2. `interaction`：触发、结果、校验和反馈；
3. `data`：适用的排序、分页、限制、空值和一致性规则；
4. `exceptions`：页面特有的异常、权限、并发和降级。

不适用字段省略或使用 `null`，不得填充“无”“同上”等模板文字。通用状态和反馈通过继承引用，不在每个标注重复。

## 4. 门户映射

- `annotations.json` 中每个 SXX 标注必须记录所属页面 `pageId`（PXX），门户按 `pageId` 对标注分组并与 `output/site/` 下 HTML 文件（`PXX-*.html`）匹配。
- 标注的 DOM 级定位由 `generate-portal` 在门户层完成（可选增强）：通过 `annotations.json` 中可选的 `selector` 字段（CSS 选择器）在 iframe 内查询元素并叠加高亮/角标；`selector` 缺失时标注仅按页面级展示（点击标注跳转到对应页面，不做 DOM 精确定位）。
- `annotations.json` 已声明 SXX 但对应 HTML 文件缺失时为 `WARN`（页面级孤立），不阻断构建。
- 无 `annotations.json` 时，门户降级为无标注模式（仅预览页面，隐藏标注面板），不得伪造 SXX。
- 因 `generate-html-pages` 不绑定 `data-spec-id`/`data-page-id`，门户不得依赖这些属性存在；页面识别通过文件名（`PXX-*.html`）完成。

## 5. 门户定位

- 同源且受信任的 HTML 可通过 `getBoundingClientRect()` 动态定位角标。
- `file://`、跨域或不受信任 HTML 无法安全访问 DOM 时，关闭角标定位并明确说明。
- 角标不得遮挡关键文字；密集区域可使用引线或包含框。
- 角标与右侧标注支持双向定位和键盘访问。

## 6. 降级模式

- 无标注：展示页面/规格，隐藏角标和右侧标注区或显示不可用说明。
- 无 HTML：展示经过清洗的 Markdown 规格，不伪造页面截图或角标。
- 部分 HTML：已生成页面正常预览，缺失页面显示明确状态。
- 不受信任 HTML：使用严格 sandbox，仅隔离预览，不读取 DOM、不执行非必要脚本。

## 7. 安全

- 标注文案、文件路径和 Markdown 必须转义或白名单清洗。
- 不使用未清洗的 `innerHTML` 注入业务内容。
- 不在标注中展示真实敏感数据、密钥或访问令牌。
