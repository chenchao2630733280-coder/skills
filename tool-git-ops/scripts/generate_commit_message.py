#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_commit_message.py - 自动生成 commit message。

接收路径列表,返回形如 `[auto] update {dir_summary} ({n} files)` 的字符串。
可被 git_ops.py import,也可独立运行测试。
"""

import os
import sys


def _dir_summary(paths):
    """从路径列表中提取目录摘要。

    取所有路径的公共父目录,再取其最末一级目录名作为摘要;
    无法推断时退回到 'artifacts'。
    """
    if not paths:
        return "artifacts"

    # 规范化路径,取父目录;顶层文件父目录记为 '.'
    parents = []
    for p in paths:
        norm = os.path.normpath(p)
        parent = os.path.dirname(norm)
        parents.append(parent if parent else ".")

    # 求公共前缀目录,混合绝对/相对路径时退回到首个父目录
    try:
        common = os.path.commonpath(parents) if len(parents) > 1 else parents[0]
    except ValueError:
        common = parents[0]

    # 统一斜杠,去掉前后分隔符与 '.'
    common = common.replace("\\", "/").strip("/")
    parts = [seg for seg in common.split("/") if seg and seg != "."]
    if not parts:
        return "artifacts"
    # 取最末一级目录名,避免摘要过长
    return parts[-1]


def generate_commit_message(paths):
    """根据路径列表生成 commit message。

    格式: `[auto] update {dir_summary} ({n} files)`
      - dir_summary:路径公共父目录最末一级名
      - n:实际文件数

    Args:
        paths: 路径字符串列表。

    Returns:
        形如 `[auto] update dist (3 files)` 的 commit message 字符串。
    """
    if not paths:
        return "[auto] update artifacts (0 files)"
    summary = _dir_summary(paths)
    return "[auto] update %s (%d files)" % (summary, len(paths))


def main():
    """独立运行入口:从命令行参数读取路径并打印生成的 commit message。"""
    paths = sys.argv[1:] if len(sys.argv) > 1 else []
    print(generate_commit_message(paths))


if __name__ == "__main__":
    main()
