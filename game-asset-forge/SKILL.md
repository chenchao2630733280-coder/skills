---
name: "game-asset-forge"
description: "AI 游戏生成流水线阶段 4a。读取 ASSET_MANIFEST.json,执行 AI 生图、图集打包、音频占位,产出 assets/ 目录。当被 game-forge-master 调度到本阶段,或用户要'生成游戏美术资源/切图打包'时调用。"
---

# Game Asset Forge — 资源锻造

本 skill 是 AI 游戏生成流水线的**阶段 4a**(与 game-code-forge 并行),职责是消费 ASSET_MANIFEST.json,**逐个生成图片资源**、打包图集、产出音频占位,输出 `assets/` 目录。

---

## 一、输入与输出

**输入**(必读):
- `docs/ASSET_MANIFEST.json`
- `docs/ART_SPEC.md`(取颜色调板、风格策略)

**输出**(固定路径):
- `assets/role/{role}/{state}_{frame:03}.png`
- `assets/ui/{page}/{element}.png`
- `assets/bg/{scene}_{variant}.png`
- `assets/atlases/{atlas_id}.png` + `.json`
- `assets/audio/*.wav` / `*.mp3`
- `docs/ASSET_ISSUES.md`(失败清单,如有)

---

## 二、执行流程

```
0. 依赖初始化(见 二.0)
1. 解析 ASSET_MANIFEST.json
2. 创建目录结构
3. 生成图片资源(按 category 分组)
   ├─ role:逐帧生成,同角色用首帧作 reference
   ├─ ui:逐个生成
   └─ bg:逐个生成
3.5 格式校验与转换(见 十)         ← 关键:AI 生图常返回 jpg,需转 png 透明
4. 打包图集
   ├─ 优先用 TexturePacker CLI
   └─ 失败降级用 spritesheet-js(已在本工程 devDependencies)
5. 处理音频
   ├─ 默认策略:复制静音占位文件
   └─ fallback=silent-1s 时直接复制 _placeholder.wav
6. 回写 ASSET_MANIFEST.json 的 actualFormat(见 十一)
7. 输出 ASSET_ISSUES.md(失败清单)
8. 输出汇总报告
```

### 二.0 依赖初始化(执行前一次性)

确认以下工具/依赖就绪,缺失则补装:

```bash
# 1. spritesheet-js(图集打包降级路径) - 加到工程 devDependencies
npm install --save-dev spritesheet-js

# 2. sharp(PNG 转换首选,纯 Node 无系统依赖) - 全局或本工程
npm install --save-dev sharp

# 3. 可选:ffmpeg / ImageMagick(系统级,sharp 不可用时的降级)
ffmpeg -version 2>nul
magick -version 2>nul
```

**说明**:
- TexturePacker CLI 是商用软件,默认未装 → 直接走 spritesheet-js
- sharp 是图集/格式转换的首选(跨平台、无系统依赖)
- ffmpeg 用于音频占位生成与视频转 GIF(若需)

---

## 三、图片生成规则

### 0. 增量 diff(执行前一次性)

若工程中已存在上一版 `ASSET_MANIFEST.json`(命名如 `ASSET_MANIFEST.prev.json`),启动生图前先做 diff,避免无差别全量重生成:

```
读取新 manifest(本 skill 的输入)+ 旧 manifest(prev)
以 id 为主键逐条对比:
  ├─ id 相同 + contentHash 相同        → 跳过,复用旧文件(actual* 字段直接继承)
  ├─ id 相同 + contentHash 不同        → 重生成该资源
  ├─ 新 id + predecessorId=null         → 新增,生图
  ├─ 新 id + predecessorId 命中旧 id    → 改名,移动旧文件到新 path(不生图),回写 actualPath
  └─ 旧 id 在新表消失                  → 标记为已删除,提示清理(默认保留备份)
```

