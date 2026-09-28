# -*- coding: utf-8 -*-
"""make_inline_map.py — 生成 {相对路径: dataURI} 映射表

供「JS 运行时动态拼图片路径」的场景使用：把映射表注入成
window.__INLINE_IMAGES__，然后让页面里的 img() 先查表、再回退相对路径。

用法:
    python make_inline_map.py build/webp -o build/image-map.json \
        --prefix "assets/img/"  --from-ext .jpg

    # 说明: build/webp/g318-1.w  ->  key "assets/img/g318-1.jpg"
    #       （.w / .g 后缀按 --suffix-map 还原成原扩展名）

选项:
    --prefix       key 的前缀，需与页面里 img() 拼接的前缀一致（默认 assets/img/）
    --from-ext     key 的扩展名（默认 .jpg）
    --suffix-map   输出名后缀 -> 原扩展名，默认 ".w=.jpg,.g=.jpg"
"""
import argparse
import base64
import json
import os
import sys

MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('srcdir', help="图片目录（原图目录或压缩后的目录，如 build/webp）")
    ap.add_argument('-o', '--out', required=True, help='输出 JSON')
    ap.add_argument('--prefix', default='assets/img/', help='key 前缀')
    ap.add_argument('--from-ext', default='.jpg', help='key 扩展名')
    ap.add_argument('--suffix-map', default='.w=.jpg,.g=.jpg',
                    help='输出名后缀 -> 原扩展名')
    ap.add_argument('--pretty', action='store_true', help='格式化输出（体积略大）')
    args = ap.parse_args()

    smap = {}
    for chunk in args.suffix_map.split(','):
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            smap[k.strip()] = v.strip()

    if not os.path.isdir(args.srcdir):
        sys.exit('目录不存在: %s' % args.srcdir)

    out = {}
    for f in sorted(os.listdir(args.srcdir)):
        p = os.path.join(args.srcdir, f)
        if not os.path.isfile(p):
            continue
        stem, ext = os.path.splitext(f)
        if stem == 'sizes':
            continue
        orig_ext = smap.get(ext, args.from_ext)
        key = args.prefix + stem + orig_ext
        mime = MIME.get(orig_ext, 'image/jpeg')
        with open(p, 'rb') as fp:
            out[key] = 'data:%s;base64,%s' % (mime, base64.b64encode(fp.read()).decode('ascii'))

    with open(args.out, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1 if args.pretty else None)

    size = os.path.getsize(args.out)
    print('输出   : %s' % args.out)
    print('条目   : %d' % len(out))
    print('大小   : %.2f MB' % (size / 1048576))
    print('样例   : %s' % (list(out.keys())[0] if out else '(空)'))
    print('')
    print('接下来: 在页面里让 img() 先查表 ——')
    print("  const M = window.__INLINE_IMAGES__ || {};")
    print("  const img = (f) => {")
    print("    if (!f) return '';")
    print("    if (/^(data:|https?:|blob:)/.test(f)) return f;")
    print("    const k = 'assets/img/' + f;")
    print("    return M[k] || k;")
    print("  };")


if __name__ == '__main__':
    main()
