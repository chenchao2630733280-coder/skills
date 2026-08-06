#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_review.py - 变更 diff 后置审查脚本

审查产物变更的 diff,识别删除文件、大幅删减、配置变更、依赖变更、密钥变更等风险操作,
产出 diff-review-report.md(人读)与 diff-review-report.json(机读)。

只读不写:本脚本不修改任何被审查的文件,仅产出审查报告。

仅依赖 Python 标准库(difflib/json/os/sys/argparse/datetime/subprocess/re/pathlib)。
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ========== 风险规则定义 ==========

# 风险变更类型 -> 严重级别
RISK_RULES = {
    "deleted_file": {
        "severity": "high",
        "label": "删除文件",
        "description": "变更中删除了已存在的文件",
    },
    "large_reduction": {
        "severity": "high",
        "label": "大幅删减",
        "description": "单文件行数减少超过 30%",
    },
    "config_change": {
        "severity": "medium",
        "label": "配置文件变更",
        "description": "yml/yaml/json/toml 等配置文件被修改",
    },
    "dependency_change": {
        "severity": "high",
        "label": "依赖变更",
        "description": "package.json/requirements.txt/go.mod/pom.xml 等依赖文件被修改",
    },
    "secret_change": {
        "severity": "critical",
        "label": "密钥文件变更",
        "description": "*.key/*.pem/.env* 等密钥或环境文件被修改",
    },
}

# 配置文件后缀(大小写不敏感)
CONFIG_PATTERNS = re.compile(r"\.(yml|yaml|json|toml|ini|cfg|conf)$", re.IGNORECASE)

# 依赖文件名集合
DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "yarn.lock",
    "requirements.txt", "Pipfile", "Pipfile.lock",
    "go.mod", "go.sum",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Cargo.toml", "Cargo.lock",
}

# 密钥/环境文件模式(大小写不敏感)
SECRET_PATTERNS = re.compile(
    r"(\.key$|\.pem$|\.pfx$|\.p12$|\.env|id_rsa|id_ecdsa|credentials\.json$)",
    re.IGNORECASE,
)

# 大幅删减阈值:行数减少比例 > 30%
REDUCTION_THRESHOLD = 0.30


# ========== 规则匹配函数 ==========

def match_config(path):
    """判断路径是否为配置文件。"""
    return bool(CONFIG_PATTERNS.search(path))


def match_dependency(path):
    """判断路径是否为依赖文件。"""
    return os.path.basename(path) in DEPENDENCY_FILES


def match_secret(path):
    """判断路径是否为密钥或环境文件。"""
    return bool(SECRET_PATTERNS.search(path))


# ========== diff 解析 ==========

def parse_diff(diff_text):
    """
    解析 unified diff 文本(兼容 git diff 输出),返回变更条目列表。

    每个条目结构:
        {
            "path": str,        # 变更后路径(删除文件用旧路径)
            "old_path": str,    # 变更前路径
            "status": str,      # added / modified / deleted / renamed
            "added": int,       # 新增行数(不含 +++ 头)
            "removed": int,     # 删除行数(不含 --- 头)
            "old_total": int,   # hunk header 累计的原文件行数
            "new_total": int,   # hunk header 累计的新文件行数
        }
    """
    entries = []
    if not diff_text:
        return entries

    # 按 "diff --git" 头切片
    splits = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    header_re = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)

    for chunk in splits:
        if not chunk.startswith("diff --git"):
            continue
        hm = header_re.match(chunk)
        if not hm:
            continue
        old_path, new_path = hm.group(1), hm.group(2)

        # 统计增删行(排除 +++ / --- 头)
        # ^\+(?!\+) 匹配 + 开头但非 ++,即排除 +++
        added = len(re.findall(r"^\+(?!\+)", chunk, re.MULTILINE))
        removed = len(re.findall(r"^-(?!-)", chunk, re.MULTILINE))

        # 判断状态
        if re.search(r"^new file mode", chunk, re.MULTILINE):
            status = "added"
        elif re.search(r"^deleted file mode", chunk, re.MULTILINE):
            status = "deleted"
        elif re.search(r"^rename from", chunk, re.MULTILINE):
            status = "renamed"
        else:
            status = "modified"

        # 从 hunk header 累计 old/new 行数,用于估算删减比例
        old_total = 0
        new_total = 0
        for m in hunk_re.finditer(chunk):
            oc = int(m.group(2)) if m.group(2) else 1
            nc = int(m.group(4)) if m.group(4) else 1
            old_total += oc
            new_total += nc

        entries.append({
            "path": new_path if status != "deleted" else old_path,
            "old_path": old_path,
            "status": status,
            "added": added,
            "removed": removed,
            "old_total": old_total,
            "new_total": new_total,
        })
    return entries


