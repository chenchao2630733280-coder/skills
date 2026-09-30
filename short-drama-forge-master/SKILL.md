---
name: "short-drama-forge-master"
description: "AI 短剧制作流水线总纲（调度中枢）。接收用户一句话短剧需求，判定短剧类型与制作路径（全 AI 生成 / 图文短剧 / 真人实拍辅助 / 口播短剧），选择工具链、裁剪阶段、串联下游 9 个阶段 skill（含资产定妆阶段 4.5）与跨阶段质量门（Gate 0~4 + Gate 3.5 资产门），提供失败回退策略与人工确认点。资产层（角色/变体/场景/道具/音色/风格基线）在批量生产前定妆并锁定，是全剧一致性基线。当用户要'用 AI 制作/生成一部短剧'、'端到端产出短剧成片'、'按流水线制作短剧'、'从选题到成片'时调用。"
---

# Short Drama Forge Master — AI 短剧制作总纲

本 skill 是整套"AI 制作短剧"流水线的**调度中枢**,本身不直接产出剧本/视频/成片,职责是:
1. 接收用户一句话需求,决定走哪条制作路径
2. 判定短剧类型(全 AI 生成 / 图文短剧 / 真人实拍辅助 / 口播短剧)
3. 选择生成工具链(图生视频 / 文生图 / TTS / 音乐 / 剪辑)
4. 裁剪阶段(口播短剧可跳过视频生成/分镜)
5. 串联下游 9 个阶段 skill(含**阶段 4.5 资产定妆**)+ 跨阶段质量门(含 **Gate 3.5 资产门**)的执行顺序
6. 提供固定产物路径表与失败回退策略
7. **守住资产基线**:阶段 5 开工前必须完成资产定妆与锁定,否则全剧角色/场景/道具/音色会各自漂移

---

## 一、何时调用

满足以下任一条件即调用本 skill:
- 用户说"用 AI 制作/生成一部短剧"
- 用户说"按流水线制作短剧"、"从选题到成片"
- 用户给了短剧雏形需求,需要端到端产出可发布的成片(或可执行生产工程)
- 用户调用了任意 `short-drama-*` 系列 skill 但未先经过总纲

**阶段 0 路由**:若用户需求模糊(如"想做部短剧"但未明确题材/类型),或明确要"脑暴选题/找点子",先调用 `short-drama-topic-brainstorm` 产出 `docs/TOPIC_PROPOSAL.md`,用户确认推荐方案后再进入阶段 1。

**不要**在以下场景调用:
- 用户只是问"短剧怎么做"(纯咨询,用对话回答即可)
- 用户要修改已有短剧的某一处剧本/某一段视频(直接用 Edit/Write 或对应阶段 skill)
- 用户要做的是长剧/电影(本流水线面向 1-3 分钟单集、60-100 集的竖屏短剧)

---

## 二、流水线总览

```
用户一句话需求
       ↓
(需求模糊?) ──是──→ short-drama-topic-brainstorm → docs/TOPIC_PROPOSAL.md
       │ 否                                    ↓
       ↓ ←─────────────────────────────────────┘
[本 skill] 类型判定 + 工具链选择 + 阶段裁剪
       ↓
short-drama-blueprint     → docs/SHORT_DRAMA_BLUEPRINT.md
       ↓
[Gate 0] 立项门 → docs/GATE_0_REPORT.md (FAIL 则回 1 修复)
       ↓
⏸ 人工确认点 1 (AskUserQuestion: 进入规格 / 回退 / 终止)
       ↓
short-drama-spec          → docs/STORY_SPEC.md + docs/EPISODE_OUTLINE.md
       ↓
[Gate 1] 规格门 → docs/GATE_1_REPORT.md (FAIL 则回 2 修复)
       ↓
⏸ 人工确认点 2 (AskUserQuestion: 进入剧本 / 回退 / 终止)
       ↓
short-drama-script        → docs/scripts/EP{01..NN}.md
       ↓
[Gate 2] 剧本门 → docs/GATE_2_REPORT.md (FAIL 则回 3 修复)
       ↓
⏸ 人工确认点 3 (AskUserQuestion: 进入分镜 / 回退 / 终止)
       ↓
short-drama-storyboard    → docs/STORYBOARD.md + docs/VISUAL_SPEC.md + docs/ASSET_MANIFEST.json
       ↓
[Gate 3] 分镜门 → docs/GATE_3_REPORT.md (FAIL 则回 4 修复)
       ↓
⏸ 人工确认点 4 (AskUserQuestion: 进入资产定妆 / 回退 / 终止)
       ↓
short-drama-asset-forge   → ① 生成候选定妆资产
       ↓
⏸ 人工确认点 4.5 (★ 定妆确认,AskUserQuestion: 确认候选并锁定 / 重出候选 / 改设定后重出)
       ↓
short-drama-asset-forge   → ② 锁定并落盘 → assets/{char,scene,prop,voice,style}/ + docs/ASSET_BASELINE.md(+回写 ASSET_MANIFEST.json)
       ↓
[Gate 3.5] 资产门 → docs/GATE_3.5_REPORT.md (FAIL 则回 4.5/4 修复)
       ↓
⏸ 人工确认点 4.6 (AskUserQuestion: 进入批量生产 / 回退 / 终止)
       ↓
short-drama-video-forge   → production/manifest.json + shots/{ep}/shot_{XX}.mp4
       ↓
short-drama-audio-forge   → audio/{ep}/line_{XX}.mp3 + subtitles/{ep}.srt (可与 video-forge 并行)
       ↓
[Gate 4] 生产门 → docs/GATE_4_REPORT.md (FAIL 则回 5/6 修复)
       ↓
⏸ 人工确认点 5 (AskUserQuestion: 进入剪辑 / 回退 / 终止)
       ↓
short-drama-edit          → episodes/EP{XX}.mp4 + docs/BUILD_REPORT.md (内含 Gate 5 成片实跑门)
       ↓
⏸ 人工确认点 6 (AskUserQuestion: 进入打磨(可选) / 完成 / 回退)
       ↓
⏸ 人工确认点 7 (可选 Tool,AskUserQuestion: 提交 Git / 发布 / 跳过)
```

