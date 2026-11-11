#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""截图基线对比 —— 纯标准库实现的 PNG 差异判定。

用途: 验收阶段回答"截图是不是变了、变在哪",而不是靠人眼看。
纪律来自 references/build-report-template.md §3 的四条硬规矩,本工具只做其中
"跑对比"这一步;建基线与解释差异仍然是人/agent 的活。

用法:
    # 1) 建基线(同版本连跑两次应字节一致,否则基线本身不稳)
    python scripts/visual_diff.py baseline --dir docs/screenshots/baseline \
        --name 02-game_l01_1280x720_juice0 --image shot.png

    # 2) 跑对比
    python scripts/visual_diff.py check --dir docs/screenshots/baseline \
        --name 02-game_l01_1280x720_juice0 --image shot2.png \
        --max-diff 0.002 --out docs/screenshots/diff

    # 3) 看基线清单(哪些还没建)
    python scripts/visual_diff.py list --dir docs/screenshots/baseline

退出码: 0 通过 / 1 差异超阈 / 2 出错或基线缺失

不自动收录缺失基线是有意的: 若 check 时发现没基线就自动写入,首次运行永远绿,
这正是要防的静默假绿。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import zlib
from datetime import datetime, timezone

MANIFEST = "manifest.json"
MANIFEST_VERSION = 1

