---
name: html-single-file-pack
description: 把多文件静态站点（HTML + CSS + JS + 本地图片）打包成一个自包含单文件 HTML——CSS/JS/图片全部内联，零外部依赖，双击即开、云端上传不丢图。当出现「上传到资料库/云文档/网盘后图片全裂」「发给别人打开是空白」「单文件里地图/图表/某一块整块空白但自包含检查全绿」「需要离线单文件交付」时调用。含 img() 双源兼容改造、加载失败降级占位、自包含性核查、原图优先/体积超标才压缩的取舍规则，以及 String.replace 的 $$ 转义陷阱、数据文件漏内联导致模块静默早退等必踩坑。
agent_created: true
---

# 单文件 HTML 打包（自包含交付）

把「一个 HTML + 一堆兄弟文件」的多文件站点，压成**单个 HTML 文件**，所有资源内联。

## 何时使用

| 信号 | 说明 |
| --- | --- |
| 上传到**资料库 / 云文档 / 网盘**后图片全部裂图或空白 | 最常见。这些渠道只带走你选中的那一个文件 |
| 「我发给同事/客户，他打开全是白板」 | 同上，对方没有 assets 目录 |
| 需要**离线**携带（U 盘、微信转发、断网演示） | 单文件天然满足 |
| 需要单文件归档 | 一个 HTML 就是全部 |

**不适用**：站点要长期在线托管（用 GitHub Pages / 发布为应用 / CDN，多文件更优）；站点本身有后端接口。

## 根因（一句话）

多文件版靠**相对路径**引用兄弟文件：

```html
<link rel="stylesheet" href="css/style.css">
<img src="assets/img/a-1.jpg">
```

云端资料库上传**只带走单个 `index.html`**，`css/`、`js/`、`assets/` 不会跟着走。
结果：如果 CSS 也被内联过（或用了行内样式），页面看起来「正常的空壳」；图片则**全 404**。

---

## 六步法

### 0. 先勘察：到底丢了什么

打包前先列清单，别凭印象：

```bash
python tools/selfcheck.py path/to/index.html   # 列出所有非内联外部引用
```

分类处理：

| 资源类型 | 处理方式 |
| --- | --- |
| `<link rel="stylesheet" href="本地.css">` | 读入 → 包进 `<style>` |
| `<script src="本地.js">` | 读入 → 包进 `<script>`（**注意执行顺序**） |
| 静态 `<img src="assets/x.jpg">` | 转 base64 data URI |
| CSS 里的 `url(assets/x.png)` | 转 base64 data URI |
| JS 里**动态拼**的图片路径 | 改 `img()` 解析函数（见第 2 步）——**这一步最容易被漏掉** |

> **关键判断**：如果图片路径是 JS 在运行时拼出来的（如 `'assets/img/' + f`），那么静态扫描查不到，必须改代码。绝大多数数据驱动站点都属此类。

### 1. 图片：默认内联原图，只在体积超标时才压

**先记住两个数字**：base64 的膨胀率是 **4/3 ≈ 1.333**（3 字节 → 4 字符），不是「约 37%」。
所以「34.2 MB 原图 → 约 45.6 MB base64」，这个换算要先算清楚，再决定压不压。

**默认策略：不压缩，直接内联原图。** 理由：

- 单文件版的存在意义是「换了存放方式」，不是「换了画质」。内联原图后画质与多文件版**逐像素一致**，用户没有理由为此接受损失。
- 只要没撞上传上限，压缩就是**纯亏**：画质下降、细节丢失，用户一看就发现「图糊了」。
- 用户如果明确说过「不要压缩」「用原图」，那是硬约束，不要自作主张替 TA 折中。

**只有确认体积超标时才压**，且按下面顺序妥协（越靠前损失越小）：

1. **先砍数量**——从「全部保留」降到「列表页 1 张 + 详情页 1 张」。体积直接腰斩，且用户通常不会逐张数图。
2. **再降质量**——分层设定像素与质量：

   | 用途 | 宽度 | 质量 |
   | --- | --- | --- |
   | 封面 / 首屏大图 / 卡片 | ≤1080px | q71 |
   | 详情页内图 / 缩略 | ≤800px | q66 |
   | 图标 / 占位 | 保持原样 | — |

3. **最后才考虑换交付通道**——用「发布为应用」/ 静态托管（支持多文件目录），彻底绕开单文件体积限制。

**打包器应同时支持两种来源，用一个开关切换**（参考实现）：

```bash
node tools/build-standalone.js                    # --source=orig（默认）内联原图
node tools/build-standalone.js --source=webp      # 需要时改用压过的图
node tools/build-standalone.js --out=轻量版.html --source=webp   # 两版并存
```

