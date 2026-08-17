# Gate 0~4 检查项清单(逐项打勾)

本文件是 short-drama-quality-gate 的**执行清单**,执行每个 Gate 时对照本清单逐项打勾;检查项与 SKILL.md §三~§七 一一对应。

**勾选规则**:

| 标记 | 含义 | 对结论的影响 |
|---|---|---|
| [x] | 通过 | 计入 PASS |
| [ ] | 未通过(ERROR) | 计入 FAIL,硬阻断 |
| [~] | 无法校验(数据不足) | 计入"无法校验",结论 FAIL(数据不足),补齐后重跑 |
| [!] | 软问题(WARNING) | 不阻断,记录到报告 |

**结论规则**(与 SKILL.md §八 一致):任一 [ ] → FAIL;任一 [~] → FAIL(注明数据不足);仅 [x]/[!] → PASS。

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
| 0.6 | 复杂度评级一致 | 评级与维度打分(题材/画面/集数/工具链难度)结论一致 | G0-COMPLEXITY-MISMATCH | [ ] |
| 0.7 | 阶段裁剪逐阶段标注 | 每个可裁剪阶段有"执行/跳过+理由"(阶段 7 不裁剪) | G0-TRIM-INCOMPLETE | [ ] |

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

输入:`docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md`(+ `docs/scripts/EP*.md` 对照结尾卡点)

| # | 检查项 | 通过条件 | 失败码 | 打勾 |
|---|---|---|---|---|
| 3.1 | 每镜头字段完整 | 景别/运镜/时长/画面描述/文生图 prompt/图生视频 prompt 6 字段齐全 | G3-SHOT-FIELD-MISSING | [ ] |
| 3.2 | 单集镜头数 10-25 | 每集镜头数 ∈ [10, 25](总纲 §八) | G3-SHOT-COUNT-OUT | [ ] |
| 3.3 | 镜头总时长≈单集时长 | 每集镜头时长之和与该集时长估算偏差 ≤ ±15% | G3-TIMING-MISMATCH | [ ] |
| 3.4 | 角色/场景引用一致 | 分镜引用的角色/场景均在 VISUAL_SPEC 有定义 | G3-REF-UNDEFINED | [ ] |
| 3.5 | 每集结尾是卡点镜头 | 每集最后一个镜头对应剧本结尾卡点(强冲突/反转/悬念画面) | G3-FINAL-SHOT-WRONG | [ ] |
| 3.6 | VISUAL_SPEC 四要素 | 含角色(含一致性参考)/场景/风格/字幕样式 | G3-VISUAL-SPEC-INCOMPLETE | [ ] |

辅助软检查(不阻断):单镜头时长超出 3-10 秒(总纲 §八)的镜头 → 报告标 [!] WARNING。

---

## Gate 4 生产门(short-drama-video-forge + short-drama-audio-forge 后)

输入:`production/manifest.json` + `shots/{ep}/shot_{XX}.mp4`(或 png)+ `audio/{ep}/line_{XX}.mp3` + `audio/bgm_*.mp3` + `subtitles/{ep}.srt` + `docs/STORYBOARD.md`(镜头数)+ `docs/scripts/EP*.md`(对白行)+ `docs/ASSET_ISSUES.md`(降级记录)

| # | 检查项 | 通过条件 | 失败码 | 层 | 打勾 |
|---|---|---|---|---|---|
| 4.1 | manifest 每镜头字段完整 | 每镜头含 集号/镜头号/时长/源分镜引用/文件路径/配音引用 | G4-MANIFEST-FIELD-MISSING | L1 | [ ] |
| 4.2 | 镜头文件存在 | 每镜头有 shots/{ep}/shot_{XX}.mp4,或降级 png(总纲 §6.2) | G4-SHOT-FILE-MISSING | L3 | [ ] |
| 4.3 | 每集镜头数与 STORYBOARD 一致 | manifest 每集镜头数 = 分镜该集镜头数 | G4-SHOT-COUNT-MISMATCH | L2 | [ ] |
| 4.4 | 配音与对白一一对应 | audio/{ep}/line_{XX}.mp3 与剧本该集对白行一一对应 | G4-AUDIO-MISMATCH | L2 | [ ] |
| 4.5 | 字幕覆盖每集 | subtitles/{ep}.srt 每集存在且首尾时间轴覆盖全集 | G4-SRT-MISSING | L3 | [ ] |
| 4.6 | 降级项已标记 | 所有降级(视频→静态图/TTS→静音/音乐→曲库占位)已记入 docs/ASSET_ISSUES.md | G4-DEGRADE-UNMARKED | L2 | [ ] |

辅助软检查(不阻断):已标记的降级项(如 png 静态图、静音占位)汇总为 [!] WARNING 清单,供人工后补。
