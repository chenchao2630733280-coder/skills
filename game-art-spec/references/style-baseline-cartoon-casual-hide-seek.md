# 风格基线 · 3D卡通休闲躲猫猫手游风

> **定位**：这是一份**通用风格基线**（Style Baseline），不绑定任何具体游戏内容。
> 任何"3D 卡通休闲 / 躲猫猫 / 变装隐藏 / 玩具世界"类项目在调用 `game-art-spec` 生成具体 `ART_SPEC.md` 时，应**先读本基线**，再叠加项目自身的题材差异（角色物种、地图主题、敌人形象等）。
>
> 风格标签（一句话）：**3D Cartoon Casual Hide-and-Seek mobile game style** —— 3D卡通休闲躲猫猫手游风。
>
> **适用维度声明**（供 SKILL.md 基线表命中判定）：
> - 渲染维度：**3D**
> - 推荐引擎：**Unity**（2022.3 LTS，URP 渲染管线，移动端 / 抖音小游戏）或 **Godot 4**（StandardMaterial3D + Skeleton3D，移动端 / 桌面）
> - 画风族：**卡通可爱 / Q版休闲 / 明亮圆润**
> - 平台：**移动端**（小屏幕清晰优先）

---

## 0. 章节地图

| 章节 | 内容 | 维度 |
|---|---|---|
| §1 | 美术基因总览（画风标签 + 五要素拆解 + 参考比例） | 通用 |
| §2 | 角色规范（比例 / 头部 / 眼睛 / 嘴巴 / 四肢 / 尾巴） | 通用 |
| §3 | 场景与地图规范（玩具世界 / 构图比例 / 隐藏物分层） | 通用 |
| §4 | 色彩规范（高饱和明亮色板 + 禁用色） | 通用 |
| §5 | UI 规范（大圆弹性 / 按钮尺寸 / 圆体字） | 通用 |
| §6 | 变身 / 隐藏系统规范（三阶段 + 时间） | 通用 |
| §7 | 敌人规范（搞笑猎人 / 比例 / 动画） | 通用 |
| §8 | 道具规范（轮廓 / 纯净 / 可识别） | 通用 |
| §9 | 渲染与性能（手机优化 / ASTC / 简单几何） | 3D 专用 |
| §10 | 尺寸约束表（3D 资产 + 贴图规格） | 3D 专用 |
| §11 | 动画约束（基础动作列表 + 时长） | 通用 |
| §12 | 特效规范（粒子 / 成功 / 失败） | 通用 |
| §13 | 商业化规范（皮肤三档体系） | 通用 |
| §14 | 引擎资产规范（Unity / Godot 4 命名前缀 / 目录 / 贴图压缩 / 分支对接） | 3D 专用 |
| §15 | 风格一致性策略 | 通用 |
| §16 | AI 生图 Prompt 模板（角色 / 场景 / 道具 / UI / 敌人） | 通用模板 |
| §17 | 负面词清单 | 通用 |
| §18 | 已知风险与降级策略 | 通用 |
| §19 | 与 game-art-spec 流水线的对接 | 流程约定 |

---

## 1. 美术基因总览

### 1.1 画风标签

| 维度 | 标签 |
|---|---|
| 中文全称 | 3D卡通休闲躲猫猫手游风 |
| 英文标签 | 3D Cartoon Casual Hide-and-Seek mobile game style |
| 渲染维度 | 3D（URP / Stylized，或 Godot 4 StandardMaterial3D） |
| 比例体系 | Q版（2~2.5 头身，主角头部占比大） |
| 渲染气质 | 明亮 · 圆润 · 夸张 · 简单 · 亲和 |

### 1.2 五要素拆解（生成时缺一不可）

1. **画风关键词**（Style）—— 卡通、可爱、明亮、圆润、夸张、简单
2. **角色关键词**（Character）—— Q版、大眼、柔软、表情丰富
3. **场景关键词**（Scene）—— 玩具世界、温暖、安全、儿童视角
4. **游戏 UI 关键词**（UI）—— 大、圆、弹性、强反馈
5. **渲染方式关键词**（Render）—— 3D stylized、soft lighting、bright colors、mobile optimized

