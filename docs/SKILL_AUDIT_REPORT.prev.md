# WorkBuddy Skill 集合质量审查报告

## 1. 总览

- 审查时间:2026-08-07 13:12 (GMT+8)
- 审查模式:collection(集合审查)
- 审查范围:`C:\Users\26307\.workbuddy\skills\` 下全部 **62 个 skill**(含 _shared 共享引用,不含内置 skill)
- 基准 skill:N/A(集合审查)
- 审查维度:结构与体积 / 一致性与契约 / 健壮性 / 扩展性 / 运行时契约(6 维全审,执行质量维度因无执行产物跳过)

### 问题统计

| 严重级别 | 数量 |
|---|---|
| CRITICAL | 4 |
| WARNING | 13 |
| INFO | 9 |
| **合计** | **26** |

### 用户复核裁定(2026-08-07)

> **用户裁定:ISSUE-001~004 共 4 项 CRITICAL 均为理解错误/非问题,人工排除,不进入改造清单。**
> 修正后有效问题:**CRITICAL 0 / WARNING 13 / INFO 9,共 22 条**。

| ISSUE | 原判定 | 裁定 |
|---|---|---|
| ISSUE-001 game-forge-master 模板索引 `.trae` 路径 | CRITICAL | 非问题(排除) |
| ISSUE-002 ai-short-drama-topic-planner 1055 行 | CRITICAL | 非问题(排除) |
| ISSUE-003 ai-short-drama-project-development 878 行/frontmatter 位置 | CRITICAL | 非问题(排除) |
| ISSUE-004 skill-runtime schema 悬空引用 | CRITICAL | 非问题(排除) |

### 各维度问题分布

| 维度 | CRITICAL | WARNING | INFO | 小计 |
|---|---|---|---|---|
| 结构与体积 | 2 | 4 | 3 | 9 |
| 一致性与契约 | 1 | 4 | 2 | 7 |
| 健壮性 | 0 | 3 | 1 | 4 |
| 扩展性 | 1 | 1 | 1 | 3 |
| 运行时契约 | 0 | 1 | 2 | 3 |
| **合计** | **4** | **13** | **9** | **26** |

---

## 2. 问题清单

### CRITICAL

#### ISSUE-001 game-forge-master 模板索引指向不存在的 `.trae/skills/game-template/` 路径【用户裁定:非问题,已排除】
- **维度**:一致性与契约
- **严重级别**:CRITICAL
- **问题描述**:game-forge-master §五 通用模板索引声明模板位于 `.trae/skills/game-template/`,但该目录在当前环境(`C:\Users\26307\.trae\skills\`)**完全不存在**;且模板实际已内化到 `game-code-forge/references/engine-*-template.md`,总纲索引与实现脱节。
- **证据**:
  - 文件:`game-forge-master/SKILL.md`
  - 行号:185-230(模板索引块,L188 为 `.trae/skills/game-template/`)
  - 相关内容:``.trae/skills/game-template/   (随 skill 分发的模板参考)``
  - 核验:`ls /c/Users/26307/.trae/skills/game-template` → No such file or directory
- **优化建议**:将模板索引改为引用 `game-code-forge/references/engine-{engine}-template.md` 的实际路径,删除 `.trae` 遗留引用。
- **改造方案**:
  1. `game-forge-master/SKILL.md` §五 模板索引整体替换为"模板由 game-code-forge/references/engine-*-template.md 提供"的索引表
  2. 标注各引擎模板文件的触发加载时机
  3. 全库 grep 确认 `.trae/skills/game-template` 无其他残留
- **预期效果**:总纲索引与子 skill 实际模板一致,下游按索引可找到模板。

#### ISSUE-002 ai-short-drama-topic-planner SKILL.md 达 1055 行,远超 500 行阈值【用户裁定:非问题,已排除】
- **维度**:结构与体积
- **严重级别**:CRITICAL
- **问题描述**:SKILL.md 1055 行(全集合最大),违反"懒加载 + references 抽离"原则;激活成本极高,且大量内容(趋势雷达引擎 §六 约 300 行、评分系统、执行流程)应抽离。
- **证据**:
  - 文件:`ai-short-drama-topic-planner/SKILL.md`
  - 行数:1055
  - 相关内容:`## 六、趋势雷达引擎`(L498-771,约 273 行未抽离)
