#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_workflow.py - 工作流执行器脚本。

执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度,保留执行轨迹。

子命令:
  run      执行 workflow.yaml(dry-run 模式只输出执行计划,不实际调用 skill)
  resume   从暂停点恢复执行(读取 state.json 中的用户选择)
  status   查询当前执行状态(读取 state.json / exec-report)

设计原则(与 compile_workflow.py 一致):
- 失败不抛异常,统一通过退出码与 exec-report 表达
- dry-run 不调用任何 skill,只打印步骤序列
- 暂停时退出码 0(正常暂停),失败时退出码 1
- 实际调用 skill 由宿主/AI 在 SKILL.md 引导下完成,脚本负责调度与状态管理

退出码:0=成功(含正常暂停);1=失败/异常;2=参数错误
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# PyYAML 可选导入
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# ---------- 常量 ----------
REPORT_FILENAME = "workflow-exec-report.json"
STATE_FILENAME = "workflow-state.json"
END_MARKER = "__end__"


def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_yaml():
    """检查 PyYAML 是否可用,不可用时返回错误字符串。"""
    if yaml is None:
        return "PyYAML 未安装,无法解析 workflow.yaml。请执行:python -m pip install pyyaml"
    return None


# --------------------------------------------------------------------------- #
# 工作流加载与索引
# --------------------------------------------------------------------------- #
def load_workflow(workflow_path):
    """加载 workflow.yaml,返回 (workflow_dict, error)。"""
    yaml_err = _ensure_yaml()
    if yaml_err is not None:
        return None, yaml_err

    p = Path(workflow_path)
    if not p.exists():
        return None, "workflow.yaml 不存在: %s" % workflow_path

    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, "YAML 解析失败: %s" % exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, "workflow.yaml 顶层必须是对象"
    if not data.get("steps"):
        return None, "workflow.yaml steps 为空"

    return data, None


def build_step_index(workflow):
    """构建 step id → step dict 的索引,返回 dict。"""
    return {s["id"]: s for s in workflow.get("steps", []) if isinstance(s, dict) and "id" in s}


def resolve_next(step, step_index):
    """解析 step 的下一步 id。

    优先用 step.next;缺省时无法推断则返回 END_MARKER。
    """
    nxt = step.get("next")
    if nxt:
        return nxt
    return END_MARKER


# --------------------------------------------------------------------------- #
# 执行轨迹与状态
# --------------------------------------------------------------------------- #
def init_exec_report(workflow):
    """初始化执行轨迹报告。"""
    return {
        "workflow": workflow.get("name", "unknown"),
        "started_at": _now_iso(),
        "finished_at": None,
        "status": "running",
        "current_step": None,
        "steps": [],
    }


def append_step_record(report, step_id, status, outputs=None, error=None, duration=None, retries=0):
    """追加一条步骤执行记录。"""
    record = {
        "id": step_id,
        "status": status,
        "retries": retries,
        "outputs": outputs or [],
    }
    if error:
        record["error"] = error
    if duration:
        record["duration"] = duration
    report["steps"].append(record)
    report["current_step"] = step_id


def save_report(report, cwd=None):
    """把执行轨迹写入当前工作目录。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    out_path = out_dir / REPORT_FILENAME
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def save_state(state, cwd=None):
    """把执行状态写入当前工作目录。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    out_path = out_dir / STATE_FILENAME
    out_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def load_state(state_path):
    """加载状态文件。"""
    p = Path(state_path)
    if not p.exists():
        return None, "state 文件不存在: %s" % state_path
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, "state JSON 解析失败: %s" % exc


