#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stats.py - Data 层调用统计脚本。

子命令:
  summary [--from <日期>] [--to <日期>]
  top     [--by calls|duration|failures] [--limit 10]
  slow    [--threshold-ms <毫秒>] [--limit 10]

产出 usage-stats.json
退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

USAGE_DIR = Path.home() / ".trae-cn" / "usage"
RECORDS_FILE = USAGE_DIR / "records.jsonl"
STATS_FILE = USAGE_DIR / "usage-stats.json"
LOCAL_TZ = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _read_records():
    if not RECORDS_FILE.exists():
        return []
    records = []
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return records


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None


def _filter_by_date(records, start, end):
    if not start and not end:
        return records
    result = []
    for r in records:
        ts = r.get("start_time", "")
        try:
            rt = datetime.fromisoformat(ts)
        except Exception:
            result.append(r)  # 解析失败保留
            continue
        if start and rt < start:
            continue
        if end and rt > end + timedelta(days=1):
            continue
        result.append(r)
    return result


def _percentile(data, p):
    """计算百分位数。"""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[f]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def _by_skill_stats(records):
    """按 skill 聚合统计。"""
    skill_map = {}
    for r in records:
        skill = r.get("skill", "unknown")
        if skill not in skill_map:
            skill_map[skill] = {"calls": 0, "durations": [], "fails": 0}
        skill_map[skill]["calls"] += 1
        dur = r.get("duration_ms")
        if dur is not None:
            skill_map[skill]["durations"].append(dur)
        if r.get("status") == "fail":
            skill_map[skill]["fails"] += 1

    result = []
    for skill, data in skill_map.items():
        durs = data["durations"]
        entry = {
            "skill": skill,
            "calls": data["calls"],
            "avg_ms": round(statistics.mean(durs)) if durs else 0,
            "fail_rate": round(data["fails"] / data["calls"], 4) if data["calls"] else 0,
            "p95_ms": round(_percentile(durs, 95)) if durs else 0,
        }
        result.append(entry)
    return result


def cmd_summary(args):
    """summary:汇总统计。"""
    records = _read_records()
    start = _parse_date(args.from_date)
    end = _parse_date(args.to_date)
    records = _filter_by_date(records, start, end)

    if not records:
        print("无记录")
        return 0

    total = len(records)
    successes = sum(1 for r in records if r.get("status") == "success")
    durations = [r["duration_ms"] for r in records if r.get("duration_ms") is not None]

    by_skill = _by_skill_stats(records)
    slow_skills = [s["skill"] for s in by_skill if s["p95_ms"] > 60000]
    high_fail = [s["skill"] for s in by_skill if s["fail_rate"] > 0.1]

    # 所有 skill 集合(用于检测未使用)
    all_known = set()
    ws_dir = Path(__file__).resolve().parents[1]
    for entry in ws_dir.iterdir():
        if entry.is_dir() and entry.name not in ("_shared", ".trae") and (entry / "SKILL.md").exists():
            all_known.add(entry.name)
    used = {s["skill"] for s in by_skill}
    unused = sorted(all_known - used) if all_known else []

    stats = {
        "period": f"{args.from_date or 'all'}~{args.to_date or 'now'}",
        "total_calls": total,
        "success_rate": round(successes / total, 4) if total else 0,
        "avg_duration_ms": round(statistics.mean(durations)) if durations else 0,
        "p95_ms": round(_percentile(durations, 95)) if durations else 0,
        "p99_ms": round(_percentile(durations, 99)) if durations else 0,
        "by_skill": by_skill,
        "slow_skills": slow_skills,
        "high_fail_skills": high_fail,
        "unused_skills": unused,
        "timestamp": _now_iso(),
    }

    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"汇总统计:共 {total} 次调用  成功率 {stats['success_rate']}")
    print(f"  平均耗时 {stats['avg_duration_ms']}ms  P95 {stats['p95_ms']}ms")
    print(f"  慢 skill(>{60000}ms):{slow_skills}")
    print(f"  高失败率(>10%):{high_fail}")
    print(f"  未使用 skill:{unused[:10]}{'...' if len(unused) > 10 else ''}")
    print(f"  统计文件:{STATS_FILE}")
    return 0


def cmd_top(args):
    """top:排名。"""
    records = _read_records()
    by_skill = _by_skill_stats(records)

    by = args.by
    if by == "calls":
        by_skill.sort(key=lambda x: x["calls"], reverse=True)
        label = "调用次数"
    elif by == "duration":
        by_skill.sort(key=lambda x: x["avg_ms"], reverse=True)
        label = "平均耗时"
    elif by == "failures":
        by_skill.sort(key=lambda x: x["fail_rate"], reverse=True)
        label = "失败率"
    else:
        by_skill.sort(key=lambda x: x["calls"], reverse=True)
        label = "调用次数"

    limit = args.limit or 10
    print(f"排名(按{label},Top {limit}):")
    for s in by_skill[:limit]:
        print(f"  {s['skill']:30s} | calls={s['calls']:4d} | "
              f"avg={s['avg_ms']}ms | fail={s['fail_rate']}")
    return 0


def cmd_slow(args):
    """slow:慢 skill。"""
    records = _read_records()
    by_skill = _by_skill_stats(records)
    threshold = args.threshold_ms or 60000

    slow = [s for s in by_skill if s["p95_ms"] > threshold]
    slow.sort(key=lambda x: x["p95_ms"], reverse=True)

    limit = args.limit or 10
    print(f"慢 skill(P95 > {threshold}ms,共 {len(slow)} 个):")
    for s in slow[:limit]:
        print(f"  {s['skill']:30s} | P95={s['p95_ms']}ms | avg={s['avg_ms']}ms | "
              f"calls={s['calls']}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="stats.py",
        description="Data 层调用统计脚本。汇总/排名/慢 skill。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码:0=成功;1=有错误;2=参数错误",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    p_sum = sub.add_parser("summary", help="汇总统计")
    p_sum.add_argument("--from", dest="from_date", default=None, help="开始日期(YYYY-MM-DD)")
    p_sum.add_argument("--to", dest="to_date", default=None, help="结束日期(YYYY-MM-DD)")
    p_sum.set_defaults(func=cmd_summary)

    p_top = sub.add_parser("top", help="调用排名")
    p_top.add_argument("--by", default="calls", choices=["calls", "duration", "failures"],
                       help="排名维度(默认 calls)")
    p_top.add_argument("--limit", type=int, default=10, help="返回条数")
    p_top.set_defaults(func=cmd_top)

    p_slow = sub.add_parser("slow", help="慢 skill")
    p_slow.add_argument("--threshold-ms", type=int, default=60000, help="阈值(默认 60000ms)")
    p_slow.add_argument("--limit", type=int, default=10, help="返回条数")
    p_slow.set_defaults(func=cmd_slow)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except Exception as e:
        print(f"FAIL  未捕获异常:{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
