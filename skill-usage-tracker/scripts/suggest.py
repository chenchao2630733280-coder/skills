#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suggest.py - Data 层优化建议生成脚本。

基于 usage-stats.json 生成优化建议 Markdown。
若 usage-stats.json 不存在,先跑 stats.py summary。

产出:optimization-suggestions.md
退出码:0=成功;1=有错误;2=参数错误
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

USAGE_DIR = Path.home() / ".trae-cn" / "usage"
STATS_FILE = USAGE_DIR / "usage-stats.json"
SUGGEST_FILE = USAGE_DIR / "optimization-suggestions.md"
LOCAL_TZ = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _load_stats():
    if not STATS_FILE.exists():
        return None, "usage-stats.json 不存在,请先运行 stats.py summary"
    try:
        return json.loads(STATS_FILE.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"读取 usage-stats.json 失败:{e}"


def generate_suggestions(stats):
    """根据统计数据生成建议列表。"""
    suggestions = []
    by_skill = stats.get("by_skill", [])

    # 1. 高失败率 skill
    high_fail = [s for s in by_skill if s.get("fail_rate", 0) > 0.1]
    for s in high_fail:
        suggestions.append({
            "priority": "P0",
            "skill": s["skill"],
            "issue": f"失败率 {s['fail_rate']:.1%}({s['calls']} 次调用)",
            "action": f"查 failure-casebook 看历史失败原因,优化 {s['skill']} 的错误处理",
        })

    # 2. 慢 skill
    slow = [s for s in by_skill if s.get("p95_ms", 0) > 60000]
    for s in slow:
        suggestions.append({
            "priority": "P1",
            "skill": s["skill"],
            "issue": f"P95 耗时 {s['p95_ms']}ms(超 60s 阈值)",
            "action": f"优化 {s['skill']} 性能,考虑加 runtime.yaml 声明 timeout 或拆分任务",
        })

    # 3. 高频 skill(调用次数最多 Top 3)
    by_calls = sorted(by_skill, key=lambda x: x.get("calls", 0), reverse=True)
    for s in by_calls[:3]:
        if s.get("calls", 0) > 10:
            suggestions.append({
                "priority": "P2",
                "skill": s["skill"],
                "issue": f"高频调用({s['calls']} 次)",
                "action": f"考虑缓存 {s['skill']} 产物或并行化调用",
            })

    # 4. 未使用 skill
    unused = stats.get("unused_skills", [])
    for skill in unused[:5]:
        suggestions.append({
            "priority": "P3",
            "skill": skill,
            "issue": "近期未调用",
            "action": f"评估 {skill} 是否需要归档或从索引移除",
        })

    return suggestions


def render_markdown(stats, suggestions):
    """渲染建议 Markdown。"""
    lines = [
        "# skill 优化建议",
        "",
        f"> 生成时间:{_now_iso()}",
        f"> 统计周期:{stats.get('period', 'all')}",
        f"> 总调用:{stats.get('total_calls', 0)}  成功率:{stats.get('success_rate', 0)}",
        "",
        "## 建议清单",
        "",
    ]

    if not suggestions:
        lines.append("暂无优化建议(各项指标正常)。")
    else:
        lines.append("| 优先级 | Skill | 问题 | 建议 |")
        lines.append("|--------|-------|------|------|")
        for s in suggestions:
            lines.append(f"| {s['priority']} | {s['skill']} | {s['issue']} | {s['action']} |")

    # 附加统计摘要
    lines.extend([
        "",
        "## 统计摘要",
        "",
        f"- 总调用数:{stats.get('total_calls', 0)}",
        f"- 成功率:{stats.get('success_rate', 0)}",
        f"- 平均耗时:{stats.get('avg_duration_ms', 0)}ms",
        f"- P95:{stats.get('p95_ms', 0)}ms",
        f"- P99:{stats.get('p99_ms', 0)}ms",
        "",
        "### 慢 skill(P95 > 60s)",
    ])
    slow = stats.get("slow_skills", [])
    if slow:
        for s in slow:
            lines.append(f"- {s}")
    else:
        lines.append("- 无")

    lines.extend(["", "### 高失败率 skill(>10%)"])
    high_fail = stats.get("high_fail_skills", [])
    if high_fail:
        for s in high_fail:
            lines.append(f"- {s}")
    else:
        lines.append("- 无")

    lines.extend(["", "### 未使用 skill"])
    unused = stats.get("unused_skills", [])
    if unused:
        for s in unused[:10]:
            lines.append(f"- {s}")
        if len(unused) > 10:
            lines.append(f"- ...(共 {len(unused)} 个)")
    else:
        lines.append("- 无")

    return "\n".join(lines)


def main(argv=None):
    parser = __import__("argparse").ArgumentParser(
        prog="suggest.py",
        description="Data 层优化建议生成脚本。",
        epilog="退出码:0=成功;1=有错误;2=参数错误",
    )
    parser.add_argument("--from", dest="from_date", default=None, help="开始日期(忽略,由 stats 决定)")
    parser.add_argument("--to", dest="to_date", default=None, help="结束日期(忽略,由 stats 决定)")
    args = parser.parse_args(argv)

    stats, err = _load_stats()
    if err:
        print(f"FAIL  {err}")
        return 1

    suggestions = generate_suggestions(stats)
    md = render_markdown(stats, suggestions)

    SUGGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUGGEST_FILE.write_text(md, encoding="utf-8")

    print(f"PASS  优化建议已生成:{SUGGEST_FILE}")
    print(f"  建议数:{len(suggestions)}")
    for s in suggestions[:5]:
        print(f"  [{s['priority']}] {s['skill']}: {s['issue']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
