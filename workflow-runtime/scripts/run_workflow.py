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
import os
import subprocess
import sys
import time
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

# skills 工作台根目录(用于定位 track_usage.py / casebook_ops.py)
_SKILLS_ROOT = Path(__file__).resolve().parents[2]
_TRACK_USAGE_PY = _SKILLS_ROOT / "skill-usage-tracker" / "scripts" / "track_usage.py"
_CASEBOOK_PY = _SKILLS_ROOT / "failure-casebook" / "scripts" / "casebook_ops.py"

# external_overrides 默认查找路径(不依赖每个 skill 单独声明)
_DEFAULT_OVERRIDES_PATHS = [
    Path.home() / ".trae-cn" / "tuner-overrides" / "runtime-overrides.yaml",
]


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


# --------------------------------------------------------------------------- #
# runtime.yaml 读取与 external_overrides 合并
# --------------------------------------------------------------------------- #
def load_runtime_yaml(runtime_ref, workflow_dir):
    """读取 step.runtime 引用的 runtime.yaml，返回 (runtime_dict, warnings)。

    runtime_ref 是相对 workflow.yaml 所在目录的路径。
    若文件不存在或解析失败，返回 ({}, [warning])。
    """
    warnings = []
    if not runtime_ref:
        return {}, []

    runtime_path = Path(workflow_dir) / runtime_ref
    if not runtime_path.exists():
        warnings.append("runtime.yaml 不存在: %s" % runtime_ref)
        return {}, warnings

    yaml_err = _ensure_yaml()
    if yaml_err is not None:
        warnings.append(yaml_err)
        return {}, warnings

    try:
        data = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        warnings.append("runtime.yaml 解析失败: %s" % exc)
        return {}, warnings

    if data is None:
        data = {}
    if not isinstance(data, dict):
        warnings.append("runtime.yaml 顶层非 object: %s" % type(data).__name__)
        return {}, warnings

    return data, warnings


