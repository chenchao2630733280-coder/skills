#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""git_ops.py - Git 工具层操作封装。

封装 commit / branch / push / diff / log 五个子命令,
统一产出 git-ops-report.json,失败不抛异常,不阻塞编排总纲。
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 把本脚本所在目录加入搜索路径,保证既能直接运行也能被 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_commit_message import generate_commit_message  # noqa: E402

# 黑名单路径模式:命中则不 add / 不 commit
BLACKLIST = (".env", "credentials.json", ".key", ".pem", "id_rsa")


def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _is_blacklisted(path):
    """判断给定路径是否命中黑名单。

    覆盖: .env / *.env、credentials.json、*.key、*.pem、id_rsa / id_rsa.*
    """
    p = path.lower()
    name = os.path.basename(p)
    if name == "id_rsa" or name.startswith("id_rsa."):
        return True
    if name == ".env" or name.endswith(".env"):
        return True
    if name == "credentials.json":
        return True
    if p.endswith(".key") or p.endswith(".pem"):
        return True
    return False


def _filter_blacklist(paths):
    """过滤掉黑名单路径,返回 (合法路径, 命中路径) 两个列表。"""
    safe, blocked = [], []
    for p in paths:
        if _is_blacklisted(p):
            blocked.append(p)
        else:
            safe.append(p)
    return safe, blocked


def _parse_paths(raw):
    """把原始 --paths 输入(支持逗号分隔与多次传入)解析为干净列表。"""
    result = []
    for item in raw:
        for part in item.split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result


def _run_git(args, repo):
    """执行 git 命令,返回 (returncode, stdout, stderr)。失败不抛异常。"""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git executable not found"
    except Exception as exc:  # noqa: BLE001 - 兜底,失败不阻塞
        return 1, "", str(exc)


def _is_git_repo(repo):
    """判断 repo 是否为 git 仓库。"""
    code, _, _ = _run_git(["rev-parse", "--is-inside-work-tree"], repo)
    return code == 0


def _current_branch(repo):
    """获取当前分支名,失败返回 None。"""
    code, out, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    return out if code == 0 else None


def _write_report(report, target_dir=None):
    """将报告写入当前目录(或指定目录)的 git-ops-report.json。"""
    out_dir = Path(target_dir) if target_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "git-ops-report.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return str(report_path)


def _base_report(command):
    """构造初始报告字典。"""
    return {
        "command": command,
        "files": [],
        "commitHash": None,
        "branch": None,
        "pushed": False,
        "error": None,
        "timestamp": _now_iso(),
    }


def cmd_commit(args):
    """commit 子命令:add 指定路径并提交。"""
    report = _base_report("commit")
    repo = args.repo

    if not _is_git_repo(repo):
        report["error"] = "not a git repository"
        _write_report(report)
        return report

    # 解析路径并做黑名单过滤
    raw_paths = _parse_paths(args.paths)
    safe, blocked = _filter_blacklist(raw_paths)
    report["files"] = safe
    if blocked:
        sys.stderr.write("blocked by blacklist: %s\n" % ", ".join(blocked))
    if not safe:
        report["error"] = "all paths blocked by blacklist" if raw_paths else "no paths provided"
        _write_report(report)
        return report

    # 仅 add 指定路径,绝不 add 全部
    add_code, _, add_err = _run_git(["add", "--"] + safe, repo)
    if add_code != 0:
        report["error"] = "git add failed: %s" % add_err
        _write_report(report)
        return report

    # 生成 commit message:未传则自动生成
    message = args.message if args.message else generate_commit_message(safe)

    c_code, c_out, c_err = _run_git(["commit", "-m", message], repo)
    combined = (c_out + "\n" + c_err).lower()
    if c_code != 0:
        # 无变更时 git commit 返回非 0,视为正常无 hash
        if "nothing to commit" in combined or "no changes" in combined:
            report["error"] = None
        else:
            report["error"] = "git commit failed: %s" % (c_err or c_out)
    else:
        h_code, h_out, _ = _run_git(["rev-parse", "--short", "HEAD"], repo)
        if h_code == 0:
            report["commitHash"] = h_out

    report["branch"] = _current_branch(repo)
    _write_report(report)
    return report


def cmd_branch(args):
    """branch 子命令:创建并切换到新分支。"""
    report = _base_report("branch")
    repo = args.repo

    if not _is_git_repo(repo):
        report["error"] = "not a git repository"
        _write_report(report)
        return report

    b_code, b_out, b_err = _run_git(["checkout", "-b", args.name], repo)
    if b_code != 0:
        report["error"] = "git checkout -b failed: %s" % (b_err or b_out)
    else:
        report["branch"] = args.name
    _write_report(report)
    return report


