---
name: "game-level-design"
description: "AI 游戏生成流水线阶段 2.5。读取 PRD/技术设计，产出关卡难度曲线、运行期关卡配置 config/levels.json 与难度评审报告 docs/DIFFICULTY_REPORT.md；内置两套难度口径——离散可枚举局面走确定性（可解性证明 + naive/strict/golden 三态闸 + 静态压力分排序），连续/实时走模型预测与抽样，另含相邻跳变检测、异常卡点诊断与单变量参数推荐。当被 game-forge-master 调度到阶段 2.5，或用户要'设计/评审关卡难度、配关卡数值、排查卡点、给难度定口径'时调用。保证交付的难度数字可复现（同输入两次运行决策字段逐一相等）、可证伪、且闸门能红（注入坏关卡会 FAIL）。"
version: 3.2.0
---

# Game Level Design — 阶段 2.5 关卡难度设计

本 skill 是 AI 游戏生成流水线的**阶段 2.5**，职责是把 PRD 里的"难度曲线"从一句话变成
**可复算的关卡序列 + 可被代码直接加载的配置 + 带证据的评审报告**。

它不产出美术、不写业务代码；它产出的是**数值契约**：关卡有哪些参数、每关该多难、为什么这么难。

**两层分工**：难度方法论（三分量配方、旋钮实测、编号规则）的**本体**在
`content-difficulty-gate`，本 skill 不复制；本 skill 补的是流水线必需的**证明层、闸门纪律与
科学验收**（`references/17`）＋ **工程夹具契约**（`references/18`）。

---

## 一、在流水线中的位置

```
game-spec → docs/PRD.md + docs/TECH_DESIGN.md
   ↓ [Gate 1] 规格门
   ↓ 确认点 2
【本 skill】game-level-design → docs/LEVEL_PLAN.md + docs/LEVEL_AUTHORING.md + config/levels.json + docs/DIFFICULTY_REPORT.md(§0 评估口径) + docs/DIFFICULTY_REVIEW.json(evaluation 块)
   ↓ [Gate 2.5] 关卡门（game-quality-gate 执行）
game-art-spec → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json
   ↓ [Gate 2] 美术门
   ↓ 确认点 3（简报含关卡难度摘要）
game-asset-forge ∥ game-code-forge
   ↓ [Gate 3] 产物门（3.28 检查 levels.json ↔ src 引用一致性）
```

**为什么在这里**：关卡是"配置驱动"的中间产物——它需要 PRD 的数值口径（前置），
又必须**早于美术与代码生成**（后置）：早于美术，是因为场景数、主题数由关卡清单决定；
早于代码，是因为否则 `game-code-forge` 只能把难度写死在代码里。

**上下游契约**

| 方向 | 来源/去向 | 取用什么 |
|---|---|---|
| 上游 | `docs/PRD.md` | 核心循环、关卡数量、单局时长、可调数值、失败条件、玩家分层 |
| 上游 | `docs/TECH_DESIGN.md` | 配置加载方式、数据结构、`config/` 路径约定 |
| 上游（可选） | `docs/NUMERIC_MODEL.csv` | 复刻专线的数值区间，作为 `legal_ranges` / `per_unit` 初值 |
| 上游（可选） | 线上 `attempts.csv` | 真实首通/终通/道具使用，用于校准与预测背离检测 |
| 下游 | `game-code-forge` | `config/levels.json`（唯一数据源，不得内联复制） |
| 下游（人） | 策划 / 外包 | `docs/LEVEL_AUTHORING.md`（改关说明书：字段、档位、旋钮有效区间、硬约束、验收对跑） |
| 下游（工程） | 写生成器的人 / `game-code-forge` | `docs/LEVEL_GENERATOR_SPEC.md`（生成路径与算法规格，仅生成器/导入路线产出） |
| 下游 | `game-integrate` | Gate 4 核对：`sampled`/`telemetry` 档比目标带；`deterministic` 档改为核对闸门结论（实机重跑 + 实机试玩，无 `pred_win` 可用） |
| 下游 | `game-quality-gate` | Gate 2.5 检查产物；读 `DIFFICULTY_REVIEW.json` 的 `evaluation` 块（可复现证据 / 闸门自检 / 指标有效性，判据见 `references/18` §7）；Gate 3 检查代码是否走样 |