**阶段性质**:
- 阶段 0(short-drama-topic-brainstorm):**可选**,用户需求模糊或要脑暴选题时调用
- 阶段 1-7(蓝图→规格→剧本→分镜→**资产定妆**→视频→音频→剪辑):**按裁剪规则走**,产出可发布成片
- **阶段 4.5(short-drama-asset-forge):不可裁剪**(任何制作类型都需要资产基线;音频裁剪只豁免音色资产)
- **质量门 Gate 0~4 + Gate 3.5:必走**,由 short-drama-quality-gate 介入,FAIL 时硬阻断回原阶段修复
- **质量门 Gate 5:成片实跑门**,内置于 short-drama-edit,校验时长/字幕/音画/集数
- **人工确认点 1~6 + 4.5 + 4.6:强制暂停**,每阶段 Gate PASS 后用 AskUserQuestion 确认,不允许自动进入下一阶段(见 §九.1)
- **资产基线是硬前置**:阶段 5 只允许消费 `status=locked` 的资产;未经 Gate 3.5 PASS 不得进入批量生产

**为什么要有资产层**:短剧一集 10-25 镜头、全剧 60-100 集。角色形象若在批量生产时才"第一次被确定",一旦不像就要全量返工 —— 且观众对角色统一的敏感度远高于单个镜头的画质。资产层把"一致性"从**事后检测**变成**事前锁定**。

**关键约束**:每阶段产物的路径与文件名固定,下游 skill 必须按固定路径读取上游产物,不允许自定义路径。
**workflow-runtime 驱动(可选)**:本流水线可由 `workflow-runtime` skill 编译为 `workflow.yaml` 自动驱动执行,详见 §七 末尾。

---

## 三、短剧类型与工具链决策树

### 3.1 类型判定(决定裁剪与工具链)

```
用户需求
   ├─ 有真人演员/实拍素材 → 真人实拍辅助型(剧本/分镜/剪辑 AI 辅助,拍摄人工)
   ├─ 有真实人物肖像素材(如短剧换脸/数字分身) → AI 数字人型(口播+半身镜头为主)
   ├─ 需要完整剧情画面但无实拍 → 全 AI 生成型(文生图+图生视频)
   ├─ 低成本/快速验证 → 图文短剧型(图+卡点+字幕+BGM)
   └─ 用户明确指定类型 → 尊重用户选择
```

### 3.2 工具链决策树(类比 game 套件的引擎决策树)

按**预算/质量要求/风格/宿主能力**选择,结果写入蓝图的"8. 工具链选型"章节:

