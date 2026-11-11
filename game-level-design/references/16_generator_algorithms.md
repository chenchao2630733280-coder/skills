# 16 生成路径的算法伪代码（五工位 + 反向生成）

> 本文是 `references/15` 的下钻层：**15 说"用什么"，16 说"怎么写"**。
> 只给伪代码、判据与反例，**不给可运行实现**——算法是机制无关的，实现一定绑定状态表示，
> 而"状态怎么表示"恰恰是最该按自己游戏重写的一段。给代码会让人连状态表示一起照抄。
>
> 读法：先按 15 §1 定下要哪几个工位，再回本文取对应的伪代码段。没开的工位直接跳过。

---

## 0 一句话

这五段伪代码的共同前提是**状态定义先行**。状态定义错，后面所有优化都是在错的搜索空间上做加速。
下面每段都先给状态，再给迁移，最后给剪枝。

---

## 1 工位 A：量化

### A-1 定点调色板（颜色是机制旋钮时用这个）

```
to_palette(grid, palette):
    for each pixel p in grid:
        grid[p] = argmin_i dist2(p, palette[i])      # 最近邻，无随机
    return grid
```

确定性来自"无随机"，代价是画稿色域跨度大时会被压死。

### A-2 K-means（颜色数由算法决定时用）

```
kmeans(points, k, seed):
    centers = [points[rand(seed)]]
    while len(centers) < k:                          # k-means++ 初始化
        w[i] = min_j dist2(points[i], centers[j])     # 到最近中心的平方距离
        centers.append(sample(points, weights=w))     # 按 w 加权抽一个
    repeat until 中心不再移动 or 达到迭代上限:
        labels[i] = argmin_j dist2(points[i], centers[j])
        centers[j] = mean(points where labels == j)   # 空簇保留原中心，不删
    return centers, labels
```

三个容易写错的地方：

1. **空簇**：某一轮没有任何点归到中心 j，不能删（会让 k 变小），保留原值继续。
2. **平局**：`argmin` 遇到等距必须取下标小的，否则两次运行结果不同（不确定性来自浮点比较顺序）。
3. **迭代上限**：必须设，且设了要报"未收敛"。不收敛的量化结果不能进关卡——它会随机器抖动。

### A-3 量化后必须算的指标

```
blocks[color] = 连通块数(4 邻接)
fragmentation = Σ blocks / Σ pixels
```

`fragmentation` 直接决定关卡碎度与操作步数。量化完不看它就直接进工位 B，
等于把难度交给图片本身的噪点——这是"同一批画稿产出难度乱跳"的根因。

**k 怎么定**：不是拍脑袋，是看 `fragmentation` 随 k 的拐点。k 增大到碎度开始陡升的位置，
就是"再细分只会更碎、不会更清楚"的位置。

---

## 2 工位 B：分配

### 精确分割（I1 的落地形态）

```
exact_partition(amount, cap_lib):
    best[0] = 0                                       # best[s] = 凑出 s 的最少根数
    for s in 1..amount:
        for c in cap_lib:
            if s >= c and best[s-c] + 1 < best[s]:
                best[s] = best[s-c] + 1
                last[s] = c                           # 记录选择，用于回溯
    if best[amount] == INF: return None               # 无解 → 报错，不向上取整
    caps = []
    s = amount
    while s > 0: caps.append(last[s]); s -= last[s]
    return sorted(caps)
```

**为什么必须精确，不能"多给一点"**：
多给的那部分容量在正向游玩时永远吃不掉，会永久占住一个容器位。这就是 15 §3 I1 的反例。
`Σcap > need` 不是"容错"，是"埋了一颗必输的雷"。

### 复杂度

`O(amount × |cap_lib|)`，amount 是单色需求总量（几百量级）。逐色独立，可并行。

---

## 3 工位 C：布局

```
layout_from_plan(plan, positions, seed):
    depth = {}                                        # 每个 pos 当前的层号
    for i, (color, cap) in enumerate(plan):           # plan 是消耗序
        pos   = (i + rand(seed)) % positions          # 位置随机，层号不随机
        layer = depth[pos]                            # 先消耗的 → 层号小 → 靠外
        depth[pos] += 1
        emit spool(color, cap, pos, layer)
```

