---
name: "game-polish"
description: "AI 游戏生成流水线阶段 6(可选)。在 game-integrate 产出可运行游戏后,叠加视觉/手感/反馈层面的动画与效果打磨,不改变核心玩法与数值。当被 game-forge-master 调度到本阶段,或用户要'优化游戏效果/让画面更好看/加特效/提升手感/打磨动画'时调用。"
---

# 游戏效果优化(game-polish)

## 一、定位与边界

**前置**: game-integrate 已产出可运行游戏(npm run dev 能跑、核心玩法可玩)
**输出**: 在原工程基础上增量叠加效果,产出 POLISH_REPORT.md
**核心原则(不可违背)**:
1. **不改玩法**: 不修改 GameConfig 的数值平衡字段(speed/interval/jumpVelocity/gravityY/obstacle.*)
2. **不改逻辑**: 不修改状态机、碰撞判定、计分规则
3. **只加效果**: 视觉层(粒子/光影/缓动) + 手感层(挤压拉伸/镜头反馈) + 细节层(呼吸/微动)
4. **温和叠加**: 所有效果作为"增量"叠加,不直接覆盖原有运动(借鉴 fish-tank 的 Boids 力叠加原则)

## 二、效果菜单(6 大维度,33 项)

从 fish-tank-animation-polish 等 PoC 提炼的通用优化项。每项标注:
- ⭐ 优先级(⭐⭐⭐ 高频高收益 / ⭐⭐ 中 / ⭐ 低)
- 适用类型(跑酷/平台/飞行/养成/解谜/通用)
- 实现层(逻辑层/渲染层/粒子层/镜头层)

### A. 角色生命感(⭐⭐⭐,通用)

让静态/移动中的角色"活起来"。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| A1 | **呼吸缩放** | `scale = 1 + 0.03*sin(t/600 + phase)` 每角色随机 phase | 通用 | 渲染 |
| A2 | **待机微动** | 重心 y 偏移 `±2px` 正弦,呼吸节奏 | 通用 | 渲染 |
| A3 | **移动惯性** | 速度变化用 lerp 平滑,不瞬变 | 跑酷/平台 | 逻辑 |
| A4 | **转身翻转** | 速度方向改变时 scaleX 渐变翻转(非瞬切) | 平台/养成 | 渲染 |
| A5 | **眨眼** | 每 3-8s 随机闭眼 100ms(眨眼帧或遮罩) | 养成/对话 | 渲染 |

**fish-tank 来源**: 鱼鳃呼吸动画(相位 + 透明度 + 大小三参数调制)

### B. 动作反馈(⭐⭐⭐,跑酷/平台/飞行)

让关键动作有"手感"。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| B1 | **跳跃挤压拉伸**(Disney 12 原则之一) | 起跳瞬间 scaleY↑scaleX↓(0.1s 内回正),落地反向 | 跑酷/平台 | 渲染 |
| B2 | **落地粒子** | 落地瞬间生成 4-6 个尘土粒子,向外扩散+衰减 | 跑酷/平台 | 粒子 |
| B3 | **受击闪烁** | 受击后 0.3s 内 alpha 在 0.3~1 间闪烁 | 通用 | 渲染 |
| B4 | **击退定格** | 受击瞬间暂停 50ms(hitstop)增强打击感 | 动作/格斗 | 逻辑 |
| B5 | **拖尾** | 高速移动时每帧留半透明残影(最近 5 帧) | 跑酷/飞行 | 渲染 |
| B6 | **速度线** | 高速时屏幕边缘出现速度线 | 跑酷/飞行 | 渲染 |

### C. 环境氛围(⭐⭐⭐,通用)