| 环节 | 默认推荐 | 备选 | 决策依据 |
|---|---|---|---|
| 文生图(角色/场景/道具) | 即梦/可画 | Midjourney、SD(ComfyUI)、Flux | 角色一致性要求高→即梦/SD 控图;出图快→即梦 |
| **资产定妆图(阶段 4.5)** | **同文生图工具,但需支持参考图+seed 双控** | 即梦(参考图+seed)、SD/Flux(IPAdapter/LoRA) | **定妆是全剧一致性基点,必须可复现**;不支持控图的工具不得产出定妆图 |
| 图生视频 | 可灵(Kling) | 即梦、Runway、Pika、海螺(MiniMax)、Sora | 画质优先→Sora/Runway;中文生态+低成本→可灵/即梦;时长 5-10s/镜头 |
| 数字人/口播 | 即梦数字人、HeyGen | D-ID、剪映数字人 | 有口播台本且需要真人形象时 |
| TTS 配音 | 火山引擎、Edge TTS | 阿里 CosyVoice、微软 Azure、MiniMax 语音 | 情感戏多→火山/CosyVoice 情感音色;低成本→Edge TTS |
| 音乐/BGM | Suno | Udio、网易天音、平台曲库 | 需要原创 OST→Suno;版权曲库→平台曲库 |
| 音效 | 平台素材库 | AI 音效生成 | 可选 |
| 字幕 | 剪映/AutoSub 类 | 自研 ffmpeg 烧录 | 见 short-drama-edit |
| 剪辑合成 | FFmpeg(脚本化) | 剪映(人工)、Premiere(人工) | 流水线自动合成→FFmpeg 脚本;人工精剪→剪映 |

### 3.3 决策结果写入

蓝图"8. 工具链选型"章节格式:
```
制作类型:全 AI 生成
文生图:即梦
图生视频:可灵(Kling)
TTS:火山引擎
音乐:Suno
剪辑:FFmpeg 脚本化
理由:[一句话]
```

---

## 四、阶段裁剪规则

不是所有短剧都要走完整 8 阶段。按类型与复杂度裁剪:

| 类型 | 特征 | 裁剪 |
|---|---|---|
| ★ 口播短剧 | 单人讲述+素材画面 | 跳过 storyboard/video-forge,只用 script→asset-forge(仅音色)→audio→edit(图文卡点合成) |
| ★★ 图文短剧 | 图+字幕+卡点+BGM | 跳过 video-forge(视频生成),storyboard 只出图 prompt;asset-forge 照走(图卡一致性更依赖定妆) |
| ★★★ 全 AI 生成 | 完整剧情画面 | 全流程 |
| ★★★★ 数字人型 | 数字人+剧情画面混合 | 全流程,audio-forge 数字人 TTS 优先;asset-forge 增加数字人形象定妆 |
| ★★★★★ 真人实拍辅助 | 实拍+AI 后期 | script/storyboard/asset-forge(含实拍人物参考图登记)/edit 必走,其余裁剪 |

**不可裁剪的两个阶段**:
- **阶段 4.5(short-drama-asset-forge)不裁剪**:任何制作类型都需要资产基线(哪怕是真人实拍,也要把实拍人物参考图登记为资产以保证后期一致)。音频裁剪只豁免音色资产(标 `voice.skipped=true`)。
- **阶段 7(short-drama-edit)不裁剪**:任何类型最终都要合成成片(口播/图文也要出成片)。

裁剪结果写入 `docs/SHORT_DRAMA_BLUEPRINT.md` 的"10. 阶段裁剪建议",逐阶段标注:
```
4. short-drama-storyboard: 执行/跳过 (理由: ...)
4.5 short-drama-asset-forge: 执行 (不可裁剪;音色资产: 执行/跳过)
5. short-drama-video-forge: 执行/跳过 (理由: ...)
```

---

## 五、通用模板索引

各下游 skill 自带 `references/` 与 `templates/` 目录,维护本阶段所需的模板与规范文件。references 清单:

| skill | references/templates 内容 |
|-------|--------------------------|
| short-drama-topic-brainstorm | 观看动力变量库、趋势雷达信号分层、选题多样性引擎 |
| short-drama-blueprint | 立项模板、短剧类型判定细则、工具链选型表 |
| short-drama-spec | 故事发动机模板、人物卡模板、秘密系统模板、情绪曲线规则 |
| short-drama-script | 竖屏剧本格式规范、单集钩子/卡点规则、对白规则、单集剧本模板 |
| short-drama-storyboard | 镜头语言(景别/运镜/时长)、视觉 prompt 引擎(文生图/图生视频) |
| **short-drama-asset-forge** | **资产清册 schema(唯一真源)、定妆技术规范与变体派生配方、失败/影响面/豁免签字配方;templates 含 ASSET_MANIFEST 示例与 ASSET_BASELINE 模板** |
| short-drama-video-forge | 工具调用配方、角色一致性控制(消费锁定资产)、失败降级配方(图文短剧) |
| short-drama-audio-forge | TTS 情感脚本规则、音乐情绪匹配、字幕断句规范 |
| short-drama-edit | ffmpeg 合成模板、成片验收清单 |
| short-drama-quality-gate | Gate 0~4 检查项、报告模板 |
| **本 skill(templates/project/)** | **短剧项目模板骨架**:复制即得固定路径项目结构(蓝图/规格/大纲/分镜/视觉/音频/门报告/验收/剧本示例/manifest 示例),见 §十 模板模式 |

