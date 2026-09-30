---
name: "short-drama-asset-forge"
description: "Stage 4.5 of the AI short-drama production pipeline (asset baseline lock). Reads docs/ASSET_MANIFEST.json + docs/VISUAL_SPEC.md + docs/STORYBOARD.md, materializes the baseline assets (character key-art + variants, scene plates, plot props, voice timbre samples, style baseline token), writes assets/{char,scene,prop,voice,style}/ + docs/ASSET_BASELINE.md, and writes asset status/hash/lockedAt back into docs/ASSET_MANIFEST.json. Hard prerequisite for stage 5: video-forge may only consume locked assets. Use when scheduled by short-drama-forge-master after Gate 3, or when the user asks to produce / lock the character baseline (定妆) before mass production."
---

# Short Drama Asset Forge — 短剧资产定妆与基线锁定（阶段 4.5）

本 skill 是 AI 短剧制作流水线的**阶段 4.5**，也是整条流水线的**一致性中枢**。职责是在批量生产**之前**，把角色形象（含变体）、常驻场景、剧情道具、音色、风格基线一次性定稿并**锁定为不可静默变更的资产基线**，产出的 `assets/` 目录与 `docs/ASSET_MANIFEST.json` 是阶段 5(short-drama-video-forge) 与阶段 6(short-drama-audio-forge) 的**唯一资产来源**。

**解决的结构性风险**：短剧一集 10-25 镜头、全剧 60-100 集，角色形象若在批量生产时才"第一次被确定"，一旦不像就要全量返工 —— 成本后置到整条链路最贵的环节。

**核心信条（不可商量）**：
1. **无锁定资产，不得进入批量生产**：阶段 5 只允许引用 `status=locked` 的资产。
2. **资产是资产的唯一真源**：资产定义只存在于 `docs/ASSET_MANIFEST.json`，`production/manifest.json` 只准**引用**（id + variant + assetVersion + hash），不准复制定义。
3. **定妆必须人工确认**：候选图由本 skill 生成，但**锁定动作必须经用户确认**（见 §三.2 ★ 定妆确认门）。
4. **禁止静默改图**：任何资产替换都要版本递增 + 基线留痕 + 影响面报告。

---

## 一、输入与输出

**输入**（必读）：
- `docs/ASSET_MANIFEST.json`（阶段 4 short-drama-storyboard 产出，`status=declared` 的资产需求清册；本 skill 的唯一资产定义来源）
- `docs/VISUAL_SPEC.md`（角色卡/场景设定/风格基线/字幕样式，定妆图的文字依据）
- `docs/SHORT_DRAMA_BLUEPRINT.md`（工具链选型：文生图/TTS 工具；阶段裁剪：音频是否裁剪）
- `docs/STORYBOARD.md`（引用统计：各资产被多少镜头引用、引用在哪几集，用于判断 oneOff 与影响面）

**输出**（固定路径，与总纲 §八 严格一致，不允许自定义路径）：

| 产物 | 路径 | 说明 |
|---|---|---|
| 角色定妆图 | `assets/char/{charId}/{variantId}.png` | 每角色至少 `default` 变体；变体见 §四.1 |
| 场景定稿图 | `assets/scene/{sceneId}.png` | 常驻场景必产；oneOff 场景可免 |
| 道具定稿图 | `assets/prop/{propId}.png` | 剧情线索类道具必产 |
| 音色试音 | `assets/voice/{charId}.mp3` | 每角色一个 voiceId + 试音样本 |
| 风格基线卡 | `assets/style/baseline.json` | 全剧强制叠加的 locked 风格 token |
| 资产基线锁定表 | `docs/ASSET_BASELINE.md` | 锁定表 + 变更记录 + 豁免签字 |
| 资产需求清册（回写） | `docs/ASSET_MANIFEST.json` | 回写 status/assetVersion/hash/lockedAt |
| 变更影响面报告 | `docs/ASSET_IMPACT.md` | **仅在资产变更时**产出 |
| 失败清单 | `docs/ASSET_ISSUES.md` | 有失败/降级时追加 |

> **跨阶段契约**：Gate 3.5 资产门（short-drama-quality-gate）只按上表校验；阶段 5 只按上表读取。文件名与目录必须逐字一致。

---

## 二、执行流程

```
0. 输入校验（见 二.1）
1. 分类生成候选资产：char（含变体）→ scene → prop → voice → style
2. ★ 定妆确认门（见 三.2）：AskUserQuestion 逐角色确认候选图，用户选定或要求重出
3. 锁定：计算 hash、写 assetVersion/lockedAt、status=locked，回写 ASSET_MANIFEST.json
4. 产出 docs/ASSET_BASELINE.md 锁定表
5. 自检（见 §七），不通过回 1~3 修复
6. 简报（见 §八）
```

