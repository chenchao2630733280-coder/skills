#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replan.py - 重规划器脚本。

提供两个子命令:
  replan  接收原 task-tree.json + 失败信息 JSON,做影响分析后产出
          task-tree.v2.json(符合 task-tree-schema)+ replan-report.md(变更说明)。
          实际策略选择由 AI 在 SKILL.md 引导下完成,脚本负责影响分析、
          格式校验与产物脚手架生成。
  impact  读取 task-tree.json + 失败任务 id,输出受影响任务清单
          (直接/间接依赖传播 + 影响分级)。

退出码:0=成功;1=校验失败;2=参数错误。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 常量
SCHEMA_VERSION = "1.0"
VALID_PRIORITIES = ("P0", "P1", "P2")
VALID_COMPLEXITIES_ROOT = ("low", "medium", "high")
VALID_EST_COMPLEXITIES = ("★", "★★", "★★★", "★★★★", "★★★★★")

MAX_REPLAN_ROUNDS = 3  # 关键约束:最多 3 轮重规划,超过转人工

# 影响分级
IMPACT_BLOCK = "阻断"      # 关键路径(P0)被阻断,需立即处理
IMPACT_DEGRADE = "降级"    # 非关键任务受影响,可降级处理
IMPACT_NONE = "无影响"     # 不在依赖传播路径上


def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Schema 校验(与 task-planner 的 task-tree-schema 保持一致)
# --------------------------------------------------------------------------- #
def validate_task_tree(data):
    """校验 task-tree 字典是否符合 Schema。

    返回 (ok: bool, errors: list[str])。
    """
    errors = []

    if not isinstance(data, dict):
        return False, ["顶层必须是对象"]

    if data.get("version") != SCHEMA_VERSION:
        errors.append("version 必须为 %r,实际 %r" % (SCHEMA_VERSION, data.get("version")))

    root = data.get("root")
    if not isinstance(root, dict):
        errors.append("root 必须是对象")
    else:
        for field in ("id", "title", "complexity"):
            if not root.get(field):
                errors.append("root.%s 缺失" % field)
        if root.get("complexity") and root.get("complexity") not in VALID_COMPLEXITIES_ROOT:
            errors.append("root.complexity 必须为 %s" % "/".join(VALID_COMPLEXITIES_ROOT))

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks 必须是数组")
        return len(errors) == 0, errors

    ids = set()
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append("tasks[%d] 必须是对象" % idx)
            continue
        for field in ("id", "title", "priority", "est_complexity"):
            if not task.get(field):
                errors.append("tasks[%d].%s 缺失" % (idx, field))
        tid = task.get("id")
        if tid:
            if tid in ids:
                errors.append("tasks[%d].id 重复:%s" % (idx, tid))
            ids.add(tid)
        if task.get("priority") and task.get("priority") not in VALID_PRIORITIES:
            errors.append("tasks[%d].priority 必须为 %s" % (idx, "/".join(VALID_PRIORITIES)))
        ec = task.get("est_complexity")
        if ec and ec not in VALID_EST_COMPLEXITIES:
            errors.append("tasks[%d].est_complexity 必须为 ★~★★★★★" % idx)
        for arr_field in ("depends_on", "parallel_with"):
            val = task.get(arr_field)
            if val is not None and not isinstance(val, list):
                errors.append("tasks[%d].%s 必须为数组" % (idx, arr_field))

    # 引用完整性
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        for arr_field in ("depends_on", "parallel_with"):
            for ref in task.get(arr_field, []) or []:
                if ref not in ids:
                    errors.append("tasks[%d].%s 引用了不存在的 id:%s" % (idx, arr_field, ref))

    return len(errors) == 0, errors


