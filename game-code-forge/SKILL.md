---
name: "game-code-forge"
description: "AI 游戏生成流水线阶段 4b。读取 PRD+TECH_DESIGN+ASSET_MANIFEST,生成完整可运行工程代码(支持 Phaser/Pixi/纯 Canvas 三引擎)。当被 game-forge-master 调度到本阶段,或用户要'生成游戏代码/工程'时调用。"
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

**约束**:不依赖任何可视化编辑器产物(.scene/.prefab/.anim 一律不生成)。所有节点树、动画、UI 用代码定义。

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

## 三、Phaser 引擎模板

### 3.1 main.ts
```typescript
import Phaser from 'phaser';
import { GameConfig } from './config/GameConfig';
import { BootScene } from './scenes/BootScene';
import { HomeScene } from './scenes/HomeScene';
import { GameScene } from './scenes/GameScene';

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game',
  width: GameConfig.designWidth,
  height: GameConfig.designHeight,
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  physics: { default: 'arcade', arcade: { gravity: { y: 0 } } },
  scene: [BootScene, HomeScene, GameScene],
  backgroundColor: '#000'
};

new Phaser.Game(config);
```

### 3.2 BootScene.ts(资源加载)
```typescript
export class BootScene extends Phaser.Scene {
  constructor() { super('Boot'); }
  
  preload(): void {
    // 读 ASSET_MANIFEST,逐图集加载
    const manifest = require('../config/AssetManifest');
    manifest.atlases.forEach(a => {
      this.load.atlas(a.id, a.output, a.dataOutput);
    });
    manifest.audio.forEach(a => {
      this.load.audio(a.id, a.path);
    });
  }
  
  create(): void {
    this.scene.start('Home');
  }
}
```

### 3.3 帧动画注册
```typescript
// 在 BootScene.create 中
const manifest = require('../config/AssetManifest');
const animDefs = [
  // 从 TECH_DESIGN 取
  { key: 'skin0-run', atlas: 'skin0', prefix: 'run_', start: 1, end: 6, fps: 12, repeat: -1 },
  // ...
];

animDefs.forEach(def => {
  this.anims.create({
    key: def.key,
    frames: this.anims.generateFrameNames(def.atlas, {
      prefix: def.prefix, start: def.start, end: def.end, zeroPad: 3
    }),
    frameRate: def.fps,
    repeat: def.repeat
  });
});
```

### 3.4 Character.ts(角色基类)
```typescript
export class Character extends Phaser.Physics.Arcade.Sprite {
  private animPrefix: string;
  
  constructor(scene: Phaser.Scene, x: number, y: number, texture: string, animPrefix: string) {
    super(scene, x, y, texture);
    this.animPrefix = animPrefix;
    scene.add.existing(this);
    scene.physics.add.existing(this);
  }
  
  playRun(): void { this.play(`${this.animPrefix}-run`); }
  playJump(): void { this.play(`${this.animPrefix}-jump`); }
}
```

### 3.5 弹窗系统
```typescript
export abstract class BasePopup extends Phaser.GameObjects.Container {
  protected mask: Phaser.GameObjects.Rectangle;
  protected content: Phaser.GameObjects.Container;
  
  constructor(scene: Phaser.Scene) {
    super(scene);
    this.mask = scene.add.rectangle(0, 0, scene.scale.width, scene.scale.height, 0x000000, 0.6)
      .setInteractive();
    this.mask.on('pointerdown', () => this.close());
    this.content = scene.add.container(0, 0);
    this.add([this.mask, this.content]);
    this.setVisible(false);
  }
  
  abstract build(): void;
  
  show(): void {
    this.setVisible(true);
    this.scene.tweens.add({ targets: this.content, scale: { from: 0.8, to: 1 }, duration: 200, ease: 'Back.Out' });
  }
  
  close(): void {
    this.scene.tweens.add({
      targets: this.content, scale: 0.8, alpha: 0, duration: 150,
      onComplete: () => this.destroy()
    });
  }
}
```

---

## 四、Pixi.js 引擎模板(关键差异)

```typescript
// main.ts
import { Application } from 'pixi.js';
const app = new Application({ width: 750, height: 1624, backgroundAlpha: 0 });
document.body.appendChild(app.view);

// Scene 自己实现
abstract class Scene {
  abstract update(dt: number): void;
  abstract enter(): void;
  abstract leave(): void;
}

class SceneManager {
  private current?: Scene;
  switch(s: Scene) {
    this.current?.leave();
    this.current = s;
    s.enter();
  }
  update(dt: number) { this.current?.update(dt); }
}

// 帧动画
const sheet = await Assets.load('assets/atlases/skin0.json');
const sprite = new AnimatedSprite(sheet.animations['skin0-run']);
sprite.play();
```