---

## 二、何时执行 / 何时裁剪

| 条件 | 动作 |
|---|---|
| PRD 含关卡序列、难度递进、关卡目标（三消/合成/解谜/塔防/跑酷关卡制） | **必走** |
| 单局制、无关卡序列（2048、单屏街机、无尽模式无阶段目标） | **可裁剪**，但必须产出 `docs/LEVEL_PLAN.md` 占位，写明"无关卡序列 + 难度递进靠 X 机制" |
| 关卡数据已存在且只做微调 | **走轻量模式**：只跑静态分 + 跳变（跳过模拟与穷举），报告中标注 `SIM_SKIPPED` 与 `PROOF_SKIPPED`，且 `evaluation.status` 记为 `PASS_LIGHT` |
| 复刻专线且 `docs/NUMERIC_MODEL.csv` 存在 | **必走**，先用拆解数值区间反解 `legal_ranges`，再按本流程配平 |

裁剪结果同时写入 `docs/LEVEL_PLAN.md` §0 与 `docs/GAME_BLUEPRINT.md` §10 的阶段裁剪建议。

### 2.1 先定评估档位（`tier`，必填）

**判据只有一句：能不能把"初盘→终局"枚举出来。**

| 档位 | 适用 | 判定用什么 | 排序用什么 | 铁律 |
|---|---|---|---|---|
| **`deterministic`** | 局面离散可枚举（三消/合成/堆叠/解谜/层叠消除/卡槽归集） | 可解性证明 + `naive` 必死 | 静态结构压力分 | 判定只认 L0/L1，排序只认 L2；L2 不得否决 L1 |
| `sampled` | 状态不可枚举、含随机发牌或连续动作（跑酷/动作/发牌类） | 抽样风险筛查，**不作判定** | 预测分 + 真实数据校准 | 抽样通关率**不得**进 gate 判定 |
| `telemetry` | 已接入线上真实数据 | 真实首通/终通 + 分层 | 实测曲线 | 样本 < 30 的关不做调参结论 |

档位与理由写进 `docs/LEVEL_PLAN.md §0`，机读值写进 `docs/DIFFICULTY_REVIEW.json` 的
`evaluation.tier`。**档位是一次性决定**：同一批关卡内不允许混用两套口径（混用 = 排序不可比）。

> 为什么要有这条闸：抽样通关率有三个硬伤（不可复现 / 不单调 / 混了机器人运气），
> 实测同一条命令当天跑出过 `0.94→0.51`、`0.48→0.55`、`0.78→1.00` 三组互斥读数。
> 详见 `references/17` §1。**不是"不够准"，是方向错。**

---

## 三、输入不足时怎么办

按顺序处理，**不要凭空编造项目数据**：

1. **缺关卡数量/单局时长**：问一个最关键的问题（"这一章多少关、单局目标多少秒"），其余用假设并标注。
2. **缺数值口径**：从 PRD 的"可调参数"表推导；没有就按品类默认（见 `references/01`），标注为假设。
3. **缺真实数据**：正常跑纯模型预测，报告 `data_source` 写"未接入"，禁止把预测当实际。
4. **NUMERIC_MODEL 与 PRD 冲突**：以 PRD 为准，冲突项写入 `docs/LEVEL_PLAN.md` §5"冲突与裁决"，并交确认点 3 由人决策。

---

## 四、工作流（⓪ 定口径 → ⑧ 交门禁）

