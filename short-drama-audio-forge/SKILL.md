---
name: "short-drama-audio-forge"
description: "AI short-drama pipeline stage 6 (audio; runs in parallel with video-forge). Reads the script docs/scripts/EP*.md and the storyboard docs/STORYBOARD.md, produces voice-over audio/{ep}/line_{XX}.mp3, BGM audio/bgm_{name}.mp3, and subtitles subtitles/{ep}.srt. Use when scheduled by short-drama-forge-master for this stage, or when the user asks to generate dubbing / BGM / sound effects / subtitles for a short drama."
---

# Short Drama Audio Forge — 配音 / 音乐 / 字幕

本 skill 是 AI 短剧制作流水线的**阶段 6(音频生产)**,与阶段 5(short-drama-video-forge)**并行执行**,职责是读取剧本与分镜,产出三路产物——配音、BGM/音效、字幕,供阶段 7(short-drama-edit)合成成片使用。

---

## 一、输入与输出

**输入**(必读):
- `docs/scripts/EP{01..NN}.md`:正式剧本(对白行、旁白、动作提示)
- `docs/STORYBOARD.md`:分镜(镜头号、时长、景别、音效/音乐提示)
- `docs/ASSET_MANIFEST.json`(**音色资产唯一来源**:取 `voice[]` 的 `voiceId`/`ttsVoiceName`/`timbre`/`speechRate`/`emotionTags`;必须 `status=locked`,音频裁剪时 `skipped=true`)
- `docs/VISUAL_SPEC.md`:角色视觉设定(仅用于理解角色,音色**以清册为准**)
- `docs/SHORT_DRAMA_BLUEPRINT.md`(取"8. 工具链选型"章节,TTS/音乐工具按蓝图决定)

> **音频层同样有资产基线**:音色由阶段 4.5 定妆锁定(每角色一个 `voiceId` + 试音样本)。本阶段**不选音色**,只按 `voiceId` 取音 —— 跨集音色漂移是观众最容易察觉的破绽之一。

**输出**(固定路径,与总纲 §八 严格一致):
- `audio/{ep}/line_{XX}.mp3`:每集每镜头配音(XX=镜头号,2 位补零)
- `audio/bgm_{name}.mp3`:BGM 曲目(name=情绪场景名)
- `audio/sfx_{name}.mp3`(可选):音效
- `subtitles/{ep}.srt`:每集字幕
- `docs/AUDIO_SPEC.md`:音频规格(音色映射/情感标签/语速/BGM 匹配标注)
- `docs/ASSET_ISSUES.md`:失败清单(追加,不覆盖)

> 配音文件名 `line_{XX}.mp3` 的 XX 必须与 STORYBOARD 镜头号一致,保证与 video-forge 的 `shots/{ep}/shot_{XX}.mp4` 一一对应,这是 Gate 4/5 音画对位的契约基础。

---

## 二、执行流程

```
0. 输入校验(见 二.1)
1. 解析剧本:抽取每集全部对白行(说话人/台词/旁白)
2. 解析分镜:镜头号→时长→音效/音乐提示
3. 构建"台词×镜头"映射表(一句台词↔一个镜头↔一个 line 文件)
4. TTS 情感配音(见 三)
5. 音乐/BGM(见 四)
6. 音效(可选,见 五)
7. 字幕生成(见 六)
8. 自检(见 八)+ 失败项写入 docs/ASSET_ISSUES.md
9. 输出汇总简报
```

### 二.1 输入校验(执行前一次性)

- 剧本文件缺失 → 报错"docs/scripts/EP*.md 缺失,请先调用 short-drama-script",列出期望路径,直接退出
- 分镜缺失 → 报错"docs/STORYBOARD.md 缺失,请先调用 short-drama-storyboard",直接退出
- 台词抽取时发现分镜缺少对应镜头号 → 记录到 ASSET_ISSUES,该句降级为"旁白式配音"(归入最近镜头),不阻塞

---

## 三、TTS 情感配音

### 3.1 角色→音色映射(取自 voice 资产,不得自选)

**取数契约**:每句台词的说话人 → 清册 `voice[].id`(经 `charId` 对应角色)→ 用该条目的 `ttsVoiceName` / `speechRate` 生成。**本阶段没有"挑音色"的权限。**

| 步骤 | 动作 |
|---|---|
| 1 | 读 `ASSET_MANIFEST.json` 的 `voice[]`,建立 `charId → voiceId / ttsVoiceName / speechRate / emotionTags` 映射 |
| 2 | 每条台词按说话人解析到 `charId`,再取 `voiceId`;解析不到 → 记入 ASSET_ISSUES,该句降级为旁白式配音 |
| 3 | 情感语速 = 资产基准 `speechRate` × 情感标签偏移(§3.2 表);**基准值不可改** |
| 4 | 情感标签必须 ∈ 该资产的 `emotionTags`;超出范围 → 记 ASSET_ISSUES 并就近归入已批准标签 |

