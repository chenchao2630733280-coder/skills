#!/usr/bin/env python3
"""关卡难度自动化评审 CLI。

输入：campaign.json（关卡配置）+ 可选 attempts.csv（真实通关数据）
输出：out 目录下的 review.md / review.json 与 5 张表

用法：
    python tools/design_review.py --campaign examples/campaign_demo.json
    python tools/design_review.py --campaign examples/campaign_demo.json \
        --attempts examples/attempts_campaign.csv --out review_out --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cdl.actuals import load_attempts
from cdl.curve import build_curve, phase_summary
from cdl.diagnose import diagnose
from cdl.jump import detect
from cdl.mapping import pass_rate
from cdl.recommend import recommend
from cdl.report import TYPE_LABELS, write_all
from cdl.schema import ConfigError, Campaign
from cdl.score import score_features, top_dimensions
from cdl.sim import simulate


def build_records(campaign, curve):
    curve_by_id = {c["level_id"]: c for c in curve}
    records = []
    for lv in campaign.levels:
        c = curve_by_id[lv.level_id]
        total, parts = score_features(lv.features, campaign.weights)
        pred_by_segment = {
            name: pass_rate(total, seg.theta, campaign.spread)
            for name, seg in campaign.segments.items()
        }
        records.append(
            {
                "index": lv.index,
                "level_id": lv.level_id,
                "tag": lv.tag,
                "features": lv.features,
                "params": lv.params,
                "legal_ranges": lv.legal_ranges,
                "new_mechanics": lv.new_mechanics,
                "score": total,
                "parts": parts,
                "pred_win": pred_by_segment[campaign.ref_segment],
                "pred_by_segment": pred_by_segment,
                "target_win": c["target_win"],
                "target_score": c["target_score"],
                "top_dims": "、".join(
                    f"{label} {lv.features[name]:.2f}" for name, _, label in top_dimensions(parts, 3)
                ),
            }
        )
    return records


def run(args) -> int:
    campaign = Campaign.load(args.campaign)
    curve = build_curve(campaign)
    records = build_records(campaign, curve)

    jumps = detect(campaign, records)
    sim = simulate(campaign, records)
    actuals = load_attempts(args.attempts) if args.attempts else None
    diagnostics = diagnose(campaign, records, jumps, sim, actuals)
    recs = recommend(campaign, records, diagnostics)

    payload = write_all(args.out, campaign, curve, records, jumps, sim, diagnostics, recs, actuals)

    _print_summary(campaign, curve, records, jumps, diagnostics, recs, payload, args.out)

    if args.strict and payload["gate"]["status"] == "FAIL":
        print("\n[门禁] 存在 HIGH 级问题，--strict 模式下退出码 1。", file=sys.stderr)
        return 1
    return 0


def _print_summary(campaign, curve, records, jumps, diagnostics, recs, payload, out_dir):
    ref = campaign.ref_segment
    print(f"战役: {campaign.campaign_id}  品类: {campaign.genre}  关卡: {len(records)}  参考分层: {ref}")
    print("阶段目标:")
    for row in phase_summary(campaign, curve):
        print(f"  - {row['phase']:<8} {row['range']:<12} 形状={row['shape']:<6} 目标首通 {row['target_win_min']:.0%}–{row['target_win_max']:.0%}")
    print("\n逐关（目标 / 预测 / 偏差 / 难度分）:")
    for r in records:
        flag = "  <<<" if abs(r["pred_win"] - r["target_win"]) > campaign.thresholds["band_tolerance"] else ""
        print(
            f"  {r['level_id']:<6} {r['target_win']:>5.0%} {r['pred_win']:>6.0%} "
            f"{r['pred_win'] - r['target_win']:>+6.0%} {r['score']:>6.3f}{flag}"
        )
    counts = {s: sum(1 for d in diagnostics if d["severity"] == s) for s in ("HIGH", "WARN", "INFO")}
    print(f"\n跳变 {len(jumps)} 处；诊断 HIGH {counts['HIGH']} / WARN {counts['WARN']} / INFO {counts['INFO']}")
    for d in [x for x in diagnostics if x["severity"] == "HIGH"][:5]:
        print(f"  [HIGH] {d['level_id']} {TYPE_LABELS.get(d['type'], d['type'])} —— {d['detail'][:60]}")
    print(f"参数建议：{len(recs)} 关有条目（{sum(len(r['options']) for r in recs)} 个候选方案）")
    print(f"\n门禁: {payload['gate']['status']}   产物目录: {Path(out_dir).resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="休闲游戏关卡难度自动化评审")
    parser.add_argument("--campaign", required=True, help="campaign.json 路径")
    parser.add_argument("--attempts", help="真实通关数据 attempts.csv（可选）")
    parser.add_argument("--out", default="review_out", help="输出目录，默认 review_out")
    parser.add_argument("--strict", action="store_true", help="存在 HIGH 级问题时返回非 0 退出码，可用作 CI 门禁")
    parser.add_argument("--json-only", action="store_true", help="只打印 review.json 的路径，不打印摘要")
    args = parser.parse_args(argv)
    try:
        code = run(args)
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2
    if args.json_only:
        print(json.dumps({"review": str(Path(args.out) / "review.json")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
