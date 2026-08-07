#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compile_workflow.py - 工作流编译器脚本。

把编排总纲的执行顺序或 task-planner 的 task-tree.json 编译为可执行的 workflow.yaml。

子命令:
  compile-from-master  从编排总纲 SKILL.md 的执行顺序章节编译为 workflow.yaml
  compile-from-tasktree 从 task-planner 的 task-tree.json 转为 workflow.yaml
  validate             校验 workflow.yaml 是否符合 schema

设计原则(与 validate_runtime.py / plan_tasks.py 一致):
- 失败不抛异常,统一通过退出码与 stderr 表达
- compile-from-master 的解析较复杂,脚本识别基本模式(调用/暂停/并行/回退),
  实际编译由 AI 在 SKILL.md 引导下完成,脚本负责产出框架与格式校验
- PyYAML 可选:缺失时 validate/编译产物输出会降级为提示

退出码:0=成功;1=校验失败;2=参数错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# PyYAML 可选导入
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# ---------- 常量 ----------
SCHEMA_VERSION = "1.0"
STEP_TYPE_ENUM = ("skill", "pause")
ON_FAIL_ACTION_ENUM = ("back_to", "skip", "abort")
DEFAULT_MAX_RETRIES = 3

# 编排总纲执行顺序的模式识别正则
# 章节头:如 "## 七、执行顺序" / "## 八、执行顺序"
RE_SECTION = re.compile(r"^##\s+([七八九十]+|[0-9]+)、?执行顺序")
# 暂停点:"⏸ **人工确认点 N**" 或 "⏸ **人工确认点 N（可选 Tool）**"(数字后可有括号注解)
RE_PAUSE = re.compile(r"⏸\s*\*\*人工确认点\s*(\d+)[^*]*\*\*")
# 调用 skill:"调用 `xxx`"  (可能多个,如 "调用 `game-asset-forge` 和 `game-code-forge`")
RE_SKILL = re.compile(r"调用\s+`([^`]+)`")
# 并行同伴 skill:"和 `xxx`" / "与 `xxx`"(并行行中跟在首个 skill 后的同伴)
RE_COMPANION = re.compile(r"(?:和|与)\s*`([^`]+)`")
# 产出:"产出 `docs/xxx.md`"
RE_OUTPUTS = re.compile(r"产出\s+`([^`]+)`")
# 并行:"**并行**调用"
RE_PARALLEL = re.compile(r"\*\*并行\*\*\s*调用")
# 回退:"FAIL 则回 N 修复"
RE_BACK_TO = re.compile(r"FAIL\s*则\s*回\s*(\d+)")
# 可选标记:"(可选)" / "（可选）" / "（可选 Tool）"(可选后可跟说明)
RE_OPTIONAL = re.compile(r"[（(]可选[^）)]*[）)]")


def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_yaml():
    """检查 PyYAML 是否可用,不可用时返回错误字符串。"""
    if yaml is None:
        return "PyYAML 未安装,无法解析/输出 YAML。请执行:python -m pip install pyyaml"
    return None


def _is_nonempty_string(value):
    return isinstance(value, str) and len(value) > 0


