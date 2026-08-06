#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_runtime.py - Agent Runtime 层契约校验脚本。

子命令:
  check --skill <skill名>   校验单个 skill 的 runtime.yaml
  scan                     扫描工作台全部 skill,输出汇总

设计原则(与 tool-git-ops 一致):
- 失败不抛异常,统一通过 error 字段与退出码表达
- runtime.yaml 是可选的:不存在则标 UNDECLARED(非 FAIL)
- 一旦声明则必符 schema:字段缺失或类型错误标 FAIL

产出:在当前工作目录写入 runtime-contract-report.json
退出码:0=全部通过(含 UNDECLARED);1=有 FAIL 项;2=argparse 参数错误
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# PyYAML 可选导入:缺失时仍能处理"runtime.yaml 不存在"的场景
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# ---------- 常量 ----------

# 工作台根目录:本脚本位于 <ws>/skill-runtime/scripts/validate_runtime.py
# parents[0]=skill-runtime  parents[1]=skills(工作台根)  parents[2]=.agents
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]

REPORT_FILENAME = "runtime-contract-report.json"

# 已知字段类型(用于 schema 校验)
BACKOFF_ENUM = ("fixed", "exponential")
OUTPUT_TYPE_ENUM = ("file", "directory")


# ---------- 工具函数 ----------

def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_yaml():
    """检查 PyYAML 是否可用,不可用时返回错误字符串。"""
    if yaml is None:
        return (
            "PyYAML 未安装,无法解析 runtime.yaml。"
            "请执行:python -m pip install pyyaml"
        )
    return None


def _is_nonempty_string(value):
    """判断是否为非空字符串。"""
    return isinstance(value, str) and len(value) > 0


def _is_nonneg_int(value):
    """判断是否为非负整数(bool 会被排除,因为 isinstance(True, int) 为 True)。"""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_pos_int(value):
    """判断是否为正整数(>=1)。"""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _is_bool(value):
    """判断是否为布尔值。"""
    return isinstance(value, bool)


# ---------- schema 校验 ----------

def _validate_retry(retry, errors, path="retry"):
    """校验 retry 对象。"""
    if not isinstance(retry, dict):
        errors.append(f"{path}:期望 object,实际 {type(retry).__name__}")
        return
    # retry.max
    if "max" in retry and not _is_nonneg_int(retry["max"]):
        errors.append(f"{path}.max:期望非负整数,实际 {retry['max']!r}")
    # retry.backoff
    if "backoff" in retry and retry["backoff"] not in BACKOFF_ENUM:
        errors.append(
            f"{path}.backoff:期望枚举 {BACKOFF_ENUM},实际 {retry['backoff']!r}"
        )
    # retry.interval
    if "interval" in retry and not _is_pos_int(retry["interval"]):
        errors.append(f"{path}.interval:期望正整数,实际 {retry['interval']!r}")


def _validate_inputs(inputs, errors, path="inputs"):
    """校验 inputs 数组。"""
    if not isinstance(inputs, list):
        errors.append(f"{path}:期望 array,实际 {type(inputs).__name__}")
        return
    for idx, item in enumerate(inputs):
        item_path = f"{path}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path}:期望 object,实际 {type(item).__name__}")
            continue
        # name 必填
        if "name" not in item or not _is_nonempty_string(item["name"]):
            errors.append(f"{item_path}.name:必填且为非空字符串")
        # schema 可选,string 或 null
        if "schema" in item and item["schema"] is not None \
                and not isinstance(item["schema"], str):
            errors.append(f"{item_path}.schema:期望 string 或 null,实际 {type(item['schema']).__name__}")
        # required 可选,boolean
        if "required" in item and not _is_bool(item["required"]):
            errors.append(f"{item_path}.required:期望 boolean,实际 {type(item['required']).__name__}")


def _validate_outputs(outputs, errors, path="outputs"):
    """校验 outputs 数组。"""
    if not isinstance(outputs, list):
        errors.append(f"{path}:期望 array,实际 {type(outputs).__name__}")
        return
    for idx, item in enumerate(outputs):
        item_path = f"{path}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path}:期望 object,实际 {type(item).__name__}")
            continue
        # path 必填
        if "path" not in item or not _is_nonempty_string(item["path"]):
            errors.append(f"{item_path}.path:必填且为非空字符串")
        # type 必填,枚举
        if "type" not in item or item["type"] not in OUTPUT_TYPE_ENUM:
            errors.append(
                f"{item_path}.type:必填且为枚举 {OUTPUT_TYPE_ENUM},实际 {item.get('type')!r}"
            )
        # optional 可选,boolean
        if "optional" in item and not _is_bool(item["optional"]):
            errors.append(f"{item_path}.optional:期望 boolean,实际 {type(item['optional']).__name__}")