**字段读取约定**:
- `contentHash` / `predecessorId` 由 game-art-spec 写入,本 skill 只读不写
- 移动文件后必须回写新 manifest 的 `actualPath`
- 若 `predecessorId` 命中但旧文件已不存在 → 降级为重生成(等价于新增)
- 首次生成(无 prev manifest)时全部走生图,等价于全量

**输出**:diff 完成后,生图任务清单 = [重生成] + [新增] + [改名后文件缺失降级],其余跳过。后续 §三.1 ~ §三.5 仅对任务清单执行。

### 1. 调用 GenerateImage 工具
每个**任务清单内**的图片资源,调用 `GenerateImage`:
- prompt:取 manifest 的 `prompt` 字段
- path:取 manifest 的 `path` 字段(相对工程根)
- image_size:按 manifest 的 `size` 转换为 GenerateImage 支持的格式

### 2. image_size 映射
manifest 的 size 是 [width, height],GenerateImage 支持预设或自定义:
- [256, 256] → `square_hd`
- [200, 80] → `"{width}x{height}"` 自定义
- [750, 1624] → `portrait_4_3` 或自定义

### 3. 风格一致性策略(关键)

逐帧动画是本 skill 最大难点。策略:

**步骤 A**:对每个角色,先生成首帧
```
生成 skin0_run_001.png,固定 seed=manifest.seed
```

**步骤 B**:用首帧作 image reference 生成后续帧
```
image_paths=["assets/role/skin0/run_001.png"]
prompt="参考首帧角色设计,生成奔跑第2帧,腿前伸,..."
```

**步骤 C**:生成完整后做视觉一致性检查
- 颜色采样:每帧主色应在调板 ±10% 范围
- 比例检查:角色外接矩形宽高一致(±5%)
- 不一致则重新生成(最多 3 次)

### 4. 失败处理

| 失败场景 | 处理 |
|---|---|
| GenerateImage 报错 | 重试 2 次 |
| 重试仍失败 | 用占位图(纯色 + 文字标识) |
| 尺寸不符 | 警告但保留 |
| 风格不一致 | 用 reference 重生成 1 次 |
| **返回 jpg 但要 png**(高频) | 见第十章格式转换 |

**占位图生成**(用代码生成,不调 AI):
```typescript
// 256x256 红色占位 + "skin0-run-1" 白字
function placeholder(name: string, size: [number, number], color: string)
```
可用 `canvas` npm 包或直接写 PNG。

### 5. 并行生成
**调用 GenerateImage 时必须并行**(单条消息多个 tool call),最多 5 个并行。

---

## 四、图集打包规则

### 1. 优先 TexturePacker CLI
```bash
TexturePacker --format phaser-json-array \
  --sheet assets/atlases/{atlas_id}.png \
  --data assets/atlases/{atlas_id}.json \
  --max-size 2048 \
  --padding 2 \
  assets/role/{role}/*.png
```

### 2. 检测 TexturePacker 是否安装
```bash
TexturePacker --version
```
失败则降级。

### 3. 降级用 spritesheet-js
```bash
npm install spritesheet-js --save-dev
npx spritesheet-js --format=phaser-json-array \
  --padding 2 \
  --max-width 2048 --max-height 2048 \
  --out assets/atlases/ \
  assets/role/{role}/*.png
```

### 4. 进一步降级
若 spritesheet-js 也失败,**直接用散图**,Phaser 可直接 load 单图,只是 DrawCall 高一些。

---

## 五、音频处理规则

### 1. 默认策略(静音占位)
所有 manifest 的 `audio` 项,若 `fallback` 字段为 `silent-1s` 或未指定:

```bash
# 准备静音占位
ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 1 assets/audio/_placeholder.wav
ffmpeg -i assets/audio/_placeholder.wav assets/audio/_placeholder.mp3

# 复制到每个目标路径
cp assets/audio/_placeholder.wav assets/audio/sfx_jump.wav
cp assets/audio/_placeholder.mp3 assets/audio/bgm_home.mp3
```

若 ffmpeg 不可用,用 `wav` npm 包生成 1 秒静音 wav,mp3 暂用 wav 替代。