```
⓪ 定评估口径   判 tier（§2.1）：deterministic / sampled / telemetry —— 定不下来不要往下走
⓪a 选路线      这批关卡从哪来 → 手调 / 生成器 / 导入（判据见 references/14；生成器内部再选反向构造或正向筛选）
⓪b 定生成路径 仅生成器/导入路线：五工位开关 + 四不变量 → docs/LEVEL_GENERATOR_SPEC.md（见 references/15）
① 抽关卡表    PRD 关卡表 + 数值表 → campaign.json（映射见 references/13）
② 定曲线      phases：阶段划分、形状（ramp/flat/spike/relief/wave/step）、起止目标首通率
③ 跑评估      双轨，按 ⓪ 的 tier 走：
                 · deterministic：静态分（秒级看曲线）→ 可解性证明 → 三态闸
                 · sampled / telemetry：tools/design_review.py → 曲线/跳变/模拟/诊断/建议
④ 改参数      按诊断逐条单变量修正 → 复跑，直到 HIGH 清零或可解释
⑤ 导配置      tools/export_levels.py → config/levels.json（运行期唯一数据源）
⑥ 写四份文档  docs/LEVEL_PLAN.md（为什么这样设计）+ LEVEL_AUTHORING.md（手怎么动）+ DIFFICULTY_REPORT.md（§0 评估口径，模板见 templates/DIFFICULTY_EVAL_section.md）+ LEVEL_GENERATOR_SPEC.md（仅生成器路线）
⑦ 复现自检    连跑两次 → tools/repro_check.py；不一致先修随机源，**不许先写报告**
⑧ 交门禁      tools/validate_levels.py 过 → Gate 2.5（L1 产物完整 + L2 与 PRD 一致 + evaluation 块证据齐）
```

**deterministic 轨的顺序不可换**：**先证明这关能过（L0），再用确定性打法判断它有没有决策（L1），
最后才用结构分排序（L2）**。反过来（先打分再证明）会把无解关算出一个漂亮的难度分，
而这个分数描述的是一个不可能发生的事件。三层定义与铁律见 `references/17` §2。

**⓪ / ⓪a 共用的判据只有一句**：这批关卡有没有**离散、可枚举、可序列化**的局面？没有（跑酷/平台跳跃/实时动作）就手调，
别写生成器——连续游戏没有"初盘→终局"的反推关系，可解性也不是构造能保证的。反向构造的五步骨架、
四条判据（P1 可解性由构造保证 / P2 解路数下限 / P3 步骤数≠难度 / P4 初盘退化必查）见 `references/14`。

**⓪b 只做一件事**：把"这个游戏需要哪几个生成工位、每站用什么算法"定下来，写进 `docs/LEVEL_GENERATOR_SPEC.md`。
五个工位（内容量化 / 资源分配 / 布局与依赖 / 可解性验证 / 难度打分）**每个都要用游戏事实换**，
换不到就砍掉——砍掉一站省一份实现和一份永远调不好的参数。四条不变量（容量守恒 / 需求序⊑可达序 /
干扰项可处置 / 压力上界）必须逐条给裁决，不适用也要写"不适用 + 原因"。选型与反例见 `references/15`，
动手写生成器时看 `references/16` 的伪代码（只给伪代码不给实现——状态表示必须按自己游戏重写）。

**关键纪律**：③→④ 至少走两轮。第一轮几乎总会暴露目标与关卡的矛盾（满屏 BAND_MISS），
这时先怀疑目标或数值口径，而不是逐关硬调——16 关全往一个方向偏，通常是 phases 定错了。

**改参数之前先看报告 §0**（评估口径与可复现性）：它回答"这份难度数字本身可不可信"。
`sampled` 轨看 §0 的量尺体检（维度恒定/顶格/未参与）——量尺坏了，后面的 CLIFF/BAND_MISS 全是噪声；
`deterministic` 轨看 §0.3 闸门自检与 §0.4 指标有效性——闸门失明或指标不可复现时，逐关调参没有意义。
两轨共同的硬规则：出现「结构性必赢 / 结构性不可达」时，那几关的难度分描述的是一个不可能发生的事件，先修结构。

---

## 五、工具

### 5.1 sampled / telemetry 轨（模型评审）