让场景"有空气感"。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| C1 | **飘落粒子** | 雪花/花瓣/落叶/灰尘,从顶部生成,受风偏移 | 通用 | 粒子 |
| C2 | **背景视差** | 多层背景以不同速度滚动(远慢近快) | 跑酷/平台 | 渲染 |
| C3 | **光影焦散** | 水下/林间光斑,`globalCompositeOperation='screen'`,alpha≤0.08 | 水族/森林 | 渲染 |
| C4 | **环境光呼吸** | 整体光照 alpha 随时间正弦微变 | 通用 | 渲染 |
| C5 | **天气循环** | 雨/雪/晴切换,影响粒子类型与背景色 | 养成/开放世界 | 粒子 |

**fish-tank 来源**: 光线焦散 caustics(6 光斑 + screen 混合 + 径向渐变)

### D. 反馈与提示(⭐⭐,通用)

让事件结果"看得见"。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| D1 | **得分飘字** | 得分位置生成 +10 文字,上浮+淡出 | 通用 | 渲染 |
| D2 | **拾取光圈** | 拾取位置生成扩散圆环,0.4s 衰减 | 通用 | 粒子 |
| D3 | **连击高亮** | 连击数 UI 缩放脉冲 | 通用 | 渲染 |
| D4 | **危险预警** | 障碍即将到达时 Hero 边缘红色脉冲 | 跑酷/飞行 | 渲染 |
| D5 | **进度条流光** | 进度条上叠加流动高光 | 通用 | 渲染 |

### E. 镜头效果(⭐⭐,跑酷/平台/动作)

让镜头"会说话"。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| E1 | **镜头跟随** | 相机 lerp 跟随主角(不瞬切) | 平台/动作 | 镜头 |
| E2 | **镜头震动** | 受击/碰撞时相机偏移随机抖动 0.2s | 通用 | 镜头 |
| E3 | **关键事件缩放** | 得分/受击瞬间 zoom-in 1.05×,0.3s 回正 | 通用 | 镜头 |
| E4 | **前方视野** | 高速时镜头前移露出更多前方 | 跑酷/飞行 | 镜头 |

### F. 资源适配修复(⭐⭐⭐,通用,必做)

修复 AI 生图的"不统一"问题。

| # | 效果 | 实现 | 适用 | 层 |
|---|---|---|---|---|
| F1 | **朝向自动检测+翻转** | 运行时检测每图头朝向,按需 scaleX=-1 | 通用 | 渲染 |
| F2 | **尺寸归一化** | 加载后 resize 到设计尺寸(已由 game-asset-forge 处理) | 通用 | 资源 |
| F3 | **颜色一致性** | 同组资源色调统一(可选 LUT 或 hue 偏移) | 通用 | 渲染 |

**fish-tank 来源**: 鱼朝向运行时检测(像素列宽度曲线找最宽处判定头朝向)

## 三、执行流程

```
1. 读取 POLISH_REQUEST.md(用户选定的优化项清单)
   ├─ 无该文件 → 用默认推荐集(见 3.1)
   └─ 有该文件 → 按用户选择
2. 读取 GameConfig.ts 确认数值字段(只读,不修改)
3. 按菜单分类逐项实现:
   ├─ 渲染层效果 → 在对应 Sprite/Object 类的 update/渲染方法中叠加
   ├─ 粒子层效果 → 新建 ParticleManager 或在 Scene 中维护粒子数组
   ├─ 镜头层效果 → 在 Scene update 中操作 cameras.main
   └─ 逻辑层效果(惯性/定格) → 在 Object 类中加平滑逻辑(不改数值)
4. 每项实现后立即浏览器自测(见 六)
5. 输出 POLISH_REPORT.md
```

### 3.1 默认推荐集(用户未指定时)

按游戏类型推荐 5-8 项:

| 类型 | 推荐项 |
|---|---|
| 跑酷/无尽奔跑 | B1 跳跃挤压、B2 落地粒子、B5 拖尾、C2 视差、D1 得分飘字、E2 镜头震动 |
| 平台跳跃 | A1 呼吸、B1 挤压、B2 落地粒子、C2 视差、E1 镜头跟随、E2 震动 |
| 飞行躲避 | A1 呼吸、B3 受击闪烁、B5 拖尾、B6 速度线、C2 视差、E4 前方视野 |
| 养成/水族 | A1 呼吸、A4 翻身、A5 眨眼、C3 焦散、C4 光呼吸、F1 朝向修复 |
| 解谜 | A1 呼吸、C4 光呼吸、D3 连击高亮、D5 流光 |

