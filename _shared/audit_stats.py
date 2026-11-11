"""统计各 skill 的 SKILL.md 行数与 description 长度。

用法:
    python _shared/audit_stats.py            # 只打印超限/接近上限
    python _shared/audit_stats.py --all      # 全部打印
    python _shared/audit_stats.py --dump     # 把违规者的 description 原文导出到
                                            # _shared/_desc_dump.txt 供改写用

description 的三种写法都要认（否则会漏统计，误报"全部合规"）:
    1. 单行引号     description: "……"
    2. 折叠/字面     description: >    /    description: |
    3. 无引号续行    description: ……（下一行缩进继续）
"""

import os
import re
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE_LIMIT = 500
DESC_LIMIT = 200


def frontmatter(text):
    """取出 --- 与 --- 之间的 frontmatter 文本；没有则返回空串。"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def field(fm, key):
    """从 frontmatter 取一个标量字段，支持单行引号 / 折叠 / 字面 / 续行。"""
    lines = fm.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^" + key + r":\s*(.*)$", line)
        if not m:
            continue
        first = m.group(1).strip()

        # 折叠(>)、字面(|)及其带修饰符的变体：收集后续缩进行
        if re.match(r"^[>|][+-]?\d*$", first):
            buf = []
            for nxt in lines[i + 1:]:
                if nxt.strip() == "":
                    continue
                if not nxt.startswith((" ", "\t")):
                    break
                buf.append(nxt.strip())
            return " ".join(buf) if first.startswith(">") else "\n".join(buf)

        # 单行已封闭的引号
        if len(first) >= 2 and first[0] == first[-1] == '"':
            return first[1:-1]
        if len(first) >= 2 and first[0] == first[-1] == "'":
            return first[1:-1]

        # 开引号但没闭合，或无引号续行：往后收，直到出现新的顶层 key
        buf = [first]
        started_quote = first[:1] in ('"', "'")
        for nxt in lines[i + 1:]:
            if re.match(r"^[A-Za-z_][\w-]*:\s", nxt):
                break
            if nxt.strip() == "":
                continue
            buf.append(nxt.strip())
            joined = " ".join(buf)
            if started_quote and joined.count(first[0]) >= 2:
                break
        joined = " ".join(buf)
        if started_quote:
            joined = joined.strip('"').strip("'")
        return joined
    return None


def main():
    dump = "--dump" in sys.argv
    show_all = "--all" in sys.argv
    rows = []
    for f in sorted(glob.glob("*/SKILL.md")):
        text = open(f, encoding="utf-8").read()
        n = text.count("\n")
        d = field(frontmatter(text), "description")
        rows.append((os.path.basename(os.path.dirname(f)), n, d, text))

    bad, near, ok = [], [], []
    for name, n, d, _ in rows:
        dlen = len(d) if d is not None else -1
        if n > LINE_LIMIT or dlen > DESC_LIMIT or d is None:
            bad.append((name, n, dlen))
        elif dlen >= 190:
            near.append((name, n, dlen))
        else:
            ok.append((name, n, dlen))

    print("=== 违规 ===")
    for name, n, d in bad:
        tags = []
        if n > LINE_LIMIT:
            tags.append("超500行")
        if d > DESC_LIMIT:
            tags.append("描述超200(=%d)" % d)
        if d < 0:
            tags.append("描述解析失败")
        print("%5d  desc=%5d  %s  [%s]" % (n, d, name, " / ".join(tags)))
    print("合计 %d 个" % len(bad))

    if near:
        print("=== 接近上限（190-200）===")
        for name, n, d in near:
            print("%5d  desc=%5d  %s" % (n, d, name))

    if show_all:
        print("=== 合规 ===")
        for name, n, d in ok:
            print("%5d  desc=%5d  %s" % (n, d, name))

    if dump:
        out = os.path.join(ROOT, "_shared", "_desc_dump.txt")
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            for name, n, d, text in rows:
                if d is None or len(d) <= DESC_LIMIT:
                    continue
                fh.write("#### %s  (%d)\n%s\n\n" % (name, len(d), d))
        print("已导出 -> %s" % out)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