```bash
# 生成/复跑评审（无数据时纯模型预测）
python tools/design_review.py --campaign campaign.json --out review_out

# 接入线上真实通关数据（有则必接，用于校准与背离检测）
python tools/design_review.py --campaign campaign.json \
    --attempts attempts.csv --out review_out

# 门禁模式：存在 HIGH 级问题返回非 0，可直接作为阶段 2.5 的自检
python tools/design_review.py --campaign campaign.json --strict

# 导出运行期关卡配置（供 game-code-forge 加载）
python tools/export_levels.py --campaign campaign.json --review review_out/review.json \
    --out config/levels.json

# 交付物校验：config/levels.json 的结构与一致性（ERROR 阻塞，可直接当 Gate 2.5 的判据）
python tools/validate_levels.py --levels config/levels.json --campaign campaign.json

# 规则自检（34 项断言，确认检测器本身没坏）
python tools/selftest.py
```

### 5.2 deterministic 轨（证明 → 闸门 → 结构分）

五个工具、一个实现（契约见 `references/18` §0–§2）：

| 工具 | 干什么 | 特性 |
|---|---|---|
| `level_score`（库） | 结构压力分 + 诊断列 | 纯静态，秒级，无对局无随机 |
| `level_play`（库） | `naive / strict / greedy / golden` 四策略对局 | 一局一跑，无随机 |
| `level_audit`（库） | 可解性证明：贪心见证 → 有界穷举 → 三态结论 | 预算与结论分开记 |
| `score_table`（CLI） | 只出分与排序 | 改完关卡先看曲线，< 1 秒 |
| `gate_solver`（CLI） | 表格：证明 + 分 + 三态闸 + PASS/FAIL | 交门禁时看 |
| `level_designer`（CLI） | 同上，出 JSON + 退出码 | CI / 报告生成 |

```bash
# 只出分（改完关卡立刻看，不建 core）
python tools/score_table.py --dir data/levels

# 全量审计：证明 + 静态分 + 三态闸（8 关 / 24x24 约 8~10 秒）
python tools/gate_solver.py --dir data/levels

# 机读 + 退出码（0 全过 / 2 有关卡 FAIL / 3 输入坏）；CI 与报告都读它
python tools/level_designer.py --dir data/levels --out build/eval/gate.json

# 单关可解性未知时加大穷举预算（默认 400 节点）
python tools/level_designer.py --level 5 --nodes 8000

# 验草案：先放 build/level_design/proposed，验过再写回正式目录
python tools/gate_solver.py --dir build/level_design/proposed

# 可复现自检：连跑两次，逐字段比对，剔计时（**报告 §0.2 的证据就来自这里**）
python tools/level_designer.py --dir data/levels --out build/eval/run_a.json
python tools/level_designer.py --dir data/levels --out build/eval/run_b.json
python tools/repro_check.py --a build/eval/run_a.json --b build/eval/run_b.json \
    --marker LEVEL_DESIGNER_JSON= --json build/eval/repro.json
```

`repro_check.py` 是**通用**的（不依赖引擎、不依赖游戏规则），任何"两次运行应完全一致"的输出都能比。
它有三个必须的行为，缺一个就会骗人：

1. **剔计时按字段名、覆盖所有层级**（`entry.ms` / `policies.*.ms` 都要剔）——只剔顶层必然假 FAIL；
2. **比全字段，不只比结论**——`verdict` 相同不代表过程可复现；
3. **比对字段数 < 10 判 FAIL**——防"比了 0 个字段的 PASS"（闸门空转和闸门放行在日志里长得一样）。

**三个不许**：不许平行跑两个审计进程（实测会互相污染读数）；不许在审计里读网络或线上数据；
不许把计时字段写进报告结论（它不是难度，也不是稳定性指标）。

产物：`review_out/review.md`（报告正文，第 0 节为量尺与契约体检）、`review.json`（机读，含 `audit`）、
5 张表、`config/levels.json`（运行期配置）。导出到 `docs/` 时另落 `docs/DIFFICULTY_REPORT.md`（人读）
与 `docs/DIFFICULTY_REVIEW.json`（机读，Gate 2.5 的 2.5.7 与 `game-integrate` 的数值核对都读它）。

---

## 六、Gate 2.5 自检清单

交付前逐项确认（`game-quality-gate` 会按同一份清单复核）：

