"""目标难度曲线生成。

设计师用"阶段 + 波形 + 起止通关率"描述意图，这里把它展开成逐关目标，
并换算成难度分（target_score），供后续对比与推荐使用。

曲线形状：
- ramp   缓升：阶段内线性推进
- flat   平稳：保持中位
- spike  波峰：在阶段后段设置一个考核峰值（更难）
- relief 回落：阶段前段先放松，再爬升
- wave   波浪：阶段内一次完整起伏
- step   阶梯：前半段一档、后半段一档
"""

from __future__ import annotations

import math

from .mapping import score_for_target
from .schema import Campaign


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _bump(t: float, center: float, width: float) -> float:
    return math.exp(-((t - center) ** 2) / (2 * width ** 2))


def build_curve(campaign: Campaign) -> list:
    """返回逐关目标列表，每项含 index / level_id / phase / target_win / target_score。"""
    ref_theta = campaign.ref_theta()
    spread = campaign.spread
    default_target = campaign.segments[campaign.ref_segment].target_first_try or 0.55
    rows = []
    for level in campaign.levels:
        phase = campaign.phase_of(level.index)
        start = phase.start_win if phase.start_win is not None else default_target
        end = phase.end_win if phase.end_win is not None else start
        span = max(1, phase.to_index - phase.from_index)
        t = (level.index - phase.from_index) / span
        t = min(max(t, 0.0), 1.0)

        if phase.shape == "flat":
            base = (start + end) / 2
        elif phase.shape == "step":
            base = start if t < 0.5 else end
        else:
            base = _lerp(start, end, t)

        if phase.shape == "spike":
            base -= 0.12 * _bump(t, 0.72, 0.10)
        elif phase.shape == "relief":
            base += 0.10 * _bump(t, 0.22, 0.12)
        elif phase.shape == "wave":
            base += 0.05 * math.sin(2 * math.pi * t)

        # 微节奏：每 5 关一个"小考 + 喘息"，避免整条曲线过于机械
        if campaign.micro_rhythm:
            pos = level.index - phase.from_index
            if pos % 5 == 4:
                base -= 0.03
            elif pos % 5 == 1 and pos > 0:
                base += 0.02

        target_win = min(max(base, 0.03), 0.95)
        rows.append(
            {
                "index": level.index,
                "level_id": level.level_id,
                "phase": phase.name,
                "shape": phase.shape,
                "target_win": round(target_win, 4),
                "target_score": round(score_for_target(target_win, ref_theta, spread), 4),
                "new_mechanics": ", ".join(level.new_mechanics),
                "tag": level.tag,
            }
        )
    return rows


def phase_summary(campaign: Campaign, curve: list) -> list:
    """按阶段汇总目标区间，便于和设计师沟通"这段到底想要多难"。"""
    out = []
    for phase in campaign.phases:
        rows = [r for r in curve if phase.from_index <= r["index"] <= phase.to_index]
        if not rows:
            continue
        wins = [r["target_win"] for r in rows]
        out.append(
            {
                "phase": phase.name,
                "range": f"{rows[0]['level_id']}–{rows[-1]['level_id']}",
                "shape": phase.shape,
                "target_win_min": round(min(wins), 3),
                "target_win_max": round(max(wins), 3),
                "mechanics": ", ".join(phase.mechanics_intro) or "—",
            }
        )
    return out