**跨 skill 引用**:阶段 2 之后所有 skill 需读取上游固定路径产物(见 §八),质量门读取对应报告与产物。

---

## 六、失败回退策略

下游 skill 执行失败时的统一处理,分**硬阻断**与**软降级**两类:

### 6.1 硬阻断(质量门 FAIL)

由 `short-drama-quality-gate` 在 Gate 0~4 检出,不允许进入下一阶段,回原产出 skill 修复后重跑 Gate:

| 失败场景 | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0/1/2 FAIL(静态/契约) | **硬阻断**,不允许进入下一阶段 | 对应阶段 skill 修复后重跑 Gate |
| Gate 3 FAIL(分镜缺镜头/prompt 不可执行/资产清册非法) | **硬阻断** | short-drama-storyboard 修复后重跑 |
| **Gate 3.5 FAIL(资产未锁定/定妆图缺失/hash 不符/变体缺失/降级未签字)** | **硬阻断** | 实体层问题回 short-drama-asset-forge;声明层问题回 short-drama-storyboard |
| Gate 4 FAIL(manifest 缺镜头/音频缺失/资产引用 hash 不符) | **硬阻断** | short-drama-video-forge / short-drama-audio-forge 修复后重跑 |

### 6.2 软降级(允许继续,标记到报告)

失败项汇总到 `docs/BUILD_REPORT.md` 与 `docs/ASSET_ISSUES.md`,不阻塞流水线:

| 失败场景 | 回退策略 |
|---|---|
| 图生视频失败 | 降级为单帧静态图+镜头运动(缩放/平移模拟运镜)+标记 |
| 文生图失败 | 纯色+文字占位图(标注"待人工出图")+标记 |
| 视频生成接口全部不可用 | 整剧降级为图文短剧模式(图+卡点+字幕+BGM) |
| TTS 失败 | 静音占位+字幕保留+标记;或切换备选 TTS |
| 音乐生成失败 | 平台免费曲库 BGM 占位+标记 |
| 字幕烧录失败 | 输出独立 .srt,标注"未烧录,发布前需人工烧录" |
| 镜头时长与剧本不符 | 剪辑时按 manifest 重排,超长镜头用转场压缩 |
| **镜头级**角色一致性漂移(单个镜头与锁定定妆图不符) | 用**锁定参考图 + 该资产 hash** 重生成 ≤2 次;仍漂移标 `character-drift` 并记入 ASSET_ISSUES |
| 定妆图/资产质量不合格 | **不适用软降级**(见 §6.3),由 Gate 3.5 硬阻断 |
| 音色试音失败 | 保留 voiceId/音色描述,样本留空并标 degraded;阶段 6 仍可按 ttsVoiceName 直出 |
| 资产变更(换定妆图/改风格) | 走 short-drama-asset-forge §五流程:影响面报告 + 用户决策 + assetVersion 递增 |

**原则**:内容质量类问题(剧本/分镜/契约)**硬阻断**;镜头级资源类问题(单张图/单个视频/单条音频)**软降级**。

### 6.3 资产类失败为什么不软降级

**一个坏资产会被全剧 800+ 镜头放大。** 镜头级降级(第 37 集第 5 个镜头用了静态图)是局部瑕疵,观众几乎无感;资产级降级(全剧主角的定妆图是占位图)会让整部剧垮掉。因此:

- 资产类失败由 **Gate 3.5 资产门硬阻断**,回归 short-drama-asset-forge 修复
- **唯一豁免**:用户在 `docs/ASSET_BASELINE.md`「已知风险签字」栏明确接受(写明资产清单/后果/签字人/时间),该条 ERROR 降为 WARNING,其余检查项不受影响
- **禁止静默通过、禁止改写 `status=degraded` 为 `locked`**
- 所有降级项最终必须出现在 `docs/BUILD_REPORT.md` 的遗留问题清单

**软降级与硬阻断的分界(一图记住)**:
```
镜头内的资源 → 软降级(坏了就坏了,标记即可)
跨镜头的资产 → 硬阻断(坏了会污染全剧,必须修)
```

---

## 七、执行顺序(必须严格遵循,每阶段人工确认)

调用本 skill 后,必须按以下顺序执行下游 skill 与质量门。**每个阶段完成后必须暂停,用 AskUserQuestion 向用户确认后再进入下一阶段**(见 §九.1):

