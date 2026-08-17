---
name: "short-drama-quality-gate"
description: "Cross-stage quality gate for the AI short-drama production pipeline. Intervenes at 5 checkpoints (Gate 0 post-blueprint, Gate 1 post-spec, Gate 2 post-script, Gate 3 post-storyboard, Gate 4 post-production) to run contract validation and runtime pre-checks; on FAIL it hard-blocks the pipeline and returns fix suggestions. Read-only on business artifacts (writes gate reports only). Call when short-drama-forge-master dispatches a Gate 0~4 checkpoint, or when the user asks to validate / gate-check / inspect the short-drama production artifacts."
---

# 短剧流水线质量门(short-drama-quality-gate)

## 一、定位与职责

本 skill 是 AI 短剧制作流水线(short-drama-forge-master 总纲)的**跨阶段质检员**,在 Gate 0~4 五个关键节点介入做契约校验与实跑预检,不通过则硬阻断流水线并给出修复建议。解决"各阶段自检宽松、错误累积到剪辑阶段才爆发"的结构性风险。

**三层校验机制**:

| 层 | 名称 | 职责 | 不通过行为 |
|---|---|---|---|
| L1 | 静态门 | 字段完整性 / 格式 / 命名 / 路径 | 硬阻断(ERROR) |
| L2 | 契约门 | 跨阶段一致性(蓝图↔规格↔剧本↔分镜↔生产) | 硬阻断(ERROR) |
| L3 | 实跑预检 | 实际读文件系统验证(镜头文件 / 配音 / 字幕存在) | 缺失硬阻断;降级仅标记 |

**只读原则**:本 skill 不修改任何业务产物,只读 + 校验 + 输出报告。FAIL 时返回失败清单与修复建议,**修复由原产出 skill 重跑完成**,本 skill 不接管修复职责(避免"自审自修"与职责越界)。

**门禁范围**:只管 Gate 0~4。**Gate 5 成片实跑门内置于 short-drama-edit**,本 skill 不重复校验,下游可引用其 `docs/BUILD_REPORT.md` 作参考。

**不越级原则**:每次执行只针对当前 Gate 的输入产物,不检查其他阶段的产物。

## 二、五个检查点总览(与总纲 §二/§七 对应)

```
short-drama-blueprint → docs/SHORT_DRAMA_BLUEPRINT.md
   ↓ [Gate 0] 立项门 → docs/GATE_0_REPORT.md (FAIL 回阶段 1)
short-drama-spec → docs/STORY_SPEC.md + docs/EPISODE_OUTLINE.md
   ↓ [Gate 1] 规格门 → docs/GATE_1_REPORT.md (FAIL 回阶段 2)
short-drama-script → docs/scripts/EP{01..NN}.md
   ↓ [Gate 2] 剧本门 → docs/GATE_2_REPORT.md (FAIL 回阶段 3)
short-drama-storyboard → docs/STORYBOARD.md + docs/VISUAL_SPEC.md
   ↓ [Gate 3] 分镜门 → docs/GATE_3_REPORT.md (FAIL 回阶段 4)
short-drama-video-forge ∥ short-drama-audio-forge → production/ + shots/ + audio/ + subtitles/
   ↓ [Gate 4] 生产门 → docs/GATE_4_REPORT.md (FAIL 回阶段 5/6)
short-drama-edit(内置 Gate 5 成片实跑门,不属于本 skill)
```

| 检查点 | 时机 | 层 | 输入(固定路径,总纲 §八) | 输出 | 回退 |
|---|---|---|---|---|---|
| Gate 0 立项门 | 蓝图后 | L1+L2 | docs/SHORT_DRAMA_BLUEPRINT.md | docs/GATE_0_REPORT.md | 回阶段 1 |
| Gate 1 规格门 | 规格后 | L1+L2 | docs/STORY_SPEC.md + docs/EPISODE_OUTLINE.md(+蓝图总集数) | docs/GATE_1_REPORT.md | 回阶段 2 |
| Gate 2 剧本门 | 剧本后 | L1+L2 | docs/scripts/EP*.md(+大纲+STORY_SPEC) | docs/GATE_2_REPORT.md | 回阶段 3 |
| Gate 3 分镜门 | 分镜后 | L1+L2 | docs/STORYBOARD.md + docs/VISUAL_SPEC.md | docs/GATE_3_REPORT.md | 回阶段 4 |
| Gate 4 生产门 | 视频+音频后 | L1+L2+L3 | production/manifest.json + shots/ + audio/ + subtitles/(+分镜/剧本/ASSET_ISSUES) | docs/GATE_4_REPORT.md | 回阶段 5/6 |

## 三、Gate 0 立项门(short-drama-blueprint 后)

