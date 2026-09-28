# -*- coding: utf-8 -*-
"""mksheet.py — 为指定条目生成拼版对照图（定点复采后复查用）

用法:
  python mksheet.py "id1,id2,id3" [输出名] [图片目录]
"""
import os
import sys
from PIL import Image

ids = sys.argv[1].split(',')
name = sys.argv[2] if len(sys.argv) > 2 else 'check'
IMG = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else './assets/img')
OUT = os.path.join(os.path.dirname(IMG), 'tools', 'sheets')

os.makedirs(OUT, exist_ok=True)
files = [f for i in ids for f in sorted(os.listdir(IMG)) if f.startswith(i + '-') and f.lower().endswith(('.jpg', '.jpeg', '.png'))]
if not files:
    print('没有匹配的图片'); sys.exit(1)

COLS, TW, TH = 5, 320, 210
ROWS = (len(files) + COLS - 1) // COLS
sheet = Image.new('RGB', (COLS * TW, ROWS * TH), (12, 16, 26))
for i, f in enumerate(files):
    im = Image.open(os.path.join(IMG, f)).convert('RGB')
    im.thumbnail((TW, TH), Image.LANCZOS)
    sheet.paste(im, ((i % COLS) * TW + (TW - im.size[0]) // 2, (i // COLS) * TH + (TH - im.size[1]) // 2))
path = os.path.join(OUT, name + '.jpg')
sheet.save(path, 'JPEG', quality=82)

for i in range(0, len(files), COLS):
    print('r%d: ' % (i // COLS + 1) + ' | '.join(files[i:i + COLS]))
print('已生成:', path)
