# 风格基线 · Q版国风修仙水墨手游

> **定位**：这是一份**通用风格基线**（Style Baseline），不绑定任何具体游戏内容。
> 任何"Q版国风修仙 / 仙侠水墨手游"类项目在调用 `game-art-spec` 生成具体 `ART_SPEC.md` 时，应**先读本基线**，再叠加项目自身的题材差异（角色名、世界观、门派设定等）。
>
> 风格标签（一句话）：**Chibi Chinese Xianxia mobile RPG ink painting style** —— Q版国风修仙水墨手游风。

---

## 0. 章节地图

| 章节 | 内容 | 是否项目相关 |
|---|---|---|
| §1 | 美术基因总览（画风标签 + 五要素拆解） | 通用 |
| §2 | 角色规范（比例 / 面部 / 服饰 / 姿态） | 通用 |
| §3 | 场景与地图规范（水墨淡彩 + 手绘大地图） | 通用 |
| §4 | 色彩规范（主辅强调阴影色板 + 用色禁忌） | 通用 |
| §5 | UI 规范（玉石 / 金描边 / 卷轴 / 木纹 / 圆角） | 通用 |
| §6 | 灵兽与坐骑规范 | 通用 |
| §7 | 装备与道具图标规范 | 通用 |
| §8 | 渲染方式与笔触约束 | 通用 |
| §9 | 尺寸约束表 | 通用 |
| §10 | 帧动画约束 | 通用 |
| §11 | 图集与格式约束 | 通用 |
| §12 | 风格一致性策略（seed / reference / 描边 / 阴影方向） | 通用 |
| §13 | AI 生图 Prompt 模板（角色 / UI / 背景 / 地图 / 完整截图） | 通用模板 |
| §14 | 负面词清单 | 通用 |
| §15 | 已知风险与降级策略 | 通用 |
| §16 | 与 game-art-spec 流水线的对接 | 流程约定 |

---

## 1. 美术基因总览

### 1.1 画风标签

| 维度 | 标签 |
|---|---|
| 中文全称 | Q版国风修仙水墨手游风 |
| 英文标签 | Chibi Chinese Xianxia mobile RPG ink painting style |
| 画种 | 2D 手绘 + 水墨淡彩 |
| 比例体系 | Q版 2.5~3 头身 |
| 渲染气质 | 可爱但不幼儿 · 国风但不写实 · 仙侠但不厚重 |

### 1.2 五要素拆解（生成时缺一不可）

不能用单一关键词「中国风修仙游戏」生成，否则会偏仙侠插画而非游戏截图。必须拆为五段：

1. **画风关键词**（Style）—— 决定笔触、质感、饱和度
2. **角色关键词**（Character）—— 决定比例、面部、服饰
3. **场景关键词**（Scene）—— 决定背景层次、留白、云雾
4. **游戏 UI 关键词**（UI）—— 决定面板、按钮、装饰材质
5. **渲染方式关键词**（Render）—— 决定光照、对比度、后期

各要素的详细约束见 §2 ~ §8。

---

## 2. 角色规范

### 2.1 比例

| 角色类型 | 头身比 | 头部占比 | 适用 |
|---|---|---|---|
| 主角 / NPC | 2.5 ~ 3 头身 | 约 35% ~ 40% | 默认 |
| 童体型角色 | 2 ~ 2.5 头身 | 约 45% | 萌系辅助角色 |
| 威严长辈 / Boss 化身 | 3.5 ~ 4 头身 | 约 28% | 略成熟，但仍属 Q 版范畴 |

**硬约束**：
- 大头小身是核心识别点，**禁止写实人体比例**（7~8 头身）
- 可爱但不是幼儿向（区别于"婴儿"质感），脸颊不画过分红润
- 日系卡通骨架 + 中国古风服饰的融合

### 2.2 面部

- 简化五官，眼睛占比大（约脸宽 1/3）
- 眼神偏清澈、少年感，**禁止成熟性感眼型**
- 眉毛细长，唇线简淡
- 国风发饰：发髻、玉簪、丝带，禁用现代发色（如荧光色）

### 2.3 服饰

