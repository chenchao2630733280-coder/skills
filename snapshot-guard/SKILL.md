---
name: "snapshot-guard"
description: "交付集快照纪律与外部改写取证。改前必刷新快照（唯一回滚兜底），改后必做『磁盘 vs 快照』逐字节比对；发现差异时用 mtime 时序定位外部改写范围，先保全现场再逐条还原。当交付物可能被编辑器/格式化工具/其他会话污染、或需要证明『当前磁盘就是交付时的那一份』时调用。"
---

# 交付集快照纪律与外部改写取证 (snapshot-guard)

## 一、定位与职责

本 skill 管**交付物目录的字节级基线**，解决两个问题：

1. **回滚兜底**：批量改动前留一份可整目录回退的快照。
2. **完整性证明**：随时回答「当前磁盘上的这批文件，就是交付时那一批吗？有没有谁动过？」

**适用**：任何「一批文件 = 一次交付」的项目（静态站点、文档集、发布包、生成产物）。
**不适用**：会话上下文快照（那走 `session-snapshot`）、操作风险拦截（那走 `guardrail`）。

**本 skill 的独特价值**：静态的语法检查、内容规范检查、一致性门禁**全都检测不到「文件被外部改写」** ——
因为它们只看「内容是否符合规则」，而一份被回退过的、被格式化过的文件**内容依然合规**。
唯一能发现的判据是：**与快照逐字节比对**。

职责边界：
- ✅ 负责：建/刷快照、改动前后比对、差异取证、现场保全、逐条还原、还原后复核。
- ❌ 不负责：判断内容对错（那是门禁的活）；本地版本控制（有 git 时优先用 git，本 skill 是**无 VCS 场景**的兜底）。

## 二、快照三态

| 快照 | 内容 | 用途 |
|---|---|---|
| `baseline.zip` | 历史稳定基线 | 长期回滚锚点 |
| `current.zip` | **当前已验收状态** | 「验收入库单」—— 磁盘应当等于它 |
| `current.prev.zip` | 上一轮状态 | 上一轮 diff 校验的对照基准 |

**纪律**：
- **改前必刷**（`current` → `current.prev`，再重建 `current`）—— 否则没有回滚，也没有 diff 基准。
- **改完、门禁全绿后立刻重建 `current`** —— 让「磁盘 == 快照」这条不变式重新成立。
- `current` 与磁盘不一致时，**不要急着重刷快照**：那等于把污染「洗白」成基线。先取证。

## 三、两个核心脚本

### 1. `snapshot.py` — 建/刷快照

```python
import os, zipfile
BASE, OUT = os.path.dirname(os.path.abspath(__file__)), 'current.zip'
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}
SKIP_PARTS = ['/archive/']            # 归档目录通常不进当前交付集（按项目约定）
n = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, BASE).replace('\\', '/')
            if any(s in '/' + rel for s in SKIP_PARTS):
                continue
            z.write(p, rel); n += 1
print('快照 %s：%d 文件 / %.1f KB' % (OUT, n, os.path.getsize(OUT) / 1024))
```

### 2. `snapshot_diff.py` — 逐字节比对（**这是本 skill 的核心判据**）

```python
import os, sys, zipfile
BASE = os.path.dirname(os.path.abspath(__file__))
Z = os.path.join(BASE, sys.argv[1] if len(sys.argv) > 1 else 'current.zip')
z = zipfile.ZipFile(Z)
names = [n for n in z.namelist() if not n.endswith('/')]
miss, diff = [], []
for n in names:
    p = os.path.join(BASE, n.replace('/', os.sep))
    if not os.path.exists(p):
        miss.append(n); continue
    if open(p, 'rb').read() != z.read(n):
        diff.append(n)

print('快照 %s（%d 文件）· 缺失 %d · 不一致 %d' % (os.path.basename(Z), len(names), len(miss), len(diff)))
for n in diff:
    b = open(os.path.join(BASE, n.replace('/', os.sep)), 'rb').read()
    d = z.read(n)
    i = 0
    while i < min(len(b), len(d)) and b[i] == d[i]:
        i += 1
    print('  [差异] %s  disk=%dB  snap=%dB  首个差异@%d' % (n, len(b), len(d), i))
if miss or diff:
    raise SystemExit('不一致：%d 缺失 / %d 差异' % (len(miss), len(diff)))
print('结论：磁盘与快照逐字节一致（%d/%d）✅' % (len(names), len(names)))
```

