---
name: "game-code-forge"
description: "AI 游戏生成流水线阶段 4b。读取 PRD+TECH_DESIGN+ASSET_MANIFEST,生成完整可运行工程代码(支持 Phaser 3/Pixi.js/纯 Canvas/Godot 4/Unity/Three.js 六引擎)。存在 docs/GAME_TEARDOWN.md 时进入复刻模式:参数外置对齐 NUMERIC_MODEL.csv、四维状态分离、事务式状态更新、重置确定性。当被 game-forge-master 调度到本阶段,或用户要'生成游戏代码/工程'时调用。"
---

# Game Code Forge — 代码锻造

本 skill 是 AI 游戏生成流水线的**阶段 4b**(与 game-asset-forge 并行),职责是消费 PRD + TECH_DESIGN + ASSET_MANIFEST,**生成完整工程代码**,产出 `src/`、`index.html`、`package.json` 等。

---

## 一、输入与输出

**输入**(必读):
- `docs/GAME_BLUEPRINT.md`(取引擎选择)
- `docs/PRD.md`(取玩法/UI/状态机)
- `docs/TECH_DESIGN.md`(取目录/模块/类设计)
- `docs/ASSET_MANIFEST.json`(取资源 ID 与路径映射)

**关卡制附加输入**(存在 `config/levels.json` 时**必读**,由阶段 2.5 `game-level-design` 产出):
- `config/levels.json`(运行期关卡配置,**唯一关卡数据源**,加载方式见 §4.1)
- `docs/LEVEL_PLAN.md`(仅作参考:目标首通率、参数口径;**不要据此重写数值**)

**复刻模式附加输入**(存在 `docs/GAME_TEARDOWN.md` 时**必读**):
- `docs/NUMERIC_MODEL.csv`(参数唯一来源)
- `docs/TEARDOWN_MATRIX.json`(判定基准、状态建模条目)

**复刻模式五条实现约束**:
1. **参数外置**:所有数值进配置对象,字段名与 CSV `parameter` 同名,注释保留 `matrix_id`;代码里出现魔法数字即违反本条
2. **四维状态分离**:`belongsTo` / `renderOrder` / `blocksWhat` / `removable` 各自独立字段;禁止用渲染层号推导可交互(详见 `../game-teardown/references/state-modeling.md`)
3. **派生不存副本**:`remaining*` / `progress` / `available*` 一律实时计算,不得持久化
4. **事务式状态更新**:一次操作在事务内改完权威状态再发事件;动画/音效只订阅事件,**禁止在动画回调里改规则**
5. **判定基准按 MATRIX 实现**:遮挡/命中用矩阵 `value_or_range` 里声明的基准(中心点/碰撞区/多边形/人工配置),不得自行换基准——换基准 = 换手感
6. **确定性**:随机只用于表现参数;同一关重置 N 次逻辑结果一致(供 game-integrate Gate 4 回归)

**输出**(固定路径):
- `package.json`、`tsconfig.json`、`vite.config.ts`、`index.html`
- `src/**/*.ts`
- `README.md`

Godot 4 工程产物(当引擎为 Godot 时,替代上述 Web 工程产物):
```
Godot 4 工程:
- project.godot           # 工程配置
- export_presets.cfg      # 导出预设
- scenes/                 # 场景文件
  ├── Main.tscn           # 主场景
  ├── BootScene.tscn      # 启动场景
  └── {SceneName}.tscn    # 各游戏场景
- scripts/                # GDScript 脚本
  ├── main.gd             # 主入口
  ├── BootScene.gd        # 启动逻辑
  ├── Character.gd        # 角色控制
  └── {Module}.gd         # 各模块脚本
- assets/                 # 复用 game-asset-forge 产出(符号链接或复制)
```

Unity 工程产物(当引擎为 Unity 时,替代上述 Web 工程产物):
```
Unity 工程:
- ProjectSettings/ProjectVersion.txt         # Unity 版本标识(2022.3 LTS)
- Assets/Scripts/Runtime/*.cs                # 运行时脚本(MonoBehaviour)
- Assets/Scripts/Runtime/{ProjectName}.asmdef # 运行时程序集定义
- Assets/Scripts/Editor/SceneBuilder.cs      # 场景程序化构建
- Assets/Scripts/Editor/BuildScript.cs       # 构建入口(供 -executeMethod 调用)
- Assets/Scripts/Editor/{ProjectName}.Editor.asmdef  # Editor 程序集
- Assets/Scenes/*.unity                      # 场景文件(由 SceneBuilder 程序化生成)
- Packages/manifest.json                     # 包依赖
- {ProjectName}.csproj                       # 工程文件(Unity 重新生成会覆盖)
- assets/                                    # 复用 game-asset-forge 产出,放入 Assets/Resources/
```

