"""相邻关卡难度跳变检测。

只比较相邻关，不比较"整体趋势"——趋势由曲线阶段负责，跳变负责找突变。

判定使用两个尺度：
1. 难度分差 Δscore（设计尺度，便于定位参数）
2. 参考分层首次通关率差 Δwin（体验尺度，玩家真正感知到的）
阈值取 max(配置阈值, 3×MAD)，避免平滑曲线上误报。

类型：
- CLIFF        跳崖：突然变难
- DIP          断崖回落：突然变简单，失去张力
- OVERLOAD     多维同升：难度分涨幅不大，但 3 个以上维度同时抬升（认知过载）
- MECHANIC_SPIKE 新机制 + 难度抬升：教与考挤在同一关
- SAWTOOTH     锯齿震荡：5 关内难度反复来回
- PLATEAU      长期平推：4 关以上几乎无变化
"""

from __future__ import annotations

import statistics

from .schema import Campaign, FEATURE_LABELS, FEATURES


def _mad(values: list) -> float:
    if len(values) < 3:
        return 0.0
    med = statistics.median(values)
    return statistics.median([abs(v - med) for v in values]) * 1.4826


def detect(campaign: Campaign, records: list) -> list:
    """records 为逐关记录，需含 index/level_id/score/pred_win/features/new_mechanics。"""
    th = campaign.thresholds
    records = sorted(records, key=lambda r: r["index"])
    if len(records) < 2:
        return []

    d_scores = [records[i]["score"] - records[i - 1]["score"] for i in range(1, len(records))]
    d_wins = [records[i]["pred_win"] - records[i - 1]["pred_win"] for i in range(1, len(records))]
    thr_score = max(th["jump_score"], min(3 * _mad(d_scores), th["jump_score"] * 1.6))
    thr_win = max(th["jump_winrate"], min(3 * _mad(d_wins), th["jump_winrate"] * 1.6))

    findings = []

    for i in range(1, len(records)):
        prev, cur = records[i - 1], records[i]
        ds, dw = d_scores[i - 1], d_wins[i - 1]
        risen = [
            FEATURE_LABELS[f]
            for f in FEATURES
            if cur["features"].get(f, 0) - prev["features"].get(f, 0) >= th["overload_dim_rise"]
        ]

        if dw <= -thr_win:
            findings.append(
                _finding(
                    "CLIFF",
                    cur,
                    ratio=abs(dw) / thr_win,
                    evidence={
                        "Δ首次通关率": f"{dw:+.3f}",
                        "Δ难度分": f"{ds:+.3f}",
                        "阈值": f"{thr_win:.3f}",
                    },
                    detail=f"从 {prev['level_id']} 到 {cur['level_id']}，参考分层首次通关率下降 {-dw:.1%}，"
                    f"主因维度：{_delta_text(prev, cur)}",
                )
            )
        elif dw >= thr_win * 1.3:
            findings.append(
                _finding(
                    "DIP",
                    cur,
                    ratio=dw / (thr_win * 2.2),
                    evidence={"Δ首次通关率": f"{dw:+.3f}", "Δ难度分": f"{ds:+.3f}"},
                    detail=f"{cur['level_id']} 相比上一关骤降难度（首次通关率 +{dw:.1%}），"
                    f"若不是刻意安排的缓冲关，会让前面积累的张力泄掉",
                )
            )

        if len(risen) >= th["overload_dims"] and 0 < ds <= max(thr_score * 1.6, 0.15):
            hidden = ds <= thr_score
            findings.append(
                _finding(
                    "OVERLOAD",
                    cur,
                    ratio=len(risen) / th["overload_dims"],
                    evidence={"同时上升维度数": str(len(risen)), "维度": "、".join(risen), "Δ难度分": f"{ds:+.3f}"},
                    detail=(
                        f"{cur['level_id']} 有 {len(risen)} 个维度同时抬升（{'、'.join(risen)}）；"
                        + (
                            f"难度分只涨了 {ds:+.3f}，但玩家的学习负担是叠加的，评分会把这类问题低估"
                            if hidden
                            else f"难度分涨了 {ds:+.3f}，且所有维度一起抬，玩家没有可依赖的熟悉维度"
                        )
                    ),
                )
            )

        if cur["new_mechanics"] and dw <= -thr_win * 0.5:
            findings.append(
                _finding(
                    "MECHANIC_SPIKE",
                    cur,
                    ratio=abs(dw) / thr_win,
                    evidence={"新机制": "、".join(cur["new_mechanics"]), "Δ首次通关率": f"{dw:+.3f}"},
                    detail=f"{cur['level_id']} 首次引入 {'、'.join(cur['new_mechanics'])} 的同时难度上调，"
                    f"玩家还没学会就被考核",
                )
            )

    # 锯齿：连续 5 关内方向翻转 >= 3 次
    for i in range(len(d_scores) - 3):
        window = d_scores[i : i + 4]
        flips = sum(
            1
            for j in range(1, len(window))
            if window[j - 1] * window[j] < 0 and abs(window[j]) > campaign.thresholds["jump_score"] * 0.4
        )
        if flips >= 3:
            findings.append(
                _finding(
                    "SAWTOOTH",
                    records[i + 4],
                    ratio=1.0,
                    severity="WARN",
                    evidence={"方向翻转次数": str(flips), "窗口": f"{records[i]['level_id']}–{records[i + 4]['level_id']}"},
                    detail="连续 4 次相邻变化反复变号，玩家会觉得难度在随机抖动而不是在推进",
                )
            )
            break

    # 平推：连续 4 关难度分几乎不动
    run = 1
    for i in range(1, len(d_scores)):
        if abs(d_scores[i]) < campaign.thresholds["jump_score"] * 0.15:
            run += 1
            if run >= 4:
                findings.append(
                    _finding(
                        "PLATEAU",
                        records[i],
                        ratio=1.0,
                        severity="WARN",
                        evidence={"连续关数": str(run), "区间": f"{records[i - run + 1]['level_id']}–{records[i]['level_id']}"},
                        detail="连续多关难度几乎不变，可能是数值复制未调，也可能是刻意留白——需人工确认意图",
                    )
                )
                break
        else:
            run = 1

    order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["index"]))
    return findings


def _finding(kind, cur, ratio, evidence, detail, severity=None):
    if severity is None:
        severity = "HIGH" if ratio >= 1.5 else ("WARN" if ratio >= 1.0 else "INFO")
    return {
        "type": kind,
        "index": cur["index"],
        "level_id": cur["level_id"],
        "severity": severity,
        "evidence": evidence,
        "detail": detail,
    }


def _delta_text(prev, cur) -> str:
    diffs = [
        (FEATURE_LABELS[f], cur["features"].get(f, 0) - prev["features"].get(f, 0))
        for f in FEATURES
    ]
    diffs = [(name, d) for name, d in diffs if abs(d) >= 0.10]
    diffs.sort(key=lambda kv: abs(kv[1]), reverse=True)
    if not diffs:
        return "各维度变化均小于 0.10，可能是多维度小幅叠加"
    return "、".join(f"{name} {d:+.2f}" for name, d in diffs[:3])