def cmd_push(args):
    """push 子命令:需 --confirm 才真正推送。"""
    report = _base_report("push")
    repo = args.repo

    if not _is_git_repo(repo):
        report["error"] = "not a git repository"
        _write_report(report)
        return report

    # 安全门:缺少 --confirm 不执行真实推送
    if not args.confirm:
        report["error"] = "push requires --confirm to execute"
        report["pushed"] = False
        _write_report(report)
        return report

    p_code, p_out, p_err = _run_git(["push", args.remote], repo)
    if p_code != 0:
        report["error"] = "git push failed: %s" % (p_err or p_out)
        report["pushed"] = False
    else:
        report["pushed"] = True
    report["branch"] = _current_branch(repo)
    _write_report(report)
    return report


def cmd_diff(args):
    """diff 子命令:只读,展示差异文本(输出到 stdout)。"""
    report = _base_report("diff")
    repo = args.repo

    if not _is_git_repo(repo):
        report["error"] = "not a git repository"
        _write_report(report)
        return report

    git_args = ["diff"]
    if args.paths:
        paths = _parse_paths(args.paths)
        safe, blocked = _filter_blacklist(paths)
        report["files"] = safe
        if blocked:
            sys.stderr.write("blocked by blacklist: %s\n" % ", ".join(blocked))
        if safe:
            git_args += ["--"] + safe
    d_code, d_out, d_err = _run_git(git_args, repo)
    if d_code != 0:
        report["error"] = "git diff failed: %s" % (d_err or d_out)
    else:
        report["error"] = None
        sys.stdout.write(d_out + "\n")
    _write_report(report)
    return report


def cmd_log(args):
    """log 子命令:只读,展示提交历史(输出到 stdout)。"""
    report = _base_report("log")
    repo = args.repo

    if not _is_git_repo(repo):
        report["error"] = "not a git repository"
        _write_report(report)
        return report

    l_code, l_out, l_err = _run_git(["log", "-n", str(args.limit)], repo)
    if l_code != 0:
        report["error"] = "git log failed: %s" % (l_err or l_out)
    else:
        report["error"] = None
        sys.stdout.write(l_out + "\n")
    _write_report(report)
    return report


def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="git_ops.py",
        description="Git 工具层:封装 commit/branch/push/diff/log,统一产出 git-ops-report.json",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # commit 子命令
    p_commit = sub.add_parser("commit", help="add 指定路径并提交(自动生成 message 或使用 --message)")
    p_commit.add_argument("--paths", nargs="+", required=True, help="要提交的路径列表,支持逗号分隔或多次传入")
    p_commit.add_argument("--message", default=None, help="commit message,不传则自动生成")
    p_commit.add_argument("--repo", default=".", help="git 仓库路径,默认当前目录")
    p_commit.set_defaults(func=cmd_commit)

    # branch 子命令
    p_branch = sub.add_parser("branch", help="创建并切换到新分支")
    p_branch.add_argument("--name", required=True, help="新分支名")
    p_branch.add_argument("--repo", default=".", help="git 仓库路径,默认当前目录")
    p_branch.set_defaults(func=cmd_branch)

    # push 子命令
    p_push = sub.add_parser("push", help="推送到远端(需 --confirm 才执行)")
    p_push.add_argument("--repo", default=".", help="git 仓库路径,默认当前目录")
    p_push.add_argument("--remote", default="origin", help="远端名,默认 origin")
    p_push.add_argument("--confirm", action="store_true", help="确认执行 push(安全门)")
    p_push.set_defaults(func=cmd_push)

    # diff 子命令
    p_diff = sub.add_parser("diff", help="查看差异(只读)")
    p_diff.add_argument("--repo", default=".", help="git 仓库路径,默认当前目录")
    p_diff.add_argument("--paths", nargs="+", default=None, help="可选路径列表,支持逗号分隔")
    p_diff.set_defaults(func=cmd_diff)

    # log 子命令
    p_log = sub.add_parser("log", help="查看提交历史(只读)")
    p_log.add_argument("--repo", default=".", help="git 仓库路径,默认当前目录")
    p_log.add_argument("--limit", type=int, default=10, help="显示条数,默认 10")
    p_log.set_defaults(func=cmd_log)

    return parser


def main():
    """入口函数:解析参数并分发到对应子命令。"""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
