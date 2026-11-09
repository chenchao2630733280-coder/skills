#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零依赖 PNG 预览器：把"网格 + 配色表"渲染成 PNG，用于程序化美术的快速校对。

用法:
    python preview_grid.py content/level13.json
    python preview_grid.py content/level13.json content/level14.json   # 横向拼图对比
    python preview_grid.py content/level13.json --cell 32 --no-grid --ascii

支持的输入格式（任选其一）：
  A) {"cols":36,"rows":20,"image":["AABB...", ...],
      "legend":{"A":"sky","B":"sand"},
      "palette":{"sky":{"bead":"#5AA9FF"}, ...}}
  B) 同上，但 palette 直接是 {"sky":"#5AA9FF"}
  C) {"grid":[["#5AA9FF","#E8C88F", ...], ...]}   # 已经是二维颜色字符串

为什么不用 Pillow：环境里经常装不上（pip 限流），而 zlib + struct 足够写 PNG。
渲染 36×20 @ cell=32 约 0.2 秒，比启动游戏看效果快一个数量级。

**这只用于美术校对，不是交付物。** 最终必须看实机截图（见 ../references/preview-pipeline.md）。
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

RGB = Tuple[int, int, int]


# ── 最小 PNG 编码器 ──────────────────────────────────────────────────────
def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack('>I', len(data)) + tag + data
            + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path: Path, w: int, h: int, rows: Sequence[bytearray]) -> None:
    """rows: h 行，每行 w*3 字节。filter 固定 0（None）。"""
    raw = bytearray()
    for row in rows:
        raw.append(0)          # 每行必须有 filter 字节，漏了就是花屏
        raw.extend(row)
    png = (b'\x89PNG\r\n\x1a\n'
           + _chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + _chunk(b'IDAT', zlib.compress(bytes(raw), 6))
           + _chunk(b'IEND', b''))
    path.write_bytes(png)


def hex2rgb(s: str) -> RGB:
    s = s.lstrip('#')
    if len(s) == 3:
        s = ''.join(ch * 2 for ch in s)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def darken(rgb: RGB, f: float = 0.72) -> RGB:
    return tuple(int(v * f) for v in rgb)  # type: ignore[return-value]


# ── 读内容 ──────────────────────────────────────────────────────────────
def load_grid(data: dict) -> List[List[Optional[str]]]:
    """返回 rows × cols 的 #RRGGBB 矩阵，None 表示空格（渲染成背景色）。"""
    if 'grid' in data:                                   # 格式 C
        return [[c for c in row] for row in data['grid']]

    cols = int(data['cols'])
    rows = int(data['rows'])
    image: List[str] = data['image']
    legend: Dict[str, str] = data.get('legend', {})
    palette: Dict[str, object] = data.get('palette', {})

    def color_of(ch: str) -> Optional[str]:
        key = legend.get(ch, ch)
        spec = palette.get(key)
        if spec is None:
            return None if ch in '. ' else '#808080'
        if isinstance(spec, str):
            return spec
        return spec.get('bead') or spec.get('color')         # dict: 取填充色

    out: List[List[Optional[str]]] = []
    for r in range(rows):
        line = image[r] if r < len(image) else ''
        out.append([color_of(line[c]) if c < len(line) else None for c in range(cols)])
    return out


def print_ascii(data: dict, grid: List[List[Optional[str]]]) -> None:
    """字符图：拓扑校对用（列内空洞 / 形状闭合 / 越界裁剪）。"""
    if 'image' in data:
        for i, line in enumerate(data['image']):
            print(f'{i:>3} {line}')
    else:
        sym = {}
        for row in grid:
            for c in row:
                if c is not None and c not in sym:
                    sym[c] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(sym) % 26]
        for i, row in enumerate(grid):
            print(f'{i:>3} ' + ''.join(sym.get(c, '.') if c else '.' for c in row))


# ── 渲染 ────────────────────────────────────────────────────────────────
def render(grid: List[List[Optional[str]]], cell: int, grid_lines: bool,
           bg: str = '#FFFFFF') -> Tuple[int, int, List[bytearray]]:
    rows = len(grid)
    cols = max(len(r) for r in grid) if rows else 0
    W, H = cols * cell, rows * cell
    bg_rgb = hex2rgb(bg)

    # 先把每个单元画成纯色块，再决定要不要压格子线
    rows_px: List[bytearray] = []
    for r in range(H):
        row = bytearray()
        gy = r // cell
        for c in range(W):
            gx = c // cell
            hexv = grid[gy][gx] if gx < len(grid[gy]) else None
            rgb = hex2rgb(hexv) if hexv else bg_rgb
            if grid_lines and (r % cell == 0 or c % cell == 0):
                rgb = darken(rgb, 0.72)      # 单元上/左边界压暗一档
            row.extend(rgb)
        rows_px.append(row)
    return W, H, rows_px


def hstack(imgs: List[Tuple[int, int, List[bytearray]]], gap: int = 12) -> Tuple[int, int, List[bytearray]]:
    H = max(i[1] for i in imgs)
    W = sum(i[0] for i in imgs) + gap * (len(imgs) - 1)
    out: List[bytearray] = []
    for y in range(H):
        row = bytearray()
        for k, (w, h, px) in enumerate(imgs):
            row.extend(px[y] if y < h else bytearray([255] * w * 3))
            if k < len(imgs) - 1:
                row.extend(b'\x20\x20\x20' * gap)   # 深灰间隔条
        out.append(row)
    return W, H, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+', help='内容 JSON')
    ap.add_argument('--cell', type=int, default=28, help='单格像素（默认 28）')
    ap.add_argument('--no-grid', action='store_true', help='不画格子线')
    ap.add_argument('--ascii', action='store_true', help='只打印字符图，不出 PNG')
    ap.add_argument('--out', help='输出路径（默认 _preview_<首个文件名>.png）')
    ap.add_argument('--bg', default='#FFFFFF', help='空白单元的背景色')
    args = ap.parse_args()

    imgs = []
    for f in args.files:
        data = json.loads(Path(f).read_text(encoding='utf-8'))
        grid = load_grid(data)
        if args.ascii:
            print(f'=== {Path(f).name}')
            print_ascii(data, grid)
            continue
        imgs.append(render(grid, args.cell, not args.no_grid, args.bg))

    if args.ascii:
        return 0

    if len(imgs) == 1:
        W, H, px = imgs[0]
    else:
        W, H, px = hstack(imgs)

    out = Path(args.out) if args.out else Path(f'_preview_{Path(args.files[0]).stem}.png')
    write_png(out, W, H, px)
    print(f'saved {out.name}  {W}x{H}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
