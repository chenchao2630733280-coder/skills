#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全护栏 - 路径前置检查脚本。

根据操作类型(read/write/delete)和敏感路径清单,判定风险级别并输出
guardrail-report.json。该脚本只读不写,不修改任何被检查的文件。

用法:
    python scripts/check_paths.py --paths a,b --operation write
    python scripts/check_paths.py --operation delete --paths x --paths y
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# 默认敏感路径正则清单(可被项目级 .guardrail.yml 覆盖)
DEFAULT_SENSITIVE_PATTERNS = [
    # 生产配置
    r"config/production/.*\.ya?ml$",
    r".*\.env\.prod$",
    r"\.env\.production$",
    # 数据库
    r"migrations/.*",
    r".*schema\.sql$",
    r"db/init/.*",
    # 核心代码
    r"src/core/.*",
    r".*/main\.ts$",
    r"app/main\.py$",
    r"cmd/server/main\.go$",
    # 密钥
    r".*\.key$",
    r".*\.pem$",
    r".*id_rsa$",
    r".*credentials.*",
    r"^\.env$",
]


def load_sensitive_patterns(project_root=None):
    """加载敏感路径正则清单。

    优先读取项目根目录的 .guardrail.yml 中的 sensitive_patterns 列表;
    若不存在或解析失败,回退到内置默认清单。
    """
    # 默认清单
    patterns = list(DEFAULT_SENSITIVE_PATTERNS)
    if project_root is None:
        project_root = os.getcwd()
    cfg = Path(project_root) / ".guardrail.yml"
    if cfg.exists():
        try:
            # 简单解析 yml 中的 sensitive_patterns 列表(避免依赖第三方库)
            text = cfg.read_text(encoding="utf-8")
            in_block = False
            custom = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("sensitive_patterns:"):
                    in_block = True
                    continue
                if in_block:
                    if stripped.startswith("- "):
                        custom.append(stripped[2:].strip().strip('"').strip("'"))
                    elif stripped and not stripped.startswith("#"):
                        # 遇到非列表项,退出块
                        in_block = False
            if custom:
                patterns = custom
        except Exception:
            # 解析失败,回退默认清单
            patterns = list(DEFAULT_SENSITIVE_PATTERNS)
    return patterns


def is_sensitive(path, patterns):
    """判断给定路径是否匹配任一敏感正则。

    返回: (是否敏感, 命中的正则)
    """
    # 统一为正斜杠,便于跨平台匹配
    norm = path.replace("\\", "/")
    for pat in patterns:
        try:
            if re.search(pat, norm):
                return True, pat
        except re.error:
            # 跳过非法正则
            continue
    return False, None


def classify_risk(operation, sensitive):
    """按操作类型 + 是否敏感,判定风险级别。

    返回: (riskLevel, blocked, warning)
    """
    op = operation.lower()
    if op == "read":
        # 只读一律放行
        return "low", False, None
    if op == "write":
        if sensitive:
            return "high", False, "写入敏感路径需用户二次确认"
        return "low", False, None
    if op == "delete":
        if sensitive:
            return "forbidden", True, "禁止删除敏感路径"
        return "low", False, None
    # 未知操作降级为 low
    return "low", False, None


def build_report(check_type, operation, paths, risk_level, blocked, warnings, extra=None):
    """构造 guardrail-report.json 报告字典。"""
    report = {
        "checkType": check_type,
        "operation": operation,
        "paths": paths,
        "riskLevel": risk_level,
        "blocked": blocked,
        "warnings": warnings,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if extra:
        report.update(extra)
    return report


def main():
    """入口:解析参数、检查路径、写报告。"""
    parser = argparse.ArgumentParser(
        description="安全护栏 - 路径前置检查。判定 read/write/delete 风险级别。",
    )
    parser.add_argument(
        "--paths",
        action="append",
        help="待检查路径,逗号分隔或多次传入 --paths",
    )
    parser.add_argument(
        "--operation",
        choices=["read", "write", "delete"],
        required=True,
        help="操作类型",
    )
    parser.add_argument(
        "--output",
        default="guardrail-report.json",
        help="报告输出路径(默认 guardrail-report.json)",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="项目根目录(用于加载 .guardrail.yml),默认当前目录",
    )
    args = parser.parse_args()

    # 合并 paths(支持逗号分隔 + 多次 --paths)
    raw_paths = []
    if args.paths:
        for chunk in args.paths:
            for item in chunk.split(","):
                item = item.strip()
                if item:
                    raw_paths.append(item)

    patterns = load_sensitive_patterns(args.project_root)

    warnings = []
    overall_risk = "low"
    overall_blocked = False
    for p in raw_paths:
        sensitive, matched = is_sensitive(p, patterns)
        if not os.path.exists(p):
            # 路径不存在,记录但不阻断
            warnings.append(f"{p}: 路径不存在,按 low 处理")
        risk, blocked, warning = classify_risk(args.operation, sensitive)
        # 升级总体风险级别
        severity_order = {"low": 0, "high": 1, "forbidden": 2}
        if severity_order.get(risk, 0) > severity_order.get(overall_risk, 0):
            overall_risk = risk
        if blocked:
            overall_blocked = True
        if warning:
            warnings.append(f"{p}: {warning} (匹配规则: {matched})")

    report = build_report(
        "path-check",
        args.operation,
        raw_paths,
        overall_risk,
        overall_blocked,
        warnings,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 控制台简要输出
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # forbidden 时以退出码 2 提示编排总纲
    sys.exit(2 if overall_blocked else 0)


if __name__ == "__main__":
    main()
