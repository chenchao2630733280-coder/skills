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
【本 skill】game-level-design → docs/LEVEL_PLAN.md + config/levels.json + docs/DIFFICULTY_REPORT.md
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

## 四、七步工作流

```
① 抽关卡表    PRD 关卡表 + 数值表 → campaign.json（映射见 references/13）
② 定曲线      phases：阶段划分、形状（ramp/flat/spike/relief/wave/step）、起止目标首通率
③ 跑评审      tools/design_review.py → 曲线/跳变/模拟/诊断/建议
④ 改参数      按诊断逐条单变量修正 → 复跑，直到 HIGH 清零或可解释
⑤ 导配置      tools/export_levels.py → config/levels.json（运行期唯一数据源）
⑥ 写计划      docs/LEVEL_PLAN.md（人读：目标、口径、旋钮、假设、冲突裁决）
⑦ 交门禁      Gate 2.5（L1 产物完整 + L2 与 PRD 一致）
```

**关键纪律**：③→④ 至少走两轮。第一轮几乎总会暴露目标与关卡的矛盾（满屏 BAND_MISS），
这时先怀疑目标或数值口径，而不是逐关硬调——16 关全往一个方向偏，通常是 phases 定错了。

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

# 规则自检（20 项断言，确认检测器本身没坏）
python tools/selftest.py
```

产物：`review_out/review.md`（报告正文）、`review.json`（机读）、5 张表、
`config/levels.json`（运行期配置）。

---

## 六、Gate 2.5 自检清单

交付前逐项确认（`game-quality-gate` 会按同一份清单复核）：

- [ ] `docs/LEVEL_PLAN.md` 存在，含：阶段划分、目标首通率区间、参数口径、被裁剪项说明、冲突裁决。
- [ ] `config/levels.json` 存在且可解析，字段符合 `references/13` 的 schema（`level_id/index/tag/params/target_win/difficulty_score`）。`difficulty_score` 是 0~1 的排序/诊断分，**不是**通关率（`pred_win` 才是）。
- [ ] `docs/DIFFICULTY_REPORT.md` 存在，`gate.status` 为 PASS，或 FAIL 项已在 `LEVEL_PLAN.md` 逐条说明处置。
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

- `tools/design_review.py` 评审 CLI；`tools/export_levels.py` 运行期导出；`tools/selftest.py` 规则自检。
- `tools/cdl/`：schema / score / mapping / curve / jump / sim / actuals / diagnose / recommend / report。
- `references/01–05`：难度模型库、评估框架、DDA 规范、关卡节奏、埋点与数据分析。
- `references/06–08`：模拟器接口规范、玩家能力与校准、上线治理。
- `references/09–12`：流水线契约、跳变与异常分类、推荐引擎、门禁与验收。
- `references/13`：**与 game 流水线的接入契约**（PRD→campaign 映射、levels.json schema、Gate 2.5 细则）。
- `templates/`：campaign 模板、参数表、关卡评审表、指标字典、模型卡、验收清单。
- `examples/`：16 关示例战役（含刻意埋入的问题）、示例通关数据、示例报告。
