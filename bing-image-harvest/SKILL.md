---
name: "bing-image-harvest"
description: 为网站/原型/图鉴类项目批量采集真实配图（无需 API Key、无需外网直连），并做质量筛检与人工抽查。当任务需要「给 N 个条目各配几张真实图片」「抓取配图并本地化」「配图有水印/防盗链/跑题需要替换」时调用。含必应图库检索解析、图库/水印站屏蔽、缩略图优先下载、Pillow 质检、拼版抽查、定点重采六步法。
agent_created: true
---

# Bing 图片采集与质检（无 API、可本地化）

在受限网络环境下（国内直连、无 Unsplash/Wikimedia 访问、无 API Key）为项目批量获取**真实、干净、不跑题**的配图。已被验证可在 100 秒内采集 59 条 × 4 张 = 236 张图。

## 何时使用

- 网站 / HTML 原型 / 图鉴 / 商品册需要「每个条目 2–4 张真实图片」
- 生成式配图不合适（要真实景观、实物、街景）
- 已有配图带水印、防盗链占位图、与主题不符，需要批量替换

## 前置条件

- Node.js ≥ 18（用内置 `fetch`，零依赖）
- Python + Pillow（质检与压缩）
- 网络：`cn.bing.com` 可达即可（`curl` 可能被沙箱拦，Node `fetch` 通常可用）

先做连通性探测，别直接跑全量：

```bash
node -e "fetch('https://cn.bing.com/images/search?q=test',{headers:{'User-Agent':'Mozilla/5.0'}}).then(r=>console.log(r.status))"
```

## 六步法

### 1. 准备检索词表

建 `queries.json`，**每个条目至少给中文 + 英文两条检索词**：

```json
{ "entry-id": { "zh": "稻城亚丁 三神山 秋色", "en": "Daocheng Yading three sacred mountains autumn" } }
```

英文检索词极其重要：中文检索会大量命中图库站（昵图网 / 699pic / 摄图网），英文检索会命中 Wikimedia / Flickr / 官方媒体 / 旅行博客，源干净得多。

检索词要带**具体景物**而不是泛指（`九寨沟 五花海 彩林` 优于 `九寨沟风景`），并追加 `imagesize-large` 过滤参数。

### 2. 检索并解析结果

```js
const url = `https://cn.bing.com/images/search?q=${encodeURIComponent(q)}`
  + `&qft=%2Bfilterui%3Aimagesize-large&form=IRFLTR&first=1`;
const html = await (await fetch(url, { headers: { 'User-Agent': UA } })).text();

