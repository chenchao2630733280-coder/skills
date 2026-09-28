---
name: html-single-file-pack
description: 把多文件静态站点（HTML + CSS + JS + 本地图片）打包成一个自包含单文件 HTML——CSS/JS/图片全部内联，零外部依赖，双击即开、云端上传不丢图。当出现「上传到资料库/云文档/网盘后图片全裂」「发给别人打开是空白」「需要离线单文件交付」时调用。含图片分层压缩预算、img 双源兼容改造、加载失败降级占位、自包含性核查，以及 String.replace 的 $$ 转义陷阱等必踩坑。
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
| JS 里**动态拼**的图片路径 | 改 `img()` 解析函数（见第 3 步）——**这一步最容易被漏掉** |

> **关键判断**：如果图片路径是 JS 在运行时拼出来的（如 `'assets/img/' + f`），那么静态扫描查不到，必须改代码。绝大多数数据驱动站点都属此类。

### 1. 图片压缩：先定体积预算

base64 会让体积**膨胀约 37%**（3 字节 → 4 字符）。云端上传有体积上限，所以图片必须先瘦身。

分层策略（按用途分配像素与质量）：

| 用途 | 宽度 | 质量 | 说明 |
| --- | --- | --- | --- |
| 封面 / 首屏大图 / 卡片 | ≤1080px | q71 | 1080 已能覆盖多数屏幕 |
| 详情页内图 / 缩略 | ≤800px | q66 | 小图上更激进地压 |
| 图标 / 占位 | 保持原样 | — | 本身很小，可不处理 |

若单文件目标 ≤8MB 仍超标，**优先砍数量而非砍质量**——每张图从「全部保留」降到「封面 1 张 + 内容 1 张」，体积直接腰斩，视觉损失远小于全局降质。

用 `tools/shrink_images.py` 一条命令跑完并打印体积报告：

```bash
python tools/shrink_images.py <图片目录> <输出目录> --tiers cover=1080,71 detail=800,66
```

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

### 3. 惰性加载的图被误判为坏图

未进视口的 `<img data-src="...">` 在 Chrome 里 `complete === true && naturalWidth === 0`。
统计/降级前**先滚动触发加载**，并过滤出真正有 `src` 的元素。否则你会误判「图片全坏了」而白折腾一轮。

### 4. `[hidden]` 被 CSS 覆盖

补上：

```css
[hidden]{ display: none !important }
```

打包时若把弹层样式一并内联，`display:grid/flex` 会盖掉 UA 的 `[hidden]`，导致弹层全程遮挡页面并拦截点击。

### 5. Windows 上 `/tmp` 是 `C:\tmp`

`PIL.Image.save('/tmp/x.png')` → `OSError: [Errno 22] Invalid argument`（目录不存在且无权限）。
改用 `io.BytesIO()` 或项目内 `build/` 目录。

### 6. `assets/img/` 的残留计数是假警报

`img()` 里保留的 `'assets/img/' + f` 兜底分支会被正则扫到，但那是死代码。
核查脚本要排除带 `${` 的模板字面量与字符串拼接，只看**静态标签属性**。

---

## 交付时要讲清的两件事

1. **体积与数量的取舍**：明确告诉用户单文件版少了几张图、为什么。例如「为控制上传体积，配图从 233 张降到 118 张（每条 1 封面 + 1 实景），压成 WebP」。
2. **想要全量图的替代路径**：如果用户不接受砍图，指向「发布为应用」或静态托管——它们支持多文件目录，会完整带上 `assets/`。

把这两点写进 README 的对应章节（含构建命令、体积对照表），下次不用重新推理。

---

## 配套脚本

| 脚本 | 作用 |
| --- | --- |
| `tools/selfcheck.py` | 核查自包含性：外部引用 / 外链 CSS / 相对路径残留 |
| `tools/shrink_images.py` | 分层压缩图片为 WebP，打印体积报告 |
| `tools/pack_html.py` | 通用打包器：内联本地 CSS / JS / 静态图片 |
| `tools/make_inline_map.py` | 生成 `{相对路径: dataURI}` 映射表，供 JS 动态路径查表 |

## 实战记录

- `travel-guide`「山海图鉴」：59 条线路 / 233 张图（35MB 目录）→ 单文件版 118 张 / **7.52MB**，隔离目录验证 59 卡片 / 0 占位 / 0 console error / 2.7s 加载。构建链：`pack-webp.py` → `build-standalone.js` → `selfcheck.py`。
