# docs/ASSET_MANIFEST.json — 资产需求清册 Schema（v1.0）

> 本文件是短剧流水线的**资产唯一真源契约**。阶段 4 short-drama-storyboard 产出（`status=declared` 的需求清册），阶段 4.5 short-drama-asset-forge 回写状态（`locked`）并落地实体文件，Gate 3.5 与阶段 5/6 只按本文件校验与读取。

---

## 1. 两个 manifest 的分工（关键，避免双真源）

| 文件 | 谁产出 | 角色 | 内容 |
|---|---|---|---|
| `docs/ASSET_MANIFEST.json` | 阶段 4 声明 / 阶段 4.5 回写 | **资产唯一真源** | 资产定义：refImage 路径、seed、变体、音色、风格 token、锁定状态与 hash |
| `production/manifest.json` | 阶段 5 | **生产清单** | 每镜头生产参数 + **引用**资产（id/variant/assetVersion/hash），**不得复制**资产定义 |

**铁律**：`production/manifest.json` 里出现 `refImage`/`seed`/`styleKeywords` 的副本 = 双真源缺陷。资产字段一律通过 `assets` 引用块指向本清册，Gate 4 校验两侧 hash 相等。

---

## 2. 顶层结构

```json
{
  "version": "1.0",
  "project": { },
  "styleBaseline": { },
  "characters": [ ],
  "scenes": [ ],
  "props": [ ],
  "voice": [ ],
  "usage": { },
  "summary": { }
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| version | 是 | 固定 `"1.0"`；schema 变更时递增 |
| project | 是 | 剧名/总集数/画幅/分辨率/风格（与蓝图 §3 一致） |
| styleBaseline | 是 | 风格基线锁（§6） |
| characters | 是 | 角色资产（含变体，§3） |
| scenes | 是 | 场景资产（§4） |
| props | 是 | 道具资产（§5） |
| voice | 是 | 音色资产（§7）；音频被裁剪时为空数组 + `skipped: true` |
| usage | 是 | 引用统计，由阶段 4 从 STORYBOARD 扫描得出（决定 oneOff / 影响面） |
| summary | 是 | 计数汇总，供 Gate 3.5 快速对账 |

---

## 3. characters[]（角色 + 变体）

```json
{
  "id": "linwan",
  "name": "林晚",
  "role": "protagonist",
  "ageRange": "25 岁左右",
  "appearsIn": ["EP01", "EP02", "EP07"],
  "shotRefCount": 412,
  "variants": [
    {
      "variantId": "default",
      "label": "常态",
      "appearance": "高马尾/黑色风衣/利落碎发",
      "refImage": "assets/char/linwan/default.png",
      "seed": 20241,
      "styleKeywords": ["都市悬疑", "冷色调", "电影感"],
      "derivedFrom": null,
      "episodes": ["EP01", "EP02"],
      "status": "locked",
      "assetVersion": 1,
      "hash": "a1b2c3d4e5f6",
      "lockedAt": "2025-01-01T10:00:00+08:00",
      "lockedBy": "user-confirm"
    },
    {
      "variantId": "student",
      "label": "学生时代（回忆线）",
      "appearance": "齐耳短发/白衬衫/校服外套",
      "refImage": "assets/char/linwan/student.png",
      "seed": 20242,
      "styleKeywords": ["都市悬疑", "冷色调", "电影感"],
      "derivedFrom": "default",
      "episodes": ["EP07"],
      "status": "locked",
      "assetVersion": 1,
      "hash": "b2c3d4e5f6a1",
      "lockedAt": "2025-01-01T10:00:00+08:00",
      "lockedBy": "user-confirm"
    }
  ]
}
```

| 字段 | 必填 | 约束 |
|---|---|---|
| id | 是 | 小写字母/下划线，全剧唯一，与 STORYBOARD「角色」列一致 |
| name | 是 | 中文名 |
| role | 是 | `protagonist` / `antagonist` / `romance` / `ally` / `traitor` / `secret-holder` / `mirror` / `minor` |
| ageRange | 是 | 文字描述，供音色与外观推导 |
| appearsIn | 是 | 集号数组，来自 STORYBOARD 实际引用 |
| shotRefCount | 是 | 被引用镜头数（含变体折算），用于成本估算 |
| variants | 是 | ≥1；**必须含且仅含 1 个 `variantId="default"`** |
| variants[].variantId | 是 | `default` / `student` / `young` / `elder` / `disguise` / `uniform` / `injured` / `haggard` / `reveal` / 自定义 |
| variants[].refImage | 是 | 固定路径 `assets/char/{charId}/{variantId}.png` |
| variants[].seed | 是 | 整数；**同角色各变体 seed 必须互异** |
| variants[].derivedFrom | 是 | `default` 为 `null`，其余必为 `"default"` |
| variants[].episodes | 是 | 引用该变体的集号，与 STORYBOARD 一致（不得为空数组） |
| variants[].status | 是 | `declared` / `locked` / `degraded`（见 §8 状态机） |
| variants[].assetVersion | 锁定后必填 | 整数，单调递增，起始 1 |
| variants[].hash | 锁定后必填 | 文件 sha256 前 12 位 |
| variants[].lockedAt | 锁定后必填 | ISO8601 |
| variants[].lockedBy | 锁定后必填 | `user-confirm`（人工确认）；其它值 Gate 3.5 视同未锁定 |

---

## 4. scenes[]

```json
{
  "id": "rainy_alley",
  "name": "雨夜巷口",
  "description": "雨夜巷口，霓虹灯牌，水洼倒影",
  "mood": "压抑悬疑",
  "lighting": "冷蓝侧光，雨丝可见",
  "refImage": "assets/scene/rainy_alley.png",
  "seed": 30011,
  "oneOff": false,
  "episodes": ["EP01", "EP02", "EP11"],
  "shotRefCount": 96,
  "status": "locked",
  "assetVersion": 1,
  "hash": "c3d4e5f6a1b2",
  "lockedAt": "2025-01-01T10:00:00+08:00",
  "lockedBy": "user-confirm"
}
```

| 字段 | 必填 | 约束 |
|---|---|---|
| id / name / description | 是 | 与 VISUAL_SPEC 场景设定卡一致 |
| mood / lighting | 是 | 供 prompt 情绪-光线映射 |
| refImage | 是（oneOff 时可为 null） | 固定路径 `assets/scene/{sceneId}.png` |
| seed | 是（oneOff 时可为 null） | 同场景全剧固定 |
| oneOff | 是 | `true` = 仅 1 集且 <3 镜头的一次性场景，可免定妆（Gate 3.5 跳过其文件检查） |
| episodes / shotRefCount | 是 | 引用统计 |

---

## 5. props[]

```json
{
  "id": "prop_watch",
  "name": "旧怀表",
  "significance": "终极真相线索：表盖内侧刻字指向真凶",
  "firstHintEp": "EP03",
  "refImage": "assets/prop/prop_watch.png",
  "seed": 41002,
  "episodes": ["EP03", "EP12", "EP48"],
  "shotRefCount": 14,
  "status": "locked",
  "assetVersion": 1,
  "hash": "d4e5f6a1b2c3",
  "lockedAt": "2025-01-01T10:00:00+08:00",
  "lockedBy": "user-confirm"
}
```

| 字段 | 必填 | 约束 |
|---|---|---|
| significance | 是 | 剧情作用；**凡进入 STORY_SPEC 秘密系统铺垫的道具必须定妆** |
| firstHintEp | 是 | 首次暗示集数（Gate 3.5 校验其 ≥ EP01 且 ≤ 总集数） |
| refImage / seed | 是 | 固定路径 `assets/prop/{propId}.png`；固定 seed |

---

## 6. styleBaseline

```json
{
  "id": "style_main",
  "name": "都市悬疑-冷调电影感",
  "keywords": ["都市悬疑", "冷色调", "电影感"],
  "negativeKeywords": ["低质量", "变形", "多余手指", "文字水印"],
  "colorTendency": "冷蓝+霓虹点缀",
  "lightMoodMap": { "紧张": "冷光硬影", "温馨": "暖光柔焦" },
  "status": "locked",
  "assetVersion": 1,
  "hash": "e5f6a1b2c3d4",
  "lockedAt": "2025-01-01T10:00:00+08:00",
  "lockedBy": "user-confirm",
  "cardPath": "assets/style/baseline.json"
}
```

**规则**：全剧唯一（非数组）；`keywords`/`negativeKeywords` 非空；阶段 5 生成任何 prompt 强制叠加；`lightMoodMap` 按镜头情绪取值。

---

## 7. voice[]

```json
{
  "id": "voice_linwan",
  "charId": "linwan",
  "timbre": "低沉磁性女声，略带沙哑",
  "baseEmotion": "平静",
  "speechRate": 1.0,
  "ttsVoiceName": "zh-CN-XiaoxiaoNeural",
  "samplePath": "assets/voice/linwan.mp3",
  "emotionTags": ["平静", "愤怒", "悲伤", "阴险"],
  "status": "locked",
  "assetVersion": 1,
  "hash": "f6a1b2c3d4e5",
  "lockedAt": "2025-01-01T10:00:00+08:00",
  "lockedBy": "user-confirm"
}
```

| 字段 | 必填 | 约束 |
|---|---|---|
| id | 是 | `voice_{charId}`，与 characters[].id 对应 |
| charId | 是 | 必须在 characters[] 中存在 |
| timbre / baseEmotion / speechRate | 是 | 由 VISUAL_SPEC 年龄/性别/气质推导 |
| ttsVoiceName | 是 | 具体工具的音色名（按蓝图 toolchain 的 TTS 工具） |
| samplePath | 是 | `assets/voice/{charId}.mp3`（TTS 失败可留空并标 degraded） |
| emotionTags | 是 | 该角色在全剧用到的情感标签（阶段 6 只准用这些标签） |
| skipped | 音频裁剪时必填 | `true` 表示本类整体裁剪，Gate 3.5 跳过校验 |

---

## 8. 状态机（status）

```
declared ──(定妆生成 + 用户确认 + 落盘 + hash)──→ locked
   │                                                 │
   ├──(生成失败 / 不达标)──→ degraded ──(重试成功)──→ locked
   │                            │
   │                            └──(用户签字豁免)──→ degraded（放行，Gate 3.5 降为 WARNING）
   └──(变更)──→ declared（assetVersion+1，重新确认后回 locked）