def compute_reduction(entry):
    """
    根据 hunk header 的 old/new 行数估算单文件删减比例。

    删减比例 = (old_total - new_total) / old_total。
    若 old_total 为 0(无 hunk 信息)返回 0.0。
    """
    old_total = entry.get("old_total", 0)
    new_total = entry.get("new_total", 0)
    if old_total == 0:
        return 0.0
    return max((old_total - new_total) / old_total, 0.0)


# ========== 风险审查 ==========

def review_entries(entries):
    """根据风险规则审查变更条目,返回风险变更清单。"""
    risks = []
    for e in entries:
        path = e["path"]
        status = e["status"]

        # 1. 删除文件(标 high),命中后不再叠加其他规则
        if status == "deleted":
            risks.append({
                "type": "deleted_file",
                "file": path,
                "severity": RISK_RULES["deleted_file"]["severity"],
                "detail": "删除文件: {}".format(path),
            })
            continue

        # 2. 大幅删减(仅对 modified / renamed 判断)
        if status in ("modified", "renamed"):
            ratio = compute_reduction(e)
            if ratio > REDUCTION_THRESHOLD:
                risks.append({
                    "type": "large_reduction",
                    "file": path,
                    "severity": RISK_RULES["large_reduction"]["severity"],
                    "detail": "大幅删减: 行数减少约 {:.1f}% (added={}, removed={})".format(
                        ratio * 100, e["added"], e["removed"]),
                })

        # 3-5. 配置 / 依赖 / 密钥(对所有变更状态均判断,新增密钥同样是风险)
        # 优先级:密钥(critical)> 依赖(high)> 配置(medium),每文件至多命中一类
        if match_secret(path):
            risks.append({
                "type": "secret_change",
                "file": path,
                "severity": RISK_RULES["secret_change"]["severity"],
                "detail": "密钥/环境文件变更: {} ({})".format(path, status),
            })
        elif match_dependency(path):
            risks.append({
                "type": "dependency_change",
                "file": path,
                "severity": RISK_RULES["dependency_change"]["severity"],
                "detail": "依赖文件变更: {} ({})".format(path, status),
            })
        elif match_config(path):
            risks.append({
                "type": "config_change",
                "file": path,
                "severity": RISK_RULES["config_change"]["severity"],
                "detail": "配置文件变更: {} ({})".format(path, status),
            })
    return risks


# ========== diff 生成(--before/--after 模式)==========

def build_diff_from_paths(before, after):
    """对比两个目录或文件,生成 unified diff 文本(带 diff --git 头)。"""
    before_p = Path(before)
    after_p = Path(after)
    if before_p.is_file() and after_p.is_file():
        return _diff_two_files(before_p, after_p, before, after)
    if before_p.is_dir() and after_p.is_dir():
        return _diff_two_dirs(before_p, after_p)
    raise ValueError("--before 与 --after 必须同为目录或同为文件")


def _read_lines(p):
    """读取文件行(保留换行符),读失败返回空列表。"""
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except Exception:
        return []


def _diff_two_files(before_p, after_p, before, after):
    """对比两个文件,产出 unified diff。"""
    bl = _read_lines(before_p)
    al = _read_lines(after_p)
    diff = difflib.unified_diff(bl, al, fromfile="a/{}".format(before), tofile="b/{}".format(after))
    body = "".join(diff)
    if not body:
        return ""
    return "diff --git a/{} b/{}\n{}".format(before, after, body)


