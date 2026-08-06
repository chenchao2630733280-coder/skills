#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""register_prompt.py - prompt 注册脚本。

子命令:
  add    --skill <skill名> --version <版本> --file <prompt文件> [--tag <标签>] [--notes <说明>]
  update --skill <skill名> --version <新版本> --file <prompt文件> [--tag <标签>] [--notes <说明>]
  list   [--skill <skill名>]

设计原则(与 skill-runtime/validate_runtime.py 一致):
- 失败不抛异常,统一通过 error 字段与退出码表达
- update 不覆盖旧版本:以新版本号注册,旧版本保留
- add 同 skill+version 重复时标 error

数据存储:
- 注册表:.trae-cn/prompts/prompt-registry.json
- prompt 模板:.trae-cn/prompts/prompts/{skill}/{version}.md

退出码:0=成功;1=有错误;2=argparse 参数错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------- 常量 ----------

# 本脚本位于 <ws>/prompt-registry/scripts/register_prompt.py
# parents[0]=prompt-registry  parents[1]=skills(工作台根)
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[1]

# 注册表根目录:.trae-cn/prompts/
PROMPTS_ROOT = WORKSPACE_DIR / ".trae-cn" / "prompts"
REGISTRY_FILE = PROMPTS_ROOT / "prompt-registry.json"
PROMPTS_DIR = PROMPTS_ROOT / "prompts"

REGISTRY_VERSION = "1.0"

# 已知 tag(不强制,仅提示;超出不报错)
KNOWN_TAGS = ("stable", "detailed", "concise", "experimental")


# ---------- 工具函数 ----------

def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_dir(path):
    """确保目录存在。"""
    path.mkdir(parents=True, exist_ok=True)


def _load_registry():
    """加载注册表,不存在则返回空结构。

    返回 (data, error):成功时 error=None;失败时 data=None。
    """
    if not REGISTRY_FILE.exists():
        return {
            "registry_version": REGISTRY_VERSION,
            "updated_at": _now_iso(),
            "skills": [],
        }, None
    try:
        text = REGISTRY_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception as e:
        return None, f"读取注册表失败:{e}"
    if not isinstance(data, dict) or "skills" not in data:
        return None, "注册表格式错误:缺少 skills 字段"
    return data, None


def _save_registry(data):
    """保存注册表。"""
    _ensure_dir(PROMPTS_ROOT)
    data["updated_at"] = _now_iso()
    REGISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _find_skill(data, skill_name):
    """在注册表中查找 skill 条目,返回 dict 或 None。"""
    for s in data["skills"]:
        if s["skill"] == skill_name:
            return s
    return None


def _find_version(skill_entry, version):
    """在 skill 条目中查找版本,返回 dict 或 None。"""
    for v in skill_entry["versions"]:
        if v["version"] == version:
            return v
    return None


