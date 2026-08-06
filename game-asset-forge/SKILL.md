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
1. 解析 ASSET_MANIFEST.json(见 二.1 输入校验)
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

### 二.1 输入校验(解析 manifest 前一次性)

读取 `docs/ASSET_MANIFEST.json` 前必须做两步校验,失败则明确报错退出,不进入后续流程:

1. **存在性校验**:文件不存在 → 报错"ASSET_MANIFEST.json 缺失,请先调用 game-art-spec 生成",列出期望路径,直接退出
2. **JSON 解析校验**:`JSON.parse` 包 try-catch,非法 JSON → 报错"ASSET_MANIFEST.json 解析失败(行 {N}):{错误信息}",附原文片段供 game-art-spec 修复,直接退出

> **边界处理原则**:输入错误以明确报错暴露,不允许以 undefined 崩溃或静默继续(会导致后续生图引用空字段)。

---

## 三、图片生成规则

### 0. 增量 diff(执行前一次性)

**步骤 0.1:备份当前 manifest(增量更新场景必备)**

若工程中已存在 `docs/ASSET_MANIFEST.json`,先将其复制为 `docs/ASSET_MANIFEST.prev.json`(供 game-quality-gate 增量追溯使用),再进行后续 diff。首次生成时无当前 manifest,跳过本步骤。

**步骤 0.2:启动 diff**

读取新 manifest(本 skill 的输入)+ 旧 manifest(prev),启动生图前先做 diff,避免无差别全量重生成:

```
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
**调用 GenerateImage 默认并行**(单条消息多个 tool call),最多 5 个并行;**但当任务总量大(>30 张)或遇到 RequestLimitExceeded 限额错误时,必须降级为串行 + 退避 + 待重试队列**(见 十三),否则会持续饱和、永远失败。

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

## 十、格式校验与转换(详见 references)

> **本章完整内容已抽离到 `references/format-conversion-guide.md`**(问题背景、三档降级实现、决策树、一致性保证)。
>
> **何时读取**:当 manifest.format = "png-32" 且实际格式不符(读 magic number 判为 JPG 或无 alpha 通道)时。
>
> **核心流程速览**:
> 1. 读 magic number 判真实格式(PNG: `89 50 4E 47` / JPG: `FF D8 FF`)
> 2. JPG / 无 alpha → 触发转换,三档降级:sharp 阈值抠图 → ImageMagick → ffmpeg chromakey
> 3. 转换后覆盖原 path,记录到 ASSET_ISSUES.md
> 4. 全部不可用 → 警告,代码侧降级用散图(不用 atlas)

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

## 十二、卡片/对话框背景图生成规范(详见 references)

> **本章完整内容已抽离到 `references/card-bg-spec.md`**(问题背景、Prompt 编写规范、模板、尺寸要求、颜色对比度校验、失败处理、与代码侧协作)。
>
> **何时读取**:当生成需要叠加文字的背景图(UI 卡片/对话框/面板)时。
>
> **核心要点速览**:
> 1. Prompt 必须包含 4 要素:中心区域干净留白 / 装饰只留边框 / 类比说明 / 禁止内框
> 2. 生成尺寸 ≥ 3,686,400 像素,后用 sharp 缩放到目标尺寸
> 3. 颜色对比度:背景与文字亮度差 ≥ 40%(WCAG AA 简化版)

---

## 十三、生图平台限额与文件名碰撞(关键章节)

### 13.1 问题背景(实战高频)

`GenerateImage` 后端有**任务并发上限**(实测约 150 个在途任务即饱和)。当一次生图任务量大(如 78 张核心图 + 逐帧动画),会出现两类坑:
- **RequestLimitExceeded**:即使只发 1 张也会被拒(平台在途任务已饱和),不是 prompt 问题,直接重试无效。
- **文件名碰撞**:同批并行生成时若文件名相似/同名,后续帧会**互相覆盖**(如 `run_001` 被同批另一角色同帧覆盖),且工具不报错,肉眼难发现。

### 13.2 限额处理策略(降级链)

```
提交生图 → 捕获 RequestLimitExceeded?
├─ 否 → 正常入库
└─ 是 → 暂停提交,等待限额释放(平台按完成数回血,所有会话共享)
        ├─ 串行退避: 单张提交 + 间隔(sleep 2-3s)避免瞬时打满
        ├─ 失败任务入"待重试队列",限额释放后分批补(每批 ≤5)
        └─ 全部完成后统一回写 manifest + 抽查覆盖
```
**要点**:不要用"无限重试"硬顶限额——会持续饱和、永远失败。改为**记录失败 → 等释放 → 分批补**。限额是平台级(所有会话共享),与你发几张无关,需等其自然回落。

### 13.3 文件名碰撞处理(入库流水线)

**推荐:搭建一个串行 ingest 脚本**(如 `tools/ingest.mjs`),生图完成后统一:
- 用 sharp 缩放/改名到 `assets/role/{role}/{state}_{frame:03}.png`(帧序号 3 位补零,避免 `1`/`10` 排序错)
- prompt 注入时间戳/唯一后缀做**清洗**,避免同批同名
- 入库前校验目标路径已存在 → 报错(防覆盖),而非静默覆盖

**为什么串行**:并行生成返回的文件若用同一文件名,写入时后到覆盖先到。串行(或显式唯一命名)可彻底避免。

### 13.4 决策树

```
生图任务 > 30 张?
├─ 否 → 常规并行(≤5)即可
└─ 是 → 必须搭 ingest 流水线 + 限额退避策略(见 13.2/13.3)
        └─ 限额触顶 → 串行 + 待重试队列,勿硬顶
```

---

## references 使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/format-conversion-guide.md` | 格式校验与转换(§十):manifest.format = "png-32" 且实际格式不符时 |
| `references/card-bg-spec.md` | 卡片/对话框背景图生成(§十二):生成需叠加文字的背景图时 |