**约束**:不依赖任何可视化编辑器产物(Web 引擎:所有节点树/动画/UI 用代码定义)。Godot 4 例外:生成 .tscn 场景文件(文本格式,AI 可直接生成)和 .gd 脚本,但不依赖 Godot 编辑器交互操作。Unity 例外:生成 .cs 脚本与工程配置,.unity 场景文件由 Editor/SceneBuilder.cs 在 batchmode 首次导入时程序化构建,AI 不直接写 YAML 场景文件。

---

## 二、通用工程结构(Web 四引擎通用;Godot/Unity 见各自 references 模板)

```
{项目名}/
├── index.html              # Phaser 3/Pixi.js/纯 Canvas 入口
├── package.json
├── tsconfig.json
├── vite.config.ts
├── README.md
├── src/
│   ├── main.ts             # 引擎初始化入口
│   ├── config/
│   │   ├── GameConfig.ts    # 全局配置(分辨率/物理/缩放)
│   │   ├── AssetManifest.ts # 引用 ../assets/manifest.json 或 ../docs/ASSET_MANIFEST.json
│   │   ├── SkinConfig.ts    # 皮肤映射
│   │   └── LevelConfig.ts   # 关卡数值:存在 config/levels.json 时只读它,禁止硬编码(见 §4.1)
│   ├── scenes/
│   │   ├── BootScene.ts      # 资源预加载
│   │   ├── HomeScene.ts
│   │   ├── GameScene.ts
│   │   └── ResultScene.ts   # 可选,也可用弹窗
│   ├── objects/
│   │   ├── BaseObject.ts     # 工厂基类
│   │   ├── Character.ts      # 角色基类
│   │   ├── Obstacle.ts       # 障碍物
│   │   └── ProgressBar.ts
│   ├── managers/
│   │   ├── AudioManager.ts
│   │   ├── PopupManager.ts
│   │   ├── StateManager.ts
│   │   └── GameData.ts       # 全局单例
│   ├── ui/
│   │   ├── BasePopup.ts
│   │   ├── HUD.ts
│   │   └── {各弹窗}.ts
│   ├── net/                   # 可选,如 PRD 有网络
│   │   ├── Request.ts
│   │   ├── Signature.ts      # 如需签名
│   │   └── Service.ts
│   ├── utils/
│   │   ├── eventBus.ts
│   │   ├── tween.ts
│   │   └── storage.ts
│   └── types/
│       └── index.ts
├── assets/                    # 由 game-asset-forge 产出
│   └── ...
└── docs/                      # 已有文档
```

---

## 全局约束

遵循 `../_shared/references/engineering-constraints.md`（项目隔离/技术栈沿用/密钥/验证/追溯/增量修改等 10 条通用工程约束，唯一事实来源）。

## references 使用指引

本 Skill 的引擎模板、配置模板和踩坑专题已抽离到 `references/` 目录,按需读取避免全量加载。

| 文件 | 何时读取 |
|------|---------|
| `references/engine-phaser-template.md` | 引擎为 Phaser 时 |
| `references/engine-pixi-template.md` | 引擎为 Pixi 时 |
| `references/engine-canvas-template.md` | 引擎为 Canvas 时 |
| `references/engine-godot-template.md` | 引擎为 Godot 4 时 |
| `references/engine-unity-template.md` | 引擎为 Unity 时 |
| `references/engine-three-template.md` | 引擎为 Three.js 时 |
| `references/web-config-template.md` | Web 引擎生成配置文件时 |
| `references/pitfall-sprite-body-offset.md` | Phaser 角色物理碰撞生成时 |
| `references/pitfall-balance-validation.md` | 跑酷类游戏数值配置生成时 |
| `references/pitfall-phaser-text-wrap.md` | Phaser 含中文文字渲染时 |
| `references/pitfall-atlas-frame-format.md` | Phaser 帧动画图集生成时 |
| `references/pitfall-phaser-ui-overlay-input.md` | Phaser UI 弹窗/长按/拖拽交互与层级（自定义容器被蒙层遮挡、setInteractive 写法、长按定时器、dragMode 区分） |
| `references/pitfall-state-visual-feedback.md` | 切换型玩法状态（潜行/加速/变身/整活/开盾）必须有可见反馈，否则玩家误判"点了没反应" |

