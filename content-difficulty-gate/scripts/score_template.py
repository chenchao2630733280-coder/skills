#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压力分骨架：把一份内容包算成"排序建议表"。

用法:
    python score_template.py --dir ./content             # 扫描目录下所有 *.json
    python score_template.py --dir ./content --json      # 机器可读输出

**这不是通用工具，是骨架。** 你只需要替换下面三个 extract() 里的实现，
让它读得懂你的内容格式；公式、归一化、断崖告警都不用改。

三个分量（定义见 ../references/pressure-score.md）：
    D 深度  —— 只作诊断列，不进公式
    C 容量  —— 待处理单元数 / 并发上限
    T 陷阱  —— 开局"能碰但推不动"的单元数 / 并发上限
    压力分  = C * (1 + T)，按全量最大值归一化到 100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


# ── 需要按项目替换的三个提取器 ────────────────────────────────────────────
def extract(data: dict) -> Dict[str, float]:
    """从一份内容 JSON 里取出三个分量需要的原始量。

    返回:
        depth       最深一条线上的状态段数（诊断用）
        units       待处理单元总数（例：轴数 / 题数 / 条目数）
        slots       并发上限（例：槽位数 / 单屏提示数）
        traps       开局"能碰但推不动"的单元数
        front       开局"可推进"的独立类别数（诊断用）

    ── 替换这一段 ──────────────────────────────────────────────────────
    下面是"网格/线轴"类内容的示例实现，换项目时整段替掉：
    """
    cols = data["cols"]
    rows = data["rows"]
    legend = data.get("legend", {})
    image: List[str] = data["image"]

    # 深度：逐列去连续重复，取段数最大值
    depth = 0
    for c in range(cols):
        seq = [image[r][c] for r in range(rows)]
        runs = 1 + sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
        depth = max(depth, runs)

    units = len(data["tray"]["spools"])
    slots = int(data["slotMax"])
    # 陷阱：这里用"能点到、但该类不在底行"的单元数；换项目请改判据
    bottom = {legend[ch] for ch in image[rows - 1] if ch in legend}
    traps = sum(1 for s in data["tray"]["spools"] if s["color"] not in bottom)
    front = len(bottom)
    return dict(depth=depth, units=units, slots=slots, traps=traps, front=front)
    # ── 替换结束 ────────────────────────────────────────────────────────


def score(items: List[Dict]) -> List[Dict]:
    raw = []
    for it in items:
        m = extract(it["data"])
        cap = m["units"] / max(1, m["slots"])
        trap = m["traps"] / max(1, m["slots"])
        raw.append({**it, **m, "capacity": cap, "trap": trap, "raw": cap * (1 + trap)})

    top = max((r["raw"] for r in raw), default=0) or 1
    for r in raw:
        r["pressure"] = round(100 * r["raw"] / top)
    return raw


def report(rows: List[Dict]) -> None:
    head = f"{'ID':<6}{'名称':<18}{'D':>4}{'单元':>6}{'并发':>6}{'C':>7}{'T':>7}{'压力':>6}"
    print(head)
    print("─" * len(head))
    for r in rows:
        print(f"{r['id']:<6}{r['name'][:16]:<18}{r['depth']:>4}{r['units']:>6}"
              f"{r['slots']:>6}{r['capacity']:>7.1f}{r['trap']:>7.2f}{r['pressure']:>6}")

    print()
    for prev, cur in zip(rows, rows[1:]):
        if prev["pressure"] and cur["pressure"] < prev["pressure"] * 0.7:
            print(f"⚠️ 断崖：{prev['id']}({prev['pressure']}) → {cur['id']}({cur['pressure']})"
                  f" 回落 {100 - round(100 * cur['pressure'] / prev['pressure'])}%"
                  " —— 确认是刻意放水还是设计漏项")

    worst = max(rows, key=lambda r: r["pressure"])
    print(f"压力最大：{worst['id']} {worst['name']}  容量 {worst['capacity']:.1f} × 陷阱 {worst['trap']:.2f} = {worst['pressure']}")
    print()
    print("排序建议（按压力升序，与制作顺序无关）：")
    print("  ->", ", ".join(r["id"] for r in sorted(rows, key=lambda r: r["pressure"])))
    print()
    print("提醒：归一化分母取自本次扫描的最大值，改内容后绝对值不可跨版本直比。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="内容 JSON 所在目录")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = ap.parse_args()

    files = sorted(Path(args.dir).glob("*.json"))
    if not files:
        print(f"目录下没有 JSON：{args.dir}", file=sys.stderr)
        return 1

    items = []
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        items.append({"id": str(data.get("id", p.stem)),
                      "name": data.get("name", p.stem),
                      "data": data})
    # 按数值 id 排序（否则 "10" 会排在 "2" 前面，断崖告警会拿错邻居比）
    items.sort(key=lambda it: (0, int(it["id"])) if it["id"].isdigit() else (1, it["id"]))
    rows = score(items)

    if args.json:
        print(json.dumps([{k: v for k, v in r.items() if k != "data"} for r in rows],
                         ensure_ascii=False, indent=1))
    else:
        report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
