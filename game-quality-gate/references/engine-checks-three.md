# Gate 3 引擎特定检查：Three.js

> 对应 `game-quality-gate` SKILL.md §6.3（L2）/ §6.4（L3）表格登记
> 新增引擎时只需新建 `references/engine-checks-{engine}.md` 并在此处登记,SKILL.md 不动。
> 编号段：L2 = 3.21~3.26，L3 = 3.15 / 3.19 / 3.20（3.18 为通用依赖检查）

---

## L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.21 | Loader 路径 ↔ manifest | `TextureLoader` / `FileLoader` / `GLTFLoader` 引用的每个路径都能在 `ASSET_MANIFEST.json` 找到对应 asset；程序化几何不产生外部请求 | `G3-THREE-LOADER-PATH` | ERROR |
| 3.22 | InstancedMesh 契约 | `InstancedCrowd` 的 geometry / material key 与 manifest 程序化资源登记一致；`instanceMatrix` 每帧上传数量 ≤ 渲染上限；逻辑数量与渲染数量解耦 | `G3-THREE-INSTANCE-CONTRACT` | ERROR |
| 3.23 | Renderer 单例 | `WebGLRenderer` 全局仅创建 1 次；`Scene` / `PerspectiveCamera` 由 `Scene3D` 统一管理；仅 1 条 `requestAnimationFrame` 主循环 | `G3-THREE-RENDERER-SINGLETON` | ERROR |
| 3.24 | 曲线路径 ↔ 关卡数据 | `Pipe` 的 `CatmullRomCurve3` 控制点与关卡配置 `pipes[].control` 一致；入口/出口坐标与 `from` / `to` 一致；单位按独立 `t` 进度插值 | `G3-THREE-CURVE-MISMATCH` | ERROR |
| 3.25 | 判定坐标契约 | 门 / 塔 / 机关判定只读取赛道局部坐标 `(lane, z)`；`clientX` / `screen` / `camera.project()` 结果不得参与数值判定 | `G3-THREE-SCREEN-COORD-JUDGE` | ERROR |
| 3.26 | 固定步长与插值 | 判定只在固定步长 tick 内发生，渲染帧只做插值；无「渲染帧里改状态」的写入 | `G3-THREE-TICK-BOUNDARY` | ERROR |

> 3.25 / 3.26 是 Three.js 项目最高频的两类隐性缺陷：透视下用屏幕坐标判定会直接错位，帧内改状态会导致判定与视觉不同步。

---

## L3 实跑预检

| # | 检查项 | 命令 / 条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.15 | typecheck | `npm run typecheck` 退出码 0 | `G3-TYPECHECK-FAIL` | ERROR |
| 3.18 | 依赖可解析 | `npm ls` 无 `missing` / `invalid` | `G3-DEP-MISSING` | ERROR |
| 3.19 | 构建产物 | `npm run build` 退出码 0 且产出 `dist/index.html` | `G3-THREE-BUILD-FAIL` | ERROR |
| 3.20 | 浏览器启动 | 打开 `dist/index.html` 无控制台 error、WebGL 上下文创建成功 | `G3-THREE-BOOT-FAIL` | ERROR |

> L3 只检测不修复：失败时回传错误日志，由 `game-code-forge` 接手（≤3 轮），本清单不修改任何代码。
> 3.20 属 Gate 3 预检；完整的浏览器实跑与数值平衡由 `game-integrate` 的 Gate 4 负责，本门不重复。

---

## 检查要点速查

- 单位池：单位不是 `Object3D`，是池中的数据结构；一帧一次矩阵批量上传，禁止每单位一个 Mesh。
- 数量抽象：`×N` 可让逻辑人数超过渲染上限，必须分离「逻辑整数」与「视觉代表数量」，并用 K 单位压缩显示。
- 资源：Three.js 工程多为程序化几何，`ASSET_MANIFEST.json` 仍须登记材质/配色 token，否则 3.21 空转。
- 输入：拖拽须射线投射到地面平面（`Raycaster` + `Plane`）再换算 `lane`，与摄像机解耦。
