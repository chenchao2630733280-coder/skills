#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规范化 SKILL.md frontmatter 的 name 值：统一为 name: "<value>" 双引号风格。

用法：
    python3 _shared/fix-frontmatter-name.py            # 处理全部 skill（默认）
    python3 _shared/fix-frontmatter-name.py slides     # 只处理指定 skill 目录名

设计要点（踩过的坑）：
- **必须 CRLF 安全**。本仓库部分 SKILL.md 是 CRLF 换行。若按 "\\n" 切行再匹配
  r'^name:[ \\t]*(.+?)[ \\t]*$'，尾部的 \\r 会被 (.+?) 吃掉，导致：
    CRLF 未加引号  ->  name: "xxx<CR>"   （CR 被塞进引号里，静默丢换行）
    CRLF 已加引号  ->  name: ""xxx"<CR>" （直接畸形，且 lint 能抓到）
  正确做法：先按行尾符切出「行体 + 终止符」，只在行体上取值，回写时保留原终止符。
- 值里的引号一律剥掉再重新包一层，避免幂等性问题。
- 只在内容真正变化时才写盘。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_RE = re.compile(r'^name:[ \t]*(.*)$')
SCAN_LINES = 6  # frontmatter 的 name 一定在前几行内


def normalize(path):
    """返回 (old_line, new_line) 若发生改写，否则返回 None。"""
    with open(path, encoding='utf-8', newline='') as fh:
        lines = fh.read().splitlines(keepends=True)

    for i in range(min(SCAN_LINES, len(lines))):
        line = lines[i]
        body = line.rstrip('\r\n')
        term = line[len(body):] or '\n'
        m = NAME_RE.match(body)
        if not m:
            continue

        raw = m.group(1).strip()
        # 剥掉可能已存在的成对引号，以及任何残留的引号 / CR
        if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        value = raw.replace('"', '').replace('\r', '').strip()
        if not value:
            return None

        new_line = 'name: "%s"%s' % (value, term)
        if new_line == line:
            return None
        lines[i] = new_line
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(''.join(lines))
        return body, new_line.rstrip('\r\n')
    return None


def main():
    targets = sys.argv[1:]
    if not targets:
        targets = sorted(
            d for d in os.listdir(ROOT)
            if os.path.isfile(os.path.join(ROOT, d, 'SKILL.md'))
        )
    changed = skipped = missing = 0
    for name in targets:
        path = os.path.join(ROOT, name, 'SKILL.md')
        if not os.path.isfile(path):
            print('MISS  %s (无 SKILL.md)' % name)
            missing += 1
            continue
        # 换行风格只用于打印
        with open(path, 'rb') as fh:
            crlf = b'\r\n' in fh.read()
        res = normalize(path)
        if res:
            print('FIX   %-28s [%s] %s  ->  %s'
                  % (name, 'CRLF' if crlf else 'LF', res[0], res[1]))
            changed += 1
        else:
            skipped += 1

    print('\n共修复 %d 个文件；已合规 %d 个；缺失 %d 个' % (changed, skipped, missing))


if __name__ == '__main__':
    main()
