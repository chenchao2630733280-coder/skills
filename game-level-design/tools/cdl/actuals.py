"""把真实通关数据（attempts.csv）聚合成可对比的分层指标。

必需列：player_id, level_id, won
可选列：attempt_index, segment, booster_used, level_version, duration_seconds

口径说明：
- first_try_rate：每个玩家的"首次尝试"是否通关。缺 attempt_index 时按文件顺序取首次出现。
- final_clear_rate：观察窗口内该玩家是否在任意一次尝试通关（含买活/重试）。
- 分母是"进入过该关的玩家数"，不是尝试数——两者不可混用。
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .schema import ConfigError


def load_attempts(path) -> dict:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"找不到通关数据: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    missing = {"player_id", "level_id", "won"} - set(rows[0].keys())
    if missing:
        raise ConfigError(f"attempts.csv 缺少列: {', '.join(sorted(missing))}")

    by_level = defaultdict(lambda: {"first": {}, "final": {}, "boosters": 0, "segments": defaultdict(lambda: {"first": {}, "final": {}})})
    for order, row in enumerate(rows):
        pid = row["player_id"]
        lid = row["level_id"]
        won = _as_int(row.get("won"))
        seg = (row.get("segment") or "").strip() or None
        att = _as_int(row.get("attempt_index"), default=None)
        bucket = by_level[lid]
        key = (att if att is not None else order, order)
        if pid not in bucket["first"] or key < bucket["first"][pid][0]:
            bucket["first"][pid] = (key, won)
        bucket["final"][pid] = bucket["final"].get(pid, 0) or won
        if seg:
            sb = bucket["segments"][seg]
            if pid not in sb["first"] or key < sb["first"][pid][0]:
                sb["first"][pid] = (key, won)
            sb["final"][pid] = sb["final"].get(pid, 0) or won
        if _as_int(row.get("booster_used")) == 1:
            bucket["boosters"] += 1

    out = {}
    for lid, bucket in by_level.items():
        n = len(bucket["first"])
        if n == 0:
            continue
        first_hits = sum(1 for _, w in bucket["first"].values() if w == 1)
        final_hits = sum(1 for w in bucket["final"].values() if w == 1)
        seg_rows = {}
        for seg, sb in bucket["segments"].items():
            sn = len(sb["first"])
            if sn == 0:
                continue
            seg_rows[seg] = {
                "n": sn,
                "first_try_rate": round(sum(1 for _, w in sb["first"].values() if w == 1) / sn, 4),
                "final_clear_rate": round(sum(1 for w in sb["final"].values() if w == 1) / sn, 4),
            }
        out[lid] = {
            "n_players": n,
            "first_try_rate": round(first_hits / n, 4),
            "final_clear_rate": round(final_hits / n, 4),
            "booster_ratio": round(bucket["boosters"] / max(1, n), 3),
            "segments": seg_rows,
        }
    return out


def _as_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
