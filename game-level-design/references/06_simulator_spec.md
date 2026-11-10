# 06｜关卡模拟器接口规范

## 目标
用可重复的模拟快速发现不可解、极端坏局、资源预算不合理和策略差异。模拟器不是玩家体验的替代品。

## 标准接口

```python
initial_state(level_config, seed) -> state
legal_actions(state) -> list[action]
step(state, action, rng) -> (next_state, reward, done, info)
policy(state, player_profile) -> action
run_episode(level_config, seed, policy, player_profile) -> result
batch_evaluate(level_config, seeds, policies, profiles) -> metrics
```

## 结果字段
- level_id / level_version / seed / policy_id / player_profile
- win / fail_reason / turns / remaining_resource
- objective_progress / booster_used / deadlock / invalid_state
- runtime_ms / simulator_version

## 策略基线
1. Random：随机合法动作，用于粗略基线。
2. Heuristic：简单规则策略，模拟普通玩家的局部决策。
3. Strong：搜索/求解器或强启发式，估计高水平玩家上限。

## 必须测试
- 多随机种子批量模拟；
- 固定种子回归测试；
- 关卡配置边界值；
- 不可解状态和软锁；
- 策略差异；
- 资源剩余与目标进度分布；
- 模拟器版本一致性。

## 解释边界
模拟通关率不等于真实通关率。策略模型越简单，越不能将模拟结果外推到真实玩家。应使用玩家数据验证模拟器对关卡难度排序的相关性。
