#!/usr/bin/env python3
"""自检：验证每个检测器/引擎在构造样本上确实按预期工作。

用法：
    python tools/selftest.py

为什么需要它：示例战役不可能同时触发所有规则（比如"近似无解"需要极端关卡），
自检用最小构造样本证明规则本身有效，避免"报告没报 = 规则没跑"的误判。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cdl.actuals import _as_int  # noqa: F401  (确保模块可导入)
from cdl.curve import build_curve
from cdl.diagnose import diagnose
from cdl.jump import detect
from cdl.mapping import pass_rate, score_for_target
from cdl.recommend import recommend
from cdl.schema import Campaign, ConfigError, FEATURES
from cdl.score import score_features
from cdl.sim import simulate

PASSED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}{('  — ' + detail) if detail else ''}")
    else:
        print(f"  FAIL  {name}{('  — ' + detail) if detail else ''}")
        raise SystemExit(1)


def campaign(levels, phases=None, segments=None, **over):
    data = {
        "campaign_id": "selftest",
        "genre": "match3",
        "version": "0.0.0",
        "segments": segments
        or {
            "novice": {"theta": -0.9, "theta_sd": 0.4},
            "regular": {"theta": 0.0, "theta_sd": 0.4},
            "skilled": {"theta": 0.9, "theta_sd": 0.4},
        },
        "mapping": {"spread": 4.0, "ref_segment": "regular"},
        "simulation": {"players_per_segment": 200, "batches": 8, "max_attempts": 4},
        "levels": levels,
        "phases": phases or [],
    }
    data.update(over)
    return Campaign.from_dict(data)


def flat_level(idx, x, lid=None, mechanics=(), params=None, ranges=None):
    return {
        "level_id": lid or f"T{idx:02d}",
        "index": idx,
        "tag": "TEST",
        "features": {f: x for f in FEATURES},
        "params": params or {},
        "legal_ranges": ranges or {},
        "new_mechanics": list(mechanics),
    }


def records_of(cam):
    out = []
    for lv in cam.levels:
        total, parts = score_features(lv.features, cam.weights)
        out.append(
            {
                "index": lv.index,
                "level_id": lv.level_id,
                "features": lv.features,
                "params": lv.params,
                "legal_ranges": lv.legal_ranges,
                "new_mechanics": lv.new_mechanics,
                "score": total,
                "parts": parts,
                "pred_win": pass_rate(total, cam.segments[cam.ref_segment].theta, cam.spread),
                "pred_by_segment": {},
                "target_win": 0.5,
                "target_score": score_for_target(0.5, cam.ref_theta(), cam.spread),
                "top_dims": "—",
            }
        )
    return out


def test_score_and_mapping():
    print("\n[1] 评分与映射")
    low, _ = score_features({f: 0.2 for f in FEATURES})
    high, _ = score_features({f: 0.8 for f in FEATURES})
    check("特征升高 → 难度分升高", high > low, f"{low:.3f} < {high:.3f}")

    target = 0.62
    score = score_for_target(target, 0.0, 4.0)
    back = pass_rate(score, 0.0, 4.0)
    check("目标通关率往返一致", abs(back - target) < 1e-6, f"{target:.3f} -> {back:.3f}")

    easy = pass_rate(0.2, -0.9, 4.0)
    hard = pass_rate(0.8, -0.9, 4.0)
    check("同一关对弱分层更难", easy > hard, f"novice {easy:.2f} vs {hard:.2f}")


def test_curve():
    print("\n[2] 目标曲线生成")
    cam = campaign(
        [flat_level(i, 0.4) for i in range(1, 9)],
        phases=[
            {"name": "A", "from_index": 1, "to_index": 4, "shape": "ramp", "start_win": 0.8, "end_win": 0.6},
            {"name": "B", "from_index": 5, "to_index": 8, "shape": "spike", "start_win": 0.6, "end_win": 0.5},
        ],
    )
    curve = build_curve(cam)
    first = curve[0]["target_win"]
    last_of_a = curve[3]["target_win"]
    check("ramp 阶段目标单调下降", first > last_of_a and last_of_a >= curve[4]["target_win"], f"{first:.2f} > {last_of_a:.2f}")
    peak = min(r["target_win"] for r in curve if r["phase"] == "B")
    check("spike 阶段存在明显峰值", peak <= 0.45, f"谷底 {peak:.2f}")


def test_jump():
    print("\n[3] 跳变检测")
    # 难度序列：平滑 → 跳崖 → 回落 → 锯齿
    xs = [0.20, 0.22, 0.24, 0.26, 0.60, 0.58, 0.62, 0.40, 0.60, 0.42, 0.62]
    cam = campaign([flat_level(i + 1, x) for i, x in enumerate(xs)])
    recs = records_of(cam)
    for r, x in zip(recs, xs):
        r["target_win"], r["target_score"] = 0.5, score_for_target(0.5, 0.0, cam.spread)
    found = detect(cam, recs)
    types = {f["type"] for f in found}
    check("识别跳崖 CLIFF", "CLIFF" in types, f"检出 {sorted(types)}")
    check("识别断崖回落 DIP", "DIP" in types)
    check("识别锯齿震荡 SAWTOOTH", "SAWTOOTH" in types)

    plateau_xs = [0.3, 0.301, 0.302, 0.301, 0.30, 0.302]
    cam2 = campaign([flat_level(i + 1, x) for i, x in enumerate(plateau_xs)])
    found2 = detect(cam2, records_of(cam2))
    check("识别长期平推 PLATEAU", any(f["type"] == "PLATEAU" for f in found2))

    # 多维同升：难度分涨幅小，但 4 个维度同时抬升
    lv_a = flat_level(1, 0.3)
    lv_b = flat_level(2, 0.3)
    for dim in ("mechanic_load", "strategy_depth", "randomness", "goal_complexity"):
        lv_b["features"][dim] = 0.45
    cam3 = campaign([lv_a, lv_b])
    found3 = detect(cam3, records_of(cam3))
    check("识别多维同升 OVERLOAD", any(f["type"] == "OVERLOAD" for f in found3))


def test_sim():
    print("\n[4] 玩家表现模拟")
    calm = flat_level(1, 0.45, lid="CALM", params={})
    calm["features"]["randomness"] = 0.05
    wild = flat_level(2, 0.45, lid="WILD", params={})
    wild["features"]["randomness"] = 0.95
    cam = campaign([calm, wild])
    recs = records_of(cam)
    sim = simulate(cam, recs)
    calm_sd = sim["CALM"]["regular"]["batch_sd"]
    wild_sd = sim["WILD"]["regular"]["batch_sd"]
    check("随机性高的关卡种子波动更大", wild_sd > calm_sd * 1.5, f"{calm_sd:.3f} vs {wild_sd:.3f}")
    check("弱分层通关率低于强分层",
          sim["CALM"]["novice"]["first_try_rate"] < sim["CALM"]["skilled"]["first_try_rate"])

    brutal = flat_level(1, 1.0, lid="BRUTAL")
    cam2 = campaign([brutal])
    sim2 = simulate(cam2, records_of(cam2))
    check("极端关卡的最终通关率显著下降",
          sim2["BRUTAL"]["regular"]["clear_rate"] < 0.6, f"{sim2['BRUTAL']['regular']['clear_rate']:.2f}")


def test_diagnose_and_recommend():
    print("\n[5] 诊断与推荐")
    brutal = flat_level(1, 1.0, lid="BRUTAL", params={"moves": 10}, ranges={"moves": [8, 30]})
    cam = campaign([brutal], knobs=[{"param": "moves", "dim": "resource_pressure", "per_unit": -0.05, "step": 1, "max_delta": 6, "label": "可用步数"}])
    recs = records_of(cam)
    recs[0]["target_win"] = 0.47
    recs[0]["target_score"] = score_for_target(0.47, cam.ref_theta(), cam.spread)
    sim = simulate(cam, recs)
    diags = diagnose(cam, recs, [], sim, None)
    types = {d["type"] for d in diags}
    check("识别近似无解 NEAR_UNWINNABLE", "NEAR_UNWINNABLE" in types, f"检出 {sorted(types)}")

    easy = flat_level(1, 0.40, lid="EASY", params={"moves": 24}, ranges={"moves": [8, 30]})
    cam2 = campaign([easy], knobs=[{"param": "moves", "dim": "resource_pressure", "per_unit": -0.05, "step": 1, "max_delta": 6, "label": "可用步数"}])
    recs2 = records_of(cam2)
    recs2[0]["target_win"] = 0.54
    recs2[0]["target_score"] = score_for_target(0.55, cam2.ref_theta(), cam2.spread)
    diags2 = diagnose(cam2, recs2, [], simulate(cam2, recs2), None)
    rec_items = recommend(cam2, recs2, diags2)
    check("偏易关卡给出建议", bool(rec_items and rec_items[0]["options"]))
    if rec_items and rec_items[0]["options"]:
        opt = rec_items[0]["options"][0]
        check("建议方向正确：降低步数变难", opt["to"] < opt["from"], f"{opt['from']} -> {opt['to']}")
        check("建议在合法范围内", 8 <= opt["to"] <= 30)
        check("建议幅度受 max_delta 约束", abs(opt["to"] - opt["from"]) <= 6)


def test_schema_guard():
    print("\n[6] 配置校验")
    bad = {"campaign_id": "x", "genre": "match3", "segments": {"regular": {"theta": 0}}, "levels": [flat_level(1, 0.3)], "weights": {"resource_pressure": 0.9}}
    try:
        Campaign.from_dict(bad)
        check("权重之和不为 1 时报错", False, "未抛出异常")
    except ConfigError as exc:
        check("权重之和不为 1 时报错", "weights" in str(exc), str(exc)[:40])

    out_of_range = [flat_level(1, 0.3)]
    out_of_range[0]["features"]["goal_complexity"] = 1.5
    try:
        Campaign.from_dict({"campaign_id": "y", "genre": "match3", "segments": {"regular": {"theta": 0}}, "levels": out_of_range})
        check("特征超出 [0,1] 时报错", False, "未抛出异常")
    except ConfigError as exc:
        check("特征超出 [0,1] 时报错", "goal_complexity" in str(exc), str(exc)[:40])


def main():
    print("cdl 自检")
    test_score_and_mapping()
    test_curve()
    test_jump()
    test_sim()
    test_diagnose_and_recommend()
    test_schema_guard()
    print(f"\n全部通过：{len(PASSED)} 项检查")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