---

## 三、Phaser 引擎模板

> 完整模板已抽离到 `references/engine-phaser-template.md`,生成 Phaser 代码时读取该文件。

| 模块 | 文件 | 说明 |
|------|------|------|
| 主入口 | main.ts | Phaser.Game 实例配置 |
| 启动场景 | BootScene.ts | 资源预加载 |
| 帧动画 | 帧动画注册 | generateFrameNames/Numbers |
| 角色控制 | Character.ts | CharacterBody + 状态机 |
| 弹窗系统 | BasePopup | 模态弹窗基类 |

**Phaser 专属踩坑**(生成时按需读取):
- Sprite/Body 偏移安全:见 `references/pitfall-sprite-body-offset.md`
- 中文文字换行:见 `references/pitfall-phaser-text-wrap.md`
- 图集帧名格式匹配:见 `references/pitfall-atlas-frame-format.md`

---

## 四、Pixi.js 引擎模板(关键差异)

> 完整模板已抽离到 `references/engine-pixi-template.md`,生成 Pixi 代码时读取该文件。

| 模块 | 说明 |
|------|------|
| Application | 初始化+Ticker |
| AnimatedSprite | 帧动画播放 |
| Assets.load | 资源加载 |

---

## 五、纯 Canvas 引擎模板(关键差异)

> 完整模板已抽离到 `references/engine-canvas-template.md`,生成 Canvas 代码时读取该文件。

| 模块 | 说明 |
|------|------|
| 主循环 | requestAnimationFrame |
| 帧动画 | 手动切帧 |
| 碰撞检测 | AABB |

---

## 六、Godot 4 引擎模板

> 完整模板已抽离到 `references/engine-godot-template.md`,生成 Godot 代码时读取该文件。Godot 4 例外:生成 .tscn 场景文件和 .gd 脚本,但不依赖 Godot 编辑器交互操作。

| 模块 | 文件 | 说明 |
|------|------|------|
| 工程配置 | project.godot | config_version=5,input映射 |
| 主场景 | Main.tscn | format=3,Node2D+GameLayer+UILayer |
| 主脚本 | main.gd | 场景切换、Toast |
| 启动场景 | BootScene.gd | ResourceLoader线程加载 |
| 角色控制 | Character.gd | CharacterBody2D+状态机 |
| 导出预设 | export_presets.cfg | Windows Desktop + HTML5 |

**关键差异**:Godot 4 与 Web 引擎在入口/脚本/场景/资源/物理/导出/类型检查/3D支持上均不同,详见 `references/engine-godot-template.md` §6.7 差异对比表。

---

## 七、Unity 引擎模板

> 完整模板已抽离到 `references/engine-unity-template.md`,生成 Unity 代码时读取该文件。Unity 例外:生成 .cs 脚本与工程配置,.unity 场景文件由 Editor/SceneBuilder.cs 在 batchmode 首次导入时程序化构建,AI 不直接写 YAML 场景文件。

| 模块 | 文件 | 说明 |
|------|------|------|
| 工程版本 | ProjectVersion.txt | Unity 2022.3 LTS 标识 |
| 程序集定义 | {ProjectName}.asmdef | Runtime 程序集,与 Editor 分离 |
| 主入口 | UnityMain.cs | MonoBehaviour,场景初始化与首场景加载 |
| 启动场景 | BootScene.cs | 异步加载+进度条 |
| 角色控制 | CharacterController.cs | Rigidbody2D+Animator 状态机 |
| 全局状态 | GameManager.cs | 单例+状态机+分数 |
| 场景构建 | Editor/SceneBuilder.cs | 程序化生成 .unity 场景(替代手写 YAML) |
| 构建入口 | Editor/BuildScript.cs | 供 -executeMethod 调用,Windows/WebGL |
| 包依赖 | Packages/manifest.json | 2D/3D 包按需裁剪 |

