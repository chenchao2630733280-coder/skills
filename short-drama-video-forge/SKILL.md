---
name: "short-drama-video-forge"
description: "Stage 5 of the AI short-drama production pipeline. Reads docs/STORYBOARD.md and docs/VISUAL_SPEC.md, builds the machine-readable production manifest (production/manifest.json), then generates per-shot videos shots/{ep}/shot_{XX}.mp4 (static .png with simulated camera motion on failure). Use when scheduled by short-drama-forge-master after Gate 3, or when the user asks to generate short-drama shots/videos from a storyboard."
---

# Short Drama Video Forge — 短剧 AI 视频生成

本 skill 是 AI 短剧制作流水线的**阶段 5**,职责是消费分镜脚本与视觉规范,产出**机读生产清单** `production/manifest.json` 与**各集镜头视频** `shots/{ep}/shot_{XX}.mp4`;视频生成失败时降级为静态图 `shots/{ep}/shot_{XX}.png`。

---

## 一、输入与输出

**输入**(必读):
- `docs/STORYBOARD.md`(分镜,取每镜头 prompt/时长/景别/运镜/角色/场景)
- `docs/VISUAL_SPEC.md`(取角色参考图路径/seed/风格关键词/场景设定)
- `docs/SHORT_DRAMA_BLUEPRINT.md`(取工具链选型,决定调用哪些工具)

**输出**(固定路径,与总纲 §八 一致):
- `production/manifest.json`(机读生产清单,阶段 7 剪辑与 Gate 4 只读此文件)
- `shots/{ep}/shot_{XX}.mp4`(镜头视频)
- `shots/{ep}/shot_{XX}.png`(视频失败时的静态图降级)
- `docs/ASSET_ISSUES.md`(失败记录,有降级/失败时必写)

---

## 二、执行流程

```
0. 输入校验 + 解析 STORYBOARD/VISUAL_SPEC → 生成 manifest 骨架(见 scripts/manifest_builder.py)
1. 按 manifest 逐镜头执行:文生图 → 图生视频 → 质检 → 落盘(见 二.1)
2. 分批执行(每批一集),批间暂停,进度写回 manifest.status
3. 失败按 §六 降级链处理,全部写入 docs/ASSET_ISSUES.md
4. 输出汇总简报
```

### 二.0 输入校验

- `docs/STORYBOARD.md` / `docs/VISUAL_SPEC.md` 缺失 → 报错并退出,提示先调用 short-drama-storyboard
- manifest 生成后必须通过 §三 schema 校验(每镜头字段非空、与 STORYBOARD 镜头数一致)

### 二.1 每镜头生成流水线

```
文生图(§四 工具A) → 落盘临时图
  → 图生视频(§四 工具B)
  → 质检:时长 3-10s / 分辨率 1080x1920 / 内容与 prompt 一致性
  → 落盘 shots/{ep}/shot_{XX}.mp4 → manifest.status=done
```

质检不合格或工具失败 → 按 §六 重试(≤3 次)/降级,状态写 failed/degraded。

---

## 三、production/manifest.json(中枢契约)

**字段与总纲 §八 固定路径严格一致**;阶段 7(short-drama-edit)与 Gate 4 只读此文件,不读 STORYBOARD。

### 3.1 Schema 示例(1 集 2 镜)

```json
{
  "version": "1.0",
  "project": {
    "title": "雨夜追凶",
    "totalEpisodes": 60,
    "aspectRatio": "9:16",
    "resolution": [1080, 1920],
    "style": "都市悬疑"
  },
  "toolchain": {
    "textToImage": "即梦",
    "imageToVideo": "可灵(Kling)"
  },
  "characters": [
    {
      "id": "linwan",
      "refImage": "char/linwan.png",
      "seed": 20241,
      "styleKeywords": ["都市悬疑", "冷色调", "电影感"],
      "description": "黑色风衣,高马尾,25 岁女性"
    }
  ],
  "scenes": [
    { "id": "rainy_alley", "description": "雨夜巷口,霓虹倒影,冷蓝侧光", "seed": 30011 }
  ],
  "episodes": [
    {
      "ep": "EP01",
      "shots": [
        {
          "id": "EP01-S01",
          "scriptFile": "docs/scripts/EP01.md",
          "imagePrompt": "portrait 9:16, 林晚(reference:char/linwan.png, seed:20241, 都市悬疑,冷色调,电影感), 回望侧脸, 雨夜巷口霓虹, 冷蓝侧光, cinematic",
          "videoPrompt": "林晚缓缓回头,眼神从平静转锐利,镜头缓慢推近,5s",
          "duration": 5,
          "shotSize": "中景",
          "camera": "推",
          "characters": ["linwan"],
          "scenes": ["rainy_alley"],
          "sound": "雨声+低频心跳",
          "subtitle": "你终于来了。",
          "status": "pending",
          "outputPath": "shots/EP01/shot_01.mp4"
        },
        {
          "id": "EP01-S02",
          "scriptFile": "docs/scripts/EP01.md",
          "imagePrompt": "portrait 9:16, 雨夜巷口空镜, 霓虹灯牌闪烁, 雨丝, 冷蓝侧光, 都市悬疑, cinematic",
          "videoPrompt": "雨丝缓慢飘落,霓虹灯牌闪烁,镜头缓慢横移,4s",
          "duration": 4,
          "shotSize": "远景",
          "camera": "移",
          "characters": [],
          "scenes": ["rainy_alley"],
          "sound": "雨声",
          "subtitle": "",
          "status": "pending",
          "outputPath": "shots/EP01/shot_02.mp4"
        }
      ]
    }
  ]
}
```