### 2. AI 生成策略(用户明确要求时)
- 短音效(<2s):可用 AudioCraft / ElevenLabs API
- 长 BGM:建议人工,因 AI 音乐质量不稳定

### 3. 检测 ffmpeg
```bash
ffmpeg -version
```
失败则用 Node 脚本生成静音 wav(直接写 WAV 头 + 静音 PCM 数据)。

---

## 六、ASSET_ISSUES.md 模板

失败时必须产出:

```markdown
# 资源生成问题清单

生成时间:{ISO timestamp}
总资源数:{N}
成功:{成功数}
失败:{失败数}
占位替代:{占位数}

## 失败清单

| ID | 路径 | 失败原因 | 当前状态 | 建议处理 |
|---|---|---|---|---|
| skin2-jump-3 | assets/role/skin2/jump_003.png | GenerateImage 报错 | 占位图 | 人工后补 |
| bg-game-parallax | assets/bg/game_parallax_far.png | 尺寸过大 | 跳过 | 拆分生成 |

## 待人工后补
- [ ] skin2-jump-3 替换真实图
- [ ] bg-game-parallax 拆分或缩放
```

---

## 七、生成顺序与并行

按依赖关系排序:
1. 先生成所有 role 帧序列(每个角色内部串行,不同角色并行)
2. 再生成 UI 图(可全并行)
3. 再生成背景图(可全并行)
4. 所有图就绪后打包图集
5. 同时(无依赖)处理音频

**并行约束**:单次消息最多 5 个 GenerateImage 调用。

---

## 八、汇总报告

完成后输出简报:

```
资源生成完成:
- 图片:{成功}/{失败}/{占位} 共 {总} 张
- 图集:{打包成功} 个(散图降级 {N} 个)
- 音频:{静音占位} 个
- 失败清单见 docs/ASSET_ISSUES.md
- 下一步可调用 game-integrate 集成构建
```

---

## 九、质量检查清单

- [ ] manifest 中每条资源都有对应文件
- [ ] 角色帧首帧作 reference 生成了后续帧
- [ ] 图集 .json 帧映射正确
- [ ] 音频文件存在且非 0 字节
- [ ] 占位图带文字标识(易识别)
- [ ] 失败项已写入 ASSET_ISSUES.md
- [ ] 汇总报告数字与实际一致
- [ ] 透明资源实际为 PNG 且 alpha 通道非空(见 十)
- [ ] ASSET_MANIFEST.json 已回写 actualFormat(见 十一)

---

## 十、格式校验与转换(关键章节)

### 10.1 问题背景

GenerateImage 工具常**忽略 prompt 中的 "transparent PNG" 要求**,直接返回 jpg:
- 现象:文件扩展名是 .jpg 或虽为 .png 但无 alpha 通道(纯白底)
- 影响:角色/UI 带方形背景,无法正常打包图集,代码侧 anims 看起来像贴方块
- 这是**高频坑**,所有 role/ui/effect 资源必须经过本章节处理

### 10.2 转换流程

```
对每张要求透明的资源(path 以 .png 结尾 且 manifest.format = "png-32"):
  1. 读文件头判断真实格式(magic number)
     - PNG: 89 50 4E 47
     - JPG: FF D8 FF
  2. 若实为 JPG / 无 alpha 通道 → 触发转换
  3. 转换后覆盖原 path(保持文件名不变)
  4. 记录到 ASSET_ISSUES.md
```

### 10.3 转换实现(三档降级)

**档 1:sharp(首选)** —— 纯 Node、跨平台、无系统依赖

```typescript
// scripts/convert-to-png.ts —— 接受输入路径数组,统一转透明 PNG
import sharp from 'sharp';

async function toTransparentPng(input: string, output: string, bg: { r: number; g: number; b: number }) {
  // 把背景色(白底/黑底)抠成透明,加 alpha 通道
  await sharp(input)
    .flatten({ background: bg })           // 若本身无 alpha,先合成
    .removeAlpha()                          // 去掉旧 alpha
    .raw()                                  // 拿像素 buffer
    .toBuffer({ resolveWithObject: true })
    .then(({ data, info }) => {
      // 简化方案:直接生成带 alpha 的 png,背景色阈值替为透明
      // 复杂场景建议用 chroma key,见档 2
    });
  // 实战推荐:sharp 直接 chroma key 不便,改用阈值方案
  await sharp(input)
    .modulate({ brightness: 1 })
    .png({ palette: true, colors: 32, quality: 80 })
    .toFile(output);
}
```

