#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy_ops.py - 部署工具层操作脚本.

封装 deploy / rollback / healthcheck 三个子命令,支持
github-pages / vercel / netlify / cloudbase / cos 五个平台.
仅使用 Python 标准库,无外部依赖.

调用方式见 ../SKILL.md 第四节.各平台部署命令与配置模板见
../references/deploy-platforms.md(其内容引用自 web-static-deploy/references/).
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.request

# 平台 -> 对应 CLI 工具名(用于可用性检测)
# github-pages 走 npx gh-pages,故 CLI 工具实际是 npx
PLATFORM_CLI = {
    "github-pages": "npx",
    "vercel": "vercel",
    "netlify": "netlify",
    "cloudbase": "tcb",
    "cos": "coscli",
}

REPORT_FILE = "deploy-ops-report.json"
HEALTHCHECK_TIMEOUT = 15  # 健康检查超时秒数


def now_iso():
    """返回本机时区的 ISO8601 时间字符串(带时区,精度到秒)."""
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def find_cli(tool):
    """检测指定 CLI 工具是否在 PATH 中可用.

    用 where(Windows) / which(Unix) 查找,返回路径或 None.
    """
    finder = "where" if os.name == "nt" else "which"
    try:
        result = subprocess.run(
            [finder, tool], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def git_short_sha():
    """返回当前 git short SHA;不在 git 仓库或无 git 时返回 None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def version_id():
    """生成本次部署版本标识:优先 git short SHA,否则用时间戳."""
    sha = git_short_sha()
    if sha:
        return sha
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


def build_deploy_command(platform, source, target):
    """根据平台构造部署命令(list 形式,可直接交给 subprocess 执行).

    各命令的语义与配置模板详见 references/deploy-platforms.md.
    """
    if platform == "github-pages":
        # npx gh-pages 直接把 source 发布到 gh-pages 分支
        return ["npx", "gh-pages", "-d", source]
    if platform == "vercel":
        cmd = ["vercel", "deploy", source, "--prod", "--yes"]
        if target:
            cmd += ["--name", target]
        return cmd
    if platform == "netlify":
        cmd = ["netlify", "deploy", "--prod", "--dir=" + source]
        if target:
            cmd += ["--site", target]
        return cmd
    if platform == "cloudbase":
        # target 为 CloudBase envId
        cmd = ["tcb", "hosting", "deploy", source]
        if target:
            cmd += ["-e", target]
        return cmd
    if platform == "cos":
        # target 为 COS 桶名
        bucket = target or "bucket"
        return ["coscli", "cp", source, "cos://" + bucket + "/", "-r"]
    return None


def build_rollback_command(platform, target):
    """根据平台构造回滚命令.不支持 CLI 回滚的平台返回 None(走降级)."""
    if platform == "github-pages":
        # GitHub Pages 回滚:revert 最近一次提交(随后 push 触发 CI 重部署)
        return ["git", "revert", "HEAD", "--no-edit"]
    if platform == "vercel":
        # vercel rollback 需要 deployment id,target 作为该 id
        cmd = ["vercel", "rollback"]
        if target:
            cmd.append(target)
        return cmd
    # netlify / cloudbase / cos 无直接 CLI 回滚,返回 None 触发降级
    return None


def build_degrade_hint(platform, action, source=None, target=None):
    """构造降级时输出的手动指令文本(平台 CLI 不可用 / 不支持时使用)."""
    if action == "deploy":
        cmd = build_deploy_command(platform, source, target)
    elif action == "rollback":
        cmd = build_rollback_command(platform, target)
    else:
        cmd = None
    if cmd is None:
        return ("[降级] 平台 {0} 暂不支持 {1} 的自动 CLI 操作, "
                "请到控制台手动回滚或重新部署上一版本产物").format(platform, action)
    return "[降级] 平台 CLI 不可用,请手动执行: " + " ".join(cmd)


def extract_url_from_stdout(stdout, domain_suffix):
    """从 CLI 输出中提取包含指定域名的 https URL,找不到返回 None."""
    for token in (stdout or "").replace("\n", " ").split():
        if token.startswith("https://") and domain_suffix in token:
            return token.rstrip(",.;")
    return None


def infer_url(platform, target, stdout=""):
    """尽力推断部署后的访问 URL,推断不到返回 None.

    github-pages: target 形如 user/repo -> https://user.github.io/repo/
    vercel / netlify: 从 CLI stdout 中提取部署后返回的 URL
    cloudbase / cos: 无法可靠推断,返回 None(由上层另跑 healthcheck)
    """
    if platform == "github-pages" and target and "/" in target:
        user, repo = target.split("/", 1)
        return "https://{0}.github.io/{1}/".format(user, repo)
    if platform == "vercel":
        return extract_url_from_stdout(stdout, ".vercel.app")
    if platform == "netlify":
        return extract_url_from_stdout(stdout, ".netlify.app")
    return None


def do_healthcheck(url):
    """对 URL 做 HTTP GET,返回 (ok, statusCode, responseTimeMs, error)."""
    start = datetime.datetime.now()
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "tool-deploy-ops/1.0"}
        )
        with urllib.request.urlopen(req, timeout=HEALTHCHECK_TIMEOUT) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
    except urllib.request.HTTPError as e:
        # HTTP 错误(4xx/5xx)也能拿到状态码,标 WARNING 但不阻断
        end = datetime.datetime.now()
        ms = int((end - start).total_seconds() * 1000)
        return False, e.code, ms, "HTTPError: {0}".format(e.code)
    except urllib.request.URLError as e:
        end = datetime.datetime.now()
        ms = int((end - start).total_seconds() * 1000)
        return False, None, ms, "URLError: {0}".format(e.reason)
    except Exception as e:
        end = datetime.datetime.now()
        ms = int((end - start).total_seconds() * 1000)
        return False, None, ms, "Exception: {0}".format(e)
    end = datetime.datetime.now()
    ms = int((end - start).total_seconds() * 1000)
    ok = 200 <= int(status) < 400
    return ok, int(status), ms, None


def write_report(report):
    """把报告写入当前工作目录的 deploy-ops-report.json(同名覆盖)."""
    path = os.path.join(os.getcwd(), REPORT_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("报告已写入: " + path)
    return path


def cmd_deploy(args):
    """deploy 子命令:部署产物到目标平台."""
    platform = args.platform
    source = args.source
    target = args.target
    report = {
        "command": "deploy",
        "platform": platform,
        "source": source,
        "target": target,
        "url": None,
        "version": version_id(),
        "healthStatus": None,
        "error": None,
        "timestamp": now_iso(),
    }

    cmd = build_deploy_command(platform, source, target)
    cmd_str = " ".join(cmd)

    # 1) 未带 --confirm:只打印命令,不执行(预演;不校验产物,便于提前查看将执行什么)
    if not args.confirm:
        report["error"] = "未带 --confirm,仅打印命令未执行(预演)"
        write_report(report)
        print("[预演] 将执行: " + cmd_str)
        print("       确认后加 --confirm 重新运行")
        return 0

    # 2) 校验产物目录:不存在或为空属于"输入不合法",阻断(返回非零)
    if not source or not os.path.isdir(source):
        report["error"] = "产物路径不存在或不是目录: {0}".format(source)
        write_report(report)
        print("[错误] " + report["error"])
        return 1
    if not os.listdir(source):
        report["error"] = "产物目录为空: {0}".format(source)
        write_report(report)
        print("[错误] " + report["error"])
        return 1

    # 3) 检查平台 CLI 可用性;不可用则降级输出手动指令(不阻断)
    cli_tool = PLATFORM_CLI[platform]
    if not find_cli(cli_tool):
        hint = build_degrade_hint(platform, "deploy", source, target)
        report["error"] = hint
        write_report(report)
        print(hint)
        return 0

    # 4) 实际执行部署
    print("[部署] 执行: " + cmd_str)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        report["error"] = "CLI 调用失败: {0}".format(e)
        write_report(report)
        print(build_degrade_hint(platform, "deploy", source, target))
        return 0

    if result.returncode != 0:
        # 部署失败:写 error,不阻断(交上层决策)
        report["error"] = "部署失败(returncode={0}): {1}".format(
            result.returncode, (result.stderr or result.stdout).strip()
        )
        write_report(report)
        print("[失败] " + report["error"])
        return 0

    print("[成功] " + (result.stdout or "").strip())

    # 5) 部署成功后:尽力推断 URL 并自动接一次健康检查
    url = infer_url(platform, target, result.stdout)
    if url:
        ok, status, ms, err = do_healthcheck(url)
        report["url"] = url
        report["healthStatus"] = {
            "ok": ok, "statusCode": status, "responseTimeMs": ms
        }
        if not ok:
            # 健康检查失败:标 WARNING,不阻断
            report["error"] = "健康检查 WARNING: {0}".format(err)
            print("[WARNING] 健康检查未通过({0}): {1}".format(url, err))
        else:
            print("[健康] {0} -> {1} ({2}ms)".format(url, status, ms))
    else:
        print("[提示] 未能推断部署 URL,请另行运行: "
              "python scripts/deploy_ops.py healthcheck --url <URL>")

    write_report(report)
    return 0


def cmd_rollback(args):
    """rollback 子命令:回滚到上一版本."""
    platform = args.platform
    target = args.target
    report = {
        "command": "rollback",
        "platform": platform,
        "source": None,
        "target": target,
        "url": None,
        "version": None,
        "healthStatus": None,
        "error": None,
        "timestamp": now_iso(),
    }

    cmd = build_rollback_command(platform, target)

    # 平台不支持 CLI 回滚:降级输出手动指令(不阻断)
    if cmd is None:
        hint = build_degrade_hint(platform, "rollback", target=target)
        report["error"] = hint
        write_report(report)
        print(hint)
        return 0

    cmd_str = " ".join(cmd)

    # 未带 --confirm:只打印命令(回滚是高风险操作,必须显式确认)
    if not args.confirm:
        report["error"] = "未带 --confirm,仅打印命令未执行(预演)"
        write_report(report)
        print("[预演] 将执行: " + cmd_str)
        print("       确认后加 --confirm 重新运行")
        return 0

    # github-pages 回滚用 git;其余用平台 CLI
    cli_tool = "git" if platform == "github-pages" else PLATFORM_CLI[platform]
    if not find_cli(cli_tool):
        hint = build_degrade_hint(platform, "rollback", target=target)
        report["error"] = hint
        write_report(report)
        print(hint)
        return 0

    print("[回滚] 执行: " + cmd_str)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        report["error"] = "CLI 调用失败: {0}".format(e)
        write_report(report)
        print(build_degrade_hint(platform, "rollback", target=target))
        return 0

    if result.returncode != 0:
        report["error"] = "回滚失败(returncode={0}): {1}".format(
            result.returncode, (result.stderr or result.stdout).strip()
        )
        write_report(report)
        print("[失败] " + report["error"])
        return 0

    print("[成功] " + (result.stdout or "").strip())
    # 回滚后记录当前(回退到的)版本标识
    report["version"] = git_short_sha()
    write_report(report)
    return 0


def cmd_healthcheck(args):
    """healthcheck 子命令:对 URL 做 HTTP GET 健康检查."""
    url = args.url
    report = {
        "command": "healthcheck",
        "platform": None,
        "source": None,
        "target": None,
        "url": url,
        "version": None,
        "healthStatus": None,
        "error": None,
        "timestamp": now_iso(),
    }
    ok, status, ms, err = do_healthcheck(url)
    report["healthStatus"] = {
        "ok": ok, "statusCode": status, "responseTimeMs": ms
    }
    if not ok:
        # 健康检查失败:标 WARNING,不阻断(退出码 0)
        report["error"] = "健康检查 WARNING: {0}".format(err)
        print("[WARNING] {0} 未通过: {1}".format(url, err))
    else:
        print("[健康] {0} -> {1} ({2}ms)".format(url, status, ms))
    write_report(report)
    return 0


def main():
    """命令入口:解析参数并派发到对应子命令."""
    # 避免 Windows 控制台编码问题导致中文打印崩溃
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="部署工具层操作脚本(deploy/rollback/healthcheck),仅用标准库.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # deploy 子命令
    p_deploy = sub.add_parser("deploy", help="部署产物到目标平台")
    p_deploy.add_argument(
        "--platform", required=True,
        choices=["github-pages", "vercel", "netlify", "cloudbase", "cos"],
        help="目标平台",
    )
    p_deploy.add_argument("--source", required=True, help="产物路径(dist/build)")
    p_deploy.add_argument("--target", help="目标名(仓库名/项目名/envId/桶名)")
    p_deploy.add_argument(
        "--confirm", action="store_true", help="确认执行;不带则只打印命令"
    )

    # rollback 子命令
    p_rb = sub.add_parser("rollback", help="回滚到上一版本")
    p_rb.add_argument(
        "--platform", required=True,
        choices=["github-pages", "vercel", "netlify", "cloudbase", "cos"],
        help="目标平台",
    )
    p_rb.add_argument("--target", help="目标名(项目名/deployment id)")
    p_rb.add_argument(
        "--confirm", action="store_true", help="确认执行;不带则只打印命令"
    )

    # healthcheck 子命令
    p_hc = sub.add_parser("healthcheck", help="HTTP GET 健康检查")
    p_hc.add_argument("--url", required=True, help="检查的 URL")

    args = parser.parse_args()
    if args.command == "deploy":
        return cmd_deploy(args)
    if args.command == "rollback":
        return cmd_rollback(args)
    if args.command == "healthcheck":
        return cmd_healthcheck(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main() or 0)
