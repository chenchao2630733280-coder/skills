# Gate 0~4 检查项清单(逐项打勾)

本文件是 short-drama-quality-gate 的**执行清单**,执行每个 Gate 时对照本清单逐项打勾;检查项与 SKILL.md §三~§八 一一对应。

**勾选规则**:

| 标记 | 含义 | 对结论的影响 |
|---|---|---|
| [x] | 通过 | 计入 PASS |
| [ ] | 未通过(ERROR) | 计入 FAIL,硬阻断 |
| [~] | 无法校验(数据不足) | 计入"无法校验",结论 FAIL(数据不足),补齐后重跑 |
| [!] | 软问题(WARNING) | 不阻断,记录到报告 |

**结论规则**(与 SKILL.md §九 一致):任一 [ ] → FAIL;任一 [~] → FAIL(注明数据不足);仅 [x]/[!] → PASS。

---

## Gate 0 立项门(short-drama-blueprint 后)

输入:`docs/SHORT_DRAMA_BLUEPRINT.md`

| # | 检查项 | 通过条件 | 失败码 | 打勾 |
|---|---|---|---|---|
| 0.1 | 一句话定义 | ≤30 字 | G0-DEFINITION-TOO-LONG | [ ] |
| 0.2 | 制作类型明确 | 存在且 ∈ {全 AI 生成, 图文短剧, 真人实拍辅助, 口播短剧, AI 数字人型} | G0-TYPE-INVALID | [ ] |
| 0.3 | 类型与裁剪一致 | 阶段裁剪与类型特征匹配(口播短剧→跳过 storyboard/video-forge;图文短剧→跳过 video-forge;全 AI 生成→全流程) | G0-TYPE-TRIM-MISMATCH | [ ] |
| 0.4 | 工具链选型完整 | 文生图/图生视频/TTS/音乐/剪辑 5 环节均选定工具(裁剪环节标注"不适用"即可) | G0-TOOLCHAIN-INCOMPLETE | [ ] |
| 0.5 | 范围边界"不做" | 明确"不做"项 ≥3 | G0-SCOPE-NOT-ENOUGH | [ ] |
| 0.6 | 复杂度评级一致 | 评级与 6 维度打分(场景数/角色数/资产数/特效量/镜头数/外部依赖)结论一致 | G0-COMPLEXITY-MISMATCH | [ ] |
| 0.7 | 阶段裁剪逐阶段标注 | 每个可裁剪阶段有"执行/跳过+理由"(阶段 4.5 与阶段 7 不裁剪) | G0-TRIM-INCOMPLETE | [ ] |
| 0.8 | 资产规模已估算 | 蓝图 §11 含资产总数(角色+变体+场景+道具+音色)与出图张数估算 | G0-ASSET-SCALE-MISSING | [ ] |
| 0.9 | 变体已逐个点名 | 需变体的角色已列明(年龄跨度/换装/战损/身份反转造型);确实未定时标注"待分镜阶段确定" | G0-VARIANT-UNPLANNED | [ ] |

---

## Gate 1 规格门(short-drama-spec 后)

输入:`docs/SHORT_DRAMA_BLUEPRINT.md`(总集数)+ `docs/STORY_SPEC.md` + `docs/EPISODE_OUTLINE.md`

| # | 检查项 | 通过条件 | 失败码 | 打勾 |
|---|---|---|---|---|
| 1.1 | 故事发动机八要素 | 主角/欲望/启动事件/不能退出原因/核心阻碍/对手/升级机制/最终选择 8 项齐全 | G1-ENGINE-MISSING | [ ] |
| 1.2 | 分集数与蓝图一致 | EPISODE_OUTLINE 集数 = 蓝图总集数 | G1-EPISODE-COUNT-MISMATCH | [ ] |
| 1.3 | 每集开场钩子+结尾卡点 | 大纲每集均有"开场钩子"与"结尾卡点"字段 | G1-HOOK-CLIFFHANGER-MISSING | [ ] |
| 1.4 | 卡点类型不连续重复 | 相邻两集卡点类型不同(情感/悬念/反转/危机等交替) | G1-CLIFFHANGER-REPEAT | [ ] |
| 1.5 | 情绪曲线结构 | 整部情绪曲线满足 3 爽点 / 2 反转 / 1 最低点 | G1-EMOTION-CURVE-WEAK | [ ] |
| 1.6 | 规格评分 | STORY_SPEC 评分 ≥60;<60 阻断 | G1-SCORE-LOW | [ ] |

