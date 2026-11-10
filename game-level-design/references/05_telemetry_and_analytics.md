# 05｜埋点与数据分析建议

## 1. 事件清单

| 事件名 | 触发时机 | 必要字段 |
|---|---|---|
| level_enter | 进入关卡 | player_id, level_id, level_version, attempt_id, segment |
| level_action | 每次关键操作 | action_type, action_index, board/state hash（必要时） |
| objective_progress | 目标进度变化 | objective_id, current, total |
| resource_change | 资源变化 | resource_type, delta, source |
| booster_use | 使用道具 | booster_id, source, action_index |
| continue_offer | 出现续关机会 | offer_type, resource_cost |
| continue_accept | 接受续关 | offer_type, payment/source |
| level_fail | 失败 | fail_reason, progress, remaining_resource, duration |
| level_win | 胜利 | remaining_resource, duration, score |
| level_exit | 主动退出/中断 | action_index, progress, duration, exit_reason |
| hint_show | 提示展示 | hint_type, trigger_reason |
| dda_offer | DDA辅助出现 | assist_type, trigger_reason, model_version |
| dda_accept | 接受辅助 | assist_type |
| survey_response | 问卷回答 | question_id, answer, context |

遵循数据最小化原则，不采集与分析目的无关的个人信息。

## 2. 通用字段

- `player_id`：匿名化稳定标识；
- `session_id`；
- `level_id`；
- `level_version`；
- `attempt_id`；
- `event_time`；
- `player_segment`；
- `experiment_group`；
- `random_seed`（随机玩法）；
- `client_version`；
- `device_tier`（性能影响玩法时）。

## 3. 数据质量检查

- 同一attempt是否有且仅有合理的开始/结束；
- 重复事件与离线补发；
- 事件时间乱序；
- 后台挂起时长；
- 版本变更；
- 随机种子缺失；
- 玩家跨组；
- 指标分母口径变化。

## 4. 看板分层

### 关卡总览
关卡ID、设计难度分、首次/最终通关率、失败次数、耗时、资源消耗、下一关继续率。

### 难度异常
与相邻关卡、同标签关卡、同机制关卡对比，标出异常跳变。

### 玩家分层
新手、普通、熟练、高水平；每层展示通关与资源分布。

### 随机性
按种子/初始状态比较通关率、极端坏局和可解率。

### DDA监控
触发率、接受率、调节幅度、冷却命中、玩家公平感、实验组差异。

## 5. 解释边界

- 相关性不是因果；
- 道具使用率上升可能代表关卡难，也可能代表道具更有价值；
- 低通关率可能来自规则不清、性能问题或随机性；
- 高通关率不一定代表关卡无聊；
- 留存变化通常受多因素影响，单关归因需实验支持。