**档 1.5:sharp + 阈值 + 饱和度抠图(推荐实战)** —— 把低饱和度浅色背景改透明,保留高饱和度角色

```typescript
import sharp from 'sharp';

// 实战调参(PoC 验证):
//   - 阈值 245 只能抠纯白,AI 生图常返回浅灰背景(RGB 220-245)会漏抠
//   - 阈值 200 + 饱和度判断(max-min<25)能覆盖浅灰背景,且不误伤角色高光
const BG_THRESHOLD = 200;   // RGB 均 > 此值视为候选背景
const SAT_THRESHOLD = 25;   // max-min < 此值视为低饱和度(灰色系)
const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
for (let i = 0; i < data.length; i += info.channels) {
  const r = data[i], g = data[i + 1], b = data[i + 2];
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const sat = max - min;
  if (r > BG_THRESHOLD && g > BG_THRESHOLD && b > BG_THRESHOLD && sat < SAT_THRESHOLD) {
    data[i + 3] = 0;  // alpha 置 0
  }
}
await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } })
  .png().toFile(output);
```

**为什么加饱和度判断**:浅橙/浅蓝高光 RGB 可能都 > 200,但 max-min 较大(有色);浅灰背景 RGB 都 > 200 且 max-min 很小(无色)。加饱和度判断能区分两者,避免误抠角色高光。

**PoC 实测数据**(阈值 200 + 饱和度 25):
| 帧 | 转换前透明% | 转换后透明% |
|---|---|---|
| run_001 | 10.2 | 80.5 |
| run_002 | 9.5 | 83.7 |
| run_003 | 77.3 | 79.2 |
| run_004 | 72.8 | 75.8 |

**档 2:ImageMagick(系统级)**

```bash
magick input.jpg -fuzz 20% -transparent white output.png
# 复杂背景用 chroma key
magick input.jpg -fill none -draw "matte 0,0 floodfill" output.png
```

**档 3:ffmpeg chromakey(系统级)**

```bash
ffmpeg -i input.jpg -filter_complex "colorkey=white:0.3:0.2" output.png
```

### 10.4 决策树

```
manifest.format = png-32?
├─ 否 → 跳过(背景图直接用 jpg)
└─ 是 → 读 magic number
        ├─ 真为 PNG 且有 alpha 通道 → 通过
        └─ 实为 jpg / 无 alpha → 触发转换
            ├─ sharp 可用 → 档 1.5(阈值抠图)
            ├─ sharp 不可用 + magick 可用 → 档 2
            ├─ sharp 不可用 + ffmpeg 可用 → 档 3
            └─ 全部不可用 → 警告并写入 ASSET_ISSUES.md
                            代码侧降级用散图(不用 atlas)
```

### 10.5 一致性保证

- 同角色 4 帧必须用**相同的转换参数**(同阈值、同背景色),否则帧间抖动
- 转换后做一次视觉抽检:首帧和末帧的角色外接矩形尺寸差应 < 5%
- 若抽检不一致 → 全部 4 帧重新走档 1.5,记录到 ASSET_ISSUES.md

---

## 十一、manifest 回写

### 11.1 为什么回写

ASSET_MANIFEST.json 的 `format` 字段是**期望格式**(由 game-art-spec 写入)。
game-asset-forge 完成后,实际格式可能与期望不符(如 jpg 转成 png、或转失败保留 jpg)。
必须回写真实状态,让下游 skill(代码生成)和验收(ASSET_ISSUES)读到的是真相。

### 11.2 回写字段

