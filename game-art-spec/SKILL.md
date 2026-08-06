---
name: "game-art-spec"
description: "AI 游戏生成流水线阶段 3。读取 PRD 与技术设计,产出美术规范、ASSET_MANIFEST.json 资源清单(机读)和音频规范。当被 game-forge-master 调度到本阶段,或用户要'生成美术规范/资源清单'时调用。"
---

# Game Art Spec — 美术规范与资源清单

本 skill 是 AI 游戏生成流水线的**阶段 3**,职责是把 PRD 与 TECH_DESIGN 转换成可执行的美术资源规范,并产出**机读的资源清单**(ASSET_MANIFEST.json),这是连接美术与代码的中枢契约。

---

## 一、输入与输出

**输入**(必读):
- `docs/PRD.md`(取 UI 节点树、玩法机制、音效清单)
- `docs/TECH_DESIGN.md`(取帧动画表、配置结构)

**输出**(固定路径,3 份产物):
- `docs/ART_SPEC.md`(人读,美术约束 + 生图 prompt 模板)
- `docs/ASSET_MANIFEST.json`(机读,资源清单,代码 skill 直接消费)
- `docs/AUDIO_SPEC.md`(人读,音频清单 + 生成指引)

---

## 二、风格基线(可选前置)

当项目画风命中已收录的**风格基线**时,应先加载基线再生成 ART_SPEC.md。基线提供通用约束(角色比例 / 色板 / UI 材质 / Prompt 模板 / 负面词 / 风险降级),项目仅叠加题材差异(角色名 / 世界观 / 门派色),避免重复造轮子。

**已收录基线**:

| 基线名 | 维度 | 引擎 | 路径 | 适用画风 |
|---|---|---|---|---|
| Q版国风修仙水墨手游风 | 2D | Phaser 3 / Pixi.js / 纯 Canvas / Godot 4 | `references/style-baseline-chibi-xianxia-ink.md` | Q版 2.5~3 头身 + 水墨淡彩 + 玉石金描边 UI + 仙侠题材 |
| 3D卡通休闲躲猫猫手游风 | 3D | Unity (URP) / Godot 4 | `references/style-baseline-cartoon-casual-hide-seek.md` | Q版 2~2.5 头身 + 卡通明亮圆润 + 大圆弹性 UI + 躲猫猫/变装隐藏题材 |

**判定规则**:
1. **先判维度**:从 PRD / TECH_DESIGN 读渲染维度(2D / 3D)与目标引擎,缩小候选基线范围。
2. **再判画风关键词**:
   - 2D + `chibi / 国风 / 修仙 / 仙侠 / 水墨 / 手游 RPG` → 命中 chibi-xianxia-ink
   - 3D + `卡通 / 可爱 / 明亮 / 圆润 / 躲猫猫 / 变装 / 玩具世界 / 休闲手游` → 命中 cartoon-casual-hide-seek
3. **命中后**:在生成的 `ART_SPEC.md` 顶部按对应基线的"项目级扩展声明"小节(chibi-xianxia-ink 为 §16.1,cartoon-casual-hide-seek 为 §19.2)声明扩展,资源 prompt 直接复用基线对应章节的模板(chibi-xianxia-ink 为 §13,cartoon-casual-hide-seek 为 §16),负面词固定附加基线负面词清单(chibi-xianxia-ink 为 §14,cartoon-casual-hide-seek 为 §17)。
4. **维度差异注意**:2D 基线 asset type 走 spriteframe/image + 图集打包;3D 基线 asset type 走 model/texture/material/animation/prefab + 不打包(Unity 用 Sprite Atlas,Godot 4 用直接 Texture / AtlasTexture)。下游 game-code-forge 按基线维度选择引擎分支(2D → Phaser 3 / Pixi.js / 纯 Canvas / Godot 4 等,3D → Unity / Godot 4)。

未命中任何基线时,沿用本 skill §四的通用 ART_SPEC 模板自行定义风格。

---

## 三、ASSET_MANIFEST.json Schema(中枢契约)

这是整套方案最关键的产物,**代码 skill 只读此文件**,不读美术文档。schema:

