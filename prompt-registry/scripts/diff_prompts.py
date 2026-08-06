#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_prompts.py - prompt 版本/变体对比脚本。

用法:
  # 同 skill 两个版本对比
  python diff_prompts.py --skill game-blueprint \\
      --left-version 1.0.0 --right-version 1.1.0-beta

  # 跨 skill 对比
  python diff_prompts.py --left-skill game-blueprint --left-version 1.0.0 \\
      --right-skill implement-frontend --right-version 1.0.0

设计原则(与 skill-runtime/validate_runtime.py 一致):
- 失败不抛异常,统一通过 error 字段与退出码表达
- 输出 unified diff 格式 + 增删统计

退出码:0=成功(含无差异);1=有错误;2=参数错误
"""

import argparse
import difflib
import json
import sys
from datetime import datetime
from pathlib import Path

# ---------- 常量 ----------

# 本脚本位于 <ws>/prompt-registry/scripts/diff_prompts.py
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]

# 注册表根目录
PROMPTS_ROOT = WORKSPACE_DIR / ".trae-cn" / "prompts"
REGISTRY_FILE = PROMPTS_ROOT / "prompt-registry.json"


# ---------- 工具函数 ----------

def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_registry():
    """加载注册表。

    返回 (data, error):成功时 error=None;失败时 data=None。
    """
    if not REGISTRY_FILE.exists():
        return None, "注册表不存在(.trae-cn/prompts/prompt-registry.json)"
    try:
        text = REGISTRY_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as e:
        return None, f"读取注册表失败:{e}"
    if not isinstance(data, dict) or "skills" not in data:
        return None, "注册表格式错误:缺少 skills 字段"
    return data, None


def _resolve_prompt_path(registry, skill, version):
    """从注册表解析 prompt 模板文件的绝对路径。

    返回 (path, error):成功时 error=None;失败时 path=None。
    """
    for s in registry["skills"]:
        if s["skill"] == skill:
            for v in s["versions"]:
                if v["version"] == version:
                    return PROMPTS_ROOT / v["path"], None
            return None, f"版本不存在:{skill}@{version}"
    return None, f"skill 不存在:{skill}"


def _output_report(command, results=None, stats=None, error=None):
    """输出 JSON 报告到 stdout。"""
    report = {
        "command": command,
        "results": results or [],
        "stats": stats or {},
        "error": error,
        "timestamp": _now_iso(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


# ---------- 子命令实现 ----------

def cmd_diff(args):
    """diff 子命令:对比两个版本/变体的 prompt。"""
    # 确定左右两侧的 skill
    left_skill = args.left_skill or args.skill
    right_skill = args.right_skill or args.skill
    left_version = args.left_version
    right_version = args.right_version

    if not left_skill or not right_skill:
        err = "缺少 skill 参数:需指定 --skill 或 --left-skill/--right-skill"
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 2

    # 加载注册表
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1

    # 解析路径
    left_path, err = _resolve_prompt_path(data, left_skill, left_version)
    if err:
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1
    right_path, err = _resolve_prompt_path(data, right_skill, right_version)
    if err:
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1

    # 读取文件
    try:
        left_text = left_path.read_text(encoding="utf-8")
    except Exception as e:
        err = f"读取左侧 prompt 失败:{e}"
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1
    try:
        right_text = right_path.read_text(encoding="utf-8")
    except Exception as e:
        err = f"读取右侧 prompt 失败:{e}"
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1

    left_lines = left_text.splitlines(keepends=True)
    right_lines = right_text.splitlines(keepends=True)

    # 生成 unified diff
    diff = list(difflib.unified_diff(
        left_lines,
        right_lines,
        fromfile=f"{left_skill}@{left_version}",
        tofile=f"{right_skill}@{right_version}",
        lineterm="",
    ))

    # 统计增删
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    diff_text = "".join(diff)

    stats = {
        "added": added,
        "removed": removed,
        "changed": added + removed,
    }

    results = [{
        "left": f"{left_skill}@{left_version}",
        "right": f"{right_skill}@{right_version}",
        "diff": diff_text,
        "added": added,
        "removed": removed,
    }]

    # 控制台输出
    if not diff_text:
        print(f"无差异:{left_skill}@{left_version} == {right_skill}@{right_version}")
    else:
        print(f"diff {left_skill}@{left_version} vs {right_skill}@{right_version}")
        print(f"  +{added} 行  -{removed} 行")
        print()
        print(diff_text, end="" if diff_text.endswith("\n") else "\n")

    _output_report("diff", results=results, stats=stats)
    return 0


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="diff_prompts.py",
        description="prompt 版本/变体对比脚本。输出 unified diff + 增删统计。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  # 同 skill 两版本对比\n"
            "  python diff_prompts.py --skill game-blueprint "
            "--left-version 1.0.0 --right-version 1.1.0-beta\n"
            "  # 跨 skill 对比\n"
            "  python diff_prompts.py --left-skill game-blueprint --left-version 1.0.0 "
            "--right-skill implement-frontend --right-version 1.0.0\n"
            "\n"
            "退出码:0=成功(含无差异);1=有错误;2=参数错误"
        ),
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="同 skill 对比时的 skill 名(与 --left-skill/--right-skill 二选一)",
    )
    parser.add_argument(
        "--left-skill",
        default=None,
        help="左侧 skill 名(跨 skill 对比时使用)",
    )
    parser.add_argument(
        "--left-version",
        required=True,
        help="左侧版本号",
    )
    parser.add_argument(
        "--right-skill",
        default=None,
        help="右侧 skill 名(跨 skill 对比时使用)",
    )
    parser.add_argument(
        "--right-version",
        required=True,
        help="右侧版本号",
    )
    return parser


# ---------- 主入口 ----------

def main(argv=None):
    """主入口,返回退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return cmd_diff(args)
    except Exception as e:
        # 兜底:任何未捕获异常都输出报告并返回 exit 1
        err = f"未捕获异常:{e}"
        print(f"FAIL  {err}")
        _output_report("diff", error=err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