def _diff_two_dirs(before_p, after_p):
    """对比两个目录,逐文件产出 unified diff(带 diff --git 头)。"""
    before_files = {
        str(p.relative_to(before_p)).replace("\\", "/"): p
        for p in before_p.rglob("*") if p.is_file()
    }
    after_files = {
        str(p.relative_to(after_p)).replace("\\", "/"): p
        for p in after_p.rglob("*") if p.is_file()
    }
    all_keys = sorted(set(before_files) | set(after_files))
    out = []
    for key in all_keys:
        bf = before_files.get(key)
        af = after_files.get(key)
        if bf and af:
            bl = _read_lines(bf)
            al = _read_lines(af)
            diff = difflib.unified_diff(bl, al, fromfile="a/{}".format(key), tofile="b/{}".format(key))
            body = "".join(diff)
            if body:
                out.append("diff --git a/{} b/{}\n{}".format(key, key, body))
        elif bf and not af:
            # 删除文件
            out.append("diff --git a/{} b/{}\n".format(key, key))
            out.append("deleted file mode 100644\n")
            out.append("--- a/{}\n".format(key))
            out.append("+++ /dev/null\n")
            for line in _read_lines(bf):
                out.append("-" + line if line.endswith("\n") else "-" + line + "\n")
        elif af and not bf:
            # 新增文件
            out.append("diff --git a/{} b/{}\n".format(key, key))
            out.append("new file mode 100644\n")
            out.append("--- /dev/null\n")
            out.append("+++ b/{}\n".format(key))
            for line in _read_lines(af):
                out.append("+" + line if line.endswith("\n") else "+" + line + "\n")
    return "".join(out)


# ========== git staged 模式 ==========