## 四、实现规范

### 4.1 文件组织

新增文件(不修改原有文件结构,只增量):
```
src/
  effects/
    ParticleManager.ts      # 粒子统一管理(飘字/光圈/尘土)
    JuiceEffects.ts          # 挤压拉伸/闪烁/定格等角色反馈
    CameraController.ts      # 镜头震动/跟随/缩放
  objects/
    Hero.ts                  # 在原有基础上 import 并调用 effects
```

### 4.2 粒子系统统一管理(借鉴 fish-tank)

```typescript
// 粒子类型枚举
export enum ParticleType {
  Dust = 'dust',         // 落地尘土
  FloatText = 'float',  // 飘字
  Ring = 'ring',         // 扩散光圈
  Snow = 'snow',         // 雪花
}

interface Particle {
  type: ParticleType;
  x: number; y: number;
  vx: number; vy: number;
  life: number; maxLife: number;
  // 类型特定字段
  text?: string; color?: number; radius?: number;
}

export class ParticleManager {
  private particles: Particle[] = [];

  emit(type: ParticleType, x: number, y: number, opts?: Partial<Particle>): void { ... }
  update(dt: number): void { ... }    // 位置更新 + 生命衰减
  draw(scene: Phaser.Scene): void { ... }  // 按类型分层绘制
}
```

**fish-tank 经验**: 粒子在主循环中统一 update,在 drawTank 中按层级绘制(背景后/角色前/角色后)。

### 4.3 挤压拉伸(Disney 原则)

```typescript
// JuiceEffects.ts
export class JuiceEffects {
  static squashJump(sprite: Phaser.GameObjects.Sprite, duration = 100): void {
    // 起跳:拉伸(scaleY↑, scaleX↓)
    scene.tweens.add({
      targets: sprite,
      scaleY: 1.2, scaleX: 0.85,
      duration: duration / 2,
      yoyo: true,
      ease: 'Quad.easeOut',
    });
  }
  static squashLand(sprite, duration = 100): void {
    // 落地:压扁(scaleY↓, scaleX↑)
    scene.tweens.add({
      targets: sprite,
      scaleY: 0.8, scaleX: 1.15,
      duration: duration / 2,
      yoyo: true,
      ease: 'Quad.easeOut',
    });
  }
}
```

### 4.4 镜头震动

```typescript
// CameraController.ts
export class CameraController {
  static shake(scene: Phaser.Scene, intensity = 0.01, duration = 200): void {
    scene.cameras.main.shake(duration, intensity);
  }
  static zoomPulse(scene: Phaser.Scene, zoom = 1.05, duration = 300): void {
    scene.cameras.main.zoomTo(zoom, duration / 2, 'Quad.easeOut');
    scene.time.delayedCall(duration / 2, () => {
      scene.cameras.main.zoomTo(1, duration / 2, 'Quad.easeIn');
    });
  }
}
```

### 4.5 朝向自动检测(借鉴 fish-tank 的 detectHeadSide)

```typescript
// 适用于需要左右翻转的角色(平台跳跃/养成)
export function detectHeadSide(texture: Phaser.Textures.Texture): number {
  // 1. 用 canvas 读取 texture 像素
  // 2. 计算每列非透明像素数(宽度曲线)
  // 3. 找最宽列 maxCol(通常在头部后方鳃部)
  // 4. maxCol < center - threshold → 头朝左(-1)
  //    maxCol > center + threshold → 头朝右(1)
  // 5. 默认 1
  return headSide;
}
```

## 五、POLISH_REQUEST.md 模板(用户可选填)

