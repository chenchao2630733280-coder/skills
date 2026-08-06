#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""execute_agents.py - Agent Runtime 执行层脚本。

子命令:
  delegate  --from <主Agent> --to <从Agent列表> --tasks <JSON任务数组>
             [--mode master-slave|peer|pipeline|fan-out] [--timeout 300]
             [--protocol <orchestration-protocol.md路径>]
             委派子任务给子 Agent,创建执行状态
  collect   --exec-id <id> [--timeout 300]
             收集子 Agent 结果,检查超时
  merge     --exec-id <id> [--strategy priority|voting|human|latest]
             [--priority-order "sub-1,sub-2,sub-3"]
             合并结果,产出执行报告(调用 resolve_conflicts.py)
  monitor   --exec-id <id> [--cancel <Agent名>]
             监控执行状态,支持取消

产物:
  agent-exec-state.json  - 执行状态(当前工作目录)
  agent-exec-report.json - 执行报告(merge 时产出)

退出码:0=成功;1=有错误(无结果/超时/部分失败);2=参数错误

设计原则:执行器是辅助调度,不是关键路径。宁可降级到人工也不能拖垮主流程。
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOCAL_TZ = timezone(timedelta(hours=8))
STATE_FILE = Path.cwd() / "agent-exec-state.json"
REPORT_FILE = Path.cwd() / "agent-exec-report.json"
DEFAULT_TIMEOUT = 300
RETENTION_DAYS = 30

# 冲突解决脚本路径(同目录下的 resolve_conflicts.py)
CONFLICT_SCRIPT = Path(__file__).parent / "resolve_conflicts.py"


# ============================================================
# 工具函数
# ============================================================

def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _now():
    return datetime.now(LOCAL_TZ)


def _parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _gen_exec_id():
    """生成 exec-{YYYYMMDD}-{NNN} 格式的执行 ID。"""
    today = _now().strftime("%Y%m%d")
    prefix = f"exec-{today}-"
    nnn = 1
    # 读取已有状态文件确定序号
    existing = []
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = [e.get("exec_id", "") for e in data]
            elif "exec_id" in data:
                existing = [data["exec_id"]]
        except Exception:
            pass
    while f"{prefix}{nnn:03d}" in existing:
        nnn += 1
    return f"{prefix}{nnn:03d}"


def _gen_msg_id(exec_state):
    """生成 M001/M002/... 格式的消息 ID。"""
    existing = [d.get("msg_id", "") for d in exec_state.get("delegations", [])]
    n = 1
    while f"M{n:03d}" in existing:
        n += 1
    return f"M{n:03d}"


def _load_exec_state(exec_id):
    """加载指定 exec_id 的执行状态。支持单文件(单 exec)或多文件(列表)格式。"""
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: 解析执行状态文件失败:{e}", file=sys.stderr)
        return None
    # 支持列表格式(多个 exec)和单对象格式
    if isinstance(data, list):
        for e in data:
            if e.get("exec_id") == exec_id:
                return e
        return None
    if isinstance(data, dict) and data.get("exec_id") == exec_id:
        return data
    return None


def _save_exec_state(exec_state):
    """保存执行状态(支持多 exec 列表)。失败只打 WARNING。"""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                # 更新或追加
                found = False
                for i, e in enumerate(data):
                    if e.get("exec_id") == exec_state["exec_id"]:
                        data[i] = exec_state
                        found = True
                        break
                if not found:
                    data.append(exec_state)
            elif isinstance(data, dict):
                if data.get("exec_id") == exec_state["exec_id"]:
                    data = exec_state
                else:
                    data = [data, exec_state]
            else:
                data = [exec_state]
        else:
            data = exec_state
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 保存执行状态失败:{e}", file=sys.stderr)


# ============================================================
# delegate 子命令
# ============================================================

