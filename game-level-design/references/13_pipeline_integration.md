# 13｜与 game 流水线的接入契约（阶段 2.5）

本文件定义本 skill 在 `game-forge-master` 流水线里的所有接口。改动本文件等于改接口，
必须同步 `game-forge-master` §七/§八 与 `game-quality-gate` 的 Gate 2.5。

## 1. 阶段定位

| 项 | 值 |
|---|---|
| 阶段编号 | **2.5**（插在 Gate 1 规格门之后、Gate 2 美术门之前） |
| 必走条件 | PRD 含关卡序列 / 难度递进 / 关卡目标 |
| 可裁剪条件 | 单局制、无关卡序列（2048、单屏街机、无尽模式无阶段目标） |
| 裁剪但不许省略 | 必须产出 `docs/LEVEL_PLAN.md` 占位（写"无关卡序列 + 难度靠 X 机制"），Gate 2.5 按占位文档通过 |
| 质量门 | **Gate 2.5 关卡门**（L1 静态 + L2 契约） |
| 人工确认 | 不新增确认点；并入**确认点 3** 的简报（追加关卡难度摘要） |

**为什么在美术之前**：场景数、主题数、UI 数量是由关卡清单决定的（N 个章节 → N 套主题），
先做美术规范再定关卡会让美术返工；同时阶段 2.5 也早于代码生成，
保证 `config/levels.json` 是代码的输入而不是事后补丁。

> **门编号说明**：门号沿用所属阶段号，所以执行顺序是"Gate 1 → Gate 2.5 → Gate 2"（编号不递增）。
> 引用门号时以 `game-forge-master` §七 的顺序为准。

## 2. 产物清单

| 产物 | 路径 | 说明 |
|---|---|---|
| 关卡设计说明 | `docs/LEVEL_PLAN.md` | 人读。§0 裁剪说明 / §1 关卡总览 / §2 阶段与目标曲线 / §3 参数口径与可调范围 / §4 旋钮与敏感度 / §5 冲突与裁决 / §6 假设与待校准项 |
| 关卡作者手册 | `docs/LEVEL_AUTHORING.md` | 人读。**改关说明书**：上手步骤与常见坑 / 字段表 / 语义档位 / 旋钮有效区间与越界后果 / 构建期硬约束（每条带"为什么"）/ 生产路线 / 两种极端策略对跑验收 / 已知边界。模板 `templates/LEVEL_AUTHORING_template.md`。单局制可裁剪 |
| 运行期配置 | `config/levels.json` | 机读。**game-code-forge 的唯一关卡数据源** |
| 难度评审报告 | `docs/DIFFICULTY_REPORT.md` | 由 `tools/design_review.py` 生成的 `review.md` 原件或重命名副本 |
| 机读评审判定 | `docs/DIFFICULTY_REVIEW.json` | `review.json` 副本，含 `audit`（量尺与结构性判据），供 Gate 2.5 / game-integrate 读取 |
| 关卡门报告 | `docs/GATE_2_5_REPORT.md` | 由 `game-quality-gate` 产出，本 skill 不写 |

> 不要改名、不要改路径。下游按固定路径读取。

## 3. PRD → campaign.json 映射

PRD 是自由文本，映射靠人（或 AI）读出来，不靠解析器。按下表逐项落地：

| campaign 字段 | PRD 里的来源 | 缺失时 |
|---|---|---|
| `genre` | §游戏类型 / 核心玩法 | 必问，无法假设 |
| `segments` | §目标用户 / 玩家分层 | 用 −0.9 / 0 / +0.95 占位，标注假设 |
| `phases` | §难度曲线 / §关卡节奏 / 章节划分 | 按关卡数均分 3–4 段，形状默认 ramp |
| `levels[].params` | §关卡表（步数/时间/目标量/障碍…） | 按品类默认值生成，标注假设 |
| `legal_ranges` | §可调参数及上下限 / 数值模型 | 取「当前值 ×0.6 ~ ×1.4」作探索区间，标注假设 |
| `feature_model` | 无直接来源，由品类知识给出 | 用 `references/01` 的模型库自拟，并写明归一化区间来源 |
| `knobs.per_unit` | §数值敏感度 / 拆解数值模型 | 用内置品类默认值，标注"未校准" |
| `data_source` | 是否有线上数据 | 必须写实：`未接入` / `synthetic` / 真实数据窗口 |

**复刻专线**：若存在 `docs/NUMERIC_MODEL.csv`，把其中的数值区间直接搬进 `legal_ranges`，
把"每 +1 步 ≈ +X% 通关率"之类的敏感度搬进 `knobs.per_unit`，并在 `LEVEL_PLAN §5` 注明来源。

## 4. config/levels.json schema

```jsonc
{
  "schema_version": "1.0",
  "campaign": {
    "campaign_id": "my_saga_ch01",
    "genre": "match3",
    "version": "0.1.0",
    "level_count": 16,
    "data_source": "未接入",
    "exported_at": "2026-11-10T14:00:00+08:00",
    "model": {"spread": 4.0, "ref_segment": "regular", "weights": {"...": 0.2}, "status": "占位假设，需项目校准"}
  },
  "difficulty_gate": {"status": "PASS", "high_count": 0, "blocking_levels": [], "report": "docs/DIFFICULTY_REPORT.md"},
  "levels": [
    {
      "level_id": "L01",          // 必填，全局唯一，PRD 关卡表同名
      "index": 1,                  // 必填，正整数，连续
      "tag": "TUTORIAL",           // TUTORIAL/PRACTICE/STANDARD/CHALLENGE/BOSS
      "phase": "教学",             // 阶段名，与 LEVEL_PLAN §2 一致
      "params": {"moves": 26, "target_amount": 1600},
      "new_mechanics": ["基础交换"],
      "difficulty_score": 0.038,   // 0~1，仅用于排序与诊断，不等于通关率
      "target_win": 0.86,          // 目标首次通关率（参考分层）
      "pred_win": 0.856,           // 预测首次通关率
      "notes": ""
    }
  ]
}
```

