---
name: "short-drama-storyboard"
description: "Stage 4 of the AI short-drama production pipeline. Reads docs/scripts/EP{01..NN}.md and converts the script into an executable storyboard (docs/STORYBOARD.md) with per-shot text-to-image and image-to-video prompts, a visual specification (docs/VISUAL_SPEC.md) covering characters, scenes, style baseline, subtitles and safe areas, plus a machine-readable asset requirement manifest (docs/ASSET_MANIFEST.json) declaring every character/variant, scene, prop, voice and the style baseline for stage 4.5 to materialize. Use when scheduled by short-drama-forge-master after Gate 2, or when the user asks to turn a short-drama script into storyboards and visual specs."
---

# Short Drama Storyboard — 短剧分镜与视觉设计

本 skill 是 AI 短剧制作流水线的**阶段 4**,职责是把正式剧本(`docs/scripts/EP{01..NN}.md`)转换成**可执行的分镜脚本**、**视觉规范**与**机读资产需求清册**,让阶段 4.5(short-drama-asset-forge)能照清单定妆并锁定角色/场景/道具/音色基线,让阶段 5(short-drama-video-forge)能直接照 prompt 生产镜头,让阶段 6(short-drama-audio-forge)能取对白与音效。

**本阶段是"资产需求"的唯一出口**:分镜是全剧唯一知道"有哪些角色/变体/场景/道具、各被引用多少镜头"的产物,因此资产清册必须在此声明,不允许下游自行推断。

---

## 一、输入与输出

**输入**(必读):
- `docs/scripts/EP{01..NN}.md`(阶段 3 产出,每集一文件,取对白/动作/场景/情绪)
- `docs/SHORT_DRAMA_BLUEPRINT.md`(取制作类型/工具链选型/画幅,判定是否图文短剧裁剪)
- `docs/VISUAL_SPEC.md`(若已存在则增量修订,不重写)

**输出**(固定路径,3 份产物,与总纲 §八 一致):
- `docs/STORYBOARD.md`(分镜脚本,人读+机读:每镜头含文生图/图生视频 prompt)
- `docs/VISUAL_SPEC.md`(视觉规范:角色卡/场景设定/风格基线/字幕样式/画幅安全区)
- `docs/ASSET_MANIFEST.json`(机读资产需求清册:角色/变体/场景/道具/音色/风格基线的**声明**,`status=declared`,交阶段 4.5 定妆锁定)

**关键**:分镜是阶段 5 的唯一画面依据,所有 prompt 必须"可执行"(见 §3.3 与 references/visual-prompt-engine.md),不允许模糊描述。**资产清册是阶段 4.5/5/6 的唯一资产来源**(见 §五)。

---

## 二、执行流程

```
0. 输入校验(见 二.0)
1. 定视觉基线:风格/画幅/分辨率/字幕安全区 → 先写 docs/VISUAL_SPEC.md 骨架
2. 逐集逐场拆镜头(见 三):对白驱动 + 动作驱动,遵循镜头语言规则(见 六)
3. 每镜头补全 12 字段(见 三.1),含文生图 prompt + 图生视频 prompt
4. 全剧角色/场景/道具引用对齐 VISUAL_SPEC(见 七)
5. 汇总资产需求 → 产出 docs/ASSET_MANIFEST.json(见 五),status 全部为 declared
6. 自检(见 八),不通过回 2 修复
7. 简报(见 九)
```

### 二.0 输入校验

- `docs/scripts/` 不存在或无 `EP*.md` → 报错"剧本缺失,请先调用 short-drama-script",列出期望路径,直接退出
- 剧本格式异常(缺对白/场景标记)→ 报错指出文件与位置,回阶段 3 修复

---

## 三、分镜脚本(docs/STORYBOARD.md)

### 3.1 每镜头字段(12 项必填 + 1 项可选)