def cmd_delegate(args):
    """delegate:委派子任务给子 Agent。"""
    # 解析任务列表
    try:
        tasks = json.loads(args.tasks)
        if not isinstance(tasks, list) or not tasks:
            print("FAIL  --tasks 必须是 JSON 数组且非空")
            return 2
    except Exception as e:
        print(f"FAIL  解析 --tasks JSON 失败:{e}")
        return 2

    # 解析子 Agent 列表
    to_agents = [a.strip() for a in args.to.split(",") if a.strip()]
    if not to_agents:
        print("FAIL  --to 不能为空")
        return 2

    # 读取协议(若存在,仅记录遵循,不强制校验)
    protocol_file = args.protocol or "orchestration-protocol.md"
    protocol_note = ""
    if Path(protocol_file).exists():
        protocol_note = f"遵循协议:{protocol_file}"
    else:
        protocol_note = "无协议文件(将使用默认消息格式)"

    exec_id = _gen_exec_id()
    now = _now_iso()
    timeout = args.timeout or DEFAULT_TIMEOUT
    deadline = (_now() + timedelta(seconds=timeout)).isoformat(timespec="seconds")

    exec_state = {
        "exec_id": exec_id,
        "created_at": now,
        "mode": args.mode,
        "master": args.from_agent,
        "protocol_note": protocol_note,
        "timeout": timeout,
        "delegations": [],
        "status": "running",
        "summary": None,
    }

    # 为每个任务创建委派记录
    # 如果任务数 == Agent 数,一一对应;否则所有任务委派给所有 Agent
    if len(tasks) == len(to_agents):
        pairs = list(zip(tasks, to_agents))
    elif len(tasks) == 1:
        # 单任务委派给所有 Agent(扇出)
        pairs = [(tasks[0], a) for a in to_agents]
    else:
        # 多任务委派给所有 Agent(每个 Agent 执行所有任务)
        pairs = [(t, a) for t in tasks for a in to_agents]

    for task, agent in pairs:
        msg_id = _gen_msg_id(exec_state)
        exec_state["delegations"].append({
            "msg_id": msg_id,
            "from": args.from_agent,
            "to": agent,
            "type": "delegate",
            "correlation_id": exec_id,
            "task": task.get("task", ""),
            "assigned_skill": task.get("skill", ""),
            "payload": task,
            "deadline": deadline,
            "ack_required": True,
            "timestamp": now,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "result": None,
        })

    _save_exec_state(exec_state)

    print(f"PASS  委派执行:{exec_id}")
    print(f"  模式:{args.mode}")
    print(f"  主 Agent:{args.from_agent}")
    print(f"  子 Agent:{','.join(to_agents)}")
    print(f"  委派数:{len(exec_state['delegations'])}")
    print(f"  超时:{timeout}s(deadline:{deadline})")
    print(f"  {protocol_note}")
    print(f"  状态文件:{STATE_FILE}")
    print(f"  exec_id:{exec_id}")
    return 0


# ============================================================
# collect 子命令
# ============================================================

def cmd_collect(args):
    """collect:收集子 Agent 结果,检查超时。"""
    exec_state = _load_exec_state(args.exec_id)
    if exec_state is None:
        print(f"FAIL  执行状态不存在:{args.exec_id}")
        return 1

    now = _now()
    timeout = args.timeout or exec_state.get("timeout", DEFAULT_TIMEOUT)

    completed = 0
    failed = 0
    timeout_count = 0
    pending = 0

    for d in exec_state.get("delegations", []):
        status = d.get("status", "pending")
        if status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1
        elif status == "timeout":
            timeout_count += 1
        else:
            # pending 或 running,检查是否超时
            deadline_str = d.get("deadline", "")
            deadline = _parse_iso(deadline_str)
            if deadline and now > deadline:
                d["status"] = "timeout"
                timeout_count += 1
                print(f"WARN  {d['to']} 超时(deadline:{deadline_str})")
            else:
                pending += 1

    # 更新执行状态
    total = len(exec_state.get("delegations", []))
    if pending == 0:
        if failed == total:
            exec_state["status"] = "failed"
        elif timeout_count > 0 or failed > 0:
            exec_state["status"] = "partial"
        else:
            exec_state["status"] = "completed"
    else:
        exec_state["status"] = "running"
    _save_exec_state(exec_state)

    print(f"PASS  收集结果:{args.exec_id}")
    print(f"  总委派数:{total}")
    print(f"  已完成:{completed}")
    print(f"  失败:{failed}")
    print(f"  超时:{timeout_count}")
    print(f"  待处理:{pending}")
    print(f"  整体状态:{exec_state['status']}")

    if timeout_count > 0:
        print(f"WARN  {timeout_count} 个子 Agent 超时,建议转人工裁决(merge --strategy human)")
    return 0 if pending == 0 else 1


