"""量尺体检与结构性判据。

两块与"这一关难不难"无关、但决定"难度分可不可信"的检查：

1. **量尺体检（dim_profile / scale_issues）**：把全战役每个维度的 p10/p50/p90/max 摊开，
   看刻度是否被用满。三种病：
   - 分母过大：p90 很低（刻度只用了三分之一）→ DIM_UNDERUSED
   - 分母过小：p10 就顶格（所有关都接近满分）→ DIM_SATURATED
   - 指标恒定：p50 等于最大值（等于给所有关加同一个常数）→ DIM_CONSTANT
   另加一个整体信号：加权总分上限压得太低 → SCALE_COMPRESSED。

2. **结构性必赢（dominance_hits）**：某些参数关系一旦成立，"输"在数学上就不可能发生
   （例如"槽位 ≥ 颜色数"），此时难度分描述的是一个不存在的事件 → TRIVIAL_BY_CONSTRUCTION。

判据全部是启发式，只用于提示"你的量尺可能坏了"，不替代项目校准。
"""

from __future__ import annotations

import statistics

OPS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: abs(a - b) <= 1e-9,
    "!=": lambda a, b: abs(a - b) > 1e-9,
}


def _quantile(values, q: float) -> float:
    """最近秩分位数，避免引入 numpy。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    # 最近秩：位置 = ceil(q * n) - 1
    import math

    idx = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return float(ordered[idx])


def dim_profile(records) -> dict:
    """每个维度的分布画像。records 为 build_records 的产物（含 features / parts / score）。"""
    profile = {}
    grand = sum(sum(float(v) for v in r["parts"].values()) for r in records) or 1.0
    for name in (records[0]["features"] if records else []):
        vals = [float(r["features"].get(name, 0.0)) for r in records]
        contrib = [float(r["parts"].get(name, 0.0)) for r in records]
        profile[name] = {
            "p10": _quantile(vals, 0.10),
            "p50": _quantile(vals, 0.50),
            "p90": _quantile(vals, 0.90),
            "max": max(vals),
            "min": min(vals),
            "mean": statistics.mean(vals),
            "sd": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "contrib_mean": statistics.mean(contrib),
            "contrib_share": (sum(contrib) / grand) if grand else 0.0,
        }
    return profile


def scale_issues(profile: dict, n_levels: int = 0) -> list:
    # 关卡太少时分位数噪声大，只提示不告警（6 关的 p90 本质是第 5 关的值）
    sev = "WARN" if n_levels >= 10 else "INFO"
    issues = []
    for name, p in profile.items():
        span = p["max"] - p["min"]
        if p["max"] <= 0.01:
            issues.append(
                {
                    "code": "DIM_UNDERUSED",
                    "severity": sev,
                    "scope": "*",
                    "detail": f"{name} 全战役为 0：该维度未参与评分（特征没派生出来，或机制里本来没有这个压力源）；"
                    f"要么删掉它，要么在 feature_model 里补派生规则",
                    "meta": {"dim": name, "max": p["max"]},
                }
            )
        elif span <= 0.01:
            issues.append(
                {
                    "code": "DIM_CONSTANT",
                    "severity": sev,
                    "scope": "*",
                    "detail": f"{name} 全战役恒定在 {p['p50']:.2f}：对排序没有任何贡献（等于给所有关加同一个常数），"
                    f"应删除、改为减分项，或换成能区分的口径",
                    "meta": {"dim": name, "p50": p["p50"]},
                }
            )
        elif p["p10"] >= 0.90:
            issues.append(
                {
                    "code": "DIM_SATURATED",
                    "severity": sev,
                    "scope": "*",
                    "detail": f"{name} 的 p10={p['p10']:.2f}：八成关卡已顶格，该维度没有区分度（分母可能过小）",
                    "meta": {"dim": name, "p10": p["p10"], "max": p["max"]},
                }
            )
        elif p["p90"] <= 0.35 and p["max"] <= 0.50:
            issues.append(
                {
                    "code": "DIM_UNDERUSED",
                    "severity": sev,
                    "scope": "*",
                    "detail": f"{name} 的 p90={p['p90']:.2f}、max={p['max']:.2f}：刻度只用了不到一半，"
                    f"该维度几乎不参与排序（分母可能过大）",
                    "meta": {"dim": name, **{k: p[k] for k in ("p10", "p50", "p90", "max")}},
                }
            )
    return issues


def score_ceiling(records) -> float:
    """加权总分上限的代理：取全部关卡里的最高分，并提示"刻度是否压缩"。"""
    return max((float(r["score"]) for r in records), default=0.0)


def dominance_hits(campaign) -> list:
    """按 campaign.raw['dominance'] 声明的关系逐关检查；成立即报 HIGH。"""
    rules = (campaign.raw or {}).get("dominance") or []
    if not rules:
        return []
    issues = []
    for rule in rules:
        lhs, rhs, op = rule.get("lhs"), rule.get("rhs"), rule.get("op", ">=")
        if not lhs or not rhs or op not in OPS:
            continue
        check = OPS[op]
        means = rule.get("means", f"{lhs} {op} {rhs}")
        for lv in campaign.levels:
            a, b = lv.params.get(lhs), lv.params.get(rhs)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                continue
            if check(float(a), float(b)):
                issues.append(
                    {
                        "code": "TRIVIAL_BY_CONSTRUCTION",
                        "severity": "HIGH",
                        "scope": lv.level_id,
                        "detail": f"{lv.level_id}：{lhs}={a:g} {op} {rhs}={b:g} 成立——{means}；"
                        f"该关难度分不可信，且加槽类修复会把难度彻底买光",
                        "meta": {"lhs": lhs, "rhs": rhs, "op": op, "left": a, "right": b},
                    }
                )
    return issues


def run(campaign, records) -> dict:
    profile = dim_profile(records)
    dominance = dominance_hits(campaign)
    scale = scale_issues(profile, len(records))
    ceiling = score_ceiling(records)
    if ceiling < 0.60:
        scale.append(
            {
                "code": "SCALE_COMPRESSED",
                "severity": "INFO",
                "scope": "*",
                "detail": f"全战役最高加权分只有 {ceiling:.2f}（8 维满分 1.00）：星级/分档会全部挤在低段，"
                f"与'用等分切档'的假设冲突",
                "meta": {"ceiling": ceiling},
            }
        )
    issues = dominance + scale
    return {
        "profile": profile,
        "dominance_rules": (campaign.raw or {}).get("dominance") or [],
        "issues": issues,
        "ceiling": ceiling,
        "status": "FAIL" if any(i["severity"] == "HIGH" for i in issues) else "PASS",
        "note": "量尺与结构性判据是启发式提示，用于发现'分数不可信'，不能替代项目校准。",
    }