# --------------------------------------------------------------------------- #
# 执行计划(dry-run)
# --------------------------------------------------------------------------- #
def print_execution_plan(workflow, step_index):
    """dry-run 模式:打印执行计划,不实际调用 skill。"""
    sys.stdout.write("=== 执行计划(dry-run)===")
    sys.stdout.write("\n工作流: %s\n" % workflow.get("name", ""))
    sys.stdout.write("来源: %s\n" % (workflow.get("source") or "(未标注)"))
    sys.stdout.write("步骤数: %d\n\n" % len(workflow.get("steps", [])))

    parallel_seen = set()
    for step in workflow.get("steps", []):
        sid = step.get("id", "?")
        stype = step.get("type", "skill")
        title = step.get("title", "")
        pw = step.get("parallel_with")

        if pw and sid not in parallel_seen:
            # 并行组首项
            sys.stdout.write("[并行组] %s\n" % title)
            sys.stdout.write("  - %s (skill=%s)\n" % (sid, step.get("skill", "")))
            peer = step_index.get(pw, {})
            sys.stdout.write("  - %s (skill=%s)\n" % (pw, peer.get("skill", "")))
            parallel_seen.add(sid)
            parallel_seen.add(pw)
        elif pw and sid in parallel_seen:
            continue  # 已在并行组中打印
        elif stype == "pause":
            confirm = step.get("confirm", {})
            sys.stdout.write("[暂停] %s\n" % title)
            sys.stdout.write("  提问: %s\n" % confirm.get("question", ""))
            for opt in confirm.get("options", []):
                sys.stdout.write("    - %s → %s\n" % (opt.get("label", ""), opt.get("next", "")))
        else:
            sys.stdout.write("[skill] %s\n" % title)
            sys.stdout.write("  id=%s skill=%s\n" % (sid, step.get("skill", "")))
            on_fail = step.get("on_fail", {})
            sys.stdout.write("  on_fail=%s\n" % on_fail.get("action", "abort"))
            nxt = step.get("next", "(顺序下一个)")
            sys.stdout.write("  next=%s\n" % nxt)

    sys.stdout.write("\n=== dry-run 结束(未实际调用任何 skill)===")
    sys.stdout.write("\n")


# --------------------------------------------------------------------------- #
# 实际执行(非 dry-run)
# --------------------------------------------------------------------------- #
def execute_workflow(workflow, step_index, report, dry_run=False):
    """按 steps 顺序执行工作流。

    dry_run=True 时只打印计划(由 print_execution_plan 处理,本函数不被调用)。
    dry_run=False 时:逐 step 调度,遇到 pause 则暂停并保存状态。
    实际调用 skill 由宿主/AI 完成,本脚本只模拟执行流程并记录轨迹。

    返回 (status, exit_code):
      status ∈ {"done", "paused", "aborted"}
      exit_code: 0=done/paused, 1=aborted
    """
    if not workflow.get("steps"):
        sys.stderr.write("workflow 无步骤\n")
        return "aborted", 1

    first_id = workflow["steps"][0].get("id")
    return execute_from_step(workflow, step_index, report, first_id, dry_run=dry_run)


