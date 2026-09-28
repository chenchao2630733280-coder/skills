# App AI UI Design System v2.3 跨 Skill 蒸馏整合方案（v3 终版）

## 一、核心结论：三层知识分工

用户指令："业务知识可以蒸馏到 generate-system-prd"。结合此前确认的 What/How 分离原则，最终架构：

```
需求文档
   ↓
generate-system-prd（What：业务领域知识 ← v2.3 的垂直业务章节蒸馏至此）
   产出 PRD + state-machines.json / business-rules.json / pages.json（含领域状态/实体/角色/规则）
   ↓
generate-prototype（项目级视觉决策载体：design-tokens.json，双端共享——现有机制，不动）
   ↓
generate-html-mobile（How：渲染知识 ← v2.3 的主题/模式/展示原则蒸馏至此）
   从工件结构识别业务形态 → 匹配渲染模式 → 现有 10 原型 → HTML
```

| v2.3 内容 | 蒸馏目的地 | 形态 |
|-----------|-----------|------|
| 垂直业务章节（保险§7/§48-62、家庭保险§38-46、宠物§75-120、医疗§139-198） | **generate-system-prd** | 领域模式库：PRD 写作的领域检查清单 |
| 通用领域抽象（§127-134） | **generate-system-prd** | 数据建模启发式，并入领域模式库 |
| 主题 Profile（§6/§24/§126/§187） | **generate-html-mobile** | 最低优先级视觉兜底启发式 |
| 5 大通用渲染模式 + 展示原则 + 布局变体（§200-205/§44-45/§59 等） | **generate-html-mobile** | 工件结构触发→UI 渲染规则 |
| AI Prompt 章节、Foundation Token、PascalCase 命名 | 丢弃 | 与 skill 执行流不匹配 / 与现有体系冲突 |

**为什么不按业务建独立基线库 / 不加流水线阶段**：v2.3 自身 5 个项目迭代结论（§74/§137/§207）即分层复用而非固定模板；`design-tokens.json` 已是项目级视觉基线实例化载体；PRD 工件（带 sourceRefs）已是项目级业务知识载体。

---

## 二、Part A：generate-system-prd 整合（业务知识 What）

### A1：新建 `generate-system-prd/references/business-domain-patterns.md`（约 350-450 行）

> 头部定位声明：领域模式是**检查清单与启发式**，不是模板硬套。用户实际需求与模式冲突时以需求为准，差异记入 `decision-log.json`。

内容结构：

1. **领域识别与复杂度评估**（源自 §24/§127）：六维判断（Project Type / Trust Level / Transaction Level / Form Complexity / State Complexity / Local Service），输入来自 Step 1 需求收集，输出领域结论与复杂度评级
2. **通用领域抽象**（源自 §128-131/§200-205）：Entity 统一结构（Identity/Status/Metadata/Content/Actions/History）、Role-Relationship 模型、Resource-Capacity-Lock、Record 模型——作为第 3 章数据建模的启发式
3. **4 个垂直领域模式**，每个统一为五段式：
   - 领域特征（信任等级/状态复杂度/角色复杂度）
   - 核心实体与角色（如保险：投保人/被保人/监护人；医疗：登录人≠就诊人、医院-院区-科室-医生层级）
   - 关键状态机清单（如保险：**支付状态机与保单状态机必须分离**、核保 5 态、授权 5 态；医疗：号源 Available/Full/Locked/Expired、预约含 Missed 爽约态、排队叫号）
   - 流程要点（如保险：资格核验→报价→协议→支付→结果→保单；宠物：领养=浏览→筛选→申请→审核→线下交付，非电商 Checkout）
   - **PRD 章节落点映射 + 领域检查清单**（生成后自检：双状态机是否分离？资格不符原因是否可解释？号源锁定超时是否释放？操作人≠被操作对象时角色是否显式建模？）
4. **读取规则**：仅当 Step 1 识别出对应领域时读取对应章节；懒加载，不预读全文

### A2：修改 `generate-system-prd/SKILL.md`（净增约 12 行）