# ---------------------------------------------------------------- PNG 解码

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _unfilter(raw: bytes, width: int, height: int, bpp: int) -> bytearray:
    """撤销 PNG 行过滤。返回去过滤后的像素字节(stride*height)。"""
    stride = width * bpp
    out = bytearray(stride * height)
    pos = 0
    prev = bytearray(stride)
    for y in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 0:
            pass
        elif ftype == 1:  # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        else:
            raise ValueError("未知 PNG 过滤类型 %d" % ftype)
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def read_png(path: str) -> tuple:
    """读非交错 8bit PNG -> (width, height, rgb_bytes)。"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG: %s" % path)
    pos = 8
    idat = bytearray()
    palette = b""
    width = height = depth = ctype = interlace = -1
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctag = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctag == b"IHDR":
            width, height, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", payload)
        elif ctag == b"PLTE":
            palette = payload
        elif ctag == b"IDAT":
            idat += payload
        elif ctag == b"IEND":
            break
    if depth != 8:
        raise ValueError("仅支持 8bit PNG(当前 %dbit): %s" % (depth, path))
    if interlace:
        raise ValueError("不支持交错 PNG,请让截图工具输出非交错: %s" % path)
    if ctype not in _CHANNELS:
        raise ValueError("不支持的 PNG 颜色类型 %d: %s" % (ctype, path))

    bpp = _CHANNELS[ctype]
    px = _unfilter(zlib.decompress(bytes(idat)), width, height, bpp)
    stride = width * bpp
    rgb = bytearray(width * height * 3)
    for i in range(width * height):
        s = i * bpp
        d = i * 3
        if ctype == 2:
            rgb[d:d + 3] = px[s:s + 3]
        elif ctype == 6:
            rgb[d:d + 3] = px[s:s + 3]
        elif ctype == 0:
            v = px[s]
            rgb[d] = rgb[d + 1] = rgb[d + 2] = v
        elif ctype == 4:
            v = px[s]
            rgb[d] = rgb[d + 1] = rgb[d + 2] = v
        else:  # 3 palette
            idx = px[s] * 3
            if idx + 3 > len(palette):
                raise ValueError("调色板索引越界: %s" % path)
            rgb[d:d + 3] = palette[idx:idx + 3]
    return width, height, bytes(rgb)


def write_png(path: str, width: int, height: int, rgb: bytes) -> None:
    """写 8bit RGB PNG(filter=0),用于产出 diff 可视化。"""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(body)


# ---------------------------------------------------------------- 对比核心

def parse_mask(values) -> list:
    masks = []
    for v in values or []:
        parts = [p.strip() for p in str(v).split(",")]
        if len(parts) != 4:
            raise ValueError("--mask 需要 x,y,w,h: %s" % v)
        masks.append(tuple(int(float(p)) for p in parts))
    return masks


def _in_mask(x: int, y: int, masks: list) -> bool:
    for mx, my, mw, mh in masks:
        if mx <= x < mx + mw and my <= y < my + mh:
            return True
    return False


def compare(base: tuple, cur: tuple, tolerance: int, masks: list, grid: int) -> dict:
    bw, bh, bp = base
    cw, ch, cp = cur
    if (bw, bh) != (cw, ch):
        return {
            "status": "SIZE_MISMATCH",
            "base_size": [bw, bh],
            "cur_size": [cw, ch],
            "diff_ratio": 1.0,
            "note": "视口尺寸变了,对比无意义。先固定视口再重建基线。",
        }

    total = 0
    diff = 0
    minx, miny, maxx, maxy = bw, bh, -1, -1
    tiles = [[0] * grid for _ in range(grid)]
    tw = max(1, (bw + grid - 1) // grid)
    th = max(1, (bh + grid - 1) // grid)
    out = bytearray(bp)

    for y in range(bh):
        row = y * bw
        for x in range(bw):
            if masks and _in_mask(x, y, masks):
                continue
            total += 1
            i = (row + x) * 3
            d = max(abs(bp[i] - cp[i]), abs(bp[i + 1] - cp[i + 1]), abs(bp[i + 2] - cp[i + 2]))
            if d > tolerance:
                diff += 1
                out[i] = 255
                out[i + 1] = 40
                out[i + 2] = 40
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
                tiles[min(y // th, grid - 1)][min(x // tw, grid - 1)] += 1
            else:
                g = (bp[i] * 30 + bp[i + 1] * 59 + bp[i + 2] * 11) // 100
                g = 90 + g // 4
                out[i] = out[i + 1] = out[i + 2] = g

    ratio = (diff / total) if total else 0.0
    hot = []
    for gy in range(grid):
        for gx in range(grid):
            if tiles[gy][gx]:
                hot.append({
                    "tile": [gx, gy],
                    "box": [gx * tw, gy * th, min(tw, bw - gx * tw), min(th, bh - gy * th)],
                    "diff": tiles[gy][gx],
                })
    hot.sort(key=lambda t: -t["diff"])
    return {
        "status": "OK",
        "base_size": [bw, bh],
        "cur_size": [cw, ch],
        "pixels": total,
        "diff_pixels": diff,
        "diff_ratio": round(ratio, 6),
        "bbox": [minx, miny, maxx - minx + 1, maxy - miny + 1] if diff else None,
        "hot_tiles": hot[:8],
        "_diff_image": bytes(out),
    }


# ---------------------------------------------------------------- manifest

def load_manifest(folder: str) -> dict:
    path = os.path.join(folder, MANIFEST)
    if not os.path.exists(path):
        return {"version": MANIFEST_VERSION, "entries": {}}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("entries", {})
    data["version"] = MANIFEST_VERSION
    return data


def save_manifest(folder: str, data: dict) -> None:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 命令

def cmd_baseline(args) -> int:
    if not os.path.exists(args.image):
        print("[ERROR] 截图不存在: %s" % args.image, file=sys.stderr)
        return 2
    os.makedirs(args.dir, exist_ok=True)
    man = load_manifest(args.dir)
    entry = man["entries"].get(args.name)
    if entry and not args.force:
        old = os.path.join(args.dir, entry.get("file", ""))
        if os.path.exists(old) and sha256(old) == sha256(args.image):
            print("[SKIP] 基线未变化,仍为字节一致: %s" % args.name)
            return 0
        print("[ERROR] 基线已存在且内容不同。重建基线会让旧差异失去参照,", file=sys.stderr)
        print("        确认要走新基线请加 --force 并说明原因(写进 note):", file=sys.stderr)
        print("        %s" % args.name, file=sys.stderr)
        return 2

    w, h, _ = read_png(args.image)
    fname = args.name + ".png"
    dst = os.path.join(args.dir, fname)
    with open(args.image, "rb") as src, open(dst, "wb") as out:
        out.write(src.read())
    man["entries"][args.name] = {
        "file": fname,
        "width": w,
        "height": h,
        "sha256": sha256(dst),
        "note": args.note or "",
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_manifest(args.dir, man)
    print("[OK] 基线已记录 %s %dx%d -> %s" % (args.name, w, h, dst))
    print("     再跑一次同条件截图并 check,确认 diff_ratio=0(基线自检)")
    return 0


def cmd_check(args) -> int:
    man = load_manifest(args.dir)
    entry = man["entries"].get(args.name)
    if not entry:
        print("[ERROR] 没有基线 %s。先 baseline 再 check ——" % args.name, file=sys.stderr)
        print("        不自动收录是为了避免'首次运行永远绿'。", file=sys.stderr)
        return 2
    base_path = os.path.join(args.dir, entry["file"])
    if not os.path.exists(base_path):
        print("[ERROR] 基线文件丢失: %s" % base_path, file=sys.stderr)
        return 2
    if not os.path.exists(args.image):
        print("[ERROR] 当前截图不存在: %s" % args.image, file=sys.stderr)
        return 2

    base = read_png(base_path)
    cur = read_png(args.image)
    masks = parse_mask(args.mask)
    res = compare(base, cur, args.tolerance, masks, args.grid)
    diff_img = res.pop("_diff_image", None)

    written = None
    if diff_img is not None and args.out:
        os.makedirs(args.out, exist_ok=True)
        written = os.path.join(args.out, args.name + "_diff.png")
        write_png(written, res["base_size"][0], res["base_size"][1], diff_img)
    res["baseline"] = args.name
    res["current"] = args.image
    res["tolerance"] = args.tolerance
    res["max_diff"] = args.max_diff
    res["mask_count"] = len(masks)
    res["diff_image"] = written

    if res["status"] == "SIZE_MISMATCH":
        res["verdict"] = "FAIL"
    else:
        res["verdict"] = "PASS" if res["diff_ratio"] <= args.max_diff else "FAIL"

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(json.dumps({k: v for k, v in res.items() if k != "hot_tiles"},
                     ensure_ascii=False, indent=2))
    if res.get("hot_tiles"):
        print("差异热点(按像素数降序, 前 8):")
        for t in res["hot_tiles"]:
            print("  tile%s box=%s diff=%d px" % (t["tile"], t["box"], t["diff"]))
    if res["verdict"] == "FAIL":
        print("[FAIL] 差异 %.4f%% 超过阈值 %.4f%%" % (res["diff_ratio"] * 100, args.max_diff * 100),
              file=sys.stderr)
        print("       差异必须逐条给出'为什么变',没有理由的一律当回归。", file=sys.stderr)
        return 1
    print("[PASS] 差异 %.4f%% <= 阈值 %.4f%%" % (res["diff_ratio"] * 100, args.max_diff * 100))
    return 0


def cmd_list(args) -> int:
    man = load_manifest(args.dir)
    entries = man.get("entries", {})
    if not entries:
        print("[WARN] 基线目录为空: %s" % args.dir)
        return 0
    print("%-46s %-12s %-10s %s" % ("name", "size", "recorded", "note"))
    for name in sorted(entries):
        e = entries[name]
        exists = "" if os.path.exists(os.path.join(args.dir, e.get("file", ""))) else " [文件缺失]"
        print("%-46s %-12s %-10s %s%s" % (
            name,
            "%dx%d" % (e.get("width", 0), e.get("height", 0)),
            (e.get("recorded_at") or "")[:10],
            e.get("note", ""),
            exists,
        ))
    print("\n共 %d 条基线" % len(entries))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="截图基线对比(纯标准库 PNG)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("baseline", help="记录一张基线截图")
    b.add_argument("--dir", required=True)
    b.add_argument("--name", required=True, help="建议 {图名}_{关卡id}_{视口}_{JUICE系数}")
    b.add_argument("--image", required=True)
    b.add_argument("--note", default="")
    b.add_argument("--force", action="store_true", help="覆盖已有基线(必须说明原因)")
    b.set_defaults(func=cmd_baseline)

    c = sub.add_parser("check", help="对比当前截图与基线")
    c.add_argument("--dir", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--image", required=True)
    c.add_argument("--max-diff", type=float, default=0.002, help="允许的差异像素占比, 默认 0.2%%")
    c.add_argument("--tolerance", type=int, default=8, help="单通道容差 0-255, 默认 8")
    c.add_argument("--mask", action="append", help="忽略区域 x,y,w,h,可重复")
    c.add_argument("--grid", type=int, default=8, help="热点网格数, 默认 8")
    c.add_argument("--out", help="diff 可视化输出目录")
    c.add_argument("--json", help="结果写入 JSON")
    c.set_defaults(func=cmd_check)

    l = sub.add_parser("list", help="列出基线")
    l.add_argument("--dir", required=True)
    l.set_defaults(func=cmd_list)

    args = ap.parse_args(argv)
    # 参数越界一律拒绝，不允许"调大一点就变绿"。这三个值写错的后果都是**静默 PASS**，
    # 而本工具存在的意义就是不许静默 PASS，所以自己先守住。
    if args.cmd == "check":
        if not 0 <= args.tolerance <= 255:
            print("[ERROR] --tolerance 必须在 0~255（当前 %d）。调大等于宣布所有像素都算相同，"
                  "结果必然 PASS。" % args.tolerance, file=sys.stderr)
            return 2
        if not 0.0 <= args.max_diff <= 1.0:
            print("[ERROR] --max-diff 是差异像素**占比**，必须在 0~1（0.002 = 0.2%%）。"
                  "当前 %g 会让任何差异都通过。" % args.max_diff, file=sys.stderr)
            return 2
        if args.grid < 1:
            print("[ERROR] --grid 必须 >= 1（当前 %d）。" % args.grid, file=sys.stderr)
            return 2
    try:
        return args.func(args)
    except (ValueError, OSError) as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
