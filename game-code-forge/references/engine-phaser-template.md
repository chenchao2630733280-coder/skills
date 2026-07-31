# Phaser 引擎模板

> 本文件从 game-code-forge SKILL.md 抽离,作为 Phaser 引擎的完整模板。生成 Phaser 代码时按需读取。

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