**反向自检（必做）**：拿**上一轮**的快照去比对，应当报出「该轮改动过的文件」。
若报 0 差异，说明比对脚本在空转（例如 zip 路径分隔符不匹配、或遍历的是 zip 里的名字但判据写错）。

## 四、外部改写取证（五步）

> 真实场景：一轮工作已收工、快照已重建、全部门禁全绿；三分钟后某个交付文档被**外部工具**
> （编辑器自动格式化 / 陈旧缓冲区回写）改成了「改动前的标签 + 重排过的表格」。
> **71/72 文件与快照一致，只有它不一致**；而所有静态门禁照绿。

```
① 全量比对       跑 snapshot_diff.py → 得到「不一致文件清单」
② 时序定位       列 mtime > 快照 mtime 的文件 → 区分「本轮正常改动」与「快照后被改写」
③ 性质判定       【先复跑一次 diff 确认差异仍在 —— 若已自愈属「瞬时写回」，只记档勿还原（还原瞬间
                 可能覆盖正在写入的会话）】差异块的形态：是「新增内容」还是「同长度重排/回退」？
                 行数不变 + 内容回退 + 空白重排 ⇒ 典型的外部格式化/陈旧回写
④ 现场保全       把被改写的文件**另存一份**再动手（见下方命名纪律）
⑤ 覆写还原       用 z.read(rel) 取快照内容写回（**勿用 extractall**）
⑥ 复核           复跑 snapshot_diff（应 N/N）+ 复跑门禁
```

### 现场保全的命名纪律

保全文件用 **`.txt`** 后缀，**不要**用 `.md` / `.py` / `.json`等会被项目扫描器/门禁扫到的后缀 ——
否则这个「取证物」自己会变成新的污染源（被文档审计、行尾检查、内容扫描当成交付物处理）。

### `extractall` 的陷阱

`zipfile.extractall()` **会静默跳过已存在的文件**（不覆盖、不报错）。
用它「回滚」时你会以为还原了，其实什么都没发生。正确做法二选一：

```python
# 方式一：单文件取内容覆写
open(rel, 'wb').write(z.read(rel))

# 方式二：逐条 extract 并显式覆盖（先删再抽）
```

## 五、标准流程（把本 skill 挂进日常工作流）

```
【改动前】刷快照：current → current.prev，重建 current
【改动中】正常编辑（配合 batch-rewrite-surgery 的落盘脚本）
【改动后】跑 snapshot_diff（此时应当有差异 —— 就是你刚改的那些文件，逐条核对是否都是预期）
【收工前】门禁全绿 → 重建 current → 再跑一次 snapshot_diff，必须 N/N ✅
【日常】  任何时候怀疑「有谁动过文件」→ 直接跑 snapshot_diff
```

**最后一条是关键**：`snapshot_diff` 不只是收工仪式，它是**随时可用的完整性探针**。

## 六、产出契约

| 产出 | 说明 |
|---|---|
| `current.zip` / `current.prev.zip` / `baseline.zip` | 三态快照 |
| `snapshot.py` | 建/刷快照脚本 |
| `snapshot_diff.py` | 逐字节比对脚本（只读，退出码 0/1，打印首个差异字节位） |
| `snapshot-guard-report.md` | 取证报告：不一致清单 / mtime 时序 / 差异性质 / 保全位置 / 还原结果 / 复核结论 |

## 七、质量检查清单

- [ ] 改动**之前**已经刷新快照（回滚兜底存在）。
- [ ] 快照排除了版本控制目录、依赖目录、以及项目约定不入快照的归档目录。
- [ ] 快照文件计数与预期一致（页数/文件数符合项目基线）。
- [ ] 收工前跑过 `snapshot_diff`，且达到 **N/N 逐字节一致**。
- [ ] `snapshot_diff` 做过**反向自检**（拿上一轮快照应报出该轮改动）。
- [ ] 发现差异时：先查 mtime 时序，再判差异性质，**未直接重刷快照掩盖差异**。
- [ ] 动手还原前已**复跑确认差异仍在**；「瞬时写回（自愈型）」只记档未还原。
- [ ] 现场已保全，且保全文件用的是**不会被扫描器误扫的后缀**。
- [ ] 还原用 `read + write` 或显式覆盖，**未用 `extractall`**。
- [ ] 还原后已复跑比对与门禁，并更新 `current.zip`。
- [ ] 取证报告记录了「谁在什么时候、把哪个文件、改成了什么形态」。

## 八、参考

- `references/forensics.md` — 外部改写取证速查（差异形态判读表 / mtime 时序 / 常见元凶）。