### 二.1 输入校验（执行前一次性）

- `docs/ASSET_MANIFEST.json` 缺失 → 报错「资产需求清册缺失，请先调用 short-drama-storyboard（阶段 4）」，列出期望路径，直接退出
- 清册存在但 `version` 非 `1.0` 或五类资产（`characters`/`scenes`/`props`/`voice`/`styleBaseline`）缺类 → 报错指出缺失类，回阶段 4 修复
- `docs/VISUAL_SPEC.md` 缺失 → 报错并退出（定妆图的文字依据不可省）
- 清册中某角色无 `variants[].default` → 回阶段 4 补齐（default 变体强制）
- 蓝图标注音频裁剪（口播/图文短剧）→ 跳过 `voice` 类，清册 `voice` 标记 `skipped: true`，其余照常

---

## 三、定妆流程与人工确认

### 三.1 生成策略（按资产类型）

| 资产类 | 生成策略 | 每类候选数 |
|---|---|---|
| 角色（父级） | 先定 `default` 变体为"母版"，其余变体一律以母版图作 reference 派生 | 每角色 2-4 张候选 |
| 角色变体 | 以 default 母版图 + 变体描述（换装/年龄/战损）重生成，seed 必须与 default **互异** | 每变体 2-3 张候选 |
| 场景 | 按 VISUAL_SPEC 场景设定卡出图，固定 seed；同场景多光线变体时以"基准光线"版为锁定版 | 每场景 2-3 张候选 |
| 道具 | 白底/极简背景产品图式，固定 seed，须能看清材质与磨损细节（线索类道具会被特写） | 每道具 2 张候选 |
| 音色 | 用角色首集台词/试音句合成，比对 VISUAL_SPEC 年龄性别气质 | 每角色 1-2 个候选音 |
| 风格 | 不产图，产 `assets/style/baseline.json`（token 固化，无需确认） | — |

### 三.2 ★ 定妆确认门（强制人工确认）

**这是本 skill 唯一允许向用户提问的节点，且不可跳过。** 候选图全部生成后：

1. **简报**：列出每个角色/变体的候选图路径 + 当前选中的推荐候选（默认取第一张）
2. **AskUserQuestion 询问**，选项固定 3 个：
   - 「确认定妆并锁定」（推荐）：按当前候选锁定，进入下一步
   - 「重出候选」：说明不满意的点（脸型/服装/气质/年龄感），重生成 ≤3 轮
   - 「改文字设定后重出」：回阶段 4 改 VISUAL_SPEC 角色卡，再回本阶段
3. **未确认不允许 lock**：未经用户确认的资产只能停在 `status=declared`
4. 角色多时**分批确认**（每批 ≤4 个角色），避免一次问太多

> 与总纲 §9.1 的关系：本门对应**人工确认点 4.5（定妆确认）**，位于 Gate 3 之后、Gate 3.5 之前。它比其它确认点更强：其它确认点是"阶段推进确认"，本点是"内容锁定确认"。

### 三.3 锁定动作（原子化）

对每个已确认资产依次执行：

1. 落盘到固定路径（`assets/...`）
2. 计算文件 `sha256`，取前 12 位写入 `hash`
3. 写 `status: "locked"`、`lockedAt`（ISO8601）、`assetVersion: 1`（变更时递增）、`lockedBy: "user-confirm"`
4. 回写 `docs/ASSET_MANIFEST.json`（**保持其余字段原样**，只改状态字段）
5. 追加一行到 `docs/ASSET_BASELINE.md` 锁定表

**幂等规则**：重跑本阶段时，`status=locked` 且文件存在且 hash 相等的资产**跳过**，不重复生成；只处理 `declared`/`degraded` 项。

---

## 四、五类资产规格

### 4.1 角色定妆（含变体，本 skill 的核心）

**定妆图硬性要求**（不达标不允许 lock）：
- 单人（无其他人物、无镜像分身）
- 正面或 3/4 侧脸，半身（角色识别主要靠脸型+发型+服装轮廓）
- 极简背景（纯色/浅景深），不抢主体
- 无文字、无水印、无 UI 边框
- 短边 ≥1024px（俯拍/远景图不可作定妆图）
- 格式 png

**变体（variant）机制** —— 解决"同角色跨集形象变化"：

| 变体触发场景 | 示例 variantId | 派生方式 |
|---|---|---|
| 常态（强制） | `default` | 母版，独立生成 |
| 年代/年龄跨度 | `student` / `young` / `elder` | 以 default 为 reference 派生 |
| 换装/身份伪装 | `disguise` / `uniform` | 以 default 为 reference 派生 |
| 战损/受伤/落难 | `injured` / `haggard` | 以 default 为 reference 派生 |
| 身份反转造型（中后段） | `reveal` | 以 default 为 reference 派生 |