### 1.3 视觉参考比例

```
70% 可爱休闲游戏（糖豆人 / 宝可梦角色亲和力）
20% 搞笑动画（夸张表情与笑点）
10% 益智隐藏游戏（躲猫猫识别度）
```

### 1.4 风格识别"一眼感"

- 第一眼**可爱**（角色亲和力，不攻击感）
- 第二眼**搞笑**（夸张表情，非严肃）
- 第三眼**想玩**（明亮色彩激发愉悦）

---

## 2. 角色规范

### 2.1 比例（主角）

| 部位 | 占比 | 单位（高度 1.0 基准，Unity / Godot 4 均为米） |
|---|---|---|
| 头 | 45% | 0.45 |
| 身体 | 35% | 0.35 |
| 尾巴 / 下肢 | 20% | 0.20 |

**硬约束**：
- Q版大头小身是核心识别点，**禁止写实比例**
- 头身比 2 ~ 2.5，禁止 7~8 头身
- 圆润造型，**禁止尖锐 / 凶猛 / 写实生物比例**

### 2.2 头部

| 要素 | 允许 | 禁止 |
|---|---|---|
| 轮廓 | 大、圆、柔软 | 尖锐、棱角、凶猛 |
| 材质表现 | 哑光磨砂、柔软感 | 真实鳞片、硬壳 |

### 2.3 眼睛（最重要资产）

- 占头部 35% ~ 40%
- 黑色大瞳孔 + 白色高光（高光 ≥ 2 个）
- 可左右独立移动（动画支持）
- 眼神清澈、好奇，**禁止成熟 / 性感 / 凶狠眼型**
- Idle 动画：左右观察

### 2.4 嘴巴（表情库，至少 8 种）

| 状态 | 用途 |
|---|---|
| 开心 | 胜利 / 默认 |
| 紧张 | 即将被发现 |
| 害怕 | 危险临近 |
| 惊讶 | 突发事件 |
| 得意 | 躲避成功 |
| 哭泣 | 被抓住 |
| 生气 | 罕见触发 |
| 偷笑 | 恶作剧 |

### 2.5 四肢

- 圆形吸盘脚 / 肉垫脚，**禁止真实爪子 / 利爪**
- 短小可爱，动作带弹性（挤压拉伸）

### 2.6 尾巴（如有）

- 长、卷曲、有弹性
- Idle：左右摆动；移动：跟随晃动；开心：可形成爱心等符号

---

## 3. 场景与地图规范

### 3.1 场景构图比例

| 元素 | 占比 |
|---|---|
| 场景（可交互 / 躲藏载体） | 70% |
| 隐藏物（玩家变装目标） | 20% |
| 纯装饰 | 10% |

### 3.2 场景主题（玩具世界方向）

- 儿童房 / 玩具工厂 / 糖果乐园 / 积木城堡等温暖安全场景
- **禁止**：写实战场、恐怖黑暗、赛博都市、末日废墟

### 3.3 场景尺寸（引擎基准，Unity 单位 / Godot 4 米）

| 项目 | 推荐尺寸 |
|---|---|
| 单地图 | 20×20 单位 |
| 高度 | 3 ~ 5 单位 |
| 隐藏物数量 | 30 ~ 60 个 / 地图 |

### 3.4 隐藏物分层（难度递进）

| 难度 | 特征 | 示例方向 |
|---|---|---|
| A 简单 | 颜色明显、形状独立 | 水果、球、积木 |
| B 中等 | 形状相似、需辨识 | 玩偶、靠垫、书本 |
| C 困难 | 环境融合、考验眼力 | 装饰品、植物、摆件 |

> 具体物件由项目 ART_SPEC 注入，本基线只提供分层规则。

---

## 4. 色彩规范

### 4.1 主色板（Baseline Palette）