在每条 asset 对象追加 2 个字段:

```json
{
  "id": "hero-run-1",
  "format": "png-32",                   // 期望(不变)
  "actualFormat": "png-32",             // 实际格式(回写)
  "actualPath": "assets/role/hero/run_001.png",  // 实际路径(若 game-asset-forge 改名或按 predecessorId 移动旧文件则回写)
  "converted": true,                    // 是否经过格式转换
  "conversionNote": "jpg→png via sharp threshold 245"  // 转换备注
}
```

### 11.3 回写时机

- 全部资源生成 + 转换完成后,统一一次回写
- 用 Node 脚本读 manifest → 改字段 → 写回(保留缩进 2 空格)
- 回写后必须通过 JSON schema 校验

### 11.4 代码侧消费

game-code-forge 读 manifest 时:
- 优先读 `actualFormat`(若存在),否则回退 `format`
- 优先读 `actualPath`(若存在),否则回退 `path`
- 若 `actualFormat` 仍是 jpg 而 `format` 是 png-32 → 走散图降级,不用 atlas


---

## 十二、卡片/对话框背景图生成规范(关键章节)

### 12.1 问题背景

AI 生成的卡片/对话框背景图常出现两类问题导致叠加文字看不清:
- **装饰侵入文字区域**:AI 会在整张图上铺装饰纹理,中心区域不干净,叠加文字后不可读
- **对话框内框问题**:对话框生成了比文本区域小的内框装饰线,文字溢出框外
- **颜色对比不足**:深色背景配深色文字、浅色背景配浅色文字,都导致不可读

这是**高频坑**,所有需要叠加文字的背景图(UI 卡片/对话框/面板)生成时必须遵守本章规范。

### 12.2 Prompt 编写规范(强制)

生成卡片/对话框背景图时,prompt **必须**包含以下要素:

**要素 1:明确中心区域干净留白**
```
The ENTIRE center area is pure clean {color} solid color with ABSOLUTELY NO patterns, NO decorations, NO textures
```

**要素 2:装饰只留在边框**
```
Only the outer border (about {N}px wide on each side) has decorative elements
```

**要素 3:类比说明帮助 AI 理解**
```
Think of it as a blank rice paper with an ornate frame
```

**要素 4:禁止内框(对话框专用)**
```
NO inner frames, NO decorative lines inside, NO inner rectangles
```

### 12.3 Prompt 模板

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

### 12.4 尺寸要求

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

### 12.5 颜色对比度校验

背景图生成后,必须校验文字可读性:

| 背景底色 | 文字颜色 | 适用场景 |
|---|---|---|
| 浅米黄(#F5E6C8) | 深红(#8B0000)/深灰(#444444)/深棕(#5a0a12) | 水墨风卡片 |
| 深红(#2a1810) | 金色(#FFD700)/白色(#FFFFFF) | 宫廷风卡片 |
| 浅灰(#E8E8E8) | 深灰(#333333)/黑色(#000000) | 现代风面板 |

**规则**:背景与文字的亮度差应 >= 40%(WCAG AA 标准简化版)。

### 12.6 失败处理

| 失败场景 | 处理 |
|---|---|
| 中心区域仍有装饰 | prompt 中重复强调 "ABSOLUTELY NO patterns in center",重新生成 |
| 对话框有内框 | prompt 中添加 "NO inner frames, NO inner rectangles",重新生成 |
| 文字看不清 | 调整文字颜色适配背景(见 12.5),或重新生成浅色底背景 |
| 尺寸不够报错 | 用更大尺寸生成后 sharp 缩放(见 12.4) |

### 12.7 与代码侧的协作

背景图生成完成后,通知 game-code-forge:
- 卡片背景图用 `load.image` 加载(非 atlas)
- 代码侧用 `add.image(x, y, 'card_bg_key').setDisplaySize(w, h)` 显示
- 文字叠加在背景图之上,颜色按 12.5 表选择
- **不要**再叠加 9patch 或纯色 rectangle 作为底色(背景图已包含完整底色+边框)

