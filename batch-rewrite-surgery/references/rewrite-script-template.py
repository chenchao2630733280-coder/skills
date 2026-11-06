# -*- coding: utf-8 -*-
"""批量改写落盘脚本骨架（配合 batch-rewrite-surgery skill）

用法：
    python apply_<topic>.py            # dry-run（默认，不写盘）
    python apply_<topic>.py --apply    # 真正落盘

设计要点（五条硬约束，勿删）：
  1. DRY 门控只在 save() 上 —— sub1() 永远只改内存；
  2. 同一文件的所有替换必须在一次 load()/save() 内完成（二次 load 丢前趟改动）；
  3. dry 下不跑「落盘后应满足」的断言（用 `if not DRY:` 门控）；
  4. 全部终检读内存文本 mem[rel]，不读磁盘；
  5. 失配批量收集到 MISS，循环后统一报出并 SystemExit，不首处即崩。
"""
import argparse
import os
import sys

# ---------------- 配置区（按项目改这几处） ----------------

# 目标文件的扫描根（相对项目根）
ROOTS = ['output', 'src', 'docs']

# 活文件集边界：命中这些片段的路径一律不动
EXCLUDE_PARTS = ['/archive/', '/node_modules/', '/.git/']

# 只改这些后缀
EXTS = ('.html', '.htm', '.js', '.ts', '.css', '.json', '.md', '.py', '.vue')

# 根目录下的活动脚本白名单（交付物之外、但必须同步改的校验器/扫描器）
ROOT_WHITELIST = []          # 例：['_scan_ledger.py', '_verify_derived.js']

# 全局替换对：[(旧, 新, 说明)]
PAIRS = [
    # ('旧口径', '新口径', '全局替换'),
]

# 定向替换：{相对路径: [(旧, 新, 说明)]}  —— 用于「同词不同义」的少数处
FIX = {}

# 全局替换要在这些文件里被禁用（该处属「同词不同义」）
PAIR_SKIP = {}

# 缩减护栏（文件 → 允许的最小长度比），整块删除时才需要
MIN_RATIO = {}
DEFAULT_MIN_RATIO = 0.9

# 禁词表：改完后全仓不得再出现的旧口径
BAN = []

# 断言「这些新词必须仍在位」（防止部分回退时被连带清掉）
MUST_KEEP = []               # 例：[('output/site/pc/x.js', '新口径', 1)]

BAN_EXTRA = []               # 额外必查禁词的文件（白名单脚本等）

# ---------------- 引擎区（通常不用改） ----------------

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true', help='真正写盘（默认 dry-run）')
args = ap.parse_args()
DRY = not args.apply

BASE = os.path.dirname(os.path.abspath(__file__))
MISS = []      # 失配收集
HITS = []      # 命中统计
mem = {}       # 相对路径 → 内存文本


def _norm(rel):
    return rel.replace('\\', '/')


def in_scope(rel):
    rel = _norm(rel)
    if rel.startswith('.'):
        return False
    if any(p in '/' + rel.lstrip('/') for p in EXCLUDE_PARTS):
        return False
    if rel in ROOT_WHITELIST:
        return True
    if not rel.endswith(EXTS):
        return False
    head = rel.split('/')[0]
    return head in ROOTS


def load(rel):
    """读取并归一化行尾；返回 (文本, 原始行尾, 原字节长度)。"""
    raw = open(os.path.join(BASE, rel), 'rb').read()
    crlf = raw.count(b'\r\n')
    lf = raw.count(b'\n')
    eol = '\r\n' if (crlf > 0 and crlf >= lf * 0.9) else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    return text, eol, len(text)


def save(rel, text, eol, n0, ratio=None):
    """按 DRY 门控写盘；输出字节对比供人工核对。"""
    nb = len(text.encode('utf-8'))
    limit = ratio if ratio is not None else MIN_RATIO.get(rel, DEFAULT_MIN_RATIO)
    # 注意：CRLF 文件还原行尾后长度会「变大」（+行数），不是内容膨胀
    if not DRY and nb < n0 * limit * 0.8:
        raise SystemExit('[护栏] %s 缩减异常：%d → %d，先确认是否 EOL 误报' % (rel, n0, nb))
    if not DRY:
        with open(os.path.join(BASE, rel), 'wb') as f:
            f.write(text.replace('\n', eol).encode('utf-8'))
    print('   %s %s  %d → %d B  (%d 处)' % ('[写]' if not DRY else '[dry]',
                                            rel, n0, nb, sum(1 for h in HITS if h[0] == rel)))


def sub1(rel, text, old, new, note, expect=1):
    """精确替换一处；不匹配时收集到 MISS 而不是立即崩溃。"""
    c = text.count(old)
    if c == 0 and expect == 0:
        return text
    if c != expect:
        MISS.append('%s × %d（期望 %d）: %s  ← %s' % (rel, c, expect, note, repr(old[:60])))
        return text
    HITS.append((rel, note, c))
    return text.replace(old, new)


def walk():
    out = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__')]
        for fn in files:
            rel = _norm(os.path.relpath(os.path.join(root, fn), BASE))
            if in_scope(rel):
                out.append(rel)
    return sorted(set(out))


def main():
    files = walk()
    print('%s 扫描 %d 个在范围内的文件' % ('[APPLY]' if not DRY else '[DRY]', len(files)))

    for rel in files:
        text, eol, n0 = load(rel)
        before = text
        skips = PAIR_SKIP.get(rel, [])
        for old, new, note in PAIRS:
            if old in skips:
                continue
            text = sub1(rel, text, old, new, note, expect=text.count(old))
        for old, new, note in FIX.get(rel, []):
            text = sub1(rel, text, old, new, note, expect=1)
        if text != before:
            mem[rel] = (text, eol, n0)
            save(rel, text, eol, n0, MIN_RATIO.get(rel))

    if MISS:
        print('\n!!! 原文失配 %d 处，未落盘：' % len(MISS))
        for m in MISS:
            print('   ' + m)
        raise SystemExit('存在原文失配，未落盘')

    # ---------- 落盘后断言（dry 下跳过）----------
    if not DRY:
        bad = []
        for old, _n, _note in PAIRS:
            for rel in BAN_EXTRA + files:
                p = os.path.join(BASE, rel)
                if os.path.exists(p) and old in open(p, 'rb').read().decode('utf-8', 'replace'):
                    bad.append('%s 仍含旧口径 %s' % (rel, old))
        for old in BAN:
            for rel in files:
                p = os.path.join(BASE, rel)
                if os.path.exists(p) and old in open(p, 'rb').read().decode('utf-8', 'replace'):
                    bad.append('%s 命中禁词 %s' % (rel, old))
        for rel, word, n in MUST_KEEP:
            raw = open(os.path.join(BASE, rel), 'rb').read().decode('utf-8', 'replace')
            if raw.count(word) != n:
                bad.append('MUST_KEEP 失守：%s 中 %s 期望 %d 处，实得 %d' % (rel, word, n, raw.count(word)))
        if bad:
            for b in bad:
                print('   [收口失败] ' + b)
            raise SystemExit('收口检查未通过')

    print('\n命中文件 %d 个，替换 %d 处。%s'
          % (len(mem), sum(h[2] for h in HITS), '（dry-run，未写盘）' if DRY else '（已落盘）'))
    print('下一步：跑 verify_<topic>_diff.py 做反向 diff 逐字节校验。')


if __name__ == '__main__':
    main()
