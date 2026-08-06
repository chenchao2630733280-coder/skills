#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""message_bus.py - Agent 消息总线脚本。

子命令:
  send     发送消息到消息总线
  receive  拉取待处理消息(按 to/correlation_id/type 过滤)
  history  查询消息历史

设计原则(参照 skill-runtime/scripts/validate_runtime.py):
- 失败不抛异常,统一通过 error 字段与退出码表达
- 消息日志保留 30 天,过期自动裁剪
- receive 拉取后不删除消息(只标记 delivered),便于历史追溯

产出:agent-messages.json(消息日志,追加写)
退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ---------- 常量 ----------

MESSAGES_FILENAME = "agent-messages.json"
RETENTION_DAYS = 30

# 已知消息类型
MSG_TYPES = ("delegate", "ack", "result", "query", "notify", "heartbeat")

# receive 默认拉取上限
DEFAULT_RECEIVE_LIMIT = 10

# history 默认返回上限
DEFAULT_HISTORY_LIMIT = 50


# ---------- 工具函数 ----------

def _now_iso():
    """返回当前 ISO8601 带本地时区的时间戳。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _now_dt():
    """返回当前带时区的 datetime。"""
    return datetime.now().astimezone()


def _parse_iso(s):
    """解析 ISO8601 时间字符串,失败返回 None。"""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _gen_msg_id(messages):
    """根据现有消息列表生成下一个 msg_id(M001/M002/...)。"""
    max_num = 0
    for m in messages:
        mid = m.get("msg_id", "")
        if isinstance(mid, str) and mid.startswith("M") and mid[1:].isdigit():
            num = int(mid[1:])
            if num > max_num:
                max_num = num
    return f"M{max_num + 1:03d}"


def _messages_path(cwd=None):
    """返回消息日志路径(当前工作目录)。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    return out_dir / MESSAGES_FILENAME


def _load_messages(cwd=None):
    """加载消息日志。不存在或损坏返回空列表。"""
    path = _messages_path(cwd)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "messages" in data:
            msgs = data["messages"]
            return msgs if isinstance(msgs, list) else []
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_messages(messages, cwd=None):
    """保存消息日志。"""
    path = _messages_path(cwd)
    doc = {
        "version": "1.0",
        "retention_days": RETENTION_DAYS,
        "messages": messages,
        "updated_at": _now_iso(),
    }
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _prune_expired(messages):
    """裁剪超过保留期的消息(按 timestamp 字段)。"""
    cutoff = _now_dt() - timedelta(days=RETENTION_DAYS)
    kept = []
    for m in messages:
        ts = _parse_iso(m.get("timestamp", ""))
        if ts is None:
            # 无时间戳的消息保留(避免误删)
            kept.append(m)
            continue
        if ts >= cutoff:
            kept.append(m)
    return kept


# ---------- 子命令:send ----------

def cmd_send(args):
    """send:发送消息到消息总线。"""
    messages = _load_messages()
    messages = _prune_expired(messages)

    # 解析 payload
    try:
        payload = json.loads(args.payload)
    except Exception as e:
        print(f"FAIL  payload 不是合法 JSON:{e}")
        return 1

    if not isinstance(payload, dict):
        print("FAIL  payload 必须是 JSON 对象")
        return 1

    msg_id = _gen_msg_id(messages)
    message = {
        "msg_id": msg_id,
        "from": args.from_agent,
        "to": args.to_agent,
        "type": args.type,
        "correlation_id": args.correlation_id,
        "payload": payload,
        "ack_required": args.ack,
        "timestamp": _now_iso(),
        "status": "pending",
    }

    messages.append(message)
    _save_messages(messages)

    print(f"消息已发送  msg_id={msg_id}")
    print(f"  from: {args.from_agent}  to: {args.to_agent}  type: {args.type}")
    print(f"  correlation_id: {args.correlation_id}")
    print(f"  ack_required: {args.ack}")
    print(f"  消息日志: {_messages_path()}")
    return 0


# ---------- 子命令:receive ----------

def cmd_receive(args):
    """receive:拉取待处理消息(按 to/correlation_id/type 过滤)。"""
    messages = _load_messages()

    # 过滤:只拉取 pending / delivered 状态的消息
    matched = []
    for m in messages:
        if m.get("status") not in ("pending", "delivered"):
            # 已完成/失败的消息不再拉取
            continue
        if args.to_agent and m.get("to") != args.to_agent:
            continue
        if args.correlation_id and m.get("correlation_id") != args.correlation_id:
            continue
        if args.type and m.get("type") != args.type:
            continue
        matched.append(m)

    # 限制条数
    matched = matched[: args.limit]

    # 标记为 delivered(不删除,便于历史追溯);peek 模式不标记
    if matched and not args.peek:
        msg_ids = {m["msg_id"] for m in matched}
        for m in messages:
            if m.get("msg_id") in msg_ids and m.get("status") == "pending":
                m["status"] = "delivered"
        _save_messages(messages)

    # 控制台输出
    print(f"拉取消息  命中:{len(matched)}")
    if args.peek:
        print("  (peek 模式:不标记 delivered)")
    for m in matched:
        print(f"  [{m.get('msg_id')}] type={m.get('type')}  "
              f"from={m.get('from')}  to={m.get('to')}")
        print(f"    correlation_id: {m.get('correlation_id', '')}")
        print(f"    status: {m.get('status', 'unknown')}")
        print(f"    timestamp: {m.get('timestamp', '')}")
    return 0