| 角色 | 色名 | HEX | RGB | 用途 |
|---|---|---|---|---|
| 主色 | 草绿 | `#65D75A` | 101/215/90 | 主角基础色 |
| 辅色 | 活力黄 | `#FFD84D` | — | 奖励、金币、UI 高亮 |
| 辅色 | 天空蓝 | `#5AC8FA` | — | 背景、按钮 |
| 强调色 | 活力橙 | `#FF914D` | — | 危险、提示 |
| 点缀色 | 粉红 | `#FF7EB6` | — | 装饰、女性化皮肤 |
| 阴影色 | 暖灰 | `#8A8A8A` | — | 阴影（非纯黑） |

> 项目可在此 6 色基线上**新增 ≤ 4 色**用于皮肤 / 主题区分，但不得替换基础 6 色。

### 4.2 禁用颜色

| 禁止 | 原因 |
|---|---|
| 纯黑（#000000） | 压抑，破坏明亮基调 |
| 暗灰（低明度） | 降低小屏可见度 |
| 低饱和绿 | 与主角基础色融合困难，识别度下降 |
| 大量渐变 | 手机显示不稳定，性能开销 |
| 写实暗调光影 | 偏离卡通明亮 |

---

## 5. UI 规范

### 5.1 UI 风格关键词

大、圆、弹性、有反馈、高识别度。

### 5.2 按钮规范

| 要素 | 约束 |
|---|---|
| 最小尺寸 | 200×80 px |
| 圆角 | 30px |
| 状态 | 正常 → 按下 → 成功（必须有动画） |
| 反馈 | 按下时挤压回弹（squash & stretch） |
| 字号 | 标题 ≥ 32pt，正文 ≥ 20pt |

### 5.3 字体

| 用途 | 推荐 | 禁止 |
|---|---|---|
| 标题 / 数值 | 圆体（粗、可爱、清晰） | 细字体、衬线宋 |
| 正文 | 圆体或亲和无衬线 | 等宽冷硬字体 |

### 5.4 弹窗与面板

- 弹窗以"弹跳进入 + 回弹"动画
- 面板圆角统一 R20 ~ R30
- 底色用辅色（黄 / 蓝），描边用主色或强调色
- 禁用直角硬边、扁平无反馈

---

## 6. 变身 / 隐藏系统规范

### 6.1 三阶段变身（核心玩法视觉）

| 阶段 | 内容 | 粒子 / 特效 |
|---|---|---|
| 阶段 1 | 颜色变化 | 彩色光点扩散 |
| 阶段 2 | 材质变化（木纹 / 金属反光 / 织物） | 材质过渡光晕 |
| 阶段 3 | 形态变化（轮廓改变） | 轮廓重塑闪光 |

### 6.2 变身时间

- 推荐 **1.2 秒**
- 不要太快（需"哇，它变了"的感觉）
- 不要太慢（≤ 1.5 秒，避免拖沓）

### 6.3 伪装完成态

- 进入伪装后保留微弱呼吸动画（提示玩家位置）
- **禁止完全静止**（玩家会找不到自己）

---

## 7. 敌人规范

### 7.1 定位

- **搞笑猎人**，不是坏角色
- 慢半拍、笨拙、表情夸张
- 失败时哭泣，不恐怖

### 7.2 比例（敌人）

| 部位 | 占比 |
|---|---|
| 头 | 50% |
| 身体 | 40% |
| 腿 | 10% |

### 7.3 表情库

| 状态 | 表现 |
|---|---|
| 怀疑 | 眯眼 |
| 发现 | 瞪眼 |
| 失败 | 哭 |

### 7.4 敌人动画（必须）

Idle / Walk / Search / Question / Surprise / Catch / Fail

---

## 8. 道具规范

| 要素 | 约束 |
|---|---|
| 轮廓 | 清晰，小屏 1 秒可识别 |
| 颜色 | 纯净，避免复杂纹理 |
| 识别度 | 1 秒知道是什么 |
| 朝向 | 主道具居中，光源左上 45° |
| 风格 | 卡通 3D，圆润造型 |

---

## 9. 渲染与性能（3D 专用）

### 9.1 渲染管线

