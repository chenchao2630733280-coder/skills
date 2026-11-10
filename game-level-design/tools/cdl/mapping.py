"""难度分与通关率之间的映射。

模型：b = (score - 0.5) * spread，p = sigmoid(theta - b)
- score 是 [0,1] 的难度分，b 是 logit 尺度上的关卡难度。
- theta 是玩家能力（分层均值），spread 控制难度分的"分辨率"。
- 该模型是占位假设：spread 与 theta 必须用真实数据校准，不能当行业常数。
"""

from __future__ import annotations

import math


def sigmoid(x: float) -> float:
    if x >= 30:
        return 1.0
    if x <= -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def score_to_b(score: float, spread: float = 4.0) -> float:
    return (score - 0.5) * spread


def b_to_score(b: float, spread: float = 4.0) -> float:
    return 0.5 + b / spread


def pass_rate(score: float, theta: float, spread: float = 4.0) -> float:
    """给定难度分与玩家能力，返回单次尝试的预计通过率。"""
    return sigmoid(theta - score_to_b(score, spread))


def score_for_target(target_p: float, theta: float, spread: float = 4.0) -> float:
    """反向：想要某分层达到 target_p 的首次通过率，难度分应该是多少。"""
    return b_to_score(theta - logit(target_p), spread)


def pass_rate_delta(score_from: float, score_to: float, theta: float, spread: float = 4.0) -> float:
    return pass_rate(score_to, theta, spread) - pass_rate(score_from, theta, spread)
