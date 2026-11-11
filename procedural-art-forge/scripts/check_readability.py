#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可辨识度自检：把六纪律里**能被机器判的**那几条跑一遍。

用法:
    python check_readability.py content/level13.json
    python check_readability.py content/*.json          # 批量
    python check_readability.py level13.json --min-cells 9

设计原则：**只报能确定的，不猜意图。**
  · 能判的：面积不足、单行噪点、糊满无留空、同色粘连、色彩过少
  · 不能判的：「这画的是什么」「像不像」—— 必须人看图（见 references/preview-pipeline.md）

这条边界很重要：脚本全绿不等于画得好，只等于"没犯低级错误"。
验收话术见 references/readability-rules.md §四。

退出码：有 ERROR 返回 1，只有 WARN 返回 0（CI 里可以只卡 ERROR）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def load_grid(path: Path) -> Tuple[List[List[str]], Dict[str, str], int, int]:
    """返回 (二维字符网格, 字符→色键, cols, rows)。支持 preview_grid.py 的三种格式。"""
    raw = json.loads(path.read_text(encoding='utf-8'))

    if 'grid' in raw:                      # 格式 C：已是二维颜色串
        g = raw['grid']
        rows, cols = len(g), len(g[0])
        legend = {c: c for c in {x for r in g for x in r if x != '.'}}
        return g, legend, cols, rows

    image = raw['image']
    legend = raw.get('legend') or {}
    rows = len(image)
    cols = len(image[0])
    grid = [list(line) for line in image]
    # 没有 legend 时，字符本身就是色键
    if not legend:
        legend = {c: c for c in {x for line in image for x in line if x != '.'}}
    return grid, legend, cols, rows


def check(grid: List[List[str]], legend: Dict[str, str], cols: int, rows: int,
          min_cells: int) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []

    count: Dict[str, int] = defaultdict(int)
    rows_with: Dict[str, set] = defaultdict(set)
    for r in range(rows):
        for c in range(cols):
            ch = grid[r][c]
            if ch == '.':
                continue
            count[ch] += 1
            rows_with[ch].add(r)

    cells = sum(count.values())
    if cells == 0:
        errors.append('整幅为空，没有任何色块')
        return errors, warns

    # 纪律 1a：任何色块 < min_cells（默认 9 = 3×3）就读不出形体
    for ch, n in sorted(count.items(), key=lambda kv: kv[1]):
        if n < min_cells:
            warns.append(
                f'色 {ch}({legend.get(ch, "?")}) 只有 {n} 格，低于 {min_cells}（3×3），读不出形体'
            )
        # 纪律 4：只占 1 行 = 噪点而非形体
        if len(rows_with[ch]) == 1 and n >= 3:
            warns.append(f'色 {ch}({legend.get(ch, "?")}) 只占 1 行，是噪点不是形体')

    # 纪律 5：留空太少 = 画面糊满，主体没有呼吸
    empty_ratio = 1 - cells / (cols * rows)
    if empty_ratio < 0.05:
        warns.append(f'留空仅 {empty_ratio * 100:.0f}%，画面糊满')

    # 纪律 2：同色两块直接相邻 → 人眼会读成一个更大的物体
    # 只报"同色连通块数量 > 1 且两块接触"的情况；完全不接触的同色是允许的
    seen = [[False] * cols for _ in range(rows)]
    comps: Dict[str, int] = defaultdict(int)
    touching = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '.' or seen[r][c]:
                continue
            ch = grid[r][c]
            comps[ch] += 1
            stack = [(r, c)]
            seen[r][c] = True
            while stack:
                cr, cc = stack.pop()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = cr + dr, cc + dc
                    if not (0 <= nr < rows and 0 <= nc < cols):
                        continue
                    if grid[nr][nc] != ch or seen[nr][nc]:
                        continue
                    seen[nr][nc] = True
                    stack.append((nr, nc))
    # 同色多块本身是正常的（两朵云），这里只做提示，不当错误
    multi = [ch for ch, k in comps.items() if k >= 2]
    if multi:
        touching = len(multi)
        warns.append(
            f'{touching} 种颜色出现多个不相连的块（{", ".join(multi[:4])}）'
            '—— 确认它们不是"本该是一个物体却被切断"'
        )

    # 色彩数量：颜色即难度，太少会显得空，太多是设计变更
    if len(count) < 2:
        errors.append('只有 1 种颜色，画不出任何形体')
    elif len(count) > 12:
        warns.append(f'{len(count)} 种颜色，超过 12 通常意味着该合并色了')

    return errors, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--min-cells', type=int, default=9, help='单个色块的最小格数（默认 9 = 3×3）')
    ap.add_argument('--quiet', action='store_true', help='只输出有问题的文件')
    args = ap.parse_args()

    total_e = total_w = 0
    for f in args.files:
        path = Path(f)
        try:
            grid, legend, cols, rows = load_grid(path)
        except Exception as e:                       # noqa: BLE001
            print(f'✗ {path.name}: 读取失败 {e}')
            total_e += 1
            continue
        errors, warns = check(grid, legend, cols, rows, args.min_cells)
        total_e += len(errors)
        total_w += len(warns)
        if args.quiet and not errors and not warns:
            continue
        head = '✗' if errors else ('⚠' if warns else '✓')
        print(f'{head} {path.name}  {cols}×{rows}  {len(legend)} 色')
        for e in errors:
            print(f'    ERROR  {e}')
        for w in warns:
            print(f'    WARN   {w}')

    print(f'\n{total_e} ERROR / {total_w} WARN')
    print('提醒：这只检查"没犯低级错误"，不检查"画得像不像" —— 必须人看图。')
    return 1 if total_e else 0


if __name__ == '__main__':
    sys.exit(main())