1. **参考文件使用指引表**：新增 `business-domain-patterns.md` 行——"识别到保险/家庭保险/宠物/医疗等垂直领域时，逐章生成前读取对应章节作为领域检查清单"
2. **Step 1 需求收集**：第 3 项"核心业务域和用户任务"扩展——识别业务领域并评估六维复杂度（指向新文件）
3. **Step 2 逐章生成**：增加一条——识别出垂直领域时，第 3/4/5/7 章生成前读取领域模式对应章节，确保领域关键状态/角色/规则不遗漏
4. **Step 3 交叉校验**：新增第 11 项"领域完整性校验"——对照领域检查清单核查关键状态机、角色关系、异常路径覆盖
5. **§六 关键设计模式参考**：末尾加一行指向 `references/business-domain-patterns.md`（垂直领域模式）

---

## 三、Part B：generate-html-mobile 整合（渲染知识 How）

### B1：新建 `generate-html-mobile/references/mobile-theme-profiles.md`（约 150-200 行）

1. **业务形态识别输入**：从 PRD 产品定位 + `pages.json`/`state-machines.json` 结构特征判断（明确不依赖 skill 内置业务知识——业务内容一律以工件为准）
2. **主题 Profile 表**：9+ 主题（City/Commerce/Insurance/Healthcare/Government/Enterprise/Content/Pet/Travel），每主题给关键词与密度建议；金融/城市/宠物/医疗 4 个给 `--m-*` 覆盖值示例，其余关键词级指引
3. **密度映射**：v2.3 的 4 档 → 现有 3 档（comfortable/standard/compact）对齐规则
4. **使用规则**：优先级最低（用户 UI 规范 > `design-tokens.json` > 主题启发式 > 默认值）；**双端场景换色必须经 `design-tokens.json` 统一下发**，移动端不得单方面覆盖双端共享色；只覆盖值不改 `--m-*` 命名；结论记入 build-report `sourceRefs`

### B2：新建 `generate-html-mobile/references/mobile-business-patterns.md`（约 200-250 行）

> 头部定位声明：本文件**不含业务知识**（业务流程/字段/状态/角色一律以上游 PRD/JSON 工件为准，领域知识已沉淀于 `generate-system-prd`）；本文件只定义"从工件结构识别出某类业务形态时，如何渲染"。

1. **5 大通用渲染模式**（每个 = 触发条件〔工件结构特征〕+ UI 结构 + 状态展示 + `.m-*` 类名建议）：
   - Resource Availability（触发：存在带容量/时段的资源实体）→ 日期→时段→剩余→操作 + Available/Limited/Full/Locked/Expired 样式
   - Queue（触发：存在实时位置型状态机）→ 大字号当前值 + 前方人数 + 位置提示；不伪造精确等待时间
   - Identity（触发：存在证件类型字段 + 核验动作）→ 证件类型显式选择 + 统一脱敏 + 验证 Loading 与失败原因
   - Record（触发：存在 owner/type/date/status 记录实体）→ 统一卡片结构 + 状态标签
   - Appointment（触发：存在参与者×资源×时间预约实体）→ 确认页全要素 + 锁定倒计时
2. **跨领域展示原则**：双状态机分离展示（`state-machines.json` 识别）；敏感数据列表态脱敏/编辑态经授权；操作人≠对象时关键步骤显式角色关系；多步验证分步展示；结果页失败三问（发生了什么/为什么/下一步怎么办）
3. **布局变体**：瀑布流内容（2 列 masonry）、保障矩阵（表格型数据）、Care Mode（字号/间距/点击区放大的 Token 覆盖组）
4. **结果页（result）原型规则**：Success/Processing/Failed/Cancelled 四态结构——补现有 10 原型缺口

### B3：修改 `generate-html-mobile/SKILL.md`（净增约 30 行）