- **Unity**：URP（Universal Render Pipeline），Stylized 着色，soft lighting，禁用写实 PBR 厚重光照
- **Godot 4**：StandardMaterial3D + WorldEnvironment，ShaderMaterial 用于卡通描边，禁用写实 PBR
- 阴影：soft shadow，强度 ≤ 50%（Unity: Soft Shadows；Godot 4: shadow_blur 调低）

### 9.2 几何约束

| 资产 | 三角面上限 | LOD 要求 |
|---|---|---|
| 主角 | ≤ 8000 | LOD0/LOD1 两级 |
| 敌人 | ≤ 6000 | LOD0/LOD1 |
| 隐藏物 | ≤ 1500 | 单 LOD |
| 装饰 | ≤ 500 | 单 LOD |

### 9.3 贴图压缩

- **Unity**：**ASTC 6×6**（移动端推荐）
- **Godot 4**：VRAM 压缩（移动端 s3tc/bptc，按平台导入）
- 主角贴图：2048×2048
- 道具 / 敌人：1024×1024
- UI：512×512（禁用压缩，Unity 用 RGBA32、Godot 4 用 Lossless，保清晰）

### 9.4 性能预算

- 单场景 Draw Call ≤ 80
- 同屏三角面 ≤ 50k
- 目标帧率 60fps（抖音小游戏 30fps 保底）

---

## 10. 尺寸约束表（3D）

| 类型 | 贴图尺寸 | 透明 | 备注 |
|---|---|---|---|
| 主角贴图 | 2048×2048 | 否 | Unity ASTC 6×6 / Godot 4 VRAM |
| 敌人贴图 | 1024×1024 | 否 | Unity ASTC 6×6 / Godot 4 VRAM |
| 道具贴图 | 1024×1024 | 否 | Unity ASTC 6×6 / Godot 4 VRAM |
| 场景物件贴图 | 1024×1024 | 否 | 可合图 |
| UI 元素 | 512×512 | 是 | Unity RGBA32 / Godot 4 Lossless |
| UI 按钮 | 200×80 起步 | 是 | Unity RGBA32 / Godot 4 Lossless |
| 图标 | 128×128 | 是 | Unity RGBA32 / Godot 4 Lossless |
| 头像 | 256×256 | 是 | Unity RGBA32 / Godot 4 Lossless |
| 特效贴图 | 256×256 | 是 | Unity ASTC 8×8 / Godot 4 VRAM |

> 3D 项目无需图集打包（Unity 用 Sprite Atlas 或直接 Texture；Godot 4 用直接 Texture / AtlasTexture）；§11 图集约束不适用 3D 路线。

---

## 11. 动画约束

### 11.1 基础动作列表

| 动作 | 时长 | 循环 | 备注 |
|---|---|---|---|
| Idle | 3s | 是 | 呼吸 + 眨眼 + 尾巴摆动 |
| Walk | 1s | 是 | 小跳+爬，**禁止蜥蜴爬行** |
| Run | 0.6s | 是 | 身体前倾夸张 |
| Hide | 1.2s | 否 | 三阶段变身 |
| Found | 0.8s | 否 | 震惊 + 跳起 + 眼睛放大 |
| Win | 2s | 是 | 跳舞 + 尾巴旋转 |

### 11.2 Hide 动画时间轴

| 时间段 | 内容 |
|---|---|
| 0 ~ 0.3s | 观察（左右看） |
| 0.3 ~ 0.8s | 颜色扩散 |
| 0.8 ~ 1.5s | 身体变化 |
| 完成 | 进入伪装（保留微呼吸） |

### 11.3 动画原则

- 挤压拉伸（squash & stretch）贯穿所有动作
- 缓动曲线 ease-out 为主，**禁止线性**
- 表情与动作同步切换

---

## 12. 特效规范

### 12.1 粒子风格

- 小颗粒、高亮色、圆润
- 禁用尖锐碎片、写实火焰

### 12.2 成功特效

星星 + 金币 + 彩带，明亮欢快。

### 12.3 失败特效

**不要负面**。用冒烟 + 眼泪 + 脸红，营造"哎呀"而非"惩罚"。

### 12.4 变身特效

彩色光点扩散 + 轮廓重塑闪光（与 §6.1 三阶段对应）。

---

## 13. 商业化规范（皮肤体系）

