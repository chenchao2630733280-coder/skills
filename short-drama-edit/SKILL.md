---
name: "short-drama-edit"
description: "AI short-drama pipeline stage 7 (final edit, contains the Gate 5 runnable gate). Reads production/manifest.json + shots/ + audio/ + subtitles/, assembles each episode into episodes/EP{XX}.mp4, and writes docs/BUILD_REPORT.md including the Gate 5 acceptance results. Use when scheduled by short-drama-forge-master for this stage, or when the user asks to edit / assemble / mux the final episodes of a short drama."
---

# Short Drama Edit — 剪辑合成成片

本 skill 是 AI 短剧制作流水线的**阶段 7(最终合成,任何类型均不可裁剪)**,职责是读取生产清单、镜头素材、配音/BGM、字幕,用 **FFmpeg 脚本化**合成每集成片,产出 `episodes/EP{XX}.mp4`,并内置 **Gate 5 成片实跑门**,将验收结果写入 `docs/BUILD_REPORT.md`。

---

## 一、输入与输出

**输入**(必读):
- `production/manifest.json`:生产清单(每集镜头顺序/时长/类型,short-drama-video-forge 产出)
- `shots/{ep}/shot_{XX}.mp4`(或降级静态图 `shot_{XX}.png`):镜头素材
- `audio/{ep}/line_{XX}.mp3`、`audio/bgm_{name}.mp3`、`audio/sfx_{name}.mp3`(short-drama-audio-forge 产出)
- `subtitles/{ep}.srt`:字幕
- `docs/AUDIO_SPEC.md`(如有,BGM 分段电平标注)
- `docs/GATE_4_REPORT.md`(如有,了解已知问题)

**输出**(固定路径,与总纲 §八 严格一致):
- `episodes/EP{XX}.mp4`:每集成片(XX=两位数编号)
- `docs/BUILD_REPORT.md`:合成与验收报告(内含 Gate 5 结果)

> manifest 结构以 short-drama-video-forge 产出为准;本 skill 的最小读取契约:每集含 `episode`、`shots[]`(每镜头含 `shot_id`、`file`、`type`(video/image)、`duration`、可选 `line`(对应配音文件))、`bgm`。字段缺失时按 §六 降级。

---

## 二、执行流程

```
0. 输入校验(见 二.1)
1. 解析 manifest,按集分组,生成"每集镜头序列"
2. 逐集生成 ffmpeg 命令(见 三/四;可复用 scripts/build_episodes.py)
3. 执行合成(逐集,单集失败不阻塞其他集,见 六)
4. 逐集跑 Gate 5 验收(见 五),结果写入 docs/BUILD_REPORT.md
5. 输出汇总简报
```

### 二.1 输入校验(执行前一次性)

- `production/manifest.json` 缺失 → 报错"manifest 缺失,请先调用 short-drama-video-forge",列出期望路径,退出
- JSON 解析失败 → 报错附原文片段,退出
- manifest 中引用的镜头文件缺失 → **不退出**,走占位降级(见 六),并在报告标注

---

## 三、合成流程细则

对每集按以下顺序合成:

1. **镜头拼接**:按 manifest 的镜头顺序拼接;镜头时长**以 manifest 为准校准**(与剧本不符的镜头按 manifest 重排,超长镜头用转场压缩)
2. **转场**:硬切为主;关键处(场景切换/情绪转折/卡点前)用淡入淡出或叠化,**单次转场 ≤0.5s**
3. **静态图运镜**:静态图镜头(`shot_{XX}.png`)用 zoompan 缩放/平移模拟运镜,时长=镜头时长(§四模板)
4. **混音**:对白轨 + BGM(ducking:对白时约 -18dB、纯音乐段 -10dB、高潮卡点 -6dB,按 AUDIO_SPEC 标注)+ 音效轨(可选,约 -12dB)
5. **字幕烧录**:srt → ass(竖屏 1080x1920 底部安全区 y≈1720-1760,白字+黑描边,字号 48-56px,卡点句高亮),烧录进画面
6. **导出**:**1080x1920(竖屏)** mp4,H.264,码率 **4-8Mbps**,帧率 **30fps**,AAC 音频