**关键差异**:Unity 与 Godot/Web 引擎在入口/脚本语言/场景格式/资源加载/物理/导出/类型检查/工程识别上均不同,详见 `references/engine-unity-template.md` §7.12 差异对比表。

## 八、Three.js 引擎模板(关键差异)

> 完整模板已抽离到 `references/engine-three-template.md`,生成 Three.js 代码时读取该文件。

| 模块 | 文件 | 说明 |
|------|------|------|
| 场景单例 | Scene3D.ts | Scene / PerspectiveCamera / WebGLRenderer 全局唯一 |
| 实例化人群 | InstancedCrowd.ts | InstancedMesh + 对象池,逻辑数量与渲染数量解耦 |
| 曲线路径 | Pipe.ts | CatmullRomCurve3,单位按独立 t 进度插值 |
| 输入映射 | DragToLane.ts | 射线投射到地面平面,输出 (lane,z) |
| 构建 | vite.config.ts | npm run typecheck / build → dist/index.html |

**关键差异**:判定一律用赛道局部坐标 `(lane,z)`,禁止屏幕像素参与;详见 `references/engine-three-template.md` §判定契约。

---

## 九、生成规则

### 1. 严格 TypeScript
- `strict: true`
- 所有函数标注返回类型
- 所有数据结构用 interface
- 禁用 any(除非外部 API 返回,且必须加注释)

### 2. 资源引用走 Manifest
**禁止硬编码资源路径**。所有 `load.image(key, path)` 的 path 必须来自 `AssetManifest.ts`:

```typescript
// 正确
import { AssetManifest } from '../config/AssetManifest';
this.load.atlas(atlas.id, atlas.output, atlas.dataOutput);

// 错误
this.load.atlas('skin0', 'assets/atlases/skin0.png', 'assets/atlases/skin0.json');
```

**ASSET_MANIFEST.json 读取规则**:读取 manifest 时,`actualFormat`/`actualPath` 优先于 `format`/`path`(由 game-asset-forge 回写实际产出格式和路径)。若 `actualFormat` 存在且与 `format` 不同(如 format=png-32 但 actualFormat=jpg),按 actualFormat 走散图降级,不用 atlas 加载。

### 3. UI 节点树直接翻译
PRD 的节点树必须 1:1 翻译为代码:
```
PRD:
Canvas
├─ bg (Sprite)       → this.add.sprite(0, 0, AssetManifest.get('bg-home'))
├─ title (Text)       → this.add.text(0, 0, '一马当先', { fontFamily: '...', fontSize: 64 })
└─ startBtn (Btn)     → const btn = this.add.container(0, 0, [bg, label]); btn.setSize(200, 80).setInteractive();
```

### 4. 数值与配置分离
PRD 的"数值设计"表 → `config/GameConfig.ts`:
```typescript
export const GameConfig = {
  initialSpeed: 300,
  maxSpeed: 800,
  speedIncreasePerSec: 10,
  jumpVelocity: -600,
  // ...
} as const;
```

### 4.1 关卡数据加载(存在 `config/levels.json` 时必读)

关卡制项目由 `game-level-design`(阶段 2.5)产出 `config/levels.json`,它是**运行期唯一关卡数据源**。
本 skill 只负责"读它 + 按 `level_id` 取档",**不得把 `params` 的数值抄成常量**——`game-quality-gate` 的
3.28(`G3-LEVEL-DATA-DRIFT`)会比对 `src/` 里出现的关卡数值字面量,抄了就不一致。

| 引擎 | 加载方式 | 说明 |
|---|---|---|
| Phaser 3 / Pixi.js / 纯 Canvas / Three.js | `import levels from '../../../config/levels.json'`(`tsconfig` 开 `resolveJsonModule`) | 打包进 bundle,构建期即可发现字段错误;`LevelConfig.ts` 做类型映射 + 按 `level_id` 取档 |
| 同上,且需部署后热改数值 | 复制到 `public/config/levels.json`,`await fetch('/config/levels.json')` | 需处理加载失败:降级用内置默认关卡并写 `ASSET_ISSUES.md` |
| Godot 4 | 构建时把 `config/levels.json` 复制到工程根,`JSON.parse_string(FileAccess.get_file_as_string("res://config/levels.json"))` | 解析失败要报错并回退到首关配置,不要静默崩溃 |
| Unity | `Assets/StreamingAssets/config/levels.json` + `File.ReadAllText(Path.Combine(Application.streamingAssetsPath, "config/levels.json"))` | WebGL 平台必须用 `UnityWebRequest` 读 StreamingAssets |