需自建:
- 碰撞检测(AABB 工具函数)
- 输入系统(`app.stage.eventMode = 'static'`)
- 音频(用 `howler` npm 包)

---

## 五、纯 Canvas 引擎模板(关键差异)

```typescript
// main.ts
const canvas = document.getElementById('game') as HTMLCanvasElement;
canvas.width = 750; canvas.height = 1624;
const ctx = canvas.getContext('2d')!;

let lastTime = 0;
function loop(time: number) {
  const dt = (time - lastTime) / 1000;
  lastTime = time;
  update(dt);
  render(ctx);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

// 帧动画
const img = new Image();
img.src = 'assets/role/skin0/run_001.png';
let frame = 0;
setInterval(() => { frame = (frame + 1) % 6; img.src = `assets/role/skin0/run_${String(frame+1).padStart(3,'0')}.png`; }, 83);

// 碰撞 AABB
function aabb(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}
```

---

## 六、生成规则

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

## 七、配置文件生成

### 7.1 package.json
```json
{
  "name": "{game-name}",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview"
  },
  "dependencies": {
    "phaser": "^3.80.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

### 7.2 tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "lib": ["ES2020", "DOM"]
  },
  "include": ["src"]
}
```

### 7.3 vite.config.ts
```typescript
import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  server: { port: 5173, open: true },
  build: { outDir: 'dist', assetsInlineLimit: 0 }
});
```

