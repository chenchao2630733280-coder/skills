# Three.js 引擎模板（Web H5 真 3D）

> 供 `game-code-forge` 在引擎字段为 `Three.js` 时读取
> 平台：Web H5 · 栈：TypeScript + Vite + Three.js · 产物：`dist/index.html`
> 对应质量检查：`../game-quality-gate/references/engine-checks-three.md`

---

## 1. 何时选 Three.js

| 游戏特征 | 判断 |
|---|---|
| 真 3D 透视（纵深收窄、俯角镜头） | ✅ 首选 |
| 数百~数千同模单位（人群、弹幕、粒子） | ✅ `InstancedMesh` |
| 曲线路径 / 管道 / 轨道运动 | ✅ `CatmullRomCurve3` |
| 纯代码程序化美术、不依赖外部模型 | ✅ 几何 + 材质即可 |
| 需要浏览器直开自测、离线可跑 | ✅ 无编辑器依赖 |
| 需导出 exe / 原生包 | ❌ 改选 Godot 4 |
| 纯 2D 无纵深 | ❌ 改选 Phaser 3 / Pixi.js |

---

## 2. 工程骨架

```
package.json          three, vite, typescript
tsconfig.json         strict: true
vite.config.ts        base: './'（保证 dist 可离线直开）
index.html
src/
├─ main.ts            启动：Scene3D → 状态机 → 主循环
├─ core/
│   ├─ GameLoop.ts    固定步长 tick（判定）+ 插值渲染
│   ├─ StateMachine.ts
│   ├─ EventBus.ts
│   └─ Config.ts      数值、颜色规则、渲染上限集中管理
├─ render/
│   ├─ Scene3D.ts     Scene / PerspectiveCamera / WebGLRenderer 单例
│   ├─ CameraRig.ts   跟随、微震、Safe Area 适配
│   ├─ InstancedCrowd.ts
│   └─ Materials.ts   程序化几何与材质
├─ sim/
│   ├─ UnitPool.ts    单位 = 数据结构，非 Object3D
│   ├─ CrowdFormation.ts
│   └─ CombatResolver.ts
├─ entities/          Gate / Tower / Pipe / Launcher / Hazard
├─ levels/            LevelDef[] / LevelLoader / LevelSim
├─ feedback/          FloatingNumber / Particles / ScreenShake / AudioBus
├─ ui/                DOM 叠层（HUD 用 HTML，不用 3D 文字）
└─ input/             DragToLane.ts（Raycaster → lane）
```

---

## 3. 判定契约（最高优先级）

**所有实体位置与判定一律使用赛道局部坐标 `(lane, z)`，禁止用屏幕像素。**

```
输入：Raycaster 从相机射向 y=0 地面平面 → 交点 → lane 参数
判定：固定步长 tick 内，比较 unit.z 与 gate.z / tower.z，比较 unit.lane 与左右门范围
渲染：把 (lane, z) 映射到 3D 世界坐标，只做插值，不回写状态
```

| 反模式 | 后果 | 正确做法 |
|---|---|---|
| `clientX` 直接当 lane | 3D 透视下横向位移非线性，拖拽失准 | 射线投射求交点 |
| 渲染帧里改人数 / HP | 判定与视觉不同步、帧率影响结果 | 只在 tick 内改状态 |
| 每单位一个 Mesh | 600+ 单位直接掉帧 | `InstancedMesh` + 对象池 |
| 逻辑人数 = 渲染人数 | `×80` 后爆显存 | 逻辑整数独立，视觉封顶 600，>999 用 K 显示 |

---

## 4. 关键代码骨架

```ts
// Scene3D.ts —— 单例，禁止重复创建
export class Scene3D {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
  readonly renderer: THREE.WebGLRenderer;
  constructor(canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  }
  resize(w: number, h: number) {
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }
}

// InstancedCrowd.ts —— 逻辑数量与渲染数量解耦
const MAX_VISIBLE = 600;
class InstancedCrowd {
  private mesh: THREE.InstancedMesh;
  private dummy = new THREE.Object3D();
  sync(units: readonly Unit[], logicalCount: number) {
    const n = Math.min(units.length, MAX_VISIBLE, logicalCount);
    this.mesh.count = n;
    for (let i = 0; i < n; i++) {
      const u = units[i];
      this.dummy.position.set(u.lane * LANE_W, 0, u.z);
      this.dummy.updateMatrix();
      this.mesh.setMatrixAt(i, this.dummy.matrix);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}

// Pipe.ts —— 曲线插值，单位各自持有进度 t
const curve = new THREE.CatmullRomCurve3(points);
unit.t += speed * dt / curve.getLength();
const p = curve.getPointAt(Math.min(unit.t, 1));
```

---

## 5. 与流水线其它阶段的接口

| 上游 | 读取内容 |
|---|---|
| `docs/GAME_BLUEPRINT.md` | 引擎字段 = `Three.js`、设计分辨率、适配模式 |
| `docs/TECH_DESIGN.md` | 目录结构、模块契约、`(lane,z)` 定义 |
| `docs/ASSET_MANIFEST.json` | 程序化几何/材质/配色 token 登记（可无位图） |

**输出**：`src/**/*.ts`、`index.html`、`package.json`、`tsconfig.json`、`vite.config.ts`、`dist/`。

---

## 6. 常见坑

1. **WebGL 上下文重复创建**：热更新/重开关卡时再 new 一次 Renderer → 上下文丢失。用单例 + `dispose()`。
2. **`setSize` 撑爆布局**：第三参数必须 `false`，否则 canvas 内联样式覆盖 CSS 适配。
3. **`getPoint` vs `getPointAt`**：前者按参数非等速，管道内单位会忽快忽慢 → 用 `getPointAt`。
4. **实例矩阵未标脏**：改完 `setMatrixAt` 忘记 `instanceMatrix.needsUpdate = true` → 画面静止。
5. **中文文字用 3D 网格**：字体加载重且易 404 → HUD/数字门用 HTML/CSS 叠层，按 `project()` 只做定位不做判定。
6. **Vite base 缺省**：`dist/index.html` 直接双击打开会因绝对路径 404 → `base: './'`。
7. **像素比不设上限**：高分屏 `devicePixelRatio=3` 直接三倍填充率 → `Math.min(dpr, 2)`。

---

## 7. 构建与自测

```
npm install
npm run typecheck      # Gate 3 / 3.15
npm ls                 # Gate 3 / 3.18
npm run build          # Gate 3 / 3.19 → dist/index.html
浏览器打开 dist/index.html  # Gate 3 / 3.20（完整实跑由 game-integrate Gate 4 负责）
```
