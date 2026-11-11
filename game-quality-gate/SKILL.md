---
name: "game-quality-gate"
description: "AI 游戏生成流水线的跨阶段质量门。在关键节点(拆解后[Gate 0.5·仅复刻专线]/蓝图后/规格后/关卡后[Gate 2.5·关卡制]/美术后/资源代码后)介入做契约校验与实跑预检,不通过则阻断流水线并给出修复建议。当被 game-forge-master 调度到检查点,或用户要'校验/门禁/质量检查/关卡难度校验/实跑验证游戏产物'时调用。"
---

# 游戏流水线质量门

## 一、定位与职责

本 skill 是 AI 游戏生成流水线的**跨阶段质检员**,解决"各 skill 自检宽松 + 实跑验证只在最后 + 错误累积到集成阶段才爆发"的结构性风险。

**核心机制**:三层门禁 × 六个检查点(含 Gate 0.5 与 Gate 2.5 两个条件门)。

| 层 | 名称 | 职责 | 不通过行为 |
|---|---|---|---|
| L1 | 静态门(Static) | 字段完整性 / 格式 / 命名 / 路径 | **阻断**,返回修复建议,不允许进入下一阶段 |
| L2 | 契约门(Contract) | 跨阶段一致性(PRD 节点树 vs 代码、manifest vs 实际文件) | **阻断**,返回差异清单 + 修复建议 |
| L3 | 实跑门(Runtime) | typecheck / 构建预检 / 浏览器启动自测 | **阻断**,返回错误日志供 game-code-forge 修复(本 skill 不修复) |

**与现有"质量检查清单"的区别**:
- 现有清单是各 skill 的**自我声明**,标准宽松,无阻断权
- 本 skill 是**独立第三方校验**,有阻断权,标准统一

**只读原则**:本 skill 不修改任何产物文件,只读 + 校验 + 输出报告。FAIL 即返回失败清单与修复建议,**修复由原产出 skill 重跑完成**,本 skill 不接管修复职责(避免职责越界与"自审自修"的伦理风险)。