- [ ] `docs/LEVEL_PLAN.md` 存在，含：阶段划分、目标首通率区间、参数口径、被裁剪项说明、冲突裁决。
- [ ] `config/levels.json` 存在且可解析，字段符合 `references/13` 的 schema（`level_id/index/tag/params/target_win/difficulty_score`）。`difficulty_score` 是 0~1 的排序/诊断分，**不是**通关率（`pred_win` 才是）。
- [ ] `docs/DIFFICULTY_REPORT.md` 存在，`gate.status` 为 PASS，或 FAIL 项已在 `LEVEL_PLAN.md` 逐条说明处置。
- [ ] **评估档位已声明**（`docs/DIFFICULTY_REVIEW.json` 的 `evaluation.tier`），全批关卡同一档位，未混用两套口径。
- [ ] **（`deterministic` 轨）§0 评估口径节齐备**：报告头四件套（`tier` / `metric` / `normalization` / `data_source`）+ §0.1 口径声明 + §0.2 可复现证据 + §0.3 闸门自检 + §0.4 指标有效性 + §0.5 逐关判定 + §0.6 处置；模板见 `templates/DIFFICULTY_EVAL_section.md`。
- [ ] **可复现证据是跑出来的，不是写"已验证"三个字**：`evaluation.repro.verdict = pass` 且 `fields_compared ≥ 10`；差异只出现在计时字段。
- [ ] **闸门自检三条变异全红**（无解关 / 无决策关 / 难度倒挂）：`gate_selftest.detected` 三条齐。只红两条 = 闸门对第三类失明，此时"全量通过"比"红"更危险。
- [ ] **判定与排序没串位**：`naive` 能过的关一律 FAIL（除已登记豁免，豁免 ≤ `max(1, ⌈10%×关卡数⌉)` 且不计入通过率分子）；压力分高的关**不因分高**而 PASS。
- [ ] **指标可证伪**：`validity.falsifiers` 非空，且每条都能被现有工具产出观测（不是思想实验）。
- [ ] **归一化基准已声明**（`normalization.basis_version`）；跨版本比较只用相对序/分段比值，未拿绝对值直比。
- [ ] `docs/LEVEL_AUTHORING.md` 存在，含 §1 上手 / §2 字段 / §4 旋钮有效区间 / §5 硬约束（每条带"为什么"）/ §7 两种极端策略对跑 / §6 生产路线与 P1–P4 裁决；模板见 `templates/LEVEL_AUTHORING_template.md`。
- [ ] (走生成器/导入路线时)`docs/LEVEL_GENERATOR_SPEC.md` 存在，§2 的 Q1–Q5 每条有答案且工位 E 有结论、§4 四条不变量**逐条有裁决**（不适用也要写原因）；模板见 `templates/LEVEL_GENERATOR_SPEC_template.md`。
- [ ] `levels.json` 的关卡数量、`level_id` 序列与 PRD 关卡表**完全一致**（不多不少不改名）。
- [ ] 每关的 `params` 都落在 `legal_ranges` 内。
- [ ] 报告中的 `spread` / θ / 权重 / `per_unit` 状态已标注（占位 or 已校准），未把占位值写成结论。
- [ ] 若接入了真实数据：样本量 < 30 的关卡没有调参结论；预测与实际背离项已标注"先查模型"。

---

## 七、判读规则（诊断 → 动作）

| 信号 | 优先动作 |
|---|---|
| BAND_MISS | 看 `top_dims` 定位主因维度，再选旋钮；不要整体加难/减难 |
| CLIFF / MECHANIC_SPIKE | 拆开教学关与考核关，新机制不与难度上调同关 |
| DIP | 确认是否刻意缓冲；不是则把释放关抬回目标带 |
| OVERLOAD | 一次只抬一个维度，保留熟悉维度 |
| PLATEAU | 查是否复制关卡未调，确认留白意图 |
| UNSTABLE | 查初始局面/随机数生成，不要继续调均值难度 |
| NEAR_UNWINNABLE | 先跑求解器/种子回归确认可解性 |
| CONFIG_OUTLIER | 先"对齐邻近关卡"排除漏改，再谈调优 |
| PRED_ACTUAL_DIVERGENCE | 先查模型与埋点口径；预测不准时推荐值不可信 |
| DATA_GAP | 不调参，补样本 |
| BLOCKER | 最高优先级：跳变 + 低通关率叠加处 |

