# 移动端主题 Profile 与密度映射

> 本文件从 App AI UI Design System v2.0-v2.3 的 Theme Profile 章节蒸馏而来（蒸馏自 App AI UI Design System v2.0-v2.3），定义 generate-html-mobile 在**缺少项目级视觉输入时的主题气质启发式与密度建议**。
>
> **定位声明**：主题 Profile 是**优先级最低的视觉兜底**，只回答"这个业务形态适合什么视觉气质"，不携带任何业务内容。业务流程、字段、状态、角色一律以上游 PRD 与 JSON 工件为准；领域建模知识已沉淀于 `generate-system-prd/references/business-domain-patterns.md`。

---

## 一、业务形态识别输入

主题判断的输入**全部来自工件与文档结构**，不依赖本 skill 内置的业务知识：

| 判断输入 | 来源 | 示例特征 |
|---------|------|---------|
| 产品定位 | PRD 产品定位章节 / `pipeline-context.json` | "保险专区"、"宠物生活服务"、"预约挂号" |
| 页面结构 | `pages.json`（archetypeId 分布） | 交易类页面占比高 → 偏专业紧凑；内容发现页占比高 → 偏舒展 |
| 状态机结构 | `state-machines.json` | 存在支付/核保状态机 → 高信任形态；存在号源锁定 → 资源预约形态 |
| 项目 Token | `design-tokens.json` | **存在即直接使用，跳过主题启发式** |

识别结论记入页面设计决策，并在 `build-report.json` 的 `sourceRefs` 中注明来源。

---

## 二、主题 Profile 表

| 主题 | 关键词 | 密度建议 | 典型形态特征（来自工件结构） |
|------|--------|---------|------------------------------|
| City / Lifestyle 城市生活 | 自然、亲和、清新、生活化、可信 | standard | 综合入口 + 服务宫格 + 缴费/出行/社区模块 |
| Commerce 电商 | 商品、转化、价格、促销、视觉刺激 | standard | 分类检索 + 商品卡 + 购物车 + 促销标签 |
| Insurance / Finance 保险金融 | 专业、可信、稳健、安全、透明、可解释 | compact | 核保/支付/保单状态机 + 资格核验 + 长协议 |
| Family Insurance 家庭保险 | 温和、可信、关系 | compact | 被保人多人选择 + 授权状态机 + 关系角色 |
| Healthcare 医疗 | 专业、安全、舒缓、可读 | compact（内容/关怀页 comfortable） | 号源/预约/排队状态机 + 报告实体 |
| Government / Public Service 政务 | 规范、可信、清晰、正式、高可读 | compact | 办事指南 + 表单办理 + 公共账户 |
| Enterprise 企业服务 | 效率、准确、密度、状态、权限 | compact | 工单/审批流 + 状态标签 + 筛选列表 |
| Content / Social 内容社区 | 内容、图片、互动、阅读、情绪 | comfortable | 内容发现首页 + 图文流 + 评论互动 |
| Pet 宠物生活 | 温暖、陪伴、生命力、亲近、轻松、活泼 | standard | 宠物档案实体 + 服务预约 + 领养 + 内容流 |
| Travel / Map 出行地图 | 空间、位置、实时、状态、导航 | standard | 定位 + POI + 实时信息列表 |
| Productivity 工具效率 | 极简、效率、操作、快捷 | standard | 强操作 + 强状态 + 少装饰 |

---

## 三、四个主题的 `--m-*` 覆盖值示例

以下仅为**无项目 Token 时的兜底示例**。只覆盖 `--m-*` 变量的值，不新增变量名、不改变命名空间。双端场景必须经 `design-tokens.json` 统一下发（见 §五）。

### 3.1 Insurance / Finance（专业深蓝）

```css
:root {
  --m-primary: #2768D9;        /* 深蓝，专业稳健 */
  --m-primary-hover: #3F8CFF;
  --m-primary-soft: #E9F0FB;
  --m-bg: #F4F6F9;
  --m-text-primary: #1A2433;
}
```

禁忌（高信任形态通用）：大面积强渐变、过多彩色入口、促销式 Banner 压过保障内容。

