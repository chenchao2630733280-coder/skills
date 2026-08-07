#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_usage.py - Data 自适应优化层脚本。

子命令:
  analyze  [--stats <usage-stats.json路径>]            分析统计数据,打印各 skill 运行特征
  suggest  [--stats <...>] [--output <目录>]           生成 tuning-suggestions.json + runtime-overrides.yaml
  apply    --overrides <yaml> --confirm yes             应用覆盖(需用户确认)
  revert   --backup <备份目录或文件>                    回退覆盖

退出码:0=成功;1=有错误;2=参数错误
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LOCAL_TZ = timezone(timedelta(hours=8))
USAGE_STATS_FILE = Path.home() / ".trae-cn" / "usage" / "usage-stats.json"
BACKUP_DIR = Path.home() / ".trae-cn" / "tuner-backups"

# 白名单:不参与自动调优(安全/稳定性考虑)
WHITELIST = {"guardrail", "skill-auditor", "diff-reviewer", "adaptive-tuner"}

# 默认 runtime 参数(未声明 runtime.yaml 的 skill 使用)
DEFAULT_TIMEOUT = 300
DEFAULT_RETRY_MAX = 0

# 调优约束
MAX_TIMEOUT_MULTIPLIER = 2          # timeout 上限 = 默认 × 2
MAX_RETRY = 5                        # retry.max 上限
MIN_SAMPLE_FOR_SUGGEST = 10          # 生成建议的最小样本数
SLOW_THRESHOLD_RATIO = 0.8           # P95 > timeout × 80% 触发调优
HIGH_FAIL_RATE = 0.10                # fail_rate > 10% 触发调优
VERY_HIGH_FAIL_RATE = 0.30           # fail_rate > 30% 不增加 retry


def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _read_stats(stats_path):
    """读取 usage-stats.json。"""
    p = Path(stats_path)
    if not p.exists():
        print(f"FAIL  统计数据不存在:{p}")
        print("请先运行:python skill-usage-tracker/scripts/stats.py summary")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL  解析统计数据失败:{e}")
        return None


def _calc_confidence(sample_count, durations):
    """计算置信度。"""
    if sample_count < MIN_SAMPLE_FOR_SUGGEST:
        return 0.0
    sample_factor = min(sample_count / 30.0, 1.0)
    # 方差惩罚
    if len(durations) < 2 or sum(durations) == 0:
        variance_penalty = 0.0
    else:
        mean = sum(durations) / len(durations)
        var = sum((d - mean) ** 2 for d in durations) / len(durations)
        variance = var / (mean ** 2) if mean else 0
        variance_penalty = min(variance / 2.0, 0.5)
    return round(sample_factor * (1 - variance_penalty), 3)


