# game 流水线（阶段 2.5 接入后）- Skill 质量审查报告

## 1. 总览

- 审查时间：2026-11-10T15:05:24+08:00
- 审查模式：**pipeline**（流水线审查）
- 审查范围：
  - `C:/Users/26307/.agents/skills/game-forge-master`（编排总纲）
  - `C:/Users/26307/.agents/skills/game-quality-gate`（门禁）
  - `C:/Users/26307/.agents/skills/game-level-design`（本次新增阶段 2.5）
  - 上下文核对：`game-code-forge`、`game-integrate`、`game-teardown`（仅核查契约是否被消费）
- 基准 skill：N/A（未走对比基准模式）
- 审查维度：结构与体积 / 一致性与契约 / 健壮性 / 扩展性（4 维全审）

### 问题统计

| 严重级别 | 数量 |
|---|---|
| CRITICAL | 4 |
| WARNING | 10 |
| INFO | 5 |
| **合计** | **19** |

### 各维度问题分布

| 维度 | CRITICAL | WARNING | INFO | 小计 |
|---|---|---|---|---|
| 结构与体积 | 0 | 0 | 2 | 2 |
| 一致性与契约 | 4 | 7 | 3 | 14 |
| 健壮性 | 0 | 2 | 0 | 2 |
| 扩展性 | 0 | 1 | 0 | 1 |

**一句话结论**：`game-forge-master` 与 `game-quality-gate` 已经把阶段 2.5 接进去了，但**新技能自己的三份文档还停留在旧顺序**，且**两个下游 skill（game-code-forge / game-integrate）完全不知道 `config/levels.json` 的存在**——结果是"门禁要检查一件代码从没被要求做的事"。这 4 个 CRITICAL 必须在下次跑流水线前修掉。

---

## 2. 问题清单

### CRITICAL

#### ISSUE-001 阶段顺序三方打架：新技能自述仍是"关卡在美术之后"

- **维度**：一致性与契约
- **严重级别**：CRITICAL
- **问题描述**：`game-forge-master` 与 `game-quality-gate` 已改成"规格门 → 关卡门 → 美术门 → 产物门"，但 `game-level-design` 的 SKILL.md、README、references/13 三处仍写"美术门之后"，同一条流水线存在两套顺序。
- **证据**：
  - `game-level-design/SKILL.md:22-26`
    ```
    game-art-spec → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json
       ↓ [Gate 2] 美术门
    【本 skill】game-level-design → ...
       ↓ [Gate 2.5] 关卡门
    ```
  - `game-level-design/README.md:11-15`
    ```
    game-spec → [Gate 1] → game-art-spec → [Gate 2]
       ↓ [Gate 2.5] 关卡门
    ```
  - `game-level-design/references/13_pipeline_integration.md:10`
    ```
    | 阶段编号 | **2.5**（插在 Gate 2 美术门之后、确认点 3 之前） |
    ```
  - 对照正确顺序：`game-forge-master/SKILL.md:61-73`、`game-quality-gate/SKILL.md:44-52`
- **优化建议**：以 master 的 `§七` 为唯一事实源，三处统一为"规格门 → 关卡门 → 美术门 → 产物门"，并说明理由（关卡表先定，美术才知道几套场景/主题）。
- **改造方案**：
  1. `SKILL.md` §一 位置图重画：`game-spec → 规格门 → 确认点 2 → 【本 skill】→ 关卡门 → game-art-spec → 美术门 → 确认点 3 → forge`
  2. `README.md` 同图同步（第 11–15 行整块替换）
  3. `references/13` 第 10 行表格改为"插在 Gate 1 规格门之后、Gate 2 美术门之前"；第 15 行"并入确认点 3"保留（确认点 3 仍在美术门后，语义不变）
- **预期效果**：执行者按任一文档都能得到同一顺序；避免关卡阶段被排到美术后导致场景数返工。

#### ISSUE-002 字段名 `score` 与 `difficulty_score` 不一致，按文档实现必挂 Gate 2.5

- **维度**：一致性与契约
- **严重级别**：CRITICAL
- **问题描述**：新技能的文档要求 `levels.json` 每关含 `score`，但导出工具实际输出 `difficulty_score`，门禁检查项也要求 `difficulty_score`。按文档写校验器或手写配置都会 FAIL。
- **证据**：
  - `game-level-design/SKILL.md:120`：`（level_id/index/tag/params/target_win/score）`
  - `game-level-design/references/13_pipeline_integration.md:96`：`每关含 level_id/index/tag/params/target_win/score`
  - 权威实现：`tools/export_levels.py` 导出键为 `['difficulty_score','index','level_id','new_mechanics','notes','params','phase','pred_win','tag','target_win']`
  - `game-quality-gate/SKILL.md:116`：`每关含 level_id/index/tag/params/target_win/difficulty_score`
