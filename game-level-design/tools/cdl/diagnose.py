"""异常关卡与潜在卡点识别。

原则：每条诊断都必须能回溯到证据（预测值 / 模拟分布 / 真实样本量 / 参数值），
并给出"先查什么"而不是直接下结论。无法用数据判断的，标记为待人工确认。
"""

from __future__ import annotations

import statistics

from .schema import FEATURE_LABELS, FEATURES

_SEV_ORDER = {"HIGH": 0, "WARN": 1, "INFO": 2}


def diagnose(campaign, records: list, jumps: list, sim: dict, actuals: dict | None) -> list:
    th = campaign.thresholds
    ref = campaign.ref_segment
    tol = th["band_tolerance"]
    items = []
    local_stats = _local_param_stats(campaign)
    cv_map = _param_cv(campaign)

    for rec in records:
        lid = rec["level_id"]
        expected = rec["target_win"]
        predicted = rec["pred_win"]
        diff = predicted - expected
        sim_ref = sim.get(lid, {}).get(ref, {})
        act = (actuals or {}).get(lid)

        if abs(diff) > tol:
            sev = "HIGH" if abs(diff) > tol * 2 else "WARN"
            direction = "偏难" if diff < 0 else "偏易"
            items.append(
                _item(
                    "BAND_MISS",
                    sev,
                    rec,
                    {"预测首次通关率": f"{predicted:.3f}", "阶段目标": f"{expected:.3f}", "偏差": f"{diff:+.3f}"},
                    f"预测{direction}：参考分层（{ref}）首次通关率 {predicted:.1%}，目标是 {expected:.1%}。"
                    f"主要难度来源：{rec['top_dims']}",
                )
            )

        clear_rate = sim_ref.get("clear_rate")
        if clear_rate is not None and clear_rate < th["near_unwinnable"]:
            items.append(
                _item(
                    "NEAR_UNWINNABLE",
                    "HIGH",
                    rec,
                    {"模拟最终通关率": f"{clear_rate:.3f}", "阈值": f"{th['near_unwinnable']:.2f}",
                     "尝试次数上限": str(campaign.simulation["max_attempts"])},
                    f"参考分层在 {campaign.simulation['max_attempts']} 次尝试内通关率仅 {clear_rate:.1%}，"
                    f"属于近似无解区，需要先验证可解性（求解器/种子回归）再谈手感",
                )
            )

        sd = sim_ref.get("batch_sd")
        if sd is not None and sd > th["unstable_sd"]:
            sev = "HIGH" if sd > th["unstable_sd"] * 1.5 else "WARN"
            items.append(
                _item(
                    "UNSTABLE",
                    sev,
                    rec,
                    {
                        "批间标准差": f"{sd:.3f}",
                        "区间": f"{sim_ref.get('batch_p10'):.1%}–{sim_ref.get('batch_p90'):.1%}",
                    },
                    f"不同初始局面（种子）下首次通关率标准差 {sd:.1%}（区间 {sim_ref.get('batch_p10'):.0%}–{sim_ref.get('batch_p90'):.0%}），"
                    f"玩家体验会时难时易：先查随机性与种子分布，而不是继续加/减难度",
                )
            )

        heavy = [FEATURE_LABELS[f] for f in FEATURES if rec["features"].get(f, 0) >= 0.7]
        if len(heavy) >= 3:
            items.append(
                _item(
                    "OVERLOAD_COGNITIVE",
                    "WARN",
                    rec,
                    {"高负荷维度数": str(len(heavy)), "维度": "、".join(heavy)},
                    f"{len(heavy)} 个维度处于高位（{'、'.join(heavy)}），认知负荷叠加，"
                    f"建议拆成两关或降低其中一个维度",
                )
            )

        if rec["new_mechanics"] and predicted < expected - tol:
            items.append(
                _item(
                    "MECHANIC_FIRST_HARD",
                    "WARN",
                    rec,
                    {"新机制": "、".join(rec["new_mechanics"]), "预测": f"{predicted:.3f}", "目标": f"{expected:.3f}"},
                    "新机制首次出现就低于目标通关率，教学与考核挤在同一关",
                )
            )

        # 参数异常：与"邻近关卡"的中位数比较，而不是全战役中位数——
        # 目标量这类参数本身会随进度增长，用全局中位数会把正常爬坡误报成异常。
        for param, value in rec["params"].items():
            stat = local_stats.get(rec["level_id"], {}).get(param)
            if stat is None or param not in rec["legal_ranges"]:
                continue
            # 只检查"全战役基本稳定"的参数；目标量/障碍数这类本身随进度爬坡的参数，
            # 逐关变化是设计意图，不该按离群值报错。
            if cv_map.get(param, 1.0) > 0.25:
                continue
            ratio = value / stat if stat > 0 else 1.0
            if ratio > 1.5 or ratio < 0.67:
                items.append(
                    _item(
                        "CONFIG_OUTLIER",
                        "WARN",
                        rec,
                        {param: str(value), "邻近关卡中位数": f"{stat:g}", "倍数": f"{ratio:.2f}"},
                        f"参数 `{param}` 与相邻关卡中位数偏离 {ratio:.2f}×，先确认是不是复制关卡后漏改",
                        meta={"param": param, "local_median": stat},
                    )
                )

        # 真实数据相关
        if act:
            n = act["n_players"]
            if n < th["min_sample"]:
                items.append(
                    _item(
                        "DATA_GAP",
                        "INFO",
                        rec,
                        {"样本量": str(n), "最小要求": str(th["min_sample"])},
                        f"仅 {n} 名玩家进入过该关，实际通关率不具备统计意义，先补样本再调参",
                    )
                )
            else:
                gap = act["first_try_rate"] - predicted
                if abs(gap) >= 0.15:
                    items.append(
                        _item(
                            "PRED_ACTUAL_DIVERGENCE",
                            "WARN",
                            rec,
                            {"实际首次通关率": f"{act['first_try_rate']:.3f}", "预测": f"{predicted:.3f}",
                             "样本量": str(n)},
                            f"实际与预测相差 {gap:+.1%}（样本 {n}）：优先怀疑预测模型/特征口径漂移，"
                            f"确认后再动关卡参数，否则会越调越偏",
                        )
                    )

    items.extend(_blockers(records, sim, ref, jumps))
    items.sort(key=lambda it: (_SEV_ORDER[it["severity"]], it["index"]))
    return items