# ============================================================
# merge 子命令
# ============================================================

def cmd_merge(args):
    """merge:合并结果,产出执行报告。调用 resolve_conflicts.py 解决冲突。"""
    exec_state = _load_exec_state(args.exec_id)
    if exec_state is None:
        print(f"FAIL  执行状态不存在:{args.exec_id}")
        return 1

    # 收集已完成的结果
    results = []
    for d in exec_state.get("delegations", []):
        if d.get("status") == "completed" and d.get("result"):
            results.append({
                "agent": d.get("to", ""),
                "msg_id": d.get("msg_id", ""),
                "status": d.get("status", ""),
                "summary": (d.get("result") or {}).get("summary", ""),
                "result": d.get("result"),
                "completed_at": d.get("completed_at", ""),
            })

    strategy = args.strategy or "priority"

    # 调用 resolve_conflicts.py 解决冲突
    merged_result = None
    conflicts = []
    if results:
        if CONFLICT_SCRIPT.exists():
            try:
                cmd = [
                    sys.executable, str(CONFLICT_SCRIPT), "resolve",
                    "--exec-id", args.exec_id,
                    "--strategy", strategy,
                ]
                if args.priority_order:
                    cmd.extend(["--priority-order", args.priority_order])
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      encoding="utf-8", timeout=30)
                if proc.returncode == 0:
                    # 尝试读取 resolve_conflicts 产出的结果
                    resolve_output = Path.cwd() / "conflict-resolve-result.json"
                    if resolve_output.exists():
                        resolve_data = json.loads(resolve_output.read_text(encoding="utf-8"))
                        merged_result = resolve_data.get("merged_result")
                        conflicts = resolve_data.get("conflicts", [])
                    else:
                        # 内联解决(脚本可能直接输出)
                        merged_result = {"summary": results[0].get("summary", ""),
                                         "source": results[0].get("agent", "")}
                        conflicts = []
                else:
                    print(f"WARNING: resolve_conflicts 返回 {proc.returncode}: {proc.stderr}",
                          file=sys.stderr)
                    merged_result = {"summary": "冲突解决失败,取首个结果",
                                     "source": results[0].get("agent", "")}
            except Exception as e:
                print(f"WARNING: 调用 resolve_conflicts 失败:{e}", file=sys.stderr)
                merged_result = {"summary": results[0].get("summary", ""),
                                 "source": results[0].get("agent", "")}
        else:
            # resolve_conflicts.py 不存在,内联简单合并
            merged_result = {"summary": results[0].get("summary", ""),
                             "source": results[0].get("agent", "")}

    # 统计
    total = len(exec_state.get("delegations", []))
    completed = sum(1 for d in exec_state["delegations"] if d.get("status") == "completed")
    failed = sum(1 for d in exec_state["delegations"] if d.get("status") == "failed")
    timeout_count = sum(1 for d in exec_state["delegations"] if d.get("status") == "timeout")

    report = {
        "exec_id": args.exec_id,
        "created_at": exec_state.get("created_at", ""),
        "completed_at": _now_iso(),
        "mode": exec_state.get("mode", ""),
        "master": exec_state.get("master", ""),
        "total_delegations": total,
        "completed": completed,
        "failed": failed,
        "timeout": timeout_count,
        "results": results,
        "merge_strategy": strategy,
        "merged_result": merged_result,
        "conflicts": conflicts,
    }

    # 更新执行状态
    exec_state["status"] = "completed" if failed == 0 and timeout_count == 0 else "partial"
    exec_state["summary"] = merged_result
    _save_exec_state(exec_state)

    # 写执行报告
    try:
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 写执行报告失败:{e}", file=sys.stderr)

    print(f"PASS  合并结果:{args.exec_id}")
    print(f"  总委派数:{total}")
    print(f"  已完成:{completed}")
    print(f"  失败:{failed}")
    print(f"  超时:{timeout_count}")
    print(f"  合并策略:{strategy}")
    if merged_result:
        print(f"  合并结果:{merged_result.get('summary', '')}(来源:{merged_result.get('source', '')})")
    if conflicts:
        print(f"  冲突记录:{len(conflicts)} 条")
    print(f"  报告文件:{REPORT_FILE}")
    return 0