### 13.1 三档皮肤体系

| 档位 | 获取 | 视觉特征 |
|---|---|---|
| 普通 | 免费 | 单色变体（基础色系） |
| 稀有 | 付费 | 多色 / 材质变化（如彩虹、糖果） |
| 传奇 | 特殊 | 特效皮肤（如银河、机器人、火焰，带粒子） |

### 13.2 皮肤一致性约束

- 所有皮肤共用同一骨架与比例
- 仅替换贴图 + 材质 + 特效，**不改模型**
- 传奇皮肤可附加粒子挂点

---

## 14. 引擎资产规范（3D 专用）

### 14.1 命名前缀（Unity / Godot 通用）

| 前缀 | 用途 | 示例 |
|---|---|---|
| `CHR_` | 角色 | `CHR_Chameleon_Idle` |
| `ENV_` | 场景 | `ENV_Room_Bed` |
| `PROP_` | 道具 | `PROP_Toy_Bear` |
| `UI_` | UI | `UI_Button_Start` |
| `FX_` | 特效 | `FX_ColorChange` |

### 14.2 目录结构（按引擎）

**Unity**：
```
Assets/
├─ Models/         # .fbx
├─ Textures/       # 贴图（ASTC）
├─ Materials/      # .mat
├─ Animations/     # .anim + .controller
├─ Prefabs/        # .prefab
├─ UI/             # Sprite + 图集
└─ FX/             # 粒子预设
```

**Godot 4**：
```
├─ project.godot              # 入口配置（config_version=5）
├─ scenes/
│  └─ Main.tscn               # 主场景（文本格式 format=3）
├─ models/                    # .glb / .gltf（推荐 glb）
├─ textures/                  # .png / .svg（导入后生成 .import）
├─ materials/                 # .tres（Material 资源）
├─ animations/                # .res / .tres（AnimationLibrary）
├─ ui/                        # .tscn + .png（Control 节点）
├─ fx/                        # .tscn（GPUParticles3D / CPUParticles3D）
└─ scripts/                   # .gd（GDScript 4.x）
```

### 14.3 贴图压缩（按引擎）

| 用途 | Unity | Godot 4 |
|---|---|---|
| 移动端贴图 | ASTC 6×6 | VRAM 压缩（s3tc/bptc，按平台导入） |
| UI / 图标 | RGBA32（禁压缩） | Lossless（禁 VRAM 压缩） |
| 法线贴图 | ASTC 4×4 | VRAM 压缩（normal 压缩模式） |

### 14.4 与 game-code-forge 引擎分支对接

**Unity 分支**：
- 入口：`Assets/Scenes/Main.unity` + `UnityMain.cs`（由 SceneBuilder.cs 程序化生成）
- 程序集：`Assets/Scripts/Runtime/{ProjectName}.asmdef` + `Assets/Scripts/Editor/{ProjectName}.Editor.asmdef`
- 构建产物：`Build/` 目录
- 构建命令：`unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.BuildScript.BuildWindows/BuildWebGL`
- 沙箱无 Unity Editor 时产出代码与配置，构建延后宿主执行

**Godot 4 分支**：
- 入口：`project.godot`（config_version=5）+ `scenes/Main.tscn`（文本格式 format=3）
- 脚本：GDScript 4.x（.gd 文件）
- 类型检查：`godot --headless --check-only`
- 构建产物：`export/` 目录
- 构建命令：`godot --headless --export-release "{preset}" {output}`
- 沙箱无 Godot Editor 时产出 .tscn/.gd/project.godot，构建延后宿主执行

---

## 15. 风格一致性策略

| 策略 | 说明 |
|---|---|
| 同角色同 seed | seed = `hash(roleName + state) % 100000`，写入 manifest |
| Reference image | 首张渲染图作 reference，生成后续皮肤 / 状态 |
| 描边 / 轮廓统一 | 卡通描边 1.5px（若有 toon shader），全项目一致 |
| 阴影方向统一 | 右下 45°，soft shadow ≤ 50% |
| 色板锁定 | 项目内禁止超出基线 6 色 + 项目扩展 4 色 |
| 风格拒绝判定 | 若 AI 生图返回写实比例 / 恐怖 / 暗调，立即重生成，不降级接受 |
| 表情库对齐 | 所有角色共用 8 种基础表情命名，便于动画复用 |