### 3.2 Healthcare（公共卫生蓝）

```css
:root {
  --m-primary: #3F8CFF;        /* 公共卫生蓝 */
  --m-primary-hover: #2768D9;
  --m-primary-soft: #E9F3FF;
  --m-bg: #F5F9FF;             /* 浅蓝背景 */
  --m-text-primary: #18253A;
  --m-text-regular: #65738A;
}
```

医疗形态附加约束：字体可读性优先、状态色明确、医疗风险信息突出；避免大面积强渐变、过度圆润、装饰压过数据。

### 3.3 Pet（温暖橙）

```css
:root {
  --m-primary: #FF7A3D;        /* 暖橙 */
  --m-primary-hover: #F45A24;
  --m-primary-soft: #FFE0C2;   /* 蜜桃色 */
  --m-bg: #FFF5E9;             /* 暖奶油底 */
  --m-text-primary: #3A302A;
  --m-text-regular: #7A7068;
  --m-success: #2DBB72;
  --m-warning: #FFB020;
  --m-danger: #F04438;
}
```

注意：暖奶油页面底 + 白色卡片 + 橙色强调的组合比纯白+纯橙更柔和；成功/警告/危险语义色同步偏暖调整。

### 3.4 City / Lifestyle（清新绿）

```css
:root {
  --m-primary: #2FA98C;        /* 蓝绿，自然亲和 */
  --m-primary-hover: #37BE9E;
  --m-primary-soft: #E3F4EE;
  --m-bg: #F5F7F6;
  --m-text-primary: #22302B;
}
```

---

## 四、密度映射（v2.3 四档 → 现有三档）

现有 `SKILL.md` §3.1 的内容密度为 `comfortable / standard / compact` 三档。v2.3 源文档的四档按以下规则对齐：

| v2.3 密度 | 映射到现有档 | 适用形态 |
|-----------|-------------|---------|
| Compact | `compact` | 保险、金融、医疗、政务、企业系统、数据密集页 |
| Default | `standard` | 电商、城市服务、工具、出行 |
| Comfortable | `comfortable` | 内容阅读、健康科普、FAQ、关怀模式 |
| Spacious | `comfortable` | 品牌首页、营销活动页 |

补充规则：

1. 同一项目内允许按页面类型混用密度：如医疗项目首页 `standard`、号源/报告页 `compact`、科普文章页 `comfortable`。
2. 高信任形态（保险/医疗/政务）整体偏 `compact`：信息优先、字段密集、层级清晰、操作明确、减少装饰。
3. 任务页（表单/结算/预约确认）不因主题轻松而放松密度——业务页必须让用户"完成"，首页才允许让用户"喜欢"。

---

## 五、使用规则

1. **优先级（从高到低）**：用户 UI 规范 > `design-tokens.json` > 主题启发式（本文件）> 默认 Token（`mobile-tokens-and-classes.md`）。
2. **双端一致性**：双端场景换色**必须**经 `design-tokens.json` 统一下发，移动端不得单方面覆盖双端共享的品牌色/语义色（项目硬约束：品牌色与语义色与 PC 端 `pc-admin-navigation-style.md` 保持一致）。
3. **只覆盖值，不改命名**：主题只提供 `--m-*` 变量的值建议，禁止引入 `--brand-*`、`--page-bg`、`--surface`、`--gray-*` 等新命名空间。
4. **主题 ≠ 业务模式**：同一主题可承载不同页面结构（医疗主题下既有预约模式也有内容模式）；主题只影响气质（色彩/密度/装饰度），页面结构由 archetypeId 与 `mobile-business-patterns.md` 决定。
5. **结论可追溯**：使用了主题兜底时，在 `build-report.json` 中把主题判断记入对应字段的 `sourceRefs`（如 `"theme-profiles:Insurance"`），`sourceLevel` 标记为 `FALLBACK`。
6. **情绪分层**：允许内容/首页层有更高情绪权重，但交易/办理/预约页保持任务优先——装饰服务于信任与完成率，不服务于氛围。