// 原图地址（用于判断来源站点）
const murls = [...html.matchAll(/murl&quot;:&quot;(.*?)&quot;/g)].map(m => m[1]);
// 必应缩略图 id（用于真正下载）
const oips = [...new Set([...html.matchAll(/OIP\.[A-Za-z0-9_-]{10,}/g)].map(m => m[0]))];
```

`first=1 / 36 / 71…` 翻页可拿到更多候选。

> 注意：`murl` 与 `OIP` 是按页面顺序一一对应的，按索引 zip 即可。

### 3. 关键决策：下载走必应缩略图，不走原图

**这是整套流程最重要的一条经验。**

- 原图下载 = 直连源站 → 大量防盗链占位图（昵图网返回一张 28KB 的广告图）、403、超时。
- 必应缩略图 = `tse{1..4}.mm.bing.net/th?id={OIP}&w=1500&h=1000&c=7&rs=1&p=0` → 必应 CDN 代理，**永远可达、格式统一、无水印注入**，1500px 宽约 100–200KB，网页用足够。

```js
async function grabThumb(oip) {
  for (const host of [1,2,3,4]) {
    try {
      const r = await fetch(`https://tse${host}.mm.bing.net/th?id=${oip}&w=1500&h=1000&c=7&rs=1&p=0`,
        { headers: { 'User-Agent': UA, Referer: 'https://cn.bing.com/' }, signal: AbortSignal.timeout(22000) });
      const b = Buffer.from(await r.arrayBuffer());
      if (b.length > 40000 && b[0] === 0xff && b[1] === 0xd8) return b;  // JPEG 魔数校验
    } catch {}
  }
  return null;
}
```

失败时再回退原图（且原图需过黑名单）。

### 4. 来源站点分级

按 `murl` 的域名给候选**打分排序**，同域名最多贡献 2 张（保证图片多样性）：

- **0 分（优先）** — wikimedia / flickr / unsplash / nationalgeographic / lonelyplanet / tripadvisor / gov.cn / 官方媒体 / 旅行博客
- **1 分** — 其他未知站点
- **3 分（屏蔽）** — 昵图网 nipic、699pic、redocn、616pic、huitu、huaban、zcool、58pic、veer、chuangkit、alamy、gettyimages、freepik、shutterstock、dreamstime、tuchong、500px、pconline…

> 黑名单只影响 `murl` 的排序，不影响下载通道（下载永远走必应缩略图）。这样既避开图库站内容，又不受防盗链影响。

### 5. Pillow 质检 + 压缩

`tools/qc.py`：剔除异常图并统一压缩。判据：

- 尺寸 `w < 480` 或 `h < 320`、宽高比 > 2.4 或 < 0.35 → 丢弃
- 缩到 64px 灰度后 **标准差 < 18** → 纯色/占位图，丢弃
- **FIND_EDGES 均值 < 3.0** → 糊图，丢弃
- 宽度 > 1500px → 等比缩到 1500，重存 JPEG `quality=82, optimize, progressive`

### 6. 拼版人工抽查 + 定点重采

**必做**。自动化筛不掉文字海报、跑题图、AI 合成图，只能靠眼睛。用 `tools/mksheet.py` 把图按 5 列拼成若干张大图，一次看 25 张，成本极低。

抽查时对照文件名映射（脚本会打印行列 → 文件名），把问题图记成清单，然后**按条目整体重采**：

1. 在 `overrides.json` 里为该条目写更精确的检索词
2. 删掉该条目的 `/^<id>-\d+\.jpg$/` 文件
3. 只重跑这些条目（`ONLY=id1,id2`）

常见问题与对策：

| 症状 | 对策 |
| --- | --- |
| 文字海报 / 路线清单截图 | 换更具体的景物词 |
| 带水印（暖图/光厂/智游） | 加黑名单域 + 换英文词 |
| 旅游社广告图、越野车广告 | 避开 `自驾` `俱乐部` `包车` 类词 |
| 主题跑题（如甘南搜出喀斯特峰林） | 词里加行政区+地貌（`Gannan grassland monastery`） |
| AI 合成 / 抠图合成图 | 换英文词，一般能避开 |
| 古画扫描件（`<地名>山图卷`） | 词里加 `photo` `scenery` |
| 必应反复返回同一张问题图 | 直接删掉，条目少一张不影响；或叠加 `overrides` 重试一次后放弃 |

**不要为了凑满张数无限重试。** 每条 3–4 张，删掉 1 张可接受。

## 并行与限流

- 并发 5–6 条线路 / 秒级间隔，59 条约 100 秒
- 每条线路内候选之间 `sleep(100~150ms)`
- 检索失败重试 3 次，`first` 参数换页兜底
- **不要 `run_in_background`**：后台任务可能拿不到网络权限而静默产出 0 张。前台跑并重定向日志：

```bash
ONLY=id1,id2 PER_TRIP=4 CONCURRENCY=6 node tools/harvest.js > tools/fetch.log 2>&1; tail -20 tools/fetch.log
```

## 收尾

采集完生成图片索引供前端使用（`fetch()` 在 `file://` 下会被 CORS 拦，所以要落成 JS）：

```js
// assets/img/manifest.json -> data/images.js
window.IMAGES = { "entry-id": ["entry-id-1.jpg", "entry-id-2.jpg"] };
```

页面里用 `loading="lazy"` + IntersectionObserver 惰性加载，避免一次性拉 200 张图。

## 附：脚本

- `tools/harvest.js` — 采集器（`queries.json` + `overrides.json` + 环境变量）
- `tools/qc.py` — 质检压缩 + 拼版图
- `tools/mksheet.py` — 指定条目生成对照拼版图

## 常见坑

1. **变量被误删**：大段替换函数时容易把辅助函数（如 `hostOf`）删掉，报 `X is not defined`。改完先跑单条目 smoke test。
2. **JSON 重复键**：往 JSON 顶部插新键时若原键还在，`JSON.parse` 取后者，覆盖不生效且不报错。改完 `Object.keys()` 数一下。
3. **`/tmp` 在 Windows Node 里是 `C:\tmp`**：可能不存在导致 ENOENT。用项目内 `tools/` 目录当临时目录。
4. **检查图是否加载**：未进入视口的懒加载 `img`（只有 `data-src` 没有 `src`）在 `complete===true` 且 `naturalWidth===0`，会被误判为「坏图」。统计前先滚动一遍并过滤 `getAttribute('src')`。
5. **`[hidden]` 被覆盖**：若 CSS 给弹层写了 `display:grid/flex`，会盖掉 `[hidden]` 的 `display:none`。必须加 `[hidden]{display:none !important}`，否则弹层始终遮挡页面并拦截点击。
