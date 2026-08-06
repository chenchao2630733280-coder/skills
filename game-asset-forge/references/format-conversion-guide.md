# 格式校验与转换指南

> 本文件从 game-asset-forge SKILL.md §十抽离,作为图片格式校验与转换的详细规范。当 manifest.format = "png-32" 且实际格式不符时读取本文件。

---

## 10.1 问题背景

GenerateImage 工具常**忽略 prompt 中的 "transparent PNG" 要求**,直接返回 jpg:
- 现象:文件扩展名是 .jpg 或虽为 .png 但无 alpha 通道(纯白底)
- 影响:角色/UI 带方形背景,无法正常打包图集,代码侧 anims 看起来像贴方块
- 这是**高频坑**,所有 role/ui/effect 资源必须经过本章节处理

---

## 10.2 转换流程

```
对每张要求透明的资源(path 以 .png 结尾 且 manifest.format = "png-32"):
  1. 读文件头判断真实格式(magic number)
     - PNG: 89 50 4E 47
     - JPG: FF D8 FF
  2. 若实为 JPG / 无 alpha 通道 → 触发转换
  3. 转换后覆盖原 path(保持文件名不变)
  4. 记录到 ASSET_ISSUES.md
```

---

## 10.3 转换实现(三档降级)

### 档 1:sharp(首选) —— 纯 Node、跨平台、无系统依赖

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

### 档 1.5:sharp + 阈值 + 饱和度抠图(推荐实战) —— 把低饱和度浅色背景改透明,保留高饱和度角色

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

### 档 2:ImageMagick(系统级)

```bash
magick input.jpg -fuzz 20% -transparent white output.png
# 复杂背景用 chroma key
magick input.jpg -fill none -draw "matte 0,0 floodfill" output.png
```

### 档 3:ffmpeg chromakey(系统级)

```bash
ffmpeg -i input.jpg -filter_complex "colorkey=white:0.3:0.2" output.png
```

---

## 10.4 决策树

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

---

## 10.5 一致性保证

- 同角色 4 帧必须用**相同的转换参数**(同阈值、同背景色),否则帧间抖动
- 转换后做一次视觉抽检:首帧和末帧的角色外接矩形尺寸差应 < 5%
- 若抽检不一致 → 全部 4 帧重新走档 1.5,记录到 ASSET_ISSUES.md
