---
name: "short-drama-forge-master"
description: "AI 短剧制作流水线总纲（调度中枢）。接收用户一句话短剧需求，判定短剧类型与制作路径（全 AI 生成 / 图文短剧 / 真人实拍辅助 / 口播短剧），选择工具链、裁剪阶段、串联下游 8 个阶段 skill 与跨阶段质量门，提供失败回退策略与人工确认点。当用户要'用 AI 制作/生成一部短剧'、'端到端产出短剧成片'、'按流水线制作短剧'、'从选题到成片'时调用。"
---

# Short Drama Forge Master — AI 短剧制作总纲

本 skill 是整套"AI 制作短剧"流水线的**调度中枢**,本身不直接产出剧本/视频/成片,职责是:
1. 接收用户一句话需求,决定走哪条制作路径
2. 判定短剧类型(全 AI 生成 / 图文短剧 / 真人实拍辅助 / 口播短剧)
3. 选择生成工具链(图生视频 / 文生图 / TTS / 音乐 / 剪辑)
4. 裁剪阶段(口播短剧可跳过视频生成/分镜)
5. 串联下游 8 个阶段 skill + 跨阶段质量门的执行顺序
6. 提供固定产物路径表与失败回退策略

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
short-drama-storyboard    → docs/STORYBOARD.md + docs/VISUAL_SPEC.md
       ↓
[Gate 3] 分镜门 → docs/GATE_3_REPORT.md (FAIL 则回 4 修复)
       ↓
⏸ 人工确认点 4 (AskUserQuestion: 进入生产 / 回退 / 终止)
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
- 阶段 1-7(蓝图→规格→剧本→分镜→视频→音频→剪辑):**按裁剪规则走**,产出可发布成片
- **质量门 Gate 0~4:必走**,由 short-drama-quality-gate 介入,FAIL 时硬阻断回原阶段修复
- **质量门 Gate 5:成片实跑门**,内置于 short-drama-edit,校验时长/字幕/音画/集数
- **人工确认点 1~6:强制暂停**,每阶段 Gate PASS 后用 AskUserQuestion 确认,不允许自动进入下一阶段(见 §九.1)

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
| ★ 口播短剧 | 单人讲述+素材画面 | 跳过 storyboard/video-forge,只用 script→audio→edit(图文卡点合成) |
| ★★ 图文短剧 | 图+字幕+卡点+BGM | 跳过 video-forge(视频生成),storyboard 只出图 prompt |
| ★★★ 全 AI 生成 | 完整剧情画面 | 全流程 |
| ★★★★ 数字人型 | 数字人+剧情画面混合 | 全流程,audio-forge 数字人 TTS 优先 |
| ★★★★★ 真人实拍辅助 | 实拍+AI 后期 | script/storyboard/edit 必走,其余裁剪 |

**阶段 7(short-drama-edit)不裁剪**:任何类型最终都要合成成片(口播/图文也要出成片)。

裁剪结果写入 `docs/SHORT_DRAMA_BLUEPRINT.md` 的"9. 阶段裁剪建议",追加一行:
```
6. short-drama-video-forge: 执行/跳过 (理由: ...)
```

---

## 五、通用模板索引

各下游 skill 自带 `references/` 与 `templates/` 目录,维护本阶段所需的模板与规范文件。references 清单:

| skill | references/templates 内容 |
|-------|--------------------------|
| short-drama-topic-brainstorm | 观看动力变量库、趋势雷达信号分层、选题多样性引擎 |
| short-drama-blueprint | 立项模板、短剧类型判定细则、工具链选型表 |
| short-drama-spec | 故事发动机模板、人物卡模板、秘密系统模板、情绪曲线规则 |
| short-drama-script | 竖屏剧本格式规范、单集钩子/卡点规则、对白规则 |
| short-drama-storyboard | 镜头语言(景别/运镜/时长)、视觉 prompt 引擎(文生图/图生视频) |
| short-drama-video-forge | 工具调用配方、角色一致性控制、失败降级配方(图文短剧) |
| short-drama-audio-forge | TTS 情感脚本规则、音乐情绪匹配、字幕断句规范 |
| short-drama-edit | ffmpeg 合成模板、成片验收清单 |
| short-drama-quality-gate | Gate 0~4 检查项、报告模板 |

**跨 skill 引用**:阶段 2 之后所有 skill 需读取上游固定路径产物(见 §八),质量门读取对应报告与产物。

---

## 六、失败回退策略

下游 skill 执行失败时的统一处理,分**硬阻断**与**软降级**两类:

### 6.1 硬阻断(质量门 FAIL)

由 `short-drama-quality-gate` 在 Gate 0~4 检出,不允许进入下一阶段,回原产出 skill 修复后重跑 Gate:

| 失败场景 | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0/1/2 FAIL(静态/契约) | **硬阻断**,不允许进入下一阶段 | 对应阶段 skill 修复后重跑 Gate |
| Gate 3 FAIL(分镜缺镜头/prompt 不可执行) | **硬阻断** | short-drama-storyboard 修复后重跑 |
| Gate 4 FAIL(manifest 缺镜头/音频缺失) | **硬阻断** | short-drama-video-forge / short-drama-audio-forge 修复后重跑 |

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
| 角色一致性漂移 | 标记受影响镜头,建议用角色参考图重新生成 |