### 3.1 输入
- `docs/SHORT_DRAMA_BLUEPRINT.md`

### 3.2 检查项(全部 L1/L2,ERROR 硬阻断)

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 0.1 | 一句话定义 | ≤30 字 | G0-DEFINITION-TOO-LONG |
| 0.2 | 制作类型明确 | 存在且 ∈ {全 AI 生成, 图文短剧, 真人实拍辅助, 口播短剧, AI 数字人型} | G0-TYPE-INVALID |
| 0.3 | 类型与裁剪一致 | 阶段裁剪与类型特征匹配(口播短剧→跳过 storyboard/video-forge;图文短剧→跳过 video-forge;全 AI 生成→全流程) | G0-TYPE-TRIM-MISMATCH |
| 0.4 | 工具链选型完整 | 文生图/图生视频/TTS/音乐/剪辑 5 环节均选定工具(裁剪环节标注"不适用"即可) | G0-TOOLCHAIN-INCOMPLETE |
| 0.5 | 范围边界"不做" | 明确"不做"项 ≥3 | G0-SCOPE-NOT-ENOUGH |
| 0.6 | 复杂度评级一致 | 评级与维度打分(题材/画面/集数/工具链难度)结论一致 | G0-COMPLEXITY-MISMATCH |
| 0.7 | 阶段裁剪逐阶段标注 | 每个可裁剪阶段有"执行/跳过+理由"(阶段 7 不裁剪) | G0-TRIM-INCOMPLETE |

### 3.3 说明
本门把"能不能立项"的决策要素契约化,保证下游规格阶段有可依赖的基线(类型/集数/工具链/边界)。裁剪项标注"不适用"时,该工具链环节按通过计。

## 四、Gate 1 规格门(short-drama-spec 后)

### 4.1 输入
- `docs/SHORT_DRAMA_BLUEPRINT.md`(总集数)
- `docs/STORY_SPEC.md`
- `docs/EPISODE_OUTLINE.md`

### 4.2 检查项(全部 L1/L2,ERROR 硬阻断)

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 1.1 | 故事发动机八要素 | 主角/欲望/启动事件/不能退出原因/核心阻碍/对手/升级机制/最终选择 8 项齐全 | G1-ENGINE-MISSING |
| 1.2 | 分集数与蓝图一致 | EPISODE_OUTLINE 集数 = 蓝图总集数 | G1-EPISODE-COUNT-MISMATCH |
| 1.3 | 每集开场钩子+结尾卡点 | 大纲每集均有"开场钩子"与"结尾卡点"字段 | G1-HOOK-CLIFFHANGER-MISSING |
| 1.4 | 卡点类型不连续重复 | 相邻两集卡点类型不同(情感/悬念/反转/危机等交替) | G1-CLIFFHANGER-REPEAT |
| 1.5 | 情绪曲线结构 | 整部情绪曲线满足 3 爽点 / 2 反转 / 1 最低点 | G1-EMOTION-CURVE-WEAK |
| 1.6 | 规格评分 | STORY_SPEC 评分 ≥60;<60 阻断 | G1-SCORE-LOW |

### 4.3 说明
1.6 评分字段缺失时该检查项标"无法校验"(见 §九),不猜测结论。故事发动机与情绪曲线是后续剧本/分镜的秘密揭露与爽点排布依据,1.1/1.5 缺失会导致 Gate 2/3 无契约可对。

## 五、Gate 2 剧本门(short-drama-script 后)

### 5.1 输入
- `docs/scripts/EP{01..NN}.md`(每集一文件,总纲 §八 约定)
- `docs/EPISODE_OUTLINE.md`(集数/卡点对照)
- `docs/STORY_SPEC.md`(秘密揭露节奏)

### 5.2 检查项(全部 L1/L2,ERROR 硬阻断)

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 2.1 | 集数齐全且与大纲一致 | EP 文件数 = 大纲集数;编号 EP01..NN 连续无缺号 | G2-EPISODE-FILES-MISMATCH |
| 2.2 | 开场 5 秒出钩子 | 每集开场(前 5 秒 / 前 2 句对白)即进入钩子 | G2-OPENING-HOOK-MISSING |
| 2.3 | 结尾强卡点且类型与前集不同 | 每集结尾有强卡点;类型与前集不重复 | G2-ENDING-WEAK / G2-CLIFFHANGER-REPEAT |
| 2.4 | 对白单句 ≤20 字 | 每句对白(不含标点)≤20 字 | G2-DIALOGUE-TOO-LONG |
| 2.5 | 每集台词量 300-600 字 | 每集对白总字数 ∈ [300, 600] | G2-DIALOGUE-VOLUME-OUT |
| 2.6 | 主角每集有具体行动 | 每集主角有推进剧情的主动行动(非纯旁观/被叙述) | G2-PROTAGONIST-PASSIVE |
| 2.7 | 秘密揭露节奏一致 | 剧本各集揭露的秘密点与 STORY_SPEC 秘密系统节奏表一致 | G2-SECRET-RHYTHM-MISMATCH |
| 2.8 | 时长估算 1-3 分钟 | 每集标注时长估算(或按台词量折算)∈ [1, 3] 分钟(总纲 §八) | G2-DURATION-OUT |

