#!/usr/bin/env python3
"""Elo-style player/level baseline from attempt CSV: player_id, level_id, won."""
import csv, sys, math
from collections import defaultdict

def sigmoid(x):
    if x >= 30: return 1.0
    if x <= -30: return 0.0
    return 1.0 / (1.0 + math.exp(-x))

def estimate(path, k=16.0, initial=0.0):
    players, levels = defaultdict(lambda: initial), defaultdict(lambda: initial)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # Sort by input order; production use should order by event time.
    for r in rows:
        p, l, y = r["player_id"], r["level_id"], int(r["won"])
        expected = sigmoid(players[p] - levels[l])
        delta = k * (y - expected)
        players[p] += delta
        levels[l] -= delta
    return players, levels

def main():
    if len(sys.argv) < 2:
        print("Usage: python player_skill.py <attempts.csv>")
        raise SystemExit(2)
    players, levels = estimate(sys.argv[1])
    print("Player skill estimates (relative):")
    for k,v in sorted(players.items()): print(f"  {k}: {v:.2f}")
    print("Level difficulty estimates (relative; higher = harder):")
    for k,v in sorted(levels.items()): print(f"  {k}: {v:.2f}")
    print("\\nCaution: baseline only; control for items, seeds, retries, versions and selection bias.")

if __name__ == "__main__":
    main()