- 映射结果写入 `docs/AUDIO_SPEC.md`(**引用 `voiceId`,而非重复描述音色**)
- 原则:**音色已由阶段 4.5 定妆锁定**;本阶段不做音色决策,只做忠实还原。音色不合适 → 回阶段 4.5 走资产变更流程,不在本阶段换音
- 音色参考表(阶段 4.5 定妆时的选音依据,本阶段仅供理解)见 `../short-drama-asset-forge/references/asset-baseline-rules.md` §4

### 3.1b 旁白/画外音的资产归属

旁白也必须有归属:若为某角色的内心独白 → 用该角色 `voiceId`(情感标签取 `平静`/`悲伤` 等);若为纯叙述旁白 → 在清册 `voice[]` 中登记一条 `voice_narrator`(阶段 4.5 产出),**不得临时用一个"看起来合适"的音色**。

### 3.2 情感标签体系

每句台词必须标注**情感标签 + 语速**(写入 AUDIO_SPEC 台词清单:台词/情感/语速/对应镜头号):

| 情感标签 | 默认语速 | 说明 |
|---|---|---|
| 平静 | 1.0x | 叙述、过场 |
| 愤怒 | 1.15x | 语气加重 |
| 悲伤 | 0.85x | 放慢、气声 |
| 惊喜 | 1.2x | 上扬、短促 |
| 恐惧 | 0.9x | 颤抖、压低 |
| 撒娇 | 0.95x | 尾音拖长 |
| 阴险 | 0.9x | 压低、慢、气声 |
| 兴奋/燃 | 1.2x | 高亢、有力 |
| 释然 | 0.9x | 松一口气、渐弱 |

情感标签从剧本上下文/情绪曲线推导,须与剧情一致(自检项)。

### 3.3 台词断句规则(与字幕共用)

- **按语义节奏断句**:主谓宾完整、语气停顿处断,不在介词/助词后硬断
- **单句 ≤20 字**,超过则拆成多句(同一 line 文件内可含多句,句间留 0.2-0.3s 静音)
- 标点保留:逗号/省略号即停顿点;问号/叹号表语气
- 断句结果同时用于字幕(见 六),保证对白/字幕/镜头三者一致

### 3.4 TTS 工具选型(总纲 §3.2)

| 场景 | 首选 | 备选 |
|---|---|---|
| 情感戏多(愤怒/悲伤/阴险) | 火山引擎 / 阿里 CosyVoice(情感音色) | 微软 Azure |
| 低成本/快速验证 | Edge TTS | MiniMax 语音 |
| 数字人口型(数字人型短剧) | 即梦数字人 / HeyGen(与嘴型同步) | 剪映数字人 |

- 每句生成后校验:时长与台词字数匹配(异常慢/快 → 重试 1 次)
- 单集全部生成完成后,抽样 2-3 句试听(如宿主支持播放)

---

## 四、音乐 / BGM

### 4.1 BGM 情绪匹配(情绪→场景)

| 情绪场景 | 适配 BGM | 用途 |
|---|---|---|
| 开场悬念 | 悬疑低频 pad、慢速 | EP 开场 |
| 冲突紧张 | 快节奏鼓点/弦乐 staccato | 冲突、追逃 |
| 甜宠温馨 | 轻快木琴/钢琴 | 恋爱、日常 |
| 虐心悲伤 | 钢琴慢板/弦乐长音 | 分离、误会 |
| 高潮燃 | 交响/电子鼓点 crescendo | 反转、爽点 |
| 结局释然 | 温暖钢琴/吉他渐弱 | EP 结尾 |

- **选曲**:优先从平台版权曲库按情绪标签选;需原创 OST 时用 Suno/Udio 生成(总纲 §3.2)
- 每首 BGM 写入情绪匹配标注(使用镜头段/情绪/建议电平),记入 `docs/AUDIO_SPEC.md`
- 命名 `audio/bgm_{name}.mp3`,name 用情绪场景名(如 `bgm_tension.mp3`)

### 4.2 BGM ducking 规则(对白优先)

| 场景 | BGM 目标电平 |
|---|---|
| 对白时 | 压到约 **-18dB**(sidechain 或固定衰减) |
| 纯音乐段落(无对白) | **-10dB** |
| 高潮卡点(无对白) | 可到 -6dB,随后让位对白 |

- 本 skill 只产出 BGM 文件 + 建议电平标注;ducking 混音由 short-drama-edit 执行

---

## 五、音效(可选)

- 按 STORYBOARD 每镜头的音效提示(打斗/开门/提示音等)生成或从平台素材库选取
- 命名 `audio/sfx_{name}.mp3`;短音效 <2s
- 缺失音效不阻塞:跳过并在 ASSET_ISSUES 标记"音效未配"