0. **(可选)** 若需求模糊或用户要脑暴选题,调用 `short-drama-topic-brainstorm`,产出 `docs/TOPIC_PROPOSAL.md`,用户确认推荐方案后进入下一步
1. 调用 `short-drama-blueprint`,产出 `docs/SHORT_DRAMA_BLUEPRINT.md`
   - **调用 `short-drama-quality-gate` Gate 0 立项门**,产出 `docs/GATE_0_REPORT.md`;FAIL 则回 1 修复
   - ⏸ **人工确认点 1**:简报蓝图摘要(类型/集数/工具链/复杂度),AskUserQuestion 询问"进入规格设计 / 回退修改蓝图 / 终止流水线"
2. 调用 `short-drama-spec`,读取蓝图,产出 `docs/STORY_SPEC.md` + `docs/EPISODE_OUTLINE.md`
   - **调用 `short-drama-quality-gate` Gate 1 规格门**,产出 `docs/GATE_1_REPORT.md`;FAIL 则回 2 修复
   - ⏸ **人工确认点 2**:简报故事发动机关键要素+分集数,AskUserQuestion 询问"进入剧本创作 / 回退修改规格 / 终止流水线"
3. 调用 `short-drama-script`,读取规格+大纲,产出 `docs/scripts/EP{01..NN}.md`(每集一文件)
   - **调用 `short-drama-quality-gate` Gate 2 剧本门**,产出 `docs/GATE_2_REPORT.md`;FAIL 则回 3 修复
   - ⏸ **人工确认点 3**:简报剧本集数/单集字数/卡点覆盖,AskUserQuestion 询问"进入分镜设计 / 回退修改剧本 / 终止流水线"
4. 调用 `short-drama-storyboard`,读取剧本,产出 `docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md` + `docs/ASSET_MANIFEST.json`(资产需求清册,`status=declared`)
   - **调用 `short-drama-quality-gate` Gate 3 分镜门**,产出 `docs/GATE_3_REPORT.md`;FAIL 则回 4 修复
   - ⏸ **人工确认点 4**:简报镜头总数/角色数(含变体数)/场景数/道具数,AskUserQuestion 询问"进入资产定妆 / 回退修改分镜 / 终止流水线"
4.5 调用 `short-drama-asset-forge`,读取清册 + VISUAL_SPEC + STORYBOARD,先**批量生成候选资产**,再:
   - ⏸ **人工确认点 4.5(★ 定妆确认)**:逐批(每批 ≤4 角色)简报候选图路径与推荐项,AskUserQuestion 询问"确认定妆并锁定 / 重出候选(说明不满意点) / 改文字设定后重出"。**未确认不得 lock**
   - 确认后锁定并落盘:`assets/{char,scene,prop,voice,style}/` + `docs/ASSET_BASELINE.md` + 回写 `docs/ASSET_MANIFEST.json`(`status=locked` + hash + assetVersion)
   - **调用 `short-drama-quality-gate` Gate 3.5 资产门**,产出 `docs/GATE_3.5_REPORT.md`;FAIL 则按分流回 4.5(实体层)或 4(声明层)修复
   - ⏸ **人工确认点 4.6**:简报锁定资产数(角色/变体/场景/道具/音色)+ 降级项,AskUserQuestion 询问"进入批量生产 / 回退修改资产 / 终止流水线"
5. **并行**调用 `short-drama-video-forge` 与 `short-drama-audio-forge`:前者产出 `production/manifest.json` + `shots/`,后者产出 `audio/` + `subtitles/`
   - **硬前置**:阶段 5 只允许消费 `status=locked` 的资产;`production/manifest.json` 必须含 `assets` 引用块(指向 `docs/ASSET_MANIFEST.json` + 逐条 hash),**不得复制资产定义**
   - **调用 `short-drama-quality-gate` Gate 4 生产门**,产出 `docs/GATE_4_REPORT.md`;FAIL 则回 5/6 修复
   - ⏸ **人工确认点 5**:简报镜头数/视频时长/音频文件数/资产 hash 一致性,AskUserQuestion 询问"进入剪辑合成 / 回退修复产物 / 终止流水线"