def _is_nonneg_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# --------------------------------------------------------------------------- #
# Schema 校验
# --------------------------------------------------------------------------- #
def validate_workflow(data):
    """校验 workflow.yaml dict 是否符合 schema。

    返回 (ok: bool, errors: list[str])。
    """
    errors = []

    if not isinstance(data, dict):
        return False, ["顶层必须是对象"]

    # 未知字段检测
    known_top = {"name", "source", "version", "steps"}
    unknown_top = set(data.keys()) - known_top
    if unknown_top:
        errors.append("顶层含未知字段:%s" % sorted(unknown_top))

    # name 必填
    if not _is_nonempty_string(data.get("name")):
        errors.append("name:必填且为非空字符串")

    # steps 必填
    steps = data.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        errors.append("steps:必填且为非空数组")
        return len(errors) == 0, errors

    # 收集所有 id
    ids = set()
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append("steps[%d]:必须是对象" % idx)
            continue
        sid = step.get("id")
        if not _is_nonempty_string(sid):
            errors.append("steps[%d].id:必填且为非空字符串" % idx)
        elif sid in ids:
            errors.append("steps[%d].id:重复 %s" % (idx, sid))
        else:
            ids.add(sid)

    # 第二轮:字段类型与引用校验
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        sid = step.get("id", "<?>")
        stype = step.get("type", "skill")
        if stype not in STEP_TYPE_ENUM:
            errors.append("steps[%d].%s.type:必须为 %s" % (idx, sid, "/".join(STEP_TYPE_ENUM)))

        # step 级未知字段检测
        known_step_fields = {"id", "type", "skill", "args", "outputs", "on_fail", "next",
                             "parallel_with", "runtime", "confirm", "optional", "title"}
        unknown_step = set(step.keys()) - known_step_fields
        if unknown_step:
            errors.append("steps[%d].%s:含未知字段:%s" % (idx, sid, sorted(unknown_step)))

        # 可选字段类型校验
        if "args" in step and not isinstance(step["args"], dict):
            errors.append("steps[%d].%s.args:必须为对象" % (idx, sid))
        if "outputs" in step and not isinstance(step["outputs"], list):
            errors.append("steps[%d].%s.outputs:必须为数组" % (idx, sid))
        if "runtime" in step and not (step["runtime"] is None or isinstance(step["runtime"], str)):
            errors.append("steps[%d].%s.runtime:必须为字符串或 null" % (idx, sid))
        if "optional" in step and not isinstance(step["optional"], bool):
            errors.append("steps[%d].%s.optional:必须为布尔值" % (idx, sid))
        if "title" in step and not (step["title"] is None or isinstance(step["title"], str)):
            errors.append("steps[%d].%s.title:必须为字符串或 null" % (idx, sid))

        # type=skill 时 skill 必填
        if stype == "skill":
            if not _is_nonempty_string(step.get("skill")):
                errors.append("steps[%d].%s:type=skill 时 skill 必填" % (idx, sid))

        # type=pause 时 confirm 必填
        if stype == "pause":
            # pause 与 skill/args/outputs 互斥(暂停点不应声明执行类字段)
            for mutex_field in ("skill", "args", "outputs"):
                if mutex_field in step:
                    errors.append("steps[%d].%s:type=pause 时不应声明 %s" % (idx, sid, mutex_field))
            confirm = step.get("confirm")
            if not isinstance(confirm, dict):
                errors.append("steps[%d].%s:type=pause 时 confirm 必填且为对象" % (idx, sid))
            else:
                if not _is_nonempty_string(confirm.get("question")):
                    errors.append("steps[%d].%s.confirm.question:必填" % (idx, sid))
                opts = confirm.get("options")
                if not isinstance(opts, list) or len(opts) < 2:
                    errors.append("steps[%d].%s.confirm.options:至少 2 项" % (idx, sid))
                else:
                    for oi, opt in enumerate(opts):
                        if not isinstance(opt, dict):
                            errors.append("steps[%d].%s.confirm.options[%d]:必须是对象" % (idx, sid, oi))
                            continue
                        if not _is_nonempty_string(opt.get("label")):
                            errors.append("steps[%d].%s.confirm.options[%d].label:必填" % (idx, sid, oi))
                        if not _is_nonempty_string(opt.get("next")):
                            errors.append("steps[%d].%s.confirm.options[%d].next:必填" % (idx, sid, oi))

        # on_fail 校验
        on_fail = step.get("on_fail")
        if on_fail is not None:
            if not isinstance(on_fail, dict):
                errors.append("steps[%d].%s.on_fail:必须是对象" % (idx, sid))
            else:
                action = on_fail.get("action", "abort")
                if action not in ON_FAIL_ACTION_ENUM:
                    errors.append("steps[%d].%s.on_fail.action:必须为 %s" % (idx, sid, "/".join(ON_FAIL_ACTION_ENUM)))
                if action == "back_to":
                    target = on_fail.get("target")
                    if not _is_nonempty_string(target):
                        errors.append("steps[%d].%s.on_fail.target:action=back_to 时必填" % (idx, sid))
                    elif target not in ids:
                        errors.append("steps[%d].%s.on_fail.target:引用了不存在的 step id %s" % (idx, sid, target))
                if "max_retries" in on_fail and not _is_nonneg_int(on_fail["max_retries"]):
                    errors.append("steps[%d].%s.on_fail.max_retries:必须为非负整数" % (idx, sid))

        # next 引用校验
        nxt = step.get("next")
        if nxt is not None and _is_nonempty_string(nxt) and nxt != "__end__":
            if nxt not in ids:
                errors.append("steps[%d].%s.next:引用了不存在的 step id %s" % (idx, sid, nxt))

        # parallel_with 引用校验
        pw = step.get("parallel_with")
        if pw is not None and _is_nonempty_string(pw):
            if pw not in ids:
                errors.append("steps[%d].%s.parallel_with:引用了不存在的 step id %s" % (idx, sid, pw))

    # parallel_with 双向声明校验
    id_to_step = {s.get("id"): s for s in steps if isinstance(s, dict)}
    for sid, step in id_to_step.items():
        pw = step.get("parallel_with")
        if _is_nonempty_string(pw) and pw in id_to_step:
            peer = id_to_step[pw]
            if peer.get("parallel_with") != sid:
                errors.append("steps.%s.parallel_with=%s 但对端未反向声明" % (sid, pw))

    return len(errors) == 0, errors


