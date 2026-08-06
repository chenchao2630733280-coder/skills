#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全护栏 - diff 后置审查脚本。

识别风险变更:删除文件、大幅删减(>30% 行数减少)、配置文件变更、
依赖文件变更(package.json/requirements.txt/go.mod)。
输出含 riskChanges 列表的 guardrail-report.json。只读不写。

用法:
    python scripts/diff_review.py --before ./old --after ./new
    git diff HEAD~1 | python scripts/diff_review.py --diff -
"""

import argparse
import difflib
import json
import os
import re
import sys
from datetime import datetime


# 风险文件名/扩展名(配置类)
CONFIG_PATTERNS = [
    r".*\.ya?ml$",
    r".*\.env(\..*)?$",
    r".*\.toml$",
    r".*\.ini$",
    r".*config.*\.js$",
    r".*config.*\.ts$",
]

# 依赖文件名集合
DEPENDENCY_FILES = {
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
}


def is_config_file(path):
    """判断是否为配置文件。"""
    norm = path.replace("\\", "/")
    for pat in CONFIG_PATTERNS:
        try:
            if re.search(pat, norm):
                return True
        except re.error:
            continue
    return False


def is_dependency_file(path):
    """判断是否为依赖文件。"""
    name = os.path.basename(path)
    return name in DEPENDENCY_FILES


def read_lines(path):
    """安全读取文件行,失败返回空列表。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except Exception:
        return []


def review_file_pair(before_path, after_path):
    """对比单个文件 before/after,返回风险变更项列表。"""
    changes = []
    before_exists = os.path.isfile(before_path)
    after_exists = os.path.isfile(after_path)

    # 删除文件
    if before_exists and not after_exists:
        changes.append({
            "file": before_path,
            "change": "deleted",
            "severity": "high",
            "reason": "文件被删除",
        })
        return changes

    # 新增文件(仅依赖文件记为高风险)
    if not before_exists and after_exists:
        if is_dependency_file(after_path):
            changes.append({
                "file": after_path,
                "change": "added-dependency",
                "severity": "high",
                "reason": "新增依赖文件",
            })
        return changes

    if not before_exists or not after_exists:
        return changes

    before_lines = read_lines(before_path)
    after_lines = read_lines(after_path)

    # 大幅删减 >30%(且删多于增)
    before_count = max(len(before_lines), 1)
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    if before_count > 0 and removed / before_count > 0.30 and removed > added:
        changes.append({
            "file": before_path,
            "change": "large-reduction",
            "severity": "high",
            "reason": f"删减 {removed} 行,占原文件 {removed * 100 // before_count}%",
        })

    # 配置文件变更
    if is_config_file(before_path):
        changes.append({
            "file": before_path,
            "change": "config-changed",
            "severity": "medium",
            "reason": "配置文件发生变更",
        })

    # 依赖文件变更
    if is_dependency_file(before_path):
        changes.append({
            "file": before_path,
            "change": "dependency-changed",
            "severity": "high",
            "reason": "依赖文件发生变更",
        })

    return changes


def collect_pairs(before, after):
    """收集 before/after 的文件对(支持目录递归)。"""
    pairs = []
    if os.path.isfile(before) and os.path.isfile(after):
        pairs.append((before, after))
        return pairs
    if os.path.isdir(before) and os.path.isdir(after):
        before_files = {}
        for root, _, files in os.walk(before):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, before)
                before_files[rel] = full
        after_files = {}
        for root, _, files in os.walk(after):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, after)
                after_files[rel] = full
        all_rels = set(before_files.keys()) | set(after_files.keys())
        for rel in all_rels:
            b = before_files.get(rel, "")
            a = after_files.get(rel, "")
            # 缺失侧用占位路径,review_file_pair 会按不存在处理
            pairs.append((b or os.path.join(before, rel), a or os.path.join(after, rel)))
        return pairs
    # 一边文件一边目录:当作单文件对处理
    pairs.append((before, after))
    return pairs