```json
{
  "version": "1.0",
  "engine": "phaser",
  "meta": {
    "designResolution": [750, 1624],
    "fitMode": "fitWidth"
  },
  "atlases": [
    {
      "id": "skin0",
      "output": "assets/atlases/skin0.png",
      "dataOutput": "assets/atlases/skin0.json",
      "maxSize": [1024, 1024],
      "padding": 2,
      "format": "phaser-json-array"
    }
  ],
  "assets": [
    {
      "id": "skin0-run-1",
      "category": "role",
      "type": "spriteframe",
      "path": "assets/role/skin0/run_001.png",
      "size": [256, 256],
      "format": "png-32",
      "atlas": "skin0",
      "animKey": "skin0-run",
      "frameIndex": 0,
      "totalFrames": 6,
      "prompt": "卡通小马奔跑第1帧,侧面,新年红色皮肤,256x256,透明背景",
      "seed": 12345
    },
    {
      "id": "ui-home-btn-start",
      "category": "ui",
      "type": "image",
      "path": "assets/ui/home/btn_start.png",
      "size": [200, 80],
      "format": "png-32",
      "atlas": "ui-home",
      "prompt": "开始按钮,圆角矩形,红色,游戏风格,200x80,透明背景",
      "contentHash": "a1b2c3...",
      "predecessorId": null
    },
    {
      "id": "bg-home",
      "category": "bg",
      "type": "image",
      "path": "assets/bg/home_main.png",
      "size": [750, 1624],
      "format": "jpg-80",
      "atlas": null,
      "prompt": "新年主题背景,红金配色,喜庆,750x1624"
    }
  ],
  "audio": [
    {
      "id": "bgm-home",
      "path": "assets/audio/bgm_home.mp3",
      "duration": 30,
      "loop": true,
      "format": "mp3-128k",
      "prompt": "新年主题欢快背景音乐,30秒循环,民乐+电子",
      "fallback": "silent-1s"
    },
    {
      "id": "sfx-jump",
      "path": "assets/audio/sfx_jump.wav",
      "duration": 1,
      "loop": false,
      "format": "wav",
      "prompt": "跳跃音效,清脆短促,200ms",
      "fallback": "silent-1s"
    }
  ],
  "fonts": []
}
```

### 字段约束

| 字段 | 必填 | 说明 |
|---|---|---|
| id | 是 | 全局唯一,小写连字符 `skin0-run-1` |
| category | 是 | role / ui / bg / effect / icon |
| type | 是 | spriteframe / image / audio |
| path | 是 | 相对工程根目录的路径 |
| size | 是 | [width, height] 像素 |
| format | 是 | png-32 / jpg-80 / wav / mp3-128k(**期望格式**,实际见 actualFormat) |
| atlas | 否 | 所属图集 ID,无则 null |
| animKey | 否 | 帧动画时所属的动画 key |
| frameIndex | 否 | 动画中的第几帧(从 0) |
| totalFrames | 否 | 该动画总帧数 |
| prompt | 是 | 给 AI 生图的 prompt |
| seed | 否 | 固定 seed(同角色同 seed) |
| fallback | 否 | 音频失败时的降级方案 |
| contentHash | 是 | 内容指纹 `sha256(prompt + size + format)`,由本 skill 写入。下游对比新旧 manifest,hash 不变 → 复用旧文件不重生成 |
| predecessorId | 否 | 改名前的 id。布局调整导致 asset 改名时,由本 skill 写入旧 id;下游据此移动旧文件而非重生成 |
| actualFormat | 否 | **实际格式**(由 game-asset-forge 回写,见下"与下游 skill 的契约") |
| actualPath | 否 | **实际路径**(若 game-asset-forge 改名则回写) |
| converted | 否 | 是否经过格式转换(回写) |
| conversionNote | 否 | 转换备注(回写) |

### 与下游 skill 的契约(关键)

ASSET_MANIFEST.json 是美术规范与代码生成之间的**中枢契约**,但 `format` 字段是**期望**而非**真相**。
真相由 game-asset-forge 在生成完成后回写:

```
game-art-spec  →  写入 format="png-32"          (期望)
                  ↓
game-asset-forge → AI 生图常返回 jpg            (现实)
                   → 用 sharp 阈值抠图转 png    (修正)
                   → 回写 actualFormat="png-32"  (真相)
                   → 或回写 actualFormat="jpg-80"(降级)
                  ↓
game-code-forge → 读 actualFormat 优先于 format  (消费真相)
                   若 actualFormat != png-32 → 走散图降级
```

