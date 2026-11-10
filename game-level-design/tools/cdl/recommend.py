"""参数反向推荐：从"离目标多远"反推"该动哪个旋钮、动多少"。

方法（刻意保持保守）：
1. 只动一个参数（单变量），保证可归因；多变量组合留给人工。
2. 用 knob.per_unit 把参数变化换算成维度变化，再换算成难度分与通关率。
3. 每个关卡给两个视角：
   - 渐进方案：单次改动不超过原值 25%，符合设计师小步迭代的习惯；
   - 一步到位：数学上能把预测拉回目标带的最小改动，用来看"差距到底有多大"。
4. 参数改动超过原值 35% 仍不达标时，不再推荐数值，而是建议结构性调整（拆关/换机制）。
5. 对已被判为"随机性导致不稳定"的关卡，禁止推荐随机性相关旋钮。

推荐是"待验证假设"，不是可直接上线的数值。
"""

from __future__ import annotations

import math

from .mapping import pass_rate
from .schema import FEATURES, FEATURE_LABELS
from .score import score_features

INCREMENTAL_CAP = 0.25
MAX_PCT_CHANGE = 0.35


def recommend(campaign, records: list, diagnostics: list, limit: int = 3) -> list:
    th = campaign.thresholds
    tol = th["band_tolerance"] * 0.6  # 推荐时要求落进更窄的带内，给模拟误差留余量
    by_id = {r["level_id"]: r for r in records}

    targets = {
        d["level_id"]
        for d in diagnostics
        if d["type"] in ("BAND_MISS", "BLOCKER", "NEAR_UNWINNABLE")
    }
    unstable = {d["level_id"] for d in diagnostics if d["type"] == "UNSTABLE"}
    outliers = {}
    for d in diagnostics:
        meta = d.get("meta") or {}
        if d["type"] == "CONFIG_OUTLIER" and meta.get("param"):
            outliers.setdefault(d["level_id"], {})[meta["param"]] = meta["local_median"]

    out = []
    for lid in sorted(targets, key=lambda x: by_id[x]["index"]):
        rec = by_id[lid]
        need = rec["target_score"] - rec["score"]
        if abs(need) <= 0.008:
            continue
        options, blocked = _search(campaign, rec, need, tol, lid in unstable)
        restored = _restore_options(campaign, rec, outliers.get(lid, {}))
        if restored:
            options = restored + options
        item = {
            "level_id": lid,
            "index": rec["index"],
            "score": round(rec["score"], 4),
            "target_score": round(rec["target_score"], 4),
            "pred_win": round(rec["pred_win"], 4),
            "target_win": round(rec["target_win"], 4),
            "gap_win": round(rec["pred_win"] - rec["target_win"], 4),
            "options": options[:limit],
            "blocked_knobs": blocked,
            "escalate": None,
        }
        if not options:
            item["escalate"] = (
                "合法范围内没有可用的单参数改动，建议结构性调整：拆分为两关、"
                "替换高负荷机制，或重新划分该阶段的目标区间（先确认目标本身是否合理）"
            )
        elif not any(o["in_band"] for o in options):
            item["escalate"] = (
                "单参数在合法范围内无法完全落回目标带：建议分 2–3 轮小步迭代并每轮复评，"
                "或复核该关的目标是否与阶段定位冲突"
            )
        out.append(item)
    return out


