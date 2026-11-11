---
name: "game-level-design"
description: "AI 游戏生成流水线阶段 2.5。读取 PRD/技术设计，产出关卡难度曲线、运行期关卡配置 config/levels.json 与难度评审报告 docs/DIFFICULTY_REPORT.md；内置难度预测、相邻跳变检测、分层玩家模拟、异常卡点诊断与单变量参数推荐。当被 game-forge-master 调度到阶段 2.5，或用户要'设计/评审关卡难度、配关卡数值、排查卡点'时调用。"
version: 3.1.0
---

# Game Level Design — 阶段 2.5 关卡难度设计

本 skill 是 AI 游戏生成流水线的**阶段 2.5**，职责是把 PRD 里的"难度曲线"从一句话变成
**可复算的关卡序列 + 可被代码直接加载的配置 + 带证据的评审报告**。

它不产出美术、不写业务代码；它产出的是**数值契约**：关卡有哪些参数、每关该多难、为什么这么难。

---

## 一、在流水线中的位置

```
game-spec → docs/PRD.md + docs/TECH_DESIGN.md
   ↓ [Gate 1] 规格门
   ↓ 确认点 2
【本 skill】game-level-design → docs/LEVEL_PLAN.md + docs/LEVEL_AUTHORING.md + config/levels.json + docs/DIFFICULTY_REPORT.md
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
| 下游 | `game-integrate` | Gate 4 数值平衡核对 `docs/DIFFICULTY_REPORT.md` 的目标带 |
| 下游 | `game-quality-gate` | Gate 2.5 检查产物；Gate 3 检查代码是否走样 |

---

## 二、何时执行 / 何时裁剪

| 条件 | 动作 |
|---|---|
| PRD 含关卡序列、难度递进、关卡目标（三消/合成/解谜/塔防/跑酷关卡制） | **必走** |
| 单局制、无关卡序列（2048、单屏街机、无尽模式无阶段目标） | **可裁剪**，但必须产出 `docs/LEVEL_PLAN.md` 占位，写明"无关卡序列 + 难度递进靠 X 机制" |
| 关卡数据已存在且只做微调 | **走轻量模式**：只跑曲线 + 跳变（跳过模拟），报告中标注 `SIM_SKIPPED` |
| 复刻专线且 `docs/NUMERIC_MODEL.csv` 存在 | **必走**，先用拆解数值区间反解 `legal_ranges`，再按本流程配平 |

裁剪结果同时写入 `docs/LEVEL_PLAN.md` §0 与 `docs/GAME_BLUEPRINT.md` §10 的阶段裁剪建议。

---

## 三、输入不足时怎么办

按顺序处理，**不要凭空编造项目数据**：

1. **缺关卡数量/单局时长**：问一个最关键的问题（"这一章多少关、单局目标多少秒"），其余用假设并标注。
2. **缺数值口径**：从 PRD 的"可调参数"表推导；没有就按品类默认（见 `references/01`），标注为假设。
3. **缺真实数据**：正常跑纯模型预测，报告 `data_source` 写"未接入"，禁止把预测当实际。
4. **NUMERIC_MODEL 与 PRD 冲突**：以 PRD 为准，冲突项写入 `docs/LEVEL_PLAN.md` §5"冲突与裁决"，并交确认点 3 由人决策。

---

## 四、工作流（⓪ 选路线 → ⑦ 交门禁）

```
⓪ 选路线      这批关卡从哪来 → 手调 / 生成器 / 导入（判据见 references/14；生成器内部再选反向构造或正向筛选）
⓪b 定生成路径 仅生成器/导入路线：五工位开关 + 四不变量 → docs/LEVEL_GENERATOR_SPEC.md（见 references/15）
① 抽关卡表    PRD 关卡表 + 数值表 → campaign.json（映射见 references/13）
② 定曲线      phases：阶段划分、形状（ramp/flat/spike/relief/wave/step）、起止目标首通率
③ 跑评审      tools/design_review.py → 曲线/跳变/模拟/诊断/建议
④ 改参数      按诊断逐条单变量修正 → 复跑，直到 HIGH 清零或可解释
⑤ 导配置      tools/export_levels.py → config/levels.json（运行期唯一数据源）
⑥ 写三份文档  docs/LEVEL_PLAN.md（为什么这样设计）+ LEVEL_AUTHORING.md（手怎么动）+ LEVEL_GENERATOR_SPEC.md（仅生成器路线）
⑦ 交门禁      tools/validate_levels.py 过 → Gate 2.5（L1 产物完整 + L2 与 PRD 一致）
```

**⓪ 的判据只有一句**：这批关卡有没有**离散、可枚举、可序列化**的局面？没有（跑酷/平台跳跃/实时动作）就手调，
别写生成器——连续游戏没有"初盘→终局"的反推关系，可解性也不是构造能保证的。反向构造的五步骨架、
四条判据（P1 可解性由构造保证 / P2 解路数下限 / P3 步骤数≠难度 / P4 初盘退化必查）见 `references/14`。

**⓪b 只做一件事**：把"这个游戏需要哪几个生成工位、每站用什么算法"定下来，写进 `docs/LEVEL_GENERATOR_SPEC.md`。
五个工位（内容量化 / 资源分配 / 布局与依赖 / 可解性验证 / 难度打分）**每个都要用游戏事实换**，
换不到就砍掉——砍掉一站省一份实现和一份永远调不好的参数。四条不变量（容量守恒 / 需求序⊑可达序 /
干扰项可处置 / 压力上界）必须逐条给裁决，不适用也要写"不适用 + 原因"。选型与反例见 `references/15`，
动手写生成器时看 `references/16` 的伪代码（只给伪代码不给实现——状态表示必须按自己游戏重写）。

**关键纪律**：③→④ 至少走两轮。第一轮几乎总会暴露目标与关卡的矛盾（满屏 BAND_MISS），
这时先怀疑目标或数值口径，而不是逐关硬调——16 关全往一个方向偏，通常是 phases 定错了。

**改参数之前先看报告第 0 节**（量尺与契约体检）：它回答"这套分数本身可不可信"。
量尺坏了（维度恒定/顶格/未参与）时，后面的 CLIFF/BAND_MISS 全是噪声；出现「结构性必赢」时，
那几关的难度分描述的是一个不可能发生的事件，逐关调参没有意义。

---

## 五、工具

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

产物：`review_out/review.md`（报告正文，第 0 节为量尺与契约体检）、`review.json`（机读，含 `audit`）、
5 张表、`config/levels.json`（运行期配置）。导出到 `docs/` 时另落 `docs/DIFFICULTY_REPORT.md`（人读）
与 `docs/DIFFICULTY_REVIEW.json`（机读，Gate 2.5 的 2.5.7 与 `game-integrate` 的数值核对都读它）。

---

## 六、Gate 2.5 自检清单

交付前逐项确认（`game-quality-gate` 会按同一份清单复核）：

- [ ] `docs/LEVEL_PLAN.md` 存在，含：阶段划分、目标首通率区间、参数口径、被裁剪项说明、冲突裁决。
- [ ] `config/levels.json` 存在且可解析，字段符合 `references/13` 的 schema（`level_id/index/tag/params/target_win/difficulty_score`）。`difficulty_score` 是 0~1 的排序/诊断分，**不是**通关率（`pred_win` 才是）。
- [ ] `docs/DIFFICULTY_REPORT.md` 存在，`gate.status` 为 PASS，或 FAIL 项已在 `LEVEL_PLAN.md` 逐条说明处置。
- [ ] `docs/LEVEL_AUTHORING.md` 存在，含 §1 上手 / §2 字段 / §4 旋钮有效区间 / §5 硬约束（每条带"为什么"）/ §7 两种极端策略对跑 / §6 生产路线与 P1–P4 裁决；模板见 `templates/LEVEL_AUTHORING_template.md`。
- [ ] (走生成器/导入路线时)`docs/LEVEL_GENERATOR_SPEC.md` 存在，§2 五工位开关有答案、§4 四条不变量**逐条有裁决**（不适用也要写原因）；模板见 `templates/LEVEL_GENERATOR_SPEC_template.md`。
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

---

## 九、禁止事项

- 不把示例阈值/权重当行业标准；不把相关性当因果；不用小样本给精确结论。
- 不为了让 Gate 2.5 变绿而调宽阈值——改判据不等于把东西做对。
- 不推荐一次改多个参数；不超出 `max_delta` / 合法范围 / 单次 35%。
- 不对被判为"随机性不稳定"的关卡继续推荐随机性旋钮。
- 不在 `levels.json` 里写业务逻辑（它是数据，不是代码）；不让代码内联复制关卡数值。
- 不隐性操纵随机数制造付费压力；不把竞技/排行榜纳入不透明 DDA。

---

## 十、文件索引

- `tools/design_review.py` 评审 CLI；`tools/export_levels.py` 运行期导出；
  `tools/validate_levels.py` 交付物校验（结构 + 源↔表一致性 + 结构性必赢）；`tools/selftest.py` 规则自检。
- `tools/cdl/`：schema / score / mapping / curve / jump / sim / actuals / diagnose / recommend / report。
- `references/01–05`：难度模型库、评估框架、DDA 规范、关卡节奏、埋点与数据分析。
- `references/06–08`：模拟器接口规范、玩家能力与校准、上线治理。
- `references/09–12`：流水线契约、跳变与异常分类、推荐引擎、门禁与验收。
- `references/13`：**与 game 流水线的接入契约**（PRD→campaign 映射、levels.json schema、Gate 2.5 细则）。
- `references/14`：**关卡生产路线**（正向手调 / 反向生成 / 导入的适用判据、反向生成五步骨架、四条判据 P1–P4、什么时候别做这条路）。换游戏时先读它再决定用哪条路线。
- `references/15`：**生成路径的算法选型**（五工位开关：内容量化/资源分配/布局与依赖/可解性验证/难度打分；每站"什么时候不用这个算法"；四条不变量 I1–I4；反向 vs 正向的成本模型；何时才需要 C++/Rust）。走生成器/导入路线时读。
- `references/16`：**上述工位的算法伪代码**（量化/分配/布局/验证/打分五段 + 反向生成完整流程 + 三个"照抄会出错"的地方：精确分割下压力恒为 0、记忆化 key 漏字段、可见性缓存）。要动手写生成器时读。
- `templates/LEVEL_GENERATOR_SPEC_template.md`：`docs/LEVEL_GENERATOR_SPEC.md` 的九节模板（工位开关 + 不变量裁决 + 验证器规格 + 已知限制）。
- `templates/`：campaign 模板、参数表、关卡评审表、指标字典、模型卡、验收清单。
- `examples/`：16 关示例战役（含刻意埋入的问题）、示例通关数据、示例报告。