> 完整可复用命令模板见 `references/ffmpeg-recipes.md`,执行合成前懒加载。

---

## 四、FFmpeg 命令模板速览(详见 references)

- **镜头拼接(同参数)**:`ffmpeg -f concat -safe 0 -i list.txt -c copy prep.mp4`(参数不一致时改用 concat filter 重编码)
- **静态图运镜**:`-loop 1 -t {dur} -i shot.png -vf "zoompan=z='min(zoom+0.0015,1.5)':d={frames}:s=1080x1920:fps=30"`
- **BGM ducking(sidechain)**:`-filter_complex "[bgm][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[bgmd];[voice][bgmd][sfx]amix=3"`
- **烧字幕**:`-vf "ass=subtitle.ass"`(srt 先经 ffmpeg 或库转 ass)
- **导出**:`-c:v libx264 -b:v 6M -r 30 -c:a aac -b:a 192k -pix_fmt yuv420p`

---

## 五、Gate 5 成片实跑门(内置)

每集成片产出后**必须逐项实跑验收**(用 ffprobe/脚本检测,不靠目测):

| 检查项 | 验收标准 | 判定方式 |
|---|---|---|
| 时长 | 1-3 分钟 ±15% | ffprobe 实测 |
| 音画同步 | 对白起点对齐镜头(对白声轨起点 ≈ 对应镜头起点 ±0.3s) | 对白能量检测/抽样对比 |
| 字幕覆盖 | 字幕覆盖全片且无超长行(>20 字) | 解析 srt 校验 |
| 集数完整 | EP01..NN 全部产出 | 目录扫描 |
| 分辨率 | 1080x1920 | ffprobe |
| 无静音片断 | 无明显静音段(除非剧本要求) | 音频能量检测 |
| 卡点完整 | 结尾卡点镜头完整呈现,未被截断 | 片尾 ≥0.5s 抽样 |

**验收结果写入 docs/BUILD_REPORT.md**,每集一节(模板):

```markdown
### EP01 合成验收
- 时长: 1m45s(目标 1-3 分钟)→ PASS
- 文件大小: 28.4 MB
- 分辨率: 1080x1920 → PASS
- 音画同步: PASS / 字幕覆盖: PASS / 无静音段: PASS / 卡点完整: PASS
- 检查项汇总: 7/7 PASS
- 失败清单: (无)
```

**失败项必须列"失败清单"**(检查项/实测值/原因/建议处理),FAIL 不阻塞报告输出;集数完整 FAIL 时列出缺失集。

---

## 六、失败回退(与 runtime.yaml degrade 一致)

| 失败场景 | 回退策略 |
|---|---|
| 单集合成失败 | 清理中间文件后重试 **≤2 次**;仍失败则输出失败清单+原因,**不阻塞其他集** |
| 缺镜头文件 | 用**占位黑场**(黑屏 + 字幕"待补拍"标记)替代该镜头,写入报告 |
| 字幕烧录失败 | 输出独立 `subtitles/{ep}.srt` 并标注"未烧录,发布前需人工烧录" |
| 音频轨缺失(配音/BGM 缺失) | 保留画面+字幕,标注"音频待补",不阻塞 |

---

## 七、scripts 说明

`scripts/build_episodes.py`(可选工具):读取 `production/manifest.json`,为每集自动生成 ffmpeg 命令清单(或直接执行),用于流水线自动化;用法见脚本头部 docstring。无脚本时按 §三/§四 手动生成命令亦可,脚本与手写二选一,不强制。

---

## 八、质量检查清单

- [ ] 每集 `episodes/EP{XX}.mp4` 存在且可被 ffprobe 读取
- [ ] 集数完整(EP01..NN 齐全)
- [ ] 每集通过 Gate 5 全部检查项,或已记录失败清单
- [ ] BUILD_REPORT.md 每集含时长/文件大小/检查项 PASS/FAIL + 失败清单
- [ ] 降级项全部写入报告(占位黑场/待补拍/未烧录标记)

---

## references 使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/ffmpeg-recipes.md` | 合成命令(§三/四):需要完整可复用命令模板(拼接/混音/字幕/运镜/导出)时 |
