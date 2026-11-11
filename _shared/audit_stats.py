import os, re, sys, glob

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)

print("=== 行数 / description 长度 ===")
rows = []
for f in sorted(glob.glob("*/SKILL.md")):
    t = open(f, encoding="utf-8").read()
    n = t.count("\n")
    m = re.search(r'^description:\s*"(.*)"\s*$', t, re.M)
    d = len(m.group(1)) if m else -1
    rows.append((f.split("/")[0], n, d))
for name, n, d in rows:
    flag = ""
    if n > 500:
        flag += " [超500行]"
    if d > 200:
        flag += " [描述超200]"
    elif d >= 190:
        flag += " [描述接近200]"
    if flag:
        print(f"{n:5d}  desc={d:4d}  {name}{flag}")
print("---- 无标记的:")
for name, n, d in rows:
    if n <= 500 and d < 190:
        print(f"{n:5d}  desc={d:4d}  {name}")
