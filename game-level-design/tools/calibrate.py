#!/usr/bin/env python3
"""Small pure-Python logistic regression baseline for educational calibration."""
import csv, sys, math

def sigmoid(z):
    z = max(-30, min(30, z))
    return 1/(1+math.exp(-z))

def train(rows, features, lr=0.1, epochs=3000, l2=0.01):
    w = [0.0] * (len(features)+1)  # intercept then coefficients
    for _ in range(epochs):
        grad = [0.0] * len(w)
        for r in rows:
            x = [1.0] + [float(r[f]) for f in features]
            y = float(r["won"])
            p = sigmoid(sum(a*b for a,b in zip(w,x)))
            for j in range(len(w)):
                grad[j] += (p-y)*x[j]
        n = max(1, len(rows))
        for j in range(len(w)):
            reg = 0.0 if j == 0 else l2*w[j]
            w[j] -= lr*(grad[j]/n + reg)
    return w

def main():
    if len(sys.argv) < 2:
        print("Usage: python calibrate.py <calibration.csv>")
        raise SystemExit(2)
    with open(sys.argv[1], newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    features = [k for k in rows[0] if k != "won"]
    w = train(rows, features)
    print("Educational logistic baseline (not production-ready)")
    print("intercept:", round(w[0], 4))
    for name, val in zip(features, w[1:]):
        print(f"{name}: {val:.4f}")
    print("Validate with player-level/time split, LogLoss, Brier and calibration curves.")

if __name__ == "__main__":
    main()