### 5.3 说明
对白字数按中文字符计(是否含标点的口径在报告中注明)。台词量过少(<300)说明该集信息量不足,过多(>600)会导致单集超时,都直接影响 Gate 3 的时长拆分。

## 六、Gate 3 分镜门(short-drama-storyboard 后)

### 6.1 输入
- `docs/STORYBOARD.md`
- `docs/VISUAL_SPEC.md`
- (`docs/scripts/EP*.md` 对照结尾卡点)

### 6.2 检查项(全部 L1/L2,ERROR 硬阻断)

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 3.1 | 每镜头字段完整 | 景别/运镜/时长/画面描述/文生图 prompt/图生视频 prompt 6 字段齐全 | G3-SHOT-FIELD-MISSING |
| 3.2 | 单集镜头数 10-25 | 每集镜头数 ∈ [10, 25](总纲 §八) | G3-SHOT-COUNT-OUT |
| 3.3 | 镜头总时长≈单集时长 | 每集镜头时长之和与该集时长估算偏差 ≤ ±15% | G3-TIMING-MISMATCH |
| 3.4 | 角色/场景引用一致 | 分镜引用的角色/场景均在 VISUAL_SPEC 有定义 | G3-REF-UNDEFINED |
| 3.5 | 每集结尾是卡点镜头 | 每集最后一个镜头对应剧本结尾卡点(强冲突/反转/悬念画面) | G3-FINAL-SHOT-WRONG |
| 3.6 | VISUAL_SPEC 四要素 | 含角色(含一致性参考)/场景/风格/字幕样式 | G3-VISUAL-SPEC-INCOMPLETE |

### 6.3 说明
单镜头时长遵循总纲 §八(3-10 秒),超范围镜头在报告中标 WARNING(不阻断),剪辑阶段可按 manifest 重排。3.4 是角色一致性漂移(总纲 §6.2 软降级)的前置拦截:引用未定义角色,后续必然出图漂移。

## 七、Gate 4 生产门(short-drama-video-forge + short-drama-audio-forge 后)

### 7.1 输入
- `production/manifest.json`
- `shots/{ep}/shot_{XX}.mp4`(或降级 png)
- `audio/{ep}/line_{XX}.mp3` + `audio/bgm_*.mp3`
- `subtitles/{ep}.srt`
- `docs/STORYBOARD.md`(镜头数对照)、`docs/scripts/EP*.md`(对白行对照)
- `docs/ASSET_ISSUES.md`(降级记录)

### 7.2 检查项(L1/L2/L3,ERROR 硬阻断)

| # | 检查项 | 通过条件 | 失败码 | 层 |
|---|---|---|---|---|
| 4.1 | manifest 每镜头字段完整 | 每镜头含 集号/镜头号/时长/源分镜引用/文件路径/配音引用 | G4-MANIFEST-FIELD-MISSING | L1 |
| 4.2 | 镜头文件存在 | 每镜头有 shots/{ep}/shot_{XX}.mp4,或降级 png(总纲 §6.2) | G4-SHOT-FILE-MISSING | L3 |
| 4.3 | 每集镜头数与 STORYBOARD 一致 | manifest 每集镜头数 = 分镜该集镜头数 | G4-SHOT-COUNT-MISMATCH | L2 |
| 4.4 | 配音与对白一一对应 | audio/{ep}/line_{XX}.mp3 与剧本该集对白行一一对应 | G4-AUDIO-MISMATCH | L2 |
| 4.5 | 字幕覆盖每集 | subtitles/{ep}.srt 每集存在且首尾时间轴覆盖全集 | G4-SRT-MISSING | L3 |
| 4.6 | 降级项已标记 | 所有降级(视频→静态图/TTS→静音/音乐→曲库占位)已记入 docs/ASSET_ISSUES.md | G4-DEGRADE-UNMARKED | L2 |

### 7.3 说明
- 资源类降级(如图生视频失败→单帧静态图+镜头运动)**不阻断**,但必须已在 `docs/ASSET_ISSUES.md` 标记;已标记的降级项在报告中列为 WARNING 清单。
- 未标记的降级按契约违约处理(4.6 ERROR):下游剪辑会误以为加载的是真视频。
- 缺失镜头文件(既无 mp4 也无 png)按总纲 §六.1 硬阻断,回 short-drama-video-forge / short-drama-audio-forge。