6. 调用 `short-drama-edit`,读取 manifest + shots + audio + subtitles,产出 `episodes/EP{XX}.mp4` + `docs/BUILD_REPORT.md`(内含 Gate 5 成片实跑门;遗留问题清单须含未替换的降级资产)
   - ⏸ **人工确认点 6**:简报成片路径+每集时长+验收结果,AskUserQuestion 询问"流水线完成 / 回退修复 / 进入打磨(可选)"
   - ⏸ **人工确认点 7(可选 Tool)**:若用户明确要"提交/发布",AskUserQuestion 询问"提交产物到 Git / 发布到平台 / 跳过"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit episodes/ + docs/ + production/,默认不 push)
     - 选"发布到平台" → 按目标平台指引(短视频平台人工上传 / Web 平台走 `web-static-deploy`)
     - 选"跳过" → 结束
   - Tool 操作前过 `guardrail` 前置检查

**不允许跳步**:即使某阶段被裁剪,也必须产出对应的占位文档(如视频生成裁剪也要在 manifest 中标注"该镜头用静态图";音频裁剪也要在清册标 `voice.skipped=true`)。**质量门不可跳过**(裁剪阶段跑 Gate 时,占位产物通过即可;Gate 3.5 在任何类型下都不可跳过)。
**阶段 0 例外**:short-drama-topic-brainstorm 被跳过时**不产出占位文档**(可选增量)。
**阶段 4.5 例外**:short-drama-asset-forge **不可裁剪**;音频裁剪只豁免音色资产,且必须在清册显式标注 `skipped: true`。
**人工确认不可跳过**:确认点 1~6 + **4.5(定妆确认)** + **4.6(进入生产)** 是强制暂停点,即使用户此前已表达"全流程执行",也必须在每个确认点等待用户明确选择后才继续。**定妆确认点 4.5 尤其不可跳过** —— 它是"内容锁定"而非"阶段推进",跳过等于把全剧一致性赌在一次未经审视的出图上。

**可选:产出 workflow.yaml 交 workflow-runtime 驱动执行**

本总纲的执行顺序(§七)可由 `workflow-runtime` skill 编译为可执行 `workflow.yaml`。产出 `workflow.yaml`(可选产物,见 §八)。workflow-runtime 模式下,pause 节点自动触发 AskUserQuestion,与本文确认点 1~7(含 4.5/4.6)一一对应。

---

## 八、产物路径总表

所有 skill 必须遵守的固定路径(项目根目录假设为 `{project}/`,即用户指定的短剧项目工作目录):

| 产物 | 路径 | 由哪个 skill 产出 |
|---|---|---|
| 选题方案(可选) | `docs/TOPIC_PROPOSAL.md` | short-drama-topic-brainstorm |
| 立项蓝图 | `docs/SHORT_DRAMA_BLUEPRINT.md` | short-drama-blueprint |
| 故事规格 | `docs/STORY_SPEC.md` | short-drama-spec |
| 分集大纲 | `docs/EPISODE_OUTLINE.md` | short-drama-spec |
| 正式剧本 | `docs/scripts/EP{01..NN}.md` | short-drama-script |
| 分镜脚本 | `docs/STORYBOARD.md` | short-drama-storyboard |
| 视觉规范 | `docs/VISUAL_SPEC.md` | short-drama-storyboard |
| **资产需求清册** | **`docs/ASSET_MANIFEST.json`** | **short-drama-storyboard(声明 status=declared)/ short-drama-asset-forge(回写 locked + hash)** |
| **角色定妆图** | **`assets/char/{charId}/{variantId}.png`** | **short-drama-asset-forge** |
| **场景定稿图** | **`assets/scene/{sceneId}.png`** | **short-drama-asset-forge** |
| **道具定稿图** | **`assets/prop/{propId}.png`** | **short-drama-asset-forge** |
| **音色试音** | **`assets/voice/{charId}.mp3`** | **short-drama-asset-forge** |
| **风格基线卡** | **`assets/style/baseline.json`** | **short-drama-asset-forge** |
| **资产基线锁定表** | **`docs/ASSET_BASELINE.md`** | **short-drama-asset-forge(锁定表/变更记录/已知风险签字)** |
| **资产变更影响面报告** | **`docs/ASSET_IMPACT.md`** | **short-drama-asset-forge(仅变更时)** |
| 生产清单 | `production/manifest.json` | short-drama-video-forge(**只引用**资产,不得复制定义) |
| 镜头视频 | `shots/{ep}/shot_{XX}.mp4` | short-drama-video-forge |
| 镜头占位图 | `shots/{ep}/shot_{XX}.png` | short-drama-video-forge(降级时) |
| 配音 | `audio/{ep}/line_{XX}.mp3` | short-drama-audio-forge |
| 音乐/BGM | `audio/bgm_{name}.mp3` | short-drama-audio-forge |
| 音频规格 | `docs/AUDIO_SPEC.md` | short-drama-audio-forge(音色映射**引用 voice 资产 id**/情感标签/语速/BGM 匹配标注;short-drama-edit 可选读取) |
| 字幕 | `subtitles/{ep}.srt` | short-drama-audio-forge |
| 成片 | `episodes/EP{XX}.mp4` | short-drama-edit |
| 验收报告 | `docs/BUILD_REPORT.md` | short-drama-edit(须含遗留降级资产清单) |
| 质量门报告 0~4 + 3.5 | `docs/GATE_{0..4}_REPORT.md` + `docs/GATE_3.5_REPORT.md` | short-drama-quality-gate |
| 已知问题 | `docs/ASSET_ISSUES.md` | 任意(失败时写;含资产降级) |
| workflow.yaml(可选) | `workflow.yaml` | workflow-runtime(编译本总纲 §七 生成) |