这样默认交付无损画质，体积真出问题时一行命令切档，不用重写打包逻辑。

用 `tools/shrink_images.py` 生成压缩档并打印体积报告：

```bash
python tools/shrink_images.py <图片目录> <输出目录> --tiers cover=1080,71 detail=800,66
```

> **反例（真实教训）**：一开始默认做了「118 张 WebP / 7.5MB」的压缩版，用户随即要求「不要压缩图片，用原图片」。
> 白做一轮压缩，还差点把一个画质受损的版本交付出去。**先问/先按原图做，压是例外。**

### 2. 让代码同时兼容两种来源（关键改造）

**不要为单文件版维护第二份代码**。让同一份 `app.js` 同时认得相对路径和 `data:` URI：

```js
// 三种来源统一：data URI / http(s) / blob 原样返回，其余当相对路径补前缀
const img = (f) => (!f ? '' : /^(data:|https?:|blob:)/.test(f) ? f : 'assets/img/' + f);
```

这样多文件版和单文件版可以共用同一份 JS，只是传入的字符串不同。

### 3. 图片失败降级：绝不出现裂图

打包难免有漏网之鱼（某个图没被内联、某条目缺图）。**裂图图标比空白更难看**，所以给所有 `<img>` 挂错误降级：

```js
function fallback(el, label) {
  const ph = document.createElement('div');
  ph.className = 'img-ph';
  ph.textContent = label || '';
  el.replaceWith(ph);
}
function wireImg(el, label) {
  el.addEventListener('load',  () => el.classList.add('is-loaded'), { once: true });
  el.addEventListener('error', () => fallback(el, label),            { once: true });
}
// 惰性加载的图事后才进 DOM，需要可重复调用的批量挂钩
function wireAll(scope) {
  $$('img[src]:not([data-wired])', scope).forEach((el) => {
    el.setAttribute('data-wired', '1');
    if (el.complete && el.naturalWidth > 0) el.classList.add('is-loaded');
    else wireImg(el, el.getAttribute('alt') || '');
  });
}
```

配套 CSS（用背景色系延续站点基调，而不是突兀的红叉）：

```css
.img-ph{
  width:100%;height:100%;min-height:110px;display:grid;place-items:center;padding:14px;
  background:linear-gradient(135deg,#0E1A2B 0%,#16263C 45%,#0B1420 100%);
  color:var(--muted-2);font-size:12px;letter-spacing:.12em;text-align:center;
  border-radius:12px;line-height:1.6;
}
```

**别忘**：详情抽屉、月份切换、收藏列表等「事后渲染」的容器，都要在渲染完成后补一次 `wireAll(container)`。

### 4. 打包：内联一切

用 `tools/pack_html.py`：

```bash
python tools/pack_html.py index.html -o 单文件版.html \
  --css css/style.css \
  --js data/part1.js data/part2.js js/app.js \
  --images-dir build/webp \
  --js-image-map build/image-map.json
```

> `--js-image-map` 是给「JS 动态拼路径」用的：一个 `{"原相对路径": "data:image/webp;base64,..."}` 映射表，
> 打包器把它注入成 `window.__INLINE_IMAGES__`，然后让第 2 步的 `img()` 先查表再回退。

或者按项目实际情况手写打包脚本（见下方「手写打包的骨架」）。

### 5. 自包含性核查（必做）

```bash
python tools/selfcheck.py 单文件版.html
```

合格标准：

```
assets 残留 : 0
外链样式表  : 0
外部引用    : 无
结论        : ✅ 完全自包含，可直接上传云端
```

### 6. 隔离验证（强烈建议）

**在新开的空目录里**打开单文件版，确认没有偷偷依赖原目录：

```bash
mkdir /tmp/isolated && cp 单文件版.html /tmp/isolated/ && cd /tmp/isolated && <用浏览器打开>
```

配合 Playwright 断言：卡片数、图片 `naturalWidth>0` 数量、占位块数量（应为 0）、console error（应为 `[]`）、网络失败（应为 `[]`）。

**断言写法有三个必踩的坑**（都是实测踩出来的）：

1. **必须逐屏滚动，不能一次跳到底**——惰性加载靠 IntersectionObserver 触发，`scrollTo(0, scrollHeight)` 会让中间大片图片从未进入视口，统计时全是「未加载」，看起来像坏了。

   ```js
   await page.evaluate(async () => {
     const step = Math.round(window.innerHeight * 0.8);
     for (let y = 0; y < document.body.scrollHeight; y += step) {
       window.scrollTo(0, y);
       await new Promise((r) => setTimeout(r, 220));
     }
   });
   await page.waitForTimeout(4000);   // 大 base64 需要解码时间
   ```