**字段约束**:
- `format` 一经写入不再修改(代表美术意图)
- `actualFormat` / `actualPath` / `converted` / `conversionNote` 由 game-asset-forge 在流程末尾统一回写
- 下游 skill(game-code-forge / game-integrate)消费时**必须优先读 actual* 字段**

详见 game-asset-forge skill 的第十章"格式校验与转换"与第十一章"manifest 回写"。

### 增量更新机制(布局调整时)

当 PRD 的 UI 节点树调整(页面重排 / 元素增减 / 改名),`game-art-spec` 会整表重写 manifest。为避免下游盲目重生成全部资源,用 `contentHash` + `predecessorId` 做增量 diff:

```
重跑 game-art-spec 生成新 manifest
        ↓
对比新旧 manifest(以 id 为主键):
  ├─ id 相同 + contentHash 相同 → 未变更,跳过生图,复用旧文件
  ├─ id 相同 + contentHash 不同 → 内容变更,重生成该资源
  ├─ id 新增(predecessorId=null)→ 新增,生图
  ├─ id 新增 + predecessorId 命中旧 id → 改名,移动旧文件到新 path,不重生成
  └─ 旧 id 在新表消失 → 已删除,清理旧文件(可选保留备份)
```

**字段约束**:
- `contentHash` = `sha256(prompt + size + format)`,由本 skill 在写 manifest 时计算并填入;`actual*` 字段不参与 hash(它们是回写产物,代表执行结果而非意图)
- `predecessorId` 仅在 id 与上一版不同时填入,否则为 `null`
- 首次生成(无旧 manifest)时所有 asset 的 `predecessorId` 为 `null`,全部走生图

**下游消费约定**:
- `game-asset-forge` 启动前先 diff 新旧 manifest,仅对"需生图"和"需移动"的 asset 执行操作,其余跳过
- 移动文件后,game-asset-forge 仍需回写新 manifest 的 `actualPath`(因 path 已变)
- 若 `predecessorId` 命中但旧文件已不存在(如被清理),降级为重生成

**变更溯源**(供 ART_SPEC.md 记录):
布局调整时,本 skill 应在 ART_SPEC.md 末尾"变更记录"章节追加一行,说明本次调整影响的 asset 范围(新增 N / 删除 M / 改名 K / 内容变更 L),便于人工复核。

---

## 四、ART_SPEC.md 模板

