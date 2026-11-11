"""流水线与 Skill 的机械体检（一次性/可重复使用）。

检查项：
  A 每个 SKILL.md：行数、description 长度、references 孤儿与悬空
  B runtime.yaml outputs 是否在 SKILL.md 里被提及（承诺了却没写 = 没人读）
  C 总纲路径总表 与 各 skill runtime outputs 的差集（产物矩阵闭合性）
  D 门禁失败码重复定义
  E 文件内 §x.y 引用是否指向存在的标题

不做的事：判断"内容对不对"。那需要人读。本脚本只负责把机械问题一次列干净。
用法：python _shared/audit_pipeline.py [--only game-*]
"""
from __future__ import annotations

import os
import re
import sys
import glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def runtime_paths(skill):
    """从 runtime.yaml 里粗取 inputs/outputs 的 path 与 name。"""
    p = os.path.join(ROOT, skill, "runtime.yaml")
    if not os.path.exists(p):
        return None
    txt = read(p)
    outs, ins = [], []
    section = None
    cur = None

    def flush():
        nonlocal cur
        if cur and section == "out" and cur.get("type") != "inline" and cur.get("path"):
            outs.append(cur["path"])
        if cur and section == "in":
            ins.append(cur.get("path") or cur.get("name") or "")
        cur = None

    for line in txt.split("\n"):
        s = line.strip()
        if s.startswith("outputs:"):
            flush()
            section = "out"
            continue
        if s.startswith("inputs:"):
            flush()
            section = "in"
            continue
        if s.startswith("degrade:"):
            flush()
            section = None
            continue
        if s.startswith("- ") and section:
            flush()
            cur = {}
            s = s[2:]
        if cur is None or section is None:
            continue
        m = re.match(r"(path|name|type):\s*(.+)$", s)
        if m:
            cur[m.group(1)] = m.group(2).strip()
    flush()
    return {"inputs": [x for x in ins if x], "outputs": outs}
    return {"inputs": ins, "outputs": outs}


def headings(text):
    """抽出所有标题编号：'## 八、证据分级' -> '八'；'### 8.3 xxx' -> '8.3'；'## 四、工作流' -> '四'。"""
    nums = set()
    for line in text.split("\n"):
        m = re.match(r"^#{2,4}\s+([0-9]+(?:\.[0-9]+)?|[一二三四五六七八九十]+)[、.\s]", line)
        if m:
            nums.add(m.group(1))
        m = re.match(r"^#{2,4}\s+([0-9]+(?:\.[0-9]+)?)[)）\s]", line)
        if m:
            nums.add(m.group(1))
    return nums


def audit_skill(skill):
    issues = []
    p = os.path.join(ROOT, skill, "SKILL.md")
    if not os.path.exists(p):
        return [("A", "无 SKILL.md")], {}
    txt = read(p)
    lines = txt.count("\n")
    if lines > 500:
        issues.append(("A", "SKILL.md %d 行 > 500" % lines))
    m = re.search(r'^description:\s*"(.*)"\s*$', txt, re.M)
    dlen = len(m.group(1)) if m else -1
    if dlen > 200:
        issues.append(("A", "description %d 字符 > 200" % dlen))

    refdir = os.path.join(ROOT, skill, "references")
    if os.path.isdir(refdir):
        files = sorted(f for f in os.listdir(refdir) if f.endswith((".md", ".json")))
        has_range = re.search(r"references/\d\d\s*[–\-—~]\s*\d\d", txt)
        for f in files:
            stem = f.rsplit(".", 1)[0]
            if stem in txt:
                continue
            # 数字前缀的文件允许用区间写法引用（references/01–05）
            if has_range and re.match(r"^\d\d[_-]", f):
                continue
            issues.append(("A", "孤儿 reference：references/%s 从未被 SKILL.md 提及" % f))
    # 只认本 skill 自己的 references/（前面不能是别的目录名，如 game-xxx/references/...）
    for tok in set(re.findall(r"(?<![/\w\-])references/([A-Za-z0-9_\-.]+\.(?:md|json))", txt)):
        if not os.path.exists(os.path.join(ROOT, skill, "references", tok)):
            issues.append(("A", "悬空 reference：references/%s 不存在" % tok))

    hd = headings(txt)
    # 跨文件引用（"game-spec §2.3" / "PRD §1.5" / "`docs/LEVEL_AUTHORING.md` §1 … §7"）不算悬空。
    # lead 取"该行 § 之前的全部内容"，不能只取前 N 个字符：一句话里连续列举多个 § 时，
    # 第二个之后的 § 前面已经没有文档名了，窗口写法会把它们全部误报（实测 29 条全误报）。
    DOCPREFIX = re.compile(
        r"(game-[a-z-]+|PRD|TECH_DESIGN|AUDIO_SPEC|ART_SPEC|LEVEL_PLAN|LEVEL_AUTHORING|"
        r"GAME_BLUEPRINT|LEVEL_GENERATOR_SPEC|DIFFICULTY_REPORT|BUILD_REPORT|refs\d+|"
        r"docs/|\.md`|_SPEC\.|_REPORT\.|报告|手册|模板|规范|契约|清单|蓝图|说明)")
    prev = ""
    table_head = ""
    for lineno, line in enumerate(txt.splitlines(), 1):
        # 表格上下文：表头写了是哪份文档，表体里的 § 都继承它
        if line.lstrip().startswith("|"):
            if not table_head:
                table_head = line
        else:
            table_head = ""
        if "§" not in line:
            prev = line
            continue
        # 跨行引用：文档名只在上一行（"`AUDIO_SPEC.md` 的参数表 → 下文都写 §2.6"）或本表表头
        inherit = bool(DOCPREFIX.search(prev) or DOCPREFIX.search(table_head))
        for m in re.finditer(r"§\s*([0-9]+(?:\.[0-9]+)?)", line):
            lead, ref = line[:m.start()], m.group(1)
            if inherit or DOCPREFIX.search(lead):
                continue
            if ref not in hd:
                issues.append(("E", "§%s 引用无对应标题（第 %d 行,同文件内找不到该编号）" % (ref, lineno)))
        prev = line

    rt = runtime_paths(skill)
    if rt:
        for out in rt["outputs"]:
            base = os.path.basename(out.rstrip("/"))
            if not base:
                continue
            # 形如 docs/GATE_[0-3]_REPORT.md / docs/GATE_{0,1,2,3}_REPORT.md：取固定前缀再比
            m2 = re.match(r"([A-Za-z_]+)[\[{]", base)
            probe = m2.group(1) if m2 else base
            if probe and probe not in txt:
                issues.append(("B", "runtime output %r 未在 SKILL.md 出现（产出了但没写）" % out))
    return issues, {"lines": lines, "desc": dlen, "runtime": rt}