**变体规则**：
1. 每个角色必须有且仅有 1 个 `default`；其余变体必须声明 `derivedFrom: "default"`
2. **同角色各变体 seed 必须互异**（同 seed 不同变体会产出同一张脸 → 角色认同断裂）
3. 变体只在剧情需要时创建；**不得为"丰富度"滥建**（每个变体都要跨集一致地维护，是持续成本）
4. 变体的 `episodes[]` 必须来自 STORYBOARD 实际引用（清册已统计），不得凭想象添加

### 4.2 场景定稿

- **常驻场景**（被 ≥2 集引用）必须定妆；一次性场景（仅 1 集且 <3 镜头）可标 `oneOff: true` 免定妆
- 固定 seed；同场景多光线变体时，`default` 取基准光线版，情绪光线在 prompt 时微调（不改 seed）
- 场景图要求：无人物或仅远景剪影（避免定妆图里带人脸导致后续融合）

### 4.3 剧情道具定稿

**判据**：凡进入 STORY_SPEC 秘密系统铺垫的道具（信物/怀表/照片/手机/信件/钥匙）**必须定妆**，因为道具漂移会直接破坏悬念铺垫 —— 观众认不出"同一个怀表"，伏笔就失效了。

- 固定 seed；要求材质、磨损、独特细节可辨（后续会有特写镜头）
- 在清册 `props[].significance` 标注剧情作用与首次暗示集数

### 4.4 音色资产（voice）

- 每角色一个 `voiceId`（如 `voice_linwan`），试音样本 `assets/voice/{charId}.mp3`（10-20 秒，含 2-3 种情感）
- 记录 `timbre`（音色描述）/`baseEmotion`（基准情感）/`speechRate`（基准语速）/`ttsVoiceName`（具体 TTS 音色名）
- **规则**：同一角色全剧同 `voiceId`；跨集音色不得漂移。阶段 6 audio-forge 只准按 `voiceId` 取音，不准自选音色
- 音色必须能从 VISUAL_SPEC 的年龄/性别/气质推导，不允许凭空选音

### 4.5 风格基线锁

产出 `assets/style/baseline.json`，把 VISUAL_SPEC §四 的风格基线固化为机读 token：

```json
{
  "id": "style_main",
  "keywords": ["都市悬疑", "冷色调", "电影感"],
  "negativeKeywords": ["低质量", "变形", "多余手指", "文字水印"],
  "colorTendency": "冷蓝+霓虹点缀",
  "lightMoodMap": { "紧张": "冷光硬影", "温馨": "暖光柔焦" },
  "lockedAt": "2025-01-01T10:00:00+08:00",
  "hash": "a1b2c3d4e5f6"
}
```

**规则**：阶段 5 生成任何 prompt 时**强制叠加** `keywords` + `negativeKeywords`；`lightMoodMap` 按镜头情绪取值。风格基线全剧唯一，禁止分集多套。

---

## 五、资产变更与版本（"锁"的真正价值）

锁定之后，资产**不是不能改，而是不能静默改**。变更走以下流程：

```
1. 用户要求改某资产（换参考图/调风格/改音色）
2. 影响面分析：扫 docs/STORYBOARD.md，列出引用该资产的全部镜头 id + 集号 + 是否已生产
3. 产出 docs/ASSET_IMPACT.md（模板见 references/failover-recipes.md）
4. AskUserQuestion 让用户决策：
   - 全量重生成受影响镜头（保一致性，成本高）
   - 接受已生产部分保留旧形象 + 标记（成本低，有漂移风险）
   - 回退本次变更（不改）
5. 执行变更：assetVersion + 1，重算 hash，旧版本记录移入 ASSET_BASELINE.md 变更记录
6. 受影响镜头按决策重跑阶段 5（manifest 相应镜头 status 重置为 pending）
```

**版本规则**：`assetVersion` 单调递增；基线表保留历史版本 hash 与变更原因，便于追溯"这一集用的是哪版定妆图"。

---

## 六、失败降级（与总纲 §6.2 的关系：资产类失败**不适用软降级**）

**原则**：镜头级资源失败可以软降级（一集里一个镜头用静态图能忍），**资产级失败不能** —— 一个坏资产会被 800+ 个镜头放大到全剧。

