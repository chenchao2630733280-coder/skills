---
name: "short-drama-storyboard"
description: "Stage 4 of the AI short-drama production pipeline. Reads docs/scripts/EP{01..NN}.md and converts the script into an executable storyboard (docs/STORYBOARD.md) with per-shot text-to-image and image-to-video prompts, plus a visual specification (docs/VISUAL_SPEC.md) covering characters, scenes, style baseline, subtitles, and safe areas. Use when scheduled by short-drama-forge-master after Gate 2, or when the user asks to turn a short-drama script into storyboards and visual specs."
---

# Short Drama Storyboard — 短剧分镜与视觉设计

本 skill 是 AI 短剧制作流水线的**阶段 4**,职责是把正式剧本(`docs/scripts/EP{01..NN}.md`)转换成**可执行的分镜脚本**与**视觉规范**,让阶段 5(short-drama-video-forge)能直接照 prompt 生产镜头,让阶段 6(short-drama-audio-forge)能取对白与音效。

---

## 一、输入与输出

**输入**(必读):
- `docs/scripts/EP{01..NN}.md`(阶段 3 产出,每集一文件,取对白/动作/场景/情绪)
- `docs/SHORT_DRAMA_BLUEPRINT.md`(取制作类型/工具链选型/画幅,判定是否图文短剧裁剪)
- `docs/VISUAL_SPEC.md`(若已存在则增量修订,不重写)

**输出**(固定路径,2 份产物,与总纲 §八 一致):
- `docs/STORYBOARD.md`(分镜脚本,人读+机读:每镜头含文生图/图生视频 prompt)
- `docs/VISUAL_SPEC.md`(视觉规范:角色卡/场景设定/风格基线/字幕样式/画幅安全区)

**关键**:分镜是阶段 5 的唯一画面依据,所有 prompt 必须"可执行"(见 §三.3 与 references/visual-prompt-engine.md),不允许模糊描述。

---

## 二、执行流程

```
0. 输入校验(见 二.0)
1. 定视觉基线:风格/画幅/分辨率/字幕安全区 → 先写 docs/VISUAL_SPEC.md 骨架
2. 逐集逐场拆镜头(见 三):对白驱动 + 动作驱动,遵循镜头语言规则(见 五)
3. 每镜头补全 12 字段(见 三.1),含文生图 prompt + 图生视频 prompt
4. 全剧角色/场景引用对齐 VISUAL_SPEC(见 六)
5. 自检(见 七),不通过回 2 修复
6. 简报(见 八)
```

### 二.0 输入校验

- `docs/scripts/` 不存在或无 `EP*.md` → 报错"剧本缺失,请先调用 short-drama-script",列出期望路径,直接退出
- 剧本格式异常(缺对白/场景标记)→ 报错指出文件与位置,回阶段 3 修复

---

## 三、分镜脚本(docs/STORYBOARD.md)

### 3.1 每镜头字段(12 项,缺一不可)