```markdown
# {游戏名} - 美术资源规范

## 1. 全局命名规约

### 1.1 角色帧
`{role}_{state}_{frame:03}.png` → `skin0_run_001.png`

### 1.2 UI 图
`assets/ui/{page}/{element}.png` → `assets/ui/home/btn_start.png`

### 1.3 背景
`assets/bg/{scene}_{variant}.png` → `assets/bg/game_parallax_far.png`

### 1.4 音频
`assets/audio/{type}_{name}.{ext}` → `assets/audio/sfx_jump.wav`
- bgm:背景音乐,mp3
- sfx:音效,wav
- voice:语音,mp3

## 2. 尺寸约束

| 类型 | 推荐尺寸 | 最大尺寸 | 透明 |
|---|---|---|---|
| 角色/物体 | 256×256 | 512×512 | 是 |
| UI 按钮 | 200×80 | 400×160 | 是 |
| 图标 | 64×64 | 128×128 | 是 |
| 弹窗背景 | 750×1200 | 1500×2400 | 否 |
| 全屏背景 | 750×1624 | 1500×3248 | 否 |
| 视差远景 | 750×400 | 1500×800 | 否 |
| 粒子 | 32×32 | 64×64 | 是 |

## 3. 帧动画约束

| 状态 | 推荐帧数 | 帧率 | 循环 |
|---|---|---|---|
| run | 6-8 | 12 fps | 是 |
| jump | 7-10 | 15 fps | 否 |
| death | 8-12 | 10 fps | 否 |
| idle | 4-6 | 6 fps | 是 |
| attack | 6-10 | 15 fps | 否 |

## 4. 风格一致性约束

### 4.1 颜色调板
- 主色:#E60012(新年红)
- 辅色:#FFD700(金)
- 强调色:#FFFFFF(白)
- 阴影色:#8B0000

### 4.2 一致性策略
- 同角色同 seed(写入 manifest 的 seed 字段)
- 首帧生成后作 reference image 生成后续帧
- 描边宽度统一(2px)
- 阴影方向统一(右下 45 度)

### 4.3 文字-背景对比度参考表(需叠加文字的背景图共用)

> 本表是**全流水线唯一源**,game-asset-forge 的 `references/card-bg-spec.md` §12.5 与 game-polish 的 `references/asset-fix-recipes.md` §11.4 均引用本表,不再各自维护副本。
>
> **规则**:背景与文字的亮度差应 ≥ 40%(WCAG AA 标准简化版)。

| 背景底色 | 文字颜色 | 适用场景 |
|---|---|---|
| 浅米黄(#F5E6C8) | 深红(#8B0000)/深灰(#444444)/深棕(#5a0a12) | 水墨风卡片 |
| 深红(#2a1810) | 金色(#FFD700)/白色(#FFFFFF) | 宫廷风卡片 |
| 浅灰(#E8E8E8) | 深灰(#333333)/黑色(#000000) | 现代风面板 |

## 5. 图集打包约束
- 单图集最大 2048×2048
- 边缘 padding 2px
- 同动画帧打包进同一图集
- 输出 .png + .json(Phaser atlas 格式)

## 6. 格式约束

| 类型 | 格式 | 备注 |
|---|---|---|
| 透明图 | PNG-32 | 透明通道 |
| 不透明 | JPG-80 | 体积优先 |
| 音效短 | WAV | <2s |
| 音频长 | MP3 | 128kbps |

## 7. 生图 Prompt 模板

### 7.1 角色帧
```
[GAME ASSET]: {role_name} {state} animation frame {frame_idx}/{total_frames},
{style_description}, {color_palette}, side view, transparent background,
{width}x{height}, consistent character design, pixel-perfect alignment
```

### 7.2 UI 元素
```
[GAME UI]: {element} for {page} page, {style}, {color},
{width}x{height}, transparent PNG, game asset style
```

### 7.3 背景
```
[GAME BACKGROUND]: {scene} background, {style}, {mood},
{width}x{height}, no transparent, jpg
```

## 8. 资源清单汇总

| 类别 | 数量 | 总尺寸估算 |
|---|---|---|

详见 docs/ASSET_MANIFEST.json

## 9. 变更记录

> 布局调整时由 game-art-spec 追加一行,首次生成留空占位。

| 版本 | 日期 | 变更摘要 | asset 影响 |
|---|---|---|---|
| v1.0 | {date} | 首次生成 | 新增 N |
| | | | 新增 / 删除 / 改名 / 内容变更 |

摘要格式参考:`新增 N / 删除 M / 改名 K / 内容变更 L`

## 10. 已知风险

- {高频坑:AI 生图返回 jpg,由 game-asset-forge 用 sharp 抠图转 png}
- {本项目特有风险}
```

---

## 五、AUDIO_SPEC.md 模板