- **优化建议**：文档统一为 `difficulty_score`；如需兼容旧稿，在 schema 里显式声明 `score` 为废弃别名并给迁移说明。
- **改造方案**：
  1. 改 `SKILL.md:120`、`references/13:96` 两处 `score` → `difficulty_score`
  2. 在 `references/13` 的 schema 块补一行说明：`difficulty_score` 是 0~1 的排序/诊断分，**不等于**通关率（`pred_win` 才是）
  3. 追加 `examples/` 里的 levels.json 样例校验（断言键集合）
- **预期效果**：文档 ⇄ 工具 ⇄ 门禁三处字段名一致，Gate 2.5 的 G25-03 不再误判。

#### ISSUE-003 下游 game-code-forge 未接入 levels.json，且自身模板仍把数值写进 `src/config/LevelConfig.ts`

- **维度**：一致性与契约
- **严重级别**：CRITICAL
- **问题描述**：新契约声明"`config/levels.json` 是 game-code-forge 的唯一关卡数据源，禁止内联复制"，但 `game-code-forge` 全文没有任何 `levels.json` 引用；其目录模板明确把关卡/数值放在 `src/config/LevelConfig.ts`。代码按自身模板产出 → Gate 3 的 3.28（关卡数据走样）必然 FAIL，而修复责任又落在 code-forge 身上，形成死循环。
- **证据**：
  - `game-code-forge/SKILL.md:84-88`
    ```
    │   ├── config/
    │   │   ├── GameConfig.ts    # 全局配置(分辨率/物理/缩放)
    │   │   └── LevelConfig.ts   # 关卡/数值
    ```
  - `game-code-forge/SKILL.md:278`：`PRD 的"数值设计"表 → config/GameConfig.ts`
  - 全库 grep `levels.json`：命中 master / gate / level-design 三处 + 工具，**无 game-code-forge**
  - `game-quality-gate/SKILL.md:308`（3.28）：`代码通过 config/levels.json 加载关卡；src/ 中出现的关卡数值字面量与 levels.json 不一致即失败`
  - 契约声明方：`game-level-design/SKILL.md:42`、`runtime.yaml` outputs
- **优化建议**：给 code-forge 补"关卡数据加载"约定，并明确 `LevelConfig.ts` 降级为"读 levels.json 的类型化包装"，不存数值。
- **改造方案**：
  1. `game-code-forge/SKILL.md` 新增小节 `关卡数据加载（存在 config/levels.json 时必读）`，按引擎给落地路径：
     - Web（Phaser/Pixi/Canvas/Three，Vite）：`import levels from '../../../config/levels.json'`（`resolveJsonModule`）或放 `public/config/levels.json` 后 `fetch`；`LevelConfig.ts` 只做类型映射与按 `level_id` 取档
     - Godot 4：`res://config/levels.json`（复制进工程根），`JSON.parse_string(FileAccess.get_file_as_string(...))`
     - Unity：`Assets/StreamingAssets/config/levels.json`，`File.ReadAllText(Application.streamingAssetsPath + ...)`
  2. 目录树注释改：`LevelConfig.ts  # 关卡数值：仅从 config/levels.json 读取，禁止硬编码`
  3. 自检清单追加一条：`config/levels.json 存在时，src/ 无关卡数值字面量`
  4. 若 `config/levels.json` 不存在（单局制裁剪），回退到原 `LevelConfig.ts` 模式并注明
- **预期效果**：Gate 3 的 3.28 从"必挂"变成"可过"；关卡数值只在一处维护。

#### ISSUE-004 game-integrate 未声明消费难度目标带（单边契约）

- **维度**：一致性与契约
- **严重级别**：CRITICAL
- **问题描述**：新技能的 references/13 与 runtime.yaml 都声称"game-integrate 会用 `target_win` 目标带做 Gate 4 数值平衡核对，偏差 ≥15% 写进 BUILD_REPORT"，但 `game-integrate` 的 §十 数值平衡实测里没有任何 `DIFFICULTY_REPORT` / `levels.json` 引用——承诺无人兑现。
- **证据**：
  - `game-level-design/references/13_pipeline_integration.md:86`：`game-integrate：Gate 4 数值平衡核对 target_win 目标带；实际通关率与 pred_win 差 ≥15% 时写进 docs/BUILD_REPORT.md 的偏差表`
  - `game-level-design/runtime.yaml`：`docs/DIFFICULTY_REVIEW.json ... 供 Gate 2.5 与 game-integrate 数值平衡核对`
  - `game-integrate/SKILL.md:412` 起 §十 数值平衡实测：仅覆盖该 skill 原有指标
