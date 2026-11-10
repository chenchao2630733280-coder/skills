"""评审报告与机器可读产物的输出。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .schema import FEATURE_LABELS

TYPE_LABELS = {
    "CLIFF": "跳崖",
    "DIP": "断崖回落",
    "OVERLOAD": "多维同升",
    "MECHANIC_SPIKE": "机制与难度同挤一关",
    "SAWTOOTH": "锯齿震荡",
    "PLATEAU": "长期平推",
    "BAND_MISS": "偏离阶段目标",
    "NEAR_UNWINNABLE": "近似无解",
    "UNSTABLE": "随机性不稳定",
    "OVERLOAD_COGNITIVE": "认知过载",
    "MECHANIC_FIRST_HARD": "新机制首发过难",
    "CONFIG_OUTLIER": "参数疑似漏改",
    "DATA_GAP": "样本不足",
    "PRED_ACTUAL_DIVERGENCE": "预测与实际背离",
    "BLOCKER": "流失卡点",
}


def write_all(out_dir, campaign, curve, records, jumps, sim, diagnostics, recs, actuals) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_csv(
        out / "curve.csv",
        ["index", "level_id", "phase", "shape", "target_win", "target_score", "pred_win", "delta_win", "score", "tag"],
        [
            {
                "index": r["index"],
                "level_id": r["level_id"],
                "phase": _curve_row(curve, r["level_id"], "phase"),
                "shape": _curve_row(curve, r["level_id"], "shape"),
                "target_win": f"{r['target_win']:.4f}",
                "target_score": f"{r['target_score']:.4f}",
                "pred_win": f"{r['pred_win']:.4f}",
                "delta_win": f"{r['pred_win'] - r['target_win']:+.4f}",
                "score": f"{r['score']:.4f}",
                "tag": r.get("tag", ""),
            }
            for r in records
        ],
    )

    _write_csv(
        out / "jumps.csv",
        ["type", "severity", "index", "level_id", "evidence", "detail"],
        [{**j, "type": j["type"], "evidence": _kv(j["evidence"])} for j in jumps],
    )

    sim_rows = []
    for lid, per_seg in sim.items():
        for seg, m in per_seg.items():
            sim_rows.append({"level_id": lid, "segment": seg, **m})
    if sim_rows:
        headers = ["level_id", "segment", "first_try_rate", "clear_rate", "quit_rate", "attempts_p50", "boosters_per_player", "batch_p10", "batch_p90", "batch_sd"]
        _write_csv(out / "simulation.csv", headers, sim_rows)

    _write_csv(
        out / "diagnosis.csv",
        ["type", "severity", "index", "level_id", "evidence", "detail"],
        [{**d, "evidence": _kv(d["evidence"])} for d in diagnostics],
    )

    rec_rows = []
    for item in recs:
        if not item["options"]:
            rec_rows.append(
                {
                    "level_id": item["level_id"],
                    "index": item["index"],
                    "gap_win": f"{item['gap_win']:+.3f}",
                    "param": "—",
                    "from": "",
                    "to": "",
                    "pct_change": "",
                    "delta_abs": "",
                    "expected_win": "",
                    "note": item.get("escalate") or "无可用单参数方案",
                }
            )
            continue
        for rank, opt in enumerate(item["options"], 1):
            rec_rows.append(
                {
                    "level_id": item["level_id"],
                    "index": item["index"],
                    "gap_win": f"{item['gap_win']:+.3f}",
                    "param": f"{opt['param']} ({opt.get('scope', '方案')}{rank})",
                    "from": opt["from"],
                    "to": opt["to"],
                    "pct_change": f"{opt['pct_change']:+.1%}",
                    "delta_abs": f"{opt['delta_abs']:+g}",
                    "expected_win": f"{opt['new_win']:.3f}",
                    "note": "落带" if opt["in_band"] else "未落带，需复核",
                }
            )
    _write_csv(out / "recommendations.csv", ["level_id", "index", "gap_win", "param", "from", "to", "delta_abs", "pct_change", "expected_win", "note"], rec_rows)

    payload = {
        "campaign": {
            "campaign_id": campaign.campaign_id,
            "genre": campaign.genre,
            "version": campaign.version,
            "data_source": campaign.data_source,
            "levels": len(campaign.levels),
            "segments": {k: {"theta": v.theta, "theta_sd": v.theta_sd} for k, v in campaign.segments.items()},
            "ref_segment": campaign.ref_segment,
            "spread": campaign.spread,
        },
        "curve": curve,
        "levels": [
            {
                "index": r["index"],
                "level_id": r["level_id"],
                "score": round(r["score"], 4),
                "features": {k: round(v, 4) for k, v in r["features"].items()},
                "pred_win": round(r["pred_win"], 4),
                "target_win": round(r["target_win"], 4),
                "pred_by_segment": {k: round(v, 4) for k, v in r["pred_by_segment"].items()},
            }
            for r in records
        ],
        "jumps": jumps,
        "simulation": sim,
        "actuals": actuals or {},
        "diagnostics": diagnostics,
        "recommendations": recs,
        "gate": _gate(diagnostics),
    }
    (out / "review.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "review.md").write_text(render_markdown(payload, campaign, curve, records, sim, actuals), encoding="utf-8")
    return payload


def render_markdown(payload, campaign, curve, records, sim, actuals) -> str:
    th = campaign.thresholds
    ref = campaign.ref_segment
    diags = payload["diagnostics"]
    recs = payload["recommendations"]
    jumps = payload["jumps"]
    counts = {s: sum(1 for d in diags if d["severity"] == s) for s in ("HIGH", "WARN", "INFO")}
    gate = payload["gate"]

    lines = []
    lines.append(f"# 关卡难度评审报告 · {campaign.campaign_id}")
    lines.append("")
    lines.append(
        f"- 品类：`{campaign.genre}`　版本：`{campaign.version}`　关卡数：{len(campaign.levels)}　"
        f"参考分层：`{ref}`"
    )
    lines.append(
        f"- 数据来源：`{campaign.data_source}`　"
        + ("真实通关数据：已接入" if actuals else "真实通关数据：未接入（纯模型预测）")
    )
    lines.append(
        f"- 门禁结果：**{gate['status']}**（HIGH {counts['HIGH']} / WARN {counts['WARN']} / INFO {counts['INFO']}）"
    )
    lines.append("")
    lines.append("> 本报告中的阈值、权重、θ 与模拟参数都是**待校准的占位假设**，不是行业标准。")
    lines.append("> 模拟是替代模型，用于排序和发现风险，不能替代真机测试与真实玩家数据。")
    lines.append("")

    # ---- 摘要 ----
    lines.append("## 1. 结论摘要")
    lines.append("")
    hardest = min(records, key=lambda r: r["pred_win"])
    easiest = max(records, key=lambda r: r["pred_win"])
    lines.append(
        f"- 预测最难：**{hardest['level_id']}**（{ref} 首次通关率 {hardest['pred_win']:.1%}，"
        f"目标 {hardest['target_win']:.1%}）；最易：**{easiest['level_id']}**（{easiest['pred_win']:.1%}）。"
    )
    off_band = [r for r in records if abs(r["pred_win"] - r["target_win"]) > th["band_tolerance"]]
    lines.append(f"- 偏离阶段目标带（±{th['band_tolerance']:.0%}）的关卡：{len(off_band)} / {len(records)}。")
    if jumps:
        by_type = {}
        for j in jumps:
            by_type[j["type"]] = by_type.get(j["type"], 0) + 1
        lines.append("- 跳变：" + "、".join(f"{TYPE_LABELS.get(k, k)} {v} 处" for k, v in by_type.items()) + "。")
    top = [d for d in diags if d["severity"] == "HIGH"][:3]
    if top:
        lines.append("- 优先处理：" + "；".join(f"{d['level_id']}（{TYPE_LABELS.get(d['type'], d['type'])}）" for d in top) + "。")
    else:
        lines.append("- 无 HIGH 级问题，可按 WARN 逐条复核。")
    lines.append("")

    # ---- 曲线 ----
    lines.append("## 2. 目标曲线与预测")
    lines.append("")
    rows = []
    for r in records:
        c = _curve_row(curve, r["level_id"], None) or {}
        rows.append(
            [
                r["index"],
                r["level_id"],
                c.get("phase", ""),
                f"{r['target_win']:.0%}",
                f"{r['pred_win']:.0%}",
                f"{r['pred_win'] - r['target_win']:+.0%}",
                f"{r['score']:.3f}",
                r.get("tag", ""),
            ]
        )
    lines.append(_table(["#", "关卡", "阶段", "目标首通", "预测首通", "偏差", "难度分", "标签"], rows))
    lines.append("")

    # ---- 模拟 ----
    lines.append("## 3. 不同水平玩家模拟表现")
    lines.append("")
    seg_names = list(campaign.segments)
    rows = []
    for r in records:
        cells = [r["index"], r["level_id"]]
        for seg in seg_names:
            m = sim.get(r["level_id"], {}).get(seg, {})
            cells.append(f"{m.get('first_try_rate', 0):.0%}/{m.get('clear_rate', 0):.0%}")
        m_ref = sim.get(r["level_id"], {}).get(ref, {})
        cells.append(f"{m_ref.get('attempts_p50', 0):.1f}")
        cells.append(f"{m_ref.get('boosters_per_player', 0):.2f}")
        cells.append("是" if m_ref.get("batch_sd", 0) > th["unstable_sd"] else "")
        rows.append(cells)
    lines.append(_table(["#", "关卡"] + [f"{s} 首通/终通" for s in seg_names] + ["尝试P50", "道具/人", "波动大"], rows))
    lines.append("")
    lines.append(
        f"模拟配置：每分层 {campaign.simulation['players_per_segment']} 名虚拟玩家 × {campaign.simulation['batches']} 个种子批次，"
        f"尝试上限 {campaign.simulation['max_attempts']} 次，含尝试间学习与道具软辅助。"
    )
    lines.append("")

    # ---- 跳变 ----
    lines.append("## 4. 相邻难度跳变")
    lines.append("")
    if jumps:
        lines.append(_table(["类型", "级别", "关卡", "证据", "说明"],
                             [[TYPE_LABELS.get(j["type"], j["type"]), j["severity"], j["level_id"], _kv(j["evidence"]), j["detail"]] for j in jumps]))
    else:
        lines.append("未检出超过阈值的跳变。")
    lines.append("")

    # ---- 异常 ----
    lines.append("## 5. 异常与卡点诊断")
    lines.append("")
    if diags:
        lines.append(_table(["严重度", "类型", "关卡", "证据", "判断"],
                             [[d["severity"], TYPE_LABELS.get(d["type"], d["type"]), d["level_id"], _kv(d["evidence"]), d["detail"]] for d in diags]))
    else:
        lines.append("未检出异常。")
    lines.append("")

    # ---- 建议 ----
    lines.append("## 6. 参数调整建议（单变量，待验证）")
    lines.append("")
    if not recs:
        lines.append("所有关卡均在目标带内，或问题不属于数值层面。")
    for item in recs:
        lines.append(f"### {item['level_id']}（#{item['index']}）　预测 {item['pred_win']:.0%} → 目标 {item['target_win']:.0%}　差 {item['gap_win']:+.0%}")
        lines.append("")
        if item["options"]:
            for rank, opt in enumerate(item["options"], 1):
                seg_txt = "，".join(f"{k} {v:.0%}" for k, v in opt["segment_win"].items())
                lines.append(
                    f"- **{opt.get('scope', '方案')}方案**：`{opt['param']}` {opt['from']} → {opt['to']}"
                    f"（{opt['delta_abs']:+g}，{opt['pct_change']:+.0%}｜{opt['dim_label']}）"
                    f" → 参考分层预测 {opt['new_win']:.0%}（{opt['delta_win']:+.0%}）"
                    f"{'，落带' if opt['in_band'] else '，未落带'}"
                )
                lines.append(f"  - 各分层预测：{seg_txt}")
                lines.append(f"  - 副作用：{'；'.join(opt['side_effects'])}")
        else:
            lines.append("- 无可用的单参数方案。")
        if item.get("escalate"):
            lines.append(f"- **升级建议**：{item['escalate']}")
        if item.get("blocked_knobs"):
            for b in item["blocked_knobs"]:
                lines.append(f"- 已排除旋钮 `{b['param']}`：{b['reason']}")
        lines.append("")
    lines.append("验证方式：单变量 A/B 或灰度，观察首次通关率、失败进度分布、道具使用率与下一关继续率；")
    lines.append("护栏指标恶化则回滚，不要以通关率单项作为成功标准。")
    lines.append("")

    # ---- 数据校准 ----
    next_no = 7
    if actuals:
        lines.append(f"## {next_no}. 预测 vs 实际")
        lines.append("")
        rows = []
        for r in records:
            a = actuals.get(r["level_id"])
            if not a:
                rows.append([r["level_id"], "—", "—", "—", "—"])
                continue
            rows.append(
                [r["level_id"], str(a["n_players"]), f"{a['first_try_rate']:.0%}", f"{r['pred_win']:.0%}",
                 f"{a['first_try_rate'] - r['pred_win']:+.0%}"]
            )
        lines.append(_table(["关卡", "样本", "实际首通", "预测首通", "差值"], rows))
        lines.append("")
        lines.append(f"样本量低于 {th['min_sample']} 的关卡不参与结论；差值 ≥15% 的关卡已在诊断中标为「预测与实际背离」，")
        lines.append("处理顺序是**先查模型与埋点口径，再改关卡**。")
        lines.append("")
        next_no += 1

    # ---- 假设 ----
    lines.append(f"## {next_no}. 假设、置信度与边界")
    lines.append("")
    lines.append(_table(
        ["项目", "当前取值", "状态", "如何校准"],
        [
            ["难度分→logit 的 spread", f"{campaign.spread}", "占位假设", "用真实通关率做逻辑回归拟合"],
            ["分层能力 θ", "、".join(f"{k}:{v.theta:+.2f}" for k, v in campaign.segments.items()), "占位假设", "用玩家历史表现做 Rasch/Elo 估计"],
            [
                "维度权重",
                "、".join(
                    f"{FEATURE_LABELS[k]}{v:.2f}"
                    for k, v in list(campaign.weights.items())[:3]
                ) + f" 等 {len(campaign.weights)} 项",
                "专家先验",
                "专家标注 + 数据拟合双向校准",
            ],
            ["参数→维度敏感度", "knobs.per_unit", "占位假设", "单变量实验测边际效应"],
            ["模拟参数", f"学习 {campaign.simulation['learning_logit']}，道具率 {campaign.simulation['booster_rate']}", "占位假设", "用重试/道具行为反推"],
        ],
    ))
    lines.append("")
    lines.append("置信度分级：模拟排序 > 跳变方向 > 绝对通关率。**绝对数值不可直接对外承诺。**")
    lines.append("")

    # ---- 下一步 ----
    lines.append(f"## {next_no + 1}. 下一步")
    lines.append("")
    steps = []
    blockers = [d for d in diags if d["type"] in ("BLOCKER", "NEAR_UNWINNABLE")]
    if blockers:
        steps.append(f"先验证可解性：{('、'.join(sorted({d['level_id'] for d in blockers})))}，用求解器/种子回归确认是否存在无解局面。")
    if any(d["type"] == "PRED_ACTUAL_DIVERGENCE" for d in diags):
        steps.append("复核预测模型：对背离关卡检查埋点口径、玩家分层与版本差异。")
    if recs:
        steps.append(f"选取 1–2 个改动做灰度实验（建议从 {recs[0]['level_id']} 开始），预设回滚条件。")
    if any(d["type"] == "UNSTABLE" for d in diags):
        steps.append("对不稳定关卡检查种子分布与初始局面生成，必要时限制极端坏局。")
    steps.append("补充样本：对样本不足的关卡延长观察窗口后再评估，不做小样本调参。")
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    lines.append("")
    return "\n".join(lines)


def _gate(diagnostics) -> dict:
    high = [d for d in diagnostics if d["severity"] == "HIGH"]
    return {
        "status": "FAIL" if high else "PASS",
        "high_count": len(high),
        "blocking_levels": sorted({d["level_id"] for d in high}),
        "rule": "存在 HIGH 级问题时评审不通过；接入 --strict 时进程以非 0 退出。",
    }


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(str(h) for h in headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def _kv(evidence: dict) -> str:
    return "；".join(f"{k}={v}" for k, v in evidence.items())


def _curve_row(curve, level_id, key):
    for row in curve:
        if row["level_id"] == level_id:
            return row if key is None else row.get(key, "")
    return None


def _write_csv(path, headers, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
