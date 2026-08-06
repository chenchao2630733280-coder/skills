#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""get_prompt.py - prompt 检索脚本。

子命令:
  by-skill --skill <skill名>            按 skill 名检索全部版本
  by-tag   --tag <标签>                 按标签检索(跨 skill)
  latest   --skill <skill名> [--tag X]  获取最新版本(可选限定 tag)

设计原则(与 skill-runtime/validate_runtime.py 一致):
- 失败不抛异常,统一通过 error 字段与退出码表达
- latest 按 semver 排序(正式版 > 预发布版)

退出码:0=成功;1=有错误(如 skill 不存在);2=参数错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------- 常量 ----------

# 本脚本位于 <ws>/prompt-registry/scripts/get_prompt.py
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
        return None, (
            "注册表不存在(.trae-cn/prompts/prompt-registry.json),"
            "请先用 register_prompt.py add 注册"
        )
    try:
        text = REGISTRY_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as e:
        return None, f"读取注册表失败:{e}"
    if not isinstance(data, dict) or "skills" not in data:
        return None, "注册表格式错误:缺少 skills 字段"
    return data, None


def _semver_key(version):
    """将 semver 版本号转为可比较的元组,用于排序。

    1.0.0       -> (1, 0, 0, 1, "")
    1.1.0-beta  -> (1, 1, 0, 0, "beta")

    正式版 > 预发布版(同主次修订号下):
      正式版第 4 位 = 1,预发布版第 4 位 = 0
    """
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?$", version)
    if not m:
        return (0, 0, 0, 0, "")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre = m.group(4) or ""
    # 正式版(无 pre)排更大:pre_sort=1;预发布版 pre_sort=0
    pre_sort = 1 if pre == "" else 0
    return (major, minor, patch, pre_sort, pre)


def _output_report(command, skill=None, tag=None, results=None, error=None):
    """输出 JSON 报告到 stdout。"""
    report = {
        "command": command,
        "skill": skill,
        "tag": tag,
        "results": results or [],
        "error": error,
        "timestamp": _now_iso(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


# ---------- 子命令实现 ----------

def cmd_by_skill(args):
    """by-skill 子命令:按 skill 名检索全部版本。"""
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("by-skill", skill=args.skill, error=err)
        return 1

    results = []
    for skill_entry in data["skills"]:
        if skill_entry["skill"] != args.skill:
            continue
        for v in skill_entry["versions"]:
            results.append({
                "skill": skill_entry["skill"],
                "version": v["version"],
                "tag": v["tag"],
                "path": v["path"],
                "updated_at": v["updated_at"],
            })

    if not results:
        err = f"skill 不存在或无已注册 prompt:{args.skill}"
        print(f"FAIL  {err}")
        _output_report("by-skill", skill=args.skill, error=err)
        return 1

    print(f"{args.skill} 共 {len(results)} 个版本:")
    for r in results:
        print(f"  {r['version']}  tag={r['tag']}  {r['path']}")
    _output_report("by-skill", skill=args.skill, results=results)
    return 0


def cmd_by_tag(args):
    """by-tag 子命令:按标签检索(跨 skill)。"""
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("by-tag", tag=args.tag, error=err)
        return 1

    results = []
    for skill_entry in data["skills"]:
        for v in skill_entry["versions"]:
            if v["tag"] == args.tag:
                results.append({
                    "skill": skill_entry["skill"],
                    "version": v["version"],
                    "tag": v["tag"],
                    "path": v["path"],
                    "updated_at": v["updated_at"],
                })

    if not results:
        err = f"无 tag={args.tag} 的 prompt"
        print(f"FAIL  {err}")
        _output_report("by-tag", tag=args.tag, error=err)
        return 1

    print(f"tag={args.tag} 共 {len(results)} 条:")
    for r in results:
        print(f"  {r['skill']}@{r['version']}  {r['path']}")
    _output_report("by-tag", tag=args.tag, results=results)
    return 0


def cmd_latest(args):
    """latest 子命令:获取最新版本(可选限定 tag)。"""
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("latest", skill=args.skill, tag=args.tag, error=err)
        return 1

    # 查找 skill
    skill_entry = None
    for s in data["skills"]:
        if s["skill"] == args.skill:
            skill_entry = s
            break

    if skill_entry is None:
        err = f"skill 不存在:{args.skill}"
        print(f"FAIL  {err}")
        _output_report("latest", skill=args.skill, tag=args.tag, error=err)
        return 1

    # 按 tag 过滤
    candidates = skill_entry["versions"]
    if args.tag:
        candidates = [v for v in candidates if v["tag"] == args.tag]
        if not candidates:
            err = f"{args.skill} 无 tag={args.tag} 的版本"
            print(f"FAIL  {err}")
            _output_report("latest", skill=args.skill, tag=args.tag, error=err)
            return 1

    # 按 semver 排序取最大
    latest_v = max(candidates, key=lambda v: _semver_key(v["version"]))
    result = {
        "skill": args.skill,
        "version": latest_v["version"],
        "tag": latest_v["tag"],
        "path": latest_v["path"],
        "updated_at": latest_v["updated_at"],
    }

    print(f"最新版本:{args.skill}@{result['version']}  tag={result['tag']}")
    print(f"  路径:{result['path']}")
    _output_report("latest", skill=args.skill, tag=args.tag, results=[result])
    return 0


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="get_prompt.py",
        description="prompt 检索脚本。按 skill / tag / 最新版本检索 prompt。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python get_prompt.py by-skill --skill game-blueprint\n"
            "  python get_prompt.py by-tag --tag detailed\n"
            "  python get_prompt.py latest --skill game-blueprint --tag stable\n"
            "\n"
            "退出码:0=成功;1=有错误;2=参数错误"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # by-skill
    p_by_skill = sub.add_parser("by-skill", help="按 skill 名检索全部版本")
    p_by_skill.add_argument("--skill", required=True, help="skill 名称")
    p_by_skill.set_defaults(func=cmd_by_skill)

    # by-tag
    p_by_tag = sub.add_parser("by-tag", help="按标签检索(跨 skill)")
    p_by_tag.add_argument("--tag", required=True, help="变体标签")
    p_by_tag.set_defaults(func=cmd_by_tag)

    # latest
    p_latest = sub.add_parser("latest", help="获取最新版本(可选限定 tag)")
    p_latest.add_argument("--skill", required=True, help="skill 名称")
    p_latest.add_argument("--tag", default=None, help="限定 tag(可选)")
    p_latest.set_defaults(func=cmd_latest)

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
        # 兜底:任何未捕获异常都输出报告并返回 exit 1
        err = f"未捕获异常:{e}"
        print(f"FAIL  {err}")
        _output_report(getattr(args, "command", "unknown"), error=err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