# ---------- 子命令:history ----------

def cmd_history(args):
    """history:查询消息历史。"""
    messages = _load_messages()

    # 过滤
    matched = []
    since_dt = _parse_iso(args.since) if args.since else None
    for m in messages:
        if args.from_agent and m.get("from") != args.from_agent:
            continue
        if args.to_agent and m.get("to") != args.to_agent:
            continue
        if args.correlation_id and m.get("correlation_id") != args.correlation_id:
            continue
        if args.type and m.get("type") != args.type:
            continue
        if since_dt is not None:
            ts = _parse_iso(m.get("timestamp", ""))
            if ts is None or ts < since_dt:
                continue
        matched.append(m)

    # 限制条数
    matched = matched[: args.limit]

    # 控制台输出
    print(f"历史查询  命中:{len(matched)}")
    for m in matched:
        print(f"  [{m.get('msg_id')}] {m.get('timestamp', '')}  "
              f"type={m.get('type')}  {m.get('from')}->{m.get('to')}")
        print(f"    correlation_id: {m.get('correlation_id', '')}  "
              f"status: {m.get('status', 'unknown')}")
    return 0


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="message_bus.py",
        description="Agent 消息总线脚本。发送/接收/查询消息。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python message_bus.py send --from sub-1 --to master --type result "
            "--correlation-id T1 --payload '{\"summary\":\"蓝图已生成\"}'\n"
            "  python message_bus.py receive --to sub-1 --type delegate\n"
            "  python message_bus.py history --correlation-id T1 --limit 20\n"
            "\n退出码:0=成功;1=有错误;2=参数错误\n"
            "产出:当前工作目录下 agent-messages.json"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # send
    p_send = sub.add_parser("send", help="发送消息到消息总线")
    p_send.add_argument("--from", dest="from_agent", required=True, help="发送方 Agent 标识")
    p_send.add_argument("--to", dest="to_agent", required=True, help="接收方 Agent 标识")
    p_send.add_argument(
        "--type", required=True, choices=MSG_TYPES,
        help=f"消息类型: {MSG_TYPES}",
    )
    p_send.add_argument("--correlation-id", dest="correlation_id", required=True, help="任务关联 ID")
    p_send.add_argument("--payload", required=True, help="消息负载(JSON 字符串)")
    p_send.add_argument("--ack", action="store_true", help="是否需要接收方回 ack")
    p_send.set_defaults(func=cmd_send)

    # receive
    p_receive = sub.add_parser("receive", help="拉取待处理消息")
    p_receive.add_argument("--to", dest="to_agent", help="按接收方过滤")
    p_receive.add_argument("--correlation-id", dest="correlation_id", help="按任务关联 ID 过滤")
    p_receive.add_argument("--type", choices=MSG_TYPES, help="按消息类型过滤")
    p_receive.add_argument(
        "--limit", type=int, default=DEFAULT_RECEIVE_LIMIT,
        help=f"最多拉取条数(默认 {DEFAULT_RECEIVE_LIMIT})",
    )
    p_receive.add_argument("--peek", action="store_true", help="peek 模式:只看不标记 delivered")
    p_receive.set_defaults(func=cmd_receive)

    # history
    p_history = sub.add_parser("history", help="查询消息历史")
    p_history.add_argument("--from", dest="from_agent", help="按发送方过滤")
    p_history.add_argument("--to", dest="to_agent", help="按接收方过滤")
    p_history.add_argument("--correlation-id", dest="correlation_id", help="按任务关联 ID 过滤")
    p_history.add_argument("--type", choices=MSG_TYPES, help="按消息类型过滤")
    p_history.add_argument("--since", help="起始时间(ISO8601,含)")
    p_history.add_argument(
        "--limit", type=int, default=DEFAULT_HISTORY_LIMIT,
        help=f"最多返回条数(默认 {DEFAULT_HISTORY_LIMIT})",
    )
    p_history.set_defaults(func=cmd_history)

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
        # 兜底:任何未捕获异常都返回 exit 1,不抛出阻断调用方
        print(f"FAIL  未捕获异常:{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
