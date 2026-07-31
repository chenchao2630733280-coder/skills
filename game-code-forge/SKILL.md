---
name: "game-code-forge"
description: "AI 游戏生成流水线阶段 4b。读取 PRD+TECH_DESIGN+ASSET_MANIFEST,生成完整可运行工程代码(支持 Phaser/Pixi/纯 Canvas/Godot 4 四引擎)。当被 game-forge-master 调度到本阶段,或用户要'生成游戏代码/工程'时调用。"
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

**约束**:不依赖任何可视化编辑器产物(Web 引擎:所有节点树/动画/UI 用代码定义)。Godot 4 例外:生成 .tscn 场景文件(文本格式,AI 可直接生成)和 .gd 脚本,但不依赖 Godot 编辑器交互操作。

---

## 二、通用工程结构(三引擎通用)

```
{项目名}/
├── index.html              # Phaser/Pixi/Canvas 入口
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
│   │   └── LevelConfig.ts   # 关卡/数值
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

## references 使用指引

本 Skill 的引擎模板、配置模板和踩坑专题已抽离到 `references/` 目录,按需读取避免全量加载。

| 文件 | 何时读取 |
|------|---------|
| `references/engine-phaser-template.md` | 引擎为 Phaser 时 |
| `references/engine-pixi-template.md` | 引擎为 Pixi 时 |
| `references/engine-canvas-template.md` | 引擎为 Canvas 时 |
| `references/engine-godot-template.md` | 引擎为 Godot 4 时 |
| `references/web-config-template.md` | Web 引擎生成配置文件时 |
| `references/pitfall-sprite-body-offset.md` | Phaser 角色物理碰撞生成时 |
| `references/pitfall-balance-validation.md` | 跑酷类游戏数值配置生成时 |
| `references/pitfall-phaser-text-wrap.md` | Phaser 含中文文字渲染时 |
| `references/pitfall-atlas-frame-format.md` | Phaser 帧动画图集生成时 |

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

## 七、生成规则

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

## 八、配置文件生成

> Web 引擎配置模板已抽离到 `references/web-config-template.md`,Godot 配置见 `references/engine-godot-template.md`。

| 引擎类型 | 配置文件 | references 文件 |
|---------|---------|----------------|
| Web(Phaser/Pixi/Canvas) | package.json/tsconfig.json/vite.config.ts/index.html/README.md | `references/web-config-template.md` |
| Godot 4 | project.godot/export_presets.cfg | `references/engine-godot-template.md` |

---

## 九、生成顺序

按依赖关系顺序生成:
1. 工程配置文件(package.json/tsconfig/vite.config/index.html)
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

## 十、交互约定

1. 读取 4 份输入文档后,**不要问用户**,直接生成
2. 生成过程分批 Write,每批 5-10 个文件
3. 完成后简报:"代码生成完成,共 {N} 个 .ts 文件。下一步可调用 game-integrate 集成构建"
4. 不要自行调用 game-integrate

---

## 十一、质量检查清单

- [ ] 所有文件已生成(对照 TECH_DESIGN 目录结构)
- [ ] package.json scripts 完整(dev/build/typecheck)
- [ ] tsconfig strict:true
- [ ] 无硬编码资源路径
- [ ] 无 any 滥用(除外部 API)
- [ ] 所有 PRD 弹窗都有对应文件
- [ ] 所有 PRD 状态转换都有代码
- [ ] README 含运行命令
- [ ] Sprite/Body 偏移安全(见 十二)
- [ ] 数值平衡已校验且 GameConfig 顶部含推导注释(见 十三)

---

## 十二、Sprite/Body 偏移安全(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-sprite-body-offset.md`。

核心约束:body.setSize/setOffset 必须在 create 物理后调用,否则偏移无效导致碰撞框错位。

## 十三、数值平衡校验(关键踩坑)

> **跨引擎通用**(跑酷类)。完整规范见 `references/pitfall-balance-validation.md`。

核心约束:GameConfig 必须带注释推导链,jumpVelocity/gravity/obstacleInterval/obstacleSpeed 必须可数学验证。

## 十四、Phaser 中文文字换行(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-phaser-text-wrap.md`。

核心约束:中文文字必须用 `wordWrap.useAdvancedWrap` + 手动按字符切分,否则换行无效。

## 十五、图集帧名格式匹配(关键踩坑)

> **Phaser 专属**。完整规范见 `references/pitfall-atlas-frame-format.md`。

核心约束:generateFrameNames 的 prefix/suffix/start/end 必须与 JSON Hash 中的实际帧名完全匹配。
