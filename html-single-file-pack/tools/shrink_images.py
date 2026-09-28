# -*- coding: utf-8 -*-
"""shrink_images.py — 分层压缩图片为 WebP，为单文件内联做体积预算

用法:
    # 最简：整个目录按「文件名分组，每组第 1 张当封面、其余当详情图」
    python shrink_images.py assets/img build/webp

    # 自定义档位（宽,质量）
    python shrink_images.py assets/img build/webp --tiers cover=1080,71 detail=800,66

    # 每组只保留 N 张（默认 1，即「封面 1 + 详情 1」）
    python shrink_images.py assets/img build/webp --keep 1

    # 分组方式：按文件名最后一个连字符前的部分分组（g318-1.jpg / g318-2.jpg → g318）
    python shrink_images.py assets/img build/webp --group-sep -

输出:
    <输出目录>/<分组>-1.w   封面
    <输出目录>/<分组>-2.g   详情图
    <输出目录>/sizes.json   {文件名: 字节数}
    并在 stdout 打印体积报告

依赖: Pillow
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow: pip install Pillow')


def parse_tiers(spec):
    """'cover=1080,71 detail=800,66' -> [('cover',1080,71), ('detail',800,66)]"""
    tiers = []
    for chunk in spec.split():
        name, rest = chunk.split('=')
        w, q = rest.split(',')
        tiers.append((name, int(w), int(q)))
    if not tiers:
        tiers = [('cover', 1080, 71), ('detail', 800, 66)]
    return tiers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='源图片目录')
    ap.add_argument('out', help='输出目录')
    ap.add_argument('--tiers', default='cover=1080,71 detail=800,66',
                    help='档位，格式 name=宽,质量（空格分隔）')
    ap.add_argument('--keep', type=int, default=1,
                    help='每个分组除封面外保留几张详情图（默认 1）')
    ap.add_argument('--group-sep', default='-',
                    help='分组分隔符，取最后一段之前的部分作为分组名（默认 -）')
    ap.add_argument('--ext', default='.jpg,.jpeg,.png,.webp',
                    help='扫描的扩展名')
    args = ap.parse_args()

    tiers = parse_tiers(args.tiers)
    exts = tuple(e.strip().lower() for e in args.ext.split(','))
    os.makedirs(args.out, exist_ok=True)

    files = sorted(f for f in os.listdir(args.src) if f.lower().endswith(exts))
    if not files:
        sys.exit('源目录没有找到图片: %s' % args.src)

    groups = {}
    for f in files:
        stem = f.rsplit('.', 1)[0]
        key = stem.rsplit(args.group_sep, 1)[0] if args.group_sep in stem else stem
        groups.setdefault(key, []).append(f)

    sizes = {}
    stat = {name: [0, 0] for name, _, _ in tiers}   # name -> [张数, 字节]

    for gid, fs in sorted(groups.items()):
        for i, f in enumerate(fs):
            is_cover = (i == 0)
            if not is_cover and i > args.keep:
                continue
            tier = tiers[0][1:] if is_cover else (tiers[1][1:] if len(tiers) > 1 else tiers[0][1:])
            tier_name = tiers[0][0] if is_cover else (tiers[1][0] if len(tiers) > 1 else tiers[0][0])
            W, Q = tier

            im = Image.open(os.path.join(args.src, f)).convert('RGB')
            if W and im.width > W:
                im = im.resize((W, int(round(im.height * W / im.width))), Image.LANCZOS)

            suffix = '.w' if is_cover else '.g'
            out_name = f.rsplit('.', 1)[0] + suffix
            out_path = os.path.join(args.out, out_name)
            im.save(out_path, 'WEBP', quality=Q, method=6)

            sz = os.path.getsize(out_path)
            sizes[out_name] = sz
            stat[tier_name][0] += 1
            stat[tier_name][1] += sz

    with open(os.path.join(args.out, 'sizes.json'), 'w', encoding='utf-8') as fp:
        json.dump(sizes, fp)

    total = 0
    for name, (n, b) in stat.items():
        total += b
        if n:
            print('%s: %d 张 %.2f MB (平均 %.0f KB)' % (name, n, b / 1048576, b / n / 1024))
    print('源图片: %d 张 -> 输出 %d 张' % (len(files), len(sizes)))
    print('合计 %.2f MB  ->  base64 内联后约 %.2f MB' % (total / 1048576, total * 1.37 / 1048576))
    print('')
    print('提示: base64 会膨胀约 37%%；若超标，优先用 --keep 0 砍数量而非降质量。')


if __name__ == '__main__':
    main()
