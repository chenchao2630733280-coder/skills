# Sprite/Body 偏移安全(关键踩坑)

> 本文件从 game-code-forge SKILL.md 抽离,作为 Phaser 角色物理碰撞生成的踩坑规范。生成 Phaser 角色物理时按需读取。

## 十二、Sprite/Body 偏移安全(关键踩坑)

### 12.1 问题背景

ASSET_MANIFEST 声明 `size: [256, 256]` 是**期望尺寸**,但 AI 生图实际常返回 1024×1024 或 1920×1920(详见 game-asset-forge 第十章)。
若代码按期望尺寸硬编码 body offset,会导致 body 偏移到 sprite 视觉区域外,**角色看似随机下坠消失**。

### 12.2 反例(禁止)

```typescript
// 反例:假设 texture 是 256×256,硬编码 offset
body.setSize(80, 140, true);
body.setOffset(88, 58);  // ← 若 texture 实为 1920×1920,body 会跑到 sprite 左上角外
```

### 12.3 正例(推荐)

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

### 12.4 配置约束

GameConfig 里:
- **必须**保留 `scale` 字段(方案 B 用)
- **不要**写死 `bodyOffsetX/Y`(已被方案 A 取代,保留会让后人误用)
- Hero/Obstacle 等所有 Sprite 类**必须**用方案 A 或 B

### 12.5 验收(浏览器实测)

集成后必须用 browser_evaluate 验证:
- `hero.body.center.x === hero.x` 且 `hero.body.center.y === hero.y`(body 居中)
- `hero.body.blocked.down === true`(collider 生效)
- `hero.body.velocity.y === 0`(静止,未下坠)

任一不满足 → 回到 12.3 排查。

### 12.6 适用范围

本规则适用于**所有 Sprite 类**:
- Character (Hero/Enemy)
- Obstacle
- Collectible (金币/道具)
- Particle Sprite

**不适用**:
- 用 generateTexture 生成的纯色矩形(texture 尺寸 = 设计尺寸,无偏移问题)
- UI Text/Button(无 physics body)