| 元素 | 允许 | 禁止 |
|---|---|---|
| 领型 | 交领、直裰、对襟、道袍 | 西式立领、西装领 |
| 材质表现 | 丝绸垂感、麻布肌理 | 皮革金属盔甲、机甲面料 |
| 纹样 | 云纹、卷草、回字、八卦、缠枝 | 几何像素、赛博纹 |
| 配饰 | 玉佩、流苏、剑穗、团扇 | 手表、戒指、耳钉等现代物 |

### 2.4 姿态与表情

- 站姿多微侧 15°，避免正面死板
- 表情库（统一约定）：默认 / 微笑 / 笑脸 / 惊讶 / 严肃 / 受伤 / 战斗
- 战斗姿态需体现"剑诀 / 法印"等仙侠符号

---

## 3. 场景与地图规范

### 3.1 场景（战斗 / 关卡背景）

不是写实山水，而是 **水墨淡彩 + 留白 + 云雾**：

| 要素 | 约束 |
|---|---|
| 笔触 | 毛笔线条为主，水彩晕染为辅 |
| 留白 | 画面 ≥ 25% 留白，禁止铺满 |
| 云雾 | 必含一层淡雾，制造空间纵深 |
| 饱和度 | 低饱和，整体偏淡雅 |
| 质感 | 宣纸底纹（subtle paper texture） |
| 视角 | 2.5D 斜视或横版平视，禁用纯写实透视 |

### 3.2 大地图（World Map）

- **俯视 / 略仰视**（top-down with slight tilt）
- 手绘卷轴感：边缘做泛黄、卷边
- 元素符号化：村庄、寺庙、竹林、溪石以小图标点缀
- 路径以毛笔虚线或墨点串联
- 禁用写实卫星图、矢量地图、Google Maps 风格

### 3.3 视差层级（Parallax）

| 层 | 内容 | 模糊度 |
|---|---|---|
| Far | 远山轮廓 + 雾 | 高斯模糊 4~6px |
| Mid | 建筑 / 树木 | 不模糊或 1px |
| Near | 前景花草 / 石块 | 锐利 |

---

## 4. 色彩规范

### 4.1 主色板（Baseline Palette）

| 角色 | 色名 | HEX | 用途 |
|---|---|---|---|
| 主色 | 玉青绿 | `#7FB3A1` | 背景、UI 主面板底色 |
| 辅色 | 宣纸米白 | `#F5EFE0` | 大面积底、文字底 |
| 强调色 | 朱砂红 | `#C44536` | 重点按钮、关键提示 |
| 描边色 | 墨黑 | `#2B2B2B` | 角色线稿、UI 描边 |
| 点缀色 | 鎏金 | `#D4A537` | 高亮、稀有品质、装饰 |
| 阴影色 | 黛青 | `#3A4A4A` | 阴影、暗部 |

> 项目可在此 6 色基线上**新增 ≤ 4 色**用于门派 / 阵营区分，但不得替换基础 6 色。

### 4.2 用色禁忌

| 禁止 | 原因 |
|---|---|
| 高饱和荧光色 | 破坏水墨淡雅 |
| 西方奇幻多彩配色 | 偏离国风气质 |
| 写实光照（强高光 + 深阴影） | 偏离 2D 手绘 |
| 赛博朋克紫粉霓虹 | 风格冲突 |
| 全画面无留白 | 失去水墨呼吸感 |

---

## 5. UI 规范

### 5.1 材质语言

| 元素 | 材质 | 表现 |
|---|---|---|
| 主面板 | 玉 | 半透明青玉，内发光 |
| 边框 | 金描边 | 1~2px，暖金非亮金 |
| 按钮 | 木 + 玉 | 木底嵌玉钮，圆角 |
| 卷轴 | 宣纸 / 绢 | 用于弹窗背景 |
| 分隔线 | 墨线 | 1px，可带飞白 |

### 5.2 形态约束

- **圆角统一** R6 ~ R12，禁用直角硬边
- 弹窗以"卷轴展开 / 玉片浮现"动画进入
- 顶栏 / 底栏以木纹托底，上置玉质图标
- 按钮 hover：玉色提亮 10%，不放大
- 图标外圈：金线描边 1.5px，内填淡彩

### 5.3 字体（建议）

- 标题：思源宋体 / 方正清刻本悦宋（古韵）
- 正文：思源黑体（清晰）
- 数字：等宽宋体（装备数值）
- 禁用：现代无衬线粗体作为主标题

---