def _validate_degrade(degrade, errors, path="degrade"):
    """校验 degrade 数组。"""
    if not isinstance(degrade, list):
        errors.append(f"{path}:期望 array,实际 {type(degrade).__name__}")
        return
    for idx, item in enumerate(degrade):
        item_path = f"{path}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path}:期望 object,实际 {type(item).__name__}")
            continue
        # trigger 必填
        if "trigger" not in item or not _is_nonempty_string(item["trigger"]):
            errors.append(f"{item_path}.trigger:必填且为非空字符串")
        # action 必填
        if "action" not in item or not _is_nonempty_string(item["action"]):
            errors.append(f"{item_path}.action:必填且为非空字符串")
        # target 可选,string 或 null
        if "target" in item and item["target"] is not None \
                and not isinstance(item["target"], str):
            errors.append(f"{item_path}.target:期望 string 或 null,实际 {type(item['target']).__name__}")


def validate_runtime_data(data, errors):
    """对解析后的 runtime.yaml dict 做 schema 校验,errors 列表追加问题。"""
    if not isinstance(data, dict):
        errors.append(f"runtime.yaml 顶层:期望 object,实际 {type(data).__name__}")
        return

    # 未知字段检测(与 JSON Schema additionalProperties:false 对齐)
    known_top = {"timeout", "retry", "inputs", "outputs", "degrade", "external_overrides"}
    unknown_top = set(data.keys()) - known_top
    if unknown_top:
        errors.append(f"runtime.yaml 含未知字段:{sorted(unknown_top)}")

    # timeout
    if "timeout" in data and not _is_nonneg_int(data["timeout"]):
        errors.append(f"timeout:期望非负整数,实际 {data['timeout']!r}")

    # retry
    if "retry" in data:
        _validate_retry(data["retry"], errors)

    # inputs
    if "inputs" in data:
        _validate_inputs(data["inputs"], errors)

    # outputs
    if "outputs" in data:
        _validate_outputs(data["outputs"], errors)

    # degrade
    if "degrade" in data:
        _validate_degrade(data["degrade"], errors)

    # external_overrides(Phase 4 新增)
    if "external_overrides" in data and data["external_overrides"] is not None:
        eo = data["external_overrides"]
        if not isinstance(eo, str):
            errors.append(f"external_overrides:期望 string 或 null,实际 {type(eo).__name__}")
        elif len(eo) == 0:
            errors.append("external_overrides:为空字符串,应为有效文件路径或 null")


# ---------- 单 skill 校验 ----------

def check_skill(skill_dir):
    """校验单个 skill 目录的 runtime.yaml,返回结果 dict。

    返回结构:
      {
        "skill": <name>,
        "declared": bool,
        "status": "PASS" | "FAIL" | "UNDECLARED",
        "errors": [str, ...]
      }
    """
    skill_name = skill_dir.name
    result = {
        "skill": skill_name,
        "declared": False,
        "status": "UNDECLARED",
        "errors": [],
    }

    runtime_path = skill_dir / "runtime.yaml"
    if not runtime_path.exists():
        # runtime.yaml 是可选的,不存在标 UNDECLARED(非 FAIL)
        return result

    result["declared"] = True

    # PyYAML 不可用:标 FAIL 并提示
    yaml_err = _ensure_yaml()
    if yaml_err is not None:
        result["status"] = "FAIL"
        result["errors"].append(yaml_err)
        return result

    # 读取 + 解析
    try:
        text = runtime_path.read_text(encoding="utf-8")
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"读取 runtime.yaml 失败:{e}")
        return result

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        result["status"] = "FAIL"
        result["errors"].append(f"YAML 解析失败:{e}")
        return result

    # 空文件(YAML 解析为 None)按空 dict 处理(走默认值)
    if data is None:
        data = {}

    # schema 校验
    validate_runtime_data(data, result["errors"])

    if result["errors"]:
        result["status"] = "FAIL"
    else:
        result["status"] = "PASS"

    return result


# ---------- 全量扫描 ----------

