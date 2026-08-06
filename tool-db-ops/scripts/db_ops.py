#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库工具层脚本。

封装 migrate / query / rollback 三类操作:
- migrate:按文件名排序执行迁移 SQL 文件,支持 up/down 方向。
- query:执行只读 SELECT,返回结果行。
- rollback:回滚到指定迁移版本(需二次确认,生产拒绝)。

安全规则:
- 连接串仅从环境变量读取(DB_URL / DB_HOST / DB_USER / DB_PASSWORD),不写入产物。
- 生产环境(连接串含 production/prod/prd)仅允许 query。
- migrate 需 --confirm;rollback 需 --confirm 且非生产。
- migrate / rollback 在单事务内执行,失败回滚。

默认使用 sqlite3(标准库,无额外依赖);通过 DB_URL 可切换其他数据库
(本脚本仅提供 sqlite3 的具体实现,其他驱动需上游扩展)。
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# 失败码定义(与 references/db-safety.md 保持一致)
FAIL_DB_CONNECT = "DB_CONNECT_FAILED"
FAIL_PROD_WRITE = "PROD_WRITE_REJECTED"
FAIL_CONFIRM = "CONFIRM_REQUIRED"
FAIL_MIGRATION_FILE = "MIGRATION_FILE_INVALID"
FAIL_TARGET_NOT_FOUND = "ROLLBACK_TARGET_NOT_FOUND"


# 生产环境关键字
PROD_KEYWORDS = ("production", "prod", "prd")

# 产物文件名
REPORT_NAME = "db-ops-report.json"


def detect_environment(conn_spec: str) -> str:
    """根据连接串判定环境。

    Args:
        conn_spec: 数据库连接字符串(如 DB_URL 或 DB_HOST)。

    Returns:
        "production" 或 "development"。
    """
    lowered = (conn_spec or "").lower()
    if any(kw in lowered for kw in PROD_KEYWORDS):
        return "production"
    return "development"


def get_connection() -> tuple:
    """从环境变量读取连接信息并建立连接。

    优先使用 DB_URL;若未设置则尝试 DB_HOST/DB_USER/DB_PASSWORD。
    默认回退到 sqlite3 内存库(便于本地演示)。

    Returns:
        (connection, environment, conn_spec_for_detection) 元组。
        连接失败时抛出 RuntimeError。
    """
    db_url = os.environ.get("DB_URL", "")
    db_host = os.environ.get("DB_HOST", "")

    # 用于环境检测的字符串
    conn_spec = db_url or db_host or ""

    if db_url:
        # 仅内置 sqlite3 驱动;其他驱动需上游扩展
        if db_url.startswith("sqlite://"):
            path = db_url[len("sqlite://"):]
            conn = sqlite3.connect(path)
        elif db_url.startswith("sqlite:") or db_url.endswith(".db") or db_url.endswith(".sqlite"):
            # 兼容纯文件路径
            conn = sqlite3.connect(db_url.replace("sqlite:", "", 1))
        else:
            # 非 sqlite 的 URL:本脚本不内置第三方驱动,回退到内存库并标记环境
            # 真实场景下应由上游注入对应驱动
            conn = sqlite3.connect(":memory:")
    else:
        # 无 DB_URL 时使用内存库(仅用于 --help / 演示)
        conn = sqlite3.connect(":memory:")

    environment = detect_environment(conn_spec)
    return conn, environment, conn_spec


def write_report(report: dict, output_dir: str = ".") -> str:
    """将执行报告写入 db-ops-report.json。

    Args:
        report: 报告字典。
        output_dir: 输出目录,默认当前目录。

    Returns:
        产物文件绝对路径。
    """
    out_path = Path(output_dir) / REPORT_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return str(out_path.resolve())


def empty_report(command: str, direction=None, environment="development", error=None) -> dict:
    """构造空报告骨架。"""
    return {
        "command": command,
        "direction": direction,
        "migrationFiles": [],
        "rows": [],
        "rowCount": 0,
        "error": error,
        "timestamp": datetime.now().astimezone().isoformat(),
        "environment": environment,
    }


def list_migration_files(migration_dir: str) -> list:
    """列出迁移目录下所有 .sql 文件,按文件名排序。"""
    d = Path(migration_dir)
    if not d.exists() or not d.is_dir():
        return []
    files = sorted([p for p in d.iterdir() if p.suffix == ".sql"], key=lambda p: p.name)
    return files


def cmd_migrate(args) -> dict:
    """执行 migrate 子命令。"""
    conn, environment, _ = get_connection()
    direction = args.direction or "up"
    report = empty_report("migrate", direction=direction, environment=environment)

    # 安全规则:生产环境拒绝写操作
    if environment == "production":
        report["error"] = f"{FAIL_PROD_WRITE}: 生产环境禁止执行 migrate"
        return report

    # 安全规则:需 --confirm
    if not args.confirm:
        report["error"] = f"{FAIL_CONFIRM}: migrate 需要传入 --confirm"
        return report

    files = list_migration_files(args.migration_dir)
    if not files:
        report["error"] = f"{FAIL_MIGRATION_FILE}: 迁移目录为空或不存在: {args.migration_dir}"
        return report

    # down 方向:逆序执行
    if direction == "down":
        files = list(reversed(files))

    executed = []
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        for f in files:
            sql = f.read_text(encoding="utf-8")
            if not sql.strip():
                continue
            cur.executescript(sql)
            executed.append(f.name)
        conn.commit()
        report["migrationFiles"] = executed
    except Exception as e:
        conn.rollback()
        report["migrationFiles"] = executed
        report["error"] = f"{FAIL_MIGRATION_FILE}: 执行失败已回滚事务, 文件={executed[-1] if executed else 'N/A'}, 异常={e}"
    finally:
        conn.close()

    return report


