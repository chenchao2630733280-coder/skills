#!/usr/bin/env python3
"""把 campaign.json（+ 可选 review.json）导出为运行期关卡配置 config/levels.json。

这是阶段 2.5 交下游的唯一关卡数据源：game-code-forge 只读这个文件，
不允许把关卡数值内联复制到代码里（否则 Gate 3 的契约检查会失败）。

用法：
    python tools/export_levels.py --campaign campaign.json --out config/levels.json
    python tools/export_levels.py --campaign campaign.json \
        --review review_out/review.json --out config/levels.json --require-pass
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cdl.curve import build_curve
from cdl.mapping import pass_rate
from cdl.schema import Campaign, ConfigError
from cdl.score import score_features
from validate_levels import check_against_campaign, check_dominance, check_table

SCHEMA_VERSION = "1.0"


def build(campaign: Campaign, review: dict | None) -> dict:
    curve = {c["level_id"]: c for c in build_curve(campaign)}
    levels = []
    for lv in campaign.levels:
        total, _ = score_features(lv.features, campaign.weights)
        c = curve.get(lv.level_id, {})
        levels.append(
            {
                "level_id": lv.level_id,
                "index": lv.index,
                "tag": lv.tag,
                "phase": c.get("phase", ""),
                "params": {k: v for k, v in lv.params.items()},
                "new_mechanics": list(lv.new_mechanics),
                "difficulty_score": round(total, 4),
                "target_win": c.get("target_win"),
                "pred_win": round(pass_rate(total, campaign.segments[campaign.ref_segment].theta, campaign.spread), 4),
                "notes": lv.notes,
            }
        )

    gate = (review or {}).get("gate") or {}
    data_source = campaign.data_source
    if review:
        calib = review.get("actuals") or {}
        data_source = f"{campaign.data_source}（评审时{'已' if calib else '未'}接入真实数据）"

    return {
        "schema_version": SCHEMA_VERSION,
        "campaign": {
            "campaign_id": campaign.campaign_id,
            "genre": campaign.genre,
            "version": campaign.version,
            "level_count": len(levels),
            "data_source": data_source,
            "exported_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "model": {
                "spread": campaign.spread,
                "ref_segment": campaign.ref_segment,
                "weights": campaign.weights,
                "status": "占位假设，需项目校准",
            },
        },
        "difficulty_gate": {
            "status": gate.get("status", "NOT_RUN"),
            "high_count": gate.get("high_count"),
            "blocking_levels": gate.get("blocking_levels", []),
            "report": "docs/DIFFICULTY_REPORT.md",
        },
        "levels": levels,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="导出运行期关卡配置 config/levels.json")
    parser.add_argument("--campaign", required=True, help="campaign.json 路径")
    parser.add_argument("--review", help="review.json 路径（可选，用于写入门禁状态）")
    parser.add_argument("--out", default="config/levels.json", help="输出路径，默认 config/levels.json")
    parser.add_argument("--require-pass", action="store_true", help="评审门禁不是 PASS 时拒绝导出")
    parser.add_argument("--indent", type=int, default=2, help="缩进，默认 2；0 表示压缩输出")
    parser.add_argument("--allow-invalid", action="store_true", help="校验出 ERROR 时仍然写出文件（不推荐，仅供排查）")
    args = parser.parse_args(argv)

    try:
        campaign = Campaign.load(args.campaign)
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    review = None
    if args.review:
        review_path = Path(args.review)
        if not review_path.exists():
            print(f"[错误] 找不到评审判定: {review_path}", file=sys.stderr)
            return 2
        review = json.loads(review_path.read_text(encoding="utf-8"))

    payload = build(campaign, review)

    # 导出即自检：把校验结论内嵌进 levels.json，Gate 2.5 读同一份文件即可判定
    issues = check_table(payload) + check_against_campaign(payload, campaign) + check_dominance(payload, campaign)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    payload["validation"] = {
        "status": "FAIL" if errors else "PASS",
        "error_count": len(errors),
        "warn_count": len(issues) - len(errors),
        "issues": issues,
        "tool": "tools/validate_levels.py",
        "rule": "ERROR 阻塞下游；WARN 需人工确认。只校验结构与一致性，不评价难度是否合适。",
    }

    status = payload["difficulty_gate"]["status"]
    if args.require_pass and status != "PASS":
        print(f"[拒绝导出] 评审门禁状态为 {status}，先修复 HIGH 级问题或去掉 --require-pass", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=args.indent or None, separators=None if args.indent else (",", ":"))
    out.write_text(text + ("\n" if args.indent else ""), encoding="utf-8")

    print(f"已导出 {payload['campaign']['level_count']} 关 → {out}")
    print(f"  品类 {payload['campaign']['genre']}　战役 {payload['campaign']['campaign_id']}　门禁 {status}")
    print(f"  交付物校验 {payload['validation']['status']}（ERROR {payload['validation']['error_count']} / WARN {payload['validation']['warn_count']}）")
    if status == "FAIL":
        print(f"  注意：门禁 FAIL，阻断关卡 {payload['difficulty_gate']['blocking_levels']}", file=sys.stderr)
    if errors:
        for i in errors[:5]:
            print(f"  [ERROR] {i['code']} {i['scope']} — {i['detail']}", file=sys.stderr)
        if not args.allow_invalid:
            print("  交付物校验未通过，导出视为失败（加 --allow-invalid 可强行写出）", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