- **优化建议**：在 game-integrate §十 增设子节"关卡目标带核对"，把偏差表纳入 BUILD_REPORT 必填项。
- **改造方案**：
  1. `game-integrate/SKILL.md` §十 增 `10.5 关卡目标带核对（存在 config/levels.json 时必做）`
  2. 内容：读 `config/levels.json` 的 `target_win`/`pred_win` + 实跑通关率，逐关算偏差；`|实际 − target| ≥ 15%` 进 `docs/BUILD_REPORT.md` 偏差表，并回指 `docs/DIFFICULTY_REPORT.md`
  3. §十 验收清单追加一行（与现有 `[ ] 数值平衡实测通过` 并列）
  4. 无 levels.json 时整节跳过并标注 `LEVEL_BALANCE_SKIPPED`
- **预期效果**：难度设计到实跑形成闭环，预测 vs 实际背离在集成阶段收口，而不是等玩家反馈。

### WARNING

#### ISSUE-005 gate 顶层文案陈旧："三层门禁 × 四个检查点"

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：§二 标题已改"六个检查点"，但 §一 核心机制仍写"四个检查点"，同一文件内自相矛盾。
- **证据**：`game-quality-gate/SKILL.md:12`：`**核心机制**:三层门禁 × 四个检查点。`（对照第 30 行 `## 二、六个检查点`）
- **优化建议**：改为"三层门禁 × 六个检查点（含 Gate 0.5 / 2.5 两个条件门）"。
- **改造方案**：1) 第 12 行替换；2) 全文 grep `四个检查点` 确认无其他残留。
- **预期效果**：门禁自身描述与实际检查点数量一致。

#### ISSUE-006 gate 的 description 未含"关卡"，路由会漏

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：description 枚举的检查点时点只有"拆解后/蓝图后/规格后/美术后/资源代码后"，缺"关卡后"。用户说"校验关卡配置"时不会命中本 skill。
- **证据**：`game-quality-gate/SKILL.md:3`（149 字符，含 What+When，但无"关卡"二字）
- **优化建议**：在时点枚举里插入"关卡后[Gate 2.5·关卡制]"。
- **改造方案**：description 改为 `...在关键节点(拆解后[Gate 0.5·仅复刻]/蓝图后/规格后/关卡后[Gate 2.5·关卡制]/美术后/资源代码后)介入...`，控制在 200 字符内。
- **预期效果**：关键词"关卡/难度/关卡配置"能命中门禁 skill。

#### ISSUE-007 gate 报告路径模式的"例外"只列了 0.5，未列 2.5

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：模式为 `docs/GATE_{N}_REPORT.md`，例外说明只写"Gate 0.5 固定为 GATE_0_5_REPORT.md"。2.5 同样用下划线形式，按 `{N}` 直译会得到 `GATE_2.5_REPORT.md`（歧义）。§九 checklist 也只写 `GATE_{N}`。
- **证据**：`game-quality-gate/SKILL.md:352`、`:417`、`:421`
- **优化建议**：把例外扩为"小数门（0.5 / 2.5）一律下划线"。
- **改造方案**：1) 第 352 行改为"Gate 0.5 / 2.5 例外，固定为 `GATE_0_5_REPORT.md` / `GATE_2_5_REPORT.md`（下划线避免与整数门的 `{N}` 混淆）"；2) 第 417 行同述；3) 第 421 行"Gate 0~3"→"Gate 0/0.5/1/2.5/2/3"。
- **预期效果**：报告文件名不再有歧义，下游归档不 404。

#### ISSUE-008 gate 报告归档份数未计 2.5

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：仍写"复刻项目 5 份、非复刻 4 份"，加上关卡门后数量已变；"引用 Gate 0~3 结论（复刻含 0.5）"同样漏了 2.5。
- **证据**：`game-quality-gate/SKILL.md:360-361`
- **优化建议**：改为按"基数 + 条件门"表述，避免再随阶段增减而失效。
- **改造方案**：第 360 行改为"基数为 4 份（0/1/2/3）；复刻专线 +1（0.5）；关卡制 +1（2.5）"；第 361 行括注补 `关卡制含 2.5`。
- **预期效果**：归档数量随条件自动可算，不再硬编码。