| 字段 | 示例 | 说明 |
|---|---|---|
| 镜头号 | `EP01-S01` | `EP{XX}-S{YY}` 两位编号,全剧唯一 |
| 景别 | 中景 | 远景/全景/中景/近景/特写 |
| 运镜 | 推 | 固定/推/拉/摇/移/跟/升降;图文短剧降级用缩放/平移模拟 |
| 时长 | 5s | 3-10 秒,含对白时间 |
| 画面描述 | 林晚在雨夜巷口回望,霓虹倒映水洼,冷蓝侧光 | 主体+动作+环境+光线,四要素齐 |
| 角色 | 林晚 / `linwan` / `linwan(student)` | 引用 VISUAL_SPEC 角色 id;非 default 变体写 `角色id(变体id)`,变体写法见 §5.3 |
| 场景 | 雨夜巷口 | 引用 VISUAL_SPEC 场景 id |
| 对白/字幕 | "你终于来了。" | 完整文本,供字幕与配音 |
| 情绪基调 | 紧张 | 一两个词,驱动光线与色调 |
| 音效 | 雨声+低频心跳 | 供 audio-forge,可选 |
| 文生图 prompt | 见 3.3 | 主体/动作/环境/光线/风格/画幅 9:16/角色参考 |
| 图生视频 prompt | 见 3.3 | 画面主体+运动描述+镜头运动+时长 |
| 道具(可选) | `prop_watch` | 引用清册 `props[].id`;线索类道具出现的镜头必须标,供阶段 5 保持道具一致 |

### 3.2 分镜脚本格式(每集一节,每镜一段)

```markdown
# {剧名} - 分镜脚本

## 全局约定
画幅:9:16(1080x1920)| 风格:{风格名} | 风格关键词:{...}

## EP01
### EP01-S01
- 景别:中景
- 运镜:推
- 时长:5s
- 画面:林晚在雨夜巷口回望,霓虹倒映水洼,冷蓝侧光
- 角色:林晚
- 场景:雨夜巷口
- 对白:"你终于来了。"
- 情绪:紧张
- 音效:雨声+低频心跳
- 文生图:portrait 9:16,林晚(reference:assets/char/linwan/default.png,seed:20241,都市悬疑,冷色调,电影感),回望侧脸,雨夜巷口霓虹,冷蓝侧光,cinematic
- 图生视频:林晚缓缓回头,眼神从平静转锐利,镜头缓慢推近,5s

### EP07-S03
- 角色:linwan(student)
- 文生图:portrait 9:16,林晚学生时代(reference:assets/char/linwan/student.png,seed:20242,都市悬疑,冷色调,电影感),齐耳短发,白衬衫校服,教室窗边,暖光柔焦,cinematic
```

> 提示词里的 reference 路径**统一写 `assets/char/{charId}/{variantId}.png`** —— 该文件由阶段 4.5 定妆产出;阶段 5 开工前 Gate 3.5 会校验它确实存在且已锁定。

### 3.3 Prompt 可执行性(关键)

- **文生图 prompt 六要素**:主体 / 动作 / 环境 / 光线 / 风格 / 画幅(9:16);角色镜头必须带 `reference:assets/char/{charId}/{variantId}.png` + 固定 seed + 风格关键词 + 风格基线负面词
- **图生视频 prompt 四要素**:画面主体 / 运动描述 / 镜头运动 / 时长(秒)
- 模板与光线-情绪映射详见 `references/visual-prompt-engine.md`;命中风格基线时叠加基线关键词与负面词(见 VISUAL_SPEC §4.3)

---

## 四、视觉规范(docs/VISUAL_SPEC.md)

### 4.1 角色视觉设定卡(每个主要角色一张,含变体表)

**母卡**(角色级):

