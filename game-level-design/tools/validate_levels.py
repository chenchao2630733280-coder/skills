#!/usr/bin/env python3
"""config/levels.json 构建期校验 —— Gate 2.5 的可执行判据。

评审脚本（design_review.py）看的是"设计意图"（campaign.json），本脚本看的是"交付物"
（导出的运行期关卡表）。两者不能互相替代：表可以合法地由错误的设计导出，也可以在设计
正确时被手工改坏。

用法：
    python tools/validate_levels.py --levels config/levels.json
    python tools/validate_levels.py --levels config/levels.json --campaign campaign.json
    python tools/validate_levels.py --levels config/levels.json --campaign campaign.json --json out.json

退出码：0 = 有 WARN 或全通过；1 = 存在 ERROR（不通过，阻塞下游）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cdl.audit import OPS
from cdl.schema import Campaign, ConfigError

REQUIRED = ("level_id", "index", "params", "target_win", "difficulty_score")


def _issue(code, severity, scope, detail, meta=None):
    return {"code": code, "severity": severity, "scope": scope, "detail": detail, "meta": meta or {}}


def check_table(data: dict) -> list:
    """只依赖交付物本身的结构与取值检查。"""
    issues = []
    if not isinstance(data, dict):
        return [_issue("LEVELS_TABLE_MALFORMED", "ERROR", "*", "levels.json 顶层不是对象")]
    levels = data.get("levels")
    if not isinstance(levels, list):
        return [_issue("LEVELS_TABLE_MALFORMED", "ERROR", "*", "缺少 levels 数组")]
    if not levels:
        return [_issue("LEVELS_EMPTY", "ERROR", "*", "levels 数组为空：关卡制项目至少 1 关")]

    declared = (data.get("campaign") or {}).get("level_count")
    if isinstance(declared, int) and declared != len(levels):
        issues.append(
            _issue(
                "LEVEL_COUNT_MISMATCH",
                "WARN",
                "*",
                f"campaign.level_count={declared}，实际 levels={len(levels)}",
                {"declared": declared, "actual": len(levels)},
            )
        )

    seen_ids, seen_idx = {}, {}
    for pos, lv in enumerate(levels):
        lid = lv.get("level_id") if isinstance(lv, dict) else None
        scope = lid or f"#{pos}"
        if not isinstance(lv, dict):
            issues.append(_issue("LEVEL_FIELD_MISSING", "ERROR", scope, "关卡条目不是对象"))
            continue
        missing = [k for k in REQUIRED if k not in lv]
        if missing:
            issues.append(_issue("LEVEL_FIELD_MISSING", "ERROR", scope, f"缺少字段：{'、'.join(missing)}"))
        if isinstance(lid, str) and lid:
            seen_ids.setdefault(lid, []).append(pos)
        idx = lv.get("index")
        if isinstance(idx, int):
            seen_idx.setdefault(idx, []).append(scope)
        params = lv.get("params")
        if isinstance(params, dict):
            bad = [k for k, v in params.items() if not isinstance(v, (int, float))]
            if bad:
                issues.append(_issue("LEVEL_PARAM_NOT_NUMERIC", "ERROR", scope, f"params 含非数值：{'、'.join(bad)}"))
        elif "params" in lv:
            issues.append(_issue("LEVEL_PARAM_NOT_NUMERIC", "ERROR", scope, "params 不是对象"))
        tw = lv.get("target_win")
        if isinstance(tw, (int, float)) and not 0.0 < float(tw) < 1.0:
            issues.append(_issue("TARGET_WIN_OUT_OF_RANGE", "ERROR", scope, f"target_win={tw} 不在 (0,1)"))
        ds = lv.get("difficulty_score")
        if isinstance(ds, (int, float)) and not 0.0 <= float(ds) <= 1.0:
            issues.append(_issue("SCORE_OUT_OF_RANGE", "ERROR", scope, f"difficulty_score={ds} 不在 [0,1]"))

    for lid, positions in seen_ids.items():
        if len(positions) > 1:
            issues.append(_issue("LEVEL_ID_DUPLICATE", "ERROR", lid, f"level_id 重复 {len(positions)} 次", {"positions": positions}))
    for idx, scopes in seen_idx.items():
        if len(scopes) > 1:
            issues.append(_issue("LEVEL_INDEX_DUPLICATE", "ERROR", ",".join(scopes), f"index={idx} 重复"))
    indexes = sorted(seen_idx)
    if indexes and indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        gaps = [i for i in range(indexes[0], indexes[-1] + 1) if i not in seen_idx]
        issues.append(_issue("LEVEL_INDEX_NOT_SEQUENTIAL", "WARN", "*", f"index 不连续，缺 {gaps[:10]}{'…' if len(gaps) > 10 else ''}", {"missing": gaps}))
    return issues


def check_against_campaign(data: dict, campaign: Campaign) -> list:
    """交付物 ↔ 设计源的一致性（防止手工改表、或导出中途被覆盖）。"""
    issues = []
    rows = {lv.get("level_id"): lv for lv in data.get("levels", []) if isinstance(lv, dict)}
    src = {lv.level_id: lv for lv in campaign.levels}

    only_table = sorted(set(rows) - set(src))
    only_campaign = sorted(set(src) - set(rows))
    if only_table:
        issues.append(_issue("LEVEL_TABLE_DRIFT", "ERROR", ",".join(only_table[:5]), f"表中有、campaign 中无的关卡：{only_table[:5]}"))
    if only_campaign:
        issues.append(_issue("LEVEL_TABLE_DRIFT", "ERROR", ",".join(only_campaign[:5]), f"campaign 有、表中缺的关卡：{only_campaign[:5]}"))

    from cdl.curve import build_curve
    from cdl.score import score_features

    curve = {c["level_id"]: c for c in build_curve(campaign)}
    for lid, lv in src.items():
        row = rows.get(lid)
        if not row:
            continue
        total, _ = score_features(lv.features, campaign.weights)
        if isinstance(row.get("difficulty_score"), (int, float)) and abs(float(row["difficulty_score"]) - total) > 5e-3:
            issues.append(
                _issue(
                    "LEVEL_TABLE_DRIFT",
                    "ERROR",
                    lid,
                    f"difficulty_score 与源不一致：表 {row['difficulty_score']} vs 源 {round(total, 4)}（权重/特征被改过？）",
                )
            )
        tw_src = curve.get(lid, {}).get("target_win")
        if isinstance(row.get("target_win"), (int, float)) and isinstance(tw_src, (int, float)):
            if abs(float(row["target_win"]) - float(tw_src)) > 1e-3:
                issues.append(
                    _issue("LEVEL_TABLE_DRIFT", "ERROR", lid, f"target_win 与源不一致：表 {row['target_win']:.4f} vs 源 {tw_src:.4f}")
                )
        row_params = row.get("params") or {}
        if isinstance(row_params, dict) and set(row_params) != set(lv.params):
            issues.append(
                _issue(
                    "LEVEL_TABLE_DRIFT",
                    "WARN",
                    lid,
                    f"params 键集合与源不一致：多 {sorted(set(row_params) - set(lv.params))}，少 {sorted(set(lv.params) - set(row_params))}",
                )
            )
    return issues


def check_dominance(data: dict, campaign: Campaign) -> list:
    """结构性必赢：某些参数关系成立时，"输"在数学上不可能发生。"""
    issues = []
    for rule in (campaign.raw or {}).get("dominance") or []:
        lhs, rhs, op = rule.get("lhs"), rule.get("rhs"), rule.get("op", ">=")
        if not lhs or not rhs or op not in OPS:
            continue
        check = OPS[op]
        for lv in data.get("levels", []):
            params = lv.get("params") or {}
            a, b = params.get(lhs), params.get(rhs)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                continue
            if check(float(a), float(b)):
                issues.append(
                    _issue(
                        "TRIVIAL_BY_CONSTRUCTION",
                        "WARN",
                        lv.get("level_id", "?"),
                        f"{lhs}={a:g} {op} {rhs}={b:g}：{rule.get('means', '输在数学上不可能发生')}",
                    )
                )
    return issues


def run(levels_path: str, campaign_path: str | None) -> dict:
    data = json.loads(Path(levels_path).read_text(encoding="utf-8"))
    issues = check_table(data)
    campaign = None
    if campaign_path:
        campaign = Campaign.load(campaign_path)
        issues += check_against_campaign(data, campaign)
        issues += check_dominance(data, campaign)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    return {
        "levels": levels_path,
        "campaign": campaign_path,
        "status": "FAIL" if errors else "PASS",
        "error_count": len(errors),
        "warn_count": len(issues) - len(errors),
        "level_count": len(data.get("levels", [])),
        "issues": issues,
        "rule": "ERROR 阻塞下游；WARN 需人工确认。本脚本只校验交付物结构与一致性，不评价难度是否合适。",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="config/levels.json 构建期校验")
    parser.add_argument("--levels", required=True, help="导出的 config/levels.json")
    parser.add_argument("--campaign", help="campaign.json（给出则做源↔表一致性核对与必赢判据）")
    parser.add_argument("--json", help="把结果写入该文件（机器可读）")
    parser.add_argument("--quiet", action="store_true", help="只输出状态行")
    args = parser.parse_args(argv)

    try:
        result = run(args.levels, args.campaign)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[校验失败] 无法读取或解析：{exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.quiet:
        for i in result["issues"]:
            print(f"  [{i['severity']}] {i['code']} {i['scope']} — {i['detail']}")
    print(f"levels.json 校验：{result['status']}（ERROR {result['error_count']} / WARN {result['warn_count']}，共 {result['level_count']} 关）")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