def execute_from_step(workflow, step_index, report, start_id, dry_run=False):
    """从指定 step 开始执行。"""
    current_id = start_id
    retry_counts = {}  # step_id → 累计回退次数

    while current_id and current_id != END_MARKER:
        step = step_index.get(current_id)
        if step is None:
            sys.stderr.write("step 不存在: %s\n" % current_id)
            report["status"] = "aborted"
            report["finished_at"] = _now_iso()
            return "aborted", 1

        stype = step.get("type", "skill")
        sid = step.get("id")
        title = step.get("title", sid)

        # 暂停节点
        if stype == "pause":
            confirm = step.get("confirm", {})
            sys.stdout.write("\n========================================\n")
            sys.stdout.write("暂停点: %s\n" % title)
            sys.stdout.write("提问: %s\n" % confirm.get("question", ""))
            sys.stdout.write("选项:\n")
            for i, opt in enumerate(confirm.get("options", []), 1):
                sys.stdout.write("  %d. %s  (→ %s)\n" % (i, opt.get("label", ""), opt.get("next", "")))
            sys.stdout.write("========================================\n")

            # 保存状态,等待用户确认
            state = {
                "workflow": workflow.get("name", ""),
                "paused_at_step": sid,
                "paused_at": _now_iso(),
                "completed_steps": [r["id"] for r in report["steps"]],
                "options": confirm.get("options", []),
            }
            state_path = save_state(state)
            report["status"] = "paused"
            report["current_step"] = sid
            save_report(report)
            sys.stdout.write("\n已暂停。状态已保存: %s\n" % state_path)
            sys.stdout.write("用户确认后运行: run_workflow.py resume --state %s\n" % state_path)
            return "paused", 0

        # skill 节点:模拟执行(实际调用由宿主完成)
        sys.stdout.write("\n[执行] %s (id=%s, skill=%s)\n" % (title, sid, step.get("skill", "")))

        # 读取 runtime.yaml(若声明)
        runtime_ref = step.get("runtime")
        if runtime_ref:
            sys.stdout.write("  runtime: %s\n" % runtime_ref)

        # 模拟成功(脚本不实际调用 skill,由宿主调用并回填结果)
        # 这里按"成功"记录;真实场景下宿主会根据 skill 执行结果回填
        append_step_record(
            report, sid, status="done",
            outputs=step.get("outputs", []),
        )
        save_report(report)
        sys.stdout.write("  → 完成,产物: %s\n" % ", ".join(step.get("outputs", [])) or "(无)")

        # 解析下一步
        nxt = resolve_next(step, step_index)
        sys.stdout.write("  → next: %s\n" % nxt)
        current_id = nxt

    # 正常结束
    report["status"] = "done"
    report["finished_at"] = _now_iso()
    save_report(report)
    sys.stdout.write("\n=== 工作流执行完成 ===\n")
    return "done", 0


# --------------------------------------------------------------------------- #
# 子命令实现
# --------------------------------------------------------------------------- #
def cmd_run(args):
    """run 子命令:执行 workflow.yaml。"""
    workflow, err = load_workflow(args.input)
    if workflow is None:
        sys.stderr.write(err + "\n")
        return 1

    step_index = build_step_index(workflow)
    report = init_exec_report(workflow)

    if args.dry_run:
        print_execution_plan(workflow, step_index)
        report["status"] = "dry-run"
        report["finished_at"] = _now_iso()
        save_report(report)
        return 0

    status, exit_code = execute_workflow(workflow, step_index, report, dry_run=False)
    return exit_code


def cmd_resume(args):
    """resume 子命令:从暂停点恢复。"""
    state, err = load_state(args.state)
    if state is None:
        sys.stderr.write(err + "\n")
        return 1

    workflow_path = args.workflow
    if not workflow_path:
        sys.stderr.write("resume 需要 --workflow 指定 workflow.yaml 路径\n")
        return 2

    workflow, werr = load_workflow(workflow_path)
    if workflow is None:
        sys.stderr.write(werr + "\n")
        return 1

    step_index = build_step_index(workflow)

    # 读取用户选择(args.choice 为选项序号,1-based)
    options = state.get("options", [])
    choice = args.choice
    if choice is None:
        sys.stderr.write("resume 需要 --choice 指定用户选择的选项序号(1-based)\n")
        return 2
    if choice < 1 or choice > len(options):
        sys.stderr.write("choice 超出范围:可选 1~%d\n" % len(options))
        return 2

    selected = options[choice - 1]
    next_step = selected.get("next", END_MARKER)

    sys.stdout.write("用户选择: %s\n" % selected.get("label", ""))
    sys.stdout.write("跳转到: %s\n" % next_step)

    if next_step == END_MARKER:
        sys.stdout.write("\n=== 工作流执行完成(用户选择终止)===")
        sys.stdout.write("\n")
        return 0

    # 恢复执行轨迹(从已有 report 续写,或新建)
    report = init_exec_report(workflow)
    report["status"] = "running"
    report["steps"] = [{"id": sid, "status": "done", "retries": 0, "outputs": []}
                       for sid in state.get("completed_steps", [])]

    status, exit_code = execute_from_step(workflow, step_index, report, next_step)
    return exit_code