`LevelConfig.ts`(或等价文件)的职责边界:
```typescript
import levelsRaw from '../../../config/levels.json';

export type LevelParams = Record<string, number>;
export interface LevelDef { level_id: string; index: number; tag: string; params: LevelParams; target_win: number; difficulty_score: number; }

const levels = levelsRaw.levels as LevelDef[];           // 类型收窄,不改数值
export const getLevel = (id: string) => levels.find(l => l.level_id === id);
export const levelCount = levels.length;
```
> 允许:类型定义、按 id 查找、读取时做范围钳制(如 `clamp`)。
> **禁止**:把 `params` 的字面量写成常量表、按关卡号写 `switch` 分支硬编码数值。

**无 `config/levels.json` 时**(单局制被裁剪、或项目不走阶段 2.5):回退到把数值写进
`config/GameConfig.ts` 的原有模式,并在 `docs/TECH_DESIGN.md` 注明"无关卡序列,关卡配置不适用"。

### 5. 状态机实现
PRD 的状态转换表 → `managers/StateManager.ts`(基于 Phaser EventEmitter 或自建 EventBus):

```typescript
type State = 'idle' | 'guide' | 'countdown' | 'play' | 'paused' | 'gameOver';
const transitions: Record<State, Partial<Record<string, State>>> = {
  idle: { start: 'guide' },
  guide: { done: 'countdown' },
  // ...
};
```

### 6. 弹窗生成
PRD 每个弹窗 → 一个继承 BasePopup 的类,文件放 `src/ui/`。

---

## 十、配置文件生成

> Web 引擎配置模板已抽离到 `references/web-config-template.md`,Godot 配置见 `references/engine-godot-template.md`,Unity 配置见 `references/engine-unity-template.md`。

| 引擎类型 | 配置文件 | references 文件 |
|---------|---------|----------------|
| Web(Phaser 3/Pixi.js/纯 Canvas/Three.js) | package.json/tsconfig.json/vite.config.ts/index.html/README.md | `references/web-config-template.md` |
| Godot 4 | project.godot/export_presets.cfg | `references/engine-godot-template.md` |
| Unity | ProjectVersion.txt/manifest.json/.asmdef/.csproj | `references/engine-unity-template.md` |

---

## 十一、生成顺序

按依赖关系顺序生成(Web 引擎步骤;Godot/Unity 引擎时按对应 references 模板的目录结构生成,顺序一致但文件替换为 .gd/.cs):
1. 工程配置文件(Web:package.json/tsconfig/vite.config/index.html;Godot:project.godot/export_presets.cfg;Unity:ProjectVersion.txt/manifest.json/.asmdef/.csproj)
2. config/ 层(GameConfig/AssetManifest/SkinConfig)
3. utils/ 层(eventBus/tween/storage)
4. types/ 层
5. managers/ 层(无依赖的先写)
6. ui/ 层(BasePopup + 各弹窗)
7. objects/ 层(Character/Obstacle)
8. scenes/ 层(Boot/Home/Game/Result)
9. main.ts(最后,引用所有)
10. README.md

---

## 十二、交互约定

0. **输入校验(读取前一次性)**:先校验 **4 份必读**(缺失则报错并列出缺失文件后退出,不进入生成流程),再校验 **1 份条件输入**:
   - `docs/GAME_BLUEPRINT.md` 缺失 → "缺少蓝图,请先调用 game-blueprint"
   - `docs/PRD.md` 或 `docs/TECH_DESIGN.md` 缺失 → "缺少规格,请先调用 game-spec"
   - `docs/ASSET_MANIFEST.json` 缺失 → "缺少资源清单,请先调用 game-art-spec"
   - `ASSET_MANIFEST.json` 存在但非法 JSON → `JSON.parse` try-catch,报错附行号与错误信息,退出
   - `config/levels.json` **存在则纳入必读**(关卡制,见 §4.1);缺失则标注 `LEVELS_SKIPPED` 并继续(单局制项目合法),同时在简报中说明"未接入关卡配置"
   - `config/levels.json` 存在但非法 JSON / 缺 `levels` 数组 → 报错退出(这是阶段 2.5 的产物缺陷,不要静默兜底)
