# Pixi.js 引擎模板

> 本文件从 game-code-forge SKILL.md 抽离,作为 Pixi.js 引擎的完整模板(关键差异)。生成 Pixi 代码时按需读取。

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
