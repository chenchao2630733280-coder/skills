---
name: "short-drama-video-forge"
description: "Stage 5 of the AI short-drama production pipeline. Reads docs/STORYBOARD.md, docs/VISUAL_SPEC.md and the LOCKED baseline docs/ASSET_MANIFEST.json, builds the machine-readable production manifest (production/manifest.json) that REFERENCES the locked assets by id+variant+hash, then generates per-shot videos shots/{ep}/shot_{XX}.mp4 (static .png with simulated camera motion on failure). Hard-gated on locked assets: it must never generate from a declared or degraded asset. Use when scheduled by short-drama-forge-master after Gate 3.5, or when the user asks to generate short-drama shots/videos from a storyboard."
---

# Short Drama Video Forge — 短剧 AI 视频生成

本 skill 是 AI 短剧制作流水线的**阶段 5**,职责是消费分镜脚本、视觉规范与**已锁定的资产基线**,产出**机读生产清单** `production/manifest.json` 与**各集镜头视频** `shots/{ep}/shot_{XX}.mp4`;视频生成失败时降级为静态图 `shots/{ep}/shot_{XX}.png`。

**硬前置(不可绕过)**:本阶段**只允许消费 `status=locked` 的资产**。参考图、seed、风格关键词、音色全部来自 `docs/ASSET_MANIFEST.json`(由阶段 4.5 定妆锁定);发现未锁定/缺失/降级未签字的资产 → **直接报错退出,不生成任何镜头**(Gate 3.5 是这条约束的守门人)。

**本阶段的一致性职责**:不是"决定角色长什么样"(那已在阶段 4.5 定稿),而是"**忠实使用**那个样子" —— 每个角色镜头严格注入锁定参考图 + 该变体 seed + 风格基线 token,并在 manifest 中记录所用资产的版本与 hash。

---

## 一、输入与输出

**输入**(必读):
- `docs/STORYBOARD.md`(分镜,取每镜头 prompt/时长/景别/运镜/角色(+变体)/场景/道具)
- `docs/ASSET_MANIFEST.json`(**资产唯一真源**:取 refImage 路径/seed/styleKeywords/变体表/风格基线 token;所有资产必须 `status=locked`)
- `docs/VISUAL_SPEC.md`(取镜头级补充描述:场景设定、道具设定、字幕样式安全区)
- `docs/SHORT_DRAMA_BLUEPRINT.md`(取工具链选型,决定调用哪些工具)

**输出**(固定路径,与总纲 §八 一致):
- `production/manifest.json`(机读生产清单,阶段 7 剪辑与 Gate 4 只读此文件;**只引用资产,不复制定义**)
- `shots/{ep}/shot_{XX}.mp4`(镜头视频)
- `shots/{ep}/shot_{XX}.png`(视频失败时的静态图降级)
- `docs/ASSET_ISSUES.md`(失败记录,有降级/失败时必写)

---

## 二、执行流程

```
0. 输入校验(**含资产锁定硬校验**) + 解析 STORYBOARD/ASSET_MANIFEST/VISUAL_SPEC → 生成 manifest 骨架(见 scripts/manifest_builder.py)
1. 按 manifest 逐镜头执行:文生图 → 图生视频 → 质检 → 落盘(见 二.1)
2. 分批执行(每批一集),批间暂停,进度写回 manifest.status
3. 失败按 §六 降级链处理,全部写入 docs/ASSET_ISSUES.md
4. 输出汇总简报
```

### 二.0 输入校验(含资产锁定硬校验)

- `docs/STORYBOARD.md` / `docs/VISUAL_SPEC.md` / `docs/ASSET_MANIFEST.json` 缺失 → 报错并退出,提示先调用 short-drama-storyboard(阶段 4)与 short-drama-asset-forge(阶段 4.5)
- **资产锁定校验(硬前置)**:扫描清册中被本剧引用的每条资产,逐条检查
  | 检查 | 不通过行为 |
  |---|---|
  | `status == "locked"`(或 `skipped`) | **报错退出**:列出未锁定资产清单,提示回阶段 4.5 定妆并过 Gate 3.5 |
  | `refImage`/`samplePath` 文件存在 | 报错退出,列出缺失文件路径 |
  | 文件 sha256 前 12 位 == 清册 `hash` | 报错退出(资产被偷换),提示回阶段 4.5 走变更流程 |
  | 风格基线唯一且 `status=locked` | 报错退出 |