**集数约定**:`EP{01..NN}` 为两位数编号;单集 1-3 分钟;单镜头 3-10 秒;一集约 10-25 个镜头。

**资产单一真源规则(强制)**:资产定义**只准**写在 `docs/ASSET_MANIFEST.json`。`production/manifest.json` 通过 `assets` 引用块指向它(id + variant + assetVersion + hash),不得出现 `refImage`/`seed`/`styleKeywords` 副本 —— 两份真源必然漂移,这是本流水线明确禁止的缺陷(Gate 4.9 会阻断)。

---

## 九、用户交互约定

- 默认全程中文输出
- 每阶段完成后向用户简报产物路径与下一步
- 遇到选择(类型/工具链/裁剪)用 AskUserQuestion 确认,不擅自决定
- 全流程不依赖可视化编辑器,所有文档纯文本,视频/音频由工具链脚本化生成

### 9.1 人工确认机制(强制,见 §七 确认点 1~6 + 4.5 + 4.6)

每个阶段完成且对应质量门 PASS 后,**必须暂停流水线**,用 AskUserQuestion 确认下一步。**不允许自动连续执行下一阶段**。

**确认点标准动作**:
1. **简报**:2-3 句话汇报本阶段产物路径 + 关键指标(镜头数/集数/时长/文件数)
2. **AskUserQuestion 询问**,选项固定 3 个(按阶段语义微调文案):
   - "进入下一阶段:{下一阶段名}"(推荐)
   - "回退修改:回到本阶段修复问题"
   - "终止流水线:停止,保留当前产物"
3. **根据用户选择**:
   - 选"进入下一阶段" → 调用下游 skill
   - 选"回退修改" → 重新执行本阶段 skill(用户可补充修改要求),重跑质量门,再次确认
   - 选"终止流水线" → 输出最终简报(已完成阶段 + 产物清单),结束

### 9.2 特例确认点 4.5(★ 定妆确认)与 4.6

**确认点 4.5 与其它确认点语义不同**:其它确认点是"阶段推进确认"(产物已落盘,问是否继续);4.5 是**内容锁定确认**(产物尚是候选,用户选定后才落盘锁定)。

| 项 | 其它确认点(1~4、4.6~6) | 确认点 4.5 定妆确认 |
|---|---|---|
| 时机 | 产物已产出 + Gate PASS 后 | **候选资产已生成、尚未锁定** |
| 选项 | 进入下一阶段 / 回退 / 终止 | 确认定妆并锁定 / 重出候选(说明不满意点) / 改文字设定后重出 |
| 可否跳过 | 不可跳过 | **绝对不可跳过**(跳过 = 把全剧一致性赌在未经审视的出图上) |
| 分批 | 通常不需分批 | 角色 >4 个时分批(每批 ≤4 个角色) |
| 循环上限 | — | 重出候选 ≤3 轮;仍不满意则回阶段 4 改文字设定 |

**确认点 4.6**:Gate 3.5 资产门 PASS 后的常规推进确认(进入批量生产 / 回退修改资产 / 终止)。

**例外**:
- 阶段 0(脑暴)本身可选,用户确认推荐方案即进入阶段 1,不另设确认点
- 质量门 FAIL 时无需确认,直接回退修复(修复后重跑 Gate,Gate PASS 再走确认点)
- 确认点 7(可选 Tool)默认不强制出现,仅在用户明确要"提交/发布"时触发
- 资产未发生变更时,**重跑流水线不重复触发** 4.5(已 lock 且 hash 未变的资产跳过)

**workflow-runtime 兼容**:workflow-runtime 模式下,确认点 1~7(含 4.5/4.6)对应 workflow.yaml 中的 pause 节点,选项与本文一致。

---

## 十、短剧模板模式(快速起步)

当用户说"创建短剧模板/短剧模式/从模板开始做短剧/套用模板"时,本总纲先进入**模板模式**:用 `templates/project/` 项目模板骨架初始化项目,再按正常流水线推进。模板骨架不是独立 skill,是总纲自带的可复制项目结构。