def validate_failure_info(data):
    """校验失败信息 JSON 结构。

    必填:failed_task_id / error_message;suggested_action 与 error_code 可选。
    返回 (ok: bool, errors: list[str])。
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["失败信息必须是对象"]
    if not data.get("failed_task_id"):
        errors.append("failed_task_id 缺失")
    if not data.get("error_message"):
        errors.append("error_message 缺失")
    return len(errors) == 0, errors


# --------------------------------------------------------------------------- #
# 依赖图与影响分析(BFS 反向遍历 depends_on)
# --------------------------------------------------------------------------- #
def build_reverse_graph(tasks):
    """构建反向依赖图:被依赖任务 id -> 依赖它的任务 id 列表。

    若 B 的 depends_on 含 A,则 reverse[A] 含 B(B 受 A 影响)。
    """
    reverse = {t["id"]: [] for t in tasks if isinstance(t, dict) and t.get("id")}
    id_set = set(reverse.keys())
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        if tid not in id_set:
            continue
        for dep in t.get("depends_on", []) or []:
            if dep in id_set:
                reverse[dep].append(tid)
    return reverse


def analyze_impact(tasks, failed_task_id):
    """分析失败任务的影响传播。

    返回 dict:
      failed_task       : 失败任务节点(找不到则 None)
      direct            : 直接依赖失败任务的任务列表(id + title + priority)
      indirect          : 间接依赖(传递链)的任务列表
      affected_ids      : 所有受影响任务 id 集合(不含失败任务本身)
      impact_level      : 失败任务的影响分级(阻断/降级/无影响)
      layers            : BFS 分层(第 1 层=直接,第 2 层=间接...)
      not_affected      : 不受影响的任务 id 列表
    """
    task_map = {t["id"]: t for t in tasks if isinstance(t, dict) and t.get("id")}
    reverse = build_reverse_graph(tasks)

    failed_task = task_map.get(failed_task_id)
    if failed_task is None:
        return {
            "failed_task": None,
            "direct": [],
            "indirect": [],
            "affected_ids": set(),
            "impact_level": IMPACT_NONE,
            "layers": [],
            "not_affected": [tid for tid in task_map.keys()],
        }

    # BFS 反向遍历,找出所有受影响任务
    affected_ids = set()
    layers = []
    visited = {failed_task_id}
    current = [tid for tid in reverse.get(failed_task_id, []) if tid not in visited]
    for tid in current:
        affected_ids.add(tid)
        visited.add(tid)
    if current:
        layers.append(sorted(current))

    # 继续传播
    frontier = list(current)
    while frontier:
        nxt = []
        for tid in frontier:
            for child in reverse.get(tid, []):
                if child not in visited:
                    affected_ids.add(child)
                    visited.add(child)
                    nxt.append(child)
        if nxt:
            layers.append(sorted(nxt))
        frontier = nxt

    direct = [task_map[tid] for tid in (layers[0] if layers else [])]
    indirect = [task_map[tid] for tid in sum(layers[1:], [])] if len(layers) > 1 else []

    # 影响分级:失败任务本身 P0 -> 阻断;有 P0 直接/间接受影响 -> 阻断;
    #          否则仅 P1/P2 受影响 -> 降级;无人受影响 -> 无影响
    if failed_task.get("priority") == "P0":
        impact_level = IMPACT_BLOCK
    elif any(t.get("priority") == "P0" for t in direct + indirect):
        impact_level = IMPACT_BLOCK
    elif affected_ids:
        impact_level = IMPACT_DEGRADE
    else:
        impact_level = IMPACT_NONE

    not_affected = [tid for tid in task_map.keys()
                    if tid != failed_task_id and tid not in affected_ids]

    return {
        "failed_task": failed_task,
        "direct": direct,
        "indirect": indirect,
        "affected_ids": affected_ids,
        "impact_level": impact_level,
        "layers": layers,
        "not_affected": not_affected,
    }


# --------------------------------------------------------------------------- #
# 策略建议(基于 suggested_action + 影响分级,仅做框架性建议)
# --------------------------------------------------------------------------- #
STRATEGY_HINTS = {
    "重排": "重排",
    "reorder": "重排",
    "跳过": "跳过",
    "skip": "跳过",
    "拆分": "拆分",
    "split": "拆分",
    "合并": "合并",
    "merge": "合并",
    "降级": "降级",
    "degrade": "降级",
    "人工": "人工接管",
    "manual": "人工接管",
}


def suggest_strategy(failure_info, impact):
    """根据 suggested_action 与影响分级给出策略建议(框架性,实际由 AI 决定)。"""
    suggested = failure_info.get("suggested_action") or ""
    hinted = STRATEGY_HINTS.get(str(suggested).strip().lower())
    if hinted:
        return hinted
    # 无显式建议时按影响分级兜底
    if impact["impact_level"] == IMPACT_BLOCK:
        return "拆分"  # 关键路径阻断,优先拆分重试
    if impact["impact_level"] == IMPACT_DEGRADE:
        return "跳过"  # 非关键任务可考虑跳过
    return "重排"  # 默认重排


# --------------------------------------------------------------------------- #
# 产物渲染
# --------------------------------------------------------------------------- #
def render_report(tree, failure_info, impact, strategy, round_no):
    """渲染 replan-report.md(人读变更说明)。"""
    root = tree.get("root", {})
    failed = impact["failed_task"] or {}
    lines = []
    lines.append("# 重规划报告 (replan-report)\n")
    lines.append("- 生成时间: %s" % _now_iso())
    lines.append("- 原 task-tree 根: %s" % root.get("title", ""))
    lines.append("- 失败任务: %s (%s)" % (
        failed.get("id", failure_info.get("failed_task_id", "?")),
        failed.get("title", "未找到")))
    lines.append("- 错误码: %s" % failure_info.get("error_code", "-"))
    lines.append("- 错误信息: %s" % failure_info.get("error_message", "-"))
    lines.append("- 调用方建议: %s" % failure_info.get("suggested_action", "-"))
    lines.append("- 重规划轮次: %d / %d" % (round_no, MAX_REPLAN_ROUNDS))
    lines.append("- 影响分级: %s\n" % impact["impact_level"])

    # 影响分析摘要
    lines.append("## 一、影响分析\n")
    lines.append("- 直接受影响任务: %d 个" % len(impact["direct"]))
    lines.append("- 间接受影响任务: %d 个" % len(impact["indirect"]))
    lines.append("- 不受影响任务: %d 个\n" % len(impact["not_affected"]))

    if impact["direct"]:
        lines.append("### 直接影响(第 1 层)\n")
        lines.append("| id | 标题 | 优先级 |")
        lines.append("|----|------|--------|")
        for t in impact["direct"]:
            lines.append("| %s | %s | %s |" % (
                t.get("id", ""), t.get("title", ""), t.get("priority", "")))
        lines.append("")

    if impact["indirect"]:
        lines.append("### 间接影响(传递依赖)\n")
        lines.append("| id | 标题 | 优先级 |")
        lines.append("|----|------|--------|")
        for t in impact["indirect"]:
            lines.append("| %s | %s | %s |" % (
                t.get("id", ""), t.get("title", ""), t.get("priority", "")))
        lines.append("")

    # 策略建议
    lines.append("## 二、策略建议\n")
    lines.append("- 建议策略: **%s**" % strategy)
    lines.append("- 策略说明详见 `references/replan-strategies.md`\n")

    # 变更说明模板(AI 在此填充实际变更)
    lines.append("## 三、变更说明(AI 填充)\n")
    lines.append("> 本节由 AI 在 SKILL.md 引导下,按所选策略对 `task-tree.v2.json` 做实际调整后回填。\n")
    lines.append("- [ ] 调整类型(重排/跳过/拆分/合并/降级/人工接管):")
    lines.append("- [ ] 变更的任务(id 列表):")
    lines.append("- [ ] 变更内容(新增/删除/改依赖/改优先级/改承接 skill):")
    lines.append("- [ ] 回退方案(如何恢复原 task-tree):\n")

    if round_no >= MAX_REPLAN_ROUNDS:
        lines.append("## 四、人工接管提示\n")
        lines.append("- 已达最大重规划轮次(%d 轮),按关键约束转 **人工接管**。" % MAX_REPLAN_ROUNDS)
        lines.append("- 请人工审查失败信息与影响范围,决定是否调整需求范围或换用降级方案。\n")

    lines.append("## 五、产物\n")
    lines.append("- `task-tree.v2.json`:调整后的任务树(符合 task-tree-schema,与 task-planner 产出兼容)")
    lines.append("- `replan-report.md`:本报告")
    lines.append("- 原 `task-tree.json` 保留,可回退\n")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# impact 子命令
# --------------------------------------------------------------------------- #
def cmd_impact(args):
    """impact 子命令:分析失败任务的影响传播,输出受影响任务清单。"""
    in_path = Path(args.input)
    if not in_path.exists():
        sys.stderr.write("输入文件不存在: %s\n" % args.input)
        return 1

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write("JSON 解析失败: %s\n" % exc)
        return 1

    ok, errors = validate_task_tree(data)
    if not ok:
        sys.stderr.write("Schema 校验失败:\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1

    tasks = data.get("tasks", [])
    impact = analyze_impact(tasks, args.task_id)

    if impact["failed_task"] is None:
        sys.stderr.write("失败任务 id 不存在: %s\n" % args.task_id)
        return 1

    failed = impact["failed_task"]
    sys.stdout.write("影响分析结果\n")
    sys.stdout.write("=" * 50 + "\n")
    sys.stdout.write("失败任务: [%s] %s (优先级 %s)\n" % (
        failed.get("id", ""), failed.get("title", ""), failed.get("priority", "")))
    sys.stdout.write("影响分级: %s\n\n" % impact["impact_level"])

    sys.stdout.write("直接影响(第 1 层,共 %d 个):\n" % len(impact["direct"]))
    for t in impact["direct"]:
        sys.stdout.write("  [%s] %s (优先级 %s)\n" % (
            t.get("id", ""), t.get("title", ""), t.get("priority", "")))

    if impact["indirect"]:
        sys.stdout.write("\n间接影响(传递依赖,共 %d 个):\n" % len(impact["indirect"]))
        for t in impact["indirect"]:
            sys.stdout.write("  [%s] %s (优先级 %s)\n" % (
                t.get("id", ""), t.get("title", ""), t.get("priority", "")))

    sys.stdout.write("\n不受影响任务: %d 个\n" % len(impact["not_affected"]))
    sys.stdout.write("受影响任务总数(不含失败任务): %d\n" % len(impact["affected_ids"]))
    return 0


# --------------------------------------------------------------------------- #
# replan 子命令
# --------------------------------------------------------------------------- #
def cmd_replan(args):
    """replan 子命令:重规划,产出 task-tree.v2.json + replan-report.md。"""
    in_path = Path(args.input)
    if not in_path.exists():
        sys.stderr.write("输入文件不存在: %s\n" % args.input)
        return 1

    fail_path = Path(args.failure)
    if not fail_path.exists():
        sys.stderr.write("失败信息文件不存在: %s\n" % args.failure)
        return 1

    try:
        tree = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write("task-tree JSON 解析失败: %s\n" % exc)
        return 1

    try:
        failure_info = json.loads(fail_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write("失败信息 JSON 解析失败: %s\n" % exc)
        return 1

    # 校验
    ok, errors = validate_task_tree(tree)
    if not ok:
        sys.stderr.write("task-tree Schema 校验失败:\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1

    ok, errors = validate_failure_info(failure_info)
    if not ok:
        sys.stderr.write("失败信息校验失败:\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1

    tasks = tree.get("tasks", [])
    failed_id = failure_info["failed_task_id"]

    # 失败任务必须在 task-tree 中存在
    if not any(t.get("id") == failed_id for t in tasks if isinstance(t, dict)):
        sys.stderr.write("failed_task_id 在 task-tree 中不存在: %s\n" % failed_id)
        return 1

    # 影响分析
    impact = analyze_impact(tasks, failed_id)

    # 轮次:从 failure_info 读取(默认 1)
    round_no = int(failure_info.get("round", 1) or 1)

    # 策略建议(框架性)
    strategy = suggest_strategy(failure_info, impact)

    # 达到最大轮次强制人工接管
    if round_no >= MAX_REPLAN_ROUNDS:
        strategy = "人工接管"

    # 产出 task-tree.v2.json(脚手架=原 tree 的副本,实际调整由 AI 完成)
    # 保持 schema 兼容:仅含 version/root/tasks,不额外加字段
    tree_v2 = json.loads(json.dumps(tree))  # 深拷贝

    # 校验 v2 仍符合 schema
    ok, errors = validate_task_tree(tree_v2)
    if not ok:
        sys.stderr.write("task-tree.v2 校验失败:\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1

    out_path = Path(args.output)
    if out_path.suffix == ".json":
        # 输出路径指向具体文件
        tree_v2_path = out_path
        out_dir = out_path.parent
    else:
        out_dir = out_path
        out_dir.mkdir(parents=True, exist_ok=True)
        tree_v2_path = out_dir / "task-tree.v2.json"

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(tree_v2_path, "w", encoding="utf-8") as fh:
        json.dump(tree_v2, fh, ensure_ascii=False, indent=2)

    report_path = out_dir / "replan-report.md"
    report_path.write_text(
        render_report(tree, failure_info, impact, strategy, round_no),
        encoding="utf-8",
    )

    sys.stdout.write("重规划完成:\n")
    sys.stdout.write("  失败任务: %s\n" % failed_id)
    sys.stdout.write("  影响分级: %s\n" % impact["impact_level"])
    sys.stdout.write("  受影响任务: %d 个(直接 %d + 间接 %d)\n" % (
        len(impact["affected_ids"]), len(impact["direct"]), len(impact["indirect"])))
    sys.stdout.write("  建议策略: %s\n" % strategy)
    sys.stdout.write("  重规划轮次: %d / %d\n" % (round_no, MAX_REPLAN_ROUNDS))
    sys.stdout.write("  产物:\n")
    sys.stdout.write("    %s\n" % tree_v2_path)
    sys.stdout.write("    %s\n" % report_path)
    sys.stdout.write("请在 SKILL.md 引导下,按所选策略调整 task-tree.v2.json 并回填报告。\n")
    if round_no >= MAX_REPLAN_ROUNDS:
        sys.stdout.write("注意:已达最大轮次,建议转人工接管。\n")
    return 0


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #
def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="replan.py",
        description="重规划器:当子任务失败或上下文变化时,动态调整 task-tree。"
                    "接收原 task-tree + 失败信息,做影响分析后产出 task-tree.v2.json + replan-report.md。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # replan 子命令
    p_replan = sub.add_parser(
        "replan",
        help="重规划:读取原 task-tree + 失败信息,产出 task-tree.v2.json + replan-report.md",
    )
    p_replan.add_argument("--input", required=True, help="原 task-tree.json 路径")
    p_replan.add_argument("--failure", required=True,
                          help="失败信息 JSON 路径(含 failed_task_id/error_code/error_message/suggested_action)")
    p_replan.add_argument("--output", default=".",
                          help="输出路径(目录或具体 .json 文件),默认当前目录")
    p_replan.set_defaults(func=cmd_replan)

    # impact 子命令
    p_impact = sub.add_parser(
        "impact",
        help="影响分析:读取 task-tree + 失败任务 id,输出受影响任务清单",
    )
    p_impact.add_argument("--input", required=True, help="task-tree.json 路径")
    p_impact.add_argument("--task-id", required=True, help="失败任务 id")
    p_impact.set_defaults(func=cmd_impact)

    return parser


def main():
    """入口函数。"""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