**`deterministic` 轨专属信号**（比上面那组更硬：它们是结构事实，不是统计推断）：

| 信号 | 含义 | 优先动作 |
|---|---|---|
| `NAIVE_WINS` | `naive` 也能通关 ⇒ 该关没有决策 | **动结构不动数值**：拆细单元、加数量、收容量、造无产出段。降难度或调阈值都没用 |
| `NAIVE_DIES_STEP1` | 开局一步就死 ⇒ 开局不可读 | 调**入口宽度**（开局可用色数 / 前排活卡数），不是降难度 |
| `T_UNSOUND` | `T ≥ 1` 但 `naive` 存活 | 查 `naive` 的走位顺序与 `shift_mode` 是否同一套（不等式只单向） |
| `PROOF_UNKNOWN` | 穷举预算用尽，可解性未定 | 加大 `--nodes`；**不许**调参过关，也不许写成"不可解" |
| `PROOF_UNSOLVABLE` | 确定无解 | 当 bug 处理，不进难度讨论 |
| `REPRO_DIFF` | 两次运行决策字段不一致 | 先修随机源（RNG/哈希序/目录序），指标在此之前一律作废 |
| `GATE_BLIND` | 注入坏关卡但闸门没红 | 闸门坏了，先修闸门——此时"全绿"是最坏的情况 |
| `SCORE_INVERSION` | 分数序与公认难易相反 | 锚点失配 ⇒ **改公式，不改关卡** |
| `NO_MONOTONE` | 放宽旋钮后分数反升 | 公式里有抵消项，不是关卡错 |
| `STAR_UNREACHABLE` | `golden` 峰值使 3★ 结构上不可达 | 修星级阈值，不是关卡错 |

---

## 八、降级策略

| 失败场景 | 降级动作 | 标注 |
|---|---|---|
| 无 PRD（用户直接要关卡） | 问 3 个问题（品类/关卡数/目标首通），其余按假设跑 | `data_source: assumptions` |
| 无真实数据 | 纯模型预测，绝对值不对外承诺 | `data_source: 未接入` |
| 时间紧，只做一轮 | 只跑曲线 + 跳变，跳过模拟 | `SIM_SKIPPED` |
| 无合法范围（legal_ranges 缺失） | 推荐引擎只给方向与相对幅度，不给具体数值 | `RANGE_MISSING` |
| 数值模型与 PRD 冲突 | 以 PRD 为准，冲突写入 §5 交人工裁决 | 确认点 3 决策 |
| 关卡数 > 50 | 按阶段分批评审，报告标注批次范围 | 分批产出 |
| 局面太大，穷举不可行 | 只跑贪心见证：找到即"可解"，找不到写 `unknown`（`proof.via=greedy_only`）**不写"不可解"** | `PROOF_WEAK` |
| 引擎含物理/随机，无法确定性重放 | 降档为 `sampled`：抽样只做风险筛查，判定转人工试玩或线上数据 | `tier: sampled` |
| 关卡数据在别的系统里（表格/后端） | 先导出成 JSON 快照再评，禁止对着线上库直接跑审计 | `SNAPSHOT` |

---

## 九、禁止事项

- 不把示例阈值/权重当行业标准；不把相关性当因果；不用小样本给精确结论。
- **不在 `deterministic` 档用抽样通关率当难度或判据**；不把已废弃口径的数字写进报告正文（作废声明除外）。
- **不在 `naive` 能过时报 PASS**（未登记的"教程关"不是理由）；不把 `strict`/`greedy` 的失败当"无解"证据。
- **不把 `unknown` 写成"不可解"**；不把"贪心没找到"当结论——它只触发穷举。
- **不把计时字段当稳定性指标**；不写"已验证可复现"却不给 `fields_compared`。
- **不并行跑两个审计进程**；不在审计里读网络或线上库。
- 不为让 Gate 2.5 变绿而放宽阈值/豁免比例——改判据不等于把东西做对。
- 不推荐一次改多个参数；不超出 `max_delta` / 合法范围 / 单次 35%。
- 不对被判为"随机性不稳定"的关卡继续推荐随机性旋钮。
- 不在 `levels.json` 里写业务逻辑（它是数据，不是代码）；不让代码内联复制关卡数值。
- 不隐性操纵随机数制造付费压力；不把竞技/排行榜纳入不透明 DDA。