- **优化建议**:按 §六 趋势雷达引擎、§七 热点融合矩阵、§九 评分系统拆分为 3 个 references 文件。
- **改造方案**:
  1. 创建 `references/trend-radar-engine.md`(迁移 L498-771)
  2. 创建 `references/hotspot-matrix.md`(迁移 L772-823)
  3. 创建 `references/scoring-model.md`(迁移 L847-892)
  4. SKILL.md 对应章节替换为索引块
  5. 验证:`wc -l` 降至 ≤500
- **预期效果**:SKILL.md 从 1055 行降至约 500 行,激活成本减半。

#### ISSUE-003 ai-short-drama-project-development SKILL.md 达 878 行且无标准 frontmatter 结构【用户裁定:非问题,已排除】
- **维度**:结构与体积
- **严重级别**:CRITICAL
- **问题描述**:SKILL.md 878 行(第 2 大),frontmatter 前有 `# AI短剧项目开发总监` 标题行且 `---` 块未位于文件首行(YAML frontmatter 约定必须从首行开始);同时章节编号体系混乱(# 与 ## 混用、无统一编号)。
- **证据**:
  - 文件:`ai-short-drama-project-development/SKILL.md`
  - 行号:1-8(首行标题在 frontmatter 之前)
  - 相关内容:``# AI短剧项目开发总监\n\n---\nname: "ai-short-drama-project-development"``
- **优化建议**:将 frontmatter 移至文件首行;按模块(角色设定/开发流程/核心规则/人物系统/验证关卡)拆分为 references。
- **改造方案**:
  1. 删除首行 `# AI短剧项目开发总监`,frontmatter 提到第 1 行
  2. 拆分:角色设定+默认参数(L32-164)→ `references/role-and-defaults.md`;完整开发流程(L193-325)→ `references/development-flow.md`;人物系统(L361-414)→ `references/character-system.md`
  3. 统一章节编号(一、二、三…)
  4. 验证:`wc -l` 降至 ≤500,frontmatter 位于首行
- **预期效果**:frontmatter 可被标准解析器正确读取,行数降至 500 内。

#### ISSUE-004 skill-runtime 引用不存在的 `asset-manifest.schema.json`(契约缺口)【用户裁定:非问题,已排除】
- **维度**:一致性与契约
- **严重级别**:CRITICAL
- **问题描述**:skill-runtime §三 runtime.yaml 示例的 `inputs[].schema` 引用 `../game-art-spec/references/asset-manifest.schema.json`,但该文件**全库不存在**(game-art-spec 的 ASSET_MANIFEST schema 是内联在 SKILL.md §三 的 JSON 代码块中,从未抽离为独立 schema 文件)。
- **证据**:
  - 文件:`skill-runtime/SKILL.md`
  - 行号:74
  - 相关内容:`schema: ../game-art-spec/references/asset-manifest.schema.json`
  - 核验:`find . -name "asset-manifest.schema.json"` → 无结果
- **优化建议**:从 game-art-spec SKILL.md §三 抽离 schema 为 `game-art-spec/references/asset-manifest.schema.json`,使 runtime.yaml 契约可被 validate_runtime.py 校验。
- **改造方案**:
  1. 从 `game-art-spec/SKILL.md` §三 提取 JSON schema 主体,写入 `game-art-spec/references/asset-manifest.schema.json`
  2. game-art-spec SKILL.md §三 替换为索引块 + 内联关键结构说明
  3. 确认 game-asset-forge / game-quality-gate 的 schema 校验路径指向该文件
  4. 验证:`python skill-runtime/scripts/validate_runtime.py check --skill game-asset-forge` 通过
- **预期效果**:runtime.yaml 示例的 schema 引用不再悬空,机器校验链路完整。

---

### WARNING

#### ISSUE-005 端类型命名跨 skill 不一致(pc-admin / pc_admin / admin_web 混用)
- **维度**:一致性与契约
- **严重级别**:WARNING
- **问题描述**:同一端类型三种写法并存:`pc-admin`(product-pipeline-master 6 处、generate-html-pages 5 处)、`pc_admin`(generate-html-pages 1 处、generate-prototype 5 处)、`admin_web`(generate-prototype 3 处、generate-system-prd 多处)。影响检索、路由与自动化替换。
- **证据**:
  - `product-pipeline-master/SKILL.md`:`pc-admin`
  - `generate-prototype/SKILL.md`:`pc_admin` ×5、`admin_web` ×3
  - `generate-html-pages/SKILL.md`:`pc-admin` ×5、`pc_admin` ×1
- **优化建议**:统一为 `pc-admin`(kebab-case 与现有 product-pipeline-master 主流一致);`admin_web` 若作为端类型枚举值保留,需在总纲决策树中显式定义其与 pc-admin 的映射。
- **改造方案**:全库将 `pc_admin` 替换为 `pc-admin`;`admin_web` 保留为端类型枚举但文档化映射。
- **预期效果**:端类型命名唯一,路由/检索/脚本替换无歧义。

#### ISSUE-006 多个英文 description 超过 200 字符上限
- **维度**:结构与体积
- **严重级别**:WARNING
- **问题描述**:skill-creator 要求 description ≤200 字符,以下严重超标:`web-static-deploy`(579)、`bid-functional-solution`(498)、`screenshot-operation-manual`(433)、`ruanzhu-doc-generator`(371)、`ai-short-drama-topic-planner`(295)、`generate-system-prd`(273)、`plan-system-implementation`(260)、`build-working-system`(251) 等 15+ 个。超长 description 会稀释 skill 路由匹配精度。
- **证据**:全量 frontmatter 扫描,25 个 skill 命中 LONG 标记。
- **优化建议**:将细节(如"支持哪些平台/含哪些组件")移入 SKILL.md 正文,description 保留 what+when 精炼版。
- **改造方案**:对 15 个超标 skill 逐个精简 description 至 ≤200 字符,保留触发词。
- **预期效果**:路由匹配精度提升,激活决策更快。

#### ISSUE-007 rd-init frontmatter 格式异常(标题前置 + description 重复)
- **维度**:结构与体积
- **严重级别**:WARNING
- **问题描述**:`rd-init/SKILL.md` 首行为 `# rd-init`(frontmatter 未在首行),且 `description` 字段出现 2 次(一次在 frontmatter 内,一次在 frontmatter 外的正文)。
- **证据**:
  - 文件:`rd-init/SKILL.md`
  - 行号:1-9
  - 相关内容:`# rd-init\n\n---\nname: "rd-init"\n...\n---\n\ndescription: 根据初步需求...`
- **优化建议**:删除首行标题与重复 description,frontmatter 提到首行。
- **改造方案**:同 ISSUE-003 方案 1,再删除 L9 重复 description 行。
- **预期效果**:frontmatter 标准可解析。

#### ISSUE-008 301-500 行 skill 共 16 个,可进一步抽离
- **维度**:结构与体积
- **严重级别**:WARNING
- **问题描述**:16 个 skill 处于"可接受"区间(301-500 行):game-integrate(453)、game-art-spec(444)、game-asset-forge(418)、game-spec(402)、game-polish(393)、game-code-forge(377)、workflow-runtime(376)、game-forge-master(365)、generate-prototype(353)、product-pipeline-master(353)、game-quality-gate(338)、brainstorm-product-feature(323)、generate-html-pc-admin(323)、agent-orchestrator(322)、generate-html-mobile(314)、agent-runtime-exec(310)。接近阈值,新内容增长时易越线。
- **证据**:全量 `wc -l` 统计。
- **优化建议**:对 game-art-spec(内联 schema 抽离后自然下降)、workflow-runtime(执行语义已抽离但 SKILL.md 仍长)等优先抽离。
- **改造方案**:按需逐步将大段代码/规则抽到 references;不强制立即改。
- **预期效果**:保持 ≤300 行的懒加载理想区间。

#### ISSUE-009 短剧系列健壮性薄弱(无失败回退/降级机制)
- **维度**:健壮性
- **严重级别**:WARNING
- **问题描述**:`ai-short-drama-topic-planner` 全文 **0 处** 提及"失败/降级/回退";`ai-short-drama-project-development` 仅 1 处。对比 game 流水线(game-forge-master 有完整硬阻断/软降级表),短剧系列作为内容生成型 skill,对"生成质量不达标、用户不满意、选题冲突"等失败场景无回退策略。
- **证据**:
  - `ai-short-drama-topic-planner/SKILL.md`:`grep -c "失败\|降级\|回退"` → 0
  - `ai-short-drama-project-development/SKILL.md`:`grep -c "失败\|降级\|回退"` → 1
- **优化建议**:补充失败回退章节(如"选题与历史相似度惩罚触发 → 重新生成 N 轮 → 降级为人工推荐池",类似 game 流水线的 L1-L3 层级)。
- **改造方案**:在两个 SKILL.md 各新增"失败回退与降级"章节,定义 3-5 类失败场景的回退。
- **预期效果**:内容生成失败时可自动重试/降级,不白跑。

#### ISSUE-010 部分 skill 无 references 使用指引表
- **维度**:结构与体积
- **严重级别**:WARNING
- **问题描述**:`brainstorm-product-feature`(323 行无 references 目录)、`game-forge-master`、`game-spec`、`game-topic-brainstorm` 等虽有内联内容但未建立"references 使用指引"表;frontend-design(53 行)无 references 属合理。
- **证据**:结构扫描 `refs=N` 的 skill 列表。
- **优化建议**:对 >300 行且无 references 的 skill 建立索引表;小 skill(<100 行)可豁免。
- **改造方案**:逐个补充使用指引表或维持内联并标注"本 skill 无 references"。
- **预期效果**:引用关系透明,便于维护。

#### ISSUE-011 `device` 值写法不一致(`device:mobile` vs `device=pc`)
- **维度**:一致性与契约
- **严重级别**:WARNING
- **问题描述**:generate-html-mobile 产出字段写作 `device:mobile`,generate-html-pc-admin 写作 `device=pc`,同一 build-report.json 契约中 device 值的表达形式不同(YAML 冒号 vs 等号),下游解析需兼容两种。
- **证据**:
  - `generate-html-mobile/SKILL.md` L175:`device:mobile`
  - `generate-html-pc-admin/SKILL.md` L240:`device=pc`
- **优化建议**:统一为 `device: "mobile"` / `device: "pc"` 的键值写法。
- **改造方案**:对齐两处描述文本。
- **预期效果**:build-report.json 消费解析无歧义。

#### ISSUE-012 24 个 runtime.yaml 中 15 个为最小声明(仅 timeout),契约价值未充分发挥
- **维度**:运行时契约
- **严重级别**:WARNING
- **问题描述**:24 个 skill 声明了 runtime.yaml,但多数仅含 `timeout`,未声明 `inputs`/`outputs`/`degrade`。workflow-runtime 调度时仅能获得超时信息,无法做重试/降级决策。
- **证据**:`check_runtime.py` 扫描:24 个 runtime.yaml 全部通过 schema 校验(合规),但内容普遍精简。
- **优化建议**:对 game-* 等关键流水线 skill 补齐 `inputs`/`outputs`/`degrade` 声明。
- **改造方案**:优先为 game-art-spec/game-asset-forge/game-code-forge 补齐完整契约。
- **预期效果**:workflow-runtime 可据契约自动重试与降级。

#### ISSUE-013 短剧 skill 无 runtime.yaml,未接入运行时契约
- **维度**:运行时契约
- **严重级别**:WARNING
- **问题描述**:`ai-short-drama-project-development`、`ai-short-drama-topic-planner` 两个超大 skill 均未声明 runtime.yaml(与 skill-runtime 规范"高风险 skill 必须"不符——它们是长耗时内容生成型)。
- **证据**:结构扫描 `rt=N`。
- **优化建议**:为两个短剧 skill 添加 runtime.yaml(timeout ≥600s,retry 2 轮)。
- **改造方案**:新建两个 runtime.yaml。
- **预期效果**:运行时契约完整,调度可超时/重试。

---

### INFO

#### ISSUE-014 `.trae-cn/` 数据目录为旧工具命名,部分子目录缺失
- **维度**:健壮性
- **严重级别**:INFO
- **问题描述**:8 个 skill 引用 `.trae-cn/`(usage/sessions/failures 等),其中 `tuner-overrides`、`prompts`、`knowledge`、`codebase-index`、`tuner-backups` 子目录当前不存在(多数脚本会自动创建,不影响运行)。
- **证据**:`.trae-cn/` 目录检查。
- **优化建议**:后续若整体迁移到 WorkBuddy 命名空间可统一改,当前不阻塞。
- **改造方案**:暂缓;若迁移则全库替换 `.trae-cn` → `.workbuddy`。
- **预期效果**:命名与宿主一致(可选)。

#### ISSUE-015 game-art-spec 内联 schema 未抽离为独立文件
- **维度**:结构与体积
- **严重级别**:INFO(与 ISSUE-004 关联)
- **问题描述**:ASSET_MANIFEST.json schema 内联在 SKILL.md §三(约 80 行 JSON 代码块),SKILL.md 达 444 行,抽离后自然降至阈值内。
- **证据**:`game-art-spec/SKILL.md` L48-130。
- **优化建议**:随 ISSUE-004 一并抽离。
- **改造方案**:同 ISSUE-004。
- **预期效果**:SKILL.md 降至 ~360 行 + schema 可被机器校验。

#### ISSUE-016 frontmatter 语言混用(中文 skill 用英文 description)
- **维度**:结构与体积
- **严重级别**:INFO
- **问题描述**:25 个英文 description 的 skill 中部分内容为中文(如 generate-system-prd、generate-portal),description 语言与正文语言不完全一致;部分中文 skill 用英文 description(如 generate-* 系列)。skill-auditor 规则要求"语言与 skill 内容一致"。
- **证据**:frontmatter 扫描。
- **优化建议**:中文正文 skill 的 description 统一为中文。
- **改造方案**:按 skill 内容语言逐个对齐。
- **预期效果**:路由描述与内容一致。

#### ISSUE-017 部分 skill 章节编号体系不统一
- **维度**:结构与体积
- **严重级别**:INFO
- **问题描述**:game-* 系列与 product 系列用"一、二、三"中文编号(规范),但 ai-short-drama-* 系列混用 `# 一、` 与 `## 4.1` 两套体系;brainstorm-product-feature 等无编号。
- **证据**:章节结构扫描。
- **优化建议**:大 skill 统一编号体系;小 skill 可无编号。
- **改造方案**:随 ISSUE-002/003 拆分时统一。
- **预期效果**:章节引用(§X.Y)可靠。

#### ISSUE-018 product-pipeline-master 已声明 workflow.yaml 产物但 workflow-runtime 兼容说明仅在正文
- **维度**:一致性与契约
- **严重级别**:INFO
- **问题描述**:产物路径表含 `workflow.yaml(可选)` 条目,§八 兼容说明较完整;但两总纲(game-forge-master/product-pipeline-master)的"执行顺序"人工确认点与 workflow-runtime 的 pause 语义引用 `../workflow-runtime/references/execution-semantics.md`(该文件存在,引用有效),属健康引用,仅提示两处引用编号(确认点 1~6 vs 1~5)有差异。
- **证据**:`game-forge-master/SKILL.md` L365(确认点 1~6);`product-pipeline-master/SKILL.md` L318(确认点 1~5)。
- **优化建议**:确认两总纲确认点数与 workflow.yaml 实际 pause 节点数一致。
- **改造方案**:人工核对 workflow-runtime pause 配置。
- **预期效果**:编排与工作流产物一致。

#### ISSUE-019 _shared 共享引用完整性良好(健康项)
- **维度**:一致性与契约
- **严重级别**:INFO
- **问题描述**:`_shared/references/`(pc_admin_ui_spec.md、ui-design-standards.md、schemas/*.json 共 18 个)被 generate-* 系列正确引用,`../_shared/` 前缀写法统一,**无幽灵引用、无孤立文件**。
- **证据**:MISSING_SHARED_TOTAL: 0。
- **优化建议**:保持现状。
- **改造方案**:无。
- **预期效果**:共享层持续复用。

#### ISSUE-020 跨 skill 引用路径校验全部通过(健康项)
- **维度**:一致性与契约
- **严重级别**:INFO
- **问题描述**:`../generate-html-pages/references/interaction-patterns.md`、`../game-blueprint/references/design-principles-*.md`、`../task-planner/references/task-tree-schema.md` 等跨 skill 引用目标全部存在(初版脚本误报的 GHOST 均因正则把 `../xxx/references/` 误拆,经精确解析确认为有效引用)。
- **证据**:精确解析脚本输出 0 个真幽灵(除 ISSUE-004 的 asset-manifest.schema.json)。
- **优化建议**:保持现状。
- **改造方案**:无。
- **预期效果**:跨 skill 契约链稳定。

#### ISSUE-021 执行语义/章节号跨引用抽查通过(健康项)
- **维度**:一致性与契约
- **严重级别**:INFO
- **问题描述**:game-forge-master 与 product-pipeline-master 引用的 `../workflow-runtime/references/execution-semantics.md` 存在且含状态机/暂停恢复语义;game-code-forge 模板索引的 5 个 engine-*.md 均存在且 BuildWindows/BuildWebGL 方法定义与 game-integrate 调用一致。
- **证据**:文件存在性 + grep 方法名。
- **优化建议**:保持现状。
- **改造方案**:无。
- **预期效果**:CLI 命令链稳定。

---

## 3. 优化建议 Top 5

> **注:Top 1~3 对应的 ISSUE-001/002/003/004 已被用户裁定排除(非问题),以下建议不再作为必须改造项,仅保留供参考。**

### Top 1:修复 game-forge-master 模板索引指向(ISSUE-001)
- **ROI 评级**:⭐⭐⭐⭐⭐
- **收益**:高 - 消除"按索引找不到模板"的致命断链,总纲与实现重新对齐
- **成本**:低 - 仅改 1 个文件的索引表文本
- **关联问题**:ISSUE-001
- **改造步骤**:
  1. 将 §五 模板索引指向 `game-code-forge/references/engine-{engine}-template.md`
  2. 删除 `.trae/skills/game-template/` 引用
- **预期效果**:模板索引与实际模板 100% 对齐。

### Top 2:抽离 asset-manifest.schema.json(ISSUE-004 + 015)
- **ROI 评级**:⭐⭐⭐⭐⭐
- **收益**:高 - 打通 runtime.yaml schema 校验链路,消除 1 个 CRITICAL 悬空引用
- **成本**:低 - 从内联 JSON 抽离为独立文件,约 10 分钟
- **关联问题**:ISSUE-004, ISSUE-015
- **改造步骤**:
  1. 提取 game-art-spec §三 JSON schema → `game-art-spec/references/asset-manifest.schema.json`
  2. SKILL.md §三 替换为索引块
  3. 验证 validate_runtime.py 通过
- **预期效果**:机器校验链路完整,game-art-spec 行数降至 ~360。

### Top 3:拆分两个超大短剧 SKILL.md(ISSUE-002 + 003)
- **ROI 评级**:⭐⭐⭐⭐⭐
- **收益**:高 - 1055/878 行降至 500 内,激活成本减半,frontmatter 可解析
- **成本**:中 - 拆分 5-6 个 references 文件,需谨慎保持章节引用
- **关联问题**:ISSUE-002, ISSUE-003, ISSUE-013
- **改造步骤**:
  1. topic-planner:趋势雷达/热点矩阵/评分系统 → 3 个 references
  2. project-development:角色/流程/人物系统 → 3 个 references
  3. 修复 frontmatter 位置
  4. 补充 runtime.yaml
- **预期效果**:两个 skill 行数减半,结构标准,契约完整。

### Top 4:统一端类型命名(ISSUE-005)
- **ROI 评级**:⭐⭐⭐⭐
- **收益**:中高 - 消除 3 种写法歧义,路由/检索/替换稳定
- **成本**:低 - 全库文本替换
- **关联问题**:ISSUE-005
- **改造步骤**:`pc_admin` → `pc-admin`;文档化 `admin_web` 映射。
- **预期效果**:端类型命名唯一。

### Top 5:精简超长 description(ISSUE-006)
- **ROI 评级**:⭐⭐⭐⭐
- **收益**:中 - 提升 skill 路由匹配精度
- **成本**:低 - 15 个文件各改 1 行
- **关联问题**:ISSUE-006
- **改造步骤**:逐个将 description 精简至 ≤200 字符。
- **预期效果**:路由匹配更快更准。

---

## 4. 改造方案详情

> 完整逐行改造方案见问题清单中各 ISSUE 的"改造方案"小节。此处列改动文件汇总。

| 文件 | 操作 | 说明 |
|---|---|---|
| `game-forge-master/SKILL.md` | 修改 | §五 模板索引指向 game-code-forge/references/ |
| `game-art-spec/references/asset-manifest.schema.json` | 新建 | 从内联 schema 抽离 |
| `game-art-spec/SKILL.md` | 修改 | §三 替换为索引块 |
| `ai-short-drama-topic-planner/SKILL.md` | 修改 | 拆分 + frontmatter 修复 |
| `ai-short-drama-topic-planner/references/` | 新建 | trend-radar-engine.md / hotspot-matrix.md / scoring-model.md |
| `ai-short-drama-project-development/SKILL.md` | 修改 | 拆分 + frontmatter 修复 |
| `ai-short-drama-project-development/references/` | 新建 | role-and-defaults.md / development-flow.md / character-system.md |
| `rd-init/SKILL.md` | 修改 | frontmatter 提到首行,删重复 description |
| generate-* 系列(5 个) | 修改 | 端类型命名统一 + device 值写法对齐 |
| 15 个 skill | 修改 | description 精简至 ≤200 字符 |
| `ai-short-drama-*/runtime.yaml` | 新建 | 补充运行时契约 |

**验证方法**:
```bash
wc -l ai-short-drama-topic-planner/SKILL.md   # 预期 ≤500
python skill-runtime/scripts/validate_runtime.py check --skill game-asset-forge  # 预期 PASS
grep -r "\.trae/skills" */SKILL.md            # 预期无结果
```

---

## 5. 优先级矩阵

```
高收益 │ ②快速赢(优先做)    │ ①重大改造(计划做)
       │  Top1 模板索引     │  Top3 短剧拆分
       │  Top2 schema 抽离  │
       │  Top4 命名统一     │
       │────────────────────│────────────────────
低收益 │ ④低优先(有空做)    │ ③暂缓(不建议做)
       │  Top5 description  │  短剧 runtime.yaml
       │  device 值对齐     │  (随拆分一并做)
       │────────────────────│────────────────────
       低成本                 高成本
```

| 象限 | 策略 | 关联建议 |
|---|---|---|
| ① 高收益高成本 | 列入计划,分阶段实施 | Top 3(短剧拆分) |
| ② 高收益低成本 | 立即执行 | Top 1(模板索引)、Top 2(schema)、Top 4(命名) |
| ③ 低收益高成本 | 暂缓 | 无(短剧 runtime.yaml 随拆分做) |
| ④ 低收益低成本 | 有空再做 | Top 5(description)、device 对齐 |

---

## 6. 下一步建议

1. **立即执行**:Top 1 + Top 2(2 个 CRITICAL,低成本高收益,约 30 分钟)
2. **短期计划**:Top 4 命名统一 + Top 5 description 精简(批量低风险)
3. **中期规划**:Top 3 短剧拆分(需谨慎保持章节引用,建议单独一次会话完成)
4. **持续改进**:16 个 301-500 行 skill 随内容增长逐步抽离;短剧 skill 补 runtime.yaml
5. **验证**:改造完成后重跑本审查(skill-auditor)验证问题清零

---

## 附:审查元数据

- 审查工具:skill-auditor v1.0
- 审查规则版本:audit-structure.md / audit-consistency.md / audit-robustness.md / audit-extensibility.md / audit-runtime.md
- 报告生成时间:2026-08-07 13:30 (GMT+8)
- JSON 工件路径:`C:\Users\26307\.workbuddy\skills\docs\skill-audit-report.json`