# --------------------------------------------------------------------------- #
# compile-from-master:从编排总纲 SKILL.md 编译
# --------------------------------------------------------------------------- #
def _extract_section(text, section_name):
    """从 SKILL.md 文本中提取指定章节的内容。

    section_name 可为章节号(如 "七"/"八"或 "§七"/"§八")或标题片段(如 "执行顺序"/"编排阶段")。
    自动去除 § 前缀后匹配。
    优先匹配含"执行顺序"的标题(如 game-forge-master/product-pipeline-master);
    若未找到,回退到匹配任何含 normalized 的二级标题(如 build-working-system 的"编排阶段")。
    返回该章节正文(到下一个 ## 二级标题为止),未找到返回 None。
    """
    # 规范化：去除 § 前缀
    normalized = section_name
    if normalized.startswith("§"):
        normalized = normalized[1:]

    lines = text.splitlines()
    start = None
    # 第一轮：优先匹配含"执行顺序"的标题
    for i, line in enumerate(lines):
        if re.match(r"^##\s+", line) and ("执行顺序" in line):
            if normalized in line or normalized == "执行顺序":
                start = i
                break
    # 第二轮回退：匹配任何含 normalized 的二级标题
    if start is None:
        for i, line in enumerate(lines):
            if re.match(r"^##\s+", line) and normalized in line:
                start = i
                break
    if start is None:
        return None

    end = len(lines)
    for j in range(start + 1, len(lines)):
        # 遇到下一个二级标题则结束
        if re.match(r"^##\s+", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


def _parse_pause_options(text):
    """从暂停点文本中提取 AskUserQuestion 选项。

    总纲常见格式:"询问"进入规格设计 / 回退修改蓝图 / 终止流水线""
    返回 [(label, next_hint), ...],next_hint 为选项文案(后续由 AI 绑定具体 step id)。
    """
    # 提取引号内文本
    m = re.search(r'[询问]+["""]([^"""]+)["""]', text)
    if not m:
        return []
    raw = m.group(1)
    parts = [p.strip() for p in re.split(r"[/／]", raw) if p.strip()]
    return parts


def compile_from_master(master_path, section_name, source_label):
    """从编排总纲 SKILL.md 的执行顺序章节编译为 workflow.yaml dict。

    识别以下模式:
      - "调用 `xxx`"           → skill step
      - "⏸ **人工确认点 N**"   → pause step
      - "**并行**调用"          → parallel_with
      - "FAIL 则回 N 修复"     → on_fail.back_to
      - "产出 `path`"          → outputs

    返回 (workflow_dict, warnings)。
    实际 step id 绑定与 confirm.next 由 AI 在 SKILL.md 引导下精调。
    """
    warnings = []
    text = master_path.read_text(encoding="utf-8")
    section = _extract_section(text, section_name)
    if section is None:
        return None, ["未找到执行顺序章节(含关键词'执行顺序'的二级标题)"]

    steps = []
    # 用于记录阶段号 → step id 映射(back_to 引用)
    stage_id_map = {}
    pause_counter = 0
    step_counter = 0
    parallel_buffer = []  # 暂存并行步骤,后续绑定 parallel_with

    for line in section.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 识别阶段号(行首数字. 或 "0. " / "1. " 等)
        stage_match = re.match(r"^(\d+)\.\s", line_stripped)

        # 暂停点
        if RE_PAUSE.search(line_stripped):
            pause_counter += 1
            pid = "pause%d" % pause_counter
            opt_labels = _parse_pause_options(line_stripped)
            options = []
            for label in opt_labels:
                # next 暂留占位,由 AI 绑定实际 step id
                options.append({"label": label, "next": "__TODO__"})
            if len(options) < 2:
                options = [
                    {"label": "进入下一阶段", "next": "__TODO__"},
                    {"label": "回退修改", "next": "__TODO__"},
                    {"label": "终止流水线", "next": "__end__"},
                ]
            else:
                # 最后一个选项默认为终止
                options[-1]["next"] = "__end__"
            steps.append({
                "id": pid,
                "type": "pause",
                "title": "人工确认点 %d" % pause_counter,
                "confirm": {
                    "question": RE_PAUSE.search(line_stripped).group(0)
                    .replace("⏸ ", "").replace("**", "").strip(),
                    "options": options,
                },
            })
            continue

        # 调用 skill(可能并行)
        skills_found = RE_SKILL.findall(line_stripped)
        if not skills_found:
            continue

        is_parallel = bool(RE_PARALLEL.search(line_stripped))
        is_optional = bool(RE_OPTIONAL.search(line_stripped))
        outputs_found = RE_OUTPUTS.findall(line_stripped)
        # 并行行中"和 `path`"模式的补充识别(如 "分别产出 `assets/` 和 `src/`")
        # 仅识别像路径的产物(含 / 或 .),避免把同伴 skill 名误当产物路径
        if is_parallel:
            extra_outputs = re.findall(r"和\s*`([^`]+)`", line_stripped)
            for extra in extra_outputs:
                looks_like_path = "/" in extra or "." in extra
                if looks_like_path and extra not in outputs_found:
                    outputs_found.append(extra)
        back_match = RE_BACK_TO.search(line_stripped)

        # 并行行中追加同伴 skill("和 `xxx`" / "与 `xxx`"),去重
        if is_parallel:
            for comp in RE_COMPANION.findall(line_stripped):
                if comp not in skills_found and "/" not in comp:
                    skills_found.append(comp)

        new_step_ids = []
        for skill_name in skills_found:
            step_counter += 1
            sid = "s%d-%s" % (step_counter, skill_name.replace("-", "_"))
            step = {
                "id": sid,
                "type": "skill",
                "title": "调用 %s" % skill_name,
                "skill": skill_name,
            }
            if outputs_found:
                step["outputs"] = list(outputs_found)
            # on_fail
            if back_match:
                step["on_fail"] = {
                    "action": "back_to",
                    "target": "__TODO_stage_%s__" % back_match.group(1),
                    "max_retries": DEFAULT_MAX_RETRIES,
                }
            elif is_optional:
                step["on_fail"] = {"action": "skip"}
            else:
                step["on_fail"] = {"action": "abort"}
            steps.append(step)
            new_step_ids.append(sid)
            if stage_match:
                stage_id_map[stage_match.group(1)] = sid

        # 并行绑定:同行的多个 skill 互写 parallel_with
        if is_parallel and len(new_step_ids) >= 2:
            for i, sid in enumerate(new_step_ids):
                others = [new_step_ids[j] for j in range(len(new_step_ids)) if j != i]
                # parallel_with 只接受单个 id,取第一个伙伴
                for s in steps:
                    if s["id"] == sid:
                        s["parallel_with"] = others[0]
                        break

    if not steps:
        return None, ["未从执行顺序章节识别到任何 skill 调用或暂停点"]

    # 补全 next:无显式 next 的 step 按数组顺序指向下一个
    for i, step in enumerate(steps):
        if "next" not in step:
            if i + 1 < len(steps):
                step["next"] = steps[i + 1]["id"]
            else:
                step["next"] = "__end__"

    workflow = {
        "name": "compiled-from-master",
        "source": source_label or str(master_path.name),
        "version": SCHEMA_VERSION,
        "steps": steps,
    }
    warnings.append("compile-from-master 识别基本模式,confirm.next 与 back_to.target 标 __TODO__ 由 AI 绑定")
    return workflow, warnings


def _dump_yaml(workflow, output_path):
    """把 workflow dict 写为 YAML 文件。"""
    if yaml is None:
        return False
    # 自定义排序以保持字段顺序可读
    with open(output_path, "w", encoding="utf-8") as fh:
        yaml.dump(
            workflow, fh,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
        )
    return True


def _dump_yaml_fallback(workflow, output_path):
    """无 PyYAML 时的简易 YAML 输出(仅支持本 skill 使用的结构)。"""
    lines = []
    lines.append("name: %s" % workflow.get("name", ""))
    lines.append("source: %s" % (workflow.get("source") or ""))
    lines.append('version: "%s"' % workflow.get("version", SCHEMA_VERSION))
    lines.append("steps:")
    for step in workflow.get("steps", []):
        lines.append("  - id: %s" % step.get("id", ""))
        if "type" in step:
            lines.append("    type: %s" % step["type"])
        if "title" in step:
            lines.append("    title: %s" % step["title"])
        if "skill" in step:
            lines.append("    skill: %s" % step["skill"])
        if "outputs" in step:
            lines.append("    outputs:")
            for o in step["outputs"]:
                lines.append("      - %s" % o)
        if "on_fail" in step:
            of = step["on_fail"]
            lines.append("    on_fail:")
            lines.append("      action: %s" % of.get("action", "abort"))
            if "target" in of:
                lines.append("      target: %s" % of["target"])
            if "max_retries" in of:
                lines.append("      max_retries: %d" % of["max_retries"])
        if "next" in step:
            lines.append("    next: %s" % step["next"])
        if "parallel_with" in step:
            lines.append("    parallel_with: %s" % step["parallel_with"])
        if "confirm" in step:
            cf = step["confirm"]
            lines.append("    confirm:")
            lines.append("      question: %s" % cf.get("question", ""))
            lines.append("      options:")
            for opt in cf.get("options", []):
                lines.append("        - label: %s" % opt.get("label", ""))
                lines.append("          next: %s" % opt.get("next", ""))
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return True


# --------------------------------------------------------------------------- #
# compile-from-tasktree:从 task-tree.json 转换
# --------------------------------------------------------------------------- #
def compile_from_tasktree(task_tree):
    """把 task-planner 的 task-tree.json 转为 workflow dict。

    转换规则:
      - 每个 task → 一个 skill step(id 用 task.id,skill 用 assigned_skill)
      - depends_on → 串行依赖(前置 step 的 next 指向当前)
      - parallel_with → step.parallel_with(双向)
      - 无 depends_on 的同层 task 可并行
    """
    warnings = []
    tasks = task_tree.get("tasks", [])
    if not tasks:
        return None, ["task-tree.tasks 为空"]

    steps = []
    id_to_step = {}
    # 第一遍:建 step
    for task in tasks:
        tid = task.get("id")
        skill = task.get("assigned_skill")
        step = {
            "id": tid,
            "type": "skill",
            "title": task.get("title", tid),
            "skill": skill if skill else "__TODO_assign_skill__",
            "on_fail": {"action": "abort"},
        }
        steps.append(step)
        id_to_step[tid] = step

    # 第二遍:依赖 → next
    # 若 B depends_on A,则 A.next 指向 B(若 A 无多个后继)
    dependents = {tid: [] for tid in id_to_step}
    for task in tasks:
        tid = task.get("id")
        for dep in task.get("depends_on", []) or []:
            if dep in dependents:
                dependents[dep].append(tid)

    for tid, step in id_to_step.items():
        succs = dependents.get(tid, [])
        if len(succs) == 1:
            step["next"] = succs[0]
        # 多后继时不设单一 next(由并行或 AI 绑定)

    # parallel_with 双向绑定
    for task in tasks:
        tid = task.get("id")
        pw_list = task.get("parallel_with", []) or []
        if pw_list:
            step = id_to_step.get(tid)
            if step and pw_list[0] in id_to_step:
                step["parallel_with"] = pw_list[0]
                # 双向
                peer = id_to_step[pw_list[0]]
                if "parallel_with" not in peer:
                    peer["parallel_with"] = tid

    # 末端 step 的 next 默认 __end__
    for step in steps:
        if "next" not in step and "parallel_with" not in step:
            step["next"] = "__end__"

    workflow = {
        "name": task_tree.get("root", {}).get("title", "compiled-from-tasktree"),
        "source": "task-planner task-tree.json",
        "version": SCHEMA_VERSION,
        "steps": steps,
    }
    warnings.append("compile-from-tasktree 转换依赖为 next,多后继情况由 AI 精调")
    return workflow, warnings


# --------------------------------------------------------------------------- #
# 子命令实现
# --------------------------------------------------------------------------- #
def cmd_compile_from_master(args):
    """compile-from-master 子命令。"""
    master_path = Path(args.master)
    if not master_path.exists():
        sys.stderr.write("总纲 SKILL.md 不存在: %s\n" % args.master)
        return 1

    workflow, warnings = compile_from_master(
        master_path, args.section, args.source
    )
    if workflow is None:
        sys.stderr.write("编译失败:\n")
        for w in warnings:
            sys.stderr.write("  - %s\n" % w)
        return 1

    # 编译后立即校验(允许 __TODO__ 占位通过 next/target 存在性检查的特殊处理)
    ok, errors = validate_workflow(workflow)
    if not ok:
        sys.stderr.write("编译产物校验失败(占位 __TODO__ 需 AI 绑定):\n")
        for e in errors:
            sys.stderr.write("  - %s\n" % e)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        _dump_yaml(workflow, output_path)
    else:
        _dump_yaml_fallback(workflow, output_path)

    sys.stdout.write("已编译 workflow.yaml: %s\n" % output_path)
    for w in warnings:
        sys.stdout.write("  提示: %s\n" % w)
    sys.stdout.write("请在 SKILL.md 引导下绑定 __TODO__ 占位(confirm.next / back_to.target)。\n")
    return 0


def cmd_compile_from_tasktree(args):
    """compile-from-tasktree 子命令。"""
    in_path = Path(args.input)
    if not in_path.exists():
        sys.stderr.write("task-tree.json 不存在: %s\n" % args.input)
        return 1

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write("JSON 解析失败: %s\n" % exc)
        return 1

    workflow, warnings = compile_from_tasktree(data)
    if workflow is None:
        sys.stderr.write("转换失败:\n")
        for w in warnings:
            sys.stderr.write("  - %s\n" % w)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if yaml is not None:
        _dump_yaml(workflow, output_path)
    else:
        _dump_yaml_fallback(workflow, output_path)

    sys.stdout.write("已转换 workflow.yaml: %s\n" % output_path)
    for w in warnings:
        sys.stdout.write("  提示: %s\n" % w)
    return 0


def cmd_validate(args):
    """validate 子命令:校验 workflow.yaml。"""
    yaml_err = _ensure_yaml()
    if yaml_err is not None:
        sys.stderr.write(yaml_err + "\n")
        return 1

    in_path = Path(args.input)
    if not in_path.exists():
        sys.stderr.write("workflow.yaml 不存在: %s\n" % args.input)
        return 1

    try:
        data = yaml.safe_load(in_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.stderr.write("YAML 解析失败: %s\n" % exc)
        return 1

    if data is None:
        data = {}

    ok, errors = validate_workflow(data)
    if ok:
        sys.stdout.write("PASS  %s 符合 workflow.yaml schema\n" % args.input)
        sys.stdout.write("  steps 数量: %d\n" % len(data.get("steps", [])))
        return 0
    else:
        sys.stderr.write("FAIL  %s 校验失败:\n" % args.input)
        for e in errors:
            sys.stderr.write("  - %s\n" % e)
        return 1


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #
def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="compile_workflow.py",
        description="工作流编译器:把编排总纲执行顺序或 task-tree.json 编译为 workflow.yaml。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python compile_workflow.py compile-from-master --master game-forge-master/SKILL.md --section 七 --output workflow.yaml\n"
            "  python compile_workflow.py compile-from-tasktree --input task-tree.json --output workflow.yaml\n"
            "  python compile_workflow.py validate --input workflow.yaml\n"
            "\n退出码:0=成功;1=校验失败;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # compile-from-master
    p_master = sub.add_parser(
        "compile-from-master",
        help="从编排总纲 SKILL.md 的执行顺序章节编译为 workflow.yaml",
    )
    p_master.add_argument("--master", required=True, help="总纲 SKILL.md 路径")
    p_master.add_argument("--section", required=True, help="章节名或号(如 七 / 八 / 执行顺序)")
    p_master.add_argument("--source", default=None, help="来源说明(如 'game-forge-master §七')")
    p_master.add_argument("--output", required=True, help="workflow.yaml 输出路径")
    p_master.set_defaults(func=cmd_compile_from_master)

    # compile-from-tasktree
    p_tree = sub.add_parser(
        "compile-from-tasktree",
        help="从 task-planner 的 task-tree.json 转为 workflow.yaml",
    )
    p_tree.add_argument("--input", required=True, help="task-tree.json 路径")
    p_tree.add_argument("--output", required=True, help="workflow.yaml 输出路径")
    p_tree.set_defaults(func=cmd_compile_from_tasktree)

    # validate
    p_val = sub.add_parser(
        "validate",
        help="校验 workflow.yaml 是否符合 schema",
    )
    p_val.add_argument("--input", required=True, help="workflow.yaml 路径")
    p_val.set_defaults(func=cmd_validate)

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