**为什么层号不能随机**：层号是"可达序"的编码。随机化层号等于随机化依赖关系，
I2（需求序 ⊑ 可达序）立刻失效，生成出来的关卡会"先要的东西被后解锁的压着"。

**随机性只放在 `pos` 上**：位置分配决定"哪些线轴互不遮挡"，也就是解法空间的分叉。
位置全随机会破坏 I2 吗？不会——同一 pos 上，layer 严格按消耗序递增，所以堆内顺序永远正确。

### I2 由构造保证（不需要事后检查）

对同一 `pos` 上的任意两根线轴 `a`（第 i 个）、`b`（第 j 个），若 `i < j` 则 `layer(a) < layer(b)`，
即 a 压着 b。玩家必须先取 a 才能取 b，与消耗序一致。∎

跨 pos 之间无约束，所以"多条解法"来自位置分配，而不是来自层号。

---

## 4 工位 D：可解性验证

### 状态

```
state = (remaining_need 向量, 存活位掩码 alive, 托盘占用 used)
```

`used` **必须**进状态。漏了它，不同托盘占用的局面会被当成同一个状态合并，结果是把可解判成无解。

### 可见性（O(1) 而不是 O(n)）

```
covered_by[j] = 位掩码：所有压住 j 的线轴（同 pos 且 layer 更小）
visible(alive) = { j : alive[j] and (covered_by[j] & alive) == 0 }
```

位掩码让"这根还能不能碰"从"遍历整堆"降成一次按位与。批量生成时这一步是热路径。

### 迁移

```
successors(state):
    for j in visible(alive):
        take   = min(cap[j], need[color[j]])
        left   = cap[j] - take
        extra  = 1 if left > 0 else 0                 # 余量永久占一格
        if used + extra > tray: continue              # 装不下，非法迁移
        yield (need - take, alive - j, used + extra)
```

### 剪枝三条（缺一条就会在批量里超时）

| # | 剪枝 | 判据 |
|---|---|---|
| 1 | 死锁 | 可见集合为空，或任何迁移都装不下 → 该分支死 |
| 2 | 容量上界 | 剩余 need 总量 > 剩余可见容量 → 不可能完成（可按颜色分别算，更强） |
| 3 | 记忆化 | `(need, alive, used)` 已判死过就不再展开；key 必须含 `used` |

### 两个搜索，回答两个不同问题

```
BFS  → shortest_len（最短解长度）
DFS  → solutions（解路数，枚举到上限即停）、peak_min（所有找到的解里的最小托盘峰值）
```

**别用一个搜索回答两个问题**：BFS 天然给最短但不给解数，DFS 给解数但不保证最短。
强行合并的结果是"要么答案不全，要么跑不完"。

### 预算与截断

必须显式区分三种返回：**有解 / 无解 / 超预算未判定**。
把"超预算"当"无解"是这类引擎最常见的谎报——它会让生成器丢弃大量本来可用的关卡，
而且没有任何报错。

---

## 5 工位 E：打分

```
score(level):
    naive  = 玩家策略(随机挑可见线轴)      跑 N 次 → 通过率 p_n
    strict = 玩家策略(优先整根能吃完的)    跑 N 次 → 通过率 p_s
    return (p_n, p_s)
```

| p_s | p_s − p_n | 判定 | 动作 |
|---|---|---|---|
| < 0.6 | — | 太难或数据有问题 | 别信这个分，先查规则/状态定义 |
| ≥ 0.6 | < 0.15 | 没有决策（怎么玩都一样） | 加约束或加干扰项，别加步数 |
| ≥ 0.6 | ≥ 0.15 | 有决策 | 进曲线，按 p_s 排序 |
| > 0.9 且 p_n > 0.85 | — | 太简单 | 降容量库上限或加层数 |

**两个通过率的差距才是"有没有决策"的信号**，单个通过率只能排难度，判断不了好玩。

---

## 6 反向生成：完整伪代码

