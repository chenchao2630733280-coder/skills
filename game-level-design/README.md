# Game Level Design — 流水线阶段 2.5

简体中文 | Version 3.1.0

`game-forge-master` 流水线的**阶段 2.5**：把 PRD 里的"难度曲线"变成
**可复算的关卡序列 + 可被代码直接加载的配置 + 带证据的评审报告**。

## 在流水线中的位置

```
game-spec → [Gate 1] 规格门
   ↓ 确认点 2
【阶段 2.5】game-level-design
   → docs/LEVEL_PLAN.md + config/levels.json + docs/DIFFICULTY_REPORT.md
   ↓ [Gate 2.5] 关卡门
game-art-spec → [Gate 2] 美术门（读关卡表定场景/主题数）
   ↓ 确认点 3（简报追加关卡难度摘要）
game-asset-forge ∥ game-code-forge  ← 后者消费 config/levels.json
   ↓ [Gate 3]（3.28 检查 levels.json ↔ src 引用一致性）
```

> 关卡表先定、美术后做：场景数与主题数由关卡清单决定，反过来会让美术返工。

| 产物 | 消费方 | 约束 |
|---|---|---|
| `docs/LEVEL_PLAN.md` | 策划/主策、确认点 3 | 六节固定结构，见 `references/13` |
| `config/levels.json` | `game-code-forge`（唯一关卡数据源） | 代码禁止内联复制关卡数值 |
| `docs/DIFFICULTY_REPORT.md` | `game-quality-gate`、`game-integrate` | 含门禁结论与假设声明 |
| `docs/DIFFICULTY_REVIEW.json` | Gate 2.5 / Gate 4 | 机读，与报告同源 |

## 六项能力

| # | 能力 | 实现 | 产物 |
|---|---|---|---|
| 1 | 自动生成难度曲线 | `cdl/curve.py` | 逐关目标首通率与难度分，支持 ramp/flat/spike/relief/wave/step |
| 2 | 自动检测难度跳变 | `cdl/jump.py` | 跳崖、断崖回落、多维同升、机制与难度同挤、锯齿、平推 |
| 3 | 自动模拟分层玩家 | `cdl/sim.py` | 首通/终通/放弃、尝试 P50、道具消耗、种子波动 |
| 4 | 自动识别异常与卡点 | `cdl/diagnose.py` | 偏离目标、近似无解、不稳定、认知过载、参数漏改、流失卡点 |
| 5 | 从真实数据反推参数 | `cdl/recommend.py` | 对齐邻近/渐进/一步到位/备选四类单变量方案 |
| 6 | 难度预测与评审报告 | `cdl/report.py` | `review.md` + 5 张表 + `review.json` |

## 目录

- `SKILL.md`：阶段契约（位置、输入输出、七步工作流、Gate 2.5 自检、降级策略）。
- `runtime.yaml`：skill-runtime 契约（inputs/outputs/degrade）。
- `tools/design_review.py`：评审 CLI；`tools/export_levels.py`：运行期关卡导出；`tools/selftest.py`：20 项规则自检。
- `tools/cdl/`：schema / score / mapping / curve / jump / sim / actuals / diagnose / recommend / report。
- `references/01–05`：难度模型库、评估框架、DDA 规范、关卡节奏、埋点与数据分析。
- `references/06–08`：模拟器接口规范、玩家能力与校准、上线治理。
- `references/09–12`：数据契约、跳变与异常分类、推荐引擎、门禁与验收。
- `references/13`：**流水线接入契约**（PRD→campaign 映射、levels.json schema、Gate 2.5 细则）。
- `templates/`：campaign 模板、参数表、关卡评审表、指标字典、模型卡、验收清单。
- `examples/`：16 关示例战役（含刻意埋入的问题）、示例通关数据、示例报告。

## 快速开始

```bash
# 1) 纯模型预测
python tools/design_review.py --campaign examples/campaign_demo.json --out review_out

# 2) 接入真实通关数据
python tools/design_review.py --campaign examples/campaign_demo.json \
    --attempts examples/attempts_campaign.csv --out review_out

# 3) 门禁（存在 HIGH 级问题返回非 0）
python tools/design_review.py --campaign xxx.json --strict

# 4) 导出运行期关卡配置
python tools/export_levels.py --campaign xxx.json --review review_out/review.json \
    --out config/levels.json --require-pass

# 5) 规则自检
python tools/selftest.py
```

## 算例：示例战役会被判成什么样

`examples/campaign_demo.json` 是 16 关三消战役，刻意埋了典型问题：

- L05–L08 连续平推（复制关卡未调），目标却在爬坡 → PLATEAU + 连续偏离目标；
- L09 同时引入两个新机制并把难度拉高 → CLIFF + MECHANIC_SPIKE + OVERLOAD + BLOCKER；
- L10 步数从 22 掉到 12 → CONFIG_OUTLIER，推荐"对齐邻近关卡"（12→22）；
- L12 目标量与障碍拉满 → 预测首通 27%、种子波动大 → BLOCKER + UNSTABLE；
- L13 骤降 30 个百分点 → DIP；L13–L16 反复起落 → SAWTOOTH；
- 真实数据里 L06 实际 40% vs 预测 75% → PRED_ACTUAL_DIVERGENCE（先查模型，别改关卡）；
- L15 只有 12 个样本 → DATA_GAP（不做结论）。

完整报告见 `examples/sample_report/review.md`。

## 设计原则

1. 设计难度、预测难度、实际难度、目标体验分开记录，不混用。
2. 评分只用于排序与诊断，不宣称为通关概率；`spread`、θ、权重、`per_unit` 都是待校准占位值。
3. 先诊断难度来源，再调参数；一次只动一个参数。
4. 随机性导致的不稳定，不能靠调均值难度解决。
5. 推荐是待验证假设，必须灰度验证、预设护栏与回滚。
6. 模拟是替代模型，不替代真机测试与真实玩家数据。

## 与 v3.0（casual-game-difficulty-design）的差异

- **更名并接入流水线**：`casual-game-difficulty-design` → `game-level-design`，成为 `game-forge-master` 的阶段 2.5。
- **新增运行期产物**：`config/levels.json`（下游代码唯一数据源）+ `docs/LEVEL_PLAN.md` + 固定路径的评审报告。
- **新增导出工具** `tools/export_levels.py`（含 `--require-pass` 门禁联动）。
- **新增接入契约** `references/13`：PRD→campaign 映射、levels.json schema、Gate 2.5 八条检查项。
- **新增 runtime.yaml**：inputs/outputs/degrade 与流水线一致。
- 六项能力与检测算法未变，仍为 v3.0 实现；参考文档 01–12 保留。

## 已知边界

- 模拟器是"能力 θ vs 难度 b"的替代模型，不含棋盘/求解器；绝对通关率不可对外承诺。
- `feature_model` 的 `lo/hi` 与 `per_unit` 必须按项目实测，否则派生维度与推荐步长都会偏。
- 单变量搜索只在 `knobs` 覆盖的维度上工作；机制层面的问题（例如"这关机制本身不成立"）需要人工判断。
- PRD 是自由文本，没有自动解析器；`references/13` 给的是映射表，落表仍需人（或 AI）判断。
