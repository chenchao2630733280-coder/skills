# -*- coding: utf-8 -*-
"""pack_html.py — 把多文件静态站点打包成自包含单文件 HTML

用法:
    python pack_html.py index.html -o 单文件版.html \
        --css css/style.css \
        --js data/part1.js data/part2.js data/images.js js/app.js \
        --images-dir assets/img \
        --inline-map build/image-map.json

说明:
    --css/--js        按给定顺序内联（JS 顺序必须与应用原本的 <script> 顺序一致）
    --images-dir      允许把 HTML/CSS 里引用到该目录下的图片转成 data URI
    --inline-map      注入 window.__INLINE_IMAGES__ = {原始相对路径: dataURI}，
                      供 JS 运行时动态拼路径的场景查表（配合 img() 改造）。
                      用 tools/make_inline_map.py 生成。
    --head-script     在 </head> 前额外注入的 JS 文件（如 __INLINE_IMAGES__ 的注入）

关键: 所有注入一律使用「函数式替换」，避免 String.replace 把替换串里的
      $$ / $& / $` / $' 当转义模式还原，静默破坏源码（会导致页面白屏）。
"""
import argparse
import base64
import mimetypes
import os
import re
import sys

MIME = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml',
    '.avif': 'image/avif', '.ico': 'image/x-icon',
}

_report = {'css': 0, 'js': 0, 'img': 0, 'cssurl': 0, 'miss': []}


def to_data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = MIME.get(ext) or mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as fp:
        b = fp.read()
    return 'data:%s;base64,%s' % (mime, base64.b64encode(b).decode('ascii'))


def resolve(base_dir, url):
    """把 HTML 里的相对 URL 解析成本地路径；非本地/不存在则返回 None"""
    if url.startswith(('data:', 'http:', 'https:', '//', '#', 'javascript:', 'mailto:')):
        return None
    clean = url.split('?')[0].split('#')[0]
    p = os.path.normpath(os.path.join(base_dir, clean))
    return p if os.path.isfile(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entry', help='入口 HTML')
    ap.add_argument('-o', '--out', required=True, help='输出单文件 HTML')
    ap.add_argument('--css', nargs='*', default=[], help='要内联的 CSS 文件（按顺序）')
    ap.add_argument('--js', nargs='*', default=[], help='要内联的 JS 文件（按顺序，须与原脚本顺序一致）')
    ap.add_argument('--images-dir', default=None,
                    help='允许内联的图片目录（HTML/CSS 中引用到该目录下的图片会转 data URI）')
    ap.add_argument('--inline-map', default=None,
                    help='{相对路径: dataURI} JSON，注入为 window.__INLINE_IMAGES__')
    ap.add_argument('--inline-map-var', default='__INLINE_IMAGES__',
                    help='注入的全局变量名（默认 __INLINE_IMAGES__）')
    ap.add_argument('--title-marker', default=None,
                    help='可选：替换 <title> 内容为该字符串')
    args = ap.parse_args()

    base_dir = os.path.dirname(os.path.abspath(args.entry))
    html = open(args.entry, encoding='utf-8').read()

    img_dir_abs = os.path.abspath(os.path.join(base_dir, args.images_dir)) if args.images_dir else None

    def allowed(p):
        if img_dir_abs is None:
            return False
        p = os.path.abspath(p)
        return p.startswith(img_dir_abs + os.sep) or p == img_dir_abs

    # ---------- 1. 内联本地 <img src> ----------
    def repl_img(m):
        quote, url = m.group(1), m.group(2)
        p = resolve(base_dir, url)
        if p and allowed(p):
            _report['img'] += 1
            return 'src=%s%s%s' % (quote, to_data_uri(p), quote)
        if url.startswith(('data:', 'http', '//', '#')):
            return m.group(0)
        _report['miss'].append(url)
        return m.group(0)

    html = re.sub(r'src=(["\'])([^"\']+)\1', repl_img, html)

    # ---------- 2. 内联 CSS 里的 url(...) ----------
    def repl_css_url(m):
        quote = m.group(1) or ''
        url = m.group(2)
        p = resolve(base_dir, url)
        if p and allowed(p):
            _report['cssurl'] += 1
            return 'url(%s%s%s)' % (quote, to_data_uri(p), quote)
        return m.group(0)

    css_blocks = []
    for f in args.css:
        fp = os.path.join(base_dir, f)
        if not os.path.isfile(fp):
            sys.exit('CSS 不存在: %s' % fp)
        css = open(fp, encoding='utf-8').read()
        css = re.sub(r'url\(\s*(["\']?)([^"\')]+)\1\s*\)', repl_css_url, css)
        css_blocks.append('/* ==== %s ==== */\n%s' % (f, css))
        _report['css'] += 1

    css_all = '\n'.join(css_blocks)

    # ---------- 3. 组装 JS ----------
    js_blocks = []
    if args.inline_map:
        mp = open(args.inline_map, encoding='utf-8').read()
        js_blocks.append('window.%s = %s;' % (args.inline_map_var, mp))
    for f in args.js:
        fp = os.path.join(base_dir, f)
        if not os.path.isfile(fp):
            sys.exit('JS 不存在: %s' % fp)
        js_blocks.append('/* ==== %s ==== */\n%s' % (f, open(fp, encoding='utf-8').read()))
        _report['js'] += 1
    js_all = '\n;\n'.join(js_blocks)

    # ---------- 4. 摘掉原本的外链标签（避免重复加载不存在的文件） ----------
    for f in args.css:
        name = os.path.basename(f)
        html = re.sub(r'<link[^>]*href=["\'][^"\']*%s["\'][^>]*>' % re.escape(name), '', html, flags=re.I)
    for f in args.js:
        name = os.path.basename(f)
        html = re.sub(r'<script[^>]*src=["\'][^"\']*%s["\'][^>]*>\s*</script>' % re.escape(name), '', html, flags=re.I)

    # ---------- 5. 拼装：必须函数式替换 ----------
    if css_all:
        html = html.replace('</head>', lambda: '<style>\n' + css_all + '\n</style>\n</head>')
    if js_all:
        html = html.replace('</body>', lambda: '<script>\n' + js_all + '\n</script>\n</body>')

    if args.title_marker:
        html = re.sub(r'<title>.*?</title>', lambda m: '<title>%s</title>' % args.title_marker,
                      html, count=1, flags=re.S | re.I)

    with open(args.out, 'w', encoding='utf-8') as fp:
        fp.write(html)

    size = os.path.getsize(args.out)
    print('输出            : %s' % args.out)
    print('大小            : %.2f MB (%d bytes)' % (size / 1048576, size))
    print('内联 CSS/JS     : %d / %d' % (_report['css'], _report['js']))
    print('内联图片        : %d (标签) + %d (CSS url)' % (_report['img'], _report['cssurl']))
    print('内联图片映射表  : %s' % (args.inline_map or '未使用'))
    if _report['miss']:
        print('')
        print('!! 未能内联的引用 %d 条（需人工确认是否外部资源）:' % len(_report['miss']))
        for u in sorted(set(_report['miss']))[:20]:
            print('   - %s' % u)
    print('')
    print('下一步: python selfcheck.py %s' % args.out)


if __name__ == '__main__':
    main()