**消费方约束**

- `game-code-forge`：按 `levels[].params` 生成关卡加载逻辑，`level_id`/`index` 直接用于解锁与进度存档；
  **禁止**把 params 抄进代码常量（Gate 3 会查 `src/` 里是否出现与 `levels.json` 不一致的内联数值）。
- `game-integrate`：Gate 4 数值平衡核对 `target_win` 目标带；实际通关率与 `pred_win` 差 ≥15% 时写进 `docs/BUILD_REPORT.md` 的偏差表。
- `game-quality-gate`：Gate 2.5 校验 schema 与 PRD 一致性；Gate 3 校验代码是否走样。

## 5. Gate 2.5 检查项

| 层 | # | 检查项 | 判据 | 失败码 |
|---|---|---|---|---|
| L1 | 1 | `docs/LEVEL_PLAN.md` 存在 | 含 §0 裁剪说明 / §1 关卡总览 / §2 阶段与目标曲线 / §3 参数口径 / §5 冲突与裁决 | G25-01 |
| L1 | 2 | `config/levels.json` 存在且合法 JSON | 可解析，`schema_version` 存在 | G25-02 |
| L1 | 3 | 必填字段完整 | 每关含 `level_id/index/tag/params/target_win/difficulty_score`（`difficulty_score` 是 0~1 的排序/诊断分，不是通关率） | G25-03 |
| L1 | 4 | `docs/DIFFICULTY_REPORT.md` 存在 | 含"门禁结果"与"假设、置信度"两节 | G25-04 |
| L1 | 10 | `docs/LEVEL_AUTHORING.md` 存在（关卡制） | 含上手 / 字段 / 旋钮**有效区间** / 硬约束（每条带"为什么"）/ 验收对跑 / 生产路线（选了哪条 + P1–P4 逐条裁决）六节；只有标题没有内容不算通过 | G25-10 |
| L1 | 9 | `config/levels.json` 通过交付物校验 | `validation.status == PASS`（导出时由 `export_levels.py` 内嵌，判据实现见 `tools/validate_levels.py`）；缺该块视为未校验，记 WARNING。*编号跳到 9 是为了不给 L2 的 5~8 重排，与失败码 `G25-09` 对齐* | G25-09 |
| L1 | 11 | `docs/LEVEL_GENERATOR_SPEC.md` 存在（**条件**：LEVEL_PLAN 声明生产路线为生成器/导入） | 与模板同构（九节）；其中 §2 的 Q1–Q5 每条有答案（开/砍 + 风险谁兜）且**工位 E 有结论**（默认开；关卡数 < 30 砍掉须在 §7 写明）、§4 四条不变量 I1–I4 逐条有裁决（不适用写原因）、§7 已知限制非空；手调路线记 SKIP 不记 FAIL | G25-11 |
| L2 | 5 | 关卡序列与 PRD 一致 | `levels.json` 的 `level_id` 集合与 PRD 关卡表**完全相同**（不多不少不改名） | G25-05 |
| L2 | 6 | 参数在合法范围内 | 每关 params ⊆ `legal_ranges` | G25-06 |
| L2 | 7 | 门禁状态可解释 | `difficulty_gate.status=PASS`，或 FAIL 项在 `LEVEL_PLAN §5` 有逐条处置 | G25-07 |
| L2 | 8 | 假设已标注 | `model.status` 非空，且报告含"假设、置信度"章节 | G25-08 |
| L2 | 12 | 阈值未被静默放宽（**条件触发**） | 仅当 `difficulty_gate.status` 由 FAIL 变 PASS 时：`docs/DIFFICULTY_REVIEW.json` 的 `thresholds` 与上一版逐项一致；有放宽且 `LEVEL_PLAN.md` 未记录理由即 FAIL。未做跨版本对比记 WARNING（`THRESHOLD_BASELINE_MISSING`），**不得默认通过** | G25-12 |

FAIL 处理：硬阻断，回本阶段重跑；**不允许**通过改阈值把 FAIL 变 PASS（Gate 会核对阈值是否被改动过）。

## 6. 占位文档（阶段被裁剪时）

```markdown
# LEVEL_PLAN — 阶段 2.5 裁剪说明

## §0 裁剪说明
本作无关卡序列（单局制 / 无尽模式），难度递进靠【速度递增 / 障碍密度 / 目标刷新】实现，
不产出 config/levels.json。难度目标：前 30 秒通关率 ≥70%，3 分钟后 ≤25%。

## §1–§6
不适用（由 game-spec 的 §数值设计 覆盖）。
```

Gate 2.5 见到 `§0 裁剪说明` 且写明理由即通过 L1；L2 的关卡一致性检查跳过。

## 7. 交接给确认点 3 的简报格式

```
关卡难度：16 关 / 4 阶段（教学 86%→74%、练习 72%→60%、组合 62%→48%、考核 55%→42%）
门禁：PASS（HIGH 0 / WARN 3）
主要风险：L09 新机制与难度同关（已拆教学）、L12 种子波动大（已限幅）
产物：config/levels.json（16 关）、docs/LEVEL_PLAN.md、docs/DIFFICULTY_REPORT.md
```
