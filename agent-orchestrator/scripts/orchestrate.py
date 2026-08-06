#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""orchestrate.py - 多 Agent 协同编排脚本。

子命令:
  delegate  主 Agent 把任务委派给子 Agent
  collect   收集指定任务关联的所有 Agent 结果
  merge     聚合多 Agent 结果,处理冲突

设计原则(参照 skill-runtime/scripts/validate_runtime.py):
- 失败不抛异常,统一通过 error 字段与退出码表达
- 委派有超时(默认 300s),超时转人工裁决
- 结果冲突默认按优先级,可配置投票或人工裁决
- 消息日志保留 30 天,过期自动裁剪

产出:
  - agent-messages.json(消息日志,追加写)
  - orchestration-protocol.md(协议规范,首次委派时生成)

退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


# ---------- 常量 ----------

# 默认委派超时(秒)
DEFAULT_TIMEOUT = 300

# 消息日志文件名
MESSAGES_FILENAME = "agent-messages.json"

# 协议规范文件名
PROTOCOL_FILENAME = "orchestration-protocol.md"

# 默认冲突解决策略
DEFAULT_STRATEGY = "priority"

# 已知冲突解决策略
STRATEGIES = ("priority", "voting", "human")

# 消息日志保留天数
RETENTION_DAYS = 30


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


def _gen_correlation_id(messages):
    """自动生成关联任务 ID(T1/T2/...)。"""
    count = sum(1 for m in messages if m.get("type") == "delegate")
    return f"T{count + 1}"


def _messages_path(cwd=None):
    """返回消息日志路径(当前工作目录)。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    return out_dir / MESSAGES_FILENAME


def _protocol_path(cwd=None):
    """返回协议规范路径(当前工作目录)。"""
    out_dir = Path(cwd) if cwd else Path.cwd()
    return out_dir / PROTOCOL_FILENAME


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


# ---------- 协议文档生成 ----------

def _ensure_protocol(cwd=None):
    """首次委派时生成 orchestration-protocol.md(若不存在)。"""
    path = _protocol_path(cwd)
    if path.exists():
        return path
    content = _build_protocol_doc()
    path.write_text(content, encoding="utf-8")
    return path


def _build_protocol_doc():
    """构建协议规范文档内容。"""
    return """# Agent 协同协议规范 (orchestration-protocol)

> 本文件由 agent-orchestrator/scripts/orchestrate.py 首次委派时自动生成。
> 完整协议规范见 agent-orchestrator/references/agent-protocol.md。

## 一、消息格式

所有 Agent 间通信均采用以下 JSON 消息格式:

```json
{
  "msg_id": "M001",
  "from": "master-agent",
  "to": "sub-agent-1",
  "type": "delegate",
  "correlation_id": "T0",
  "payload": { "task": "...", "assigned_skill": "...", "deadline": "..." },
  "ack_required": true,
  "timestamp": "2026-08-06T10:00:00+08:00",
  "status": "pending"
}
```

字段说明:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| msg_id | string | 是 | 消息唯一标识(M001/M002/...) |
| from | string | 是 | 发送方 Agent 标识 |
| to | string | 是 | 接收方 Agent 标识 |
| type | enum | 是 | delegate/ack/result/query/notify/heartbeat |
| correlation_id | string | 是 | 关联任务 ID(同一任务的全部消息共享) |
| payload | object | 是 | 消息负载,结构随 type 而变 |
| ack_required | boolean | 否 | 是否需要接收方回 ack,默认 false |
| timestamp | string | 是 | ISO8601 带时区时间戳 |
| status | enum | 否 | pending/delivered/acknowledged/completed/failed |

## 二、消息类型

| type | 方向 | 用途 | payload 关键字段 |
|------|------|------|----------------|
| delegate | 主->从 | 任务委派 | task, assigned_skill, deadline |
| ack | 从->主 | 收到确认 | ack_for(msg_id) |
| result | 从->主 | 结果回传 | result, summary, status |
| query | 任一方 | 澄清询问 | question, about |
| notify | 任一方 | 通知(无需 ack) | event, detail |
| heartbeat | 任一方 | 心跳保活 | agent_state |

## 三、握手流程

1. 主 Agent 发 delegate 消息(ack_required=true)
2. 子 Agent 收到后回 ack 消息(ack_for=delegate 的 msg_id)
3. 子 Agent 执行完毕回 result 消息(correlation_id 一致)
4. 主 Agent 收集 result,按策略 merge

## 四、超时与降级

- 委派默认超时 300s,可在 payload.deadline 显式指定
- 超时未收到 result:标记 failed,转人工裁决(human 策略)
- 心跳间隔建议 60s,超过 2 个间隔未收到心跳视为掉线

## 五、冲突解决策略