---

## 16. AI 生图 Prompt 模板

> 模板中 `{占位符}` 由项目 ART_SPEC.md 注入具体内容，本基线只提供结构。

### 16.1 主角角色

```
[GAME ASSET]: {role_name} character design,
cute baby {creature} character, round body, big shiny eyes,
small legs, {tail_description}, cartoon mobile game style,
3D stylized, soft lighting, bright colors, friendly expression,
squash and stretch ready, {color_palette}, transparent background,
{width}x{height}, game character design, mobile casual RPG
```

### 16.2 敌人角色

```
[GAME ASSET]: {enemy_name} character design,
funny clumsy hunter, big head 50% proportion, round face,
big nose, slow-witted expression, cartoon mobile game style,
3D stylized, soft lighting, bright colors, non-threatening,
{color_palette}, transparent background, {width}x{height},
game character design
```

### 16.3 场景

```
[GAME BACKGROUND]: {scene_name} environment,
cute cartoon {theme} world, mobile game environment,
rounded furniture, toy world aesthetic, bright colors,
soft shadows, stylized 3D, casual game art style,
70% scene + 20% hideable objects + 10% decoration,
{width}x{height}, no transparent
```

### 16.4 道具 / 隐藏物

```
[GAME ICON]: {item_name} prop, {difficulty} tier,
cute cartoon 3D style, round shape, clear silhouette,
pure bright color, 1-second recognizable, soft lighting,
light source top-left 45 degrees, transparent background,
{width}x{height}, mobile casual game asset
```

### 16.5 UI 元素

```
[GAME UI]: {element} for {page} page,
mobile casual game interface, big and round,
bouncy elastic feedback, round corners 30px,
bright friendly colors, {color} theme,
cartoon style, {width}x{height}, transparent PNG
```

### 16.6 皮肤（三档）

```
[GAME SKIN]: {role_name} {rarity} skin,
{rarity_tier} quality ({common|rare|legendary}),
{common: single color variant} / {rare: multi-color + material change} / {legendary: particle aura},
same skeleton and proportion as base character,
3D stylized cartoon, bright colors, soft lighting,
transparent background, {width}x{height}
```

### 16.7 特效

```
[GAME FX]: {effect_name} particle effect,
small round bright particles, {success|failure|transform} type,
{success: stars + coins + ribbons} / {failure: smoke + tears + blush, not negative} / {transform: color spread + outline glow},
cartoon mobile game style, transparent background,
{width}x{height}
```

---

## 17. 负面词清单（Negative Prompt）

通用负面词，所有生图调用必须附加：

```
negative prompt:
realistic photo,
real animal proportion,
7~8 heads tall realistic body,
sharp edges, ferocious, scary,
dark horror, gore,
low saturation, dark grey, pure black,
heavy gradient,
photorealistic PBR rendering,
oil painting, thick CG painting,
western realistic fantasy,
cyberpunk, neon,
military, weapons,
complex realistic textures,
thin font, serif font,
```

---

## 18. 已知风险与降级策略

| 风险 | 触发表现 | 降级策略 |
|---|---|---|
| AI 返回写实动物 | 真实蜥蜴 / 真实猫比例 | 重生成，加强 `cute baby, round body, big head 45%` |
| AI 返回恐怖 / 凶猛 | 尖牙 / 利爪 / 暗调 | 重生成，加强 `friendly, soft, bright, non-threatening` |
| 高饱和荧光 | 刺眼霓虹 | 重生成，加强 `bright but soft, mobile friendly` |
| 道具轮廓模糊 | 小屏不可识别 | 重生成，加强 `clear silhouette, 1-second recognizable` |
| 失败特效负面 | 血腥 / 惩罚感 | 重生成，加强 `not negative, smoke tears blush, cute` |
| UI 缺弹性 | 扁平无反馈 | 加 `bouncy, squash and stretch, round corners 30px` |
| 3D 资产面数超标 | 性能不达标 | 减面 + LOD 生成（不在 prompt 层解决，走引擎工具链：Unity Mesh LOD / Godot 4 ImporterLOD） |
| 变身动画过快 | 无"哇"感 | 强制 1.2s，三阶段时间轴固定 |