```markdown
# 效果优化需求

## 必做项(优先实现)
- [ ] B1 跳跃挤压拉伸
- [ ] B2 落地粒子
- [ ] C2 背景视差

## 可选项(时间允许再做)
- [ ] D1 得分飘字
- [ ] E2 镜头震动

## 不需要
- [x] C3 焦散(本项目非水下)
- [x] F1 朝向检测(Hero 固定朝右)

## 风格偏好
- 整体偏卡通 Q 萌,挤压幅度可以大一点(1.3×)
- 粒子用浅色(米白/淡黄)
```

## 六、浏览器自测(关键)

每实现一项效果,必须浏览器验证:

```js
(() => {
  const game = window.game;
  const scene = game?.scene?.keys?.['Game'];
  return {
    // 基础游戏未被破坏
    heroY: Math.round(scene?.hero?.y),
    blockedDown: scene?.hero?.body?.blocked?.down,
    score: scene?.score,
    obstacles: scene?.obstacles?.length,
    // 效果相关
    particles: scene?.particleManager?.particles?.length,
    cameraZoom: Math.round(game?.cameras?.main?.zoom * 100) / 100,
    heroScaleX: scene?.hero?.scaleX,
    heroScaleY: scene?.hero?.scaleY,
  };
})()
```

**判定标准**:
- 基础字段(heroY/blockedDown/score/obstacles)与优化前一致 → 未破坏玩法
- 效果字段(particles/cameraZoom/scale)有变化 → 效果生效

## 七、POLISH_REPORT.md 模板

```markdown
# {游戏名} - 效果优化报告

## 实现项
| # | 效果 | 文件 | 状态 |
|---|---|---|---|
| B1 | 跳跃挤压 | src/effects/JuiceEffects.ts | ✓ |
| B2 | 落地粒子 | src/effects/ParticleManager.ts | ✓ |

## 未实现项
| # | 原因 |
|---|---|
| C3 | 非水下场景,不适用 |

## 浏览器实测
- 玩法未破坏: heroY/blockedDown 与优化前一致 ✓
- 跳跃挤压: 起跳瞬间 scaleY 峰值 1.2 ✓
- 落地粒子: 落地后 particles>=4 ✓

## 性能影响
- 优化前 FPS: 60
- 优化后 FPS: 58(粒子数 < 50,可接受)
```

## 八、质量检查清单

- [ ] GameConfig 数值字段未被修改(对比 git diff)
- [ ] 核心玩法未被破坏(浏览器自测基础字段一致)
- [ ] 每项效果都有浏览器实测截图/数据
- [ ] 粒子数有上限(单类型 < 100,总数 < 300)
- [ ] POLISH_REPORT.md 完整
- [ ] 性能 FPS 下降 < 10

## 九、与 fish-tank-animation-polish 的方法论映射

本 skill 从 fish-tank 提炼并泛化的方法论:

| fish-tank 原始效果 | 本 skill 通用化 |
|---|---|
| Boids 群游算法 | A3 移动惯性 + 群体行为(养成类可选) |
| 水流涟漪 | B2 落地粒子 + C1 飘落粒子(通用粒子系统) |
| 鱼鳃呼吸 | A1 呼吸缩放 + A2 待机微动 |
| 光线焦散 | C3 光影焦散(水下/林间场景) |
| 温度影响行为 | C5 天气循环(环境-行为联动) |
| 鱼朝向检测 | F1 朝向自动检测+翻转 |

**fish-tank 的 4 大核心原则本 skill 全部继承**:
1. 逻辑与渲染分离 → 本 skill 效果分逻辑/渲染/粒子/镜头 4 层
2. 运行时自动适配 → F1/F2/F3 资源适配
3. 温和叠加不破坏原运动 → 核心原则第 4 条
4. 粒子统一管理 → §4.2 ParticleManager

## 十、适用范围与不适用

**适用**:
- 2D 实时游戏(跑酷/平台/飞行/养成/水族)
- Phaser / Pixi / Canvas / DOM 渲染均可

**不适用**:
- 纯文字游戏(无动画可优化)
- 回合制游戏(优化空间小,仅 A1/D3 适用)
- 已有专业美术资源的商业项目(应直接换资源而非运行时优化)