1. 读取 4 份必读文档 + (如有)`config/levels.json` 后,**不要问用户**,直接生成
2. 生成过程分批 Write,每批 5-10 个文件
3. 完成后简报:"代码生成完成,共 {N} 个 .ts 文件。下一步可调用 game-integrate 集成构建"
4. 不要自行调用 game-integrate

---

## 十三、质量检查清单

- [ ] 所有文件已生成(对照 TECH_DESIGN 目录结构)
- [ ] package.json scripts 完整(dev/build/typecheck)
- [ ] tsconfig strict:true
- [ ] 无硬编码资源路径
- [ ] 无 any 滥用(除外部 API)
- [ ] 所有 PRD 弹窗都有对应文件
- [ ] 所有 PRD 状态转换都有代码
- [ ] README 含运行命令
- [ ] Sprite/Body 偏移安全(见 十三)
- [ ] 数值平衡已校验且 GameConfig 顶部含推导注释(见 十四)
- [ ] UI 自定义容器(Panel/RustButton 等)已显式 `parent.add(panel)`,未被高 depth 蒙层遮挡(见 十七)
- [ ] (复刻模式)数值零硬编码,GameConfig 字段名与 CSV `parameter` 同名
- [ ] (关卡制)`config/levels.json` 只在一处被读取(`LevelConfig.ts` 或等价文件),`src/` 中无关卡数值字面量(见 §4.1)
- [ ] (复刻模式)四维状态分离、派生态未持久化、规则未写在动画回调里、重置确定性可过
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)

---

## 十四、Sprite/Body 偏移安全(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-sprite-body-offset.md`。

核心约束:body.setSize/setOffset 必须在 create 物理后调用,否则偏移无效导致碰撞框错位。

## 十五、数值平衡校验(关键踩坑)

> **跨引擎通用**(跑酷类)。完整规范见 `references/pitfall-balance-validation.md`。

核心约束:GameConfig 必须带注释推导链,jumpVelocity/gravity/obstacleInterval/obstacleSpeed 必须可数学验证。

## 十六、Phaser 中文文字换行(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-phaser-text-wrap.md`。

核心约束:中文文字必须用 `wordWrap.useAdvancedWrap` + 手动按字符切分,否则换行无效。

## 十七、图集帧名格式匹配(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-atlas-frame-format.md`。

核心约束:generateFrameNames 的 prefix/suffix/start/end 必须与 JSON Hash 中的实际帧名完全匹配。

## 十八、Phaser UI 交互 / 层级踩坑(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-phaser-ui-overlay-input.md`。

核心约束(生成弹窗/长按/拖拽 UI 时必查):
- 自定义 `Panel`/`RustButton` 等容器构造函数会 `scene.add.existing(this)` 挂到场景根(depth 0),**必须显式 `targetContainer.add(panel)`**,否则被更高 depth 的全屏蒙层遮挡(表现"只有蒙层没有弹窗")。
- `setInteractive` 必须用配置对象 `{ hitArea, hitAreaCallback, useHandCursor }`,不能把 `useHandCursor` 当第三参。
- 长按用 `this.time.delayedCall` 定时器触发 + `done` 防重入;**不要**在 `pointerout` 取消(微抖会重置导致"卡住");拆解逻辑同步执行,不依赖抖动 tween 的 `onComplete`。
- 全局 `drag` handler 用 `setData('dragMode','free'|'h')` 区分"自由拖"与"横滑容器",避免把 UI 一起拖飞。
- 局部变量不能用 `let x?: T`,用 `let x: T | undefined`。
- 缺 favicon 会产生无害 404,`index.html` 加 `<link rel="icon" href="data:," />` 消除。

## 十九、状态切换的可见反馈(关键踩坑)

> **跨引擎通用**。完整规范见 `references/pitfall-state-visual-feedback.md`。

核心约束(生成含"潜行/加速/变身/整活/开盾"等切换态的游戏时必查):
- 状态切换不能只改逻辑布尔/数值,必须有视觉/动画反馈(潜行半透明、整活 tween 形变、按钮持续高亮)。
- 切换型按钮文字/底色要随状态变化(关→开),否则玩家以为"点了没反应"。
- 动画型动作需冻结输入,避免动画期间画面乱跳。