# ============================================================
# monitor 子命令
# ============================================================

def cmd_monitor(args):
    """monitor:监控执行状态,支持取消。"""
    exec_state = _load_exec_state(args.exec_id)
    if exec_state is None:
        print(f"FAIL  执行状态不存在:{args.exec_id}")
        return 1

    # 取消指定 Agent
    if args.cancel:
        cancelled = False
        for d in exec_state.get("delegations", []):
            if d.get("to") == args.cancel and d.get("status") in ("pending", "running"):
                d["status"] = "cancelled"
                d["completed_at"] = _now_iso()
                cancelled = True
        if cancelled:
            _save_exec_state(exec_state)
            print(f"PASS  已取消 Agent:{args.cancel}")
        else:
            print(f"WARN  未找到可取消的 Agent:{args.cancel}(可能已完成或不存在)")
        return 0

    # 打印执行状态
    print(f"执行状态:{args.exec_id}")
    print(f"  模式:{exec_state.get('mode', '')}")
    print(f"  主 Agent:{exec_state.get('master', '')}")
    print(f"  整体状态:{exec_state.get('status', '')}")
    print(f"  创建时间:{exec_state.get('created_at', '')}")
    print()
    print(f"{'Msg ID':<8} | {'To':<20} | {'任务':<25} | {'状态':<12} | {'Deadline'}")
    print("-" * 100)
    for d in exec_state.get("delegations", []):
        msg_id = d.get("msg_id", "")
        to = d.get("to", "")
        task = d.get("task", "")[:25]
        status = d.get("status", "")
        deadline = d.get("deadline", "")
        print(f"{msg_id:<8} | {to:<20} | {task:<25} | {status:<12} | {deadline}")
    return 0


# ============================================================
# argparse
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="execute_agents.py",
        description="Agent Runtime 执行层脚本。delegate/collect/merge/monitor。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码:0=成功;1=有错误;2=参数错误",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # delegate
    p_del = sub.add_parser("delegate", help="委派子任务给子 Agent")
    p_del.add_argument("--from", dest="from_agent", required=True, help="主 Agent 标识")
    p_del.add_argument("--to", required=True, help="子 Agent 列表(逗号分隔)")
    p_del.add_argument("--tasks", required=True, help="任务 JSON 数组")
    p_del.add_argument("--mode", default="master-slave",
                       choices=["master-slave", "peer", "pipeline", "fan-out"],
                       help="执行模式(默认 master-slave)")
    p_del.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                       help=f"超时秒数(默认 {DEFAULT_TIMEOUT})")
    p_del.add_argument("--protocol", default=None, help="协议文件路径")
    p_del.set_defaults(func=cmd_delegate)

    # collect
    p_col = sub.add_parser("collect", help="收集子 Agent 结果")
    p_col.add_argument("--exec-id", required=True, help="执行 ID")
    p_col.add_argument("--timeout", type=int, default=None, help="超时秒数(覆盖原配置)")
    p_col.set_defaults(func=cmd_collect)

    # merge
    p_mer = sub.add_parser("merge", help="合并结果")
    p_mer.add_argument("--exec-id", required=True, help="执行 ID")
    p_mer.add_argument("--strategy", default="priority",
                       choices=["priority", "voting", "human", "latest"],
                       help="冲突解决策略(默认 priority)")
    p_mer.add_argument("--priority-order", default=None, help="优先级顺序(逗号分隔)")
    p_mer.set_defaults(func=cmd_merge)

    # monitor
    p_mon = sub.add_parser("monitor", help="监控执行状态")
    p_mon.add_argument("--exec-id", required=True, help="执行 ID")
    p_mon.add_argument("--cancel", default=None, help="取消指定 Agent")
    p_mon.set_defaults(func=cmd_monitor)

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
        return 1  # 执行器失败标 1(不阻断主流程由调用方处理)


if __name__ == "__main__":
    sys.exit(main())