2. **滚动容器要找对**——抽屉/弹层这类 fixed 全高面板，滚动条在**面板自己**身上（如 `.drawer__panel`），不是里面的 `.drawer__body`。滚错元素 → 内部图永远不加载。

3. **按类名统计容易漏**——「卡片」在列表区叫 `.card`、在横轨里可能叫 `.fcard`、画廊图挂在 `#dGallery` 下。先 grep 源码确认真实类名，别凭感觉写选择器。

> `naturalWidth === 0 && complete === true` 对**未赋 src 的惰性图**同样成立，所以「未加载」要区分「还没轮到」和「真的失败」——**用占位块数量（`.img-ph`）判失败，用滚动触发判遗漏**，两者都为 0/正常才算过。

---

## 手写打包的骨架

```js
const css   = fs.readFileSync('css/style.css', 'utf8');
const parts = ['data/part1.js','data/part2.js','data/images.js','js/app.js']
  .map(f => '/* ==== ' + f + ' ==== */\n' + fs.readFileSync(f, 'utf8'));
const inlineScript = parts.join('\n;\n') + '\n;\n' + inlineImagesJs;

/* ---------- 拼装：必须用「函数式替换」 ----------
 * 若把内联内容直接当字符串传给 replace()，JS 会把替换串里的
 * `$$` 当作转义符还原成 `$`（`$&` / $` / $' 同理），从而**静默破坏源码**。
 * 典型后果：`const $$ = ...` 变成 `const $ = ...`
 *        → Identifier '$' has already been declared + $$ is not defined
 *        → init() 抛错 → 页面白屏（只剩 nav 和 footer）。
 */
const out = body
  .replace('</head>', () => '<style>\n' + css + '\n</style>\n</head>')
  .replace('</body>', () => '<script>\n' + inlineScript + '\n</script>\n</body>');
```

---

## 必踩的坑（按血亏程度排序）

### 1. `String.replace` 的 `$$` 陷阱 —— 会导致白屏，且极难定位

替换串中的 `$$` → `$`、`$&` → 匹配到的子串、`` $` `` → 匹配前的内容、`$'` → 匹配后的内容。

`const $$ = (s, r) => ...` 这种「jQuery 风格双美元选择器」在国内项目里很常见，一旦被内联就必炸。

**症状**：单文件版白屏（只剩 nav / footer，卡片数为 0），但多文件版完全正常——因为只有打包路径会走到这段代码。

**定位手法**：

```bash
node -e "const vm=require('vm'),fs=require('fs');new vm.Script(fs.readFileSync('build/inline.js','utf8'))"
# 报 SyntaxError: Identifier '$' has already been declared  → 就是它
grep -n 'const \$\$\? *=' build/inline.js     # 看是不是变成单 $ 了
```

**修复**：`replace(needle, () => text)` —— 永远用函数式替换。

### 2. 忘了改「JS 动态拼路径」

静态扫描查不到，页面依旧一片裂图，你会以为打包没生效。**先确认图片路径是写在 HTML 里还是拼在 JS 里。**

### 3. 漏内联「模块加载时就被读」的数据文件 —— 自检会过，功能整块空白

单个 HTML 里的 `<script>` 是**按顺序同步执行**的。如果某个模块是 IIFE，它**在加载那一刻**就会去读全局数据：

```js
// js/map.js
(function () {
  const MAP = window.MAP_CHINA;      // ← 执行到这里时，MAP_CHINA 必须已经存在
  if (!MAP) return;                  // 早退，不报错、不抛异常
  ...
})();
```

数据文件（`data/map-china.js` / `data/gateways.js` / `data/spots1-3.js`）一旦漏进内联清单、或排到了模块后面，
模块就**静默早退**：页面其他部分全正常，只有那一块渲染不出来（地图空白 / 图表空白 / 列表空）。

**为什么难发现**：外部引用数、`assets/` 残留、图片数全部合格 —— 因为**真的没有外部依赖**，自包含性核查会一路绿到「✅ 完全自包含」。

**修复**：内联顺序必须是 `数据 → 依赖数据的模块 → 主应用`，并且把顺序写进打包脚本的注释里。

**防御**：给自检脚本加一条「关键数据是否真的内联进来了」的检查，别只看外部引用数：