#### ISSUE-009 Gate 2.5 的 G25-01 判据在两处不一致

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：references/13 说 LEVEL_PLAN 要"含 §0~§6 六节标题"，门禁实现说"含 §0/§1/§2/§3/§5"。执行者按契约写文档可能缺 §4/§6 被判过，或写全了却被按另一套判。
- **证据**：`game-level-design/references/13_pipeline_integration.md:93` vs `game-quality-gate/SKILL.md:114`
- **优化建议**：以门禁为准（它才是判定方），契约文档对齐。
- **改造方案**：`references/13:93` 判据改为 `含 §0 裁剪说明 / §1 关卡总览 / §2 阶段与目标曲线 / §3 参数口径 / §5 冲突与裁决`；若确实需要 §4/§6，则同步改门禁并升 G25 版本号。
- **预期效果**：契约与门禁同一判据，避免"写全反而判错"。

#### ISSUE-010 master 阶段编号与枚举项数不符

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**："阶段 1-5"后面枚举了 6 个环节（蓝图→规格→关卡难度→美术→资源/代码→集成），且"必走"与下一行"2.5 单局制可裁剪"语义打架。
- **证据**：`game-forge-master/SKILL.md:96-97`
- **优化建议**：编号与枚举对齐，并把"可裁剪"统一到 2.5 那一行。
- **改造方案**：第 96 行改为"阶段 1~5（蓝图→规格→美术→资源/代码→集成）**必走**；阶段 2.5 见下条"；第 97 行保留裁剪说明。
- **预期效果**：读一遍就能数清阶段，不再出现"1-5 却列 6 项"。

#### ISSUE-011 Gate 2.5 的 L2 集合比较可能没有基准

- **维度**：健壮性
- **严重级别**：WARNING
- **问题描述**：2.5.5 要求 `levels.json` 的 `level_id` 集合与"PRD 关卡表"完全相同，但 Gate 1 只校验「PRD 关卡数量 ↔ TECH_DESIGN 关卡配置类数量」（1.13），没有要求 PRD 关卡表**逐关可枚举且带 id**。若 PRD 只写"共 30 关"，Gate 2.5 的 L2 无从比较，会退化为人工判断。
- **证据**：`game-quality-gate/SKILL.md:123`（2.5.5）、`:207`（1.13）
- **优化建议**：把"关卡表可枚举"前置到 Gate 1，或让 Gate 2.5 在基准缺失时降级为 WARNING 并标注。
- **改造方案**：1) Gate 1 新增 `1.19 PRD 关卡表可机读（条件）`：关卡制项目 PRD 关卡章必须逐关列出 `level_id`（或连续编号）；2) 或改 2.5.5 判据为"PRD 有关卡表 → 严格比较；无 → 标注 `LEVEL_TABLE_MISSING` 并降为 WARNING"。
- **预期效果**：门禁不会因上游文档粒度不足而空转或误判。

#### ISSUE-012 轻量模式（SIM_SKIPPED）与 Gate 2.5 报告必填项的闭环未定义

- **维度**：健壮性
- **严重级别**：WARNING
- **问题描述**：master §四 允许"关卡数据已存在只做微调 → 轻量模式，只跑曲线+跳变，标 `SIM_SKIPPED`"，但 Gate 2.5 的 2.5.4 仍要求报告含"门禁结果"与"假设、置信度"、2.5.7 要求 `difficulty_gate.status=PASS`。轻量模式下这些字段是否必须存在，两份文档都没说。
- **证据**：`game-forge-master/SKILL.md:195` vs `game-quality-gate/SKILL.md:117`、`:125`
- **优化建议**：在 Gate 2.5 增加一句轻量模式豁免规则。
- **改造方案**：`game-quality-gate/SKILL.md` §2.2 追加："**轻量模式豁免**：报告标注 `SIM_SKIPPED` 时，2.5.4 只要求'门禁结果'节存在，'假设、置信度'可写'未做模拟，不适用'；2.5.7 的 `status` 允许为 `PASS_LIGHT`。"
- **预期效果**：轻量模式不再两种解读，避免为了过门禁硬跑全量模拟。

#### ISSUE-013 新增阶段的扩展流程缺"下游消费登记"这一环（根因）