**质量门范围**:本 skill 只管 **Gate 0.5~3**(0.5 拆解门[仅复刻专线]/0 蓝图/1 规格/2 美术/**2.5 关卡**[关卡制必走]/3 产物)。**Gate 4 实跑门**(typecheck+构建+浏览器自测+数值平衡)是 game-integrate 的内置最终验收,不属于本 skill 阻断体系,本 skill 仅在 §七引用其 `docs/BUILD_REPORT.md` 作为最终判定参考。

---

## 二、六个检查点

> 分类约定:Gate 0/1/2/3 各占独立章(§三~§六);两个**条件门** Gate 0.5 / 2.5 的细则统一放在本章 §2.1 / §2.2,便于集中查阅。

```
(复刻专线,仅当存在拆解产物)
game-teardown
    ↓
[Gate 0.5] 拆解门 ────────────────────────── L1(拆解产物自身完整性 + 假设可证伪性)
    ↓
game-blueprint
    ↓
[Gate 0] 蓝图门 ──────────────────────────── L1 静态
    ↓
game-spec
    ↓
[Gate 1] 规格门 ──────────────────────────── L1 + L2(PRD ↔ TECH_DESIGN)
    ↓
game-level-design
    ↓
[Gate 2.5] 关卡门 ────────────────────────── L1 + L2(levels.json ↔ PRD 关卡表)
    ↓
game-art-spec
    ↓
[Gate 2] 美术门 ──────────────────────────── L1 + L2(manifest ↔ PRD 节点树)
    ↓
┌──────────────────┐  ┌──────────────────┐
│ game-asset-forge │  │ game-code-forge  │  (并行)
└──────────────────┘  └──────────────────┘
    ↓
[Gate 3] 产物门 ──────────────────────────── L1 + L2 + L3 预检
    ↓
game-integrate (内含 Gate 4 实跑门,由其自检;复刻模式含数值区间核对 + 确定性回归)
    ↓
game-polish (可选)
```

> **门编号约定**:门号沿用所属阶段号(关卡门挂在阶段 2.5 上,故编号 2.5),因此编号不严格递增。实际执行顺序为 **规格门 → 关卡门 → 美术门 → 产物门**,引用门号时以本表顺序为准。

| 检查点 | 时机 | 层 | 检查内容 | 输出 |
|---|---|---|---|---|
| Gate 0.5 拆解门 | game-teardown 后(仅复刻专线) | L1 | 拆解产物完整性 + 假设可证伪性 | `docs/GATE_0_5_REPORT.md` |
| Gate 0 蓝图门 | game-blueprint 后 | L1 | 蓝图字段完整性 / 引擎选择合理性 / 范围可行 | `docs/GATE_0_REPORT.md` |
| Gate 1 规格门 | game-spec 后 | L1+L2 | PRD 节点树完整性 + TECH_DESIGN 与 PRD 引擎/目录一致 | `docs/GATE_1_REPORT.md` |
| Gate 2.5 关卡门 | game-level-design 后(关卡制必走) | L1+L2 | 关卡产物完整 + levels.json 与 PRD 关卡表/合法范围一致 | `docs/GATE_2_5_REPORT.md` |
| Gate 2 美术门 | game-art-spec 后 | L1+L2 | manifest 字段 + manifest 的 UI asset 与 PRD 节点树 1:1 对齐 | `docs/GATE_2_REPORT.md` |
| Gate 3 产物门 | game-asset-forge + game-code-forge 后 | L1+L2+L3 | manifest ↔ 实际文件 + 代码 UI 节点 ↔ PRD 节点树 + typecheck 预检 | `docs/GATE_3_REPORT.md` |

**Gate 4 实跑门**已由 game-integrate 内置(typecheck + 构建 + 浏览器自测 + 数值平衡;复刻模式追加数值区间核对与确定性回归,见 game-integrate §10.4),本 skill 不重复,只引用其 `docs/BUILD_REPORT.md` 作为最终判定依据。

### 2.1 Gate 0.5 拆解门(仅复刻专线)

**触发条件**:项目存在 `docs/GAME_TEARDOWN.md` 即必跑;不存在则整条跳过(非复刻项目)。

**输入**:`docs/GAME_TEARDOWN.md` + `docs/TEARDOWN_MATRIX.json` + `docs/NUMERIC_MODEL.csv`

**L1 静态检查**(拆解产物自身;本门运行时蓝图尚未产出,**只查拆解,不查下游**——下游消费检查在 Gate 0/1/2/3):

| # | 检查项 | 判据 | 失败码 |
|---|---|---|---|
| 0.5.1 | 三份产物齐全 | TEARDOWN.md / MATRIX.json / CSV 都存在且非空 | `G05-ARTIFACT-MISSING` |
| 0.5.2 | MATRIX 可解析 | JSON 可解析且过 `../game-teardown/references/teardown-matrix.schema.json` 约束 | `G05-MATRIX-INVALID` |
| 0.5.3 | 12 维覆盖 | `dimensions_covered` 为 1~12 全集 | `G05-DIMENSION-GAP` |
| 0.5.4 | X 项全有替代 | 所有 `class=X` 条目 `replacement` 非空 | `G05-X-NO-REPLACEMENT` |
| 0.5.5 | 差异点存在 | `differentiation` 非空(空 = 换皮) | `G05-NO-DIFFERENTIATION` |
| 0.5.6 | 推断可证伪 | 所有 `kind=inferred` 条目 `falsifier` 非空 | `G05-NO-FALSIFIER` |
| 0.5.7 | 数值挂接 | CSV 每行 `matrix_id` 都能在 MATRIX items 中找到;`in_mvp=true` 且为数值型的条目 `evidence ≥E2` | `G05-CSV-ORPHAN` |
| 0.5.8 | 覆盖率如实 | `evidence_coverage` 与报告头部"证据覆盖:N/12"一致;<0.6 时报告首行有 ⚠️ 标注(未标注才 FAIL) | `G05-COVERAGE-DISHONEST` |
| 0.5.9 | 修正史存在 | 报告含"修正史"章节且 MATRIX 含 `revisions` 字段(首版可为空) | `G05-NO-REVISION-LOG` |

**裁剪**:T0/T1 档位 0.5.3 允许存在"按档位裁剪"标注的维度,但**0.5.4 / 0.5.5 / 0.5.6 / 0.5.9 任何档位不可裁剪**。
**回退**:FAIL → 回 `game-teardown` 修复(补拆/补 falsifier/补替代),**不进蓝图**。

**拆解产物被下游消费的检查**不在本门,分别落在:Gate 0(0.7~0.9,M/X 消费进蓝图)、Gate 1(1.17~1.18,数值/状态机进 PRD)、Gate 2(2.15,X 隔离进 manifest)、Gate 3(3.27,参数落地进代码)、Gate 4(game-integrate §10.4,数值区间与确定性)。

### 2.2 Gate 2.5 关卡门(关卡制必走)

**触发条件**:`docs/PRD.md` 含关卡序列/难度递进即必跑;纯单局制(无关卡序列)时,只要 `docs/LEVEL_PLAN.md` §0 写明裁剪理由即可通过,**不产出 `config/levels.json`**。
本门在 `game-level-design` 之后、`game-art-spec` 之前执行(关卡表要先定,美术才知道要几套场景/主题),**FAIL 不进美术+资源+代码生成**。

**输入**:`docs/LEVEL_PLAN.md` + `config/levels.json` + `docs/DIFFICULTY_REPORT.md` + `docs/DIFFICULTY_REVIEW.json` + `docs/PRD.md`(关卡表);声明了生成器/导入路线时另加 `docs/LEVEL_GENERATOR_SPEC.md`(2.5.11)

**L1 静态检查**

| # | 检查项 | 判据 | 失败码 |
|---|---|---|---|
| 2.5.1 | 关卡设计说明存在 | `docs/LEVEL_PLAN.md` 含 §0 裁剪说明 / §1 关卡总览 / §2 阶段与目标曲线 / §3 参数口径 / §5 冲突与裁决 | `G25-01` |
| 2.5.2 | 关卡配置可解析 | `config/levels.json` 为合法 JSON 且含 `schema_version` | `G25-02` |
| 2.5.3 | 必填字段完整 | 每关含 `level_id/index/tag/params/target_win/difficulty_score` | `G25-03` |
| 2.5.4 | 评审报告存在 | `docs/DIFFICULTY_REPORT.md` 含"门禁结果"与"假设、置信度"两节 | `G25-04` |
| 2.5.9 | 关卡表通过交付物校验 | `config/levels.json` 的 `validation.status == PASS`(由 `game-level-design` 的 `export_levels.py` 导出时内嵌,判据实现 `tools/validate_levels.py`:字段/类型/id 唯一/index 连续/源↔表一致);**缺 `validation` 块**记 WARNING 而非 FAIL(兼容旧产物) | `G25-09` |
| 2.5.10 | 关卡作者手册存在(关卡制) | `docs/LEVEL_AUTHORING.md` 与模板同构,以下六项内容齐备:**§1 上手** / **§2 字段表** / **§4 旋钮有效区间**与越界后果 / **§5 构建期硬约束**(每条带"为什么存在") / **§6 生产路线**(选了哪条 + P1–P4 逐条给裁决,不适用的写"不适用"而不是留空) / **§7 两种极端策略对跑验收**;只有标题无内容不算通过 | `G25-10` |
| 2.5.11 | 生成器规格存在(条件:声明了生成器/导入路线) | 触发条件:`docs/LEVEL_PLAN.md` §0 或 §6 声明生产路线为"生成器/导入"(**含生成器下的反向构造与正向筛选两种策略;写成"反向生成"也按生成器处理,不因措辞漏触发**)。此时 `docs/LEVEL_GENERATOR_SPEC.md` 须与模板同构(九节),且其中:① §2 的 **Q1–Q5 每条都有答案**(开/砍 + 砍掉后风险由谁兜),且**工位 E 有明确结论**(默认开;关卡数 < 30 砍掉须在 §7 写明"难度序由人工给") ② §4 四条不变量(I1 容量守恒/I2 需求序⊑可达序/I3 干扰项可处置/I4 压力上界)**逐条有裁决**,不适用的写"不适用 + 原因" ③ §7 已知限制非空 —— 三条缺任一即 FAIL;手调路线跳过(记 SKIP 不记 FAIL) | `G25-11` |

**L2 契约检查**

| # | 检查项 | 判据 | 失败码 |
|---|---|---|---|
| 2.5.5 | 关卡序列与 PRD 一致 | `levels.json` 的 `level_id` 集合与 PRD 关卡表**完全相同**(不多、不少、不改名);`index` 连续正整数 | `G25-05` |
| 2.5.6 | 参数在合法范围内 | 每关 `params` 均落在 `legal_ranges`(缺省时以 PRD 可调参数上下限为准) | `G25-06` |
| 2.5.7 | 门禁结论可解释 | `difficulty_gate.status=PASS`;或为 FAIL 时 `LEVEL_PLAN.md §5` 对每个阻断关卡有逐条处置 | `G25-07` |
| 2.5.8 | 假设已声明 | `campaign.model.status` 非空,且报告"假设、置信度"章节未被删改 | `G25-08` |
| 2.5.12 | 阈值未被静默放宽(条件触发) | 仅当 `difficulty_gate.status` 由 FAIL 变 PASS 时检查:`docs/DIFFICULTY_REVIEW.json` 的 `thresholds` 与上一版逐项一致;有放宽且 `LEVEL_PLAN.md` 未记录理由即 FAIL。未跨版本对比时记 WARNING(`THRESHOLD_BASELINE_MISSING`),不得默认通过 | `G25-12` |

**防作弊**:若 `difficulty_gate.status` 由 FAIL 变 PASS,本门核对 `docs/DIFFICULTY_REVIEW.json` 的 `thresholds` 与上一版是否一致;阈值被放宽而未在 `LEVEL_PLAN.md` 记录理由的,判 `G25-12` FAIL(判据见 2.5.12)。

**回退**:FAIL → 回 `game-level-design` 修复(补产物/对齐关卡表/收窄参数/处置阻断项),重跑本门;**不允许**通过调宽阈值放行。

**轻量模式豁免**(报告标注 `SIM_SKIPPED` 时):2.5.4 只要求"门禁结果"节存在,"假设、置信度"可写"未做模拟,不适用";2.5.7 的 `status` 允许为 `PASS_LIGHT`(需注明跳过模拟的理由)。其余检查项不放宽。

**基准缺失降级**:若 PRD 关卡表未逐关列出(仅写"共 N 关"),2.5.5 无法做集合比较 → 标注 `LEVEL_TABLE_MISSING` 并降为 WARNING,同时要求 Gate 1 的 1.19 已在规格阶段拦下该情况。

**与 Gate 3 的分工**:本门只查"配置本身对不对";`game-code-forge` 是否把关卡数值内联复制到 `src/`、是否按 `levels.json` 加载,由 Gate 3 的 3.28 项检查。

---

## 三、Gate 0 蓝图门

### 3.1 输入
- `docs/GAME_BLUEPRINT.md`

### 3.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 0.1 | 必填字段 | 类型/平台/引擎/玩法/范围/复杂度 6 项齐全 | `G0-MISSING-FIELD` |
| 0.2 | 引擎枚举 | 值 ∈ {Phaser 3, Pixi.js, 纯 Canvas, Godot 4, Unity, Three.js} | `G0-INVALID-ENGINE` |
| 0.3 | 引擎-类型匹配 | 3D 类型 → Godot 4 / Unity / Three.js;2D → 任意 | `G0-ENGINE-TYPE-MISMATCH` |
| 0.4 | 范围可行 | 核心机制 ≤ 8 项 | `G0-SCOPE-OVER` |
| 0.5 | 一句话定义 | ≤ 30 字 | `G0-DEFINITION-TOO-LONG` |
| 0.6 | 玩家动机 | 蓝图 §4.5 三行(自主/胜任/关联)齐全且主导动机已选 | `G0-MOTIVATION-MISSING` |
| 0.7 | 复刻:定义两半(条件) | **仅复刻项目**(存在 `docs/GAME_TEARDOWN.md`):一句话定义含"复刻基底 + 原创差异点"两半;只写"做一个像 XX 的游戏"判 FAIL | `G0-CLONE-DEFINITION-ONE-SIDED` |
| 0.8 | 复刻:M 项进蓝图(条件) | **仅复刻项目**:`in_mvp=true` 的 M 项,每条都能在蓝图 §5 机制清单找到,且 `来源` 列标注其 `matrix_id`(如 `D2-01`);无 ID 可标的条目才按名称匹配 | `G0-CLONE-M-NOT-IN-BLUEPRINT` |
| 0.9 | 复刻:X 项隔离(条件) | **仅复刻项目**:蓝图 §6"不做"含 X 清单的替代说明;蓝图任何章节不引用原作专名/角色名 | `G0-CLONE-X-IN-BLUEPRINT` |

### 3.3 输出格式

```markdown
# Gate 0 蓝图门报告

- 检查时间:{ISO8601}
- 结论:{PASS | FAIL}
- 失败数:{N}(ERROR:{N1} / WARNING:{N2})
- 阻断规则:ERROR > 0 则 FAIL;WARNING 仅标记到报告,不阻断

## 失败清单
| # | 检查项 | 失败码 | 严重度 | 详情 | 修复建议 |
|---|---|---|---|---|---|

## 警告清单(WARNING,不阻断)
| # | 检查项 | 失败码 | 详情 | 建议处理 |
|---|---|---|---|---|

## 通过项摘要
{N} 项通过
```

---

## 四、Gate 1 规格门

### 4.1 输入
- `docs/GAME_BLUEPRINT.md`
- `docs/PRD.md`
- `docs/TECH_DESIGN.md`

### 4.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 1.1 | PRD 章节完整 | 玩法/数值/UI/关卡/状态机/系统清单/MDA/心流 8 章齐全 | `G1-PRD-SECTION-MISSING` |
| 1.2 | TECH_DESIGN 章节完整 | 引擎/目录/类设计/接口契约 4 章齐全 | `G1-TECH-SECTION-MISSING` |
| 1.3 | PRD UI 节点树 | 每个 UI 页面有节点树 | `G1-UI-TREE-MISSING` |
| 1.4 | TECH_DESIGN 引擎 | 与蓝图引擎一致 | `G1-ENGINE-MISMATCH` |

### 4.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 1.5 | PRD ↔ BLUEPRINT 类型 | PRD 的主类型与蓝图一致 | `G1-PRD-BLUEPRINT-TYPE-MISMATCH` |
| 1.6 | PRD ↔ TECH_DESIGN 引擎 | TECH_DESIGN 的引擎字段 = 蓝图引擎 | `G1-PRD-TECH-ENGINE-MISMATCH` |
| 1.7 | PRD ↔ TECH_DESIGN 目录 | TECH_DESIGN 目录结构与 PRD 引擎适配章节一致 | `G1-DIR-MISMATCH` |
| 1.8 | PRD UI 节点树命名 | 节点 id 命名规范(`page_element` 格式) | `G1-NODE-NAMING` |
| 1.9 | PRD MDA 框架 | PRD §1.0 三行(Mechanics/Dynamics/Aesthetics)齐全且因果链声明存在 | `G1-MDA-MISSING` |
| 1.10 | PRD 心流平衡 | PRD §2.4 心流区间定义 + 难度-技能对照表齐全且与蓝图主导动机一致(胜任主导→窄带,自主/关联主导→宽带) | `G1-FLOW-MISMATCH` |
| 1.11 | PRD 系统清单 | PRD §5 每个核心系统有输入/边界/依赖三字段 | `G1-SYSTEM-FIELD-MISSING` |
| 1.12 | PRD 数值表 ↔ TECH_DESIGN 数据结构 | PRD 中每个数值条目在 TECH_DESIGN 有对应 interface/字段 | `G1-NUMBER-STRUCT-MISMATCH` |
| 1.13 | PRD 关卡清单 ↔ TECH_DESIGN 关卡配置 | PRD 关卡数量与 TECH_DESIGN 关卡配置类支持数量一致 | `G1-LEVEL-CONFIG-MISMATCH` |
| 1.14 | PRD 状态机 ↔ TECH_DESIGN 类设计 | PRD 每个状态在 TECH_DESIGN 有对应状态字段/枚举/方法 | `G1-STATE-MACHINE-MISMATCH` |
| 1.15 | PRD 实体清单 ↔ TECH_DESIGN 类清单 | PRD 中定义的实体(角色/敌人/道具)在 TECH_DESIGN 有对应类 | `G1-ENTITY-CLASS-MISMATCH` |
| 1.16 | PRD 系统边界 ↔ TECH_DESIGN 类边界 | PRD §5"边界"列的"不做"项在 TECH_DESIGN 类设计中无对应实现(防越界) | `G1-SYSTEM-BOUNDARY-VIOLATED` |
| 1.17 | 复刻:数值来源(条件) | **仅复刻项目**:PRD §2 数值表每行带 `来源(matrix_id)` 与证据等级列;数值与 `docs/NUMERIC_MODEL.csv` 一致,无自编行 | `G1-CLONE-NUMBER-FABRICATED` |
| 1.18 | 复刻:M 项/状态机落地(条件) | **仅复刻项目**:`in_mvp` 的 M 项全部在 PRD §5/§2 出现;§6 状态机按对象/容器/场景三套拆,`visible`/`removable` 为两字段 | `G1-CLONE-M-NOT-IN-PRD` |
| 1.19 | 关卡表可机读(条件) | **仅关卡制项目**(PRD 含关卡序列/难度递进):PRD 关卡章必须**逐关可枚举**——每关有 `level_id`(或连续编号)+ 至少一个可验指标(目标/时限/步数);只写"共 N 关"而无逐关清单判 FAIL(否则 Gate 2.5 的 2.5.5 无基准可比) | `G1-LEVEL-TABLE-NOT-ENUMERABLE` |
| 1.20 | 机制规格完整(条件) | **仅当机制 ≥2 个或含分层/遮挡/连锁判定**:PRD §10 逐机制成节,每节六项齐全(规则/护栏/状态机/难度推导/视觉规格/扩展点);抽查「规则」写成可判定形式(不是散文)、「难度推导」用的是 `game-level-design` 的维度名 | `G1-MECHANIC-SPEC-INCOMPLETE` |
| 1.21 | 帧与确定性契约(条件) | **仅实时/帧驱动游戏**:TECH_DESIGN §11 的「时钟与节拍」「不变式」「终局判定」三项非空;每条不变式能指到至少一条断言(在 §11 或验证脚本清单中);死锁写成**充分判据**而非"试了几步没进展" | `G1-FRAME-CONTRACT-MISSING` |

> **核心价值**:1.9~1.16 把原本要拖到 Gate 4 数值平衡实测才暴露的"数值/关卡/状态机/系统边界不一致"提前到规格阶段。MDA 保证"机制-体验"因果链显式;心流保证"物理可玩≠心理好玩";系统边界防止范围蔓延到代码层。

---

## 五、Gate 2 美术门

### 5.1 输入
- `docs/PRD.md`(读 UI 节点树)
- `docs/ASSET_MANIFEST.json`
- `docs/ART_SPEC.md`
- `docs/AUDIO_SPEC.md`

### 5.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 2.1 | manifest 必填字段 | id/category/type/path/size/format/prompt/contentHash 8 项齐全 | `G2-MANIFEST-FIELD-MISSING` |
| 2.2 | contentHash 合法 | 每个 asset 有非空 contentHash | `G2-CONTENTHASH-MISSING` |
| 2.3 | predecessorId 规则 | id 首次出现时为 null,改名时填旧 id | `G2-PREDECESSOR-INVALID` |
| 2.4 | path 命名 | 与 game-forge-master §八路径表一致 | `G2-PATH-NAMING` |

> 风格基线声明检查移至 §5.3 的 2.14(条件检查,未命中基线时跳过)。

### 5.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 2.6 | manifest UI asset ↔ PRD 节点树 | manifest 中 category=ui 的 asset 与 PRD 每个 UI 节点对齐(1:1 或改名见 §5.4) | `G2-UI-NODE-MISMATCH` |
| 2.7 | manifest 无幽灵 UI asset | manifest 的 UI asset 都能在 PRD 节点树找到对应节点(含 predecessorId 追溯,见 §5.4) | `G2-UI-ORPHAN-ASSET` |
| 2.8 | manifest 无遗漏 UI 节点 | PRD 节点树的每个 UI 节点都有对应 manifest asset(含被 predecessorId 指向的旧节点) | `G2-UI-NODE-MISSING-ASSET` |
| 2.9 | 风格基线 prompt 引用 | 命中基线时,asset prompt 以 `[GAME ASSET]` 等标签开头 | `G2-PROMPT-NO-TAG` |
| 2.10 | manifest role asset ↔ PRD 实体清单 | manifest 中 category=role 的 asset 与 PRD 定义的角色/敌人实体对齐 | `G2-ROLE-ENTITY-MISMATCH` |
| 2.11 | manifest bg asset ↔ PRD 场景清单 | manifest 中 category=bg 的 asset 与 PRD 定义的背景/场景对齐 | `G2-BG-SCENE-MISMATCH` |
| 2.12 | manifest effect asset ↔ PRD 特效清单 | manifest 中 category=effect 的 asset 与 PRD 定义的特效事件对齐 | `G2-EFFECT-MISMATCH` |
| 2.13 | manifest audio ↔ AUDIO_SPEC 事件映射表 | manifest 中 `audio` 数组的条目与 AUDIO_SPEC §2.5 SFX 事件映射表对齐:每个事件 ID 有对应音频条目(**有文件**:`path` 非 null;**或合成音频**:`path` 为 null 且 §2.6 有同名合成参数行),每个条目被至少一个事件引用 | `G2-AUDIO-EVENT-MISMATCH` |
| 2.14 | ART_SPEC 风格基线声明(条件) | **仅当 PRD/TECH_DESIGN 命中已收录风格基线时检查** ART_SPEC 顶部有声明;未命中基线时跳过 | `G2-BASELINE-DECLARATION-MISSING` |
| 2.15 | 复刻:X 项隔离 + 风格坐标(条件) | **仅复刻项目**:manifest 无任何对应 `class=X` 条目的资源(按名称/语义匹配);ART_SPEC 有 `X→替代` 标注且调板/比例对齐 GAME_TEARDOWN §7 风格坐标系 | `G2-CLONE-X-IN-MANIFEST` |

> **核心价值**:Gate 2 是防止"布局调整后 manifest 与 PRD 脱节"的关键。若 PRD 节点树新增按钮但 manifest 没对应 asset,会在本门暴露,不会等到 game-integrate 才发现"代码引用了不存在的资源"。2.10~2.13 把校验范围从单一 UI 类扩展到全 5 类 asset(role/bg/effect/audio),覆盖所有跨阶段契约。

### 5.4 增量更新场景下的 1:1 校验规则

当 manifest 含 `predecessorId`(布局调整导致 asset 改名)时,2.6/2.7/2.8 的"1:1 对齐"按以下规则放宽,避免把改名 asset 误判为幽灵:

```
对于 manifest 中每条 asset A:
  若 A.predecessorId == null:
    → A.id 必须在 PRD 节点树找到对应节点(原 1:1 规则)
  若 A.predecessorId != null:
    → A.id 找不到对应节点是允许的(改名后新 id)
    → 但 A.predecessorId 必须能在上一版 manifest + PRD 节点树找到来源
    → 且 A.id 应能在 PRD 节点树找到"改名后的新节点"(通过节点 id 与 A.id 一致)

对于 PRD 节点树中每个节点 N:
  → N.id 在 manifest 找到对应 asset(直接命中,或被某 asset 的 predecessorId 指向)
  → 若两者都不命中,才是 G2-UI-NODE-MISSING-ASSET
```

**字段约束**:
- 本 skill 校验时,若 manifest 含 predecessorId,需同时读取上一版 manifest(命名为 `ASSET_MANIFEST.prev.json`,由 game-asset-forge 在增量 diff 时备份)做追溯
- 若 `ASSET_MANIFEST.prev.json` 不存在(首次生成或未做增量),predecessorId 字段应为 null,走原 1:1 规则

---

## 六、Gate 3 产物门

### 6.1 输入
- `docs/ASSET_MANIFEST.json`
- `docs/PRD.md`(UI 节点树 + 实体/场景/特效/音频事件清单)
- `docs/ASSET_ISSUES.md`(如有,识别降级为占位图的 asset)
- `docs/ASSET_MANIFEST.prev.json`(如有,用于 predecessorId 追溯)
- `assets/` 目录
- `src/` 目录(Web 引擎)或 Godot/Unity 工程
- `config/levels.json`(如有;3.28 的比对基准,单局制项目不存在)

### 6.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.1 | manifest asset 文件存在 | manifest 每个 asset 的 path/actualPath 对应文件存在 | `G3-FILE-MISSING` | ERROR |
| 3.2 | manifest actual* 回写 | game-asset-forge 已回写 actualFormat/actualPath | `G3-ACTUAL-NOT-WRITTEN` | ERROR |
| 3.3 | 无幽灵文件 | assets/ 下文件都能在 manifest 找到对应 id | `G3-ORPHAN-FILE` | WARNING(允许 .DS_Store/.gitkeep 等系统文件) |
| 3.4 | 工程入口存在 | Web:index.html;Godot:project.godot + Main.tscn;Unity:Assets/Scenes/Main.unity | `G3-ENTRY-MISSING` | ERROR |
| 3.5 | 占位图降级 asset 标注 | 读取 `docs/ASSET_ISSUES.md`,对降级为占位图(纯色+文字)的 asset 标 WARNING,不阻断 | `G3-PLACEHOLDER-DEGRADED` | WARNING |

> **占位图豁免**:game-asset-forge 失败时会降级为占位图(文件写到原 path,contentHash 重算),3.1/3.7 仍会 PASS,但语义错位(代码以为加载"开始按钮"实际是占位)。3.5 通过读 ASSET_ISSUES.md 识别这些 asset,在报告中标 WARNING 供人工后补,不阻断流水线。

### 6.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.6 | 代码 UI 节点 ↔ PRD 节点树 | 代码中创建的 UI 节点与 PRD 节点树 1:1 对齐 | `G3-CODE-UI-NODE-MISMATCH` | ERROR |
| 3.7 | 代码资源引用 ↔ manifest | 代码中引用的资源 id 都能在 manifest 找到 | `G3-CODE-REF-MISSING` | ERROR |
| 3.8 | manifest contentHash 一致 | assets/ 下文件与 manifest contentHash 一致(内容指纹校验) | `G3-CONTENTHASH-MISMATCH` | ERROR |
| 3.27 | 复刻:参数落地(条件) | **仅复刻项目**:`GameConfig` 类配置文件字段名与 CSV `parameter` 列同名;抽查 high 敏感参数在业务代码中无硬编码字面量(只允许出现在 config) | `G3-CLONE-PARAM-HARDCODED` | ERROR |
| 3.28 | 关卡数据走样(条件) | **仅关卡制项目**:关卡数据只能来自 `config/levels.json` 或其**引擎内等价副本**(Web:`src/config` 同级 import 根文件,或 `public/config/levels.json`;Godot:`res://config/levels.json`;Unity:`Assets/StreamingAssets/config/levels.json`);副本内容须与源文件一致(可 contentHash 比对);除该文件外 `src/` 中出现关卡数值字面量即失败(允许加载后计算);levels.json 必须存在且关卡数 > 0 | `G3-LEVEL-DATA-DRIFT` | ERROR |
| 3.29 | 提示/引导契约(条件) | **仅当 PRD §1.5 非"无"**:存在提示时,求解器规则与运行时同一实现(不得有第二份 `isLegal`/`apply`),且提示解可回放;存在引导时,`skipTutorial()`/`forceStep(id)` 已实现 | `G3-HINT-CONTRACT` | ERROR |

> **引擎特定 L2 检查(3.9+)**:按 PRD/TECH_DESIGN 的引擎字段读取对应 references 文件执行,检查项编号与失败码见各文件:
>
> | 引擎 | references 文件 | L2 检查项 |
> |---|---|---|
> | Phaser 3 | `references/engine-checks-phaser.md` | 3.9 anims key 一致 |
> | Pixi.js | `references/engine-checks-pixi.md` | 3.10 AnimatedSheet 帧数一致 |
> | Godot 4 | `references/engine-checks-godot.md` | 3.11 NodePath 一致 / 3.12 信号连接一致 |
> | Unity | `references/engine-checks-unity.md` | 3.13 Resources.Load 路径 / 3.14 SceneBuilder 产出 |
> | Three.js | `references/engine-checks-three.md` | 3.21~3.26 实例化/曲线/坐标契约 |
> | 纯 Canvas | 无(无引擎特定 L2 检查) | — |
>
> **新增引擎时**:只需新建 `references/engine-checks-{engine}.md` 并在上方表格登记,SKILL.md 不动。
>
> 这些错误在 Gate 4 才会以运行时 404/NullReference 爆发,本门提前静态拦截。

### 6.4 L3 实跑预检

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.18 | 依赖可解析 | Web 引擎:`npm ls` 无 missing;Godot/Unity:工程配置完整 | `G3-DEP-MISSING` | ERROR |

> **引擎特定 L3 实跑预检**:按引擎读取对应 references 文件的 §L3 小节执行,检查项编号与失败码见各文件:
>
> | 引擎 | references 文件 | L3 检查项 |
> |---|---|---|
> | Phaser 3 | `references/engine-checks-phaser.md` §L3 | 3.15 `npm run typecheck` |
> | Pixi.js | `references/engine-checks-pixi.md` §L3 | 3.15 `npm run typecheck` |
> | 纯 Canvas | 回退到 `references/engine-checks-phaser.md` §L3(Web 引擎通用 typecheck) | 3.15 `npm run typecheck` |
> | Godot 4 | `references/engine-checks-godot.md` §L3 | 3.16 `godot --headless --check-only --script scripts/main.gd` |
> | Unity | `references/engine-checks-unity.md` §L3 | 3.17 Unity 编译检查(沙箱无 Unity 时 SKIPPED,延后 Gate 4) |
> | Three.js | `references/engine-checks-three.md` §L3 | 3.15 typecheck / 3.19 build / 3.20 浏览器启动 |
>
> **新增引擎时**:只需在对应 `references/engine-checks-{engine}.md` 中补充 §L3 小节,SKILL.md 不动。

> **严重度分级**:ERROR = 硬阻断;WARNING = 标记到报告,继续流水线;SKIPPED = 软阻断,延后到 Gate 4 补。
>
> **L3 只检测不修复**:typecheck/Godot check 失败时,本 skill 只读错误日志并归类到失败清单,返回给 game-code-forge 修复。本 skill 不修改任何代码,避免"自审自修"的伦理风险与职责越界。自动修复由 game-code-forge 重跑时按其自身的修复策略执行(沿用其 §typecheck 修复策略,最多 3 轮)。

---

## 七、报告输出

每个 Gate 产出 `docs/GATE_{N}_REPORT.md`,格式统一见 §3.3。**小数门一律用下划线**:Gate 0.5 → `docs/GATE_0_5_REPORT.md`,Gate 2.5 → `docs/GATE_2_5_REPORT.md`(避开与整数门 `{N}` 模式的混淆)。

**阻断规则**:
- Gate 报告结论为 `FAIL` → game-forge-master 不允许进入下一阶段
- 失败清单含失败码 + 详情 + 修复建议,供原产出 skill 重跑时参考
- 修复后重跑本 Gate,直到 PASS 才放行

**报告归档**:
- 报告份数 = 基数 4 份(`GATE_0/1/2/3`)+ 条件门:复刻专线 +1(`GATE_0_5`)、关卡制 +1(`GATE_2_5`),随项目保留,作为质量追溯依据
- game-integrate 的 `docs/BUILD_REPORT.md` 应引用全部已生成 Gate 报告的结论(复刻含 0.5,关卡制含 2.5)

---

## 八、与 game-forge-master 的契约

### 8.1 接入位置

game-forge-master §七执行顺序修订为:

```
0.   (可选) game-topic-brainstorm
0.5  (可选·复刻专线) game-teardown
     → [Gate 0.5] 拆解门(失败则回到 0.5 修复,不进蓝图)
1. game-blueprint
   → [Gate 0] 蓝图门(失败则回到 1 修复)
2. game-spec
   → [Gate 1] 规格门(失败则回到 2 修复)
2.5 game-level-design(关卡制必走)
   → [Gate 2.5] 关卡门(失败则回到 2.5 修复,不进美术+资源+代码)
3. game-art-spec
   → [Gate 2] 美术门(失败则回到 3 修复)
4. game-asset-forge + game-code-forge(并行)
   → [Gate 3] 产物门(失败则回到 4 修复)
5. game-integrate(内含 Gate 4 实跑门;复刻模式含数值区间核对 + 确定性回归)
6. (可选) game-polish
```

### 8.2 失败回退策略修订

原 game-forge-master §六"所有失败都允许继续往下走"修订为**分级阻断**:

| 失败层级 | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0.5 FAIL(仅复刻专线) | **硬阻断**,**不进蓝图** | game-teardown 补拆(补 falsifier/补替代/补数值)后重跑 Gate 0.5 |
| Gate 0/1/2 FAIL | **硬阻断**,不允许进入下一阶段 | 原产出 skill 修复后重跑 Gate |
| Gate 2.5 FAIL(关卡产物缺失/与 PRD 关卡表不一致/参数越界/阻断项无处置) | **硬阻断**,不允许进入美术+资源+代码生成 | game-level-design 修复后重跑 Gate 2.5(禁止调宽阈值放行) |
| Gate 3 L1/L2 FAIL | **硬阻断** | game-asset-forge / game-code-forge 修复后重跑 Gate 3 |
| Gate 3 L3 typecheck/Godot check FAIL | **硬阻断**,返回错误日志 | game-code-forge 接手修复(沿用其自身 typecheck 修复策略,≤3 轮)后重跑 Gate 3 |
| Gate 3 L3 Unity 跳过 | **软阻断**(标注 SKIPPED),允许进入 Gate 4,由 game-integrate 补 | — |
| Gate 4 实跑(数值/浏览器) | **不属于本 skill**,沿用 game-integrate 现有策略(输出清单 + 截图,不阻塞构建) | 人工后补 |

### 8.3 裁剪规则

- **不可裁剪**:Gate 0/1/2.5/2/3 是流水线必走检查点,即使对应阶段被裁剪(如音频裁剪),也要跑 Gate 校验(音频裁剪时 Gate 2 检查 AUDIO_SPEC.md 标注"全部静音占位"即可通过)
- **条件裁剪**:Gate 2.5 仅在"纯单局制、PRD 无关卡序列"时跳过,且必须由 `docs/LEVEL_PLAN.md` §0 写明裁剪理由;有任一关卡序列字段就必须跑(见 2.2 触发条件)
- **可裁剪**:Gate 4 的浏览器自测与数值平衡实测,沿用 game-integrate 现有裁剪规则

---

## 九、质量检查清单

本 skill 自身的质量检查:

- [ ] 全部 Gate 的检查项无遗漏(对照本 skill §二~§六;条件门含 Gate 0.5 / 2.5)
- [ ] (复刻项目)Gate 0.5 的 L1 9 项都执行过,FAIL 已阻断回 game-teardown;Gate 0/1/2/3 的复刻条件检查(0.7~0.9/1.17~1.18/2.15/3.27)未遗漏
- [ ] (关卡制项目)Gate 2.5 的 L1 7 项(含 2.5.9 交付物校验、2.5.10 作者手册、2.5.11 生成器规格[条件]) + L2 5 项(含 2.5.12 阈值防放宽[条件])都执行过;Gate 1 的 1.19(关卡表可机读)已在规格阶段拦住"只写共 N 关"的情况
- [ ] 每个 Gate 都输出 `docs/GATE_{N}_REPORT.md`(小数门用下划线:`GATE_0_5_REPORT.md` / `GATE_2_5_REPORT.md`);**唯一例外是 Gate 4**:它由 `game-integrate` 内置执行,结论写在 `docs/BUILD_REPORT.md` 的 §2(各阶段结果)与 §3(视觉验收),不另出 Gate 报告
- [ ] 报告含失败码 / 详情 / 修复建议三要素
- [ ] FAIL 时有阻断,无"默认通过"
- [ ] **只读原则:本 skill 不修改任何产物文件,L3 失败仅返回日志交 game-code-forge 修复**
- [ ] **质量门范围:Gate 0/0.5/1/2.5/2/3 由本 skill 管,Gate 4 归 game-integrate 内置**
- [ ] Unity 跳过场景有降级路径(延后到 Gate 4)
- [ ] 增量更新场景下 predecessorId 改名不被误判为幽灵 asset(见 §5.3)
- [ ] 占位图降级 asset 在 Gate 3 标 WARNING 而非 ERROR(见 §6.2)
- [ ] **引擎特定检查(3.9+/3.15+)在 `references/engine-checks-{engine}.md` 维护,新增引擎只加文件不改 SKILL.md(见 §6.3/§6.4)**
