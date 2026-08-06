#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_tasks.py - 通用任务规划器脚本。

提供两个子命令:
  plan      接收需求文本,生成 task-tree.json 脚手架 + task-plan.md。
            实际拆解由 AI 在 SKILL.md 引导下完成,脚本负责提供框架与格式校验。
  topology  读取 task-tree.json,校验 Schema/引用完整性/依赖无环,
            输出分层拓扑执行顺序(同层可并行)。

退出码:0=成功;1=校验失败;2=参数错误。
"""

import argparse
import json
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

# 常量
SCHEMA_VERSION = "1.0"
VALID_PRIORITIES = ("P0", "P1", "P2")
VALID_COMPLEXITIES_ROOT = ("low", "medium", "high")
VALID_EST_COMPLEXITIES = ("★", "★★", "★★★", "★★★★", "★★★★★")


def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Schema 校验
# --------------------------------------------------------------------------- #
def validate_task_tree(data):
    """校验 task-tree 字典是否符合 Schema。

    返回 (ok: bool, errors: list[str])。
    """
    errors = []

    if not isinstance(data, dict):
        return False, ["顶层必须是对象"]

    # version
    if data.get("version") != SCHEMA_VERSION:
        errors.append("version 必须为 %r,实际 %r" % (SCHEMA_VERSION, data.get("version")))

    # root
    root = data.get("root")
    if not isinstance(root, dict):
        errors.append("root 必须是对象")
    else:
        for field in ("id", "title", "complexity"):
            if not root.get(field):
                errors.append("root.%s 缺失" % field)
        if root.get("complexity") and root.get("complexity") not in VALID_COMPLEXITIES_ROOT:
            errors.append("root.complexity 必须为 %s" % "/".join(VALID_COMPLEXITIES_ROOT))

    # tasks
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks 必须是数组")
        return len(errors) == 0, errors

    ids = set()
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append("tasks[%d] 必须是对象" % idx)
            continue
        # 必填字段
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
        # 数组字段类型
        for arr_field in ("depends_on", "parallel_with"):
            val = task.get(arr_field)
            if val is not None and not isinstance(val, list):
                errors.append("tasks[%d].%s 必须为数组" % (idx, arr_field))

    # 引用完整性:depends_on / parallel_with 指向的 id 必须存在
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        for arr_field in ("depends_on", "parallel_with"):
            for ref in task.get(arr_field, []) or []:
                if ref not in ids:
                    errors.append("tasks[%d].%s 引用了不存在的 id:%s" % (idx, arr_field, ref))

    return len(errors) == 0, errors


# --------------------------------------------------------------------------- #
# 拓扑排序(Kahn 算法,带环检测与分层)
# --------------------------------------------------------------------------- #
def topological_sort(tasks):
    """对 tasks 做拓扑排序。

    返回 (layers: list[list[str]], cycles: list[str])。
    layers 为分层执行顺序(同层可并行);cycles 为参与环的 task id 列表(无环时为空)。
    """
    # 构建邻接表与入度
    graph = {t["id"]: [] for t in tasks}
    indegree = {t["id"]: 0 for t in tasks}
    id_set = set(graph.keys())

    for t in tasks:
        for dep in t.get("depends_on", []) or []:
            if dep in id_set:
                graph[dep].append(t["id"])
                indegree[t["id"]] += 1

    # Kahn 算法分层
    layers = []
    queue = deque([tid for tid, d in indegree.items() if d == 0])
    visited = 0
    while queue:
        layer = sorted(queue)  # 排序保证稳定输出
        layers.append(layer)
        next_queue = deque()
        for tid in layer:
            visited += 1
            for nxt in graph[tid]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    next_queue.append(nxt)
        queue = next_queue

    # 环检测:未访问完即有环
    cycles = [tid for tid, d in indegree.items() if d > 0]
    if visited < len(tasks):
        return layers, cycles
    return layers, []


# --------------------------------------------------------------------------- #
# plan 子命令
# --------------------------------------------------------------------------- #
def build_scaffold(requirement, context_text=None):
    """基于需求文本生成 task-tree.json 脚手架。

    实际拆解由 AI 在 SKILL.md 引导下完成;脚本只提供根节点与空 tasks 占位。
    """
    complexity = "medium"
    req_lower = requirement.lower() if isinstance(requirement, str) else ""
    if any(k in requirement for k in ("简单", "单页", "单一", "修复", "small", "simple")):
        complexity = "low"
    elif any(k in requirement for k in ("复杂", "全栈", "多模块", "系统", "复杂", "large", "complex")):
        complexity = "high"

    tree = {
        "version": SCHEMA_VERSION,
        "root": {
            "id": "ROOT",
            "title": requirement.strip().splitlines()[0][:120] if requirement.strip() else "未命名需求",
            "complexity": complexity,
        },
        "tasks": [],
    }
    return tree


def render_plan_md(tree, context_text=None):
    """把 task-tree 渲染为 task-plan.md(人读 Markdown)。"""
    root = tree.get("root", {})
    tasks = tree.get("tasks", [])
    lines = []
    lines.append("# 任务规划: %s\n" % root.get("title", ""))
    lines.append("- 整体复杂度: %s" % root.get("complexity", ""))
    lines.append("- 生成时间: %s" % _now_iso())
    lines.append("- task 数量: %d\n" % len(tasks))

    if context_text:
        lines.append("## 上下文\n")
        lines.append(context_text.strip() + "\n")

    lines.append("## 任务清单\n")
    lines.append("| id | 标题 | 优先级 | 依赖 | 并行 | 承接 skill | 复杂度 | 耗时 |")
    lines.append("|----|------|--------|------|------|-----------|--------|------|")
    for t in tasks:
        deps = ",".join(t.get("depends_on", []) or [])
        par = ",".join(t.get("parallel_with", []) or [])
        skill = t.get("assigned_skill") or "-"
        dur = t.get("est_duration") or "-"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            t.get("id", ""), t.get("title", ""), t.get("priority", ""),
            deps, par, skill, t.get("est_complexity", ""), dur,
        ))

    lines.append("\n## 执行顺序\n")
    lines.append("> 运行 `topology --input task-tree.json` 生成分层执行顺序。\n")
    return "\n".join(lines) + "\n"


def cmd_plan(args):
    """plan 子命令:生成 task-tree.json 脚手架 + task-plan.md。"""
    requirement = args.requirement
    context_text = None
    if args.context:
        ctx_path = Path(args.context)
        if not ctx_path.exists():
            sys.stderr.write("context 文件不存在: %s\n" % args.context)
            return 1
        context_text = ctx_path.read_text(encoding="utf-8")

    tree = build_scaffold(requirement, context_text)

    # 即使是脚手架也校验基本结构
    ok, errors = validate_task_tree(tree)
    if not ok:
        sys.stderr.write("脚手架校验失败:\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    tree_path = out_dir / "task-tree.json"
    with open(tree_path, "w", encoding="utf-8") as fh:
        json.dump(tree, fh, ensure_ascii=False, indent=2)

    plan_path = out_dir / "task-plan.md"
    plan_path.write_text(render_plan_md(tree, context_text), encoding="utf-8")

    sys.stdout.write("已生成脚手架:\n")
    sys.stdout.write("  %s\n" % tree_path)
    sys.stdout.write("  %s\n" % plan_path)
    sys.stdout.write("请在 SKILL.md 引导下填充 tasks 数组(实际拆解),再运行 topology 校验。\n")
    return 0


# --------------------------------------------------------------------------- #
# topology 子命令
# --------------------------------------------------------------------------- #
def cmd_topology(args):
    """topology 子命令:校验 + 拓扑排序 + 输出执行顺序。"""
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
    if not tasks:
        sys.stdout.write("tasks 为空,无可排序任务。\n")
        return 0

    layers, cycles = topological_sort(tasks)
    if cycles:
        sys.stderr.write("存在依赖环,涉及任务: %s\n" % ", ".join(cycles))
        sys.stderr.write("请拆出公共前置任务打破环,见 references/dependency-rules.md。\n")
        return 1

    # 输出分层执行顺序
    task_map = {t["id"]: t for t in tasks}
    sys.stdout.write("拓扑执行顺序(同层可并行):\n\n")
    for i, layer in enumerate(layers, 1):
        sys.stdout.write("第 %d 层:\n" % i)
        for tid in layer:
            t = task_map[tid]
            sys.stdout.write("  [%s] %s (优先级 %s, %s)\n" % (
                tid, t.get("title", ""), t.get("priority", ""), t.get("est_complexity", ""),
            ))
        sys.stdout.write("\n")

    sys.stdout.write("共 %d 层,%d 个任务,无环。\n" % (len(layers), len(tasks)))
    return 0


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #
def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="plan_tasks.py",
        description="通用任务规划器:拆解需求为子任务树+依赖+优先级,产出 task-tree.json。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # plan 子命令
    p_plan = sub.add_parser("plan", help="接收需求,生成 task-tree.json 脚手架 + task-plan.md")
    p_plan.add_argument("--requirement", required=True, help="需求描述文本")
    p_plan.add_argument("--context", default=None, help="可选上下文文件路径")
    p_plan.add_argument("--output", default=".", help="输出目录,默认当前目录")
    p_plan.set_defaults(func=cmd_plan)

    # topology 子命令
    p_topo = sub.add_parser("topology", help="校验 task-tree.json 并输出拓扑执行顺序")
    p_topo.add_argument("--input", required=True, help="task-tree.json 路径")
    p_topo.set_defaults(func=cmd_topology)

    return parser


def main():
    """入口函数。"""
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
