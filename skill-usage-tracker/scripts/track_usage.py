#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""track_usage.py - Data 层 skill 调用记录脚本。

子命令:
  record --skill <skill名> [--status success|fail] [--duration-ms <毫秒>] ...
  query  --skill <skill名> [--from <日期>] [--to <日期>] [--status fail] [--limit 20]

设计原则:
- 纯记录不阻塞:record 失败仅打印警告,不抛异常
- 数据追加写入 .trae-cn/usage/records.jsonl(JSON Lines 格式)
- 调用 ID 贯穿链路,供 failure-casebook 关联

退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ---------- 常量 ----------

USAGE_DIR = Path.home() / ".trae-cn" / "usage"
RECORDS_FILE = USAGE_DIR / "records.jsonl"

# 本地时区(东八区)
LOCAL_TZ = timezone(timedelta(hours=8))


# ---------- 工具函数 ----------

def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _gen_call_id():
    """生成 call_id,格式 call-{YYYYMMDD}-{序号}(如 call-20260806-001)。

    序号 = 当天已记录的 call_id 数量 + 1(三位补零)。
    若无法读取记录,回退为毫秒数 %1000(三位补零)。
    与 workflow-runtime/SKILL.md §12.2 声明的格式一致。
    """
    now = datetime.now(LOCAL_TZ)
    date_str = now.strftime("%Y%m%d")
    try:
        records = _read_records()
        today_prefix = f"call-{date_str}-"
        today_count = sum(
            1 for r in records
            if isinstance(r, dict) and isinstance(r.get("call_id"), str)
            and r["call_id"].startswith(today_prefix)
        )
        seq = today_count + 1
    except Exception:
        seq = (now.microsecond // 1000) % 1000  # 毫秒数 0-999
    return f"call-{date_str}-{seq:03d}"


def _ensure_dir():
    USAGE_DIR.mkdir(parents=True, exist_ok=True)


def _append_record(record):
    """追加一条记录到 records.jsonl。失败仅打印警告,不抛异常。"""
    try:
        _ensure_dir()
        with open(RECORDS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"WARN  记录写入失败(不阻塞):{e}", file=sys.stderr)
        return False


def _read_records():
    """读取全部记录。文件不存在返回空列表。"""
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
    except Exception as e:
        print(f"WARN  读取记录失败:{e}", file=sys.stderr)
    return records


def _parse_date(s):
    """解析日期字符串(YYYY-MM-DD),返回 datetime。"""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None


def _in_range(record_time_str, start, end):
    """判断记录时间是否在 [start, end] 范围内。"""
    if not start and not end:
        return True
    try:
        # 解析记录时间(兼容带时区和不带时区)
        rt = datetime.fromisoformat(record_time_str)
    except Exception:
        return True  # 解析失败不过滤
    if start and rt < start:
        return False
    if end and rt > end + timedelta(days=1):  # end 含当天
        return False
    return True


# ---------- 子命令实现 ----------

def cmd_record(args):
    """record:记录单次调用。"""
    now = _now_iso()
    call_id = args.call_id or _gen_call_id()

    # 计算 duration
    duration_ms = args.duration_ms
    if duration_ms is None and args.start_time and args.end_time:
        try:
            st = datetime.fromisoformat(args.start_time)
            et = datetime.fromisoformat(args.end_time)
            duration_ms = int((et - st).total_seconds() * 1000)
        except Exception:
            duration_ms = None

    record = {
        "call_id": call_id,
        "skill": args.skill,
        "pipeline": args.pipeline or "",
        "start_time": args.start_time or now,
        "end_time": args.end_time or now,
        "duration_ms": duration_ms,
        "status": args.status or "success",
        "error_code": args.error_code,
        "outputs": args.outputs or [],
        "caller": args.caller or "",
        "recorded_at": now,
    }

    ok = _append_record(record)
    if ok:
        print(f"PASS  记录已写入:{call_id}  skill={args.skill}  status={record['status']}")
    else:
        print(f"WARN  记录写入失败(已忽略,不阻塞)")
    return 0  # 始终返回 0(纯记录不阻塞)


def cmd_query(args):
    """query:查询调用记录。"""
    records = _read_records()
    start = _parse_date(args.from_date)
    end = _parse_date(args.to_date)

    filtered = []
    for r in records:
        # skill 过滤
        if args.skill and r.get("skill") != args.skill:
            continue
        # 状态过滤
        if args.status and r.get("status") != args.status:
            continue
        # 流水线过滤
        if args.pipeline and r.get("pipeline") != args.pipeline:
            continue
        # 时间过滤
        if not _in_range(r.get("start_time", ""), start, end):
            continue
        filtered.append(r)

    # 限制数量
    limit = args.limit or 20
    filtered = filtered[-limit:]  # 取最近 N 条

    print(f"查询结果:共 {len(filtered)} 条(限制 {limit})")
    for r in filtered:
        dur = r.get("duration_ms")
        dur_str = f"{dur}ms" if dur is not None else "?"
        print(f"  [{r.get('call_id','?')}] {r.get('skill','?')} | "
              f"{r.get('status','?')} | {dur_str} | {r.get('start_time','?')}")
    return 0


# ---------- argparse ----------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="track_usage.py",
        description="Data 层 skill 调用记录脚本。记录/查询 skill 调用数据。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python track_usage.py record --skill game-asset-forge --status success --duration-ms 330000\n"
            "  python track_usage.py query --skill game-asset-forge --status fail --limit 10\n"
            "\n退出码:0=成功;1=有错误;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # record
    p_rec = sub.add_parser("record", help="记录单次调用")
    p_rec.add_argument("--skill", required=True, help="skill 名称")
    p_rec.add_argument("--pipeline", default=None, help="流水线名称(如 game-forge)")
    p_rec.add_argument("--status", default="success", choices=["success", "fail"],
                       help="调用状态(默认 success)")
    p_rec.add_argument("--duration-ms", type=int, default=None, help="耗时(毫秒)")
    p_rec.add_argument("--call-id", default=None, help="调用 ID(不提供则自动生成)")
    p_rec.add_argument("--start-time", default=None, help="开始时间(ISO)")
    p_rec.add_argument("--end-time", default=None, help="结束时间(ISO)")
    p_rec.add_argument("--error-code", default=None, help="失败码(失败时填)")
    p_rec.add_argument("--outputs", nargs="*", default=None, help="产物路径列表")
    p_rec.add_argument("--caller", default=None, help="调用方(如 workflow-runtime)")
    p_rec.set_defaults(func=cmd_record)

    # query
    p_qry = sub.add_parser("query", help="查询调用记录")
    p_qry.add_argument("--skill", default=None, help="按 skill 名筛选")
    p_qry.add_argument("--pipeline", default=None, help="按流水线筛选")
    p_qry.add_argument("--status", default=None, choices=["success", "fail"], help="按状态筛选")
    p_qry.add_argument("--from", dest="from_date", default=None, help="开始日期(YYYY-MM-DD)")
    p_qry.add_argument("--to", dest="to_date", default=None, help="结束日期(YYYY-MM-DD)")
    p_qry.add_argument("--limit", type=int, default=20, help="返回条数(默认 20)")
    p_qry.set_defaults(func=cmd_query)

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
