# 三级校验流水线：字符图 → PNG 预览 → 实机截图

> 目标：把"改一版看一眼"的循环压到秒级，同时保证最后一关（实机）不被跳过。

---

## 一、L1 字符图（抓结构性错误）

把网格按 legend 打成 ASCII，每个色一个字母，空/背景一个符号。

```
 0 aaaSSSSaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
 1 aSSSSSSSSaaaaaaaaaaaaaaaaaaaaSSSSSaa
 2 aSSSSSSSSaaaaaaaaSSaaaaaRaaaSSSSSSSa
```

打印时用**固定宽度字体**，否则形状会被字号破坏。看三件事：

1. **列内是否有空洞**（有豆 → 空 → 有豆）：绝大多数"重力/堆叠"类玩法不允许
2. **形状是否闭合**（三角的斜边是否连续、圆是否是圆）
3. **元素是否越界后被意外裁掉**（顶部/底部的第一行是否还有内容）

字符图的优势是**能看数字**：哪一行、哪一列，一眼定位。

---

## 二、L2 PNG 预览（主迭代循环）

零依赖实现（只有 `zlib` + `struct`，不装任何图像库）：

```python
def write_png(path, w, h, pixels):          # pixels: h 行，每行 w*3 字节
    raw = bytearray()
    for row in pixels:
        raw.append(0)                        # filter type 0（None）
        raw.extend(row)
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 6))
           + chunk(b'IEND', b''))
    Path(path).write_bytes(png)
```

要点：

- `IHDR` 用 **8 位 truecolor（color type 2）**，每像素 3 字节，最简单。
- 每行前面必须有一个 filter 字节（写 0 即可），漏掉就是花屏/解不出来。
- **画格子线**：每个单元画 1px 的深色边界（用单元色的暗化版），既能看出网格密度，
  又能立刻暴露"两个色块黏在一起"的问题。
- **拼对比图**：多张画横向拼成一张，一次看完全套，比逐张点开快得多。

性能：36×20 的图在 cell=32 时是 1152×640，纯 Python 逐像素约 0.1–0.3 秒，够用。

---

## 三、L3 实机截图（不可省）

预览图能验证构图，验证不了这四件事：

| 项 | 为什么只有实机能看 |
|---|---|
| 单格真实像素 | 设计宽度 750 → 真机 375，等比缩小后细线会消失 |
| 边距与居中对齐 | 网格尺寸变化时外框是自适应的，可能一侧空一大片 |
| 背景对比 | 画面的浅色部分可能与页面底色接近（浅蓝天空 vs 浅蓝底） |
| UI 遮挡 | 顶栏、进度条、托盘可能压住画面上下沿 |

截图脚本三条纪律：

1. **等真实条件**，不要 `sleep`。低帧率下固定等待必然不稳：等"runtime 就绪""场景 key 出现""某个元素可交互"。
2. **一屏一张，别拼**。要看的是真实观感，拼接会改变缩放。
3. **记录控制台错误**。截图脚本顺手监听 `pageerror`，能提前发现渲染异常。

---

## 四、环境坑（AI 沙箱常见，会被误判成"没画好"）

| 现象 | 真因 | 处理 |
|---|---|---|
| `ERR_CONNECTION_REFUSED` 访问 `127.0.0.1` | 沙箱设了 `HTTP_PROXY`，代理拦了 localhost | 跑脚本前 `export NO_PROXY=127.0.0.1,localhost`（curl 也加 `--noproxy '*'`） |
| dev server 起来了又没起来 | 用 `(cmd &)` 起的进程在命令结束时被回收 | 用后台任务方式启动（托管进程），不要自己 detach |
| 截图里动画/进度永远不动 | 无头软件渲染只有 8–12fps，`requestAnimationFrame` 推进极慢 | 等条件、放宽超时；把"固定 900ms"改成"等状态变化" |
| 某个校验脚本偶发失败、重跑就过 | 同上（低帧率导致时序断言失败） | 在文档里标注"已知假失败"，不要为它改产物 |
| dist 校验连不上 | 预览服务没起（`vite preview` 是另一个端口） | 另起预览服务再跑 |

---

## 五、一张图定稿前的最后三问

1. 缩到真机尺寸还认得出吗？
2. 遮住一半，另一半还像同一个场景吗？
3. 把图给没参与的人看，他的第一句话是"这是什么"而不是"这像什么"？

三问全过，才允许进交付。