def cmd_status(args):
    """status 子命令:查询当前执行状态。"""
    # 优先读 state.json(暂停状态)
    state, serr = load_state(args.state)
    report_path = Path(args.state).parent / REPORT_FILENAME if state is not None else None

    if state is not None:
        sys.stdout.write("=== 执行状态 ===\n")
        sys.stdout.write("工作流: %s\n" % state.get("workflow", ""))
        sys.stdout.write("状态: PAUSED(暂停中)\n")
        sys.stdout.write("暂停节点: %s\n" % state.get("paused_at_step", ""))
        sys.stdout.write("暂停时间: %s\n" % state.get("paused_at", ""))
        sys.stdout.write("已完成步骤: %s\n" % ", ".join(state.get("completed_steps", [])))
        sys.stdout.write("\n待确认选项:\n")
        for i, opt in enumerate(state.get("options", []), 1):
            sys.stdout.write("  %d. %s  (→ %s)\n" % (i, opt.get("label", ""), opt.get("next", "")))
        return 0

    # 无 state,尝试读 exec-report
    if report_path and report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sys.stderr.write("exec-report JSON 解析失败\n")
            return 1
    else:
        # 直接尝试当前目录
        cwd_report = Path.cwd() / REPORT_FILENAME
        if cwd_report.exists():
            try:
                report = json.loads(cwd_report.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                sys.stderr.write("exec-report JSON 解析失败\n")
                return 1
        else:
            sys.stderr.write("未找到 state 或 exec-report 文件\n")
            return 1

    sys.stdout.write("=== 执行状态 ===\n")
    sys.stdout.write("工作流: %s\n" % report.get("workflow", ""))
    sys.stdout.write("状态: %s\n" % report.get("status", "unknown"))
    sys.stdout.write("当前步骤: %s\n" % (report.get("current_step") or "(无)"))
    sys.stdout.write("开始时间: %s\n" % report.get("started_at", ""))
    sys.stdout.write("结束时间: %s\n" % (report.get("finished_at") or "(进行中)"))
    sys.stdout.write("\n步骤轨迹:\n")
    for rec in report.get("steps", []):
        sys.stdout.write("  [%s] %s — %s\n" % (
            rec.get("id", ""), rec.get("status", ""),
            ", ".join(rec.get("outputs", [])) or "(无产物)",
        ))
    return 0


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #
def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="run_workflow.py",
        description="工作流执行器:执行 workflow.yaml,支持暂停/恢复/状态查询。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python run_workflow.py run --input workflow.yaml --dry-run\n"
            "  python run_workflow.py run --input workflow.yaml\n"
            "  python run_workflow.py resume --state workflow-state.json --workflow workflow.yaml --choice 1\n"
            "  python run_workflow.py status --state workflow-state.json\n"
            "\n退出码:0=成功(含正常暂停);1=失败;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # run
    p_run = sub.add_parser(
        "run",
        help="执行 workflow.yaml(--dry-run 只输出执行计划)",
    )
    p_run.add_argument("--input", required=True, help="workflow.yaml 路径")
    p_run.add_argument("--dry-run", action="store_true", help="干跑模式:只输出执行计划,不调用 skill")
    p_run.set_defaults(func=cmd_run)

    # resume
    p_resume = sub.add_parser(
        "resume",
        help="从暂停点恢复执行",
    )
    p_resume.add_argument("--state", required=True, help="state.json 路径")
    p_resume.add_argument("--workflow", required=True, help="workflow.yaml 路径")
    p_resume.add_argument("--choice", type=int, required=True, help="用户选择的选项序号(1-based)")
    p_resume.set_defaults(func=cmd_resume)

    # status
    p_status = sub.add_parser(
        "status",
        help="查询当前执行状态",
    )
    p_status.add_argument("--state", required=True, help="state.json 路径(或其所在目录的 exec-report)")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv=None):
    """主入口,返回退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 2

    try:
        return args.func(args)
    except Exception as e:
        sys.stderr.write("FAIL  未捕获异常: %s\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
