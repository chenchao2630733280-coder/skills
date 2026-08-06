#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_conflicts.py - 冲突解决脚本。

子命令:
  resolve  --exec-id <id> --strategy priority|voting|human|latest
            [--priority-order "sub-1,sub-2,sub-3"]
            按策略解决多 Agent 结果冲突

策略:
  priority - 按 Agent 优先级取首个非空结果
  voting   - 相同结果占比 >50% 取胜,无多数转人工
  human    - 不自动合并,标记待人工裁决
  latest   - 取最近完成的结果

产物:
  conflict-resolve-result.json - 解决结果(merged_result + conflicts)

退出码:0=成功;1=有错误(无结果/无法解决);2=参数错误
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOCAL_TZ = timezone(timedelta(hours=8))
STATE_FILE = Path.cwd() / "agent-exec-state.json"
RESULT_FILE = Path.cwd() / "conflict-resolve-result.json"


def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _load_exec_state(exec_id):
    """加载指定 exec_id 的执行状态。"""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: 解析执行状态文件失败:{e}", file=sys.stderr)
        return None
    if isinstance(data, list):
        for e in data:
            if e.get("exec_id") == exec_id:
                return e
        return None
    if isinstance(data, dict) and data.get("exec_id") == exec_id:
        return data
    return None


def _collect_results(exec_state):
    """从执行状态中收集已完成的结果。"""
    results = []
    for d in exec_state.get("delegations", []):
        if d.get("status") == "completed" and d.get("result"):
            results.append({
                "agent": d.get("to", ""),
                "msg_id": d.get("msg_id", ""),
                "summary": (d.get("result") or {}).get("summary", ""),
                "result": d.get("result"),
                "completed_at": d.get("completed_at", ""),
            })
    return results


# ============================================================
# 策略实现
# ============================================================

def _resolve_priority(results, priority_order):
    """优先级策略:按指定顺序取首个非空结果。"""
    if not priority_order:
        # 无指定顺序,按结果列表顺序
        priority_order = [r["agent"] for r in results]

    order_list = [a.strip() for a in priority_order.split(",") if a.strip()]
    conflicts = []
    merged = None

    # 按优先级顺序遍历
    for agent in order_list:
        for r in results:
            if r["agent"] == agent and r.get("summary"):
                merged = {
                    "summary": r["summary"],
                    "source": r["agent"],
                    "result": r.get("result"),
                }
                break
        if merged:
            break

    # 记录被忽略的结果为冲突
    if merged:
        for r in results:
            if r["agent"] != merged["source"]:
                conflicts.append({
                    "agent": r["agent"],
                    "summary": r.get("summary", ""),
                    "reason": f"priority 低于 {merged['source']}",
                })

    return merged, conflicts


def _resolve_voting(results):
    """投票策略:相同 summary 占比 >50% 取胜。"""
    if not results:
        return None, []

    # 按 summary 分组统计
    vote_map = {}
    for r in results:
        summary = r.get("summary", "")
        if summary not in vote_map:
            vote_map[summary] = []
        vote_map[summary].append(r)

    total = len(results)
    merged = None
    conflicts = []

    # 找占比 >50% 的组
    winner_summary = None
    winner_count = 0
    for summary, group in vote_map.items():
        if len(group) > total / 2:
            winner_summary = summary
            winner_count = len(group)
            break

    if winner_summary:
        winner = vote_map[winner_summary][0]
        merged = {
            "summary": winner_summary,
            "source": winner["agent"],
            "votes": winner_count,
            "total": total,
            "result": winner.get("result"),
        }
        # 记录非获胜的为冲突
        for r in results:
            if r.get("summary") != winner_summary:
                conflicts.append({
                    "agent": r["agent"],
                    "summary": r.get("summary", ""),
                    "reason": "voting 少数票",
                })
    else:
        # 无多数,转人工
        conflicts = [{
            "agent": r["agent"],
            "summary": r.get("summary", ""),
            "reason": "voting 无多数,转人工裁决",
        } for r in results]

    return merged, conflicts