def scan_all_skills(workspace_dir):
    """扫描工作台全部 skill 子目录,返回结果列表。

    skill 子目录定义:workspace_dir 下的直接子目录,且含 SKILL.md。
    _shared / .trae 等不计入。
    """
    results = []
    if not workspace_dir.exists():
        return results
    for entry in sorted(workspace_dir.iterdir()):
        if not entry.is_dir():
            continue
        # 跳过非 skill 目录
        if entry.name in ("_shared", ".trae"):
            continue
        # 必须含 SKILL.md 才算 skill
        if not (entry / "SKILL.md").exists():
            continue
        results.append(check_skill(entry))
    return results


# ---------- 报告产出 ----------

def write_report(report, cwd=None):
    """把报告 dict 写入当前工作目录的 runtime-contract-report.json。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    out_path = out_dir / REPORT_FILENAME
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def build_report(command, skills):
    """根据子命令名与 skill 结果列表,构建完整报告。"""
    summary = {
        "total": len(skills),
        "declared": sum(1 for s in skills if s["declared"]),
        "pass": sum(1 for s in skills if s["status"] == "PASS"),
        "fail": sum(1 for s in skills if s["status"] == "FAIL"),
    }
    return {
        "command": command,
        "skills": skills,
        "summary": summary,
        "error": None,
        "timestamp": _now_iso(),
    }


# ---------- 子命令实现 ----------

def cmd_check(args):
    """check 子命令:校验单个 skill。"""
    skill_dir = WORKSPACE_DIR / args.skill
    if not skill_dir.exists():
        report = {
            "command": "check",
            "skills": [],
            "summary": {"total": 0, "declared": 0, "pass": 0, "fail": 0},
            "error": f"skill 目录不存在:{skill_dir}",
            "timestamp": _now_iso(),
        }
        write_report(report)
        print(f"FAIL  skill 目录不存在:{args.skill}")
        return 1

    result = check_skill(skill_dir)
    report = build_report("check", [result])
    write_report(report)

    # 控制台输出
    status = result["status"]
    if status == "PASS":
        print(f"PASS  {args.skill} runtime.yaml 符合 schema")
    elif status == "UNDECLARED":
        print(f"UNDECLARED  {args.skill} 未声明 runtime.yaml(可选,跳过)")
    else:
        print(f"FAIL  {args.skill} runtime.yaml 校验失败:")
        for err in result["errors"]:
            print(f"       - {err}")

    return 1 if status == "FAIL" else 0


def cmd_scan(args):
    """scan 子命令:扫描全部 skill。"""
    skills = scan_all_skills(WORKSPACE_DIR)
    report = build_report("scan", skills)
    write_report(report)

    # 控制台输出
    summary = report["summary"]
    print(f"扫描完成:共 {summary['total']} 个 skill")
    print(f"  已声明 runtime.yaml:{summary['declared']}")
    print(f"  PASS:{summary['pass']}  FAIL:{summary['fail']}")

    if summary["fail"] > 0:
        print("\nFAIL 项明细:")
        for s in skills:
            if s["status"] == "FAIL":
                print(f"  - {s['skill']}:")
                for err in s["errors"]:
                    print(f"      {err}")

    return 1 if summary["fail"] > 0 else 0


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="validate_runtime.py",
        description="Agent Runtime 层契约校验脚本。校验 skill 的 runtime.yaml 是否符合 skill-runtime schema。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python validate_runtime.py check --skill game-asset-forge\n"
            "  python validate_runtime.py scan\n"
            "\n"
            "退出码:0=全部通过(含 UNDECLARED);1=有 FAIL 项;2=参数错误\n"
            "产出:当前工作目录下 runtime-contract-report.json"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # check
    p_check = sub.add_parser(
        "check",
        help="校验单个 skill 的 runtime.yaml",
    )
    p_check.add_argument(
        "--skill",
        required=True,
        help="skill 名称(工作台根下的目录名,如 game-asset-forge)",
    )
    p_check.set_defaults(func=cmd_check)

    # scan
    p_scan = sub.add_parser(
        "scan",
        help="扫描工作台全部 skill,输出汇总报告",
    )
    p_scan.set_defaults(func=cmd_scan)

    return parser


# ---------- 主入口 ----------

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
        # 兜底:任何未捕获异常都写入报告并返回 exit 1
        report = {
            "command": getattr(args, "command", "unknown"),
            "skills": [],
            "summary": {"total": 0, "declared": 0, "pass": 0, "fail": 0},
            "error": f"未捕获异常:{e}",
            "timestamp": _now_iso(),
        }
        write_report(report)
        print(f"FAIL  未捕获异常:{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