| 字段 | 说明 |
|---|---|
| 角色 id | `linwan`,全剧引用依据;与 ASSET_MANIFEST `characters[].id` 一致 |
| 姓名 | 林晚 |
| 角色功能 | protagonist / antagonist / romance / ally / traitor / secret-holder / mirror / minor |
| 年龄感 | 25 岁左右(供音色与外观推导) |
| 基础外貌 | 高马尾/黑色风衣/利落碎发(描述到可生图粒度) |
| 风格关键词 | 都市悬疑 / 冷色调 / 电影感 |
| 音色方向 | 低沉磁性女声(供阶段 4.5 音色资产,见 §5.4) |
| 变体数 | 2(default + student) |

**变体子表(每角色一份,至少含 default)**:

| variantId | 标签 | 与 default 的差异项 | 派生自 | 引用集数 |
|---|---|---|---|---|
| default | 常态 | —(母版) | — | EP01,EP02,EP11 |
| student | 学生时代(回忆线) | 发型+服装+年龄感 | default | EP07 |

- **一致性控制三件套**:参考图 `assets/char/{charId}/{variantId}.png` + 固定 seed(各变体互异)+ 风格关键词
- 变体的触发场景与规则见阶段 4.5 SKILL.md §4.1(年龄跨度/换装伪装/战损/身份反转造型)
- **不得为"丰富度"滥建变体**:每个变体都要跨集一致维护,是持续成本;变体的 `episodes` 必须来自 STORYBOARD 实际引用

### 4.2 场景设定(每个主要场景)

| 字段 | 说明 |
|---|---|
| 场景 id | `rainy_alley` |
| 名称 | 雨夜巷口 |
| 环境 | 雨夜巷口,霓虹灯牌,水洼 |
| 氛围 | 压抑悬疑 |
| 光线 | 冷蓝侧光,雨丝可见 |
| 风格 | 都市悬疑,电影感 |
| 常驻判定 | 被 ≥2 集引用 → 需定妆;仅 1 集且 <3 镜头 → 标 `oneOff` 免定妆 |

同场景固定 seed,光线按情绪基调微调(可多张环境变体)。场景图要求**无人或仅远景剪影**(避免定妆图里带人脸导致后续融合漂移)。

### 4.2b 道具设定(剧情线索类必列)

| 字段 | 说明 |
|---|---|
| 道具 id | `prop_watch` |
| 名称 | 旧怀表 |
| 剧情作用 | 终极真相线索:表盖内侧刻字指向真凶 |
| 首次暗示集 | EP03 |
| 引用集数 | EP03,EP12,EP48 |

**判据**:凡进入 STORY_SPEC 秘密系统铺垫的道具(信物/照片/信件/钥匙/手机)**必须列入**,因为道具漂移会直接破坏伏笔 —— 观众认不出"同一个怀表",悬念就失效了。

### 4.3 风格基线

写实 / 古风 / 都市 / 漫画 / 赛博…,每基线含:
- 色彩倾向(如 都市悬疑→冷蓝+霓虹点缀;古风→水墨淡彩+暖棕)
- 光线基调(硬光/柔光/高反差)
- 风格关键词 + 负面词(附加到所有 prompt)

### 4.4 字幕样式

字体(如 思源黑体 Bold)/ 字号(竖屏 40-48px)/ 描边(黑色 4px 半透明)/ 位置(底部安全区内,距底约 120px)/ 每行 ≤12 字。

### 4.5 画幅与安全区

- 画幅 9:16,分辨率 1080x1920
- 字幕安全区:底部 15%(0-162px)留白,画面主体避开
- 顶部 10%(0-108px)为状态/信息区,可留白或放标题

---

## 五、资产需求清册(docs/ASSET_MANIFEST.json)

VISUAL_SPEC 是**给人看的规范**,ASSET_MANIFEST 是**给机器读的需求清册**。二者内容必须一致(人读版写描述,机读版写 id/文件路径/seed/状态),**机读版是阶段 4.5 与阶段 5/6 的唯一资产来源**。

### 5.1 本阶段产出的形态