def _output_report(command, skill=None, results=None, error=None):
    """输出 JSON 报告到 stdout(便于机器解析)。"""
    report = {
        "command": command,
        "skill": skill,
        "results": results or [],
        "error": error,
        "timestamp": _now_iso(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


# ---------- 版本号校验(简化 semver)----------

def _validate_version(version):
    """校验版本号是否符合简化 semver 格式。

    合法:1.0.0 / 1.1.0-beta / 2.0.0-rc.1
    返回 None 表示合法,否则返回错误字符串。
    """
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    if not re.match(pattern, version):
        return (
            f"版本号格式错误:{version}"
            "(应为 X.Y.Z 或 X.Y.Z-预发布标签,如 1.0.0 / 1.1.0-beta)"
        )
    return None


# ---------- 子命令实现 ----------

def cmd_add(args):
    """add 子命令:注册新 prompt。"""
    skill_name = args.skill
    version = args.version
    tag = args.tag or "stable"
    notes = args.notes or ""

    # 校验版本号格式
    ver_err = _validate_version(version)
    if ver_err:
        print(f"FAIL  {ver_err}")
        _output_report("add", skill_name, error=ver_err)
        return 1

    # 读取 prompt 文件
    prompt_file = Path(args.file)
    if not prompt_file.exists():
        err = f"prompt 文件不存在:{args.file}"
        print(f"FAIL  {err}")
        _output_report("add", skill_name, error=err)
        return 1
    try:
        prompt_text = prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        err = f"读取 prompt 文件失败:{e}"
        print(f"FAIL  {err}")
        _output_report("add", skill_name, error=err)
        return 1

    # 加载注册表
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("add", skill_name, error=err)
        return 1

    # 查找或创建 skill 条目
    skill_entry = _find_skill(data, skill_name)
    if skill_entry is None:
        skill_entry = {"skill": skill_name, "versions": []}
        data["skills"].append(skill_entry)

    # 检查同 skill+version 是否已存在
    if _find_version(skill_entry, version) is not None:
        err = f"版本已存在:{skill_name}@{version}(用 update 子命令注册新版本)"
        print(f"FAIL  {err}")
        _output_report("add", skill_name, error=err)
        return 1

    # 写入 prompt 模板文件
    skill_prompts_dir = PROMPTS_DIR / skill_name
    _ensure_dir(skill_prompts_dir)
    prompt_path = skill_prompts_dir / f"{version}.md"
    try:
        prompt_path.write_text(prompt_text, encoding="utf-8")
    except Exception as e:
        err = f"写入 prompt 模板失败:{e}"
        print(f"FAIL  {err}")
        _output_report("add", skill_name, error=err)
        return 1

    # 注册版本记录
    rel_path = f"prompts/{skill_name}/{version}.md"
    version_entry = {
        "version": version,
        "tag": tag,
        "path": rel_path,
        "updated_at": _now_iso(),
        "notes": notes,
    }
    skill_entry["versions"].append(version_entry)
    _save_registry(data)

    print(f"OK    已注册 {skill_name}@{version}(tag={tag})")
    _output_report("add", skill_name, results=[version_entry])
    return 0


def cmd_update(args):
    """update 子命令:以新版本号注册更新(不覆盖旧版本)。"""
    skill_name = args.skill
    version = args.version
    tag = args.tag or "stable"
    notes = args.notes or ""

    # 校验版本号
    ver_err = _validate_version(version)
    if ver_err:
        print(f"FAIL  {ver_err}")
        _output_report("update", skill_name, error=ver_err)
        return 1

    # 读取 prompt 文件
    prompt_file = Path(args.file)
    if not prompt_file.exists():
        err = f"prompt 文件不存在:{args.file}"
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1
    try:
        prompt_text = prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        err = f"读取 prompt 文件失败:{e}"
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1

    # 加载注册表
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1

    # skill 必须已存在
    skill_entry = _find_skill(data, skill_name)
    if skill_entry is None:
        err = f"skill 不存在:{skill_name}(update 要求 skill 已注册,先用 add)"
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1

    # 新版本号不能已存在
    if _find_version(skill_entry, version) is not None:
        err = f"版本已存在:{skill_name}@{version}(请换一个更新的版本号)"
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1

    # 写入 prompt 模板
    skill_prompts_dir = PROMPTS_DIR / skill_name
    _ensure_dir(skill_prompts_dir)
    prompt_path = skill_prompts_dir / f"{version}.md"
    try:
        prompt_path.write_text(prompt_text, encoding="utf-8")
    except Exception as e:
        err = f"写入 prompt 模板失败:{e}"
        print(f"FAIL  {err}")
        _output_report("update", skill_name, error=err)
        return 1

    rel_path = f"prompts/{skill_name}/{version}.md"
    version_entry = {
        "version": version,
        "tag": tag,
        "path": rel_path,
        "updated_at": _now_iso(),
        "notes": notes,
    }
    skill_entry["versions"].append(version_entry)
    _save_registry(data)

    print(f"OK    已更新 {skill_name}@{version}(tag={tag},旧版本已保留)")
    _output_report("update", skill_name, results=[version_entry])
    return 0


def cmd_list(args):
    """list 子命令:列出已注册 prompt。"""
    data, err = _load_registry()
    if err:
        print(f"FAIL  {err}")
        _output_report("list", error=err)
        return 1

    results = []
    for skill_entry in data["skills"]:
        if args.skill and skill_entry["skill"] != args.skill:
            continue
        for v in skill_entry["versions"]:
            results.append({
                "skill": skill_entry["skill"],
                "version": v["version"],
                "tag": v["tag"],
                "path": v["path"],
                "updated_at": v["updated_at"],
            })

    # 控制台输出
    if not results:
        if args.skill:
            print(f"(无){args.skill} 无已注册 prompt")
        else:
            print("(空)注册表为空")
    else:
        print(f"共 {len(results)} 条 prompt 记录:")
        for r in results:
            print(f"  {r['skill']}@{r['version']}  tag={r['tag']}  {r['path']}")

    _output_report("list", skill=args.skill, results=results)
    return 0


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="register_prompt.py",
        description="prompt 注册脚本。注册/更新/列出各 skill 的 prompt 模板。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python register_prompt.py add --skill game-blueprint --version 1.0.0 --tag stable --file prompt.md\n"
            "  python register_prompt.py update --skill game-blueprint --version 1.1.0 --file prompt.md\n"
            "  python register_prompt.py list --skill game-blueprint\n"
            "\n"
            "退出码:0=成功;1=有错误;2=参数错误\n"
            "产出:更新 .trae-cn/prompts/prompt-registry.json + prompts/{skill}/{version}.md"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # add
    p_add = sub.add_parser("add", help="注册新 prompt")
    p_add.add_argument("--skill", required=True, help="skill 名称")
    p_add.add_argument("--version", required=True, help="语义化版本号(如 1.0.0)")
    p_add.add_argument("--file", required=True, help="prompt 模板文件路径")
    p_add.add_argument("--tag", default=None, help="变体标签(默认 stable)")
    p_add.add_argument("--notes", default=None, help="版本说明")
    p_add.set_defaults(func=cmd_add)

    # update
    p_update = sub.add_parser("update", help="以新版本号注册更新(不覆盖旧版本)")
    p_update.add_argument("--skill", required=True, help="skill 名称(须已注册)")
    p_update.add_argument("--version", required=True, help="新版本号(须大于现有版本)")
    p_update.add_argument("--file", required=True, help="prompt 模板文件路径")
    p_update.add_argument("--tag", default=None, help="变体标签(默认 stable)")
    p_update.add_argument("--notes", default=None, help="版本说明")
    p_update.set_defaults(func=cmd_update)

    # list
    p_list = sub.add_parser("list", help="列出已注册 prompt")
    p_list.add_argument("--skill", default=None, help="按 skill 过滤(可选)")
    p_list.set_defaults(func=cmd_list)

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
