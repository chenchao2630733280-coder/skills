# AI 生图资源常见问题修复

> 本文件从 game-polish SKILL.md §十一抽离,作为 AI 生图资源问题的运行时修复方案。当浏览器测试发现视觉问题(白底/透明/文字不可读)时读取本文件。

---

## 11.1 问题背景

game-asset-forge 产出的 AI 生图资源在实际使用中常出现以下问题,本章节提供运行时修复方案。这些问题在资源生成阶段难以完全避免,需要在 polish 阶段通过代码或脚本修复。

---

## 11.2 9patch 纹理透明问题

**现象**:9patch 卡片/对话框纹理中心区域过度透明,导致透穿后面背景。

**原因**:`remove-white-bg.mjs` 脚本处理白底时,9patch 纹理中心的宣纸纹理被误判为白色背景而去除。

**修复方案 A:排除特定资源**(推荐)

在去白底脚本中排除 9patch 纹理:
```javascript
function shouldSkip(relPath) {
  // 9patch 纹理中心需要不透明,跳过处理
  return relPath.includes('9patch_');
}
```

**修复方案 B:用 AI 生成完整背景图替代 9patch**

直接用 AI 生成包含边框+底色的完整卡片/对话框背景图(见 game-asset-forge/references/card-bg-spec.md),代码侧改用:
```typescript
// 旧方案(9patch + 纯色底)
const bgFill = scene.add.rectangle(0, 0, w, h, 0xf5e6c8, 1);
const cardBg = new NinePatch(scene, 0, 0, w, h, '9patch_card', 40);

// 新方案(AI 生成完整背景图)
const cardBg = scene.add.image(0, 0, 'card_bg').setDisplaySize(w, h);
```

---

## 11.3 按钮 hover 纹理切换白底问题

**现象**:按钮 hover 时切换到 `btn_primary_hover` 纹理,该纹理有白底残留,视觉上出现白色闪烁。

**原因**:AI 生成的 hover 态按钮纹理同样存在白底问题,且 hover 纹理与普通态纹理风格不一致。

**修复方案:改用缩放效果替代纹理切换**(推荐)

```typescript
// 旧方案(纹理切换,有白底问题)
this.bg.on('pointerover', () => {
  this.bg.setTexture('btn_primary_hover');  // ← 白底残留
});

// 新方案(缩放效果,无纹理切换)
this.bg.on('pointerover', () => {
  this.setScale(1.05);  // ← 放大 5% 作为选中态
});
this.bg.on('pointerout', () => {
  this.setScale(1);
});
this.bg.on('pointerdown', () => {
  this.setScale(0.97);  // ← 按下缩小
});
this.bg.on('pointerup', () => {
  this.setScale(1.05);  // ← 回到 hover 态
});
```

**优点**:
- 无纹理切换,避免白底问题
- 缩放反馈更自然,符合移动端交互习惯
- 减少资源加载(hover/disabled 纹理可选)

---

## 11.4 卡片背景图文字可读性问题

**现象**:AI 生成的卡片背景图装饰过于复杂/颜色过深,叠加的文字看不清。

**修复方案 A:重新生成背景图**

按 game-asset-forge/references/card-bg-spec.md 的 prompt 规范重新生成,强调中心区域干净留白。

**修复方案 B:调整文字颜色适配背景**

```typescript
// 浅色底 → 深色文字
const title = scene.add.text(0, 0, '卡片标题', {
  color: '#8B0000',  // 深红,适配浅米黄底
});

// 深色底 → 浅色文字
const title = scene.add.text(0, 0, '卡片标题', {
  color: '#FFD700',  // 金色,适配深红底
});
```

**颜色搭配参考**:见 game-art-spec/SKILL.md §4.3(全流水线唯一源,本文件不再维护副本)。

> **注**:颜色搭配表已统一抽到 game-art-spec §4.3,本文件与 game-asset-forge/references/card-bg-spec.md §12.5 均引用该处。

---

## 11.5 角色/精灵白底残留

**现象**:角色立绘/精灵图周围有白色矩形背景,与游戏背景不融合。

**原因**:AI 生图返回 jpg(无 alpha 通道)或 png 但白底未完全去除。

**修复方案:重新处理图片像素**

```javascript
// 用 sharp 重新处理,更激进的阈值
const BG_THRESHOLD = 30;   // RGB 差值小于此值视为白色
const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
for (let i = 0; i < data.length; i += info.channels) {
  const r = data[i], g = data[i+1], b = data[i+2];
  const diff = Math.max(255-r, 255-g, 255-b);
  if (diff < 30) {
    data[i+3] = 0;  // 完全透明
  } else if (diff < 60) {
    const k = (diff - 30) / 30;
    data[i+3] = Math.round(255 * k);  // 渐变透明
  }
}
await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).png().toFile(output);
```

**注意**:阈值越激进越容易误伤角色高光(如白色鱼身),需逐图调整。

---

## 11.6 修复流程

```
1. 浏览器测试发现视觉问题(白底/透明/文字不可读)
2. 定位问题资源(通过 browser_evaluate 检查纹理)
3. 选择修复方案:
   ├─ 9patch 透明 → 排除处理 或 换 AI 完整背景图
   ├─ 按钮 hover 白底 → 改缩放效果
   ├─ 卡片文字不可读 → 重新生成背景图 或 调文字颜色
   └─ 角色白底 → 重新处理像素
4. 修复后浏览器验证
5. 记录到 POLISH_REPORT.md
```