- **维度**：扩展性
- **严重级别**：WARNING
- **问题描述**：这次接入只做了"总纲流程图 + 门禁 + 产物路径表"三处，漏了"谁是消费者"——于是 ISSUE-003/004 发生。总纲的"关键约束"要求下游按固定路径读取，但没有任何地方要求**新阶段声明其下游并在下游 skill 里登记消费方式**。下次再加阶段（如经济数值、存档迁移）会重犯。
- **证据**：`game-forge-master/SKILL.md:103`（关键约束只有"路径固定"）、`:233-245`（§五 只登记 references，无消费关系）
- **优化建议**：在 master 增加"新增阶段检查清单"，把"下游消费登记"设为必做项。
- **改造方案**：1) `game-forge-master/SKILL.md` §八 末尾新增 `阶段新增检查清单`：①流程图 ②裁剪规则 ③产物路径表 ④门禁检查项 ⑤**下游消费登记（逐个改下游 SKILL.md 的输入节）** ⑥references 索引 ⑦示例产物；2) 该项在 skill-auditor 的"四位一体"基准里补为第五位。
- **预期效果**：新阶段接入不再出现"上游写了契约、下游不知道"的单边契约。

#### ISSUE-014 master §五 "5 个 engine-checks-*.md（六引擎质量检查）"自相矛盾

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：实际只有 5 个 engine-checks 文件（phaser/pixi/godot/unity/three），纯 Canvas 无专项文件（L3 回落 phaser 的 typecheck）。"5 个"对、"六引擎"的表述让读者以为漏了一个文件。
- **证据**：`game-forge-master/SKILL.md:245`；实际目录 `game-quality-gate/references/` 仅 5 个 engine-checks-*.md
- **优化建议**：写明"5 个专项 + 纯 Canvas 复用 Web 通用检查"。
- **改造方案**：第 245 行改为 `5 个 engine-checks-*.md（六引擎中纯 Canvas 复用 Phaser 的 Web 通用检查）`。
- **预期效果**：新增引擎时不会有人去找不存在的 canvas 文件。

### INFO

#### ISSUE-015 两个 SKILL.md 处于 301-500 行的"可接受区间"

- **维度**：结构与体积
- **严重级别**：INFO
- **问题描述**：`game-forge-master` 418 行、`game-quality-gate` 425 行，未超 500 行红线，但已高于 ≤300 的推荐值。
- **证据**：`wc -l` → 418 / 425 / 180（level-design 180 行合规）
- **优化建议**：后续可把 gate 的 Gate 3 检查表（§6.2–6.4）与 master 的引擎决策树（§三）抽到 references。
- **改造方案**：非本次范围，记录待办即可。

#### ISSUE-016 新技能 description 已到 196 字符，接近 200 上限

- **维度**：结构与体积
- **严重级别**：INFO
- **问题描述**：再加一句就会超限，而 description 是路由的唯一依据。
- **证据**：`game-level-design/SKILL.md:3`（196 字符）
- **优化建议**：下次修改前先压缩中段的能力枚举。

#### ISSUE-017 references/13 有错别字"追加盟卡难度摘要"

- **维度**：一致性与契约
- **严重级别**：INFO
- **证据**：`game-level-design/references/13_pipeline_integration.md:15`
- **优化建议**：改为"追加关卡难度摘要"。

#### ISSUE-018 master §八 的质量门 glob 不覆盖小数门

- **维度**：一致性与契约
- **严重级别**：INFO
- **问题描述**：`docs/GATE_{0..3}_REPORT.md` 不含 0.5 / 2.5；虽各有单列行，但容易被当成全集读。
- **证据**：`game-forge-master/SKILL.md:379`
- **优化建议**：改为 `docs/GATE_{0,1,2,3}_REPORT.md`，并注明小数门见单列行。

#### ISSUE-019 Gate 0.5 / 2.5 归入 §二 子节，与其他 Gate 独立成章的分类逻辑不一致

- **维度**：一致性与契约
- **严重级别**：INFO
- **问题描述**：Gate 0/1/2/3 各占 §三~§六，而 0.5 与 2.5 作为 §2.1/§2.2 塞在总览章。好处是"条件门"聚在一起，坏处是找 2.5 的细则要回总览。
- **证据**：`game-quality-gate/SKILL.md:78`、`:103`
- **优化建议**：可选改为独立章，或在 §二 加一行"条件门细则见 §2.1/§2.2"的显式指引。

---

## 3. 优化建议 Top 3

### Top 1：统一阶段顺序（三份文档对齐 master）
- **ROI 评级**：⭐⭐⭐⭐⭐
- **收益**：高 —— 消除"两套顺序"，避免关卡阶段被排到美术后导致场景/主题数返工
- **成本**：低 —— 3 处文本替换，约 10 分钟
- **关联问题**：ISSUE-001
- **改造步骤**：
  1. 重画 `game-level-design/SKILL.md` §一 位置图
  2. 同步 `README.md` 位置图与 `references/13` 第 10 行
  3. grep `美术门之后` 确认无残留
- **预期效果**：三份文档 + master + gate 五处顺序一致；Gate 编号非单调由"门编号约定"统一解释