### 7.4 index.html
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <title>{游戏名}</title>
  <style>
    * { margin: 0; padding: 0; }
    body { background: #000; display: flex; justify-content: center; }
    #game { display: block; }
  </style>
</head>
<body>
  <div id="game"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

### 7.5 README.md
```markdown
# {游戏名}

## 开发
npm install
npm run dev

## 构建
npm run build
产物在 dist/

## 技术栈
- 引擎:{...}
- 构建:Vite
- 语言:TypeScript strict

## 文档
见 docs/ 目录
```

---

## 八、生成顺序

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

## 九、交互约定

1. 读取 4 份输入文档后,**不要问用户**,直接生成
2. 生成过程分批 Write,每批 5-10 个文件
3. 完成后简报:"代码生成完成,共 {N} 个 .ts 文件。下一步可调用 game-integrate 集成构建"
4. 不要自行调用 game-integrate

---

## 十、质量检查清单

- [ ] 所有文件已生成(对照 TECH_DESIGN 目录结构)
- [ ] package.json scripts 完整(dev/build/typecheck)
- [ ] tsconfig strict:true
- [ ] 无硬编码资源路径
- [ ] 无 any 滥用(除外部 API)
- [ ] 所有 PRD 弹窗都有对应文件
- [ ] 所有 PRD 状态转换都有代码
- [ ] README 含运行命令
- [ ] Sprite/Body 偏移安全(见 十一)
- [ ] 数值平衡已校验且 GameConfig 顶部含推导注释(见 十二)

---

## 十一、Sprite/Body 偏移安全(关键踩坑)

### 11.1 问题背景

ASSET_MANIFEST 声明 `size: [256, 256]` 是**期望尺寸**,但 AI 生图实际常返回 1024×1024 或 1920×1920(详见 game-asset-forge 第十章)。
若代码按期望尺寸硬编码 body offset,会导致 body 偏移到 sprite 视觉区域外,**角色看似随机下坠消失**。

### 11.2 反例(禁止)

```typescript
// 反例:假设 texture 是 256×256,硬编码 offset
body.setSize(80, 140, true);
body.setOffset(88, 58);  // ← 若 texture 实为 1920×1920,body 会跑到 sprite 左上角外
```

### 11.3 正例(推荐)

**方案 A:body 居中到 sprite 中心(首选,简单)**

```typescript
// 用 setSize 第 3 参 center=true,让 body 自动居中到 sprite frame 中心
// 不调 setOffset,与 texture 实际尺寸解耦
body.setSize(80, 140, true);
```

**方案 B:setScale 缩到设计尺寸 + body 居中(视觉效果更好)**

```typescript
// 把 1920×1920 缩到 256×256(scale = 设计尺寸 / 实际尺寸)
this.setScale(GameConfig.hero.scale);  // 配置里写 scale: 0.1333
body.setSize(80, 140, true);
```

**方案 C:加载后 resize texture(根治,但需 sharp/canvas)**

```typescript
// 在 BootScene.preload 后,用 sharp 把所有 jpg resize 到 manifest.size
// 详见 game-asset-forge 第十章格式转换脚本
```

### 11.4 配置约束

GameConfig 里:
- **必须**保留 `scale` 字段(方案 B 用)
- **不要**写死 `bodyOffsetX/Y`(已被方案 A 取代,保留会让后人误用)
- Hero/Obstacle 等所有 Sprite 类**必须**用方案 A 或 B

### 11.5 验收(浏览器实测)

集成后必须用 browser_evaluate 验证:
- `hero.body.center.x === hero.x` 且 `hero.body.center.y === hero.y`(body 居中)
- `hero.body.blocked.down === true`(collider 生效)
- `hero.body.velocity.y === 0`(静止,未下坠)

任一不满足 → 回到 11.3 排查。

### 11.6 适用范围

本规则适用于**所有 Sprite 类**:
- Character (Hero/Enemy)
- Obstacle
- Collectible (金币/道具)
- Particle Sprite

**不适用**:
- 用 generateTexture 生成的纯色矩形(texture 尺寸 = 设计尺寸,无偏移问题)
- UI Text/Button(无 physics body)

---

## 十二、数值平衡校验(关键踩坑)

### 12.1 问题背景

PRD §2.3 给出了跳跃/移动/障碍的物理平衡推导,但代码生成时容易:
- 漏抄 PRD 数值,直接拍脑袋写默认值
- 只填 GameConfig 字段,不做可玩性校验
- 没有把推导注释写进 GameConfig,后人调参无从下手

**PoC 踩坑**:gravityY=1200/jumpVelocity=-700/speed=300/interval=800ms 时,滞空期障碍移动 350px > 间距 240px,Hero 永远跳不过去。

### 12.2 强制规则

生成 GameConfig.ts 时:
1. **必须**从 PRD §2.3 读取推导表,直接抄入 GameConfig 字段值
2. **必须**在 GameConfig 顶部写推导注释块(公式 + 每档 D/M/R 余量)
3. **必须**自检四条可玩性约束(见 12.3),任一不满足 → 停止生成,回到 PRD §2.3 修正数值

### 12.3 可玩性约束(硬性,全部满足才可玩)

| 约束 | 公式 | 不满足处理 |
|---|---|---|
| 跳得过去 | `H > obstacle.height + 20` | 调大 jumpVelocity 或减小 gravityY |
| 落得下地 | `D > M` | 增大 interval 或减小 speed |
| 反应得及 | `R = D - M ≥ 100px` | 增大 interval |
| **穿越时间够**(关键!) | `T_above > T_cross + 0.3s` | 降低 obstacle.height / 减小 bodyW+obstacleW / 增大 jumpVelocity |

其中:
```
T = 2 * |jumpVelocity| / gravityY           (滞空时间)
H = jumpVelocity² / (2 * gravityY)          (跳跃高度)
D = speed * interval / 1000                  (障碍间距, interval 单位 ms)
M = speed * T                                (滞空期障碍移动距离)
T_above = 2 * sqrt(2*(H - obstacle.height) / gravityY)   (body高于障碍顶的持续时间)
T_cross = (bodyW + obstacleW) / speed        (障碍穿过body水平范围的时间)
```

**第 4 条是最容易漏的坑**(PoC 踩过):即使最高点能越过,但 body 在障碍上方的时间太短,
障碍还没穿过 body 水平范围 Hero 就降落了 → overlap → game over。
表现:玩家感觉"明明跳过去了但还是撞了"。

### 12.4 GameConfig 注释模板(必须照抄)

```typescript
// 全局游戏配置常量(对应 PRD 数值设计表)
//
// 数值平衡推导(关键 - 含穿越时间校验):
//   跳跃滞空时间   T = 2 * |jumpVelocity| / gravityY
//   跳跃最大高度   H = jumpVelocity² / (2 * gravityY)
//   障碍间距       D = speed * interval / 1000
//   滞空期移动距离 M = speed * T
//   body高于障碍顶持续时间 T_above = 2 * sqrt(2*(H - obstacle.height) / gravityY)
//   障碍穿过body水平范围时间 T_cross = (bodyW + obstacleW) / speed
//
// 可玩性约束(硬性,全部满足才可玩):
//   1. 跳得过去: H > obstacle.height + 20
//   2. 间距够宽: D > M + 100px (反应余量)
//   3. 时间够长: T_above > T_cross + 0.3s (穿越余量,关键!)
//
// 当前数值:
//   T = ...   H = ...   T_above = ...
//   档1: D=..., M=..., 反应余量=... ✓  T_cross=..., 穿越余量=... ✓
//   档2: ...
//   档3: ...

export const GameConfig = { ... } as const;
```

### 12.5 校验失败时的处理

若 PRD §2.3 的推导表本身就不满足约束(常见:PRD 阶段没算清楚):
1. 不要硬抄错误数值到 GameConfig
2. 在 GameConfig 顶部注释标注 `// ⚠️ 数值不可玩,详见 ASSET_ISSUES.md`
3. 在 ASSET_ISSUES.md 追加:
   ```
   ## 数值平衡问题
   - 档 X: 约束 N 不满足
     D=... M=..., R=...(反应余量不足/或 T_above=... T_cross=..., 穿越余量不足)
     建议: [具体调参方向]
   ```
4. 提示用户回到 game-spec 修正 PRD §2.3

**穿越时间不足的调参优先级**(PoC 经验):
1. 降低 obstacle.height → 增大 T_above(最有效)
2. 减小 bodyW + obstacleW → 减小 T_cross
3. 增大 jumpVelocity / 减小 gravityY → 增大 H → 增大 T_above

### 12.6 适用范围

- 跑酷/无尽奔跑(本 PoC 类型)
- 平台跳跃(超级马里奥式)
- 飞行躲避(Flappy Bird 式,把跳跃换成拍动)
- 任何含"移动障碍 + 角色位移"的游戏

**不适用**:
- 纯解谜(无实时移动)
- 回合制(无物理曲线)
- 三消/消除(无角色位移)


---

## 十三、Phaser 中文文字换行(关键踩坑)

### 13.1 问题背景

Phaser 的 `wordWrap` 配置默认按**空格分词**,中文文本无空格不会换行,导致:
- 对话框内长句不换行,文字溢出对话框边界
- 卡片描述文字超出卡片范围
- 这在纯英文游戏中不会暴露,但中文游戏是**必现问题**

### 13.2 反例(禁止)

```typescript
// 反例:wordWrap 不带 useAdvancedWrap,中文不换行
this.add.text(0, 0, '这是一段很长的中文描述文字...', {
  fontSize: '22px',
  wordWrap: { width: 440 },  // ← 中文不会在此换行!
});
```

### 13.3 正例(必须)

```typescript
// 正例:加 useAdvancedWrap: true 启用字符级换行
this.add.text(0, 0, '这是一段很长的中文描述文字...', {
  fontSize: '22px',
  wordWrap: { width: 440, useAdvancedWrap: true },  // ← 中文会按字符换行
});
```

### 13.4 强制规则

**所有**含 `wordWrap` 的 text 配置**必须**加 `useAdvancedWrap: true`。

常见位置(逐一检查):
- 对话框/打字机组件(Typewriter)
- 卡片描述文字(各类卡片组件)
- 弹窗提示文字
- 剧情叙述文字
- 任何可能出现中文长文本的 Text 对象

### 13.5 适用范围

- 所有 Phaser 3.x 版本
- 所有含中文/日文/韩文(无空格分词语言)的文本
- 纯英文文本不受影响(加 useAdvancedWrap 也无副作用)

---

## 十四、图集帧名格式匹配(关键踩坑)

### 14.1 问题背景

Phaser 图集 JSON 有两种格式:
- **Hash 格式**:`frames` 是对象,帧以名称为 key(如 `"swim_001": { frame: {...} }`)
- **Array 格式**:`frames` 是数组,帧以索引为序

动画注册时必须用对应的 API,否则产生 "Frame not found" 警告:
- Hash 格式 → 必须用 `generateFrameNames`(按名称查找)
- Array 格式 → 必须用 `generateFrameNumbers`(按索引查找)

### 14.2 反例(禁止)

```typescript
// 反例:Hash 格式图集用 generateFrameNumbers,帧名不匹配
// 图集 JSON 帧名是 "swim_001",但 generateFrameNumbers 按索引 0/1/2/3 查找
this.anims.create({
  key: 'char_swim',
  frames: this.anims.generateFrameNumbers('char_atlas', { start: 0, end: 3 }),
  // ← 产生 "Frame not found" 警告!
});
```

### 14.3 正例(必须)

```typescript
// 正例:Hash 格式图集用 generateFrameNames,按名称匹配
this.anims.create({
  key: 'char_swim',
  frames: this.anims.generateFrameNames('char_atlas', {
    prefix: 'swim_',
    start: 1,
    end: 4,
    zeroPad: 3,
  }),
  // ← 正确匹配 "swim_001" 到 "swim_004"
});
```

### 14.4 判断图集格式

读取图集 JSON 的 `frames` 字段:
```javascript
const atlas = JSON.parse(fs.readFileSync('assets/atlases/char_atlas.json'));
const isHash = !Array.isArray(atlas.frames);  // true = Hash 格式
```

### 14.5 强制规则

1. game-asset-forge 打包图集时,**统一用 Hash 格式**(JSON Hash),便于按名称查找
2. game-code-forge 注册动画时,**必须先判断图集格式**:
   - Hash → `generateFrameNames(prefix, start, end, zeroPad)`
   - Array → `generateFrameNumbers(start, end)`
3. 帧名命名规范:`{prefix}_{index:03d}`(如 `swim_001`),zeroPad=3

### 14.6 排查方法

浏览器运行时检查纹理帧:
```javascript
const tex = game.textures.get('char_atlas');
console.log(tex.getFrameNames());  // 查看实际帧名
console.log(tex.has('swim_001'));  // 检查帧是否存在
```

