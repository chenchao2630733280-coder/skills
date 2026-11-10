#!/usr/bin/env python3
"""Transparent baseline scorer. Input CSV features should be normalized to [0,1]."""
import csv, sys
from pathlib import Path

DEFAULT_WEIGHTS = {
    "resource_pressure": 0.20,
    "mechanic_load": 0.15,
    "strategy_depth": 0.20,
    "randomness": 0.10,
    "operation_pressure": 0.10,
    "time_pressure": 0.10,
    "space_pressure": 0.10,
    "goal_complexity": 0.05,
}

def score(row, weights=DEFAULT_WEIGHTS):
    vals = {}
    for key, weight in weights.items():
        raw = row.get(key, "")
        x = float(raw) if raw not in ("", None) else 0.0
        if not 0 <= x <= 1:
            raise ValueError(f"{key} must be normalized to [0,1], got {x}")
        vals[key] = x
    total = sum(weights[k] * vals[k] for k in weights)
    return total, vals

def main():
    if len(sys.argv) < 2:
        print("Usage: python difficulty_scorer.py <features.csv>")
        raise SystemExit(2)
    path = Path(sys.argv[1])
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        total, parts = score(row)
        print(f'{row.get("level_id","?")}: {total:.3f} / 1.000')
        print("  " + ", ".join(f"{k}={v:.2f}" for k, v in parts.items()))
    print("\\nNote: baseline ranking only; not a pass-probability prediction.")

if __name__ == "__main__":
    main()