def _load_skill_runtime(skill_dir):
    """读取 skill 的 runtime.yaml(若存在),返回 dict。"""
    ws_dir = Path(__file__).resolve().parents[2]
    rt_file = ws_dir / skill_dir / "runtime.yaml"
    if not rt_file.exists():
        return None
    # 简单 YAML 解析(避免依赖 pyyaml)
    text = rt_file.read_text(encoding="utf-8")
    runtime = {"timeout": DEFAULT_TIMEOUT, "retry": {"max": DEFAULT_RETRY_MAX}}
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("timeout:"):
            try:
                runtime["timeout"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("max:"):
            try:
                runtime["retry"]["max"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return runtime


def _analyze_skill(skill_stat):
    """分析单个 skill,返回建议(或 None)。"""
    skill = skill_stat.get("skill", "")
    calls = skill_stat.get("calls", 0)
    p95_ms = skill_stat.get("p95_ms", 0)
    fail_rate = skill_stat.get("fail_rate", 0)
    avg_ms = skill_stat.get("avg_ms", 0)

    # 白名单跳过
    if skill in WHITELIST:
        return {"skill": skill, "skipped": True, "reason": "白名单(安全 skill 不调优)"}

    # 样本不足
    if calls < MIN_SAMPLE_FOR_SUGGEST:
        return {"skill": skill, "skipped": True, "reason": f"数据不足(<{MIN_SAMPLE_FOR_SUGGEST} 次调用)",
                "sample_count": calls}

    # 当前 runtime 参数
    runtime = _load_skill_runtime(skill)
    current_timeout = runtime["timeout"] if runtime else DEFAULT_TIMEOUT
    current_retry_max = runtime["retry"]["max"] if runtime else DEFAULT_RETRY_MAX

    # 置信度(简化:用 p95/avg 估算,实际应基于完整 durations 列表)
    # 由于 usage-stats 只提供 p95/avg,用 (p95/avg - 1) 作为方差代理
    variance_proxy = (p95_ms / avg_ms - 1) if avg_ms > 0 else 0
    confidence = _calc_confidence(calls, [avg_ms, p95_ms])
    # 修正:用 variance_proxy 调整
    confidence = round(confidence * (1 - min(variance_proxy / 2, 0.5)), 3)

    suggestions = []
    p95_sec = p95_ms / 1000.0

    # 1. timeout 调优
    if p95_sec > current_timeout * SLOW_THRESHOLD_RATIO:
        new_timeout = int((p95_sec * 1.5 + 29) // 30 * 30)  # 向上取整到 30 秒倍数
        new_timeout = min(new_timeout, current_timeout * MAX_TIMEOUT_MULTIPLIER)
        if new_timeout > current_timeout:
            suggestions.append({
                "field": "timeout",
                "current": current_timeout,
                "suggested": new_timeout,
                "reason": f"P95={int(p95_sec)}s 接近 timeout {current_timeout}s"
            })

    # 2. retry 调优
    if fail_rate > HIGH_FAIL_RATE and fail_rate <= VERY_HIGH_FAIL_RATE:
        new_retry = min(current_retry_max + 1, MAX_RETRY)
        if new_retry > current_retry_max:
            suggestions.append({
                "field": "retry.max",
                "current": current_retry_max,
                "suggested": new_retry,
                "reason": f"fail_rate={fail_rate:.1%}(>10%),建议增加重试"
            })
    elif fail_rate > VERY_HIGH_FAIL_RATE:
        suggestions.append({
            "field": "retry.max",
            "current": current_retry_max,
            "suggested": current_retry_max,  # 不增加
            "reason": f"fail_rate={fail_rate:.1%}(>30%),建议检查 skill 实现或增加降级(不自动增 retry)",
            "no_change": True
        })

    if not suggestions:
        return {"skill": skill, "skipped": True, "reason": "无需调优(参数合理)",
                "sample_count": calls}

    return {
        "skill": skill,
        "current": {"timeout": current_timeout, "retry": {"max": current_retry_max}},
        "suggestions": suggestions,
        "confidence": confidence,
        "sample_count": calls,
        "skipped": False,
    }


def cmd_analyze(args):
    """analyze:分析统计数据,打印各 skill 运行特征。"""
    stats_path = args.stats or str(USAGE_STATS_FILE)
    stats = _read_stats(stats_path)
    if stats is None:
        return 1

    by_skill = stats.get("by_skill", [])
    if not by_skill:
        print("无 skill 调用数据")
        return 0

    print(f"分析 {len(by_skill)} 个 skill 的运行特征:")
    print(f"{'skill':30s} | {'calls':>6s} | {'P95(ms)':>10s} | {'fail_rate':>10s} | {'状态'}")
    print("-" * 90)
    for s in by_skill:
        result = _analyze_skill(s)
        if result.get("skipped"):
            status = f"跳过:{result.get('reason', '')}"
        else:
            fields = [sg["field"] for sg in result["suggestions"]]
            status = f"建议调优:{','.join(fields)}(置信度 {result['confidence']})"
        print(f"{s.get('skill',''):30s} | {s.get('calls',0):6d} | "
              f"{s.get('p95_ms',0):10d} | {s.get('fail_rate',0):10.2%} | {status}")
    return 0


def cmd_suggest(args):
    """suggest:生成调优建议。"""
    stats_path = args.stats or str(USAGE_STATS_FILE)
    stats = _read_stats(stats_path)
    if stats is None:
        return 1

    by_skill = stats.get("by_skill", [])
    suggestions = []
    skipped = []

    for s in by_skill:
        result = _analyze_skill(s)
        if result.get("skipped"):
            skipped.append({
                "skill": result["skill"],
                "reason": result.get("reason", ""),
                "sample_count": result.get("sample_count", 0)
            })
        else:
            # 构建建议对象
            current = result["current"]
            suggested_timeout = current["timeout"]
            suggested_retry_max = current["retry"]["max"]
            reasons = []
            for sg in result["suggestions"]:
                if sg.get("no_change"):
                    reasons.append(sg["reason"])
                    continue
                if sg["field"] == "timeout":
                    suggested_timeout = sg["suggested"]
                elif sg["field"] == "retry.max":
                    suggested_retry_max = sg["suggested"]
                reasons.append(sg["reason"])

            suggestions.append({
                "skill": result["skill"],
                "current": current,
                "suggested": {
                    "timeout": suggested_timeout,
                    "retry": {"max": suggested_retry_max, "backoff": "exponential"}
                },
                "reason": "; ".join(reasons),
                "confidence": result["confidence"],
                "sample_count": result["sample_count"],
                "applied": False,
            })

    output = {
        "generated_at": _now_iso(),
        "data_source": str(stats_path),
        "total_skills_analyzed": len(by_skill),
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
        "skipped": skipped,
    }

    if args.output:
        out_dir = Path(args.output)
    else:
        # 默认输出到 workflow-runtime 的默认 overrides 查找路径
        out_dir = Path.home() / ".trae-cn" / "tuner-overrides"
    out_dir.mkdir(parents=True, exist_ok=True)

    suggestions_file = out_dir / "tuning-suggestions.json"
    suggestions_file.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    # 生成 runtime-overrides.yaml
    overrides_file = out_dir / "runtime-overrides.yaml"
    _write_overrides_yaml(overrides_file, output)

    print(f"PASS  生成调优建议:{len(suggestions)} 条")
    print(f"  跳过:{len(skipped)} 个 skill(白名单/数据不足/无需调优)")
    print(f"  建议清单:{suggestions_file}")
    print(f"  覆盖文件:{overrides_file}")
    return 0


def _write_overrides_yaml(path, output):
    """生成 runtime-overrides.yaml(简单文本拼接,无 pyyaml 依赖)。"""
    lines = [
        "# 由 adaptive-tuner 生成,供 workflow-runtime 应用",
        f"generated_at: \"{output['generated_at']}\"",
        f"data_source: \"{output['data_source']}\"",
        'tuner_version: "1.0"',
        "overrides:",
    ]
    for sg in output["suggestions"]:
        suggested = sg["suggested"]
        lines.append(f"  - skill: {sg['skill']}")
        lines.append(f"    timeout: {suggested['timeout']}")
        retry = suggested["retry"]
        lines.append(f"    retry:")
        lines.append(f"      max: {retry['max']}")
        lines.append(f"      backoff: {retry['backoff']}")
        # reason 转义引号
        reason = sg["reason"].replace('"', '\\"')
        lines.append(f"    reason: \"{reason}\"")
        lines.append(f"    confidence: {sg['confidence']}")
        lines.append(f"    sample_count: {sg['sample_count']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_apply(args):
    """apply:应用覆盖(需用户确认)。"""
    if args.confirm != "yes":
        print("FAIL  apply 需要用户确认:请传 --confirm yes")
        print("  示例:python analyze_usage.py apply --overrides runtime-overrides.yaml --confirm yes")
        return 1

    overrides_file = Path(args.overrides)
    if not overrides_file.exists():
        print(f"FAIL  覆盖文件不存在:{overrides_file}")
        return 1

    # 简单解析 overrides yaml(仅提取 skill + timeout + retry.max)
    overrides = _parse_overrides_yaml(overrides_file)
    if not overrides:
        print(f"FAIL  覆盖文件解析失败或无覆盖项:{overrides_file}")
        return 1

    # 备份目录
    timestamp = datetime.now(LOCAL_TZ).strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_DIR / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    ws_dir = Path(__file__).resolve().parents[2]
    results = []

    for ov in overrides:
        skill = ov["skill"]
        skill_dir = ws_dir / skill
        rt_file = skill_dir / "runtime.yaml"

        if not skill_dir.exists():
            results.append({"skill": skill, "status": "skip", "reason": "skill 目录不存在"})
            continue

        # 备份
        if rt_file.exists():
            backup_file = backup_dir / f"{skill}.yaml.bak"
            shutil.copy2(rt_file, backup_file)
        else:
            backup_file = backup_dir / f"{skill}.yaml.bak.missing"
            backup_file.write_text(f"# {skill} 无原 runtime.yaml(新建)", encoding="utf-8")

        # 应用覆盖(简单合并:修改 timeout/retry 行)
        _apply_override_to_runtime(rt_file, ov)
        results.append({"skill": skill, "status": "applied",
                        "backup": str(backup_file)})

    # 写 apply 结果
    result_file = backup_dir / "apply-result.json"
    result_file.write_text(json.dumps({
        "applied_at": _now_iso(),
        "overrides_file": str(overrides_file),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    applied = sum(1 for r in results if r["status"] == "applied")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"PASS  应用覆盖:{applied} 个 skill  跳过:{skipped}")
    print(f"  备份目录:{backup_dir}")
    print(f"  回退命令:python analyze_usage.py revert --backup {backup_dir}")
    return 0


def _parse_overrides_yaml(path):
    """简单解析 runtime-overrides.yaml(提取 skill/timeout/retry.max)。"""
    overrides = []
    current = None
    in_retry = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- skill:"):
            if current:
                overrides.append(current)
            current = {"skill": stripped.split(":", 1)[1].strip(), "timeout": None, "retry": {}}
            in_retry = False
        elif current and stripped.startswith("timeout:"):
            try:
                current["timeout"] = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass
            in_retry = False
        elif current and stripped == "retry:":
            in_retry = True
        elif current and in_retry and stripped.startswith("max:"):
            try:
                current["retry"]["max"] = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif current and stripped.startswith("backoff:"):
            current["retry"]["backoff"] = stripped.split(":", 1)[1].strip()
            in_retry = False
        elif not line.startswith(" ") and current:
            # 退出 override 项
            in_retry = False
    if current:
        overrides.append(current)
    return overrides


def _apply_override_to_runtime(rt_file, override):
    """把覆盖应用到 runtime.yaml(简单合并)。"""
    if rt_file.exists():
        lines = rt_file.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# runtime.yaml", f"# 由 adaptive-tuner 应用覆盖生成({_now_iso()})"]

    new_lines = []
    timeout_updated = False
    retry_max_updated = False
    in_retry = False

    for line in lines:
        stripped = line.split("#")[0].strip()
        if stripped.startswith("timeout:") and override.get("timeout") is not None:
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}timeout: {override['timeout']}  # adaptive-tuner 覆盖")
            timeout_updated = True
            continue
        if stripped == "retry:":
            in_retry = True
        elif in_retry and stripped.startswith("max:") and override.get("retry", {}).get("max") is not None:
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}  max: {override['retry']['max']}  # adaptive-tuner 覆盖")
            retry_max_updated = True
            continue
        elif not line.startswith(" ") and in_retry:
            in_retry = False
        new_lines.append(line)

    # 若 timeout 未更新且覆盖有值,追加
    if not timeout_updated and override.get("timeout") is not None:
        new_lines.append(f"timeout: {override['timeout']}  # adaptive-tuner 覆盖")
    if not retry_max_updated and override.get("retry", {}).get("max") is not None:
        if not any(l.strip().startswith("retry:") for l in new_lines):
            new_lines.append("retry:")
        new_lines.append(f"  max: {override['retry']['max']}  # adaptive-tuner 覆盖")

    rt_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def cmd_revert(args):
    """revert:回退覆盖。"""
    backup_path = Path(args.backup)
    if not backup_path.exists():
        print(f"FAIL  备份路径不存在:{backup_path}")
        return 1

    ws_dir = Path(__file__).resolve().parents[2]

    # 若是目录,遍历备份文件
    if backup_path.is_dir():
        backup_files = list(backup_path.glob("*.yaml.bak"))
    else:
        backup_files = [backup_path]

    if not backup_files:
        print(f"FAIL  备份目录无 .yaml.bak 文件:{backup_path}")
        return 1

    results = []
    for bf in backup_files:
        skill = bf.stem.replace(".yaml", "").replace(".bak", "")
        skill_dir = ws_dir / skill
        rt_file = skill_dir / "runtime.yaml"
        if not skill_dir.exists():
            results.append({"skill": skill, "status": "skip", "reason": "skill 目录不存在"})
            continue
        shutil.copy2(bf, rt_file)
        results.append({"skill": skill, "status": "reverted"})

    reverted = sum(1 for r in results if r["status"] == "reverted")
    print(f"PASS  回退覆盖:{reverted} 个 skill")
    for r in results:
        print(f"  {r['skill']}: {r['status']}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="analyze_usage.py",
        description="Data 自适应优化层脚本。分析 usage-tracker 数据生成调优建议。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码:0=成功;1=有错误;2=参数错误",
    )
    sub = parser.add_subparsers(dest="command", metavar="<子命令>")

    p_analyze = sub.add_parser("analyze", help="分析统计数据,打印各 skill 运行特征")
    p_analyze.add_argument("--stats", default=None, help="usage-stats.json 路径(默认 ~/.trae-cn/usage/)")
    p_analyze.set_defaults(func=cmd_analyze)

    p_suggest = sub.add_parser("suggest", help="生成调优建议")
    p_suggest.add_argument("--stats", default=None, help="usage-stats.json 路径")
    p_suggest.add_argument("--output", default=None, help="输出目录(默认 ~/.trae-cn/tuner-overrides/)")
    p_suggest.set_defaults(func=cmd_suggest)

    p_apply = sub.add_parser("apply", help="应用覆盖(需用户确认)")
    p_apply.add_argument("--overrides", required=True, help="runtime-overrides.yaml 路径")
    p_apply.add_argument("--confirm", required=True, help="必须传 yes 才执行")
    p_apply.set_defaults(func=cmd_apply)

    p_revert = sub.add_parser("revert", help="回退覆盖")
    p_revert.add_argument("--backup", required=True, help="备份目录或文件路径")
    p_revert.set_defaults(func=cmd_revert)

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
        print(f"FAIL  未捕获异常:{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