- `version: "1.0"`,五类资产齐备:`styleBaseline` / `characters` / `scenes` / `props` / `voice`
- 所有资产 `status` 一律为 **`declared`**,`assetVersion`/`hash`/`lockedAt`/`lockedBy` 一律为 `null`(锁定由阶段 4.5 完成)
- 字段定义、状态机、与 `production/manifest.json` 的引用关系**完整契约见 `../short-drama-asset-forge/references/asset-manifest-schema.md`**(唯一真源文档,本 skill 不重复定义)

### 5.2 从分镜到清册的三步汇总

```
1. 扫 STORYBOARD 每镜头「角色」列 → 汇总出 characters[]（去重）+ 每角色 appearsIn / shotRefCount
2. 扫「角色」列里的变体标记（如 "linwan(student)"）→ 汇总 variants[] + 每变体 episodes[]
3. 扫「场景」列 + STORY_SPEC 秘密系统涉及道具 → scenes[] / props[]
```

| 汇总项 | 来源 | 写入 |
|---|---|---|
| 角色清单 + 引用集数 | STORYBOARD 角色列去重 | `characters[].appearsIn` / `shotRefCount` |
| 变体清单 | STORYBOARD 角色列变体标记(见 §5.3) | `characters[].variants[]` |
| 场景清单 + 常驻判定 | STORYBOARD 场景列去重 + 集数统计 | `scenes[]`(+ `oneOff`) |
| 道具清单 | STORY_SPEC 秘密系统 + 分镜画面描述中的线索道具 | `props[]`(+ `significance`/`firstHintEp`) |
| 音色清单 | 角色清单 × VISUAL_SPEC 年龄/性别/气质 | `voice[]`(音频裁剪时标 `skipped`) |
| 风格基线 | VISUAL_SPEC §4.3 | `styleBaseline`(声明形态,锁定在 4.5) |
| 计数汇总 | 上述各类计数 | `summary`(供 Gate 3.5 对账) |

### 5.3 变体标记写法(镜头级)

镜头引用非 default 变体时,在「角色」列写成 `角色id(变体id)`:

```
- 角色:linwan(student)          # 引用 student 变体
- 角色:linwan                    # 等价于 linwan(default)
- 角色:linwan + chenmo           # 多人同框,默认变体
```

- 缺省即 `default`,不必显式写
- **同一角色的变体 id 必须在 VISUAL_SPEC 变体子表(§4.1)中有定义**,否则自检不通过
- 阶段 5 会把变体标记翻译为 `production/manifest.json` 的 `charVariants` 字段

### 5.4 音色声明的职责边界

本阶段只**声明**音色需求(id/timbre/emotionTags/推导依据),不生成音频;试音样本与实际 `ttsVoiceName` 由阶段 4.5 产出。TTS 工具按蓝图"8. 工具链选型"的 TTS 环节确定。

---

## 六、镜头语言规则(单集强制)

1. **单集 10-25 镜头**(总纲 §八);镜头数×平均时长 ≈ 单集时长(1-3 分钟)
2. **每集至少 1 个特写/近景**强化情绪(哭/笑/惊/杀意等)
3. **卡点镜头(结尾悬念)必须特写或大反差**,每集最后 1 镜必为卡点
4. **对话场景用正反打**:过肩(over-shoulder)或单侧(single)交替,同一人连续对白 ≤2 镜
5. 动作戏用远景/全景交代空间,近景跟拍;运镜表达升格/降格节奏
6. 镜头 3-10 秒节奏:信息量大 3-5s,情绪镜头 6-10s

规则展开(景别表/运镜表/正反打细则/卡点设计)见 `references/shot-language.md`。

---

## 七、角色一致性(本阶段只负责"声明一致",不负责"实现一致")

**职责边界(重要)**:本阶段产出的是**一致性声明**(角色卡 + 变体表 + 清册里的三件套要求);**一致性实现**由阶段 4.5 定妆锁定 + 阶段 5 按锁定资产生成共同完成。因此:

