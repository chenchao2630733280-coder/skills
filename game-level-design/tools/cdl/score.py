"""多维特征 -> 难度分与子分。与 difficulty_scorer.py 使用同一套默认权重，保证口径一致。"""

from __future__ import annotations

from .schema import DEFAULT_WEIGHTS, FEATURES, FEATURE_LABELS


def score_features(features: dict, weights: dict | None = None):
    """返回 (总分, 各维度贡献字典)。贡献之和等于总分，便于解释"难度来自哪里"。"""
    weights = weights or DEFAULT_WEIGHTS
    parts = {}
    for name in FEATURES:
        x = float(features.get(name, 0.0))
        parts[name] = weights[name] * x
    return sum(parts.values()), parts


def top_dimensions(parts: dict, n: int = 3) -> list:
    """按贡献降序返回 [(维度, 贡献, 中文名)]，用于报告里的原因解释。"""
    ordered = sorted(parts.items(), key=lambda kv: kv[1], reverse=True)
    return [(name, val, FEATURE_LABELS.get(name, name)) for name, val in ordered[:n]]


def load_shift(features: dict) -> float:
    """认知负荷的粗代理：机制 + 策略 + 目标三项之和。

    只用于提示"这一关要记/要想的东西是否偏多"，不是难度本身。
    """
    return (
        float(features.get("mechanic_load", 0.0))
        + float(features.get("strategy_depth", 0.0))
        + float(features.get("goal_complexity", 0.0))
    )
