# -*- coding: utf-8 -*-
"""
智能封面裁切：显著性检测 + 顶部偏置，替代中心裁剪。
- 演出海报关键内容（剧名、人脸）通常在中上部 → 顶部偏置
- 显著性 = 边缘密度(梯度) + 饱和度加权，滑动正方形窗口选最佳位置
- 输出 180x180 到 covers_smart/，并生成对比大图 crop-preview/ 供人工抽查
用法: python smart_crop.py [excel] [out_json]
"""
import json, os, sys, hashlib
from PIL import Image, ImageFilter, ImageDraw

EXTRACTION = 180          # 输出尺寸
TOP_BIAS = 0.15           # 顶部偏置强度 0~1：越大越偏向上部
GRID = 24                 # 滑窗步进（在 ~480px 缩放图上）

def saliency_map(im):
    """返回 (score_map, w, h)：边缘密度 + 饱和度"""
    im = im.convert("RGB")
    W = 480
    ratio = W / im.width
    im2 = im.resize((W, max(1, round(im.height * ratio))), Image.LANCZOS)
    # 边缘（梯度近似：用 FIND_EDGES 滤波）
    edge = im2.convert("L").filter(ImageFilter.FIND_EDGES)
    # 饱和度
    hsv = im2.convert("HSV")
    sat = hsv.split()[1]
    # 灰度也计入（黑白海报的文字同样重要）
    gray = im2.convert("L")
    px_e, px_s, px_g = edge.load(), sat.load(), gray.load()
    w, h = im2.size
    smap = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            # 边缘 50% + 饱和 30% + 亮度对比 20%
            smap[y][x] = px_e[x, y] * 0.5 + px_s[x, y] * 0.3 + (255 - abs(px_g[x, y] - 128) * 2) * 0.2
    return smap, w, h, ratio

def smart_crop_box(im):
    """返回 (left, top, s)：原图坐标下的正方形裁切框"""
    w, h = im.size
    s = min(w, h)
    if abs(w - h) / max(w, h) < 0.06:   # 近方形，直接用整图
        return (w - s) // 2, (h - s) // 2, s
    smap, mw, mh, ratio = saliency_map(im)
    ms = min(mw, mh)
    best, best_score = None, -1
    y = 0
    while y + ms <= mh:
        x = 0
        while x + ms <= mw:
            # 窗口内均值采样（4x4 采样降耗）
            total = 0.0
            for sy in range(4):
                for sx in range(4):
                    px = min(mw - 1, x + ms * (sx * 2 + 1) // 8)
                    py = min(mh - 1, y + ms * (sy * 2 + 1) // 8)
                    total += smap[py][px]
            score = total / 16
            # 顶部偏置：窗口越靠上加分越多
            center_y = (y + ms / 2) / mh
            score *= (1 + TOP_BIAS * (1 - center_y) * 2)
            if score > best_score:
                best_score, best = score, (x, y)
            x += GRID
        y += GRID
    bx, by = best
    # 映射回原图坐标
    left = round(bx / ratio)
    top = round(by / ratio)
    left = max(0, min(w - s, left))
    top = max(0, min(h - s, top))
    return left, top, s

def main(excel_json="coupons1.json", out_map="cover-map.json", out_dir="covers_smart", prev_dir="crop-preview"):
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(prev_dir, exist_ok=True)
    srcs = sorted({c["封面"] for c in json.load(open(excel_json, encoding="utf-8")) if c.get("封面")})
    mapping = {}
    for p in srcs:
        im = Image.open(p).convert("RGB")
        left, top, s = smart_crop_box(im)
        key = hashlib.md5(p.encode()).hexdigest()[:10]
        dst = f"{out_dir}/{key}.png"
        im.crop((left, top, left + s, top + s)).resize((EXTRACTION, EXTRACTION), Image.LANCZOS).save(dst)
        mapping[p] = dst
        # 对比预览：左=原图+裁切框，右=结果
        pv = Image.new("RGB", (im.width + EXTRACTION + 30, im.height), (240, 240, 240))
        pv.paste(im, (0, 0))
        d = ImageDraw.Draw(pv)
        d.rectangle([left, top, left + s, top + s], outline=(255, 0, 0), width=6)
        pv.paste(Image.open(dst), (im.width + 30, 0))
        pv.save(f"{prev_dir}/{os.path.basename(p)}.preview.jpg", quality=80)
    json.dump(mapping, open(out_map, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✓ 智能裁切 {len(mapping)} 张 → {out_dir}/，预览 → {prev_dir}/")

if __name__ == "__main__":
    main(*sys.argv[1:])