---

## Gate 2 剧本门(short-drama-script 后)

输入:`docs/scripts/EP{01..NN}.md`(每集一文件)+ `docs/EPISODE_OUTLINE.md` + `docs/STORY_SPEC.md`(秘密揭露节奏)

| # | 检查项 | 通过条件 | 失败码 | 打勾 |
|---|---|---|---|---|
| 2.1 | 集数齐全且与大纲一致 | EP 文件数 = 大纲集数;编号 EP01..NN 连续无缺号 | G2-EPISODE-FILES-MISMATCH | [ ] |
| 2.2 | 开场 5 秒出钩子 | 每集开场(前 5 秒 / 前 2 句对白)即进入钩子 | G2-OPENING-HOOK-MISSING | [ ] |
| 2.3 | 结尾强卡点且类型与前集不同 | 每集结尾有强卡点;类型与前集不重复 | G2-ENDING-WEAK / G2-CLIFFHANGER-REPEAT | [ ] |
| 2.4 | 对白单句 ≤20 字 | 每句对白(不含标点)≤20 字 | G2-DIALOGUE-TOO-LONG | [ ] |
| 2.5 | 每集台词量 300-600 字 | 每集对白总字数 ∈ [300, 600] | G2-DIALOGUE-VOLUME-OUT | [ ] |
| 2.6 | 主角每集有具体行动 | 每集主角有推进剧情的主动行动(非纯旁观/被叙述) | G2-PROTAGONIST-PASSIVE | [ ] |
| 2.7 | 秘密揭露节奏一致 | 剧本各集揭露的秘密点与 STORY_SPEC 秘密系统节奏表一致 | G2-SECRET-RHYTHM-MISMATCH | [ ] |
| 2.8 | 时长估算 1-3 分钟 | 每集标注时长估算(或按台词量折算)∈ [1, 3] 分钟(总纲 §八) | G2-DURATION-OUT | [ ] |

---

## Gate 3 分镜门(short-drama-storyboard 后)

输入:`docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md` + `docs/ASSET_MANIFEST.json`(+ `docs/scripts/EP*.md` 对照结尾卡点)

| # | 检查项 | 通过条件 | 失败码 | 打勾 |
|---|---|---|---|---|
| 3.1 | 每镜头字段完整 | 景别/运镜/时长/画面描述/文生图 prompt/图生视频 prompt 6 字段齐全 | G3-SHOT-FIELD-MISSING | [ ] |
| 3.2 | 单集镜头数 10-25 | 每集镜头数 ∈ [10, 25](总纲 §八) | G3-SHOT-COUNT-OUT | [ ] |
| 3.3 | 镜头总时长≈单集时长 | 每集镜头时长之和与该集时长估算偏差 ≤ ±15% | G3-TIMING-MISMATCH | [ ] |
| 3.4 | 角色/场景/变体引用一致 | 分镜引用的角色/场景/变体均在 VISUAL_SPEC 与 ASSET_MANIFEST.json 有定义 | G3-REF-UNDEFINED | [ ] |
| 3.5 | 每集结尾是卡点镜头 | 每集最后一个镜头对应剧本结尾卡点(强冲突/反转/悬念画面) | G3-FINAL-SHOT-WRONG | [ ] |
| 3.6 | VISUAL_SPEC 要素完整 | 含角色母卡+变体子表/场景/道具/风格基线/字幕样式 | G3-VISUAL-SPEC-INCOMPLETE | [ ] |
| 3.7 | 资产需求清册 schema 合法 | ASSET_MANIFEST.json 可解析、version=1.0、五类齐全 | G3-ASSET-MANIFEST-INVALID | [ ] |
| 3.8 | 清册与分镜引用闭合 | 清册声明 ⊆ 分镜实际引用(无凭空资产)且 分镜引用 ⊆ 清册声明(无漏声明) | G3-ASSET-REF-MISMATCH | [ ] |
| 3.9 | 变体 seed 互异 | 同角色各变体 seed 互不相同 | G3-VARIANT-SEED-COLLISION | [ ] |