def merge_external_overrides(local_runtime, overrides_path, skill_name):
    """合并 external_overrides 引用的 overrides 文件。

    overrides_path 是已解析的绝对路径(由 resolve_runtime_params 传入)。
    支持 list 格式(adaptive-tuner 产出,每项含 skill 字段)和 dict 格式(旧式,以 skill 名为 key)。
    用其 timeout/retry 覆盖本地值,不覆盖 inputs/outputs/degrade。

    返回 (merged_runtime, warnings)。
    """
    warnings = []
    if not overrides_path or not overrides_path.exists():
        return local_runtime, warnings

    yaml_err = _ensure_yaml()
    if yaml_err is not None:
        warnings.append(yaml_err)
        return local_runtime, warnings

    try:
        overrides_data = yaml.safe_load(overrides_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        warnings.append("overrides 文件解析失败: %s" % exc)
        return local_runtime, warnings

    if not isinstance(overrides_data, dict):
        warnings.append("overrides 文件顶层非 object")
        return local_runtime, warnings

    overrides_field = overrides_data.get("overrides", [])
    # 支持 list 格式(adaptive-tuner 产出)和 dict 格式(旧式)
    skill_overrides = None
    if isinstance(overrides_field, list):
        for idx, item in enumerate(overrides_field):
            if isinstance(item, dict):
                if "skill" not in item:
                    warnings.append("overrides 列表第 %d 项缺少 skill 字段,已跳过" % idx)
                    continue
                if item.get("skill") == skill_name:
                    skill_overrides = item
                    break
            else:
                warnings.append("overrides 列表第 %d 项非 object,已跳过" % idx)
    elif isinstance(overrides_field, dict):
        skill_overrides = overrides_field.get(skill_name)
    else:
        warnings.append("overrides 字段非 array/object: %s" % type(overrides_field).__name__)
        return local_runtime, warnings

    if not skill_overrides:
        # 当前 skill 无 overrides，用本地值
        return local_runtime, warnings

    if not isinstance(skill_overrides, dict):
        warnings.append("skill %s 的 overrides 非 object" % skill_name)
        return local_runtime, warnings

    # 合并：仅覆盖 timeout 和 retry，不覆盖 inputs/outputs/degrade
    merged = dict(local_runtime)  # 浅拷贝
    if "timeout" in skill_overrides:
        local_type = type(local_runtime.get("timeout")).__name__
        override_type = type(skill_overrides["timeout"]).__name__
        if local_type == override_type or local_runtime.get("timeout") is None:
            merged["timeout"] = skill_overrides["timeout"]
        else:
            warnings.append("timeout 类型不一致(local=%s, override=%s)，回退本地值" % (local_type, override_type))

    if "retry" in skill_overrides:
        local_retry = local_runtime.get("retry", {})
        override_retry = skill_overrides["retry"]
        if isinstance(override_retry, dict):
            merged_retry = dict(local_retry) if isinstance(local_retry, dict) else {}
            merged_retry.update(override_retry)
            merged["retry"] = merged_retry
        else:
            warnings.append("retry overrides 非 object，回退本地值")

    return merged, warnings


def resolve_runtime_params(step, workflow_dir):
    """解析 step 的最终 runtime 参数。

    流程：
    1. 读取 step.runtime 引用的 runtime.yaml
    2. 确定 overrides 文件路径:
       a. 若 runtime.yaml 含 external_overrides,相对 runtime.yaml 所在目录解析(D4-013)
       b. 否则查找默认路径 _DEFAULT_OVERRIDES_PATHS(D5-003,不依赖 skill 单独声明)
    3. 从 overrides 中筛选当前 skill 名对应的 overrides
    4. 用 overrides 的 timeout/retry 覆盖本地值
    5. 返回最终参数 (timeout, retry, warnings)

    返回 (timeout, retry_dict, warnings)：
      timeout: int (默认 300)
      retry_dict: {"max": int, "backoff": str, "interval": int}
      warnings: [str]
    """
    warnings = []
    runtime_ref = step.get("runtime")
    skill_name = step.get("skill", "")

    if not runtime_ref:
        # 未声明 runtime，用默认值
        return 300, {"max": 0, "backoff": "fixed", "interval": 5}, []

    # 1. 读取 runtime.yaml
    local_runtime, rt_warnings = load_runtime_yaml(runtime_ref, workflow_dir)
    warnings.extend(rt_warnings)

    # 2. 确定 overrides 文件路径
    #    runtime.yaml 所在目录 = runtime.yaml 文件路径的父目录(skill 根目录)
    runtime_path = Path(workflow_dir) / runtime_ref
    runtime_dir = runtime_path.parent

    external_ref = local_runtime.get("external_overrides")
    if external_ref:
        # runtime.yaml 显式声明 external_overrides:相对 runtime.yaml 所在目录解析(D4-013)
        overrides_path = runtime_dir / external_ref
    else:
        # 未声明:查找默认路径(D5-003)
        overrides_path = None
        for candidate in _DEFAULT_OVERRIDES_PATHS:
            if candidate.exists():
                overrides_path = candidate
                break

    if overrides_path:
        merged_runtime, eo_warnings = merge_external_overrides(
            local_runtime, overrides_path, skill_name
        )
        warnings.extend(eo_warnings)
    else:
        merged_runtime = local_runtime

    # 3. 提取最终参数
    timeout = merged_runtime.get("timeout", 300)
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        warnings.append("timeout 非整数，用默认值 300")
        timeout = 300

    retry_dict = merged_runtime.get("retry", {})
    if not isinstance(retry_dict, dict):
        warnings.append("retry 非 object，用默认值")
        retry_dict = {}

    retry = {
        "max": retry_dict.get("max", 0) if isinstance(retry_dict.get("max", 0), int) and not isinstance(retry_dict.get("max", 0), bool) else 0,
        "backoff": retry_dict.get("backoff", "fixed") if retry_dict.get("backoff", "fixed") in ("fixed", "exponential") else "fixed",
        "interval": retry_dict.get("interval", 5) if isinstance(retry_dict.get("interval", 5), int) and not isinstance(retry_dict.get("interval", 5), bool) else 5,
    }

    return timeout, retry, warnings


def compute_retry_delay(retry, attempt):
    """根据 retry 策略计算重试延迟（秒）。"""
    backoff = retry.get("backoff", "fixed")
    interval = retry.get("interval", 5)
    if backoff == "exponential":
        return interval * (2 ** attempt)
    return interval


# --------------------------------------------------------------------------- #
# skill-usage-tracker 与 failure-casebook 接入(D4-017/D5-001/D5-004 闭环修复)
# --------------------------------------------------------------------------- #
def _run_subprocess(script_path, args_list, timeout=15):
    """运行子脚本,返回 (returncode, stdout, stderr)。失败不抛异常。"""
    if not script_path.exists():
        return 1, "", "脚本不存在: %s" % script_path
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args_list,
            capture_output=True, text=True, timeout=timeout, encoding="utf-8",
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "子脚本超时(%ds): %s" % (timeout, script_path.name)
    except Exception as exc:
        return 1, "", "子脚本异常: %s" % exc


def _track_usage_before(skill_name, pipeline_name):
    """执行 skill 前记录调用,返回 call_id(失败返回 None,不阻塞)。

    对应 SKILL.md §十二.1 的"执行前 record"。
    """
    if not _TRACK_USAGE_PY.exists():
        return None
    args = ["record", "--skill", skill_name, "--status", "success",
            "--caller", "workflow-runtime"]
    if pipeline_name:
        args.extend(["--pipeline", pipeline_name])
    rc, stdout, stderr = _run_subprocess(_TRACK_USAGE_PY, args)
    if rc != 0:
        sys.stdout.write("  ⚠ usage-tracker 记录失败(已忽略): %s\n" % stderr.strip())
        return None
    # 从 stdout 解析 call_id(V4-001: 优先解析机器可读行,回退到字符串解析)
    for line in stdout.splitlines():
        if line.startswith("CALL_ID:"):
            return line[len("CALL_ID:"):].strip()
    # 回退:解析 "PASS  记录已写入:call-20260807-001  skill=..." 格式
    for line in stdout.splitlines():
        if "记录已写入:" in line:
            parts = line.split("记录已写入:")
            if len(parts) >= 2 and parts[1].split():
                return parts[1].split()[0]
    return None


def _track_usage_after(call_id, skill_name, status, duration_ms=None,
                       outputs=None, error_code=None):
    """执行 skill 后更新调用记录(失败不阻塞)。

    对应 SKILL.md §十二.1 的"执行后 record"。
    """
    if not call_id or not _TRACK_USAGE_PY.exists():
        return
    args = ["record", "--skill", skill_name, "--call-id", call_id,
            "--status", status, "--caller", "workflow-runtime"]
    if duration_ms is not None:
        args.extend(["--duration-ms", str(duration_ms)])
    if outputs:
        args.extend(["--outputs"] + list(outputs))
    if error_code and status == "fail":
        args.extend(["--error-code", error_code])
    rc, stdout, stderr = _run_subprocess(_TRACK_USAGE_PY, args)
    if rc != 0:
        sys.stdout.write("  ⚠ usage-tracker 更新失败(已忽略): %s\n" % stderr.strip())


def _casebook_auto_query(skill_name):
    """执行 skill 前查询历史失败案例,返回 preventive_hints 列表(失败返回空列表)。

    对应 failure-casebook/SKILL.md §六 的"执行前 auto-query"。
    """
    if not _CASEBOOK_PY.exists():
        return []
    rc, stdout, stderr = _run_subprocess(
        _CASEBOOK_PY, ["auto-query", "--skill", skill_name])
    if rc != 0:
        return []
    try:
        result = json.loads(stdout)
        return result.get("preventive_hints", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _casebook_record(skill_name, code, reason, fix):
    """skill 执行失败时记录失败案例(失败不阻塞)。

    对应 workflow-runtime/SKILL.md §八第4点的"失败时 record"。
    """
    if not _CASEBOOK_PY.exists():
        return
    args = ["record", "--skill", skill_name, "--code", code,
            "--reason", reason, "--fix", fix]
    rc, stdout, stderr = _run_subprocess(_CASEBOOK_PY, args)
    if rc != 0:
        sys.stdout.write("  ⚠ casebook 记录失败(已忽略): %s\n" % stderr.strip())


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
def execute_workflow(workflow, step_index, report, dry_run=False,
                     workflow_dir=None, simulate_failure=None):
    """按 steps 顺序执行工作流。

    dry_run=True 时只打印计划(由 print_execution_plan 处理,本函数不被调用)。
    dry_run=False 时:逐 step 调度,遇到 pause 则暂停并保存状态。
    实际调用 skill 由宿主/AI 完成,本脚本模拟执行流程并记录轨迹,
    同时接入 usage-tracker/failure-casebook 闭环,并实现 on_fail/parallel 语义。

    simulate_failure: set of step_id,模拟这些 step 执行失败(用于测试 on_fail 逻辑)。

    返回 (status, exit_code):
      status ∈ {"done", "paused", "aborted"}
      exit_code: 0=done/paused, 1=aborted
    """
    if not workflow.get("steps"):
        sys.stderr.write("workflow 无步骤\n")
        return "aborted", 1

    first_id = workflow["steps"][0].get("id")
    return execute_from_step(workflow, step_index, report, first_id,
                             dry_run=dry_run, workflow_dir=workflow_dir,
                             simulate_failure=simulate_failure)


def _execute_skill_step(step, report, workflow_dir, pipeline_name, simulate_failure, retries=0):
    """执行单个 skill step,返回 "done" 或 "failed"。

    接入点(对应 SKILL.md 声明):
    - 执行前:failure-casebook auto-query 查询历史失败案例(D5-004)
    - 执行前:skill-usage-tracker record 获取 call_id(D4-017/D5-001)
    - 执行后:skill-usage-tracker record 更新状态(D4-017/D5-001)
    - 失败时:failure-casebook record 记录失败案例(D5-004)

    实际 skill 调用由宿主/AI 完成,本函数模拟执行结果:
    - 默认成功(status="done")
    - 若 step.id 在 simulate_failure 集合中,模拟失败(status="failed")

    retries: 该 step 的累计回退次数(写入 step record,V3-004 修复)
    """
    sid = step.get("id")
    title = step.get("title", sid)
    skill_name = step.get("skill", "")

    sys.stdout.write("\n[执行] %s (id=%s, skill=%s)\n" % (title, sid, skill_name))

    # 1. failure-casebook auto-query(执行前查询历史失败案例)
    hints = _casebook_auto_query(skill_name)
    if hints:
        sys.stdout.write("  ℹ 历史失败预防提示:\n")
        for h in hints:
            sys.stdout.write("    - %s\n" % h)

    # 2. usage-tracker 记录(执行前,获取 call_id)
    call_id = _track_usage_before(skill_name, pipeline_name)

    # 3. 解析 runtime 参数(读取 runtime.yaml + 合并 external_overrides)
    runtime_ref = step.get("runtime")
    timeout = 300
    retry = {"max": 0, "backoff": "fixed", "interval": 5}
    if runtime_ref:
        sys.stdout.write("  runtime: %s\n" % runtime_ref)
        timeout, retry, rt_warnings = resolve_runtime_params(step, workflow_dir)
        for w in rt_warnings:
            sys.stdout.write("  ⚠ %s\n" % w)
        sys.stdout.write("  timeout=%ds retry(max=%d,backoff=%s,interval=%ds)\n" % (
            timeout, retry["max"], retry["backoff"], retry["interval"]))

    # 4. 模拟执行(实际调用由宿主完成,脚本记录轨迹+调用闭环接入)
    start_ts = time.time()
    is_failure = sid in simulate_failure
    status = "failed" if is_failure else "done"

    append_step_record(report, sid, status=status,
                       outputs=step.get("outputs", []), retries=retries)
    if runtime_ref:
        report["steps"][-1]["runtime"] = {"timeout": timeout, "retry": retry}
    save_report(report)

    duration_ms = int((time.time() - start_ts) * 1000)
    outputs_list = step.get("outputs", [])

    if is_failure:
        sys.stdout.write("  ✗ 模拟失败\n")
        # 5. usage-tracker 更新(失败)
        _track_usage_after(call_id, skill_name, "fail", duration_ms,
                           outputs_list, "SIMULATED_FAILURE")
        # 6. failure-casebook 记录失败案例
        _casebook_record(skill_name, "SIMULATED_FAILURE",
                         "模拟失败(用于测试 on_fail 逻辑)",
                         "检查 skill 输入参数与上下游契约")
    else:
        sys.stdout.write("  → 完成,产物: %s\n" % (", ".join(outputs_list) or "(无)"))
        # 5. usage-tracker 更新(成功)
        _track_usage_after(call_id, skill_name, "success", duration_ms, outputs_list)

    return status


def execute_from_step(workflow, step_index, report, start_id, dry_run=False,
                      workflow_dir=None, simulate_failure=None):
    """从指定 step 开始执行。

    升级后实现(对应 execution-semantics.md):
    - on_fail 三分支:back_to(回退重跑)/skip(跳过继续)/abort(终止)(D4-009)
    - parallel_with 汇聚点:同组 step 全部执行后才继续 next(D4-010)
    - retry_counts 累计:back_to 时累加,超 max_retries 升级为 abort(D4-011)

    simulate_failure: set of step_id,模拟这些 step 执行失败(用于测试 on_fail 逻辑)。
    """
    current_id = start_id
    retry_counts = {}  # step_id → 累计回退次数(D4-011)
    pipeline_name = workflow.get("name", "")
    simulate_failure = simulate_failure or set()
    # parallel_handled 记录已被作为 parallel_with 伙伴执行的 step_id(D4-010)
    # 当线性遍历到这些 step 时跳过(避免重复执行);back_to 时清空以允许重新执行
    parallel_handled = set()

    while current_id and current_id != END_MARKER:
        # 跳过已被并行调度处理的 step(避免并行组重复执行)(D4-010)
        if current_id in parallel_handled:
            step = step_index.get(current_id, {})
            current_id = step.get("next", END_MARKER)
            continue

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

        # parallel_with 汇聚点处理(D4-010)
        # 遇到 parallel_with 时,先执行同组伙伴,再执行当前 step,然后走共同 next
        parallel_ref = step.get("parallel_with")
        if parallel_ref and parallel_ref not in parallel_handled:
            if parallel_ref not in step_index:
                # V2-003: 悬空引用输出 WARNING
                sys.stdout.write("  ⚠ parallel_with 引用的 step 不存在: %s\n" % parallel_ref)
            else:
                partner_step = step_index[parallel_ref]
                sys.stdout.write("\n[并行调度] %s 与 %s 并行执行\n" % (sid, parallel_ref))
                partner_retries = retry_counts.get(parallel_ref, 0)
                partner_result = _execute_skill_step(
                    partner_step, report, workflow_dir,
                    pipeline_name, simulate_failure, retries=partner_retries)
                parallel_handled.add(parallel_ref)
                # V2-004: 并行伙伴失败时按伙伴自身 on_fail 处理
                if partner_result == "failed":
                    partner_on_fail = partner_step.get("on_fail", {})
                    partner_action = partner_on_fail.get("action", "abort")
                    sys.stdout.write("  ⚠ 并行伙伴 %s 失败,on_fail=%s\n" % (parallel_ref, partner_action))
                    if partner_action == "abort":
                        report["status"] = "aborted"
                        report["finished_at"] = _now_iso()
                        save_report(report)
                        return "aborted", 1
                    # back_to/skip 伙伴失败不阻断当前 step 执行(当前 step 的 on_fail 会处理)
                    # 但记录 WARNING 供观测

        # 执行当前 skill step
        current_retries = retry_counts.get(sid, 0)
        result = _execute_skill_step(step, report, workflow_dir,
                                     pipeline_name, simulate_failure,
                                     retries=current_retries)

        # on_fail 处理(D4-009/D4-011)
        if result == "failed":
            on_fail = step.get("on_fail", {})
            action = on_fail.get("action", "abort")

            if action == "back_to":
                target = on_fail.get("target", current_id)
                max_retries = on_fail.get("max_retries", 3)
                retry_counts[target] = retry_counts.get(target, 0) + 1

                if retry_counts[target] > max_retries:
                    # 超限升级为 abort(D4-011)
                    sys.stdout.write("  ⚠ 回退超限(%d > %d),升级为 abort\n" % (
                        retry_counts[target], max_retries))
                    report["status"] = "aborted"
                    report["finished_at"] = _now_iso()
                    save_report(report)
                    sys.stdout.write("\n建议运行: python replanner/scripts/replan.py "
                                     "replan --input task-tree.json --failure %s\n" % sid)
                    return "aborted", 1
                else:
                    # 清空 parallel_handled,允许回退后重新执行并行组(D4-010)
                    parallel_handled.clear()
                    sys.stdout.write("  ⤴ 回退到 %s (第 %d 次,上限 %d)\n" % (
                        target, retry_counts[target], max_retries))
                    current_id = target
                    continue

            elif action == "skip":
                sys.stdout.write("  ⏭ 跳过 %s,继续下一步\n" % sid)
                nxt = step.get("next", END_MARKER)
                current_id = nxt
                continue

            else:  # abort
                report["status"] = "aborted"
                report["finished_at"] = _now_iso()
                save_report(report)
                sys.stdout.write("\n建议运行: python replanner/scripts/replan.py "
                                 "replan --input task-tree.json --failure %s\n" % sid)
                return "aborted", 1

        # 成功,继续下一步
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

    # 解析 --simulate-failure(逗号分隔的 step_id 列表,用于测试 on_fail 逻辑)
    simulate_failure = set()
    if getattr(args, "simulate_failure", None):
        simulate_failure = {
            s.strip() for s in args.simulate_failure.split(",") if s.strip()
        }

    workflow_dir = Path(args.input).resolve().parent
    status, exit_code = execute_workflow(
        workflow, step_index, report, dry_run=False,
        workflow_dir=workflow_dir, simulate_failure=simulate_failure)
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

    workflow_dir = Path(args.workflow).resolve().parent
    status, exit_code = execute_from_step(workflow, step_index, report, next_step, workflow_dir=workflow_dir)
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
    p_run.add_argument("--simulate-failure", default=None,
                       help="模拟指定 step 失败(逗号分隔的 step_id,用于测试 on_fail 逻辑)")
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
