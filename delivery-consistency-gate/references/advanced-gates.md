# I~K 三类进阶门禁 · 落地写法

> 适用场景：**多端原型 / 多端应用** —— 有客户端 JS 动态渲染、有导航分类结构、有业务编号体系。
> A~H 见 `gate-catalog.md`；本文件只写 I / J / K。

---

## I 渲染真值验证

### I-1 无浏览器 DOM 桩

**动机**：页面把导航/数据/标注**动态渲染**出来时，源码里没有可比对的字面量；而源码里的**注释/死代码**会让「全文搜」误报。

**做法**：给页面 JS 一个最小桩 DOM → 真跑渲染函数 → 抓渲染产物（HTML 字符串或 DOM）→ 在产物上断言。

```js
// _dom_stub.js（骨架）
// 1) 最小 DOM：只需 renderSidebar 用到的 API
function makeEl(tag) {
  const el = {
    tagName: tag, children: [], _attrs: {}, _text: '', classList: { add(){}, remove(){} },
    setAttribute(k, v) { this._attrs[k] = v; },
    getAttribute(k) { return null; },          // 桩刻意返 null：属性断言请用 raw()
    appendChild(c) { this.children.push(c); return c; },
    get innerHTML() { return render(this); },
    set innerHTML(v) { this._raw = v; },
  };
  return el;
}
// 2) 给全局挂最小 document，然后 require/side eval 页面脚本
// 3) 真跑：const html = window.renderSidebar('portal', 'P46');  ← 跑渲染函数
// 4) 在 html 上解析断言（parseGroups 等），别去搜源码文本
```

**关键纪律**：
- **真跑渲染函数、解析产物**，绝不 `grep` 源码字面量来当渲染结果。
- 桩里一切「属性 / 存在性」断言改用 `raw()`（源码文本）核对 —— 因为 `getAttribute` 在桩里恒 null。
- 桩**判不了样式与几何**，那类断言一律交真实浏览器（见 I-2）。

### I-2 真实浏览器几何探针

**动机**：布局缺陷（遮挡、溢出、被裁剪）**读 CSS 猜不出来**，必须真跑浏览器量几何。

```js
// _ui_*_check.js（骨架，Playwright）
const box = await el.boundingBox();
const cx = box.x + box.width / 2, cy = box.y + box.height / 2;

// 先排除两种「正常」的 null：
const vp = page.viewportSize();
const inViewport = cy >= 0 && cy <= vp.height && cx >= 0 && cx <= vp.width;

const topEl = await page.evaluate(
  ([x, y]) => { const e = document.elementFromPoint(x, y); return e ? (e.id || e.className) : null; },
  [cx, cy]
);
// 判据：inViewport 且 topEl 非自身/非后代 ⇒ 被遮挡
```

**排除误报（必做）**：
1. **中心点越出视口** ⇒ `elementFromPoint` 返回 null，是正常的（行顶到视口底部时常见）。
2. **被祖先 `overflow: auto|scroll|hidden` 裁剪** ⇒ 也是正常的。
   只有「在视口内、既不被裁剪、`elementFromPoint` 又不是自己」才算真遮挡。

### I-3 常见根因库（布局）

| 症状 | 根因 | 修法 |
|---|---|---|
| 宽表把容器顶宽、`overflow-x:auto` 失效 | flex 子项默认 `min-width:auto`，不会收缩到内容宽度以下 | 给该 flex 子项加 `min-width: 0` |
| 卡片与后续卡片紧贴 | 共享容器只设了 `gap`（行内间距），漏了 `margin-bottom`（块间距） | 补 `margin-bottom`，别只靠 `gap` |

### I-4 探针判据三忌

1. 用 `textContent` 判**带标签的标记**（如 `>可下发<`）⇒ 应查 `innerHTML`；且「不可下发」含「可下发」子串，须先判否定。
2. 用**整行/整单元格文本**做子串判定 ⇒ 提示文案本身可能含关键词（按 `onclick` 的函数名判更稳）。
3. 日期与紧跟的 tag **文本串接**（`2026-09-24` + `5 天后到期` ⇒ `...245 天后到期`）⇒ 取各自元素而非单元格文本。