---

## 十、文件索引

- `tools/design_review.py` 评审 CLI；`tools/export_levels.py` 运行期导出；
  `tools/validate_levels.py` 交付物校验（结构 + 源↔表一致性 + 结构性必赢）；`tools/selftest.py` 规则自检；
  `tools/repro_check.py` **可复现比对器**（两次运行逐字段比、按名剔计时、比字段数 < 10 判假 PASS；引擎无关，任何确定性工具的输出都能比）。
- `tools/cdl/`：schema / score / mapping / curve / jump / sim / actuals / diagnose / recommend / report。
- `references/01–05`：难度模型库、评估框架、DDA 规范、关卡节奏、埋点与数据分析。
- `references/06–08`：模拟器接口规范、玩家能力与校准、上线治理。
- `references/09–12`：流水线契约、跳变与异常分类、推荐引擎、门禁与验收。
- `references/13`：**与 game 流水线的接入契约**（PRD→campaign 映射、levels.json schema、Gate 2.5 细则）。
- `references/14`：**关卡生产路线**（正向手调 / 反向生成 / 导入的适用判据、反向生成五步骨架、四条判据 P1–P4、什么时候别做这条路）。换游戏时先读它再决定用哪条路线。
- `references/15`：**生成路径的算法选型**（五工位开关：内容量化/资源分配/布局与依赖/可解性验证/难度打分；每站"什么时候不用这个算法"；四条不变量 I1–I4；反向 vs 正向的成本模型；何时才需要 C++/Rust）。走生成器/导入路线时读。
- `references/16`：**上述工位的算法伪代码**（量化/分配/布局/验证/打分五段 + 反向生成完整流程 + 三个"照抄会出错"的地方：精确分割下压力恒为 0、记忆化 key 漏字段、可见性缓存）。要动手写生成器时读。
- `references/17`：**确定性难度评估的证明层与科学验收**——三层结构（L0 可解性 / L1 决策性 / L2 难度序）+ 三条铁律、可解性证明的三级强度与四条实现纪律、三态闸与豁免登记、科学验收五项（可复现 / 单调 / 可分 / 可证伪 / 锚点校准）、口径治理。**`deterministic` 档必读**，也是"改公式还是改关卡"的裁决依据。含两个最贵的坑：最优线峰值必须取"各策略最低"（否则 3★ 被误判不可达）、陷阱段必须在走位最前（否则 `T` 归因错）。
- `references/18`：**评估夹具工程契约**——五工具一实现、CLI 与退出码、`evaluation` 块 schema、`repro_check` 用法与实测读数、变异测试闸门自检（四类必须全红，含"假陷阱"这种归因错误）、性能禁忌、Gate 2.5 字段对接表、老项目迁移六步。要动手建工具链或接 CI 时读。
- `templates/DIFFICULTY_EVAL_section.md`：`docs/DIFFICULTY_REPORT.md` **§0 评估口径与可复现性**的整节模板（口径声明 / 可复现证据 / 闸门自检 / 指标有效性四问 / 逐关判定 / 汇总处置 + 九条自检）。
- `templates/LEVEL_GENERATOR_SPEC_template.md`：`docs/LEVEL_GENERATOR_SPEC.md` 的九节模板（工位开关 + 不变量裁决 + 验证器规格 + 已知限制）。
- `templates/`：campaign 模板、参数表、关卡评审表、指标字典、模型卡、验收清单。
- `examples/`：16 关示例战役（含刻意埋入的问题）、示例通关数据、示例报告。