def _blockers(records, sim, ref, jumps) -> list:
    """卡点：既在跳变里被标为跳崖/机制同挤、又在模拟里通关率偏低——最可能造成流失的位置。"""
    cliff_levels = {j["level_id"] for j in jumps if j["type"] in ("CLIFF", "MECHANIC_SPIKE")}
    out = []
    for rec in records:
        if rec["level_id"] not in cliff_levels:
            continue
        clear_rate = sim.get(rec["level_id"], {}).get(ref, {}).get("clear_rate", 1.0)
        if clear_rate < 0.65:
            out.append(
                _item(
                    "BLOCKER",
                    "HIGH",
                    rec,
                    {"跳变": "有", "模拟最终通关率": f"{clear_rate:.3f}"},
                    "既存在难度跳变、模拟通关率又偏低，是最可能产生流失的卡点："
                    "先用真实漏斗确认，再考虑拆分或降低单变量",
                )
            )
    return out


def _item(kind, severity, rec, evidence, detail, meta=None):
    return {
        "type": kind,
        "severity": severity,
        "index": rec["index"],
        "level_id": rec["level_id"],
        "evidence": evidence,
        "detail": detail,
        "meta": meta or {},
    }


def _param_cv(campaign) -> dict:
    """全战役各参数的变异系数；>0.25 视为"随进度变化的参数"，不做离群检查。"""
    series = {}
    for lv in campaign.levels:
        for k, v in lv.params.items():
            if isinstance(v, (int, float)):
                series.setdefault(k, []).append(float(v))
    out = {}
    for k, vals in series.items():
        if len(vals) < 3:
            continue
        mean = statistics.mean(vals)
        out[k] = statistics.pstdev(vals) / mean if mean else 0.0
    return out


def _local_param_stats(campaign, window: int = 3) -> dict:
    """每个关卡每个参数：邻近关卡（不含自身）的中位数，用于识别"复制后漏改"。"""
    levels = sorted(campaign.levels, key=lambda l: l.index)
    out = {}
    for i, lv in enumerate(levels):
        neighbors = levels[max(0, i - window) : i] + levels[i + 1 : i + 1 + window]
        stats = {}
        for key, value in lv.params.items():
            if not isinstance(value, (int, float)):
                continue
            vals = [n.params[key] for n in neighbors if isinstance(n.params.get(key), (int, float))]
            if len(vals) >= 3:
                stats[key] = statistics.median(vals)
        out[lv.level_id] = stats
    return out
