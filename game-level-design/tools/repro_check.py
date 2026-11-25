#!/usr/bin/env python3
"""确定性评估的可复现性校验 —— 连跑两次，逐字段比对，剔除计时字段。

为什么需要这个工具（而不是 `cmp` / `diff`）：
  - 直接比文件**必然**报不一致：唯一差异是 `ms` 计时。实测同一份关卡数据两次运行
    得到 12930 / 12935 字节，逻辑字段无一不同。把计时当逻辑，会逼团队去修一个
    不存在的不确定性。
  - 反过来，只比"结论字段"也不行：结论相同不代表过程可复现（分数、峰位、
    blocked_episodes 都可能漂移，而 verdict 还是同一个）。
  - 所以要比**全部字段，按名字剔掉计时**，并统计比了多少个字段 ——
    比了 0 个字段的 PASS 是假 PASS。

用法：
    python tools/repro_check.py --a run_a.json --b run_b.json
    python tools/repro_check.py --a run_a.json --b run_b.txt --marker LEVEL_DESIGNER_JSON=
    python tools/repro_check.py --a a.json --b b.json --ignore sha seed_used --json out.json

退出码：0 = 可复现；2 = 存在非计时字段差异（不可复现）；3 = 输入无法解析。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 计时类字段名（小写比较）。命中即剔，不参与比对。
DEFAULT_TIMING = {
    "ms", "us", "ns",
    "elapsed", "elapsed_ms", "duration", "duration_ms", "runtime", "runtime_ms",
    "time", "time_ms", "wall_ms", "cpu_ms", "elapsed_time", "took_ms",
    "ts", "took", "latency_ms", "dt", "delta_ms",
}

MAX_SHOW = 160


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _is_timing(name: str, timing: set) -> bool:
    n = _norm(name)
    if n in timing:
        return True
    # 兜底：xxx_ms / ms_xxx / elapsedXxx
    return n.endswith("ms") and len(n) <= 24 and any(k in n for k in ("ms",)) and n in timing


def load_payload(path: Path, marker: str | None) -> dict | list:
    """从可能夹带横幅/标记的输出里取出 JSON 主体。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    candidates = []
    if marker and marker in text:
        candidates.append(text.split(marker, 1)[1].strip())
    candidates.append(text.strip())
    for cand in candidates:
        if not cand:
            continue
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
    # 最后手段：从第一个 [ 或 { 开始 raw_decode（容忍尾部有多余行）
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "[{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise SystemExit(f"[repro] 无法从 {path} 解析出 JSON（检查 --marker）")


def flatten(obj, prefix: str = "", out=None, timing_out=None, timing: set = DEFAULT_TIMING):
    """展平成 {路径: 值}，同时记录被剔除的计时路径。"""
    if out is None:
        out = {}
    if timing_out is None:
        timing_out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            path = f"{prefix}.{key}" if prefix else key
            if _is_timing(key, timing):
                timing_out[path] = _short(v)
                continue
            flatten(v, path, out, timing_out, timing)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(v, f"{prefix}[{i}]", out, timing_out, timing)
    else:
        out[prefix] = obj
    return out, timing_out


def _short(v) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= MAX_SHOW else s[:MAX_SHOW] + "…"


def compare(a: dict, b: dict):
    keys_a, keys_b = set(a), set(b)
    only_a = sorted(keys_a - keys_b)
    only_b = sorted(keys_b - keys_a)
    diffs = []
    for k in sorted(keys_a & keys_b):
        va, vb = a[k], b[k]
        if va != vb:
            # 数值型容忍浮点表示差异：按 float 再比一次
            try:
                if float(va) == float(vb):
                    continue
            except (TypeError, ValueError):
                pass
            diffs.append((k, va, vb))
    return only_a, only_b, diffs


def main() -> int:
    ap = argparse.ArgumentParser(description="两次运行结果的可复现性校验")
    ap.add_argument("--a", required=True, help="第一次运行输出")
    ap.add_argument("--b", required=True, help="第二次运行输出")
    ap.add_argument("--marker", default=None,
                    help="输出里 JSON 主体的前缀标记，如 LEVEL_DESIGNER_JSON=")
    ap.add_argument("--ignore", nargs="*", default=[], help="额外忽略的字段名")
    ap.add_argument("--min-fields", type=int, default=10,
                    help="决策字段少于该数视为假 PASS（默认 10）")
    ap.add_argument("--json", default=None, help="把判定写成 JSON")
    ap.add_argument("--verbose", action="store_true", help="打印前 10 个一致字段做抽样")
    args = ap.parse_args()

    timing = set(DEFAULT_TIMING)
    timing |= {_norm(x) for x in args.ignore}

    pa, pb = Path(args.a), Path(args.b)
    for p in (pa, pb):
        if not p.exists():
            print(f"[repro] 找不到 {p}", file=sys.stderr)
            return 3

    obj_a = load_payload(pa, args.marker)
    obj_b = load_payload(pb, args.marker)
    fa, ta = flatten(obj_a, timing=timing)
    fb, tb = flatten(obj_b, timing=timing)

    only_a, only_b, diffs = compare(fa, fb)
    compared = len(set(fa) & set(fb))

    verdict = "PASS"
    reason = ""
    if compared < args.min_fields:
        verdict, reason = "FAIL", f"只比了 {compared} 个字段（< {args.min_fields}），假 PASS"
    elif only_a or only_b:
        verdict, reason = "FAIL", "字段集合不一致（结构变了，不是同一件事的两次运行）"
    elif diffs:
        verdict, reason = "FAIL", f"{len(diffs)} 个非计时字段不一致（不可复现）"

    print("== 可复现性校验 ==")
    print(f"  A: {pa}  ({pa.stat().st_size} B)")
    print(f"  B: {pb}  ({pb.stat().st_size} B)")
    print(f"  比对字段: {compared}（已剔除计时字段 {len(ta)} 个）")

    if only_a or only_b:
        print("\n  [仅 A 有] " + ", ".join(only_a[:20]))
        print("  [仅 B 有] " + ", ".join(only_b[:20]))

    if diffs:
        print("\n  [不一致字段]")
        print(f"  {'字段':<44} {'A':<20} B")
        for k, va, vb in diffs[:30]:
            print(f"  {k:<44} {_short(va):<20} {_short(vb)}")
        if len(diffs) > 30:
            print(f"  ... 另有 {len(diffs) - 30} 项")

    # 计时字段本身是否变化：说明"剔对了"而不是"恰好都一样"
    shared_timing = set(ta) & set(tb)
    timing_changed = sum(1 for k in shared_timing if ta[k] != tb[k])
    print(f"\n  计时字段变化: {timing_changed} / {len(shared_timing)} 项"
          f"（>0 是正常的，说明剔除的是真计时）")

    if args.verbose and not diffs:
        for k in sorted(set(fa) & set(fb))[:10]:
            print(f"    = {k} = {_short(fa[k])}")

    print(f"\n  REPRO: {verdict}" + (f" — {reason}" if reason else " — 决策字段逐一相等"))

    if args.json:
        Path(args.json).write_text(json.dumps({
            "repro": verdict.lower(),
            "reason": reason,
            "fields_compared": compared,
            "timing_fields_stripped": len(ta),
            "timing_fields_changed": timing_changed,
            "diffs": [{"path": k, "a": _short(va), "b": _short(vb)} for k, va, vb in diffs],
            "only_a": only_a,
            "only_b": only_b,
            "a": str(pa),
            "b": str(pb),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