def get_git_staged_diff():
    """运行 git diff --cached,返回 diff 文本。失败返回空串。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--no-color"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (FileNotFoundError, OSError):
        return ""


# ========== 报告产出 ==========

def build_summary(risks):
    """根据风险清单汇总统计。"""
    summary = {"total": len(risks), "high": 0, "medium": 0, "critical": 0}
    for r in risks:
        sev = r["severity"]
        if sev in summary:
            summary[sev] += 1
    return summary


def write_reports(risks, summary, parse_failed=False, note=""):
    """产出 diff-review-report.md 与 diff-review-report.json 到当前工作目录。"""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # ----- JSON 机读报告 -----
    report_json = {
        "riskChanges": risks,
        "summary": summary,
        "timestamp": timestamp,
    }
    if parse_failed:
        report_json["parseFailed"] = True
    if note:
        report_json["note"] = note
    with open("diff-review-report.json", "w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)

    # ----- Markdown 人读报告 -----
    lines = []
    lines.append("# diff-reviewer 变更审查报告")
    lines.append("")
    lines.append("- 生成时间: {}".format(timestamp))
    lines.append("- 模式: 只读审查,不修改任何被审查文件")
    if parse_failed:
        lines.append("- ⚠️ diff 解析失败,已降级处理")
    if note:
        lines.append("- 备注: {}".format(note))
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("| --- | --- |")
    lines.append("| 风险变更总数 | {} |".format(summary["total"]))
    lines.append("| critical(密钥) | {} |".format(summary["critical"]))
    lines.append("| high(删除/大幅删减/依赖) | {} |".format(summary["high"]))
    lines.append("| medium(配置) | {} |".format(summary["medium"]))
    lines.append("")

    lines.append("## 风险变更清单")
    lines.append("")
    if parse_failed and not risks:
        lines.append("> 无法自动审查,建议人工 review。")
        lines.append("")
    elif not risks:
        lines.append("未识别到风险变更。")
        lines.append("")
    else:
        lines.append("| # | 严重级别 | 类型 | 文件 | 详情 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for i, r in enumerate(risks, 1):
            lines.append("| {} | {} | {} | {} | {} |".format(
                i, r["severity"], r["type"], r["file"], r["detail"]))
        lines.append("")

    lines.append("## 处置建议")
    lines.append("")
    if summary["critical"] > 0:
        lines.append("- 🔴 critical:存在密钥/凭证文件变更,建议立即人工介入,确认是否误提交或泄露。")
    if summary["high"] > 0:
        lines.append("- 🟠 high:存在删除文件 / 大幅删减 / 依赖变更,建议人工确认变更意图,防止误删。")
    if summary["medium"] > 0:
        lines.append("- 🟡 medium:存在配置文件变更,建议复核配置项,防止环境差异。")
    if summary["total"] == 0 and not parse_failed:
        lines.append("- 未发现风险变更,可继续后续流程。")
    lines.append("")

    with open("diff-review-report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ========== 主流程 ==========

def parse_args(argv=None):
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="diff_review.py",
        description="变更 diff 后置审查:识别删除/大幅删减/配置/依赖/密钥等风险变更,只读不写。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python scripts/diff_review.py --before ./before_dir --after ./after_dir\n"
            "  python scripts/diff_review.py --before old.txt --after new.txt\n"
            "  python scripts/diff_review.py --diff my.diff\n"
            "  python scripts/diff_review.py --git-staged\n"
        ),
    )
    parser.add_argument("--before", help="旧版本路径(目录或文件),需与 --after 同时使用")
    parser.add_argument("--after", help="新版本路径(目录或文件),需与 --before 同时使用")
    parser.add_argument("--diff", help="diff 文本文件路径(unified diff 格式)")
    parser.add_argument("--git-staged", action="store_true", help="审查已 staged 的变更(自动跑 git diff --cached)")
    return parser.parse_args(argv)


def main(argv=None):
    """脚本入口:解析参数、获取 diff、审查风险、产出报告。"""
    args = parse_args(argv)

    # 校验参数组合
    modes = [
        bool(args.before and args.after),
        bool(args.diff),
        bool(args.git_staged),
    ]
    if sum(modes) == 0:
        print("错误: 必须指定一种输入模式(--before/--after、--diff 或 --git-staged)", file=sys.stderr)
        print("运行 --help 查看用法。", file=sys.stderr)
        return 2
    if sum(modes) > 1:
        print("错误: 三种输入模式互斥,请仅指定一种", file=sys.stderr)
        return 2
    if (args.before is None) != (args.after is None):
        print("错误: --before 与 --after 必须同时指定", file=sys.stderr)
        return 2

    diff_text = ""
    parse_failed = False
    note = ""

    try:
        if args.before and args.after:
            # --before/--after 模式
            if not os.path.exists(args.before):
                print("错误: --before 路径不存在: {}".format(args.before), file=sys.stderr)
                return 2
            if not os.path.exists(args.after):
                print("错误: --after 路径不存在: {}".format(args.after), file=sys.stderr)
                return 2
            diff_text = build_diff_from_paths(args.before, args.after)
        elif args.diff:
            # --diff 文本文件模式
            if not os.path.exists(args.diff):
                print("错误: --diff 文件不存在: {}".format(args.diff), file=sys.stderr)
                return 2
            with open(args.diff, "r", encoding="utf-8", errors="replace") as f:
                diff_text = f.read()
        elif args.git_staged:
            # --git-staged 模式
            diff_text = get_git_staged_diff()
            if not diff_text:
                parse_failed = True
                note = "git diff --cached 无输出或非 git 仓库,无法自动审查"
    except ValueError as e:
        # --before/--after 类型不匹配
        print("错误: {}".format(e), file=sys.stderr)
        return 2
    except Exception as e:
        # 其他异常降级处理
        parse_failed = True
        note = "获取 diff 失败: {}".format(e)

    # 解析 diff
    entries = []
    if diff_text:
        try:
            entries = parse_diff(diff_text)
            if not entries and diff_text.strip():
                parse_failed = True
                note = note or "diff 可解析但未识别到标准 diff --git 条目,建议人工 review"
        except Exception as e:
            parse_failed = True
            note = "diff 解析失败: {},建议人工 review".format(e)

    # 审查风险
    risks = review_entries(entries)
    summary = build_summary(risks)

    # 产出报告
    write_reports(risks, summary, parse_failed=parse_failed, note=note)

    # 控制台摘要
    print("diff-reviewer 审查完成:")
    print("  风险变更: {} (critical={}, high={}, medium={})".format(
        summary["total"], summary["critical"], summary["high"], summary["medium"]))
    if parse_failed:
        print("  ⚠️ 已降级: {}".format(note))
    print("  报告: diff-review-report.md / diff-review-report.json")
    return 0


if __name__ == "__main__":
    main()