## 6. 灵兽与坐骑规范

| 要素 | 约束 |
|---|---|
| 比例 | 与主角同 Q 版体系，头身比 2 ~ 2.5 |
| 形象 | 取材《山海经》或传统瑞兽（麒麟 / 鸾鸟 / 玄龟 / 白泽），做萌化处理 |
| 表情 | 温顺或憨态，**禁止凶煞写实** |
| 材质表现 | 毛发以笔触感短线，鳞片以淡彩晕染 |
| 与主角同框 | 大小约为主角 0.6 ~ 0.8 倍，避免抢视觉 |

---

## 7. 装备与道具图标规范

| 要素 | 约束 |
|---|---|
| 尺寸 | 64×64 / 128×128 正方形 |
| 背景 | 透明（PNG-32） |
| 框架 | 外圈金描边 1.5px，内底宣纸米白 `#F5EFE0` |
| 品质色 | 白 < 绿 < 蓝 < 紫 < 橙 < 红（边框与底色微调） |
| 风格 | 工笔小写意，禁止 3D 渲染感 |
| 朝向 | 主道具居中，统一光源左上 45° |

### 品质配色（基线，可微调）

| 品质 | 边框色 | 底色微染 |
|---|---|---|
| 普通（白） | `#B0B0B0` | 无 |
| 优秀（绿） | `#7FB3A1` | 淡青 |
| 精良（蓝） | `#6B8FB0` | 淡蓝 |
| 史诗（紫） | `#9B7FB0` | 淡紫 |
| 传说（橙） | `#D4A537` | 淡金 |
| 神器（红） | `#C44536` | 淡朱 |

---

## 8. 渲染方式与笔触约束

### 8.1 笔触

- 主笔触：毛笔中锋 + 侧锋晕染
- 线稿粗细：角色轮廓 2px，细节 1px，UI 描边 1.5px
- 禁用：油画厚涂、CG 厚涂、像素马赛克

### 8.2 光照

- 光源：左上 45°，全局统一
- 阴影方向：右下
- 阴影浓度：≤ 30% 不透明，禁用纯黑死阴影
- 反光：玉面 / 金属面带 1 道淡高光

### 8.3 后期

- 整体加 5% 宣纸纹理 overlay
- 雾化：远景 + UI 边缘 5~8% 不透明白雾
- 禁用：镜头光晕 / 漫画速度线 / 赛博辉光

---

## 9. 尺寸约束表

| 类型 | 推荐尺寸 | 最大尺寸 | 透明 |
|---|---|---|---|
| 角色 / 物体帧 | 256×256 | 512×512 | 是 |
| 灵兽 | 320×320 | 512×512 | 是 |
| UI 按钮 | 200×80 | 400×160 | 是 |
| 装备图标 | 64×64 | 128×128 | 是 |
| 头像 | 128×128 | 256×256 | 是 |
| 弹窗背景 | 750×1200 | 1500×2400 | 否 |
| 全屏背景 | 750×1624 | 1500×3248 | 否 |
| 大地图 | 1500×1500 | 2048×2048 | 否 |
| 视差远景 | 750×400 | 1500×800 | 否 |
| 粒子 | 32×32 | 64×64 | 是 |

---

## 10. 帧动画约束

| 状态 | 推荐帧数 | 帧率 | 循环 |
|---|---|---|---|
| idle | 4~6 | 6 fps | 是 |
| run | 6~8 | 12 fps | 是 |
| jump | 7~10 | 15 fps | 否 |
| attack | 6~10 | 15 fps | 否 |
| skill | 8~12 | 15 fps | 否 |
| death | 8~12 | 10 fps | 否 |

**约束**：
- 同动作所有帧**同一 seed**，保证角色一致性
- 帧间像素对齐（pelvis 锚点固定）
- 第一帧生成后作为 reference image 生成后续帧

---

## 11. 图集与格式约束

### 11.1 图集

- 单图集最大 2048×2048
- 边缘 padding 2px
- 同角色所有帧 → 同一图集（如 `skin0`）
- 同页面 UI → 同一图集（如 `ui-home`）
- 背景与大地图**不打包**（独立 jpg / png）
- 单图集帧数 ≤ 30，超出拆分

### 11.2 格式

