# -*- coding: utf-8 -*-
"""selfcheck.py — 单文件 HTML 自包含性核查

用法:
    python selfcheck.py path/to/single.html

检查项:
    1. 非内联外部引用（<img src> / <link href> / <script src> 指向本地文件）
    2. 外链样式表 <link rel="stylesheet">
    3. 静态标签里残留的相对路径（assets/ 等）
    4. 内联 data:image/ 数量

退出码: 0 = 完全自包含, 1 = 存在外部依赖
"""
import os
import re
import sys

# JS 模板字面量与字符串拼接产生的假引用，需排除
FALSE_POSITIVE = re.compile(r'^[$]?\{|\$\{')

SKIP_PREFIX = ('data:', '#', 'javascript:', 'mailto:', 'tel:',
               'http://www.w3.org', 'https://www.w3.org')


def check(path):
    s = open(path, encoding='utf-8').read()
    size = os.path.getsize(path)

    # 只看静态属性写法：值里不含 ${ 插值
    refs = set(re.findall(r'(?:src|href)=["\']([^"\'$\{]+)["\']', s))
    external = sorted(
        u for u in refs
        if not u.startswith(SKIP_PREFIX) and not FALSE_POSITIVE.search(u)
    )

    n_asset = len(re.findall(r'(?:src|href)=["\'](?:\./)?assets/', s))
    n_data = s.count('data:image/')
    n_link = len(re.findall(r'<link[^>]*rel=["\']?stylesheet', s, re.I))
    n_script = len(re.findall(r'<script', s))
    n_style = len(re.findall(r'<style', s))
    n_trips = len(re.findall(r'\bid:\s*["\']', s))

    ok = (not external) and n_asset == 0 and n_link == 0

    print('文件            : %s' % os.path.basename(path))
    print('大小            : %.2f MB (%d bytes)' % (size / 1048576, size))
    print('内联图片        : %d 张 (data:image/)' % n_data)
    print('assets 残留     : %d' % n_asset)
    print('外链样式表      : %d' % n_link)
    print('外部引用        : %s' % (external if external else '无'))
    print('script/style    : %d / %d' % (n_script, n_style))
    if n_trips:
        print('条目数 (id:)    : %d' % n_trips)
    print('')
    print('结论            : %s' % ('OK 完全自包含，可直接上传云端' if ok
                                   else 'FAIL 存在外部依赖，云端会丢资源'))
    return 0 if ok else 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(check(sys.argv[1]))
