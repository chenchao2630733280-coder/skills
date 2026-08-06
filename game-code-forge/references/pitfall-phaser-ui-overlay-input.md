# Phaser UI 交互 / 层级踩坑（Web 三引擎通用）

> 来自《废品拆解王》实战迭代。以下坑在"用代码搭建 UI 弹窗 / 长按 / 拖拽"时高频复发，生成 Phaser 工程时默认知晓。

---

## 1. 自定义容器 `add.existing` 自动挂场景根 → 被高 depth 蒙层遮挡（最高频）

**现象**：长按/点击后屏幕仍被半透明蒙层盖住，看不到"确认弹窗"或点不到按钮；或按钮"点了没反应"。

**根因**：`Panel` / `RustButton` 这一类**自定义 `Container`**，构造函数末尾通常有一句 `scene.add.existing(this)`，会把实例默认挂到 **scene 根显示列表（depth 0）**。如果你创建弹窗时只写了 `popup.add(panel)` 但**漏了把 `panel` 显式挂进目标容器**，或者反过来——`panel` 被 `add.existing` 留在 scene 根，而它的父 `popup` 是某个 depth=70 容器的子节点——`panel` 就停在了 depth 0，**被任何更高 depth 的全屏 backdrop（0x000000/0.9 的矩形蒙层）完全盖住**。表现就是"只有蒙层、没有弹窗"。

**修法（规范做法）**：
- 凡是 `new Panel(...)` / `new RustButton(...)` 这种"构造即 `add.existing` 到 scene"的自定义容器，**必须显式 `targetContainer.add(panel/btn)`**，让它成为目标容器的子节点、跟随父容器 depth。
- 审查任何弹窗时，**优先 grep 是否漏了 `xxx.add(panel)` / `xxx.add(btn)`**——这是最容易被忽略的一步。
- 兜底：可临时 `setDepth(999)`，但规范仍是显式挂父容器（否则 layout 坐标、命中区仍按 scene 根计算，易错位）。

---

## 2. `setInteractive` 必须用配置对象形式

**错误**（第三参类型不匹配，TS 报错或手势不生效）：
```typescript
obj.setInteractive(new Phaser.Geom.Rectangle(...), Phaser.Geom.Rectangle.Contains, { useHandCursor: true });
```

**正确**（统一用配置对象）：
```typescript
obj.setInteractive({
  hitArea: new Phaser.Geom.Rectangle(-w/2, -h/2, w, h),
  hitAreaCallback: Phaser.Geom.Rectangle.Contains,
  useHandCursor: true
});
```
> 要点：`useHandCursor` 是配置项，**不能**当第三个位置参数传；命中区默认按对象左上角原点，自定义 Container 需要自己给 `setSize` + 以中心为负半宽高的 `Rectangle`。

---

## 3. 长按实现：用定时器 + `done` 防重入，禁止 `pointerout` 取消

**现象**：长按"卡住"、进度环画不满、永远触发不了拆解。

**根因**：在 `pointerout` 里取消长按进度 → 手指/鼠标在长按期间只要**轻微离开命中区**（微抖、亚像素移动）就重置，560ms 永远凑不满。

**修法**：
```typescript
let holding = false, done = false;
let holdTimer: Phaser.Time.TimerEvent | undefined;
const startHold = () => {
  if (holding || done) return;
  holding = true;
  holdTimer = scene.time.delayedCall(560, finishHold);   // 定时器触发，不依赖 tween onComplete
};
const cancelHold = () => {           // 仅提前松手才取消
  if (done) return;
  holding = false;
  holdTimer?.remove(false);
};
const finishHold = () => {
  if (done) return;
  done = true; holding = false;       // done 防重复触发
  doDismantle(...);                   // 拆解逻辑同步执行
};
img.on('pointerdown', startHold);
img.on('pointerup', cancelHold);
// 不要绑 pointerout 取消
```
- **拆解结果逻辑放 `finishHold` 同步执行**，不要挂在"抖动 tween 的 `onComplete`"里——那个回调在嵌套 tween/子对象交互组合下偶发不触发，会被静默吞掉（表现成"长按完成却没弹窗"）。
- 若担心异常被吞，用 `try/catch` 在屏幕顶部 `showToast` 红字提示，而不是无反应。