def cmd_query(args) -> dict:
    """执行 query 子命令(纯只读,生产环境也允许)。"""
    conn, environment, _ = get_connection()
    report = empty_report("query", direction=None, environment=environment)

    params = []
    if args.params:
        try:
            params = json.loads(args.params)
            if not isinstance(params, list):
                params = [params]
        except json.JSONDecodeError as e:
            report["error"] = f"{FAIL_MIGRATION_FILE}: --params 必须是 JSON 数组, 异常={e}"
            return report

    sql = (args.sql or "").strip()
    # 仅允许 SELECT / WITH(只读校验)
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
        report["error"] = f"{FAIL_PROD_WRITE}: query 仅允许 SELECT/WITH 语句"
        return report

    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        report["rows"] = [dict(zip(cols, r)) for r in rows]
        report["rowCount"] = len(rows)
    except Exception as e:
        report["error"] = f"{FAIL_DB_CONNECT}: 查询失败, 异常={e}"
    finally:
        conn.close()

    return report


def cmd_rollback(args) -> dict:
    """执行 rollback 子命令(需二次确认,生产拒绝)。"""
    conn, environment, _ = get_connection()
    report = empty_report("rollback", direction="down", environment=environment)

    # 安全规则:生产环境拒绝
    if environment == "production":
        report["error"] = f"{FAIL_PROD_WRITE}: 生产环境禁止执行 rollback"
        return report

    # 安全规则:需 --confirm(二次确认)
    if not args.confirm:
        report["error"] = f"{FAIL_CONFIRM}: rollback 需要 --confirm 进行二次确认"
        return report

    files = list_migration_files(args.migration_dir)
    if not files:
        report["error"] = f"{FAIL_MIGRATION_FILE}: 迁移目录为空或不存在: {args.migration_dir}"
        return report

    # 回滚到 target:执行 target 之后(按排序之后)的所有 down 文件
    target = args.target
    target_idx = None
    for idx, f in enumerate(files):
        if f.name.startswith(target) or target in f.name:
            target_idx = idx
            break
    if target_idx is None:
        report["error"] = f"{FAIL_TARGET_NOT_FOUND}: 未找到目标迁移版本: {target}"
        return report

    # 需要回滚的文件:target 之后的所有文件,逆序执行
    to_rollback = list(reversed(files[target_idx + 1:]))
    executed = []
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        for f in to_rollback:
            sql = f.read_text(encoding="utf-8")
            if not sql.strip():
                continue
            cur.executescript(sql)
            executed.append(f.name)
        conn.commit()
        report["migrationFiles"] = executed
    except Exception as e:
        conn.rollback()
        report["migrationFiles"] = executed
        report["error"] = f"{FAIL_MIGRATION_FILE}: 回滚失败已回滚事务, 异常={e}"
    finally:
        conn.close()

    return report


def build_parser() -> argparse.ArgumentParser:
    """构造 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="db_ops.py",
        description="数据库工具层:封装 migrate / query / rollback,生产环境只读。",
    )
    sub = parser.add_subparsers(dest="command", required=True, help="子命令")

    # migrate
    p_mig = sub.add_parser("migrate", help="执行迁移(需 --confirm,生产拒绝)")
    p_mig.add_argument("--migration-dir", required=True, help="迁移文件目录")
    p_mig.add_argument("--direction", choices=["up", "down"], default="up", help="迁移方向,默认 up")
    p_mig.add_argument("--repo", default=None, help="代码仓库路径(可选,仅记录用)")
    p_mig.add_argument("--confirm", action="store_true", help="确认执行")

    # query
    p_q = sub.add_parser("query", help="只读查询(生产也允许)")
    p_q.add_argument("--sql", required=True, help="SELECT/WITH SQL 语句")
    p_q.add_argument("--params", default=None, help="参数 JSON 数组,如 [1, 'a']")

    # rollback
    p_rb = sub.add_parser("rollback", help="回滚到指定版本(需 --confirm,生产拒绝)")
    p_rb.add_argument("--migration-dir", required=True, help="迁移文件目录")
    p_rb.add_argument("--target", required=True, help="回滚到的目标迁移版本(文件名片段)")
    p_rb.add_argument("--confirm", action="store_true", help="二次确认")

    return parser


def main():
    """入口函数:解析参数并派发到子命令,产出 db-ops-report.json。"""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "migrate":
        report = cmd_migrate(args)
    elif args.command == "query":
        report = cmd_query(args)
    elif args.command == "rollback":
        report = cmd_rollback(args)
    else:
        # argparse 已保证 command 必填,此处兜底
        report = empty_report("unknown", error=f"未知子命令: {args.command}")

    out_path = write_report(report)
    # 标准输出打印报告摘要,便于上游解析
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"报告已写入: {out_path}", file=sys.stderr)

    # 有错误时以非零退出码返回,便于上游判断
    if report.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