def _search(campaign, rec, need, tol, is_unstable):
    weights = campaign.weights
    spread = campaign.spread
    theta_ref = campaign.segments[campaign.ref_segment].theta
    target_win = rec["target_win"]
    candidates = []
    blocked = []

    for knob in campaign.knobs:
        param = knob["param"]
        dim = knob.get("dim")
        if dim not in FEATURES:
            continue
        current = rec["params"].get(param)
        if not isinstance(current, (int, float)):
            continue

        # 随机性旋钮在"结果不稳定"的关卡上禁用：此时问题是种子分布，不是均值难度
        if is_unstable and dim == "randomness":
            blocked.append({"param": param, "reason": "该关被判定为随机性导致的不稳定，优先处理种子与初始局面"})
            continue

        legal = rec["legal_ranges"].get(param)
        lo, hi = (float(legal[0]), float(legal[1])) if legal else (None, None)
        per_unit = float(knob["per_unit"])
        step = float(knob.get("step", 1))
        max_delta = float(knob.get("max_delta", float("inf")))
        eff = weights[dim] * per_unit
        if abs(eff) < 1e-9 or step <= 0:
            continue

        ideal_steps = (need / eff) / step
        tried = set()
        for mult in (1.0, 0.5, 1.5, 0.25):
            for base in (math.floor(ideal_steps * mult), math.ceil(ideal_steps * mult)):
                for n_steps in (base, base - 1, base + 1):
                    if n_steps == 0 or n_steps in tried:
                        continue
                    tried.add(n_steps)
                    new_val = current + n_steps * step
                    if lo is not None and not (lo - 1e-9 <= new_val <= hi + 1e-9):
                        continue
                    if abs(new_val - current) > max_delta + 1e-9:
                        continue
                    delta_feat = per_unit * (new_val - current)
                    new_features = dict(rec["features"])
                    new_features[dim] = min(max(new_features.get(dim, 0.0) + delta_feat, 0.0), 1.0)
                    new_score, _ = score_features(new_features, weights)
                    new_win = pass_rate(new_score, theta_ref, spread)
                    err = abs(new_win - target_win)
                    pct = (new_val - current) / max(1e-9, abs(current))
                    candidates.append(
                        {
                            "param": param,
                            "label": knob.get("label", param),
                            "dim": dim,
                            "dim_label": FEATURE_LABELS.get(dim, dim),
                            "from": _num(current),
                            "to": _num(new_val),
                            "delta_abs": _num(new_val - current),
                            "pct_change": round(pct, 4),
                            "pct_abs": round(abs(pct), 4),
                            "new_score": round(new_score, 4),
                            "new_win": round(new_win, 4),
                            "delta_win": round(new_win - rec["pred_win"], 4),
                            "err": round(err, 4),
                            "in_band": err <= tol,
                            "segment_win": {
                                name: round(pass_rate(new_score, seg.theta, spread), 4)
                                for name, seg in campaign.segments.items()
                            },
                            "side_effects": _side_effects(knob, new_val - current),
                        }
                    )

    picked = []
    # 渐进方案：只看 25% 以内的小步改动，优先落带、再要误差小
    incremental = [c for c in candidates if c["pct_abs"] <= INCREMENTAL_CAP]
    incremental.sort(key=lambda c: (0 if c["in_band"] else 1, c["err"], c["pct_abs"]))
    if incremental:
        best = incremental[0]
        best["scope"] = "渐进"
        picked.append(best)
    # 一步到位：全体候选中误差最小，用于判断"差距到底多大"
    overall = sorted(candidates, key=lambda c: (c["err"], c["pct_abs"]))
    if overall:
        best = dict(overall[0])
        if not picked or (best["param"], best["to"]) != (picked[0]["param"], picked[0]["to"]):
            best["scope"] = "一步到位"
            picked.append(best)
        else:
            picked[0]["scope"] = "一步到位"
    # 备选杠杆：换一个难度维度，避免每次都只动同一个旋钮
    used_dims = {c["dim"] for c in picked}
    alt = [
        c
        for c in sorted(candidates, key=lambda c: (0 if c["in_band"] else 1, c["err"], c["pct_abs"]))
        if c["dim"] not in used_dims
    ]
    if alt:
        option = dict(alt[0])
        option["scope"] = "备选"
        picked.append(option)
    return picked, blocked


def _restore_options(campaign, rec, outlier_params: dict) -> list:
    """参数被判定为"疑似漏改"时，最该先做的是恢复到邻近关卡水平。"""
    out = []
    for param, median in outlier_params.items():
        current = rec["params"].get(param)
        knob = next((k for k in campaign.knobs if k["param"] == param), None)
        if knob is None or not isinstance(current, (int, float)) or median == current:
            continue
        legal = rec["legal_ranges"].get(param)
        if legal and not (float(legal[0]) <= median <= float(legal[1])):
            continue
        target_val = round(median) if float(median).is_integer() else median
        dim = knob["dim"]
        delta_feat = float(knob["per_unit"]) * (target_val - current)
        features = dict(rec["features"])
        features[dim] = min(max(features.get(dim, 0.0) + delta_feat, 0.0), 1.0)
        new_score, _ = score_features(features, campaign.weights)
        new_win = pass_rate(new_score, campaign.segments[campaign.ref_segment].theta, campaign.spread)
        out.append(
            {
                "param": param,
                "label": knob.get("label", param),
                "dim": dim,
                "dim_label": FEATURE_LABELS.get(dim, dim),
                "from": _num(current),
                "to": _num(target_val),
                "delta_abs": _num(target_val - current),
                "pct_change": round((target_val - current) / max(1e-9, abs(current)), 4),
                "pct_abs": round(abs((target_val - current) / max(1e-9, abs(current))), 4),
                "new_score": round(new_score, 4),
                "new_win": round(new_win, 4),
                "delta_win": round(new_win - rec["pred_win"], 4),
                "err": round(abs(new_win - rec["target_win"]), 4),
                "in_band": abs(new_win - rec["target_win"]) <= campaign.thresholds["band_tolerance"] * 0.6,
                "segment_win": {
                    name: round(pass_rate(new_score, seg.theta, campaign.spread), 4)
                    for name, seg in campaign.segments.items()
                },
                "side_effects": ["恢复到相邻关卡水平", "先排除复制关卡漏改，再评估是否需要真正调整"],
                "scope": "对齐邻近",
            }
        )
    return out


def _side_effects(knob, delta) -> list:
    label = knob.get("label", knob["param"])
    direction = "上调" if delta > 0 else "下调"
    out = [f"{label}{direction}"]
    if knob.get("note"):
        out.append(f"旋钮特性：{knob['note']}")
    return out


def _num(v):
    return int(v) if float(v).is_integer() else round(float(v), 2)