---

## 六、字幕

### 6.1 格式规范(subtitles/{ep}.srt)

- 标准 SRT:序号、时间轴 `HH:MM:SS,mmm --> HH:MM:SS,mmm`、正文
- **断句与 TTS 台词一致**(复用 3.3 断句结果),**每行 ≤20 字**
- 竖屏适配:正文不加空行,标点保留

### 6.2 时间轴推算

- 基准:对白实测时长(TTS 生成文件的实测时长)+ 镜头时长(STORYBOARD)
- 公式:字幕行开始 = 镜头开始时间;结束 = max(镜头结束,该镜头最后一句对白结束)
- 无对白镜头:按音效/音乐提示生成说明性字幕(如"【雨声】"),或留空
- **卡点句(结尾悬念字幕)**:醒目标注——在 SRT 中追加 `<!-- CLIMAX:{ep}:{序号} -->` 注释行(生成 ASS 时转为高亮样式),并在 AUDIO_SPEC 记录"卡点字幕位置"

### 6.3 字幕完整性

- 时间轴覆盖全片(首条从 0 或镜头开始,末条到片尾)
- 时间轴不重叠、不跳变;字幕行数与台词句数一致

---

## 七、输出规范汇总

| 产物 | 路径 | 命名规则 |
|---|---|---|
| 配音 | `audio/{ep}/line_{XX}.mp3` | XX=镜头号,2 位补零,与 STORYBOARD 一致 |
| BGM | `audio/bgm_{name}.mp3` | name=情绪场景名 |
| 音效 | `audio/sfx_{name}.mp3` | name=音效名 |
| 字幕 | `subtitles/{ep}.srt` | ep=EP{01..NN} |
| 音频规格 | `docs/AUDIO_SPEC.md` | 音色(**引用 voiceId**)/情感/语速/BGM 匹配标注 |
| 失败清单 | `docs/ASSET_ISSUES.md` | 追加,不覆盖 |

---

## 八、自检清单

- [ ] 每集台词全覆盖:剧本对白行→配音文件一一对应(数量/顺序/镜头号)
- [ ] 每句台词情感标签与剧情一致(对照剧本上下文)
- [ ] **每句台词声源可解析到清册 `voice[].id`;无"临时挑的音色"**
- [ ] **同角色全剧同一 `voiceId`(跨集音色一致);`AUDIO_SPEC.md` 以 voiceId 引用而非重述音色**
- [ ] **每句情感标签 ∈ 该 voice 资产的 `emotionTags`;超出者已记入 ASSET_ISSUES**
- [ ] TTS 使用的 `ttsVoiceName` 与清册一致(未擅自换音色/换工具音)
- [ ] 字幕时间轴覆盖全片,首尾闭合,无重叠
- [ ] 字幕每行 ≤20 字,断句与 TTS 台词一致
- [ ] BGM 每首有情绪匹配标注(镜头段/情绪/建议电平)
- [ ] 卡点句字幕已醒目标注
- [ ] 失败项已写入 ASSET_ISSUES.md
- [ ] 汇总简报数字与实际一致

---

## 九、失败回退(与 runtime.yaml degrade 一致)

| 失败场景 | 回退策略 |
|---|---|
| TTS 生成失败 | 静音占位(1s 静音 mp3)+ 字幕保留并标记"配音待补";或切换备选 TTS(§3.4)重试 ≤2 次 |
| 音乐生成失败 | 平台免费曲库 BGM 占位 + 标记 |
| 字幕时间轴缺失 | 按台词平均语速(约 4 字/秒)估算时间轴并标注"估算时间轴" |
| 分镜缺镜头对应台词 | 旁白式配音降级或跳过,记入 ASSET_ISSUES |
| **声源无法解析到 voiceId** | 该句记入 ASSET_ISSUES 并降级为旁白式配音;若整角色缺失 voice 资产 → **报错退出**,回阶段 4.5 补齐音色资产(不自行挑音) |
| **`voice.status != locked`(降级未签字)** | 若清册/ASSET_BASELINE 有签字 → 按 `ttsVoiceName` 直出并标 WARNING;无签字 → **报错退出** |
| **情感标签超出 `emotionTags`** | 就近归入已批准标签并记入 ASSET_ISSUES;不得新增标签(新增即资产变更) |

---

## references 使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/tts-emotion.md` | TTS 配音(§三):需要完整音色映射表/情感标签细分/断句示例时 |
| `references/music-matching.md` | 音乐/BGM(§四):需要 BGM 情绪匹配完整表与 ducking 参数时 |
| `references/subtitle-rules.md` | 字幕(§六):需要 srt 规范细节/时间轴公式/卡点字幕实现时 |