辅助软检查(不阻断):单镜头时长超出 3-10 秒(总纲 §八)的镜头 → 报告标 [!] WARNING。

> 本门**只校验声明层**;资产实体层(文件存在/已锁定/hash)由 Gate 3.5 负责,不在此重复。

---

## Gate 3.5 资产门(short-drama-asset-forge 后)

输入:`docs/ASSET_MANIFEST.json` + `assets/char|scene|prop|voice|style/**` + `docs/ASSET_BASELINE.md` + `docs/STORYBOARD.md`(引用对照)

**判定哲学与其它 Gate 不同**:资产缺陷会被全剧镜头放大,**默认硬阻断**;唯一豁免是用户在 `docs/ASSET_BASELINE.md` 签字。

| # | 检查项 | 通过条件 | 失败码 | 层 | 打勾 |
|---|---|---|---|---|---|
| 3.5.1 | 清册可解析且五类齐全 | 合法 JSON、version=1.0、五类字段均存在 | G35-MANIFEST-INVALID | L1 | [ ] |
| 3.5.2 | 被引用资产全部已锁定 | 凡被 STORYBOARD 引用的资产 status ∈ {locked, skipped} | G35-NOT-LOCKED | L1 | [ ] |
| 3.5.3 | 锁定字段无空值 | assetVersion/hash/lockedAt 非空,lockedBy = user-confirm | G35-LOCK-FIELD-MISSING | L1 | [ ] |
| 3.5.4 | 角色定妆图存在 | 每变体 refImage 文件存在且路径合规 `assets/char/{id}/{variant}.png` | G35-ASSET-FILE-MISSING | L3 | [ ] |
| 3.5.5 | 场景/道具图存在 | 非 oneOff 场景 + 全部道具的 refImage 存在 | G35-ASSET-FILE-MISSING | L3 | [ ] |
| 3.5.6 | hash 与实体文件一致 | 重算 sha256 前 12 位 = 清册 hash(逐条) | G35-HASH-MISMATCH | L3 | [ ] |
| 3.5.7 | 基线表与清册对账 | ASSET_BASELINE.md 锁定行数 = locked 资产数;hash 逐条相等 | G35-BASELINE-MISMATCH | L2 | [ ] |
| 3.5.8 | 变体完整性 | 每角色恰有 1 个 default;非 default derivedFrom=default;seed 互异;episodes 非空且 ⊆ STORYBOARD 引用 | G35-VARIANT-INCOMPLETE | L2 | [ ] |
| 3.5.9 | 风格基线锁唯一完整 | 全剧唯一;keywords/negativeKeywords 非空;lightMoodMap 覆盖全部分镜情绪;baseline.json 存在 | G35-STYLE-BASELINE-MISSING | L1+L2 | [ ] |
| 3.5.10 | 定妆图技术达标 | 短边 ≥1024px、png(自动);单人/半身/无文字水印(目检或采样) | G35-REF-QUALITY-WEAK | L3 | [ ] |
| 3.5.11 | 音色资产齐备 | 每角色有 voice[] 条目,charId 可解析,timbre/ttsVoiceName/emotionTags 非空;skipped=true 则跳过 | G35-VOICE-MISSING | L1+L3 | [ ] |
| 3.5.12 | 无未标记的降级 | 所有 degraded 资产已在 ASSET_BASELINE.md「已知风险签字」栏列明并签字 | G35-DEGRADE-UNMARKED | L2 | [ ] |
| 3.5.13 | 影响面报告齐备(仅变更时) | 有资产变更时 ASSET_IMPACT.md 存在且含受影响镜头清单 + 用户决策 | G35-IMPACT-MISSING | L1 | [ ] |

