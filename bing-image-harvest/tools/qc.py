# -*- coding: utf-8 -*-
"""qc.py — 图片质检 + 压缩 + 生成人工抽查拼版图

用法:
  python qc.py [图片目录] [--maxw 1500] [--q 82]

判据:
  尺寸过小 / 宽高比异常 / 灰度标准差过低(纯色) / 边缘密度过低(糊) -> 删除
  宽度超限 -> 等比缩放并重存 JPEG(progressive)
  同时输出 <目录>/../tools/sheets/sheet_NN.jpg 供人眼抽查
"""
import os
import sys
import json
from PIL import Image, ImageStat, ImageFilter

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = {}
for a in sys.argv[1:]:
    if a.startswith('--'):
        k, _, v = a[2:].partition('=')
        opts[k] = v

IMG = os.path.abspath(args[0] if args else '.')
SHEET = os.path.join(os.path.dirname(IMG), 'tools', 'sheets')
MAX_W = int(opts.get('maxw', 1500))
QUALITY = int(opts.get('q', 82))
COLS, ROWS, TW, TH = 5, 5, 300, 200

os.makedirs(SHEET, exist_ok=True)
files = sorted(f for f in os.listdir(IMG) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
report = {'ok': [], 'drop': [], 'resized': 0, 'saved_kb': 0}

for f in files:
    p = os.path.join(IMG, f)
    before = os.path.getsize(p) // 1024
    try:
        im = Image.open(p).convert('RGB')
        w, h = im.size
    except Exception as e:
        report['drop'].append((f, 'unreadable: %s' % e))
        continue

    ratio = h / max(w, 1)
    if w < 480 or h < 320 or ratio > 2.4 or ratio < 0.35:
        report['drop'].append((f, 'bad size %dx%d' % (w, h)))
        continue

    small = im.convert('L').resize((64, 64))
    std = ImageStat.Stat(small).stddev[0]
    edge = ImageStat.Stat(small.filter(ImageFilter.FIND_EDGES)).mean[0]
    if std < 18:
        report['drop'].append((f, 'flat std=%.1f' % std))
        continue
    if edge < 3.0:
        report['drop'].append((f, 'blurry edge=%.1f' % edge))
        continue

    if w > MAX_W:
        im = im.resize((MAX_W, int(round(h * MAX_W / w))), Image.LANCZOS)
        report['resized'] += 1
    im.save(p, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
    after = os.path.getsize(p) // 1024
    report['saved_kb'] += max(0, before - after)
    report['ok'].append({'file': f, 'w': im.size[0], 'h': im.size[1], 'kb': after, 'std': round(std, 1)})

for f, _ in report['drop']:
    try:
        os.remove(os.path.join(IMG, f))
    except OSError:
        pass

with open(os.path.join(SHEET, 'qc-report.json'), 'w', encoding='utf-8') as fp:
    json.dump(report, fp, ensure_ascii=False, indent=2)

print('保留 %d / 淘汰 %d / 缩放 %d / 省下 %.1f MB' % (
    len(report['ok']), len(report['drop']), report['resized'], report['saved_kb'] / 1024))
for f, why in report['drop']:
    print('  DROP', f, why)

ok_files = [r['file'] for r in report['ok']]
per = COLS * ROWS
for si in range(0, len(ok_files), per):
    batch = ok_files[si:si + per]
    sheet = Image.new('RGB', (COLS * TW, ROWS * TH), (12, 16, 26))
    for i, f in enumerate(batch):
        try:
            im = Image.open(os.path.join(IMG, f)).convert('RGB')
            im.thumbnail((TW, TH), Image.LANCZOS)
            sheet.paste(im, ((i % COLS) * TW + (TW - im.size[0]) // 2, (i // COLS) * TH + (TH - im.size[1]) // 2))
        except Exception:
            pass
    sheet.save(os.path.join(SHEET, 'sheet_%02d.jpg' % (si // per + 1)), 'JPEG', quality=78)

# 打印 行 -> 文件名 映射，供对照抽查
for i in range(0, len(ok_files), COLS):
    print('sheet%02d r%d: ' % (i // per + 1, (i % per) // COLS + 1) + ' | '.join(ok_files[i:i + COLS]))
print('拼版图输出目录:', SHEET)