### Top 2：字段名与判据对齐（`score` → `difficulty_score`）
- **ROI 评级**：⭐⭐⭐⭐⭐
- **收益**：高 —— Gate 2.5 的 G25-03 从"必误判"变成"可过"
- **成本**：低 —— 2 处字段名 + 1 处判据，约 5 分钟
- **关联问题**：ISSUE-002、ISSUE-009
- **改造步骤**：
  1. 改 `SKILL.md:120`、`references/13:96`
  2. 对齐 `references/13:93` 与 gate 2.5.1 的章节判据
  3. 用 examples 的 levels.json 做一次键集合断言
- **预期效果**：文档 / 工具 / 门禁三方字段与判据一致

### Top 3：补齐下游接入（code-forge 加载约定 + integrate 目标带核对）
- **ROI 评级**：⭐⭐⭐⭐
- **收益**：高 —— Gate 3 的 3.28 从"必挂"变成可执行，难度闭环真正成立
- **成本**：中 —— 两个下游 skill 各加一节，含三引擎路径，约 30 分钟
- **关联问题**：ISSUE-003、ISSUE-004、ISSUE-013
- **改造步骤**：
  1. code-forge 加"关卡数据加载"节（Web/Godot/Unity 三条路径）+ 自检项
  2. integrate §十 加 10.5 目标带核对 + BUILD_REPORT 偏差表
  3. master 加"阶段新增检查清单"，含"下游消费登记"
- **预期效果**：新阶段成为真正闭环，而非"上游写契约、下游不知道"

---

## 4. 改造方案详情

### 方案 1：对应 Top 1 + Top 2（文档一致性，建议一起做）

**改动文件清单**：

| 文件 | 操作 | 说明 |
|---|---|---|
| `game-level-design/SKILL.md` | 修改 | §一 位置图重排；§六 `score`→`difficulty_score` |
| `game-level-design/README.md` | 修改 | 位置图重排 |
| `game-level-design/references/13_pipeline_integration.md` | 修改 | 第 10 行顺序、第 93/96 行判据与字段名、第 15 行错别字 |
| `game-quality-gate/SKILL.md` | 修改 | §一 第 12 行、description、§七 352/360-361、§九 417/421 |

**具体改动**：

#### `game-level-design/SKILL.md`
- 第 19–28 行：整块替换为
  ```text
  game-spec → docs/PRD.md + docs/TECH_DESIGN.md
     ↓ [Gate 1] 规格门
     ↓ 确认点 2
  【本 skill】game-level-design → docs/LEVEL_PLAN.md + config/levels.json + docs/DIFFICULTY_REPORT.md
     ↓ [Gate 2.5] 关卡门（game-quality-gate 执行）
  game-art-spec → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json
     ↓ [Gate 2] 美术门
     ↓ 确认点 3（简报含关卡难度摘要）
  game-asset-forge ∥ game-code-forge
     ↓ [Gate 3] 产物门（3.28 检查 levels.json ↔ src 引用一致性）
  ```
- 第 120 行：`score` → `difficulty_score`

#### `game-level-design/references/13_pipeline_integration.md`
- 第 10 行：`插在 Gate 2 美术门之后、确认点 3 之前` → `插在 Gate 1 规格门之后、Gate 2 美术门之前`
- 第 15 行：`追加盟卡难度摘要` → `追加关卡难度摘要`
- 第 93 行：判据对齐门禁 `§0/§1/§2/§3/§5`
- 第 96 行：`score` → `difficulty_score`

#### `game-quality-gate/SKILL.md`
- 第 12 行：`四个检查点` → `六个检查点（含 0.5 / 2.5 两个条件门）`
- 第 3 行：description 插入 `关卡后[Gate 2.5·关卡制]`
- 第 352 行：例外补 `2.5`
- 第 360–361 行：份数改为"基数 + 条件门"
- 第 417/421 行：`GATE_{N}` 与 `Gate 0~3` 表述补 2.5

**验证方法**：
```bash
cd "C:/Users/26307/.agents/skills"
# 1) 顺序一致性：应为 0 行命中（"关卡门在美术门之后"的老表述）
grep -rn "美术门之后" game-level-design/
# 2) 字段名一致性：只应命中 difficulty_score
grep -rn "difficulty_score" game-level-design/SKILL.md game-level-design/references/13*.md
# 3) 门禁陈旧文案
grep -n "四个检查点\|GATE_{N}_REPORT" game-quality-gate/SKILL.md
```

---

### 方案 2：对应 Top 3（下游接入）

**改动文件清单**：

