# 示例数据说明

**所有数据均为虚构样例，用于演示格式与规则触发，不代表任何真实项目。**

## 文件

| 文件 | 说明 |
|---|---|
| `campaign_demo.json` | 16 关三消战役，`feature_model` 从 params 派生维度；刻意埋入典型问题（见下） |
| `attempts_campaign.csv` | 3.6k 行合成通关记录，含 `attempt_index` / `segment` / `booster_used` |
| `sample_report/` | 上面两个文件跑出的完整产物（`review.md` + 5 张表 + `review.json`） |
| `level_features.csv` | v2 遗留：纯特征表，可直接喂给 `tools/difficulty_scorer.py` |
| `attempts.csv` | v2 遗留：最小两类列，喂给 `tools/player_skill.py` |
| `calibration_data.csv` | v2 遗留：喂给 `tools/calibrate.py` |
| `genre_rules.json` | 各品类的主动模型与必查项 |
| `match3_example.json` / `merge_example.json` / `dda_config_example.json` | v1 遗留：跨品类示例与 DDA 配置 |

## demo 里刻意埋的问题

| 关卡 | 埋了什么 | 预期检出 |
|---|---|---|
| L05–L08 | 参数几乎不变，但阶段目标在爬坡 | PLATEAU、连续 BAND_MISS |
| L09 | 同一关引入「冰块 + 传送带」并把难度拉高 | CLIFF、MECHANIC_SPIKE、OVERLOAD、BLOCKER |
| L10 | `moves` 从邻近关卡的 22 掉到 12（复制漏改） | CONFIG_OUTLIER → 推荐"对齐邻近" |
| L12 | 目标量 6200 + 4 种障碍 + 4 个目标 + 7 色 | BAND_MISS、BLOCKER、UNSTABLE |
| L13 | 比 L12 骤降 30 个百分点 | DIP（若为刻意缓冲关应放行） |
| L13–L16 | 难度反复起落 | SAWTOOTH |
| L06 | 真实数据 40% vs 预测 75% | PRED_ACTUAL_DIVERGENCE |
| L15 | 只有 12 个样本 | DATA_GAP |

## 换成自己的数据

1. 把 `campaign_demo.json` 复制成你的战役文件，替换 `levels` / `phases` / `segments`；
2. 从埋点导出 `attempts.csv`（至少 `player_id, level_id, won`）；
3. 跑 `tools/design_review.py --campaign 你的.json --attempts 你的.csv --out out`；
4. 先看"预测 vs 实际"能否对得上，再谈调参。