def _resolve_human(results):
    """人工裁决:不自动合并,标记待人工。"""
    conflicts = [{
        "agent": r["agent"],
        "summary": r.get("summary", ""),
        "reason": "human 策略,待人工裁决",
    } for r in results]
    merged = {
        "summary": "[待人工裁决]",
        "source": None,
        "status": "unresolved",
        "all_results": [{"agent": r["agent"], "summary": r.get("summary", "")}
                        for r in results],
    }
    return merged, conflicts


def _resolve_latest(results):
    """最近优先:取 completed_at 最晚的结果。"""
    if not results:
        return None, []

    # 按 completed_at 排序
    sorted_results = sorted(results,
                            key=lambda x: _parse_iso(x.get("completed_at", "")) or datetime.min.replace(tzinfo=LOCAL_TZ),
                            reverse=True)
    winner = sorted_results[0]
    merged = {
        "summary": winner.get("summary", ""),
        "source": winner["agent"],
        "result": winner.get("result"),
        "completed_at": winner.get("completed_at", ""),
    }
    conflicts = [{
        "agent": r["agent"],
        "summary": r.get("summary", ""),
        "reason": f"latest 低于 {winner['agent']}(完成更早)",
    } for r in sorted_results[1:]]

    return merged, conflicts


# ============================================================
# resolve 子命令
# ============================================================

def cmd_resolve(args):
    """resolve:按策略解决冲突。"""
    exec_state = _load_exec_state(args.exec_id)
    if exec_state is None:
        print(f"FAIL  执行状态不存在:{args.exec_id}")
        return 1

    results = _collect_results(exec_state)
    if not results:
        print(f"FAIL  无已完成的结果可合并:{args.exec_id}")
        return 1

    strategy = args.strategy
    merged = None
    conflicts = []

    if strategy == "priority":
        merged, conflicts = _resolve_priority(results, args.priority_order)
    elif strategy == "voting":
        merged, conflicts = _resolve_voting(results)
    elif strategy == "human":
        merged, conflicts = _resolve_human(results)
    elif strategy == "latest":
        merged, conflicts = _resolve_latest(results)
    else:
        print(f"FAIL  未知策略:{strategy}")
        return 2

    # 写解决结果
    output = {
        "exec_id": args.exec_id,
        "resolved_at": _now_iso(),
        "strategy": strategy,
        "total_results": len(results),
        "merged_result": merged,
        "conflicts": conflicts,
    }
    try:
        RESULT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 写解决结果失败:{e}", file=sys.stderr)

    # 输出
    print(f"PASS  冲突解决:{args.exec_id}")
    print(f"  策略:{strategy}")
    print(f"  结果数:{len(results)}")
    if merged:
        print(f"  合并结果:{merged.get('summary', '')}")
        if merged.get("source"):
            print(f"  来源:{merged['source']}")
        if merged.get("status") == "unresolved":
            print(f"  ⚠ 待人工裁决({len(conflicts)} 个结果待选)")
    if conflicts:
        print(f"  冲突记录:{len(conflicts)} 条")
        for c in conflicts:
            print(f"    - {c['agent']}: {c['summary']}({c['reason']})")
    print(f"  结果文件:{RESULT_FILE}")

    # human 策略且无合并结果时返回 1(需人工介入)
    if strategy == "human":
        return 1
    return 0


# ============================================================
# argparse
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="resolve_conflicts.py",
        description="冲突解决脚本。按策略解决多 Agent 结果冲突。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码:0=成功;1=有错误/需人工;2=参数错误",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    p_res = sub.add_parser("resolve", help="按策略解决冲突")
    p_res.add_argument("--exec-id", required=True, help="执行 ID")
    p_res.add_argument("--strategy", required=True,
                      choices=["priority", "voting", "human", "latest"],
                      help="冲突解决策略")
    p_res.add_argument("--priority-order", default=None,
                       help="优先级顺序(逗号分隔,priority 策略用)")
    p_res.set_defaults(func=cmd_resolve)

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
        print(f"WARNING: 未捕获异常:{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
