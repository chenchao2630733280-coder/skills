# 卡片/对话框背景图生成规范

> 本文件从 game-asset-forge SKILL.md §十二抽离,作为卡片/对话框背景图生成的详细规范。当生成需要叠加文字的背景图(UI 卡片/对话框/面板)时读取本文件。

---

## 12.1 问题背景

AI 生成的卡片/对话框背景图常出现两类问题导致叠加文字看不清:
- **装饰侵入文字区域**:AI 会在整张图上铺装饰纹理,中心区域不干净,叠加文字后不可读
- **对话框内框问题**:对话框生成了比文本区域小的内框装饰线,文字溢出框外
- **颜色对比不足**:深色背景配深色文字、浅色背景配浅色文字,都导致不可读

这是**高频坑**,所有需要叠加文字的背景图(UI 卡片/对话框/面板)生成时必须遵守本章规范。

---

## 12.2 Prompt 编写规范(强制)

生成卡片/对话框背景图时,prompt **必须**包含以下要素:

### 要素 1:明确中心区域干净留白
```
The ENTIRE center area is pure clean {color} solid color with ABSOLUTELY NO patterns, NO decorations, NO textures
```

### 要素 2:装饰只留在边框
```
Only the outer border (about {N}px wide on each side) has decorative elements
```

### 要素 3:类比说明帮助 AI 理解
```
Think of it as a blank rice paper with an ornate frame
```

### 要素 4:禁止内框(对话框专用)
```
NO inner frames, NO decorative lines inside, NO inner rectangles
```

---

## 12.3 Prompt 模板

**卡片背景(角色卡/信息卡等华丽风格)**:
```
Chinese traditional {theme} card background, vertical portrait layout.
The ENTIRE center area is pure clean {bgColor} solid color with ABSOLUTELY NO patterns, NO decorations, NO textures - completely blank for text overlay.
Only the outer border (about {N}px wide on each side) has decorative elements: {borderStyle}.
The border is the ONLY decorated area.
Think of it as a blank rice paper scroll with an ornate frame.
Flat, no depth, no shadows. Game UI texture.
```

**对话框背景(干净简约风格)**:
```
Chinese ink wash style dialog box background, horizontal landscape layout.
The ENTIRE center area is pure clean {bgColor} solid color with ABSOLUTELY NO inner frames, NO decorative lines inside, NO patterns - completely blank solid color for text overlay.
Only a simple outer border (about {N}px) with subtle ink brush strokes.
No inner rectangles or frames. Flat, clean, minimal. Game UI texture.
```

---

## 12.4 尺寸要求

GenerateImage 要求最小 3,686,400 像素(约 1920x1920)。卡片/对话框目标尺寸较小,策略:

| 资源类型 | 目标尺寸 | 生成尺寸(满足最小像素) |
|---|---|---|
| 竖向卡片 | 520x640 | 1720x2150 或更大 |
| 横向对话框 | 520x320 | 2620x1680 或更大 |
| 方形面板 | 400x400 | 1920x1920 |

生成后用 sharp 缩放到目标尺寸:
```javascript
await sharp(input).resize(targetW, targetH).jpeg({ quality: 90 }).toFile(output);
```

---

## 12.5 颜色对比度校验

背景图生成后,必须校验文字可读性。**颜色对比度参考表见 game-art-spec/SKILL.md §4.3**(全流水线唯一源,不再本处维护副本)。

**规则**:背景与文字的亮度差应 >= 40%(WCAG AA 标准简化版)。

> **注**:颜色对比度参考表已统一抽到 game-art-spec §4.3,本文件与 game-polish/references/asset-fix-recipes.md §11.4 均引用该处。

---

## 12.6 失败处理

| 失败场景 | 处理 |
|---|---|
| 中心区域仍有装饰 | prompt 中重复强调 "ABSOLUTELY NO patterns in center",重新生成 |
| 对话框有内框 | prompt 中添加 "NO inner frames, NO inner rectangles",重新生成 |
| 文字看不清 | 调整文字颜色适配背景(见 12.5),或重新生成浅色底背景 |
| 尺寸不够报错 | 用更大尺寸生成后 sharp 缩放(见 12.4) |

---

## 12.7 与代码侧的协作

背景图生成完成后,通知 game-code-forge:
- 卡片背景图用 `load.image` 加载(非 atlas)
- 代码侧用 `add.image(x, y, 'card_bg_key').setDisplaySize(w, h)` 显示
- 文字叠加在背景图之上,颜色按 12.5 表选择
- **不要**再叠加 9patch 或纯色 rectangle 作为底色(背景图已包含完整底色+边框)