```python
# 漏内联会让整块功能空白，但「自包含」检查仍会通过
has_map   = 'window.MAP_CHINA' in s
has_data  = 'window.GATEWAYS' in s and 'window.SPOTS' in s
has_ui    = 'mapSel' in s and 'mapCallout' in s      # 页面结构里该有的锚点
ok = (n_asset == 0 and not external and n_link == 0
      and has_map and has_data and has_ui)           # ← 这几项和外部引用同等重要
```

同时**改完必须对交付物本身再跑一遍功能回归**，不能只跑构建源：
`node tools/map-test.js 单文件版.html`。内联顺序、base64 体积这类问题只有在单文件里才暴露。

### 4. 惰性加载的图被误判为坏图

未进视口的 `<img data-src="...">` 在 Chrome 里 `complete === true && naturalWidth === 0`。
统计/降级前**先滚动触发加载**，并过滤出真正有 `src` 的元素。否则你会误判「图片全坏了」而白折腾一轮。

### 5. `[hidden]` 被 CSS 覆盖

补上：

```css
[hidden]{ display: none !important }
```

打包时若把弹层样式一并内联，`display:grid/flex` 会盖掉 UA 的 `[hidden]`，导致弹层全程遮挡页面并拦截点击。

### 6. Windows 上 `/tmp` 是 `C:\tmp`

`PIL.Image.save('/tmp/x.png')` → `OSError: [Errno 22] Invalid argument`（目录不存在且无权限）。
改用 `io.BytesIO()` 或项目内 `build/` 目录。

### 7. `assets/img/` 的残留计数是假警报

`img()` 里保留的 `'assets/img/' + f` 兜底分支会被正则扫到，但那是死代码。
核查脚本要排除带 `${` 的模板字面量与字符串拼接，只看**静态标签属性**。

---

## 交付时要讲清的三件事

1. **单文件版 vs 多文件版的差别只有「存放方式」**——默认内联原图时画质逐像素一致，主动说明这一点，别让用户猜「是不是被压过了」。
2. **体积代价要报实数**：直接给「34.2 MB 原图 → 45.80 MB 单文件」这样的换算，并说明 base64 就是会膨胀 1/3。
3. **体积超标时的降级路径**：按「先砍数量 → 再降质量 → 换交付通道（发布为应用 / 静态托管）」的顺序给出可执行选项，别只丢一句「太大了」。

把这三点写进 README 的对应章节（含构建命令、体积对照表），下次不用重新推理。

---

## 配套脚本

| 脚本 | 作用 |
| --- | --- |
| `tools/selfcheck.py` | 核查自包含性：外部引用 / 外链 CSS / 相对路径残留 + **关键全局是否真的内联进来了** |
| `tools/shrink_images.py` | 【可选】分层压缩图片为 WebP，打印体积报告（仅在体积超标时用） |
| `tools/pack_html.py` | 通用打包器：内联本地 CSS / JS / 静态图片 |
| `tools/make_inline_map.py` | 生成 `{相对路径: dataURI}` 映射表，供 JS 动态路径查表 |

## 实战记录

- `travel-guide`「山海图鉴」：59 条线路 / 233 张图（34.2 MB 原图）→ 单文件版 **45.80 MB，内联 233 张 JPG 原图（不压缩）**。file:// 直开验证：加载 1.98s / 59 卡片 / 23 五星横轨 / 图片 **97/97 全部加载** / 占位块 0 / 抽屉画廊 3/3 / console error `[]` / 网络失败 `[]`。
  构建：`node tools/build-standalone.js`（`--source=orig`）→ `python tools/selfcheck.py`。
  **教训**：初版默认做了「118 张 WebP / 7.5MB」的压缩包，用户随即要求「不要压缩图片，用原图片」——白做一轮，且画质本可无损。**默认内联原图。**
- 同上项目、次日加「景点地图」：内联清单从「CSS + JS + 图片」扩到 **9 个 JS + 302 KB 离线矢量底图 + 60 城交通数据 + 295 条景点数据**，单文件 45.80 → **46.22 MB**。
  **教训**：`js/map.js` 是 IIFE，加载那一刻就读 `window.MAP_CHINA / SPOTS / GATEWAYS`。第一次内联时数据排在了模块后面，地图整块空白，但**自包含检查一路全绿**——因为确实没有外部依赖，只是顺序错了。
  修法：内联顺序固定为 `数据 → 依赖数据的模块 → 主应用`，并给 `selfcheck.py` 加上 `has_map / has_data / has_ui` 三项存在性检查（见坑 #3）。
  **通用化**：凡有「加载时就把全局数据读进闭包」的模块（地图 / 图表 / 图谱 / 看板 / 编辑器），都按这条处理；换完内联清单**必须对单文件版本身再跑一遍功能回归**，只跑构建源发现不了这类问题。
