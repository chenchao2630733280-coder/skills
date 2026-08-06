#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snapshot_ops.py - 会话持久化层脚本。

子命令:
  save     [--session-id <id>] [--trigger manual|auto-confirm|auto-stage|auto-fail]
           [--artifacts <文件路径>...] [--context <JSON>]
           [--task-tree <task-tree.json>] [--workflow-state <JSON>]
           保存会话快照,生成 snapshot_id,顺带清理过期快照
  restore  --snapshot-id <id> | --latest  --confirm yes
           [--only task_tree|artifacts|context|workflow]
           恢复快照(必须 --confirm yes),校验文件 hash,产出 restore-result.json
  list     [--limit 20] [--session-id <id>]
           列出快照(按时间倒序)
  diff     --snapshot-a <id> --snapshot-b <id>
           对比两快照差异(任务/文件/上下文)
  clean    [--retention-days 30]
           清理过期快照

存储目录:~/.trae-cn/sessions/
退出码:0=成功(含 WARNING);1=有错误;2=参数错误

设计原则:快照是辅助记忆,不是关键路径。宁可丢快照也不能拖垮主流程。
所有异常捕获后只在 stderr 打印 WARNING,save/list/diff 退出 0,restore 失败返回空结果。
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOCAL_TZ = timezone(timedelta(hours=8))
SESSIONS_DIR = Path.home() / ".trae-cn" / "sessions"
INDEX_FILE = SESSIONS_DIR / "snapshots-index.json"
RESTORE_RESULT_FILE = SESSIONS_DIR / "restore-result.json"

DEFAULT_RETENTION_DAYS = int(os.environ.get("SESSION_SNAPSHOT_RETENTION_DAYS", "30"))


# ============================================================
# 工具函数
# ============================================================

def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _ensure_dir():
    """确保快照目录存在。失败不抛异常。"""
    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"WARNING: 创建快照目录失败:{e}", file=sys.stderr)
        return False


def _sha256_file(path):
    """计算文件 SHA-256,返回 'sha256:{hex}'。文件不存在返回 None。"""
    try:
        p = Path(path)
        if not p.exists():
            return None
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return f"sha256:{h.hexdigest()}"
    except Exception:
        return None


def _load_index():
    """加载索引。损坏时返回空结构。"""
    if not INDEX_FILE.exists():
        return {"snapshots": [], "updated_at": _now_iso()}
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        if "snapshots" not in data:
            data["snapshots"] = []
        return data
    except Exception as e:
        print(f"WARNING: 索引损坏,重建空索引:{e}", file=sys.stderr)
        return {"snapshots": [], "updated_at": _now_iso()}


def _save_index(index):
    """保存索引。失败只打 WARNING。"""
    if not _ensure_dir():
        return
    index["updated_at"] = _now_iso()
    try:
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 写索引失败:{e}", file=sys.stderr)


def _gen_snapshot_id():
    """生成 snap-{YYYYMMDD}-{NNN} 格式的快照 ID。"""
    today = datetime.now(LOCAL_TZ).strftime("%Y%m%d")
    prefix = f"snap-{today}-"
    index = _load_index()
    existing = [s["snapshot_id"] for s in index.get("snapshots", [])
                if s.get("snapshot_id", "").startswith(prefix)]
    nnn = 1
    while f"{prefix}{nnn:03d}" in existing:
        nnn += 1
    return f"{prefix}{nnn:03d}"


def _snapshot_path(snapshot_id):
    return SESSIONS_DIR / f"{snapshot_id}.json"