### 3.2 字段约束

| 字段 | 必填 | 说明 |
|---|---|---|
| project | 是 | 剧名/总集数/画幅/分辨率/风格 |
| toolchain | 是 | 文生图/图生视频工具名,按蓝图选型 |
| characters | 是 | 角色 id → 参考图路径/seed/风格关键词/描述 |
| scenes | 是 | 场景 id → 描述/seed |
| episodes[].shots[] | 是 | 每镜 12 字段(见下),与 STORYBOARD 一一对应 |
| id | 是 | `EP{XX}-S{YY}`,全剧唯一 |
| scriptFile | 是 | 来源剧本文件路径 |
| imagePrompt / videoPrompt | 是 | 直接取自 STORYBOARD,可执行 |
| duration / shotSize / camera | 是 | 时长 3-10s |
| characters / scenes | 是 | 引用上表 id,可空数组(空镜) |
| sound / subtitle | 是 | 可空字符串 |
| status | 是 | pending / done / failed / degraded(降级类型见 §六) |
| outputPath | 是 | `shots/{ep}/shot_{XX}.mp4`,降级时改 `.png` |

**状态回写**:每镜头完成后实时更新 status;增量重跑时,status=done 且文件存在的镜头跳过,不重复生成。

---

## 四、工具调用配方(按总纲 §3.2)

| 环节 | 默认推荐 | 备选 | 要点 |
|---|---|---|---|
| 文生图 | 即梦 | Midjourney、SD(ComfyUI)、Flux | 角色一致性高→即梦/SD 控图(reference+seed);出图快→即梦 |
| 图生视频 | 可灵(Kling) | 即梦、Runway、Pika、海螺(MiniMax)、Sora | 画质优先→Sora/Runway;中文生态+低成本→可灵/即梦;单镜头 5-10s |

**每工具输入参数模板 / 注意事项 / 失败重试次数(≤3)详见 `references/tool-recipes.md`**;执行时按蓝图 toolchain 加载对应小节,工具不可用时切备选(见 §六)。

---

## 五、角色一致性控制

- 用 VISUAL_SPEC 的角色参考图(`refImage`)+ 固定 seed + 风格关键词三件套注入每个镜头
- 文生图阶段:同角色同 seed + reference 图;首帧定稿后,后续镜头以定稿图作 reference
- 生成后比对参考图(发型/服装/肤色/比例),漂移镜头标 `degraded:"character-drift"` 并建议用参考图重生成(≤2 次)
- 详见 `references/character-consistency.md`

---

## 六、失败降级(与总纲 §6.2 完全一致)

| 失败场景 | 降级策略 | manifest 标记 |
|---|---|---|
| 图生视频失败(重试 ≤3 次仍失败) | 静态图 + 缩放/平移模拟运镜(ffmpeg zoompan,见 references/failover-recipes.md),落盘 `.png` | `degraded:"static-image"` |
| 文生图失败 | 纯色 + 文字占位图,标注"待人工出图" | `degraded:"placeholder"` |
| 视频生成接口全部不可用 | 整剧降级图文短剧模式(图+卡点+字幕+BGM,阶段 7 按图卡合成) | `degraded:"image-text-drama"` |
| 角色一致性漂移 | 标记受影响镜头,建议用角色参考图重新生成 | `degraded:"character-drift"` |
| 批量生成超时 | 分批执行(每批一集),批间暂停,进度写回 status | `status:"failed"` + 原因 |

**所有降级写入 `docs/ASSET_ISSUES.md`**(模板见 references/failover-recipes.md),不允许静默吞掉。

---

## 七、自检清单(产出后逐项过)

- [ ] manifest 每镜头字段完整(12 字段),status 无 pending 残留(或已标记原因)
- [ ] 每集镜头数与 STORYBOARD 一致,id 一一对应
- [ ] 文件命名符合固定路径:shots/EP{XX}/shot_{XX}.mp4(.png)
- [ ] 视频分辨率 1080x1920,时长 3-10s(ffprobe 抽查)
- [ ] 降级项已标记(degradeType 明确)并写入 ASSET_ISSUES.md
- [ ] 角色一致性:漂移镜头已标 character-drift 并建议重生成
- [ ] 汇总简报数字与文件系统实际一致

---

## 八、交互约定

1. 读取 STORYBOARD/VISUAL_SPEC 后直接开工,不向用户提问(工具链选型缺失时按总纲 §3.2 默认链执行并标注)
2. 每批一集,完成一集简报一次进度(镜头完成数/失败数/降级数)
3. 全部完成后简报:"生产清单与镜头已生成,共 {N} 镜头({M} 视频 / {K} 静态图降级 / {L} 占位),失败记录见 docs/ASSET_ISSUES.md"
4. 与 short-drama-audio-forge 并行执行;不自行调用下游 skill(Gate 4 后由总纲确认)

---

## references 使用指引(懒加载)

| 文件 | 何时读取 |
|------|---------|
| `references/tool-recipes.md` | 调用具体工具前:参数模板/注意事项/重试次数 |
| `references/failover-recipes.md` | 任一镜头失败时:模拟运镜/图文短剧/占位图规范 |
| `references/character-consistency.md` | 生成角色镜头前/一致性检查时 |