| 类型 | 格式 | 备注 |
|---|---|---|
| 透明图（角色 / UI / 图标） | PNG-32 | 含 alpha 通道 |
| 不透明大图（背景 / 地图） | JPG-80 | 体积优先 |
| 短音效 | WAV | < 2s |
| 长音频（BGM） | MP3 | 128 kbps |

> 实际格式以 `ASSET_MANIFEST.json` 的 `actualFormat` 为准（由 game-asset-forge 回写）。

---

## 12. 风格一致性策略

| 策略 | 说明 |
|---|---|
| 同角色同 seed | seed = `hash(roleName + state) % 100000`，写入 manifest |
| Reference image | 首帧生成后作 reference，生成后续帧与同角色其他状态 |
| 描边统一 | 角色轮廓 2px，UI 描边 1.5px，全项目一致 |
| 阴影方向统一 | 右下 45°，浓度 ≤ 30% |
| 色板锁定 | 项目内禁止超出基线 6 色 + 项目扩展 4 色 |
| 风格拒绝判定 | 若 AI 生图返回写实比例 / 西式奇幻 / 高饱和，立即重生成，不降级接受 |

---

## 13. AI 生图 Prompt 模板

> 模板中 `{占位符}` 由项目 ART_SPEC.md 注入具体内容，本基线只提供结构。

### 13.1 角色（单帧 / 透明背景）

```
[GAME ASSET]: {role_name} {state} animation frame {frame_idx}/{total_frames},
chibi Chinese cultivator, 2.5~3 heads tall proportion, big head small body,
cute wuxia anime style with traditional Chinese immortal cultivation aesthetic,
{costume_description} with jade accessories and traditional ornaments,
{expression}, side view 15 degrees,

hand painted with ink brush lineart, soft watercolor rendering,
low saturation pastel colors, jade green and cream tone palette,
transparent background, {width}x{height},
consistent character design, pixel-perfect alignment
```

### 13.2 灵兽 / 坐骑

```
[GAME ASSET]: {beast_name} {state} frame,
chibi mythological beast inspired by {shanjing_source},
cute 2~2.5 heads tall, gentle expression, not ferocious,
{feature_description} with traditional Chinese decorative motifs,
hand painted ink lineart, soft watercolor, low saturation,
transparent background, {width}x{height},
consistent design, pixel-perfect alignment
```

### 13.3 装备 / 道具图标

```
[GAME ICON]: {item_name} icon, {rarity} quality,
gongbi small-xieyi style, traditional Chinese craft texture,
centered, light source top-left 45 degrees,
gold outline 1.5px, cream paper background {rarity_tint},
{width}x{height}, transparent PNG, mobile RPG game asset
```

### 13.4 战斗 / 关卡背景

```
[GAME BACKGROUND]: {scene_name} scene,
hand painted Chinese ink wash landscape with soft watercolor texture,
traditional Chinese scroll painting aesthetic, misty mountains,
jade green environment, ancient paper texture,
low saturation pastel colors, at least 25% negative space,
soft brush strokes, fantasy oriental atmosphere,
{width}x{height}, no transparent, jpg
```

### 13.5 大地图

```
[GAME MAP]: cultivation world map, top-down view with slight tilt,
traditional Chinese ink painting style, hand drawn scroll aesthetic,
green bamboo forest, misty mountains, small villages, ancient temples,
river and stones, ink dotted paths connecting locations,
soft watercolor, paper texture, low saturation, aged scroll edges,
cute fantasy mobile game background,
{width}x{height}, no transparent, jpg
```

### 13.6 UI 元素

```
[GAME UI]: {element} for {page} page,
Chinese cultivation mobile RPG interface,
jade and gold decorative panel, ancient scroll style,
wood texture base, round corners R8, gold outline 1.5px,
traditional Chinese pattern ornaments,
{width}x{height}, transparent PNG, mobile game asset
```

### 13.7 完整游戏截图（含 UI）

```
A mobile Chinese cultivation RPG game screenshot,
similar to a commercial mobile game interface,

chibi immortal character standing in a fantasy world,
cute 3 heads tall proportions, big head small body,
traditional Chinese robe with jade accessories,

hand painted Chinese ink wash landscape background,
soft watercolor texture, misty mountains, jade green environment,
ancient paper texture, low saturation pastel colors, soft lighting,

mobile game UI interface, jade and gold decorative panels,
ancient Chinese scroll style buttons, wood texture,
round icons, character status panel, equipment slots at bottom,
gold coins and resources display, quest buttons,
bottom navigation bar,

professional 2D game art, clean composition, oriental atmosphere,
{width}x{height}
```