def master_table():
    """总纲 §八 路径总表里的产物路径。"""
    p = os.path.join(ROOT, "game-forge-master", "SKILL.md")
    txt = read(p)
    paths = set()
    for line in txt.split("\n"):
        if line.startswith("|") and line.count("|") >= 4:
            for cell in line.split("|")[1:-1]:
                for tok in re.findall(r"`([^`]+)`", cell):
                    if "/" in tok or tok.endswith((".json", ".md", ".ts", ".html", ".csv", ".yaml", ".py", ".gd", ".cs")):
                        paths.add(tok.split(" ")[0])
    return paths


def main():
    skills = sorted(d for d in os.listdir(ROOT)
                    if d.startswith("game-") and os.path.isdir(os.path.join(ROOT, d)))
    all_issues = {}
    meta = {}
    for s in skills:
        iss, m = audit_skill(s)
        all_issues[s] = iss
        meta[s] = m

    print("=" * 70)
    print("A/B/E 逐 skill 问题")
    print("=" * 70)
    for s in skills:
        if all_issues[s]:
            print("\n## %s  (行数 %s / desc %s)" % (s, meta[s].get("lines"), meta[s].get("desc")))
            for code, msg in all_issues[s]:
                print("  [%s] %s" % (code, msg))
        else:
            print("%-24s  clean (行数 %s / desc %s)" % (s, meta[s].get("lines"), meta[s].get("desc")))

    print()
    print("=" * 70)
    print("C 产物矩阵：总纲路径总表 vs 各 skill runtime outputs")
    print("=" * 70)
    mp = master_table()
    declared = {}
    for s in skills:
        rt = meta[s].get("runtime") or {"outputs": []}
        for o in rt["outputs"]:
            declared.setdefault(o, []).append(s)
    for o, owners in sorted(declared.items()):
        base = os.path.basename(o.rstrip("/"))
        m2 = re.match(r"([A-Za-z_]+)[\[{]", base)
        probe = m2.group(1) if m2 else base
        if not any(probe in x for x in mp):
            print("  未登记总表: %-46s (%s)" % (o, ",".join(owners)))

    print()
    print("=" * 70)
    print("D 失败码唯一性（game-quality-gate）")
    print("=" * 70)
    gt = read(os.path.join(ROOT, "game-quality-gate", "SKILL.md"))
    CODE = r"`(G[0-9A-Z_]*\d+-[A-Z0-9-]+|G25-\d+)`"
    defined = defaultdict(list)   # 表格行里"定义"的码（末列）
    used = defaultdict(list)      # 全文出现过的码（含正文交叉引用）
    for line in gt.split("\n"):
        hit = set(re.findall(CODE, line))
        for c in hit:
            used[c].append(line[:40])
        # 定义 = 出现在表格行里的码。列位置不固定（Gate 3 的表格末列是"级别"），
        # 因此不按列判定；正文里的交叉引用不计入定义。
        if hit and line.lstrip().startswith("|"):
            for c in hit:
                defined[c].append(line[:40])
    dup = {k: v for k, v in defined.items() if len(v) > 1}
    dangling = {k: v for k, v in used.items() if k not in defined}
    print("  失败码定义 %d 个（表格行），全文引用 %d 个" % (len(defined), len(used)))
    for k, v in sorted(dup.items()):
        print("  [DUP] 同码定义多行 %-18s x%d  (首行: %s)" % (k, len(v), v[0].strip()))
    for k, v in sorted(dangling.items()):
        print("  [DANGLING] 引用未定义 %-16s  (首行: %s)" % (k, v[0].strip()))
    if not dup and not dangling:
        print("  clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