1. **§3.1 设计决策**：新增第 0 步"业务形态识别与主题/密度判断"（读 `mobile-theme-profiles.md`，输入来自工件）
2. **§3.5 原型表**：补"结果页 | result | 状态图标→结论→原因→下一步操作"行；注明按工件识别的形态读 `mobile-business-patterns.md`
3. **§3.6 状态**：增加"支付状态与业务状态分离展示"约束（触发：`state-machines.json` 存在双状态机）
4. **§5.3 质量标准**：增加 4 条——高风险信息突出、敏感数据默认脱敏、双状态机分离展示、操作人≠对象时角色显式化
5. **§八 参考索引**：登记 2 个新文件（含读取时机与定位说明）

### B4：修改 `references/mobile-product-design-standards.md`（净增约 8 行）

§1 追加"业务类型决定视觉密度与主题气质"原则；§2 前置"先完成业务形态识别与主题选择"，均指向 theme-profiles。

---

## 四、Part C：删除原文件

- 删除 `generate-html-mobile/references/App_AI_UI_Design_System_v2.3.md`（增量已分流至两个 skill）
- 两个新文件头部注明"蒸馏自 App AI UI Design System v2.0-v2.3"

---

## 五、实施顺序

1. **Part A**：A1 新建 `business-domain-patterns.md` → A2 修改 `generate-system-prd/SKILL.md`
2. **Part B**：B1 新建 `mobile-theme-profiles.md` → B2 新建 `mobile-business-patterns.md` → B3 修改 `generate-html-mobile/SKILL.md` → B4 修改 `mobile-product-design-standards.md`
3. **Part C**：蒸馏内容确认完整后删除 `App_AI_UI_Design_System_v2.3.md`
4. 执行"七、验证步骤"全部校验，行数/命名空间/What-How 分离/路由完整性不达标则回改

---

## 六、假设与决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | 业务知识（What）蒸馏到 generate-system-prd，渲染知识（How）留在 generate-html-mobile | 用户指令 + What/How 分离原则 |
| 2 | 领域模式定位为"检查清单与启发式"，需求冲突时以需求为准 | 防止模式硬套覆盖真实需求 |
| 3 | 不按业务建独立基线库、不加流水线阶段 | v2.3 自身结论；design-tokens.json 与 PRD 工件已是实例化载体 |
| 4 | `--m-*` 命名空间不变，主题只覆盖值；双端换色必须经 design-tokens.json | 项目记忆硬约束：双端共享品牌/语义色 |
| 5 | 密度沿用现有 3 档 | 与 SKILL.md §3.1 现有定义对齐 |
| 6 | generate-prototype 不改动 | 其职责是工件富化与 Token 载体，领域知识经 PRD 已进入工件 |
| 7 | 原文件蒸馏后删除 | 用户偏好厌恶冗余文件 |
| 8 | 两 skill 均遵守懒加载：新参考文件按领域/形态按需读取 | generate-system-prd 已采用懒加载优化（项目记忆） |

---

## 七、验证步骤

1. **行数校验**：business-domain-patterns ≤ 450 行；theme-profiles ≤ 200 行；mobile-business-patterns ≤ 250 行；generate-system-prd SKILL.md ≤ 290 行（现 277 行）；generate-html-mobile SKILL.md ≤ 350 行（现 314 行）
2. **命名空间校验**：Grep 两个移动端新文件，无 `--brand-`/`--page-bg`/`--surface`/`--gray-` 等非 `--m-*` 变量
3. **What/How 校验**：mobile-business-patterns 中不得出现具体业务流程步骤链/实体字段清单（触发条件举例需标注"以工件为准"）；business-domain-patterns 中不得出现 UI 类名/Token/布局规则
4. **路由完整性**：两个 SKILL.md 参考索引与实际文件一一对应；无孤儿文件
5. **决策链演练**（纸面推演）：
   - 医疗挂号：generate-system-prd 识别医疗领域 → 领域检查清单确保 PRD 含号源锁定/爽约/双状态机 → 工件携带这些结构 → generate-html-mobile 从工件识别"资源+容量+锁定"→ Availability 模式渲染 → 双状态机分离展示。业务内容全程来自 PRD/工件
   - 宠物项目：PRD 阶段领域模式提示宠物实体/领养审核流程 → 工件含宠物 Record 实体 → mobile 命中 Record 模式 + 瀑布流变体 + Pet 主题兜底（无上游 Token 时）