- 全剧同一角色所有镜头:**同一参考图 + 同变体固定 seed + 同一组风格关键词**(三件套)
- 参考图路径统一写为 `assets/char/{charId}/{variantId}.png`,由阶段 4.5 落地 —— **本阶段不产图,也不允许引用不存在的路径作为"已定稿"**
- 同角色跨集形象变化**必须走变体**(见 §4.1 变体子表),不允许在同一变体内临时改服装描述 —— 那是漂移的主要来源
- 双人同框:主视角角色带参考,次视角角色在 prompt 中完整文字描述
- 场景同理:同场景固定 seed,光线按情绪基调微调
- 漂移镜头的**判定与处理在阶段 5**(video-forge §五):标 `character-drift` 并用锁定参考图重生成;本阶段只保证"声明可查、无未定义引用"

---

## 八、自检清单(产出前逐项过)

- [ ] 镜头总数与剧本时长匹配:每集 镜头数×平均时长 ≈ 单集时长(±15%)
- [ ] 单集 10-25 镜头,每集至少 1 个特写/近景
- [ ] 每镜头 12 字段齐全,文生图+图生视频 prompt 均可执行(无模糊词)
- [ ] 角色/场景引用与 VISUAL_SPEC 完全一致(角色 id / 场景 id 可查)
- [ ] 每集结尾镜头是卡点镜头(特写或大反差)
- [ ] 画幅 9:16 / 1080x1920,字幕在安全区内
- [ ] 镜头时长 3-10s;对白时长 ≤ 镜头时长
- [ ] 图文短剧裁剪时,每镜头有文生图 prompt,图生视频 prompt 标注"静态图+模拟运镜"
- [ ] **每个角色有且仅有 1 个 `default` 变体;各变体 seed 互异**
- [ ] **镜头里出现的每个 `角色id(变体id)` 标记都在 VISUAL_SPEC 变体子表有定义**
- [ ] **变体的 `episodes[]` 由 STORYBOARD 实际引用汇总得出,无凭空变体、无空引用变体**
- [ ] **常驻场景(≥2 集引用)未漏声明;一次性场景已标 `oneOff: true`**
- [ ] **STORY_SPEC 秘密系统涉及的道具已全部列入 `props[]`(含 `significance` / `firstHintEp`)**
- [ ] **`docs/ASSET_MANIFEST.json` 可解析、五类齐全、全部资产 `status=declared`**
- [ ] **`summary` 计数与文件/引用实际一致(角色/变体/场景/道具数逐项核对)**
- [ ] 自评:按 skill-auditor 执行后评测模式自查(可选)

---

## 九、交互约定

1. 读取剧本后直接产出 3 份产物,不向用户提问(仅当存在多套风格可选时,先用 AskUserQuestion 确认风格基线)
2. **变体判定需用户参与时**(如"这段回忆要不要单开一个学生时代变体"),用 AskUserQuestion 确认 —— 变体一旦创建就是跨集持续维护成本
3. 产出后简报:"分镜、视觉规范与资产需求清册已生成,共 {N} 镜头 / {M} 角色({V} 变体)/ {K} 场景 / {P} 道具。等待质量门 Gate 3 校验后进入资产定妆(阶段 4.5)"
4. 不自行调用下游 skill;Gate 3 由 short-drama-quality-gate 介入,FAIL 时回到本 skill 修复

---

## references 使用指引(懒加载)

| 文件 | 何时读取 |
|------|---------|
| `references/shot-language.md` | 拆镜头时:景别/运镜/时长/正反打/卡点规则 |
| `references/visual-prompt-engine.md` | 写 prompt 时:文生图/图生视频模板与角色一致性控制 |
| `../short-drama-asset-forge/references/asset-manifest-schema.md` | 产出资产需求清册时:ASSET_MANIFEST.json 完整字段契约(唯一真源,不重复定义) |