def parse_git_diff(diff_text):
    """解析 git diff 文本,提取风险变更。

    识别:删除文件(deleted file mode)、配置/依赖文件变更、大幅删减。
    """
    changes = []
    lines = diff_text.splitlines()
    current_file = None
    removed = 0
    added = 0
    file_mode = "modified"

    def flush():
        """收尾上一个文件的统计。"""
        nonlocal current_file, removed, added, file_mode
        if current_file is None:
            return
        if file_mode == "deleted":
            changes.append({
                "file": current_file,
                "change": "deleted",
                "severity": "high",
                "reason": "git diff 显示文件被删除",
            })
        else:
            base = max(removed + added, 1)
            if removed > 0 and removed / base > 0.30 and removed > added:
                changes.append({
                    "file": current_file,
                    "change": "large-reduction",
                    "severity": "high",
                    "reason": f"删减 {removed} 行,占比 {removed * 100 // base}%",
                })
            if is_config_file(current_file):
                changes.append({
                    "file": current_file,
                    "change": "config-changed",
                    "severity": "medium",
                    "reason": "配置文件发生变更",
                })
            if is_dependency_file(current_file):
                changes.append({
                    "file": current_file,
                    "change": "dependency-changed",
                    "severity": "high",
                    "reason": "依赖文件发生变更",
                })
        current_file = None
        removed = 0
        added = 0
        file_mode = "modified"

    for line in lines:
        if line.startswith("diff --git"):
            flush()
            m = re.match(r"diff --git a/(.+?) b/(.+)", line)
            if m:
                current_file = m.group(2)
        elif line.startswith("deleted file mode"):
            file_mode = "deleted"
        elif line.startswith("new file mode"):
            file_mode = "added"
        elif line.startswith("+++ b/"):
            if current_file is None:
                current_file = line[6:]
        elif line.startswith("--- a/"):
            pass
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
    flush()
    return changes


def main():
    """入口:解析参数、审查 diff、写报告。"""
    parser = argparse.ArgumentParser(
        description="安全护栏 - diff 后置审查。识别删除/大幅删减/配置/依赖变更。",
    )
    parser.add_argument("--before", help="变更前目录或文件路径")
    parser.add_argument("--after", help="变更后目录或文件路径")
    parser.add_argument("--diff", help="git diff 文本文件路径(传 - 表示从 stdin 读取)")
    parser.add_argument(
        "--output",
        default="guardrail-report.json",
        help="报告输出路径(默认 guardrail-report.json)",
    )
    args = parser.parse_args()

    risk_changes = []
    warnings = []

    if args.diff:
        # git diff 模式
        if args.diff == "-":
            diff_text = sys.stdin.read()
        else:
            try:
                with open(args.diff, "r", encoding="utf-8", errors="replace") as f:
                    diff_text = f.read()
            except Exception as e:
                diff_text = ""
                warnings.append(f"guardrail-check-failed: 读取 diff 失败 {e}")
        risk_changes = parse_git_diff(diff_text)
    elif args.before and args.after:
        # before/after 模式
        if not os.path.exists(args.before):
            warnings.append(f"before 路径不存在: {args.before}")
        if not os.path.exists(args.after):
            warnings.append(f"after 路径不存在: {args.after}")
        pairs = collect_pairs(args.before, args.after)
        for b, a in pairs:
            risk_changes.extend(review_file_pair(b, a))
    else:
        parser.error("必须提供 --diff,或同时提供 --before 和 --after")

    # 汇总风险级别
    severity_rank = {"low": 0, "medium": 1, "high": 2}
    overall = "low"
    for ch in risk_changes:
        sev = ch.get("severity", "low")
        if severity_rank.get(sev, 0) > severity_rank.get(overall, 0):
            overall = sev
    # 仅"删除"类高风险直接 block,其余由编排总纲决策
    blocked = any(
        ch.get("severity") == "high" and ch.get("change") == "deleted"
        for ch in risk_changes
    )

    report = {
        "checkType": "diff-review",
        "operation": "diff",
        "paths": [args.before, args.after] if (args.before and args.after) else [],
        "riskLevel": overall,
        "blocked": blocked,
        "warnings": warnings,
        "riskChanges": risk_changes,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(2 if blocked else 0)


if __name__ == "__main__":
    main()