| 策略 | 说明 | 适用 |
|------|------|------|
| priority(默认) | 按 Agent 优先级取首个非空结果 | 主从模式 |
| voting | 多数投票(相同结果占比 >50% 取胜) | 对等模式 |
| human | 转人工裁决,等待人工标注 | 冲突无法自动解决 |

## 六、日志保留

- 消息日志(agent-messages.json)保留 30 天
- 超过保留期的消息在下次写入时自动裁剪
- 协议规范文件(本文件)持久保留,不自动删除
"""


# ---------- 子命令:delegate ----------

def cmd_delegate(args):
    """delegate:主 Agent 把任务委派给子 Agent。"""
    messages = _load_messages()
    # 裁剪过期消息
    messages = _prune_expired(messages)

    msg_id = _gen_msg_id(messages)
    correlation_id = args.correlation_id or _gen_correlation_id(messages)

    # deadline 缺省时按 timeout 推算
    if args.deadline:
        deadline = args.deadline
    else:
        deadline = (_now_dt() + timedelta(seconds=args.timeout)).isoformat(timespec="seconds")

    payload = {
        "task": args.task,
        "assigned_skill": args.skill,
        "deadline": deadline,
    }

    message = {
        "msg_id": msg_id,
        "from": args.from_agent,
        "to": args.to_agent,
        "type": "delegate",
        "correlation_id": correlation_id,
        "payload": payload,
        "ack_required": args.ack,
        "timestamp": _now_iso(),
        "status": "pending",
    }

    messages.append(message)
    _save_messages(messages)
    # 首次委派时生成协议规范
    protocol_path = _ensure_protocol()

    # 控制台输出
    print(f"委派已发出  msg_id={msg_id}  correlation_id={correlation_id}")
    print(f"  from: {args.from_agent}  to: {args.to_agent}")
    print(f"  task: {args.task}")
    if args.skill:
        print(f"  assigned_skill: {args.skill}")
    print(f"  deadline: {deadline}")
    print(f"  ack_required: {args.ack}")
    print(f"  消息日志: {_messages_path()}")
    print(f"  协议规范: {protocol_path}")
    return 0


# ---------- 子命令:collect ----------

def cmd_collect(args):
    """collect:收集指定任务关联的所有 Agent 结果。"""
    messages = _load_messages()

    cid = args.correlation_id
    timeout = args.timeout

    # 筛选该 correlation_id 的 result 消息
    results = [
        m for m in messages
        if m.get("correlation_id") == cid and m.get("type") == "result"
    ]

    # 筛选该 correlation_id 的 delegate 消息(用于判断超时)
    delegates = [
        m for m in messages
        if m.get("correlation_id") == cid and m.get("type") == "delegate"
    ]

    # 判断超时:最早委派时间 + timeout 已过且结果数 < 委派数
    timeout_flag = False
    if delegates:
        earliest = None
        for d in delegates:
            ts = _parse_iso(d.get("timestamp", ""))
            if ts is not None and (earliest is None or ts < earliest):
                earliest = ts
        if earliest is not None:
            deadline_dt = earliest + timedelta(seconds=timeout)
            if _now_dt() > deadline_dt and len(results) < len(delegates):
                timeout_flag = True

    # 失败结果
    failed = [m for m in results if m.get("status") == "failed"]

    # 控制台输出
    print(f"收集任务 {cid} 的结果")
    print(f"  委派数: {len(delegates)}")
    print(f"  已收集结果: {len(results)}")
    print(f"  失败结果: {len(failed)}")
    if timeout_flag:
        print(f"  WARN  超时({timeout}s):部分结果未返回,建议转人工裁决")
    if results:
        print("\n结果明细:")
        for r in results:
            status = r.get("status", "unknown")
            print(f"  [{r.get('msg_id')}] from={r.get('from')}  status={status}")
            summary = r.get("payload", {}).get("summary", "")
            if summary:
                print(f"    summary: {summary}")

    # 退出码:有失败或超时返回 1,否则 0
    if failed or timeout_flag:
        return 1
    return 0


# ---------- 子命令:merge ----------

def cmd_merge(args):
    """merge:聚合多 Agent 结果,处理冲突。"""
    messages = _load_messages()
    cid = args.correlation_id
    strategy = args.strategy

    # 收集 result 消息
    results = [
        m for m in messages
        if m.get("correlation_id") == cid and m.get("type") == "result"
    ]

    if not results:
        print(f"FAIL  任务 {cid} 无结果可合并")
        return 1

    # 按 strategy 处理
    if strategy == "priority":
        merged, note = _merge_priority(results, args.priority_order)
    elif strategy == "voting":
        merged, note = _merge_voting(results)
    else:  # human
        merged, note = _merge_human(results, cid)

    # 控制台输出
    print(f"合并任务 {cid} 的结果(策略:{strategy})")
    print(f"  输入结果数: {len(results)}")
    print(f"  {note}")
    if merged is not None:
        print(f"  最终结果来源: {merged.get('from')}")
        print(f"  最终结果摘要: {merged.get('payload', {}).get('summary', '')}")
    else:
        print(f"  最终结果:待人工裁决")
    return 0


def _merge_priority(results, priority_order_str):
    """优先级合并:按 priority_order 取首个非空(非 failed)结果。"""
    if priority_order_str:
        order = [s.strip() for s in priority_order_str.split(",") if s.strip()]
    else:
        order = [r.get("from", "") for r in results]

    for agent in order:
        for r in results:
            if r.get("from") == agent and r.get("status") != "failed":
                return r, f"按优先级取 {agent} 的结果(优先级序列:{order})"
    # 全部失败:返回第一个
    return results[0], f"全部结果失败或为空,默认取首个({results[0].get('from')})"


def _merge_voting(results):
    """投票合并:相同结果摘要占比 >50% 取胜。"""
    valid = [r for r in results if r.get("status") != "failed"]
    if not valid:
        return results[0], "全部结果失败,默认取首个"

    # 按 summary 投票
    summaries = [r.get("payload", {}).get("summary", "") for r in valid]
    counter = Counter(summaries)
    top_summary, top_count = counter.most_common(1)[0]

    if top_count > len(valid) / 2:
        # 多数票
        for r in valid:
            if r.get("payload", {}).get("summary", "") == top_summary:
                return r, f"投票通过({top_count}/{len(valid)} 一致),取该结果"
    # 无多数票
    return None, f"投票未过半(最高 {top_count}/{len(valid)}),建议转人工裁决"


def _merge_human(results, cid):
    """人工裁决:不自动合并,标记待人工处理。"""
    print(f"\n待人工裁决的任务 {cid}:")
    for i, r in enumerate(results, 1):
        summary = r.get("payload", {}).get("summary", "")
        print(f"  [{i}] from={r.get('from')}  status={r.get('status', 'unknown')}")
        print(f"      summary: {summary}")
    print(f"  请人工选择最终结果(在 agent-messages.json 中标注 chosen=true)")
    return None, "已转人工裁决,等待标注"


# ---------- argparse ----------

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="orchestrate.py",
        description="多 Agent 协同编排脚本。委派任务/收集结果/合并冲突。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python orchestrate.py delegate --from master --to sub-1 "
            "--task \"生成蓝图\" --skill game-blueprint --ack\n"
            "  python orchestrate.py collect --correlation-id T1 --timeout 300\n"
            "  python orchestrate.py merge --correlation-id T1 "
            "--strategy priority --priority-order \"sub-1,sub-2\"\n"
            "\n退出码:0=成功;1=有错误;2=参数错误\n"
            "产出:当前工作目录下 agent-messages.json 与 orchestration-protocol.md"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    # delegate
    p_delegate = sub.add_parser("delegate", help="主 Agent 把任务委派给子 Agent")
    p_delegate.add_argument("--from", dest="from_agent", required=True, help="发送方 Agent 标识")
    p_delegate.add_argument("--to", dest="to_agent", required=True, help="接收方 Agent 标识")
    p_delegate.add_argument("--task", required=True, help="任务描述")
    p_delegate.add_argument("--skill", help="委派给哪个 skill(可选)")
    p_delegate.add_argument("--deadline", help="任务截止时间(ISO8601),缺省按 --timeout 推算")
    p_delegate.add_argument(
        "--correlation-id", dest="correlation_id",
        help="任务关联 ID(缺省自动生成 T1/T2/...)",
    )
    p_delegate.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"委派超时秒数(默认 {DEFAULT_TIMEOUT})",
    )
    p_delegate.add_argument("--ack", action="store_true", help="是否需要接收方回 ack")
    p_delegate.set_defaults(func=cmd_delegate)

    # collect
    p_collect = sub.add_parser("collect", help="收集指定任务关联的所有 Agent 结果")
    p_collect.add_argument("--correlation-id", dest="correlation_id", required=True, help="任务关联 ID")
    p_collect.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"超时秒数(默认 {DEFAULT_TIMEOUT})",
    )
    p_collect.set_defaults(func=cmd_collect)

    # merge
    p_merge = sub.add_parser("merge", help="聚合多 Agent 结果,处理冲突")
    p_merge.add_argument("--correlation-id", dest="correlation_id", required=True, help="任务关联 ID")
    p_merge.add_argument(
        "--strategy", choices=STRATEGIES, default=DEFAULT_STRATEGY,
        help=f"冲突解决策略(默认 {DEFAULT_STRATEGY})",
    )
    p_merge.add_argument(
        "--priority-order", dest="priority_order",
        help="逗号分隔的 Agent 优先级序列(仅 strategy=priority 用)",
    )
    p_merge.set_defaults(func=cmd_merge)

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