```
reverse_generate(need, cap_lib, tray, positions, waste):
    plan = exact_partition_per_color(need, cap_lib)        # ① I1 检查点
    if plan is None: raise "需求无法精确分割"               #    宁可报错，不许向上取整

    repeat up to attempts:
        seq = shuffle(flatten(plan) + waste_spools)        # ② 决定消耗序
        spools = layout_from_plan(seq, positions)          # ③ I2 由构造保证
        peak = simulate_plan_peak(seq, tray)               # ④ I4 检查点
        v = solve(spools, tray)                            # ⑤ 仍要验证（目的变了）
        if not v.solvable: continue
        if peak < tray: return spools                      # 留 1 格余量，不是"满了再补"
    return best_effort or raise
```

四个检查点与不变量的对应：① → I1、③ → I2、`waste` 的数量约束 → I3、④ → I4。

**⑤ 为什么不能省**：反向只保证"有解"（那条 seq 就是一条解），不保证解路数、不保证峰值。
验证目的从"存在性"变成"解有多少条、最短多长、峰值多高"。省掉这一步，产物就是
"必然能通关，但只有一条路、全程挤托盘"——数据上 100%，体验上照着唯一路径点完。

---

## 7 三个"照抄会出错"的地方

### 7.1 精确分割下，托盘压力恒等于 0（最容易踩）

设某色需求 `need_c`，容量拆分满足 `Σ cap_i = need_c`（精确分割）。按任意顺序取第 i 根时：

```
remaining = need_c − Σ_{j<i} cap_j = Σ_{j≥i} cap_j ≥ cap_i
```

所以 `cap_i ≤ remaining` 恒成立 → 每根都被整根吸收 → 余量恒为 0 → 托盘永远不占。

**结论：托盘压力不是"容量库"的函数，是"余量 + 干扰项"的函数。**

- 机制 M1（整根吸收、容量精确分割）：`压力 = 干扰项根数`。不做干扰项，托盘就是空的。
- 机制 M2（允许部分消耗、余量进托盘）：`压力 = 余量根数 + 干扰项根数`。

这条推论很反直觉，但它是"照抄容量库 + 精确分割，做出来的关卡全都轻松通过"的根因：
**你搭的是一套不会产生压力的机制，再怎么调容量分布都不会有压力。**

想要压力，只有三条路：加干扰项（M1/M2 都行）、让容量与需求不整除（M2）、
靠遮挡增加跨色顺序约束（两种机制都行，但它是间接的）。

### 7.2 记忆化 key 漏掉托盘占用

`(need, alive)` 相同但 `used` 不同的两个局面，可达性完全不同：`used` 大的更容易死。
合并它们 → 一个"其实还能走"的局面被判死 → 生成器误丢好关（假阴性）；
反向若把"已死"当"可复用"，还会在别的分支上给出错误结论。

**记住：状态里所有会影响可达性的字段都必须进 key，一个都不能省。**

### 7.3 可见性缓存了"死的"结果

`visible` 必须在**当前存活集合**上重算。缓存成"这根永远不可见"会在上层被取走后失效，
表现为"明明能拿却拿不到"——验证器判无解，但人一眼看出有解。

---

## 8 复杂度与预算速查

| 工位 | 复杂度 | 什么时候会成为瓶颈 |
|---|---|---|
| A 量化 | `O(pixels × k × iters)` | 大图 + k 大；先降采样再聚类 |
| B 分配 | `O(amount × |cap_lib|)` | 几乎不会 |
| C 布局 | `O(n)` | 不会 |
| D 验证 | 状态数 × 分支数，指数级 | **唯一的真瓶颈**：靠剪枝和记忆化压，不是靠换语言 |
| E 打分 | `O(trials × n)` | 与 D 相乘，先降 trials 再谈 |

先做 7.2 和 §4 的三条剪枝，再谈性能。换语言排在最后（15 §5）。

---

## 9 与 15 的接口

| 15 决定 | 16 给什么 |
|---|---|
| 开哪几个工位 | 每工位一节，没开就跳过 |
| 每站用什么算法 | 对应伪代码；同一工位给了两三种变体时，看"别用它"的条件 |
| 四条不变量怎么落地 | §6 的四个检查点 + §7.1 的压力来源分析 |
| 大约多久能跑完 | §8 速查表 |
