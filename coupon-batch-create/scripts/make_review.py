# -*- coding: utf-8 -*-
"""把裁切预览图打包成一个自包含 HTML 预览页（图片 base64 内嵌，单文件可直接分享）
用法: python make_review.py [cover-map.json] [crop-preview目录] [输出html]
"""
import base64
import io
import json
import os
import sys
from PIL import Image

MAP = sys.argv[1] if len(sys.argv) > 1 else "cover-map-smart.json"
PREV = sys.argv[2] if len(sys.argv) > 2 else "crop-preview"
OUT = sys.argv[3] if len(sys.argv) > 3 else "crop-review.html"

pairs = json.load(open(MAP, encoding="utf-8"))
items = []
for src in sorted(pairs):
    pv = os.path.join(PREV, os.path.basename(src) + ".preview.jpg")
    if not os.path.isfile(pv):
        print("跳过（无预览图）:", src)
        continue
    im = Image.open(pv)
    im.thumbnail((360, 640), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    items.append((src, base64.b64encode(buf.getvalue()).decode()))

rows = "".join(
    f'<div class="card"><img src="data:image/jpeg;base64,{b64}">'
    f'<div class="cap"><b>{os.path.basename(src)}</b><br><span>{src}</span></div></div>'
    for src, b64 in items)

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>封面智能裁切预览（{len(items)}张）</title>
<style>
body{{font-family:system-ui,"Microsoft YaHei";background:#f5f5f5;margin:20px}}
h1{{font-size:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}}
.card{{background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.12)}}
.card img{{width:100%;display:block}}
.cap{{padding:8px 10px;font-size:12px;line-height:1.5}}
.cap span{{color:#888;font-size:11px;word-break:break-all}}
</style></head><body>
<h1>封面智能裁切预览 — {len(items)} 张（红框=裁切区域，右侧小图为 180×180 成品）</h1>
<div class="grid">{rows}</div></body></html>"""

open(OUT, "w", encoding="utf-8").write(html)
print(f"✓ 预览页 {OUT}（{len(items)} 张，{os.path.getsize(OUT)//1024} KB）")
