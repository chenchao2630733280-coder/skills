# 09｜自动化评审流水线的数据契约

## 1. 为什么要定死契约

自动化评审最容易死在"输入不规范"而不是"算法不够好"。把输入格式固定下来，好处是：
设计表能导出、脚本能复用、结论能复算、报告能进 CI。

## 2. campaign.json 字段

```jsonc
{
  "campaign_id": "demo_match3_saga",      // 必填，报告标题
  "genre": "match3",                       // 必填，决定默认旋钮
  "version": "3.0.0-demo",                 // 配置版本，进报告
  "data_source": "synthetic",              // 数据来源说明，必填（写清是否真实）
  "mapping": {
    "spread": 4.0,                         // 难度分 -> logit 的分辨率，占位
    "ref_segment": "regular"               // 判定基准分层
  },
  "segments": {                            // 必填
    "regular": {"theta": 0.0, "theta_sd": 0.5, "target_first_try": 0.52}
  },
  "weights": {                             // 可选，缺省用内置 8 维权重，和必须为 1
    "resource_pressure": 0.20, "mechanic_load": 0.15
  },
  "feature_model": {                       // 可选：params -> 维度，允许只写部分维度
    "resource_pressure": {"kind": "ratio", "num": "target_amount", "den": "moves", "lo": 70, "hi": 280},
    "mechanic_load":     {"kind": "linear", "param": "obstacle_kinds", "lo": 0, "hi": 4},
    "operation_pressure":{"kind": "linear", "param": "combo_window_sec", "lo": 4, "hi": 16, "invert": true}
  },
  "legal_ranges": {"moves": [16, 30]},     // 可选：全局可调范围，关卡内可覆盖
  "thresholds": {"jump_winrate": 0.10},    // 可选：覆盖默认判据（慎用，见 12）
  "simulation": {"players_per_segment": 400, "batches": 8, "max_attempts": 5,
                 "retry_prob": 0.55, "seed_jitter_k": 0.55},
  "phases": [                              // 阶段意图：形状 + 起止目标首通率（参考分层）
    {"name": "教学", "from_index": 1, "to_index": 4, "shape": "ramp", "start_win": 0.86, "end_win": 0.74}
  ],
  "levels": [
    {"level_id": "L01", "index": 1, "tag": "TUTORIAL",
     "params": {"moves": 26, "target_amount": 1600},
     "features": {"goal_complexity": 0.10},   // 可选：直接给维度，覆盖派生值
     "new_mechanics": ["基础交换"], "notes": ""}
  ],
  "knobs": [                                 // 可选：覆盖默认旋钮
    {"param": "moves", "dim": "resource_pressure", "per_unit": -0.045,
     "step": 1, "max_delta": 6, "label": "可用步数", "note": "加步数=减压"}
  ]
}
```

### 关键约定

- **8 个维度**：`resource_pressure`、`mechanic_load`、`strategy_depth`、`randomness`、
  `operation_pressure`、`time_pressure`、`space_pressure`、`goal_complexity`，均归一化到 [0,1]。
- **`feature_model` 不是通用公式**：`lo`/`hi` 必须按项目实测取值，否则派生维度会失真。
  同一维度既可派生也可显式覆盖，混合使用是允许的。
- **`phases` 用通关率表达**，不用抽象分数：设计师说的是"这段想让 60% 的人首通"，不是"难度 0.44"。
- **`per_unit` 是敏感度**：每 1 个参数单位变化带来的维度变化，符号表示方向。它决定推荐引擎的步长，
  必须用单变量实验拟合，不要凭感觉填。
- **`max_delta`**：单次建议的最大改动，防止"一次加 3 种障碍"这种破坏性方案。

## 3. attempts.csv 字段

| 列 | 必填 | 说明 |
|---|---|---|
| `player_id` | 是 | 玩家标识 |
| `level_id` | 是 | 关卡标识，需与 campaign 对齐 |
| `won` | 是 | 1/0 |
| `attempt_index` | 否 | 第几次尝试；缺失时按文件顺序取首次 |
| `segment` | 否 | 分层标签，用于分层对比 |
| `booster_used` | 否 | 1/0，用于识别"靠道具过关" |
| `level_version` | 否 | 版本，用于排查版本混杂 |

口径：**分母是"进入过该关的玩家数"，不是尝试数**。首次通关率与最终通关率不可混用。

## 4. 各阶段输入输出

| 阶段 | 输入 | 输出 | 失败模式 |
|---|---|---|---|
| schema | campaign.json | 规范化关卡、派生特征 | 权重和≠1、维度越界、index 重复 → 抛配置错误 |
| curve | phases + segments | target_win / target_score 逐关 | 阶段未覆盖 → 自动延伸首末阶段 |
| score/mapping | 特征 + spread + θ | 难度分、分层预测首通率 | spread 未校准 → 绝对值失真（排序仍可用） |
| jump | 逐关记录 | 跳变清单（类型/严重度/证据） | 关卡太少（<3）→ 不做鲁棒阈值 |
| sim | 记录 + 模拟参数 | 分层首通/终通/尝试/道具/种子波动 | 参数过乐观 → 通关率虚高 |
| diagnose | 以上全部 + 真实数据 | 异常与卡点清单 | 无数据 → 只能给模型侧结论 |
| recommend | 诊断 + 旋钮 + 合法范围 | 单变量方案 | 无可用旋钮 → 输出"结构性调整"建议 |
| report | 全部 | review.md / json / 5 表 | 样本不足 → 标注不参与结论 |

## 5. 怎么接进现有流程

- **从表格导入**：让策划在 Excel 维护 `level_id, params...`，导出 CSV 后用几十行脚本拼成 campaign.json；
  不要手工维护两份数值。
- **进 CI**：把 campaign.json 与 attempts 快照放进仓库，`--strict` 作为门禁；HIGH 未清零不允许合入关卡改动。
- **做版本对比**：同一份 attempts 跑两个版本的 campaign.json，对比 `review.json` 里 `levels[].pred_win` 的差异，
  可以量化"这次改动到底改了多少难度"，比人肉看表可靠。

## 6. 常见错误

1. 用 `target_amount` 直接当难度：目标量上升但步数也上升时，实际难度可能不变——要用比值或派生维度。
2. 把所有维度都填 0.8：评分会告诉你"很难"，但说不出难在哪，推荐引擎也无从下手。
3. 阶段目标直接从上一版复制：目标与关卡实际脱节，报告会满屏 BAND_MISS——这时先怀疑目标，不是关卡。
4. 用全局中位数查参数离群：目标量本来就随进度爬坡，会误报一片（流水线已改为邻近关卡比较）。