def _load_snapshot(snapshot_id):
    """加载快照。不存在返回 None。"""
    p = _snapshot_path(snapshot_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WARNING: 加载快照 {snapshot_id} 失败:{e}", file=sys.stderr)
        return None


def _parse_json_arg(s):
    """解析 --context / --workflow-state 的 JSON 字符串。失败返回 None。"""
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception as e:
        print(f"WARNING: 解析 JSON 参数失败:{e}", file=sys.stderr)
        return None


def _short_summary(snapshot):
    """从快照生成一句话摘要(用于索引)。"""
    task = snapshot.get("task_tree", {}) or {}
    current = task.get("current_task", "")
    completed = task.get("completed", []) or []
    pending = task.get("pending", []) or []
    parts = []
    if current:
        parts.append(f"当前任务 {current}")
    if completed:
        parts.append(f"已完成 {len(completed)}")
    if pending:
        parts.append(f"待执行 {len(pending)}")
    if not parts:
        parts.append("无任务状态")
    return ",".join(parts)


# ============================================================
# save 子命令
# ============================================================

def cmd_save(args):
    """save:保存会话快照。"""
    if not _ensure_dir():
        return 0  # 目录创建失败不阻断主流程

    snapshot_id = _gen_snapshot_id()
    now = _now_iso()

    # 任务进度
    task_tree = {"current_task": None, "completed": [], "pending": []}
    if args.task_tree:
        tt_path = Path(args.task_tree)
        if tt_path.exists():
            try:
                tt = json.loads(tt_path.read_text(encoding="utf-8"))
                # 兼容 task-planner 的 task-tree.json 格式
                task_tree = {
                    "current_task": tt.get("current_task") or tt.get("current"),
                    "completed": tt.get("completed", []),
                    "pending": tt.get("pending", []),
                    "task_tree_file": args.task_tree,
                }
            except Exception as e:
                print(f"WARNING: 解析 task-tree 失败:{e}", file=sys.stderr)
                task_tree["task_tree_file"] = args.task_tree
        else:
            print(f"WARNING: task-tree 文件不存在:{args.task_tree}", file=sys.stderr)
            task_tree["task_tree_file"] = args.task_tree

    # 已产出文件
    artifacts = []
    if args.artifacts:
        for art_path in args.artifacts:
            p = Path(art_path)
            hash_val = _sha256_file(p)
            entry = {
                "path": art_path.replace("\\", "/"),
                "hash": hash_val if hash_val else "sha256:missing",
                "summary": "",
            }
            if p.exists():
                try:
                    entry["size"] = p.stat().st_size
                except Exception:
                    entry["size"] = None
            else:
                entry["size"] = None
            artifacts.append(entry)

    # 上下文摘要
    context_summary = {
        "key_decisions": [],
        "user_preferences": [],
        "failures": [],
        "notes": "",
    }
    if args.context:
        ctx = _parse_json_arg(args.context)
        if ctx:
            context_summary = {
                "key_decisions": ctx.get("key_decisions", []),
                "user_preferences": ctx.get("user_preferences", []),
                "failures": ctx.get("failures", []),
                "notes": ctx.get("notes", ""),
            }

    # workflow 状态
    workflow_state = {"current_step": None, "paused_at": None,
                      "workflow_file": None, "exec_report_file": None}
    if args.workflow_state:
        ws = _parse_json_arg(args.workflow_state)
        if ws:
            workflow_state = {
                "current_step": ws.get("current_step"),
                "paused_at": ws.get("paused_at"),
                "workflow_file": ws.get("workflow_file"),
                "exec_report_file": ws.get("exec_report_file"),
            }

    snapshot = {
        "snapshot_id": snapshot_id,
        "session_id": args.session_id or "unknown",
        "created_at": now,
        "trigger": args.trigger,
        "task_tree": task_tree,
        "artifacts": artifacts,
        "context_summary": context_summary,
        "workflow_state": workflow_state,
    }

    # 写快照文件
    snap_file = _snapshot_path(snapshot_id)
    try:
        snap_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    except Exception as e:
        print(f"WARNING: 写快照失败:{e}", file=sys.stderr)
        return 0  # 不阻断

    # 更新索引
    index = _load_index()
    index["snapshots"].append({
        "snapshot_id": snapshot_id,
        "session_id": snapshot["session_id"],
        "created_at": now,
        "trigger": args.trigger,
        "summary": _short_summary(snapshot),
        "file": snap_file.name,
    })
    _save_index(index)

    print(f"PASS  保存快照:{snapshot_id}")
    print(f"  路径:{snap_file}")
    print(f"  触发:{args.trigger}")
    print(f"  文件数:{len(artifacts)}")

    # 顺带清理过期快照
    try:
        cleaned = _do_clean(DEFAULT_RETENTION_DAYS)
        if cleaned > 0:
            print(f"  顺带清理过期快照:{cleaned} 个(>{DEFAULT_RETENTION_DAYS} 天)")
    except Exception as e:
        print(f"WARNING: 清理过期快照失败:{e}", file=sys.stderr)

    return 0


# ============================================================
# restore 子命令
# ============================================================

def cmd_restore(args):
    """restore:恢复快照。"""
    if args.confirm != "yes":
        print("FAIL  恢复需用户确认,请加 --confirm yes")
        return 1

    # 确定快照 ID
    snapshot_id = args.snapshot_id
    if args.latest:
        index = _load_index()
        snaps = index.get("snapshots", [])
        if not snaps:
            print("无快照可恢复")
            return 0
        # 按时间倒序取第一个
        snaps_sorted = sorted(snaps, key=lambda x: x.get("created_at", ""),
                              reverse=True)
        snapshot_id = snaps_sorted[0]["snapshot_id"]
        print(f"使用最新快照:{snapshot_id}")

    if not snapshot_id:
        print("FAIL  需指定 --snapshot-id 或 --latest")
        return 2

    snapshot = _load_snapshot(snapshot_id)
    if snapshot is None:
        print(f"FAIL  快照不存在或损坏:{snapshot_id}")
        return 1

    # 选择性恢复
    only = args.only

    # 文件 hash 校验
    artifacts_check = []
    if not only or only == "artifacts":
        for art in snapshot.get("artifacts", []):
            path = art.get("path", "")
            snap_hash = art.get("hash", "")
            current_hash = _sha256_file(path)
            if current_hash is None:
                status = "missing"
            elif current_hash == snap_hash:
                status = "ok"
            else:
                status = "conflict"
            artifacts_check.append({
                "path": path,
                "status": status,
                "snapshot_hash": snap_hash,
                "current_hash": current_hash or "missing",
            })

    # 生成恢复结果
    result = {
        "snapshot_id": snapshot_id,
        "restored_at": _now_iso(),
        "session_id": snapshot.get("session_id", "unknown"),
        "trigger": snapshot.get("trigger", ""),
        "artifacts_check": artifacts_check,
        "context_injected": (not only) or (only == "context"),
        "task_tree_restored": (not only) or (only == "task_tree"),
        "workflow_state_restored": (not only) or (only == "workflow"),
    }

    # 写恢复结果文件
    if _ensure_dir():
        try:
            RESTORE_RESULT_FILE.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception as e:
            print(f"WARNING: 写恢复结果失败:{e}", file=sys.stderr)

    # 打印恢复信息(注入到新会话)
    print(f"【会话恢复】来自快照 {snapshot_id}"
          f"({snapshot.get('created_at', '')})")
    print()

    if (not only) or (only == "task_tree"):
        tt = snapshot.get("task_tree", {}) or {}
        print("任务进度:")
        print(f"  当前任务: {tt.get('current_task', '无')}")
        completed = tt.get("completed", []) or []
        pending = tt.get("pending", []) or []
        print(f"  已完成: {', '.join(completed) if completed else '无'}")
        print(f"  待执行: {', '.join(pending) if pending else '无'}")
        print()

    if (not only) or (only == "context"):
        ctx = snapshot.get("context_summary", {}) or {}
        decisions = ctx.get("key_decisions", []) or []
        prefs = ctx.get("user_preferences", []) or []
        failures = ctx.get("failures", []) or []
        notes = ctx.get("notes", "")
        print("关键决策:")
        for d in decisions:
            print(f"  - {d}")
        if not decisions:
            print("  (无)")
        print()
        print("用户偏好:")
        for p in prefs:
            print(f"  - {p}")
        if not prefs:
            print("  (无)")
        print()
        if failures:
            print("历史失败:")
            for f in failures:
                skill = f.get("skill", "")
                code = f.get("code", "")
                case_id = f.get("case_id", "")
                print(f"  - {skill}: {code}(案例 {case_id})")
            print()
        if notes:
            print(f"备注: {notes}")
            print()

    if (not only) or (only == "artifacts"):
        print("文件校验:")
        for ac in artifacts_check:
            status_label = {
                "ok": "OK",
                "conflict": "CONFLICT(文件已被修改)",
                "missing": "MISSING(文件已删除)",
            }.get(ac["status"], ac["status"])
            print(f"  {ac['path']}: {status_label}")
        print()

    if (not only) or (only == "workflow"):
        ws = snapshot.get("workflow_state", {}) or {}
        print("Workflow 状态:")
        print(f"  当前步骤: {ws.get('current_step', '无')}")
        print(f"  暂停点: {ws.get('paused_at', '无')}")
        if ws.get("workflow_file"):
            print(f"  Workflow 文件: {ws['workflow_file']}")
        print()

    # 冲突提示
    conflicts = [ac for ac in artifacts_check if ac["status"] == "conflict"]
    missing = [ac for ac in artifacts_check if ac["status"] == "missing"]
    if conflicts:
        print(f"⚠ {len(conflicts)} 个文件被修改(已标 CONFLICT),需用户确认如何处理")
    if missing:
        print(f"⚠ {len(missing)} 个文件已删除(已标 MISSING),可能需要重新生成")

    print(f"\n恢复结果已写入:{RESTORE_RESULT_FILE}")
    return 0


# ============================================================
# list 子命令
# ============================================================

def cmd_list(args):
    """list:列出快照。"""
    index = _load_index()
    snaps = index.get("snapshots", [])

    # 按会话过滤
    if args.session_id:
        snaps = [s for s in snaps if s.get("session_id") == args.session_id]

    # 按时间倒序
    snaps_sorted = sorted(snaps, key=lambda x: x.get("created_at", ""),
                          reverse=True)

    limit = args.limit or 20
    snaps_limited = snaps_sorted[:limit]

    if not snaps_limited:
        print("无快照")
        return 0

    print(f"快照列表(共 {len(snaps)} 个,显示 {len(snaps_limited)} 个):")
    print(f"{'Snapshot ID':<25} | {'创建时间':<25} | {'触发':<15} | {'摘要'}")
    print("-" * 100)
    for s in snaps_limited:
        sid = s.get("snapshot_id", "")
        ts = s.get("created_at", "")
        trigger = s.get("trigger", "")
        summary = s.get("summary", "")
        print(f"{sid:<25} | {ts:<25} | {trigger:<15} | {summary}")
    return 0


# ============================================================
# diff 子命令
# ============================================================

def _diff_lists(a, b, label):
    """对比两个列表,返回差异描述。"""
    a_set = set(a or [])
    b_set = set(b or [])
    added = sorted(b_set - a_set)
    removed = sorted(a_set - b_set)
    lines = []
    if added:
        lines.append(f"  {label} 新增: {added}")
    if removed:
        lines.append(f"  {label} 移除: {removed}")
    if not added and not removed:
        lines.append(f"  {label}: 无变化")
    return lines


def cmd_diff(args):
    """diff:对比两快照差异。"""
    a = _load_snapshot(args.snapshot_a)
    b = _load_snapshot(args.snapshot_b)
    if a is None:
        print(f"FAIL  快照 A 不存在:{args.snapshot_a}")
        return 1
    if b is None:
        print(f"FAIL  快照 B 不存在:{args.snapshot_b}")
        return 1

    print(f"对比快照 {args.snapshot_a} vs {args.snapshot_b}")
    print(f"  A 创建于 {a.get('created_at', '')}")
    print(f"  B 创建于 {b.get('created_at', '')}")
    print()

    # 任务进度差异
    print("任务进度差异:")
    tt_a = a.get("task_tree", {}) or {}
    tt_b = b.get("task_tree", {}) or {}
    if tt_a.get("current_task") != tt_b.get("current_task"):
        print(f"  当前任务: {tt_a.get('current_task')} → {tt_b.get('current_task')}")
    else:
        print(f"  当前任务: {tt_a.get('current_task')}(无变化)")
    for line in _diff_lists(tt_a.get("completed"), tt_b.get("completed"), "已完成"):
        print(line)
    for line in _diff_lists(tt_a.get("pending"), tt_b.get("pending"), "待执行"):
        print(line)
    print()

    # 文件差异
    print("文件差异:")
    arts_a = {a_["path"]: a_ for a_ in (a.get("artifacts") or [])}
    arts_b = {b_["path"]: b_ for b_ in (b.get("artifacts") or [])}
    paths_a = set(arts_a.keys())
    paths_b = set(arts_b.keys())
    added_files = sorted(paths_b - paths_a)
    removed_files = sorted(paths_a - paths_b)
    common = sorted(paths_a & paths_b)
    if added_files:
        print(f"  新增文件: {added_files}")
    if removed_files:
        print(f"  移除文件: {removed_files}")
    hash_changed = []
    for p in common:
        ha = arts_a[p].get("hash", "")
        hb = arts_b[p].get("hash", "")
        if ha != hb:
            hash_changed.append(p)
    if hash_changed:
        print(f"  hash 变化: {hash_changed}")
    if not added_files and not removed_files and not hash_changed:
        print("  无文件变化")
    print()

    # 上下文差异
    print("上下文差异:")
    ctx_a = a.get("context_summary", {}) or {}
    ctx_b = b.get("context_summary", {}) or {}
    for line in _diff_lists(ctx_a.get("key_decisions"), ctx_b.get("key_decisions"), "关键决策"):
        print(line)
    for line in _diff_lists(ctx_a.get("user_preferences"), ctx_b.get("user_preferences"), "用户偏好"):
        print(line)
    for line in _diff_lists([f.get("case_id", "") for f in (ctx_a.get("failures") or [])],
                            [f.get("case_id", "") for f in (ctx_b.get("failures") or [])],
                            "失败案例"):
        print(line)

    return 0


# ============================================================
# clean 子命令
# ============================================================

def _do_clean(retention_days):
    """清理过期快照,返回清理数量。"""
    if not SESSIONS_DIR.exists():
        return 0
    now = datetime.now(LOCAL_TZ)
    cutoff = now - timedelta(days=retention_days)
    cleaned = 0
    index = _load_index()
    new_snaps = []
    for s in index.get("snapshots", []):
        ts_str = s.get("created_at", "")
        try:
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            new_snaps.append(s)  # 解析失败保留
            continue
        if ts < cutoff:
            # 删除快照文件
            snap_file = _snapshot_path(s.get("snapshot_id", ""))
            if snap_file.exists():
                try:
                    snap_file.unlink()
                    cleaned += 1
                except Exception:
                    new_snaps.append(s)  # 删除失败保留
            else:
                cleaned += 1  # 文件已不在,只清索引
        else:
            new_snaps.append(s)
    index["snapshots"] = new_snaps
    _save_index(index)
    return cleaned


def cmd_clean(args):
    """clean:清理过期快照。"""
    retention = args.retention_days if args.retention_days is not None else DEFAULT_RETENTION_DAYS
    cleaned = _do_clean(retention)
    print(f"PASS  清理过期快照:{cleaned} 个(>{retention} 天)")
    return 0


# ============================================================
# argparse
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        prog="snapshot_ops.py",
        description="会话持久化层脚本。save/restore/list/diff/clean。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码:0=成功(含 WARNING);1=有错误;2=参数错误",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # save
    p_save = sub.add_parser("save", help="保存会话快照")
    p_save.add_argument("--session-id", default=None, help="原会话 ID(未知则 unknown)")
    p_save.add_argument("--trigger", default="manual",
                        choices=["manual", "auto-confirm", "auto-stage", "auto-fail"],
                        help="触发类型(默认 manual)")
    p_save.add_argument("--artifacts", nargs="*", default=[], help="已产出文件路径列表")
    p_save.add_argument("--context", default=None, help="上下文 JSON 字符串")
    p_save.add_argument("--task-tree", default=None, help="task-tree.json 路径")
    p_save.add_argument("--workflow-state", default=None, help="workflow 状态 JSON 字符串")
    p_save.set_defaults(func=cmd_save)

    # restore
    p_restore = sub.add_parser("restore", help="恢复快照")
    grp = p_restore.add_mutually_exclusive_group(required=True)
    grp.add_argument("--snapshot-id", default=None, help="快照 ID")
    grp.add_argument("--latest", action="store_true", help="取最新快照")
    p_restore.add_argument("--confirm", required=True, help="必须为 yes")
    p_restore.add_argument("--only", default=None,
                           choices=["task_tree", "artifacts", "context", "workflow"],
                           help="选择性恢复(默认全量)")
    p_restore.set_defaults(func=cmd_restore)

    # list
    p_list = sub.add_parser("list", help="列出快照")
    p_list.add_argument("--limit", type=int, default=20, help="返回条数(默认 20)")
    p_list.add_argument("--session-id", default=None, help="按会话过滤")
    p_list.set_defaults(func=cmd_list)

    # diff
    p_diff = sub.add_parser("diff", help="对比两快照差异")
    p_diff.add_argument("--snapshot-a", required=True, help="快照 A ID")
    p_diff.add_argument("--snapshot-b", required=True, help="快照 B ID")
    p_diff.set_defaults(func=cmd_diff)

    # clean
    p_clean = sub.add_parser("clean", help="清理过期快照")
    p_clean.add_argument("--retention-days", type=int, default=None,
                         help=f"保留天数(默认 {DEFAULT_RETENTION_DAYS})")
    p_clean.set_defaults(func=cmd_clean)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except Exception as e:
        print(f"WARNING: 未捕获异常:{e}", file=sys.stderr)
        return 0  # 快照失败不阻断主流程


if __name__ == "__main__":
    sys.exit(main())