## 八、报告输出

- **固定路径**:`docs/GATE_{0..4}_REPORT.md`,与总纲 §八 路径表严格一致;模板见 `references/report-template.md`。
- **结构**:结论(PASS/FAIL)+ 检查项明细表(检查项/结果/证据/说明)+ FAIL 修复指引 + 软问题/无法校验清单。
- **结果枚举**:PASS / FAIL / WARNING(不阻断)/ 无法校验(数据不足)。
- **阻断规则**:
  - 任一 ERROR → 结论 FAIL → 硬阻断,不允许进入下一阶段(引用总纲 §六.1)
  - 存在"无法校验"项 → 结论 FAIL(注明"数据不足,非内容判定"),补齐后重跑本 Gate
  - 仅 WARNING/PASS → 结论 PASS
- **FAIL 修复指引**必须含:修复建议 + 回退到哪个阶段 skill(见 §十)+ 引用总纲 §六.1 对应行。
- **归档**:4 份 Gate 报告随项目保留,作为质量追溯依据;short-drama-edit 的 BUILD_REPORT.md 应引用 Gate 0~4 结论。

## 九、校验规则与严重度分级

| 级别 | 定义 | 处理 |
|---|---|---|
| ERROR | 静态/契约类问题(字段缺失/不一致/不达标)+ 资源缺失(无 mp4 无 png) | **硬阻断**:FAIL,回原阶段修复后重跑本 Gate |
| WARNING | 资源类降级(已标记)、超范围镜头时长等软问题 | 不阻断,记录到报告,供人工后补 |
| 无法校验 | 检查项数据不足(字段缺失/内容为空/文件无法读取) | 标注"无法校验",**不猜测结论**,建议补齐后重跑 |

**每次执行只针对当前 Gate,不越级检查**:本 Gate 未声明对照的上游产物不做校验;上下游一致性只做本 Gate 已列出的 L2 对照项。

## 十、与 short-drama-forge-master 的契约

### 10.1 接入位置(总纲 §七)

```
阶段 1 short-drama-blueprint → Gate 0(FAIL 回阶段 1)
阶段 2 short-drama-spec      → Gate 1(FAIL 回阶段 2)
阶段 3 short-drama-script    → Gate 2(FAIL 回阶段 3)
阶段 4 short-drama-storyboard→ Gate 3(FAIL 回阶段 4)
阶段 5 video-forge∥audio-forge → Gate 4(FAIL 回阶段 5/6)
阶段 6 short-drama-edit      → 内置 Gate 5 成片实跑门(不属于本 skill)
```

### 10.2 失败回退(引用总纲 §六.1 硬阻断规则)

| Gate | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0/1/2 FAIL | 硬阻断,不允许进入下一阶段 | 对应阶段 skill(blueprint/spec/script)修复后重跑 Gate |
| Gate 3 FAIL | 硬阻断 | short-drama-storyboard 修复后重跑 |
| Gate 4 FAIL | 硬阻断(manifest 缺镜头/音频缺失) | short-drama-video-forge / short-drama-audio-forge 修复后重跑 |

### 10.3 裁剪规则
- **Gate 不可裁剪**:即使阶段被裁剪(如口播短剧跳过 storyboard/video-forge),也要跑 Gate;裁剪阶段以占位产物通过(如 manifest 标注"该镜头用静态图")。
- 本 skill 不触发人工确认点(确认点 1~6 由总纲在 Gate PASS 后用 AskUserQuestion 执行)。

## 十一、运行时降级(runtime.yaml)

| 场景 | 行为 |
|---|---|
| 上游产物缺失(输入文件/目录不存在) | **阻断**本次 Gate,输出缺失文件清单,建议回退对应阶段 skill 补齐后重跑 |
| 检查项数据不足 | 该检查项标注"无法校验",建议补齐后重跑,**不猜测结论** |
| 报告生成失败(docs/GATE_*.md 写盘失败) | 降级输出纯文本结论(PASS/FAIL + 缺失项清单),标注报告未落盘 |

## 十二、本 skill 质量自查

- [ ] 5 个 Gate 检查项无遗漏(对照 references/gate-checks.md)
- [ ] 每次只跑当前 Gate,不越级
- [ ] 报告固定路径 docs/GATE_{0..4}_REPORT.md,与总纲 §八 一致
- [ ] 明细表含 检查项/结果/证据/说明 四列
- [ ] FAIL 含 修复建议 + 回退 skill + 引用总纲 §六.1
- [ ] 只读原则:不修改任何业务产物
- [ ] 无法校验时不猜测结论
- [ ] 已标记降级不阻断;未标记降级按 4.6 阻断
- [ ] 正文中文、描述英文;references 与 runtime.yaml 齐备