**原则**:内容质量类问题(剧本/分镜/契约)硬阻断;资源类问题(图/视频/音频)软降级。

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
4. 调用 `short-drama-storyboard`,读取剧本,产出 `docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md`
   - **调用 `short-drama-quality-gate` Gate 3 分镜门**,产出 `docs/GATE_3_REPORT.md`;FAIL 则回 4 修复
   - ⏸ **人工确认点 4**:简报镜头总数/角色数/场景数,AskUserQuestion 询问"进入视频与音频生产 / 回退修改分镜 / 终止流水线"
5. **并行**调用 `short-drama-video-forge` 与 `short-drama-audio-forge`:前者产出 `production/manifest.json` + `shots/`,后者产出 `audio/` + `subtitles/`
   - **调用 `short-drama-quality-gate` Gate 4 生产门**,产出 `docs/GATE_4_REPORT.md`;FAIL 则回 5/6 修复
   - ⏸ **人工确认点 5**:简报镜头数/视频时长/音频文件数,AskUserQuestion 询问"进入剪辑合成 / 回退修复产物 / 终止流水线"
6. 调用 `short-drama-edit`,读取 manifest + shots + audio + subtitles,产出 `episodes/EP{XX}.mp4` + `docs/BUILD_REPORT.md`(内含 Gate 5 成片实跑门)
   - ⏸ **人工确认点 6**:简报成片路径+每集时长+验收结果,AskUserQuestion 询问"流水线完成 / 回退修复 / 进入打磨(可选)"
   - ⏸ **人工确认点 7(可选 Tool)**:若用户明确要"提交/发布",AskUserQuestion 询问"提交产物到 Git / 发布到平台 / 跳过"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit episodes/ + docs/ + production/,默认不 push)
     - 选"发布到平台" → 按目标平台指引(短视频平台人工上传 / Web 平台走 `web-static-deploy`)
     - 选"跳过" → 结束
   - Tool 操作前过 `guardrail` 前置检查

**不允许跳步**:即使某阶段被裁剪,也必须产出对应的占位文档(如视频生成裁剪也要在 manifest 中标注"该镜头用静态图")。**质量门不可跳过**(裁剪阶段跑 Gate 时,占位产物通过即可)。
**阶段 0 例外**:short-drama-topic-brainstorm 被跳过时**不产出占位文档**(可选增量)。
**人工确认不可跳过**:确认点 1~6 是强制暂停点,即使用户此前已表达"全流程执行",也必须在每个确认点等待用户明确选择后才继续。

**可选:产出 workflow.yaml 交 workflow-runtime 驱动执行**

本总纲的执行顺序(§七)可由 `workflow-runtime` skill 编译为可执行 `workflow.yaml`。产出 `workflow.yaml`(可选产物,见 §八)。workflow-runtime 模式下,pause 节点自动触发 AskUserQuestion,与本文确认点 1~7 一一对应。

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
| 生产清单 | `production/manifest.json` | short-drama-video-forge |
| 镜头视频 | `shots/{ep}/shot_{XX}.mp4` | short-drama-video-forge |
| 镜头占位图 | `shots/{ep}/shot_{XX}.png` | short-drama-video-forge(降级时) |
| 配音 | `audio/{ep}/line_{XX}.mp3` | short-drama-audio-forge |
| 音乐/BGM | `audio/bgm_{name}.mp3` | short-drama-audio-forge |
| 音频规格 | `docs/AUDIO_SPEC.md` | short-drama-audio-forge(音色映射/情感标签/语速/BGM 匹配标注;short-drama-edit 可选读取) |
| 字幕 | `subtitles/{ep}.srt` | short-drama-audio-forge |
| 成片 | `episodes/EP{XX}.mp4` | short-drama-edit |
| 验收报告 | `docs/BUILD_REPORT.md` | short-drama-edit |
| 质量门报告 0~4 | `docs/GATE_{0..4}_REPORT.md` | short-drama-quality-gate |
| 已知问题 | `docs/ASSET_ISSUES.md` | 任意(失败时写) |
| workflow.yaml(可选) | `workflow.yaml` | workflow-runtime(编译本总纲 §七 生成) |

**集数约定**:`EP{01..NN}` 为两位数编号;单集 1-3 分钟;单镜头 3-10 秒;一集约 10-25 个镜头。

---

## 九、用户交互约定

- 默认全程中文输出
- 每阶段完成后向用户简报产物路径与下一步
- 遇到选择(类型/工具链/裁剪)用 AskUserQuestion 确认,不擅自决定
- 全流程不依赖可视化编辑器,所有文档纯文本,视频/音频由工具链脚本化生成

### 9.1 人工确认机制(强制,见 §七 确认点 1~6)

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

**例外**:
- 阶段 0(脑暴)本身可选,用户确认推荐方案即进入阶段 1,不另设确认点
- 质量门 FAIL 时无需确认,直接回退修复(修复后重跑 Gate,Gate PASS 再走确认点)
- 确认点 7(可选 Tool)默认不强制出现,仅在用户明确要"提交/发布"时触发

**workflow-runtime 兼容**:workflow-runtime 模式下,确认点 1~7 对应 workflow.yaml 中的 pause 节点,选项与本文一致。