```

| 状态 | 含义 | Gate 3.5 判定 |
|---|---|---|
| `declared` | 已声明未落地（仅阶段 4 产出后） | **ERROR**（阻止进入批量生产） |
| `locked` | 已落地 + 人工确认 + hash 记录 | PASS |
| `degraded` | 落地但质量/方式降级 | **ERROR**；基线表有用户签字则 WARNING |
| `skipped` | 该类被阶段裁剪（如音频） | 跳过校验（按通过计） |

---

## 9. usage / summary

```json
"usage": {
  "shotTotal": 900,
  "characterRefs": 812,
  "sceneRefs": 430,
  "propRefs": 26,
  "voiceLines": 640
},
"summary": {
  "characterCount": 7,
  "variantCount": 11,
  "sceneCount": 12,
  "propCount": 3,
  "voiceCount": 7,
  "assetTotal": 33,
  "degradedCount": 0
}
```

**用途**：`usage` 决定 oneOff 判定与变更影响面规模；`summary` 供 Gate 3.5 用 `wc -l`/文件计数对账（简报数字必须与文件系统实际一致）。

---

## 10. 与下游的引用契约

`production/manifest.json`（阶段 5 产出）中的引用块：

```json
"assets": {
  "source": "docs/ASSET_MANIFEST.json",
  "sourceVersion": "1.0",
  "sourceHash": "1a2b3c4d5e6f",
  "characters": [ { "id": "linwan", "variant": "default", "assetVersion": 1, "hash": "a1b2c3d4e5f6" } ],
  "scenes": [ { "id": "rainy_alley", "assetVersion": 1, "hash": "c3d4e5f6a1b2" } ],
  "props": [ { "id": "prop_watch", "assetVersion": 1, "hash": "d4e5f6a1b2c3" } ],
  "voice": [ { "id": "voice_linwan", "assetVersion": 1, "hash": "f6a1b2c3d4e5" } ],
  "styleBaseline": { "id": "style_main", "assetVersion": 1, "hash": "e5f6a1b2c3d4" }
}
```

- 镜头级：`shots[].characters` 保持 id 数组不变，非 default 变体用可选字段 `charVariants: {"linwan": "student"}` 声明（缺省即 `default`）；可选字段 `props: ["prop_watch"]`
- **Gate 4 校验**：manifest.assets 中每条 hash = 清册对应 hash；不一致 → `G4-ASSET-HASH-MISMATCH`（ERROR）
- **Gate 3.5 校验**：`docs/ASSET_MANIFEST.json` 自身完整性 + 实体文件存在 + 已锁定
