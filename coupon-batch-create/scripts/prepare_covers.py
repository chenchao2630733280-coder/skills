# -*- coding: utf-8 -*-
"""把 cover 里的封面中心裁剪为 180x180，输出到 covers180/，并生成映射 cover-map.json"""
import json
import os
import hashlib
from PIL import Image

OUT = "covers180"
os.makedirs(OUT, exist_ok=True)
mapping = {}

srcs = set()
for c in json.load(open("coupons1.json", encoding="utf-8")):
    if c["封面"]:
        srcs.add(c["封面"])

for p in sorted(srcs):
    key = hashlib.md5(p.encode("utf-8")).hexdigest()[:10]
    dst = os.path.join(OUT, key + ".png")
    if not os.path.exists(dst):
        im = Image.open(p)
        im = im.convert("RGB")
        w, h = im.size
        s = min(w, h)
        left, top = (w - s) // 2, (h - s) // 2
        im = im.crop((left, top, left + s, top + s)).resize((180, 180), Image.LANCZOS)
        im.save(dst, "PNG")
    mapping[p] = dst.replace("\\", "/")

json.dump(mapping, open("cover-map.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"生成 {len(mapping)} 张 180x180 封面 -> {OUT}/")