> **硬规则**：风格类风险**只重生成，不接受降级**；性能类风险（面数 / Draw Call）走引擎工具链优化（Unity 或 Godot 4），不在生图层解决。

---

## 19. 与 game-art-spec 流水线的对接

本基线是 `game-art-spec` skill 的**可选前置输入**。对接流程：

```
项目调用 game-art-spec
        │
        ├─ 1. 读 docs/PRD.md + docs/TECH_DESIGN.md
        ├─ 2. 判定画风 → 命中"3D卡通休闲躲猫猫" → 加载本基线
        ├─ 3. 项目在此基线上叠加题材差异（角色物种 / 地图主题 / 敌人形象）
        ├─ 4. 生成 docs/ART_SPEC.md（基线约束 + 项目内容）
        ├─ 5. 生成 docs/ASSET_MANIFEST.json
        │     ├─ 3D 路线：asset type = model / texture / material / animation / prefab
        │     └─ prompt 引用 §16 模板，contentHash / predecessorId 仍按增量更新机制填写
        ├─ 6. 生成 docs/AUDIO_SPEC.md（音频风格沿用卡通休闲欢快 BGM）
        └─ 7. 下游 game-code-forge 按项目引擎选择 Unity 或 Godot 4 分支
```

### 19.1 与 2D 基线的差异点

| 维度 | 2D 基线（chibi-xianxia-ink） | 3D 基线（本基线） |
|---|---|---|
| 渲染 | 2D 手绘 + 水墨淡彩 | 3D URP Stylized（Unity）/ StandardMaterial3D（Godot 4） |
| 引擎 | Phaser / Pixi / Canvas / Godot 2D | Unity（URP）/ Godot 4 |
| 资产类型 | spriteframe / image | model / texture / material / animation / prefab |
| 图集 | 必须打包（atlas） | 不打包（Unity Sprite Atlas / Godot 4 直接 Texture） |
| 性能 | 文件体积优先 | 三角面 / Draw Call 优先 |
| 压缩 | png-32 / jpg-80 | Unity ASTC 6×6 / Godot 4 VRAM |

### 19.2 项目级扩展字段（写入 ART_SPEC.md 头部）

项目应在自己的 `ART_SPEC.md` 顶部声明对基线的扩展：

```markdown
# {项目名} - 美术资源规范

## 0. 风格基线声明
- 基线：3D卡通休闲躲猫猫手游风（references/style-baseline-cartoon-casual-hide-seek.md）
- 渲染维度：3D
- 引擎：Unity 2022.3 LTS（URP） 或 Godot 4.x
- 扩展色板（≤4）：{项目自定义色}
- 比例微调：默认 2.2 头身
- 题材差异：{一句话描述本项目与基线的偏离}
```

### 19.3 资源清单 prompt 引用约定

`ASSET_MANIFEST.json` 中每个 asset 的 `prompt` 字段：
- 必须以 `[GAME ASSET]` / `[GAME BACKGROUND]` / `[GAME ICON]` / `[GAME UI]` / `[GAME SKIN]` / `[GAME FX]` 开头
- 模板占位符必须全部替换为具体值
- 风格段直接复用本基线 §16 对应模板
- 3D 路线的 `contentHash` = `sha256(prompt + size + format)`，与 2D 一致
- 不允许出现裸 prompt

### 19.4 风格拒绝自动判定

`game-asset-forge` 在生成后应对照 §18 风险表做自动检查：
- 若返回写实比例 / 恐怖 / 暗调 → 自动重生成（最多 3 次）
- 3 次仍失败 → 标记到 `ASSET_MANIFEST.json` 的 `conversionNote` 字段并提示人工介入
- 性能类问题（面数超标）不在生图层处理，由引擎工具链后续优化（Unity 或 Godot 4）