- 资产校验全部通过后,把 `sourceHash`(清册文件自身 hash)与各资产 hash **原样**写入 manifest 的 `assets` 块
- manifest 生成后必须通过 §三 schema 校验(每镜头字段非空、与 STORYBOARD 镜头数一致、无资产定义副本)

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
  "assets": {
    "source": "docs/ASSET_MANIFEST.json",
    "sourceVersion": "1.0",
    "sourceHash": "1a2b3c4d5e6f",
    "characters": [
      { "id": "linwan", "variant": "default", "assetVersion": 1, "hash": "a1b2c3d4e5f6" },
      { "id": "linwan", "variant": "student", "assetVersion": 1, "hash": "b2c3d4e5f6a1" }
    ],
    "scenes": [ { "id": "rainy_alley", "assetVersion": 1, "hash": "c3d4e5f6a1b2" } ],
    "props": [ { "id": "prop_watch", "assetVersion": 1, "hash": "d4e5f6a1b2c3" } ],
    "voice": [ { "id": "voice_linwan", "assetVersion": 1, "hash": "f6a1b2c3d4e5" } ],
    "styleBaseline": { "id": "style_main", "assetVersion": 1, "hash": "e5f6a1b2c3d4" }
  },
  "episodes": [
    {
      "ep": "EP01",
      "shots": [
        {
          "id": "EP01-S01",
          "scriptFile": "docs/scripts/EP01.md",
          "imagePrompt": "portrait 9:16, 林晚(reference:assets/char/linwan/default.png, seed:20241, 都市悬疑,冷色调,电影感), 回望侧脸, 雨夜巷口霓虹, 冷蓝侧光, cinematic, 无文字, 无水印",
          "videoPrompt": "林晚缓缓回头,眼神从平静转锐利,镜头缓慢推近,5s",
          "duration": 5,
          "shotSize": "中景",
          "camera": "推",
          "characters": ["linwan"],
          "charVariants": { "linwan": "default" },
          "scenes": ["rainy_alley"],
          "props": [],
          "sound": "雨声+低频心跳",
          "subtitle": "你终于来了。",
          "status": "pending",
          "outputPath": "shots/EP01/shot_01.mp4"
        },
        {
          "id": "EP01-S02",
          "scriptFile": "docs/scripts/EP01.md",
          "imagePrompt": "portrait 9:16, 雨夜巷口空镜, 霓虹灯牌闪烁, 雨丝, 冷蓝侧光, 都市悬疑, cinematic, 无文字, 无水印",
          "videoPrompt": "雨丝缓慢飘落,霓虹灯牌闪烁,镜头缓慢横移,4s",
          "duration": 4,
          "shotSize": "远景",
          "camera": "移",
          "characters": [],
          "charVariants": {},
          "scenes": ["rainy_alley"],
          "props": ["prop_watch"],
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
| **assets** | **是** | **资产引用块**:`source` 指向清册 + 每类资产的 `id`/`variant`/`assetVersion`/`hash`;**禁止**在此写 `refImage`/`seed`/`styleKeywords` 定义副本(Gate 4.9 阻断) |
| episodes[].shots[] | 是 | 每镜 12 字段(见下)+ 2 个可选扩展字段,与 STORYBOARD 一一对应 |
| id | 是 | `EP{XX}-S{YY}`,全剧唯一 |
| scriptFile | 是 | 来源剧本文件路径 |
| imagePrompt / videoPrompt | 是 | 直接取自 STORYBOARD,可执行(reference 路径必须是 `assets/char/{id}/{variant}.png`) |
| duration / shotSize / camera | 是 | 时长 3-10s |
| characters / scenes | 是 | 引用清册 id,可空数组(空镜) |
| **charVariants** | **可选扩展** | `{"角色id": "变体id"}`;缺省项即该角色 `default` 变体。**非 default 变体必填** |
| **props** | **可选扩展** | 引用清册 `props[].id`,空数组表示无道具 |
| sound / subtitle | 是 | 可空字符串 |
| status | 是 | pending / done / failed / degraded(降级类型见 §六) |
| outputPath | 是 | `shots/{ep}/shot_{XX}.mp4`,降级时改 `.png` |

**状态回写**:每镜头完成后实时更新 status;增量重跑时,status=done 且文件存在**且所用资产 hash 未变**的镜头跳过。**资产 hash 变了 → 该资产相关的全部已生成镜头 status 重置为 pending**(这正是资产层的价值:变更影响面可精确计算)。

**快照字段(可选但推荐)**:每镜头可加 `assetSnapshot: {"linwan": {"variant":"default","assetVersion":1,"hash":"a1b2…"}}`,用于事后追溯"这一集到底用的是哪版定妆图"。

---

## 四、工具调用配方(按总纲 §3.2)

| 环节 | 默认推荐 | 备选 | 要点 |
|---|---|---|---|
| 文生图 | 即梦 | Midjourney、SD(ComfyUI)、Flux | 角色一致性高→即梦/SD 控图(reference+seed);出图快→即梦 |
| 图生视频 | 可灵(Kling) | 即梦、Runway、Pika、海螺(MiniMax)、Sora | 画质优先→Sora/Runway;中文生态+低成本→可灵/即梦;单镜头 5-10s |

**每工具输入参数模板 / 注意事项 / 失败重试次数(≤3)详见 `references/tool-recipes.md`**;执行时按蓝图 toolchain 加载对应小节,工具不可用时切备选(见 §六)。

---

## 五、角色一致性控制(消费锁定资产,不自行决定形象)

**前提**:角色长什么样已在阶段 4.5 定稿并锁定。本阶段**没有"选参考图"的权限** —— 只从 `docs/ASSET_MANIFEST.json` 按 (角色 id, 变体 id) 取资产。

- **三件套强制注入**:`refImage`(锁定定妆图路径)+ `seed`(该**变体**的 seed)+ `styleKeywords` + 风格基线 `negativeKeywords`
- **变体路由**:镜头 `charVariants` 指向哪个变体,就取哪个变体的参考图与 seed;缺省取 `default`
  - 例:`EP07-S03` 的 `charVariants: {"linwan":"student"}` → 用 `assets/char/linwan/student.png` + seed 20242
  - **禁止**用 default 的参考图去渲染非 default 变体(这是"回忆线看起来不像同一个人"的典型成因)
- **道具一致**:镜头 `props[]` 引用的道具,其外观必须以 `assets/prop/{id}.png` 为准(尤其线索类道具的特写镜头)
- **漂移检测**:生成后比对锁定参考图(发型/服装/肤色/比例),判据见 `references/character-consistency.md` §4
  - 漂移 → 用**同一把锁定的参考图 + seed** 重生成 ≤2 次(不是换参考图,而是重试)
  - 仍漂移 → 该镜头标 `degraded:"character-drift"`,并在 ASSET_ISSUES.md 记录
  - 若**系统性漂移**(同一资产多镜头都漂)→ 说明定妆图本身不好用,应回阶段 4.5 走**资产变更流程**,而不是在本阶段逐镜头硬凑
- **记录**:每镜头落盘后写 `assetSnapshot`(所用资产的 assetVersion + hash),保证可追溯
- 详见 `references/character-consistency.md`

---

## 六、失败降级(与总纲 §6.2 完全一致)

| 失败场景 | 降级策略 | manifest 标记 |
|---|---|---|
| 图生视频失败(重试 ≤3 次仍失败) | 静态图 + 缩放/平移模拟运镜(ffmpeg zoompan,见 references/failover-recipes.md),落盘 `.png` | `degraded:"static-image"` |
| 文生图失败 | 纯色 + 文字占位图,标注"待人工出图" | `degraded:"placeholder"` |
| 视频生成接口全部不可用 | 整剧降级图文短剧模式(图+卡点+字幕+BGM,阶段 7 按图卡合成) | `degraded:"image-text-drama"` |
| 角色一致性漂移(单镜头) | 用**同一锁定参考图 + seed** 重生成 ≤2 次;仍漂移标记并记录 | `degraded:"character-drift"` |
| 批量生成超时 | 分批执行(每批一集),批间暂停,进度写回 status | `status:"failed"` + 原因 |

**以下情形不走降级,直接报错退出(硬前置违约)**:

| 情形 | 行为 |
|---|---|
| 被引用资产 `status != locked`(declared/degraded 未签字) | **报错退出**,列出未锁定资产,回阶段 4.5 |
| 资产实体文件缺失 | **报错退出**,列出缺失路径,回阶段 4.5 |
| 文件 hash ≠ 清册 hash(资产被偷换) | **报错退出**,提示回阶段 4.5 走变更流程 |
| 风格基线缺失或未锁定 | **报错退出** |
| 系统性漂移(同一资产多镜头漂移) | **报错退出**,建议回阶段 4.5 做资产变更(影响面报告 + 用户决策) |

**所有降级写入 `docs/ASSET_ISSUES.md`**(模板见 references/failover-recipes.md),不允许静默吞掉。

**降级边界提醒**:本阶段的降级只作用于**单个镜头**。任何"改动用哪把参考图/哪个 seed/哪套风格词"的动作都不属于本阶段的降级权限 —— 那是资产变更,必须回阶段 4.5。

---

## 七、自检清单(产出后逐项过)

- [ ] **开工前资产锁定校验已通过**(全部 locked + 文件存在 + hash 相等 + 风格基线唯一)
- [ ] manifest 含 `assets` 引用块,`source`/`sourceHash`/逐条 hash 齐备
- [ ] **manifest 内无 `refImage`/`seed`/`styleKeywords` 定义副本**(无双真源)
- [ ] 每镜头 `charVariants` 与 STORYBOARD 变体标记一致;非 default 变体均已显式声明
- [ ] 每镜头 `assetSnapshot` 已写入(可追溯所用资产版本)
- [ ] manifest 每镜头字段完整(12 字段),status 无 pending 残留(或已标记原因)
- [ ] 每集镜头数与 STORYBOARD 一致,id 一一对应
- [ ] 文件命名符合固定路径:shots/EP{XX}/shot_{XX}.mp4(.png)
- [ ] 视频分辨率 1080x1920,时长 3-10s(ffprobe 抽查)
- [ ] 降级项已标记(degradeType 明确)并写入 ASSET_ISSUES.md
- [ ] 角色一致性:漂移镜头已标 character-drift;系统性漂移已升级为资产变更建议而非硬凑
- [ ] 汇总简报数字与文件系统实际一致

---

## 八、交互约定

1. 读取 STORYBOARD/ASSET_MANIFEST 后直接开工,不向用户提问(工具链选型缺失时按总纲 §3.2 默认链执行并标注)
2. **资产未锁定不提问、不商量,直接报错退出**并说明回阶段 4.5 修复 —— 这是硬前置,不是可选项
3. 每批一集,完成一集简报一次进度(镜头完成数/失败数/降级数)
4. 出现系统性漂移时,简报并建议回阶段 4.5 做资产变更(附影响面规模),不自行换参考图
5. 全部完成后简报:"生产清单与镜头已生成,共 {N} 镜头({M} 视频 / {K} 静态图降级 / {L} 占位),资产引用 hash 校验 {通过/异常},失败记录见 docs/ASSET_ISSUES.md"
6. 与 short-drama-audio-forge 并行执行;不自行调用下游 skill(Gate 4 后由总纲确认)

---

## references 使用指引(懒加载)

| 文件 | 何时读取 |
|------|---------|
| `references/tool-recipes.md` | 调用具体工具前:参数模板/注意事项/重试次数 |
| `references/failover-recipes.md` | 任一镜头失败时:模拟运镜/图文短剧/占位图规范 |
| `references/character-consistency.md` | 生成角色镜头前/一致性检查时 |
| `../short-drama-asset-forge/references/asset-manifest-schema.md` | 读清册或生成 manifest 的 `assets` 引用块时:资产字段与引用契约(唯一真源) |