| 失败场景 | 处理 | 状态标记 | Gate 3.5 判定 |
|---|---|---|---|
| 文生图工具失败 | 重试 ≤3 次；仍失败 → 产占位图（纯色+角色名文字） | `degraded:placeholder` | **ERROR 硬阻断**（除非用户签字，见下） |
| 定妆图不达标（多人/带水印/短边不足） | 重生成 ≤3 次；仍不达标 → 该资产停 `declared` | `status: declared` | **ERROR 硬阻断** |
| 变体 seed 冲突 | 强制重分配 seed（保证互异） | 修正后重锁 | ERROR 若不修 |
| TTS 试音失败 | 切备选 TTS 重试 ≤2 次；仍失败 → 保留 voiceId 与音色描述，样本留空 | `voice.status: degraded` | **WARNING**（不阻断，阶段 6 仍可按 voiceId 生成） |
| 音频被裁剪（口播/图文短剧） | 清册 `voice.skipped: true` | — | 跳过该项校验（按通过计） |
| 工具链整体不可用 | 不静默降级：把「整剧只能出占位资产」的后果明确告知用户 | 全类 `degraded` | **ERROR**，需用户签字才可放行 |

**豁免签字机制**：资产类 ERROR 默认硬阻断。若用户明确接受风险（例："先用占位图，成片后补"），必须在 `docs/ASSET_BASELINE.md` 的「已知风险签字」栏写明**签字人 / 时间 / 接受的资产清单 / 后果**，Gate 3.5 才把对应 ERROR 降级为 WARNING。**无签字不得放行**，且所有降级项写入 `docs/ASSET_ISSUES.md`，最终汇总进 `docs/BUILD_REPORT.md`。

---

## 七、自检清单（产出前逐项过）

- [ ] 每个角色都有 `default` 变体且已 lock；变体 seed 互异
- [ ] 定妆图全部满足 §4.1 硬性要求（单人/半身/极简背景/无文字水印/短边 ≥1024px/png）
- [ ] 常驻场景（≥2 集引用）全部定妆；oneOff 场景已标 `oneOff: true`
- [ ] STORY_SPEC 秘密系统涉及的道具全部定妆
- [ ] 每角色有 voiceId + 试音样本（音频未裁剪时）；音色与 VISUAL_SPEC 气质一致
- [ ] `assets/style/baseline.json` 已产出，keywords/negativeKeywords 非空
- [ ] `docs/ASSET_MANIFEST.json` 回写完整：被引用资产 status 全为 locked，hash/assetVersion/lockedAt 无空值
- [ ] `docs/ASSET_BASELINE.md` 锁定表行数 = 已锁定资产数；hash 与清册逐条相等
- [ ] 变体 `episodes[]` 与 STORYBOARD 实际引用一致（无凭空变体、无空引用变体）
- [ ] 降级/失败项已写入 `docs/ASSET_ISSUES.md`；有豁免的已在基线表签字栏留痕
- [ ] 简报数字与文件系统实际一致（用命令数文件，不靠估算）

---

## 八、交互约定

1. 读取清册与 VISUAL_SPEC 后**先批量生成候选**，再进入定妆确认门（不要把生成过程变成多轮问答）
2. 定妆确认门按 §三.2 执行：角色 >4 个时分批；每批给候选图路径 + 推荐项
3. 全部锁定后简报：「资产基线已锁定：{N} 角色 / {M} 变体 / {S} 场景 / {P} 道具 / {V} 音色。基线表 docs/ASSET_BASELINE.md。等待 Gate 3.5 资产门校验后进入批量生产」
4. 不自行调用下游 skill；Gate 3.5 由 short-drama-quality-gate 介入，FAIL 时回到本 skill 修复
5. 被裁剪的阶段（音频裁剪）不产占位文件，但在清册显式标 `skipped: true`（总纲 §七「不允许跳步」）

---

## references 使用指引（懒加载）

| 文件 | 何时读取 |
|------|---------|
| `references/asset-manifest-schema.md` | 读/写 `docs/ASSET_MANIFEST.json` 时：完整字段定义、五类资产 schema、状态机、与 production/manifest.json 的引用关系 |
| `references/asset-baseline-rules.md` | 生成定妆图/变体/音色/风格卡时：定妆图技术规范、变体派生配方、音色映射细则、风格 token 规则 |
| `references/failover-recipes.md` | 失败或（因降级）需要留痕时：重试/占位图规范、ASSET_ISSUES 模板、ASSET_IMPACT 模板、豁免签字模板 |

## templates 使用指引

| 文件 | 用途 |
|------|------|
| `templates/ASSET_MANIFEST.example.json` | 清册完整示例（1 角色 2 变体 + 1 场景 + 1 道具 + 1 音色 + 风格卡），复制后按项目填写 |
| `templates/ASSET_BASELINE.template.md` | 基线锁定表模板（锁定表/变更记录/已知风险签字） |
