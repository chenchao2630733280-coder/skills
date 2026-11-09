# 原语库：语义、坐标约定与组合套路

> 原语库是程序化美术的"笔"。它不该有几十个函数，8–12 个就够画 90% 的东西；
> 缺的不是原语，是**约定**。

---

## 一、三条硬约定

1. **坐标统一 `(col, row)`，原点在左上，row 0 是画面顶部。**
   二维绘图库里 `(x, y)` 常见，但一旦写成 `(x, y)`，代码里就会出现"这个 15 是行还是列"的混乱。
   建议**所有图元签名第一参数是列**，函数名里带方向（`vline(col, r0, r1)`）。
2. **越界自动裁剪，不报错。** 画稿允许"画到画布外面"（树从左边被切一半是正常的构图），
   越界即抛异常会逼你在每处加 `if`，画稿立刻不可读。
3. **空值 ≠ 背景色。** 网格单元允许是 `None`（不铺），"空"和"涂了背景色"在透明度、外框、
   切片逻辑上完全不同。**背景铺满**还是**留空**要在规范里写死，不要一半一半。

---

## 二、原语清单

| 原语 | 签名 | 语义 | 典型用途 |
|---|---|---|---|
| `fill` | `fill(color)` | 整幅铺满 | 背景 |
| `rect` | `rect(r0, r1, c0, c1, color)` | **闭区间**矩形 | 墙、楼体、地、水面 |
| `hline` / `vline` | `hline(r, c0, c1)` / `vline(c, r0, r1)` | 单行 / 单列 | 地平线、树干、浪脊 |
| `disc` | `disc(cx, cy, rad, color)` | 实心圆（按格心判定） | 太阳、月亮、眼睛、果实 |
| `ring` | `ring(cx, cy, rad, thick)` | 圆环 | 光环、月晕、轮胎 |
| `ellipse` | `ellipse(cx, cy, rx, ry)` | 椭圆 | 树冠、云团、脸 |
| `poly` | `poly([(c,r), ...], color)` | 扫描线填充多边形 | 山、三角树、帆、棱角物 |
| `mound` | `mound(r_base, c0, c1, height, color)` | 贴底鼓包（半椭圆） | 丘陵、云朵、浪头、沙丘 |
| `wave` | `wave(r0, amp, period, thick, color)` | 水平波浪带 | 海面、漩涡、云带 |
| `paint` | `paint(mask, color)` | 条件涂色 `mask(r,c,cur)` | 阴影、描边、只改某色区域 |

> 判据：**能用 poly/mound 就不要手写像素循环**。手写循环的代价不是难写，是"换个尺寸就崩"。

---

## 三、组合套路（这七个够用）

### 1. 云 = 鼓包 + 平底

```python
def cloud(g, c0, c1, r, thick=2, color='white'):
    for c in range(c0, c1 + 1):
        t = (c - c0) / max(1, c1 - c0)
        top = round(r - 0.9 * math.sin(math.pi * t) ** 0.8)
        g.vline(c, top, r + thick - 1, color)
```

`thick=1` 会读成一条虚线；**thick ≥ 2** 才成朵。

### 2. 树 = 三角（针叶）/ 椭圆（阔叶）+ 树干

```python
def pine(g, cx, apex, base, half, color):
    g.poly([(cx - half, base), (cx, apex), (cx + half, base)], color)

def broadleaf(g, cx, cy, rx, ry, trunk_color):
    g.ellipse(cx, cy, rx, ry, 'canopy')
    g.rect(cy + ry - 1, base, int(cx) - 1, int(cx), trunk_color)   # 树干 2 列宽
```

**树干必须 ≥2 列**，否则在低分辨率上就是一根杆。

### 3. 浪 = 正弦顶 + 厚脊 + 斜向浪爪

```python
for c in range(0, crest_end):
    top = round(base - amp * math.sin(math.pi * c / span))
    g.vline(c, top, bottom, 'water')
    g.set(top - 1, c, 'foam')          # 脊：1 行，再厚的浪头加到 2 行
```

浪的"方向感"来自**斜向的泡沫条**，不是来自更复杂的曲线：从浪头往右下斜插 3–4 格泡沫即可。
（在 20 行以内的画布上，真正卷起的浪头画不出来，只能到这个程度。）

### 4. 雪冠 = 贴山尖 + 锯齿下缘 + 一格描边

```python
for c in range(cols):
    top = first_row_of(c, 'mountain')
    if top > cap_limit:
        continue
    bottom = 5 if (c // 3) % 2 == 0 else 4      # 三列一段的细锯齿
    if top + 1 < bottom:                         # 留 1 格山体描边
        g.vline(c, top + 1, bottom, 'snow')
```

- **不要"从山尖往下数 N 层"**：山尖那一列的下缘会比邻列高一格，白里透出一小块山体，像山顶破了个洞。
- **不要"填到第 N 行"而不留描边**：雪会盖住山脊线，山尖和浅色天空糊在一起，整座山失去锥形。

### 5. 倒影 = 固定宽度 + 逐行抖动

```python
for i, r in enumerate(range(horizon, rows)):
    shift = (i % 3) - 1
    g.rect(r, r, cx + shift, cx + 1 + shift, 'glint')
```

**按行加宽会堆成金字塔**，读起来像建筑物。

### 6. 窗 / 灯火 = 隔行隔列挖格

```python
for r in range(r0 + 1, r1, 2):
    for c in range(c0 + 1, c1, 2):
        g.set(r, c, 'light')
```

这是"同色被另一种色包在中间"的合法用法 —— 只要它**四周都是墙体**，不会和别的元素黏连。

### 7. 剪影人物/动物 = 躯干矩形 + 2 格腿 + 头 + 特征角

```python
g.rect(12, 14, 20, 26, 'body')   # 躯干
g.rect(10, 11, 25, 26, 'body')   # 颈
g.rect(9, 9, 26, 28, 'body')     # 头
g.set(8, 26, 'body'); g.set(8, 28, 'body')   # 角/耳（2 个点就够）
g.rect(15, 16, 21, 21, 'body')   # 腿（4 条，2 行高）
```

经验值：**5×6 格**是"读得出是活物"的下限；再小就退化成色块。颜色要和背景/远景拉开（不可同色）。

---

## 四、原语不够用时怎么办

按顺序试：

1. **换组合**：两个 poly 叠出山峰起伏；一个 disc + 一个 rect 就是钥匙孔。
2. **加一层**：中景能把"两个色块"变成"一片风景"，比加细节便宜。
3. **删元素**：把画不出的东西删掉，用"留白 + 对比"暗示它（画不出的飞鸟 → 画天空的留白）。
4. 最后才是**加原语**。加一个原语要写清：语义、边界行为、至少两个用途，否则就是过拟合一张画。
