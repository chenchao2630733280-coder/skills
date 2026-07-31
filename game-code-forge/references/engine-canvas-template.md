# 纯 Canvas 引擎模板

> 本文件从 game-code-forge SKILL.md 抽离,作为纯 Canvas 引擎的完整模板(关键差异)。生成 Canvas 代码时按需读取。

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
