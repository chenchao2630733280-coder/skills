#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI/CD 工具层操作脚本.

封装三类操作:
  - trigger: 触发 CI 构建(变更类,需 --confirm)
  - status:  查询构建状态(running / success / failed)
  - report:  读取测试报告

支持平台: github-actions / gitlab-ci / jenkins
仅依赖 Python 标准库.平台配置从环境变量读取.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


# 支持的 CI 平台
SUPPORTED_PLATFORMS = ("github-actions", "gitlab-ci", "jenkins")

# 输出报告文件名
REPORT_FILE = "ci-ops-report.json"


def _now_timestamp():
    """返回 ISO8601 格式(精度到秒)的当前时间戳."""
    return datetime.now().isoformat(timespec="seconds")


def _empty_test_results():
    """返回测试结果的空结构."""
    return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}


def _new_payload(command, platform, repo, branch=None):
    """构造初始报告 payload."""
    return {
        "command": command,
        "platform": platform,
        "repo": repo,
        "branch": branch,
        "runId": None,
        "status": None,
        "testResults": None,
        "error": None,
        "timestamp": _now_timestamp(),
    }


def _write_report(payload):
    """将结果写入 ci-ops-report.json 并打印路径.

    返回写入的文件绝对路径.
    """
    # 强制刷新时间戳,反映完成时刻
    payload["timestamp"] = _now_timestamp()
    path = os.path.join(os.getcwd(), REPORT_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("[ci-ops] 报告已写入: {}".format(path))
    return path


def _check_cli(tool):
    """检查指定 CLI 工具是否在 PATH 中可用,返回布尔值."""
    # Windows 用 where,类 Unix 用 which
    checker = "where" if os.name == "nt" else "which"
    try:
        result = subprocess.run(
            [checker, tool],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.returncode == 0
    except Exception:
        return False


def _platform_env_ok(platform):
    """检查平台所需环境变量是否就绪,返回布尔值."""
    if platform == "github-actions":
        return bool(os.environ.get("GITHUB_TOKEN"))
    if platform == "gitlab-ci":
        return bool(os.environ.get("GITLAB_TOKEN"))
    if platform == "jenkins":
        return all([
            os.environ.get("JENKINS_URL"),
            os.environ.get("JENKINS_USER"),
            os.environ.get("JENKINS_TOKEN"),
        ])
    return False


def _env_hint(platform):
    """返回平台所需环境变量的设置提示文本."""
    if platform == "github-actions":
        return "    export GITHUB_TOKEN=<your-token>"
    if platform == "gitlab-ci":
        return "    export GITLAB_TOKEN=<your-token>"
    if platform == "jenkins":
        return (
            "    export JENKINS_URL=<url>\n"
            "    export JENKINS_USER=<user>\n"
            "    export JENKINS_TOKEN=<token>"
        )
    return ""


def _degrade_hint(cmd_text, platform):
    """平台 CLI 或环境变量不可用时的降级提示.

    打印待手动执行的命令及环境变量配置说明.
    """
    print("[ci-ops] 平台 CLI 或环境变量不可用: {}".format(platform))
    print("[ci-ops] 请手动执行以下命令:")
    print("    " + cmd_text)
    print("[ci-ops] 环境变量参考:")
    print(_env_hint(platform))


def _build_trigger_command(platform, repo, branch):
    """根据平台构造触发命令(返回命令列表与文本)."""
    if platform == "github-actions":
        cmd = ["gh", "workflow", "run", repo, "--ref", branch]
        cmd_text = "gh workflow run {} --ref {}".format(repo, branch)
    elif platform == "gitlab-ci":
        cmd = ["glab", "ci", "trigger", "--repo", repo, "--branch", branch]
        cmd_text = "glab ci trigger --repo {} --branch {}".format(repo, branch)
    elif platform == "jenkins":
        # repo 视为 Jenkins job 名称
        cmd = ["jenkins-cli", "build", repo, "-p", "BRANCH=" + branch]
        cmd_text = "jenkins-cli build {} -p BRANCH={}".format(repo, branch)
    else:
        return None, None
    return cmd, cmd_text


def _build_status_command(platform, repo, run_id):
    """根据平台构造状态查询命令(返回命令列表与文本)."""
    if platform == "github-actions":
        if run_id:
            cmd = ["gh", "run", "view", run_id, "--repo", repo]
            cmd_text = "gh run view {} --repo {}".format(run_id, repo)
        else:
            cmd = ["gh", "run", "list", "--repo", repo, "--limit", "1"]
            cmd_text = "gh run list --repo {} --limit 1".format(repo)
    elif platform == "gitlab-ci":
        if run_id:
            cmd = ["glab", "ci", "view", run_id, "--repo", repo]
            cmd_text = "glab ci view {} --repo {}".format(run_id, repo)
        else:
            cmd = ["glab", "ci", "list", "--repo", repo]
            cmd_text = "glab ci list --repo {}".format(repo)
    elif platform == "jenkins":
        cmd = ["jenkins-cli", "last-build-status", repo]
        cmd_text = "jenkins-cli last-build-status {}".format(repo)
    else:
        return None, None
    return cmd, cmd_text


def _build_report_command(platform, repo, run_id):
    """根据平台构造测试报告读取命令(返回命令列表与文本)."""
    if platform == "github-actions":
        if run_id:
            cmd = ["gh", "run", "view", run_id, "--repo", repo, "--log"]
            cmd_text = "gh run view {} --repo {} --log".format(run_id, repo)
        else:
            cmd = ["gh", "run", "view", "--repo", repo, "--log"]
            cmd_text = "gh run view --repo {} --log".format(repo)
    elif platform == "gitlab-ci":
        if run_id:
            cmd = ["glab", "ci", "trace", run_id, "--repo", repo]
            cmd_text = "glab ci trace {} --repo {}".format(run_id, repo)
        else:
            cmd = ["glab", "ci", "trace", "--repo", repo]
            cmd_text = "glab ci trace --repo {}".format(repo)
    elif platform == "jenkins":
        cmd = ["jenkins-cli", "console", repo]
        cmd_text = "jenkins-cli console {}".format(repo)
    else:
        return None, None
    return cmd, cmd_text


def _parse_status_from_output(text):
    """从 CLI 输出文本中推断构建状态.

    返回 running / success / failed 之一;无法判定时返回 unknown.
    """
    lower = text.lower()
    if "success" in lower or "passed" in lower or "completed" in lower:
        return "success"
    if "fail" in lower or "error" in lower:
        return "failed"
    if "running" in lower or "in progress" in lower or "pending" in lower:
        return "running"
    return "unknown"


def _parse_test_results_from_output(text):
    """从测试日志文本中解析测试统计(简单启发式)."""
    results = _empty_test_results()
    lower = text.lower()
    # 简单关键词解析,适配常见测试框架输出
    for line in text.splitlines():
        low = line.lower()
        if "passed" in low and "total" not in low:
            results["passed"] = _extract_number(low, "passed") or results["passed"]
        if "failed" in low and "total" not in low:
            results["failed"] = _extract_number(low, "failed") or results["failed"]
        if "skipped" in low:
            results["skipped"] = _extract_number(low, "skipped") or results["skipped"]
        if "total" in low:
            results["total"] = _extract_number(low, "total") or results["total"]
    # 兜底:若 total 为 0 但有 passed,则用 passed 推算
    if results["total"] == 0:
        results["total"] = results["passed"] + results["failed"] + results["skipped"]
    return results


def _extract_number(text, keyword):
    """从文本中提取关键词前的数字(如 '5 passed')."""
    parts = text.split()
    for idx, part in enumerate(parts):
        if part == keyword or part.startswith(keyword):
            # 向前找最近的数字
            back = idx - 1
            while back >= 0:
                token = parts[back].strip(",:;")
                if token.isdigit():
                    return int(token)
                back -= 1
            # 向后找
            fwd = idx + 1
            while fwd < len(parts):
                token = parts[fwd].strip(",:;")
                if token.isdigit():
                    return int(token)
                fwd += 1
    return 0


def _run_cli(cmd):
    """执行 CLI 命令,返回(returncode, stdout, stderr)三元组."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out = result.stdout.decode("utf-8", errors="replace")
    err = result.stderr.decode("utf-8", errors="replace")
    return result.returncode, out, err


def cmd_trigger(args):
    """触发 CI 构建.

    - 未提供 --confirm:仅打印命令(dry-run)
    - 提供 --confirm 且平台就绪:调用对应 CLI 触发
    - 平台不可用:降级为手动提示
    """
    platform = args.platform
    repo = args.repo
    branch = args.branch or "main"
    payload = _new_payload("trigger", platform, repo, branch)

    cmd, cmd_text = _build_trigger_command(platform, repo, branch)
    if cmd is None:
        payload["error"] = "不支持的平台: {}".format(platform)
        payload["status"] = "failed"
        print("[ci-ops] " + payload["error"])
        _write_report(payload)
        return 1

    # 未确认:仅打印命令
    if not args.confirm:
        print("[ci-ops] 触发操作需要确认.未提供 --confirm,仅打印命令(dry-run):")
        print("    " + cmd_text)
        payload["status"] = "dry-run"
        _write_report(payload)
        return 0

    # 确认:检查 CLI 与环境变量
    cli_tool = cmd[0]
    if not _check_cli(cli_tool) or not _platform_env_ok(platform):
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "平台 CLI 或环境变量不可用,已降级为手动提示"
        _write_report(payload)
        return 0

    # 执行触发
    try:
        rc, out, err = _run_cli(cmd)
        if rc == 0:
            payload["status"] = "triggered"
            print("[ci-ops] 触发成功.")
        else:
            payload["status"] = "failed"
            payload["error"] = err.strip() or out.strip()
            print("[ci-ops] 触发失败: {}".format(payload["error"]))
    except FileNotFoundError:
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "CLI 未安装,已降级为手动提示"
    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
        print("[ci-ops] 触发异常: {}".format(exc))

    _write_report(payload)
    return 0 if payload["status"] in ("triggered", "degraded") else 1


def cmd_status(args):
    """查询构建状态.返回 running / success / failed / degraded."""
    platform = args.platform
    repo = args.repo
    run_id = args.run_id
    payload = _new_payload("status", platform, repo)
    payload["runId"] = run_id

    cmd, cmd_text = _build_status_command(platform, repo, run_id)
    if cmd is None:
        payload["error"] = "不支持的平台: {}".format(platform)
        payload["status"] = "failed"
        print("[ci-ops] " + payload["error"])
        _write_report(payload)
        return 1

    cli_tool = cmd[0]
    if not _check_cli(cli_tool) or not _platform_env_ok(platform):
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "平台 CLI 或环境变量不可用,已降级为手动提示"
        _write_report(payload)
        return 0

    try:
        rc, out, err = _run_cli(cmd)
        if rc == 0:
            status = _parse_status_from_output(out)
            payload["status"] = status
            print("[ci-ops] 构建状态: {}".format(status))
        else:
            payload["status"] = "failed"
            payload["error"] = err.strip() or out.strip()
            print("[ci-ops] 查询失败: {}".format(payload["error"]))
    except FileNotFoundError:
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "CLI 未安装,已降级为手动提示"
    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
        print("[ci-ops] 查询异常: {}".format(exc))

    _write_report(payload)
    return 0 if payload["status"] in ("success", "running", "failed", "degraded", "unknown") else 1


def cmd_report(args):
    """读取测试报告,解析 total/passed/failed/skipped."""
    platform = args.platform
    repo = args.repo
    run_id = args.run_id
    payload = _new_payload("report", platform, repo)
    payload["runId"] = run_id
    payload["testResults"] = _empty_test_results()

    cmd, cmd_text = _build_report_command(platform, repo, run_id)
    if cmd is None:
        payload["error"] = "不支持的平台: {}".format(platform)
        payload["status"] = "failed"
        print("[ci-ops] " + payload["error"])
        _write_report(payload)
        return 1

    cli_tool = cmd[0]
    if not _check_cli(cli_tool) or not _platform_env_ok(platform):
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "平台 CLI 或环境变量不可用,已降级为手动提示"
        _write_report(payload)
        return 0

    try:
        rc, out, err = _run_cli(cmd)
        if rc == 0:
            payload["status"] = "success"
            payload["testResults"] = _parse_test_results_from_output(out)
            print("[ci-ops] 测试结果: {}".format(payload["testResults"]))
        else:
            payload["status"] = "failed"
            payload["error"] = err.strip() or out.strip()
            print("[ci-ops] 读取报告失败: {}".format(payload["error"]))
    except FileNotFoundError:
        _degrade_hint(cmd_text, platform)
        payload["status"] = "degraded"
        payload["error"] = "CLI 未安装,已降级为手动提示"
    except Exception as exc:
        payload["status"] = "failed"
        payload["error"] = str(exc)
        print("[ci-ops] 读取报告异常: {}".format(exc))

    _write_report(payload)
    return 0 if payload["status"] in ("success", "degraded") else 1


def build_parser():
    """构造 argparse 解析器,含 trigger / status / report 三个子命令."""
    parser = argparse.ArgumentParser(
        prog="ci_ops.py",
        description="CI/CD 工具层:触发 CI / 查询构建状态 / 读取测试报告",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # trigger 子命令
    p_trigger = sub.add_parser("trigger", help="触发 CI 构建(变更类,需 --confirm)")
    p_trigger.add_argument("--platform", required=True, choices=SUPPORTED_PLATFORMS,
                           help="CI 平台: github-actions / gitlab-ci / jenkins")
    p_trigger.add_argument("--repo", required=True, help="仓库(owner/repo 或 Jenkins job 名)")
    p_trigger.add_argument("--branch", default=None, help="分支(默认 main)")
    p_trigger.add_argument("--confirm", action="store_true", help="确认执行触发(否则为 dry-run)")
    p_trigger.set_defaults(func=cmd_trigger)

    # status 子命令
    p_status = sub.add_parser("status", help="查询构建状态")
    p_status.add_argument("--platform", required=True, choices=SUPPORTED_PLATFORMS,
                          help="CI 平台")
    p_status.add_argument("--repo", required=True, help="仓库")
    p_status.add_argument("--run-id", default=None, help="指定 run ID(不指定则查最新)")
    p_status.set_defaults(func=cmd_status)

    # report 子命令
    p_report = sub.add_parser("report", help="读取测试报告")
    p_report.add_argument("--platform", required=True, choices=SUPPORTED_PLATFORMS,
                          help="CI 平台")
    p_report.add_argument("--repo", required=True, help="仓库")
    p_report.add_argument("--run-id", default=None, help="指定 run ID")
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv=None):
    """入口函数:解析参数并分发到对应子命令."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        # 未提供子命令时打印帮助
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
