"""玩家表现模拟（替代模型 / surrogate simulator）。

这不是真实游戏模拟器：没有棋盘、没有求解器，只用"能力 θ vs 关卡难度 b"的
响应曲线 + 多次尝试学习 + 道具软辅助 + 放弃行为，估一个量级和排序。

三个关键假设（都必须项目校准）：
1. 关卡难度 b 会随随机种子波动：seed_sd = seed_jitter_k × randomness。
   同一关不同初始局面本来就难易不一，否则"这关靠运气"这类问题会被漏掉。
2. 玩家失败后不一定重试：retry_prob 控制"失败一次仍继续"的概率。
   休闲游戏的真实流失大量发生在第 1–2 次失败之后。
3. 重试会带来学习：每次尝试的 logit 提升 learning_logit。

不可用途：预测真实绝对通关率、替代 A/B 测试、作为调参唯一依据。
"""

from __future__ import annotations

import random
import statistics

from .mapping import logit, score_to_b, sigmoid


def simulate(campaign, records: list) -> dict:
    cfg = campaign.simulation
    players = int(cfg["players_per_segment"])
    batches = int(cfg["batches"])
    max_attempts = int(cfg["max_attempts"])
    learning = float(cfg["learning_logit"])
    booster_rate = float(cfg["booster_rate"])
    booster_gain = float(cfg["booster_logit_gain"])
    retry_prob = float(cfg.get("retry_prob", 0.55))
    jitter_k = float(cfg.get("seed_jitter_k", 0.9))
    base_seed = int(cfg["base_seed"])

    seg_names = list(campaign.segments)
    out = {}
    for rec in records:
        b = score_to_b(rec["score"], campaign.spread)
        seed_sd = jitter_k * float(rec["features"].get("randomness", 0.0))
        per_seg = {}
        for s_i, seg_name in enumerate(seg_names):
            seg = campaign.segments[seg_name]
            batch_first, batch_clear, batch_attempts, batch_booster = [], [], [], []
            for batch in range(batches):
                rng = random.Random(base_seed + rec["index"] * 1000 + s_i * 100 + batch)
                b_eff = b + (rng.gauss(0, seed_sd) if seed_sd > 0 else 0.0)
                first = clear = 0
                attempts_used = []
                boosters = 0
                for _ in range(players):
                    theta = rng.gauss(seg.theta, max(1e-6, seg.theta_sd))
                    cleared = False
                    attempt_used = max_attempts
                    for attempt in range(1, max_attempts + 1):
                        p = sigmoid(theta - b_eff + learning * (attempt - 1))
                        if attempt >= 2 and rng.random() < booster_rate:
                            p = sigmoid(logit(p) + booster_gain)
                            boosters += 1
                        p = min(max(p, 0.001), 0.999)
                        if rng.random() < p:
                            if attempt == 1:
                                first += 1
                            clear += 1
                            cleared = True
                            attempt_used = attempt
                            break
                        # 失败后可能直接放弃；越到后面越容易放弃
                        if attempt < max_attempts and rng.random() > retry_prob * (0.9 ** (attempt - 1)):
                            attempt_used = attempt
                            break
                    attempts_used.append(attempt_used)
                batch_first.append(first / players)
                batch_clear.append(clear / players)
                batch_attempts.append(statistics.median(attempts_used) if attempts_used else max_attempts)
                batch_booster.append(boosters / players)

            def agg(series):
                return sum(series) / len(series)

            lo, hi = _percentile(batch_first, 0.10), _percentile(batch_first, 0.90)
            sd = statistics.pstdev(batch_first) if len(batch_first) > 1 else 0.0
            per_seg[seg_name] = {
                "first_try_rate": round(agg(batch_first), 4),
                "clear_rate": round(agg(batch_clear), 4),
                "quit_rate": round(1 - agg(batch_clear), 4),
                "attempts_p50": round(agg(batch_attempts), 2),
                "boosters_per_player": round(agg(batch_booster), 2),
                "batch_p10": round(lo, 4),
                "batch_p90": round(hi, 4),
                "batch_sd": round(sd, 4),
            }
        out[rec["level_id"]] = per_seg
    return out


def _percentile(values: list, q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * q
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)