### 10.1 模板路径

```
short-drama-forge-master/templates/project/
├── README.md                          # 模板说明 + 使用步骤
├── docs/
│   ├── SHORT_DRAMA_BLUEPRINT.template.md   # 阶段1 蓝图模板(11 章)
│   ├── STORY_SPEC.template.md              # 阶段2 故事规格模板
│   ├── EPISODE_OUTLINE.template.md         # 阶段2 分集大纲模板
│   ├── STORYBOARD.template.md              # 阶段4 分镜模板(12 字段镜头表)
│   ├── VISUAL_SPEC.template.md             # 阶段4 视觉规范模板(角色母卡+变体子表/场景/道具/风格/字幕)
│   ├── ASSET_MANIFEST.template.json        # 阶段4 资产需求清册模板(阶段4.5 回写锁定)
│   ├── ASSET_BASELINE.template.md          # 阶段4.5 资产基线锁定表模板
│   ├── AUDIO_SPEC.template.md              # 阶段6 音频规格模板
│   ├── GATE_0_REPORT.template.md           # 质量门报告模板(0~4 + 3.5 通用)
│   ├── BUILD_REPORT.template.md            # 阶段7 成片验收报告模板
│   └── scripts/EP01.example.md             # 单集剧本示例(阶段3 参考)
├── assets/                            # 阶段4.5 资产基线(空,gitkeep)
│   ├── char/{charId}/{variantId}.png  # 角色定妆图(含变体)
│   ├── scene/{sceneId}.png            # 场景定稿图
│   ├── prop/{propId}.png              # 剧情道具定稿图
│   ├── voice/{charId}.mp3             # 音色试音
│   └── style/baseline.json            # 风格基线卡(locked token)
├── production/manifest.example.json   # 阶段5 生产清单示例(只引用资产,不复制定义)
├── shots/                             # 阶段5 镜头产物(空,gitkeep)
├── audio/                             # 阶段6 配音/BGM(空,gitkeep)
├── subtitles/                         # 阶段6 字幕(空,gitkeep)
└── episodes/                          # 阶段7 成片(空,gitkeep)
```

### 10.2 初始化步骤

1. **复制骨架**:把 `templates/project/` 整个目录复制为项目根目录(如 `{项目名}/`),保留目录结构
2. **改写 README**:项目 README 替换为剧名/一句话简介
3. **填蓝图**:按 `docs/SHORT_DRAMA_BLUEPRINT.template.md` 填写并改名 `docs/SHORT_DRAMA_BLUEPRINT.md`(去 `.template` 后缀)
4. **进入流水线**:从阶段 1 开始按 §七 顺序推进;已存在的模板文件在对应阶段被覆盖为正式产物,空目录由阶段 skill 写入

### 10.3 模板模式规则

- **命名契约**:模板文件必须去掉 `.template` 后缀后使用,恢复为 §八 固定路径文件名;`EP01.example.md` 仅作格式参考,正式剧本按 `docs/scripts/EP{01..NN}.md` 新建
- **模板不阻塞流水线**:即使用户没有从模板起步,各阶段 skill 照常按自己的模板/格式产出(模板模式只是加速起步,不是必经之路)
- **模板骨架与各阶段 skill 自带 templates/ 的关系**:`project/` 提供"项目级"成套骨架;各阶段 skill 的 `references/`/`templates/` 提供"单阶段"细则模板,二者互补,内容不重复
- **模板模式本身不设质量门**:初始化只复制+改名,不产出业务内容,Gate 0 从蓝图填写完成后介入
- **资产目录契约**:`assets/` 五个子目录由阶段 4.5 写入;模板中仅作结构占位(含 `.gitkeep`)。**不要手工往 `assets/` 丢图** —— 未经定妆确认与 hash 登记的图会在 Gate 3.5 被判为未锁定/无登记而阻断

### 10.4 一句话速查:资产层在本流水线的位置

```
阶段 4 分镜 ──声明──→ docs/ASSET_MANIFEST.json（要哪些资产）
阶段 4.5 定妆 ─实产─→ assets/**（资产长什么样）+ ASSET_BASELINE.md（锁定与留痕）
              └确认→ 人工确认点 4.5（用户选定才 lock）
Gate 3.5 资产门 ─校验→ 文件存在 + 已锁定 + hash 一致（不通过不许生产）
阶段 5 生产 ─引用─→ production/manifest.json 的 assets 块（id+variant+hash）
阶段 7 出现 ─→ BUILD_REPORT.md 遗留降级资产清单
```