| 文件 | 操作 | 说明 |
|---|---|---|
| `game-code-forge/SKILL.md` | 修改 | 新增"关卡数据加载"节 + 目录树注释 + 自检项 |
| `game-integrate/SKILL.md` | 修改 | §十 新增 10.5 目标带核对 |
| `game-forge-master/SKILL.md` | 修改 | 新增"阶段新增检查清单" |

**具体改动**：

#### `game-code-forge/SKILL.md`
- 目录树第 88 行注释：`# 关卡/数值` → `# 关卡数值：仅从 config/levels.json 读取，禁止硬编码`
- 在"读 PRD 数值表 → GameConfig.ts"（第 278 行附近）之后插入新节：
  ```markdown
  ### 关卡数据加载（存在 `config/levels.json` 时必读）
  | 引擎 | 加载方式 | 说明 |
  |---|---|---|
  | Phaser 3 / Pixi.js / 纯 Canvas / Three.js | `import levels from '../../../config/levels.json'`（`resolveJsonModule: true`） | 打包进 bundle，LevelConfig.ts 只做类型映射与按 level_id 取档 |
  | 同上（需热改数值） | 复制到 `public/config/levels.json` + `fetch` | 部署后可直接改 JSON，无需重打包 |
  | Godot 4 | `res://config/levels.json`（构建时复制进工程根）+ `JSON.parse_string` | 用 `FileAccess.get_file_as_string` 读 |
  | Unity | `Assets/StreamingAssets/config/levels.json` + `File.ReadAllText` | 只读，不参与编译 |

  **禁止**：把 `params` 的数值抄进 `LevelConfig.ts` / `GameConfig.ts` 常量，Gate 3 的 3.28 会查。
  无 `config/levels.json`（单局制裁剪）时，回退原 LevelConfig.ts 模式并在 README 注明。
  ```
- 自检清单追加：`- [ ] (关卡制) config/levels.json 存在时，src/ 中无关卡数值字面量`

#### `game-integrate/SKILL.md`
- §十 末尾新增：
  ```markdown
  ### 10.5 关卡目标带核对（存在 config/levels.json 时必做）
  读 `config/levels.json` 的 target_win / pred_win，与实际通关率逐关比对；
  |实际 − target| ≥ 15% 的关卡进 `docs/BUILD_REPORT.md` 偏差表，并回指 `docs/DIFFICULTY_REPORT.md`。
  无 levels.json → 标注 LEVEL_BALANCE_SKIPPED 跳过。
  ```
- 验收清单追加一行。

#### `game-forge-master/SKILL.md`
- §八 末尾新增"阶段新增检查清单"（7 项，含"下游消费登记"），见 ISSUE-013 方案。

**验证方法**：
```bash
cd "C:/Users/26307/.agents/skills"
grep -n "levels.json" game-code-forge/SKILL.md game-integrate/SKILL.md   # 均应有命中
grep -n "下游消费登记" game-forge-master/SKILL.md
```

---

## 5. 优先级矩阵

```
高收益 │ ②快速赢(优先做)          │ ①重大改造(计划做)
       │  Top1 顺序统一           │  Top3 下游接入
       │  Top2 字段/判据          │
       │──────────────────────────│──────────────────────
       │  ISSUE-017/018/019      │
低收益 │ ④低优先(有空做)          │ ③暂缓(不建议做)
       低成本                     高成本
