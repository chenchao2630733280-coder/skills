#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""监控工具层只读查询脚本。

封装 logs / metrics / trace 三个子命令,通过标准库 urllib 请求监控平台 API。
平台配置从环境变量读取;平台不可用时降级为提示信息,不抛错。
产出 monitor-ops-report.json 到当前工作目录,并同时将 JSON report 输出到 stdout。

环境变量:
    MONITOR_PLATFORM : 监控平台标识(elk / grafana / jaeger / cloud ...)
    LOG_API_BASE     : 日志查询 API 基地址
    METRIC_API_BASE  : 指标查询 API 基地址
    TRACE_API_BASE   : 链路查询 API 基地址(可选,缺失时 trace 走提示降级)
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def _now_ts():
    """返回 ISO8601 风格的本地时间戳字符串。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _read_env():
    """读取平台相关环境变量,返回配置字典。"""
    return {
        "platform": os.environ.get("MONITOR_PLATFORM", "").strip(),
        "log_api_base": os.environ.get("LOG_API_BASE", "").strip(),
        "metric_api_base": os.environ.get("METRIC_API_BASE", "").strip(),
        "trace_api_base": os.environ.get("TRACE_API_BASE", "").strip(),
    }


def _http_get_json(url, timeout=5):
    """用标准库 urllib 发起 GET 请求并解析 JSON。

    返回 (data, error)。失败时 data 为 None,error 为错误描述字符串。
    """
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return [], None
            return json.loads(raw), None
    except urllib.error.URLError as exc:
        return None, "URLError: %s" % exc.reason
    except urllib.error.HTTPError as exc:
        return None, "HTTPError: %s" % exc.code
    except ValueError as exc:
        return None, "JSON解析失败: %s" % exc
    except Exception as exc:  # noqa: BLE001 - 降级,不抛错
        return None, "未知错误: %s" % exc


def _build_report(command, service, time_range, entries, error):
    """构造统一 report 结构。"""
    return {
        "command": command,
        "service": service,
        "timeRange": time_range,
        "entries": entries if entries is not None else [],
        "totalCount": len(entries) if entries else 0,
        "error": error,
        "timestamp": _now_ts(),
    }


def _emit_report(report):
    """将 report 写入 monitor-ops-report.json 并输出到 stdout。"""
    text = json.dumps(report, ensure_ascii=False, indent=2)
    report_path = "monitor-ops-report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        # 写文件失败不影响 stdout 输出
        sys.stderr.write("警告: 写入 %s 失败: %s\n" % (report_path, exc))
    sys.stdout.write(text + "\n")


def _degraded_report(command, service, time_range, hint):
    """平台不可用时的降级 report。"""
    msg = "监控平台不可用,请手动查询。提示: %s" % hint
    return _build_report(command, service, time_range, [], msg)


# ---------------------------------------------------------------------------
# 子命令实现:logs
# ---------------------------------------------------------------------------

def cmd_logs(args):
    """查询日志,支持关键词过滤。"""
    cfg = _read_env()
    service = args.service
    keyword = args.keyword
    limit = args.limit
    time_range = args.time_range

    # 平台未配置 -> 降级提示
    if not cfg["log_api_base"]:
        hint = "未配置 LOG_API_BASE 环境变量;请在 ELK/Grafana/云日志控制台手动检索服务 %s" % service
        return _degraded_report("logs", service, time_range, hint)

    base = cfg["log_api_base"].rstrip("/")
    query = {
        "service": service,
        "limit": str(limit),
        "time_range": time_range,
    }
    if keyword:
        query["keyword"] = keyword
    url = base + "/logs?" + urllib.parse.urlencode(query)

    data, error = _http_get_json(url)
    if error:
        return _degraded_report("logs", service, time_range,
                                "请求日志 API 失败(%s)。可改在控制台手动检索。" % error)

    # 规范化为 entries 列表
    entries = data if isinstance(data, list) else data.get("entries", []) if isinstance(data, dict) else []
    # 客户端二次关键词过滤(平台过滤不可靠时兜底)
    if keyword:
        entries = [e for e in entries if keyword in json.dumps(e, ensure_ascii=False)]
    entries = entries[:limit]
    return _build_report("logs", service, time_range, entries, None)


# ---------------------------------------------------------------------------
# 子命令实现:metrics
# ---------------------------------------------------------------------------

def cmd_metrics(args):
    """查询指标(cpu/memory/qps/error_rate)。"""
    cfg = _read_env()
    service = args.service
    metric = args.metric
    time_range = args.time_range

    if not cfg["metric_api_base"]:
        hint = "未配置 METRIC_API_BASE 环境变量;请在 Grafana/云监控控制台手动查看 %s 的 %s 指标" % (service, metric)
        return _degraded_report("metrics", service, time_range, hint)

    base = cfg["metric_api_base"].rstrip("/")
    query = {
        "service": service,
        "metric": metric,
        "time_range": time_range,
    }
    url = base + "/metrics?" + urllib.parse.urlencode(query)

    data, error = _http_get_json(url)
    if error:
        return _degraded_report("metrics", service, time_range,
                                "请求指标 API 失败(%s)。可改在 Grafana 控制台查看。" % error)

    entries = data if isinstance(data, list) else data.get("entries", []) if isinstance(data, dict) else []
    return _build_report("metrics", service, time_range, entries, None)


# ---------------------------------------------------------------------------
# 子命令实现:trace
# ---------------------------------------------------------------------------

def cmd_trace(args):
    """查询链路,可指定 trace_id,默认最近 10 条。"""
    cfg = _read_env()
    service = args.service
    trace_id = args.trace_id
    limit = args.limit
    time_range = args.time_range

    if not cfg["trace_api_base"]:
        hint = "未配置 TRACE_API_BASE 环境变量;请在 Jaeger/云链路控制台手动查询服务 %s" % service
        return _degraded_report("trace", service, time_range, hint)

    base = cfg["trace_api_base"].rstrip("/")
    query = {
        "service": service,
        "limit": str(limit),
        "time_range": time_range,
    }
    if trace_id:
        query["trace_id"] = trace_id
    url = base + "/traces?" + urllib.parse.urlencode(query)

    data, error = _http_get_json(url)
    if error:
        return _degraded_report("trace", service, time_range,
                                "请求链路 API 失败(%s)。可改在 Jaeger 控制台手动查询。" % error)

    entries = data if isinstance(data, list) else data.get("entries", []) if isinstance(data, dict) else []
    entries = entries[:limit]
    return _build_report("trace", service, time_range, entries, None)


# ---------------------------------------------------------------------------
# 入口与参数解析
# ---------------------------------------------------------------------------

def build_parser():
    """构造 argparse 解析器,支持 logs/metrics/trace 子命令。"""
    parser = argparse.ArgumentParser(
        prog="monitor_ops.py",
        description="监控工具层只读查询:logs / metrics / trace。纯只读,平台不可用时降级为提示。",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")
    sub.required = True

    # logs 子命令
    p_logs = sub.add_parser("logs", help="查询服务日志(默认最近 100 条)")
    p_logs.add_argument("--service", required=True, help="服务名")
    p_logs.add_argument("--keyword", default=None, help="日志关键词过滤(可选)")
    p_logs.add_argument("--limit", type=int, default=100, help="返回条数,默认 100")
    p_logs.add_argument("--time-range", default="1h", help="时间范围,默认 1h")
    p_logs.set_defaults(func=cmd_logs)

    # metrics 子命令
    p_metrics = sub.add_parser("metrics", help="查询服务指标(cpu/memory/qps/error_rate)")
    p_metrics.add_argument("--service", required=True, help="服务名")
    p_metrics.add_argument("--metric", required=True,
                           choices=["cpu", "memory", "qps", "error_rate"],
                           help="指标名: cpu/memory/qps/error_rate")
    p_metrics.add_argument("--time-range", default="1h", help="时间范围,默认 1h")
    p_metrics.set_defaults(func=cmd_metrics)

    # trace 子命令
    p_trace = sub.add_parser("trace", help="查询链路(默认最近 10 条)")
    p_trace.add_argument("--service", required=True, help="服务名")
    p_trace.add_argument("--trace-id", default=None, help="指定 trace id(可选)")
    p_trace.add_argument("--limit", type=int, default=10, help="返回条数,默认 10")
    p_trace.add_argument("--time-range", default="1h", help="时间范围,默认 1h")
    p_trace.set_defaults(func=cmd_trace)

    return parser


def main():
    """脚本入口:解析参数、执行子命令、输出 report。"""
    parser = build_parser()
    args = parser.parse_args()
    report = args.func(args)
    _emit_report(report)


if __name__ == "__main__":
    main()