---

## 4. 全局 `drag` handler 区分对象：用 `setData('dragMode', ...)`

**现象**：拖零件进合成台时，把底部"配方条"或其他 UI 也一起拖飞、纵向乱窜。

**根因**：全局 `this.input.on('drag', ...)` 会让**所有**可拖对象都跟随指针坐标，包括只想横滑的容器。

**修法**：
- 需要跟随指针自由拖的对象：`obj.setData('dragMode', 'free')` 并 `this.input.setDraggable(obj)`。
- 只想横滑的容器：`obj.setData('dragMode', 'h')`，其横滑由自身 `drag` handler 只改 `layer.x`。
- 全局 `drag` 回调开头：`const mode = obj.getData('dragMode'); if (mode === 'h') return;` —— 仅 `'free'` 跟随坐标。

---

## 5. TS 局部变量不能用 `?` 可选修饰符

**错误**：`let tween?: Phaser.Tweens.Tween;`（编译 TS1005/1134）。
**正确**：`let tween: Phaser.Tweens.Tween | undefined;`

> 可选修饰符 `?` 只用于**对象属性 / 接口字段**，不能用于 `let`/`const` 局部变量。

---

## 6. 缺 favicon 导致无害 404（非游戏 bug，但控制台会报）

浏览器每次打开页面自动请求 `/favicon.ico`，项目未提供则控制台报 `Failed to load resource: 404`。与游戏逻辑无关。
**修法**：在 `index.html` 的 `<head>` 加 `<link rel="icon" href="data:," />`，浏览器改用内联空图标、不再请求该文件。先核对 `AssetManifest` 清单资源是否真有 404（抽样 curl 各 `path` 是否 200），排除误判。

---

## 7. 默认 hitArea 原点陷阱 → 按钮"只有右下 1/4 可点"（最高频隐性坑）

**现象**：按钮 `setInteractive()` 后，必须点在按钮**右下角一小块区域**才能触发，其余区域点击无反应。DevTools 看不出异常，纯靠肉眼发现"点不到"。

**根因**：`setInteractive()` 不传参时，Phaser 用对象**包围盒左上角为原点**生成默认 `Rectangle(0, 0, W, H)`。但自定义 `Container` / `Image` 的子节点通常**以中心 (0.5, 0.5) 为原点布局**（子节点 x/y 是相对中心的偏移）。于是默认命中区落在中心点右下象限——与玩家看到的按钮视觉范围**错位**，只有右下 1/4 命中区与视觉重叠，表现为"只有右下能点"。

**修法（强制规范）**：所有交互元素**显式传中心负半宽高的 hitArea**，不要依赖默认：
```typescript
obj.setSize(W, H);                         // 让 setInteractive 知道尺寸
obj.setInteractive({
  hitArea: new Phaser.Geom.Rectangle(-W/2, -H/2, W, H),  // 以中心为原点
  hitAreaCallback: Phaser.Geom.Rectangle.Contains,
  useHandCursor: true
});
```

**可复用 mkBtn 模板**（含按下缩放反馈，消除"点了没反应"的感知歧义）：
```typescript
function mkBtn(scene, x, y, w, h, label, onClick) {
  const bg = scene.add.rectangle(0, 0, w, h, 0x2a6df4, 1).setStrokeStyle(2, 0xffffff);
  const txt = scene.add.text(0, 0, label, { fontSize: '28px', color: '#ffffff' }).setOrigin(0.5);
  const btn = scene.add.container(x, y, [bg, txt]);
  btn.setSize(w, h);
  btn.setInteractive({
    hitArea: new Phaser.Geom.Rectangle(-w/2, -h/2, w, h),
    hitAreaCallback: Phaser.Geom.Rectangle.Contains,
    useHandCursor: true
  });
  btn.on('pointerdown', () => btn.setScale(0.92));
  btn.on('pointerup',   () => { btn.setScale(1); onClick(); });
  btn.on('pointerout',  () => btn.setScale(1));   // 防止卡在按下态
  return btn;
}
```
> 要点：`pointerdown` 缩小 + `pointerup` 还原的缩放反馈，比只用 `useHandCursor` 更直观，玩家能明确感知"按钮被激活"。`pointerout` 必须还原 scale，否则移出后按钮卡在缩态。