```

| 象限 | 策略 | 关联建议 |
|---|---|---|
| ① 高收益高成本 | 列入计划，分阶段实施 | Top3（ISSUE-003/004/013） |
| ② 高收益低成本 | 立即执行 | Top1（ISSUE-001）、Top2（ISSUE-002/009） |
| ③ 低收益高成本 | 暂缓 | — |
| ④ 低收益低成本 | 有空再做 | ISSUE-017/018/019 |

---

## 6. 下一步建议

1. **立即执行**：Top1 + Top2（纯文档，10–15 分钟，消除 4 个 CRITICAL 中的 2 个）
2. **短期计划**：Top3 中的 code-forge 加载约定（否则 Gate 3 的 3.28 无法通过，关卡阶段等于白做）
3. **短期计划**：gate 的 4 处陈旧文案（ISSUE-005~008），约 10 分钟
4. **长期规划**：master 的"阶段新增检查清单"（ISSUE-013），防止下次接入重犯
5. **验证**：改造后重跑本审查（`skill-auditor` 流水线模式），确认 CRITICAL 归零

---

## 7. 修复记录（2026-11-10 15:40 执行）

**17 项已修复，2 项 INFO 延后**（015 行数抽离、016 description 压缩，均不影响运行）。

### CRITICAL 4/4 已修

| 编号 | 修复内容 | 改动文件 |
|---|---|---|
| ISSUE-001 | 位置图统一为「规格门 → 关卡门 → 美术门 → 产物门」，并补"为什么在美术之前"的理由与门号说明 | `game-level-design/SKILL.md` §一、`README.md`、`references/13` §1 |
| ISSUE-002 | `score` → `difficulty_score`，并注明"不排序分≠通关率" | `game-level-design/SKILL.md` §六、`references/13` §5 |
| ISSUE-003 | 新增 `§4.1 关卡数据加载`（Web/Godot/Unity 四条路径 + LevelConfig 职责边界 + 禁止清单）；§一 增"关卡制附加输入"；自检清单增一条；目录树注释改 | `game-code-forge/SKILL.md` |
| ISSUE-004 | 新增 `10.5 关卡目标带核对`（逐关偏差 + "模型偏 vs 目标偏"判定 + BLOCKER_SUSPECT + 偏差表模板）；验收清单增一条 | `game-integrate/SKILL.md` |

### WARNING 10/10 已修

| 编号 | 修复内容 | 改动文件 |
|---|---|---|
| ISSUE-005 | 「四个检查点」→「六个检查点（含 0.5 / 2.5 两个条件门）」 | `game-quality-gate/SKILL.md` §一 |
| ISSUE-006 | description 补「关卡后[Gate 2.5·关卡制]」与触发词「关卡难度校验」 | 同上 frontmatter |
| ISSUE-007 | 报告路径例外改为「小数门一律下划线」，§九 清单同步 | 同上 §七、§九 |
| ISSUE-008 | 归档份数改为「基数 4 + 复刻 +1 + 关卡制 +1」 | 同上 §七 |
| ISSUE-009 | `references/13` G25-01 判据对齐门禁（§0/§1/§2/§3/§5） | `references/13` §5 |
| ISSUE-010 | 「阶段 1~5」枚举去掉关卡难度，与 2.5 那行不再语义打架 | `game-forge-master/SKILL.md` |
| ISSUE-011 | Gate 1 新增 **1.19 关卡表可机读**（`G1-LEVEL-TABLE-NOT-ENUMERABLE`）+ Gate 2.5 增「基准缺失降级」 | `game-quality-gate/SKILL.md` §四、§2.2 |
| ISSUE-012 | Gate 2.5 增「轻量模式豁免」（`SIM_SKIPPED` → `PASS_LIGHT`） | 同上 §2.2 |
| ISSUE-013 | 总纲新增 **§8.1 阶段新增检查清单**（7 项，含⑤下游消费登记 + 反向核对命令）；skill-auditor 增 **§4.1.1** 并把该维度列为必查 | `game-forge-master/SKILL.md`、`skill-auditor/references/audit-extensibility.md`、`skill-auditor/SKILL.md` |
| ISSUE-014 | engine-checks 表述改为「5 个专项 + 纯 Canvas 复用 Web 通用检查」 | `game-forge-master/SKILL.md` §五 |

### INFO 3/5 已修

| 编号 | 修复内容 | 状态 |
|---|---|---|
| ISSUE-017 | 「追加盟卡」→「追加关卡」 | ✅ |
| ISSUE-018 | 路径表 glob 改 `GATE_{0,1,2,3}` | ✅ |
| ISSUE-019 | §二 增「分类约定」指引（条件门细则见 §2.1/§2.2） | ✅ |
| ISSUE-015 | master/gate 抽离至 ≤300 行 | ⏸ 延后（现 4xx 行未超红线） |
| ISSUE-016 | description 压缩留余量 | ⏸ 延后（196 字符仍合规） |

### 修复后验证

```text
自测                     20/20 通过
模板战役 --strict        退出码 0（PASS）
示例战役 --strict        退出码 1（FAIL，符合预期）
导出关卡配置             6 关 / schema 1.0 / gate PASS
必填字段                 含 difficulty_score ✓
下游消费登记 grep        5 个 SKILL.md 命中 levels.json（产出方 + 2 消费者 + 总纲 + 门禁）
顺序残留 grep            0 命中（"美术门之后"已全部清除）
```

---

## 附：审查元数据

- 审查工具：skill-auditor v1.0
- 审查规则版本：audit-structure.md / audit-consistency.md / audit-robustness.md / audit-extensibility.md
- 报告生成时间：2026-11-10T15:05:24+08:00
- JSON 工件路径：`docs/skill-audit-report.json`
- 上一版报告：`docs/SKILL_AUDIT_REPORT.prev.md`（2026-08-07 集合审查，非本次范围）