---

## 14. 负面词清单（Negative Prompt）

通用负面词，所有生图调用必须附加：

```
negative prompt:
realistic photo,
3D render,
western fantasy,
dark horror,
cyberpunk,
modern clothes,
real human proportion,
7~8 heads tall realistic body,
high contrast,
photorealistic,
oil painting,
thick CG painting,
Disney style,
pixel mosaic,
neon fluorescent colors,
lens flare,
overcrowded composition without negative space,
```

---

## 15. 已知风险与降级策略

| 风险 | 触发表现 | 降级策略 |
|---|---|---|
| AI 返回写实比例 | 7~8 头身成人 | 重生成，prompt 加强 `chibi, 3 heads tall, big head small body` |
| AI 返回西式奇幻 | 盔甲 / 哥特 / 精灵耳 | 重生成，prompt 加强 `traditional Chinese robe, ink brush lineart` |
| 高饱和荧光 | 霓虹紫粉 | 重生成，加强 `low saturation, pastel, ink wash` |
| 缺留白 | 构图铺满 | 加 `at least 25% negative space, misty` |
| 多角色同框走形 | 主角与 NPC 风格不一 | 分开生成后合成，不一次出多角色 |
| UI 缺玉石质感 | 偏扁平 | 加 `jade texture, gold outline, scroll panel` |
| 背景返回 3D 渲染 | 写实山水 | 加强 `hand painted, ink brush, watercolor, paper texture` |
| 装备图标 3D 化 | 厚涂金属感 | 加强 `gongbi small-xieyi, 2D hand drawn icon` |

> **硬规则**：风格类风险**只重生成，不接受降级**；格式类风险（jpg/png）才走 game-asset-forge 的格式转换降级。

---

## 16. 与 game-art-spec 流水线的对接

本基线是 `game-art-spec` skill 的**可选前置输入**。对接流程：

```
项目调用 game-art-spec
        │
        ├─ 1. 读 docs/PRD.md + docs/TECH_DESIGN.md
        ├─ 2. 判定画风 → 命中"Q版国风修仙水墨" → 加载本基线
        ├─ 3. 项目在此基线上叠加题材差异（角色名 / 世界观 / 门派色）
        ├─ 4. 生成 docs/ART_SPEC.md（基线约束 + 项目内容）
        ├─ 5. 生成 docs/ASSET_MANIFEST.json（每个 asset 的 prompt 引用 §13 模板）
        └─ 6. 生成 docs/AUDIO_SPEC.md（音频风格沿用国风民乐 + 电子）
```

### 16.1 项目级扩展字段（写入 ART_SPEC.md 头部）

项目应在自己的 `ART_SPEC.md` 顶部声明对基线的扩展：

```markdown
# {项目名} - 美术资源规范

## 0. 风格基线声明
- 基线：Q版国风修仙水墨手游风（references/style-baseline-chibi-xianxia-ink.md）
- 扩展色板（≤4）：门派A `#xxxxxx` / 门派B `#xxxxxx` / ...
- 比例微调：默认 2.7 头身
- 题材差异：{一句话描述本项目与基线的偏离}
```

### 16.2 资源清单 prompt 引用约定

`ASSET_MANIFEST.json` 中每个 asset 的 `prompt` 字段：
- 必须以 `[GAME ASSET]` / `[GAME UI]` / `[GAME BACKGROUND]` / `[GAME MAP]` / `[GAME ICON]` 开头
- 模板占位符（`{role_name}`、`{width}x{height}` 等）必须全部替换为具体值
- 风格段（画风 + 渲染 + 颜色）直接复用本基线 §13 对应模板的风格描述
- 不允许出现裸 prompt（如"好看的国风角色"）

### 16.3 风格拒绝自动判定

`game-asset-forge` 在生成后应对照 §15 风险表做自动检查：
- 若返回写实比例 / 西式奇幻 / 高饱和 → 自动重生成（最多 3 次）
- 3 次仍失败 → 标记到 `ASSET_MANIFEST.json` 的 `conversionNote` 字段并提示人工介入