```markdown
# {游戏名} - 音频规范

## 1. 默认策略
**默认走静音占位**(1 秒静音 wav/mp3),工程可跑,人工后补。

## 2. 音频清单
| ID | 类型 | 触发点 | 时长 | 循环 | 风格 | 策略 |
|---|---|---|---|---|---|---|
| bgm-home | BGM | 进入首页 | 30s | 是 | 欢快新年 | 静音占位 |
| sfx-jump | SFX | 点击跳跃 | 200ms | 否 | 清脆短促 | 静音占位 |
| sfx-crash | SFX | 撞击障碍 | 500ms | 否 | 低沉爆破 | 静音占位 |

## 2.5 SFX 事件映射表(工程接入用,必填)

供 game-code-forge 生成音频调用代码、game-quality-gate Gate 2 的 2.13"manifest audio asset ↔ AUDIO_SPEC 事件映射表"校验对齐。

| 事件 ID | 触发条件(PRD 状态机事件) | 音频 ID | 优先级 | 层级 | 备注 |
|---|---|---|---|---|---|
| evt_jump | 玩家点击 → 跳跃状态 | sfx-jump | P1 | 单次 | 跳跃失败不触发 |
| evt_crash | 碰撞 → 游戏结束 | sfx-crash | P0 | 单次 | 优先于 BGM |
| evt_score | 计分 → 分数+1 | sfx-score | P2 | 单次 | 连续得分变调(可选) |
| evt_home_bgm | 场景进入 Home | bgm-home | P3 | 循环 | 切场景淡入淡出 |
| ... | ... | ... | ... | ... | ... |

> **事件 ID 命名规范**:evt_{动作}_{对象},如 evt_jump_player / evt_crash_obstacle。
> **触发条件**:必须引用 PRD §6.2 状态转换表中的"事件"列,保证状态机与音频事件对齐。
> **优先级**:P0(必须播放,如碰撞/失败) > P1(核心反馈,如跳跃/得分) > P2(次要反馈,如按钮) > P3(背景,如 BGM)。
> **层级**:单次(播放一次)/ 循环(直到停止事件)/ 变调(连续触发时音调变化)。
> **资源预算**:同时发声数 ≤ 4(移动端),P0/P1 优先播放,P2/P3 在满负荷时丢弃。

## 3. 占位音频生成
所有音频用统一的 1 秒静音文件占位:
- wav 占位:`assets/audio/_placeholder.wav`
- mp3 占位:`assets/audio/_placeholder.mp3`

各音频文件复制占位文件到目标路径,文件名按规范命名。

## 4. 人工后补指引
替换时直接覆盖 `assets/audio/{xxx}.wav`,**不要改文件名和路径**,代码自动加载。
```

---

## 六、生成规则

### 1. 资源数量统计
- 从 PRD 的 UI 节点树逐节点列资源
- 从 TECH_DESIGN 的帧动画表逐帧列资源
- 从 PRD 的音效清单逐项列音频
- **数量上限**:单游戏美术资源 ≤200 张图 + ≤30 个音频,超出需在 ART_SPEC 标记"建议拆期"

### 2. 图集分组
- 同角色所有帧进同一图集(`skin0`、`skin1`...)
- 同页面 UI 进同一图集(`ui-home`、`ui-game`)
- 背景不打包(单独 jpg)
- 单图集帧数 ≤30,超出拆分

### 3. Prompt 必须可执行
每个资源的 prompt 必须:
- 包含尺寸
- 包含风格描述
- 包含颜色(从颜色调板)
- 角色帧必须含 `transparent background`
- 不允许模糊描述(如"好看的按钮")

### 4. seed 策略
- 同一角色的所有帧用同一 seed
- 同一页面的所有 UI 用同一 seed
- 背景类不固定 seed(可生成多样)
- seed 值用确定性算法:`hash(roleName + state) % 100000`

### 5. 失败标记
ART_SPEC.md 末尾追加"已知风险"章节,标注哪些资源可能生图困难(如复杂场景、多角色同框)。

---

## 七、交互约定

1. 读取 PRD 和 TECH_DESIGN 后,**不要问用户**,直接产出 3 份产物
2. 产出后简报:"美术规范已生成,共 {N} 张图 + {M} 个音频,图集 {K} 个。下一步可并行调用 game-asset-forge(生成资源)和 game-code-forge(生成代码)"
3. 不要自行调用下游 skill

---

## 八、质量检查清单

- [ ] ASSET_MANIFEST.json 通过 schema 校验
- [ ] 每个资源有 prompt
- [ ] 帧动画 frameIndex 从 0 连续
- [ ] 图集分组合理(同角色同图集)
- [ ] 颜色调板 4-6 色
- [ ] 尺寸约束全部满足
- [ ] 音频策略明确(占位/生成)
- [ ] 数量未超上限
- [ ] manifest 字段不写 actual*(留给 game-asset-forge 回写)
- [ ] 每个 asset 有 contentHash(首次生成必填)
- [ ] predecessorId 仅在 id 变更时填入,否则为 null
- [ ] ART_SPEC.md 末尾标注已知风险(高频坑:AI 生图返回 jpg)
- [ ] ART_SPEC.md 末尾有"变更记录"章节(布局调整时追加,首次生成可留空占位)
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