### I-5 运行纪律

- **逐条跑、显式长超时**（单条 60~200s）；`for` 循环批量跑会被默认超时 SIGTERM 掉（无输出 + 退出码 1），**别误判为断言失败**。
- 本地静态服务器**后台任务方式启动**（子 shell `&` 会被杀 ⇒ `ERR_CONNECTION_REFUSED`）；跑完停服。
- `locator().click()` 无匹配报 **TimeoutError**（不是 None 静默）。

---

## J 导航 / 分类三方一致性

**三方副本**：`侧栏分类定义` ↔ `各页面面包屑` ↔ `说明文档的菜单树`。权威源 = 侧栏定义。

```js
// 结构：分类 → [页面id]
// 1) 侧栏：真跑 renderSidebar → parseGroups(html)  → 不是解析源码
// 2) 面包屑：逐页取 crumbs，按分隔符数量判层级
// 3) 文档菜单树：解析文档对应段
// 判据：三个结构的 (分类, 页面id) 集合，双向差集都要为空
```

**要点**：
- **按字段值比对，不全文搜**：断言「某分类名已清零」时，**提取标题字段逐个比对**；分组**注释**里可能刻意保留该词，全文搜会误报。
- **层级按分隔符数量判**：面包屑第三级可能是**表达式**而非字面量，正则捕获不到 ⇒ 用「顶层逗号数」判级，不是数文本段数。
- **多角色逐角色比**：同一套侧栏在不同角色下分类可能不同（平台端 / 商家端 / 局办端…）；只覆盖一个角色是常见漏项。
- **菜单项 id ≠ 页面 id**：一个页面可对应多个菜单项（如多个入口同页），或一项对应多页 ⇒ 计数用常量 + 期望清单动态求值，别写死。
- 加**负向自检**：改一条分类 / 删一条菜单树条目，门禁必须报出。

---

## K 编号空间治理（引用 ↔ 登记双向）

**登记表** = 编号的权威清单（用例号 / 规则号 / 实体号 / 版本号…）。

```python
# 双向交叉
dangling = refs - regs     # 悬空引用：引用了不存在/未登记的编号 → 必须为空
orphans  = regs - refs     # 孤儿登记：登记了却无人引用       → 必须为空（易漏）

# 登记唯一性：同一编号不得重复登记
dups = [k for k, v in Counter(regs_list).items() if v > 1]  # 必须为空

# 区间连续性（可选）：编号区间内不得无故跳号
```

**四类问题与判据**：

| 问题 | 判据 | 说明 |
|---|---|---|
| 悬空引用 | `refs − regs` 非空 | 引用了不存在/未登记的编号 |
| **孤儿登记** | `regs − refs` 非空 | 登记的编号无人引用 —— **只做单向检查会漏掉它** |
| 重复占用 | 登记表内同号出现 ≥2 次 | 两处语义不同却共用一个号 |
| 空号 / 同前缀歧义 | 区间跳号；同一前缀被两个体系占用 | 需人工确认是否合法 |

> ⚠️ **最经典漏洞**：只查「悬空」（引用 → 登记），不查「孤儿」（登记 → 引用）。
> 一个登记的编号若从未被任何地方引用，单向检查永绿 —— 直到某天发现「声明数 ≠ 实际数」。
> **双向都要查**；改完**实跑**而非读旧报告（旧报告会被上一次的结果掩盖）。

### 维护建议

- 编号区间（如某前缀现役到多少）**以机器可读的登记表为准**，不在文档里复制数字。
- 新增编号前**先查重**（同号是否已被占用、该前缀现役区间到哪）。
- 文档里的「编号区间自述」（如「现役 V01~V17」）最容易腐烂 ⇒ 定期用脚本比对、现跑现取。
