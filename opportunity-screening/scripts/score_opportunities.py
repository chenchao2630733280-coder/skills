#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商业机会四维评分器（opportunity-screening skill）

为什么要有这个脚本：打分一旦情绪化，人会本能地给自己想做的方向抬分。
用固定权重 + 固定硬伤规则，保证不同机会之间可比、可复核。

用法：
    python score_opportunities.py --template > input.json   # 生成空白模板
    python score_opportunities.py input.json                # 输出 Markdown 裁决表
    python score_opportunities.py input.json --json         # 输出机器可读 JSON
"""

from __future__ import annotations

import argparse
import json
import sys

# 权重：获客门槛最高，因为它是唯一不可靠努力弥补的维度
WEIGHTS = {
    "purchasing_power": 0.25,
    "whitespace": 0.25,
    "startup_cost": 0.20,
    "acquisition_barrier": 0.30,
}

DIM_LABELS = {
    "purchasing_power": "客户购买力",
    "whitespace": "竞争空位",
    "startup_cost": "启动投入",
    "acquisition_barrier": "获客门槛",
}

# 这些维度原始值越大越差，计分时反向
REVERSED = {"startup_cost", "acquisition_barrier"}

# 硬伤规则：(维度, 判定函数, 说明)
HARD_FLAGS = (
    ("purchasing_power", lambda v: v <= 2, "客户无购买力"),
    ("whitespace", lambda v: v <= 2, "红海赛道"),
    ("startup_cost", lambda v: v >= 4, "启动投入过高"),
    ("acquisition_barrier", lambda v: v >= 4, "获客门槛过高"),
)

# 获客门槛满分即个人不可达，无视总分
FATAL_KEY = "acquisition_barrier"
FATAL_VALUE = 5
FATAL_LABEL = "个人不可达（获客门槛硬伤）"

TEMPLATE = {
    "opportunities": [
        {
            "name": "示例：面向独立开发者的某类工具包",
            "target_customer": "独立开发者 / 小团队",
            "purchasing_power": 3,
            "whitespace": 4,
            "startup_cost": 2,
            "acquisition_barrier": 2,
            "note": "备注可留空",
        }
    ],
    "_scale": {
        "purchasing_power": "1=客户从未为此付费 … 5=已有成熟采购品类（越高越好）",
        "whitespace": "1=血海（爆款率<1%）… 5=几乎无有效供给（越高越好）",
        "startup_cost": "1=零现金纯时间 … 5=需垫资或长账期（越低越好）",
        "acquisition_barrier": "1=平台/作品自然触达 … 5=必须人脉或专项资质（越低越好）",
    },
}


def dimension_score(key: str, value: int) -> float:
    """把原始 1-5 分转换成「该维度得分」（都是越大越好）。"""
    return float(6 - value) if key in REVERSED else float(value)


def total_score(opp: dict) -> float:
    return sum(WEIGHTS[k] * dimension_score(k, opp[k]) for k in WEIGHTS)


def verdict(opp: dict) -> str:
    if opp[FATAL_KEY] >= FATAL_VALUE:
        return FATAL_LABEL
    t = total_score(opp)
    if t >= 4.2:
        return "优先验证"
    if t >= 3.4:
        return "可行（需作品背书）"
    if t >= 2.6:
        return "谨慎（存在硬伤维度）"
    return "排除"


def flags(opp: dict) -> list:
    return [label for key, test, label in HARD_FLAGS if test(opp[key])]


def validate(opps: list) -> None:
    for i, opp in enumerate(opps):
        if not isinstance(opp, dict):
            raise ValueError(f"第 {i + 1} 项不是对象")
        if not opp.get("name"):
            raise ValueError(f"第 {i + 1} 项缺少 name")
        for key in WEIGHTS:
            if key not in opp:
                raise ValueError(f"「{opp.get('name', i + 1)}」缺少字段 {key}")
            val = opp[key]
            if not isinstance(val, int) or isinstance(val, bool) or not 1 <= val <= 5:
                raise ValueError(
                    f"「{opp.get('name')}」的 {key} 必须是 1-5 的整数，当前为 {val!r}"
                )


def render_markdown(opps: list) -> str:
    ranked = sorted(opps, key=total_score, reverse=True)
    lines = []
    lines.append("| # | 机会 | 目标客户 | 购买力 | 空位 | 启动投入 * | 获客门槛 * | 综合分 | 裁决 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, opp in enumerate(ranked, 1):
        lines.append(
            "| {i} | {name} | {cust} | {pp} | {ws} | {sc} | {ab} | {total:.2f} | {vd} |".format(
                i=i,
                name=opp["name"],
                cust=opp.get("target_customer", "-"),
                pp=opp["purchasing_power"],
                ws=opp["whitespace"],
                sc=opp["startup_cost"],
                ab=opp["acquisition_barrier"],
                total=total_score(opp),
                vd=verdict(opp),
            )
        )
    lines.append("")
    lines.append("\\* 启动投入与获客门槛为「越低越好」维度，表中显示的是原始分（1 低 / 5 高），综合分中已反向计入。")
    lines.append("")

    flagged = [(o["name"], flags(o), verdict(o)) for o in ranked if flags(o)]
    if flagged:
        lines.append("### 硬伤维度")
        lines.append("")
        for name, fs, vd in flagged:
            suffix = " → **个人不可达**" if vd == FATAL_LABEL else ""
            lines.append(f"- **{name}**：{'、'.join(fs)}{suffix}")
        lines.append("")
    else:
        lines.append("### 硬伤维度")
        lines.append("")
        lines.append("- 无")
        lines.append("")

    lines.append("### 计分口径")
    lines.append("")
    lines.append("- 权重：购买力 0.25 / 空位 0.25 / 启动投入（反向）0.20 / 获客门槛（反向）0.30")
    lines.append("- 裁决阈值：≥4.2 优先验证 ｜ 3.4–4.2 可行（需作品背书）｜ 2.6–3.4 谨慎 ｜ <2.6 排除")
    lines.append("- 硬伤规则：获客门槛 = 5 时判定「个人不可达」，**无视综合分**")
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="商业机会四维评分器")
    parser.add_argument("input", nargs="?", help="输入 JSON 文件路径")
    parser.add_argument("--template", action="store_true", help="输出空白模板并退出")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    if args.template:
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
        return 0

    if not args.input:
        parser.print_help()
        print("\n提示：先用 --template 生成输入模板。", file=sys.stderr)
        return 2

    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print(f"错误：找不到文件 {args.input}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"错误：JSON 解析失败 — {exc}", file=sys.stderr)
        return 2

    opps = data.get("opportunities") if isinstance(data, dict) else data
    if not isinstance(opps, list) or not opps:
        print("错误：输入需为 opportunity 数组，或含 opportunities 字段的对象", file=sys.stderr)
        return 2

    try:
        validate(opps)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if args.json:
        ranked = sorted(opps, key=total_score, reverse=True)
        payload = {
            "results": [
                {
                    "rank": i,
                    "name": o["name"],
                    "target_customer": o.get("target_customer", ""),
                    "total_score": round(total_score(o), 2),
                    "verdict": verdict(o),
                    "hard_flags": flags(o),
                    "note": o.get("note", ""),
                }
                for i, o in enumerate(ranked, 1)
            ]
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(render_markdown(opps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
