#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""失败案例库操作脚本。

提供四个子命令:
    record      记录一条失败案例(失败码+原因+修复方法)
    query       按 skill 名查询历史失败案例
    stats       统计各 skill 的失败概况
    auto-query  skill 执行前自动查询历史失败案例,返回精简摘要 + 预防提示

案例存储在 ~/.trae-cn/failures/ 目录下,每个案例一个 JSON 文件,
索引文件为 ~/.trae-cn/failures/failure-casebook.json。

仅依赖 Python 标准库。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 失败案例存储根目录:~/.trae-cn/failures/
CASES_DIR = Path.home() / ".trae-cn" / "failures"
# 索引文件路径
INDEX_FILE = CASES_DIR / "failure-casebook.json"
# 默认保留天数,可通过环境变量 FAILURE_CASEBOOK_RETENTION_DAYS 覆盖
DEFAULT_RETENTION_DAYS = 90
# 索引文件版本号
INDEX_VERSION = 1


def _utcnow_iso() -> str:
    """返回当前 UTC 时间的 ISO-8601 字符串(带时区)。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_dir() -> None:
    """确保案例目录存在,不存在则创建。创建失败不阻断,仅打 WARNING。"""
    try:
        CASES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"WARNING: 创建案例目录失败 {CASES_DIR}: {exc}", file=sys.stderr)


def _load_index() -> dict:
    """读取索引文件,返回 dict。损坏或不存在时返回空索引结构。"""
    empty = {"version": INDEX_VERSION, "cases": []}
    if not INDEX_FILE.exists():
        return empty
    try:
        with INDEX_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("cases"), list):
            return data
        # 索引结构异常,返回空
        print(f"WARNING: 索引文件结构异常,已忽略 {INDEX_FILE}", file=sys.stderr)
        return empty
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: 读取索引失败 {INDEX_FILE}: {exc}", file=sys.stderr)
        return empty


def _save_index(index: dict) -> None:
    """写入索引文件。失败仅打 WARNING,不抛异常。"""
    try:
        with INDEX_FILE.open("w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"WARNING: 写入索引失败 {INDEX_FILE}: {exc}", file=sys.stderr)


def _parse_ts(ts: str) -> datetime | None:
    """解析 ISO-8601 时间字符串为 datetime,失败返回 None。"""
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def _retention_days() -> int:
    """从环境变量读取保留天数,非法值回退默认 90 天。"""
    raw = os.environ.get("FAILURE_CASEBOOK_RETENTION_DAYS")
    if not raw:
        return DEFAULT_RETENTION_DAYS
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_RETENTION_DAYS
    except ValueError:
        return DEFAULT_RETENTION_DAYS


def _cleanup_expired(index: dict) -> tuple[int, dict]:
    """清理过期案例,返回 (清理条数, 新索引)。

    过期判定:timestamp 早于 now - 保留天数 的案例视为过期。
    过期案例的 JSON 文件会被删除,并从索引中移除。
    """
    days = _retention_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    kept = []
    removed = 0
    for entry in index.get("cases", []):
        ts = _parse_ts(entry.get("timestamp", ""))
        if ts is not None and ts.tzinfo is None:
            # 无时区信息按 UTC 处理
            ts = ts.replace(tzinfo=timezone.utc)
        if ts is not None and ts < cutoff:
            # 过期:删除案例文件
            case_file = CASES_DIR / f"{entry.get('id')}.json"
            try:
                case_file.unlink(missing_ok=True)
            except OSError as exc:
                print(f"WARNING: 删除过期案例失败 {case_file}: {exc}", file=sys.stderr)
            removed += 1
        else:
            kept.append(entry)
    return removed, {"version": INDEX_VERSION, "cases": kept}


def cmd_record(args: argparse.Namespace) -> int:
    """record 子命令:记录一条失败案例。

    生成 UUID 作为 id,写入单案例 JSON 文件,并更新索引;
    顺带清理过期案例。任何读写失败仅打 WARNING,不阻断主流程。
    """
    _ensure_dir()

    # 生成案例 id
    case_id = str(uuid.uuid4())
    timestamp = _utcnow_iso()

    # 构造案例对象
    case = {
        "id": case_id,
        "skill": args.skill,
        "code": args.code,
        "reason": args.reason,
        "fix": args.fix,
        "timestamp": timestamp,
        "severity": args.severity,
    }
    if args.project:
        case["project"] = args.project

    # 写入单案例 JSON 文件
    case_file = CASES_DIR / f"{case_id}.json"
    try:
        with case_file.open("w", encoding="utf-8") as f:
            json.dump(case, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"WARNING: 写入案例文件失败 {case_file}: {exc}", file=sys.stderr)
        # 不阻断主流程,返回 0
        return 0

    # 更新索引(顺带清理过期案例)
    index = _load_index()
    removed, index = _cleanup_expired(index)
    index["cases"].append(
        {
            "id": case_id,
            "skill": case["skill"],
            "code": case["code"],
            "severity": case["severity"],
            "timestamp": case["timestamp"],
            "project": case.get("project", ""),
            "file": f"{case_id}.json",
        }
    )
    _save_index(index)

    # 输出结果(JSON)
    result = {"id": case_id, "path": str(case_file), "expired_removed": removed}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """query 子命令:按 skill 查询历史失败案例。

    skill 必匹配,code 可选过滤;按时间倒序返回,受 limit 限制。
    读取每条案例详情(reason/fix),读不到则留空。
    """
    index = _load_index()
    cases = index.get("cases", [])

    # 过滤:skill 必匹配,code 可选过滤
    matched = []
    for entry in cases:
        if entry.get("skill") != args.skill:
            continue
        if args.code and entry.get("code") != args.code:
            continue
        matched.append(entry)

    # 按时间倒序(无 timestamp 排到最后)
    matched.sort(
        key=lambda e: _parse_ts(e.get("timestamp", ""))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # 应用 limit(<=0 表示不限制)
    limited = matched[: args.limit] if args.limit > 0 else matched

    # 读取每条案例的详情(reason/fix)
    results = []
    for entry in limited:
        case_file = CASES_DIR / f"{entry.get('id')}.json"
        detail = {}
        try:
            with case_file.open("r", encoding="utf-8") as f:
                detail = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: 读取案例详情失败 {case_file}: {exc}", file=sys.stderr)

        results.append(
            {
                "id": entry.get("id"),
                "skill": entry.get("skill"),
                "code": entry.get("code"),
                "severity": entry.get("severity"),
                "timestamp": entry.get("timestamp"),
                "project": entry.get("project", ""),
                "reason": detail.get("reason", ""),
                "fix": detail.get("fix", ""),
            }
        )

    output = {
        "skill": args.skill,
        "code_filter": args.code or "",
        "total_matched": len(matched),
        "returned": len(results),
        "cases": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """stats 子命令:统计各 skill 的失败概况。

    汇总各 skill 的失败次数、最近失败时间、常见失败码 Top 5。
    """
    index = _load_index()
    cases = index.get("cases", [])

    if not cases:
        print("暂无失败案例记录。")
        return 0

    # 按 skill 聚合
    per_skill: dict[str, dict] = {}
    for entry in cases:
        skill = entry.get("skill", "(unknown)")
        agg = per_skill.setdefault(
            skill, {"count": 0, "latest": "", "codes": Counter()}
        )
        agg["count"] += 1
        ts = entry.get("timestamp", "")
        # 取最近时间(ISO-8601 字符串可直接字典序比较)
        if ts > agg["latest"]:
            agg["latest"] = ts
        agg["codes"][entry.get("code", "(none)")] += 1

    # 输出汇总
    print(f"失败案例总数: {len(cases)}")
    print(f"涉及 skill 数: {len(per_skill)}")
    print("-" * 60)
    for skill, agg in sorted(
        per_skill.items(), key=lambda kv: kv[1]["count"], reverse=True
    ):
        print(f"\n[{skill}]")
        print(f"  失败次数: {agg['count']}")
        print(f"  最近失败: {agg['latest'] or '(无)'}")
        print("  常见失败码:")
        for code, cnt in agg["codes"].most_common(5):
            print(f"    {code}: {cnt} 次")
    return 0


def cmd_auto_query(args: argparse.Namespace) -> int:
    """auto-query 子命令:skill 执行前自动查询该 skill 的历史失败案例。

    供 workflow-runtime 在调用 skill 前查询,返回精简摘要 + 预防提示。
    纯查询(只读),不写入案例库;无历史失败时返回空结果,退出码 0。

    输出 auto-query-result.json(打印到 stdout),含:
      - failure_count:该 skill 的历史失败次数
      - top_failures:最常见的 3 个失败码 + 原因摘要(取每个码最近一条案例的 reason)
      - preventive_hints:预防提示(取 top 3 失败码对应案例的修复方法)
      - last_failure_time:最近一次失败时间
    """
    index = _load_index()
    cases = index.get("cases", [])

    # 筛选该 skill 的历史失败案例
    matched = [e for e in cases if e.get("skill") == args.skill]
    failure_count = len(matched)

    # 最近一次失败时间(ISO-8601 字符串可直接字典序比较取最大)
    last_failure_time = ""
    if matched:
        last_failure_time = max(
            (e.get("timestamp", "") for e in matched), default=""
        )

    # 失败码频率统计,取 top 3
    code_counter = Counter(e.get("code", "(none)") for e in matched)
    top_codes = [code for code, _ in code_counter.most_common(3)]

    # 为每个 top 失败码取最近一条案例的 reason/fix,生成摘要与预防提示
    top_failures = []
    preventive_hints = []
    for code in top_codes:
        code_entries = [e for e in matched if e.get("code", "(none)") == code]
        code_entries.sort(
            key=lambda e: _parse_ts(e.get("timestamp", ""))
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        latest = code_entries[0] if code_entries else None
        reason = ""
        fix = ""
        if latest:
            case_file = CASES_DIR / f"{latest.get('id')}.json"
            try:
                with case_file.open("r", encoding="utf-8") as f:
                    detail = json.load(f)
                reason = detail.get("reason", "")
                fix = detail.get("fix", "")
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"WARNING: 读取案例详情失败 {case_file}: {exc}",
                    file=sys.stderr,
                )
        top_failures.append(
            {"code": code, "count": code_counter[code], "reason": reason}
        )
        # 预防提示:取该失败码的修复方法;无修复方法时给出默认提示
        if fix:
            preventive_hints.append(f"[{code}] {fix}")
        else:
            preventive_hints.append(
                f"[{code}] 无历史修复方法,执行时注意规避此类失败"
            )

    result = {
        "skill": args.skill,
        "failure_count": failure_count,
        "top_failures": top_failures,
        "preventive_hints": preventive_hints,
        "last_failure_time": last_failure_time,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="casebook_ops.py",
        description="失败案例库操作脚本(record/query/stats/auto-query)。",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # record 子命令
    p_record = sub.add_parser("record", help="记录一条失败案例")
    p_record.add_argument("--skill", required=True, help="失败的 skill 名")
    p_record.add_argument("--code", required=True, help="失败码(大写蛇形)")
    p_record.add_argument("--reason", required=True, help="失败原因")
    p_record.add_argument("--fix", required=True, help="修复方法/规避建议")
    p_record.add_argument(
        "--severity",
        default="error",
        choices=["error", "warning"],
        help="严重级别,默认 error",
    )
    p_record.add_argument("--project", default=None, help="项目名(可选)")
    p_record.set_defaults(func=cmd_record)

    # query 子命令
    p_query = sub.add_parser("query", help="按 skill 查询历史失败案例")
    p_query.add_argument("--skill", required=True, help="要查询的 skill 名")
    p_query.add_argument("--code", default=None, help="按失败码过滤(可选)")
    p_query.add_argument("--limit", type=int, default=10, help="返回条数上限,默认 10")
    p_query.set_defaults(func=cmd_query)

    # stats 子命令
    p_stats = sub.add_parser("stats", help="统计各 skill 的失败概况")
    p_stats.set_defaults(func=cmd_stats)

    # auto-query 子命令
    p_auto = sub.add_parser(
        "auto-query", help="skill 执行前自动查询历史失败案例,返回预防提示"
    )
    p_auto.add_argument("--skill", required=True, help="要查询的 skill 名")
    p_auto.set_defaults(func=cmd_auto_query)

    return parser


def main() -> int:
    """入口函数,解析参数并分发到对应子命令,返回退出码。"""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