| 字段 | 示例 | 说明 |
|---|---|---|
| 镜头号 | `EP01-S01` | `EP{XX}-S{YY}` 两位编号,全剧唯一 |
| 景别 | 中景 | 远景/全景/中景/近景/特写 |
| 运镜 | 推 | 固定/推/拉/摇/移/跟/升降;图文短剧降级用缩放/平移模拟 |
| 时长 | 5s | 3-10 秒,含对白时间 |
| 画面描述 | 林晚在雨夜巷口回望,霓虹倒映水洼,冷蓝侧光 | 主体+动作+环境+光线,四要素齐 |
| 角色 | 林晚 | 引用 VISUAL_SPEC 角色 id |
| 场景 | 雨夜巷口 | 引用 VISUAL_SPEC 场景 id |
| 对白/字幕 | "你终于来了。" | 完整文本,供字幕与配音 |
| 情绪基调 | 紧张 | 一两个词,驱动光线与色调 |
| 音效 | 雨声+低频心跳 | 供 audio-forge,可选 |
| 文生图 prompt | 见 3.3 | 主体/动作/环境/光线/风格/画幅 9:16/角色参考 |
| 图生视频 prompt | 见 3.3 | 画面主体+运动描述+镜头运动+时长 |

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
- 文生图:portrait 9:16,林晚(reference:char/linwan.png,seed:20241,都市悬疑,冷色调,电影感),回望侧脸,雨夜巷口霓虹,冷蓝侧光,cinematic
- 图生视频:林晚缓缓回头,眼神从平静转锐利,镜头缓慢推近,5s
```

### 3.3 Prompt 可执行性(关键)

- **文生图 prompt 六要素**:主体 / 动作 / 环境 / 光线 / 风格 / 画幅(9:16);角色镜头必须带 `reference:char/{id}.png` + 固定 seed + 风格关键词
- **图生视频 prompt 四要素**:画面主体 / 运动描述 / 镜头运动 / 时长(秒)
- 模板与光线-情绪映射详见 `references/visual-prompt-engine.md`;命中风格基线时叠加基线关键词与负面词(见 VISUAL_SPEC §4.3)

---

## 四、视觉规范(docs/VISUAL_SPEC.md)

### 4.1 角色视觉设定卡(每个主要角色一张)

| 字段 | 说明 |
|---|---|
| 角色 id | `linwan`,全剧引用依据 |
| 外貌/服装/发型 | 高马尾/黑色风衣/利落碎发(描述到可生图粒度) |
| 年龄感 | 25 岁左右 |
| 风格关键词 | 都市悬疑 / 冷色调 / 电影感 |
| 一致性控制方式 | 固定 seed=20241 + reference:char/linwan.png(首帧定稿)+ 风格关键词三件套 |

### 4.2 场景设定(每个主要场景)

| 字段 | 说明 |
|---|---|
| 场景 id | `rainy_alley` |
| 环境 | 雨夜巷口,霓虹灯牌,水洼 |
| 氛围 | 压抑悬疑 |
| 光线 | 冷蓝侧光,雨丝可见 |
| 风格 | 都市悬疑,电影感 |

同场景固定 seed,光线按情绪基调微调(可多张环境变体)。

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

## 五、镜头语言规则(单集强制)

1. **单集 10-25 镜头**(总纲 §八);镜头数×平均时长 ≈ 单集时长(1-3 分钟)
2. **每集至少 1 个特写/近景**强化情绪(哭/笑/惊/杀意等)
3. **卡点镜头(结尾悬念)必须特写或大反差**,每集最后 1 镜必为卡点
4. **对话场景用正反打**:过肩(over-shoulder)或单侧(single)交替,同一人连续对白 ≤2 镜
5. 动作戏用远景/全景交代空间,近景跟拍;运镜表达升格/降格节奏
6. 镜头 3-10 秒节奏:信息量大 3-5s,情绪镜头 6-10s

规则展开(景别表/运镜表/正反打细则/卡点设计)见 `references/shot-language.md`。

---

## 六、角色一致性(全剧强制)

- 全剧同一角色所有镜头:**同一参考图 + 同一固定 seed + 同一组风格关键词**(三件套,写入 VISUAL_SPEC)
- 同角色首次出现即定稿参考图,后续镜头一律带 reference 参数
- 双人同框:主视角角色带参考,次视角角色在 prompt 中完整文字描述
- 场景同理:同场景固定 seed,光线按情绪基调微调
- 漂移镜头标 `[漂移]`,记录到 docs/ASSET_ISSUES.md 由阶段 5 用参考图重生成

---

## 七、自检清单(产出前逐项过)

- [ ] 镜头总数与剧本时长匹配:每集 镜头数×平均时长 ≈ 单集时长(±15%)
- [ ] 单集 10-25 镜头,每集至少 1 个特写/近景
- [ ] 每镜头 12 字段齐全,文生图+图生视频 prompt 均可执行(无模糊词)
- [ ] 角色/场景引用与 VISUAL_SPEC 完全一致(角色 id / 场景 id 可查)
- [ ] 每集结尾镜头是卡点镜头(特写或大反差)
- [ ] 画幅 9:16 / 1080x1920,字幕在安全区内
- [ ] 镜头时长 3-10s;对白时长 ≤ 镜头时长
- [ ] 图文短剧裁剪时,每镜头有文生图 prompt,图生视频 prompt 标注"静态图+模拟运镜"
- [ ] 自评:按 skill-auditor 执行后评测模式自查(可选)

---

## 八、交互约定

1. 读取剧本后直接产出 2 份产物,不向用户提问(仅当存在多套风格可选时,先用 AskUserQuestion 确认风格基线)
2. 产出后简报:"分镜与视觉规范已生成,共 {N} 镜头 / {M} 角色 / {K} 场景。等待质量门 Gate 3 校验后进入视频生产"
3. 不自行调用下游 skill;Gate 3 由 short-drama-quality-gate 介入,FAIL 时回到本 skill 修复

---

## references 使用指引(懒加载)

| 文件 | 何时读取 |
|------|---------|
| `references/shot-language.md` | 拆镜头时:景别/运镜/时长/正反打/卡点规则 |
| `references/visual-prompt-engine.md` | 写 prompt 时:文生图/图生视频模板与角色一致性控制 |