**豁免**：已签字的 degraded 资产,该条降为 [!] WARNING;签字不改变 `status=degraded`,不得改写为 locked。
**无法校验**：宿主无图像分析能力时,3.5.10 目检部分标 [~] → 结论 FAIL(数据不足),附人工检查清单,不猜测通过。
**回退分流**：实体层问题(图/hash/锁定)→ short-drama-asset-forge;声明层问题(schema/引用闭合/漏声明)→ short-drama-storyboard。

---

## Gate 4 生产门(short-drama-video-forge + short-drama-audio-forge 后)

输入:`production/manifest.json` + `shots/{ep}/shot_{XX}.mp4`(或 png)+ `audio/{ep}/line_{XX}.mp3` + `audio/bgm_*.mp3` + `subtitles/{ep}.srt` + `docs/STORYBOARD.md`(镜头数)+ `docs/scripts/EP*.md`(对白行)+ `docs/ASSET_MANIFEST.json` + `docs/ASSET_BASELINE.md`(资产 hash 对照)+ `docs/ASSET_ISSUES.md`(降级记录)

| # | 检查项 | 通过条件 | 失败码 | 层 | 打勾 |
|---|---|---|---|---|---|
| 4.1 | manifest 每镜头字段完整 | 每镜头含 集号/镜头号/时长/源分镜引用/文件路径/配音引用 | G4-MANIFEST-FIELD-MISSING | L1 | [ ] |
| 4.2 | 镜头文件存在 | 每镜头有 shots/{ep}/shot_{XX}.mp4,或降级 png(总纲 §6.2) | G4-SHOT-FILE-MISSING | L3 | [ ] |
| 4.3 | 每集镜头数与 STORYBOARD 一致 | manifest 每集镜头数 = 分镜该集镜头数 | G4-SHOT-COUNT-MISMATCH | L2 | [ ] |
| 4.4 | 配音与对白一一对应 | audio/{ep}/line_{XX}.mp3 与剧本该集对白行一一对应 | G4-AUDIO-MISMATCH | L2 | [ ] |
| 4.5 | 字幕覆盖每集 | subtitles/{ep}.srt 每集存在且首尾时间轴覆盖全集 | G4-SRT-MISSING | L3 | [ ] |
| 4.6 | 降级项已标记 | 所有降级(视频→静态图/TTS→静音/音乐→曲库占位)已记入 docs/ASSET_ISSUES.md | G4-DEGRADE-UNMARKED | L2 | [ ] |
| 4.7 | 资产引用块存在 | manifest 含 assets 引用块,source 指向 docs/ASSET_MANIFEST.json | G4-ASSET-REF-MISSING | L1 | [ ] |
| 4.8 | 资产引用 hash 一致 | manifest.assets 每条 hash = 清册对应资产 hash | G4-ASSET-HASH-MISMATCH | L2 | [ ] |
| 4.9 | 无资产定义副本 | manifest 内无 refImage/seed/styleKeywords 副本字段 | G4-ASSET-DUPLICATED | L1 | [ ] |
| 4.10 | 镜头资产引用可解析 | 每镜头 characters[](+charVariants)与可选 props[] 均可在清册解析 | G4-ASSET-REF-UNRESOLVED | L2 | [ ] |
| 4.11 | 音色引用一致 | 每集配音的 voiceId 与清册 voice[].id 一致(音频未裁剪时) | G4-VOICE-INCONSISTENT | L2 | [ ] |

辅助软检查(不阻断):已标记的降级项(如 png 静态图、静音占位)汇总为 [!] WARNING 清单,供人工后补。
