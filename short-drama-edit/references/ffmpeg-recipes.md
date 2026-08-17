# FFmpeg 合成命令模板(懒加载)

> 何时读取:执行合成(SKILL.md §三/§四)需要完整可复用命令模板时。
> 环境要求:FFmpeg ≥ 4.4(含 zoompan/sidechaincompress/ass filter),Windows/Linux 均适用;路径含空格时用双引号包裹。

## 0. 前置:探测素材参数

```bash
# 探测视频分辨率/帧率/时长
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,duration -of csv=p=0 shots/EP01/shot_01.mp4
# 探测音频时长(配音校准)
ffprobe -v error -show_entries format=duration -of csv=p=0 audio/EP01/line_01.mp3
```

## 1. 镜头拼接

### 1.1 同参数镜头(免重编码,最快)

```bash
# 生成 list.txt(file 后接相对路径,UTF-8)
echo "file 'shots/EP01/shot_01.mp4'" > list.txt
echo "file 'shots/EP01/shot_02.mp4'" >> list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy prep_EP01.mp4
```

### 1.2 参数不一致/需统一(重编码,推荐流水线用)

```bash
ffmpeg -f concat -safe 0 -i list.txt -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p" \
  -c:v libx264 -b:v 6M -r 30 -c:a aac -b:a 192k prep_EP01.mp4
```

- 竖屏强制 1080x1920:不足边用 pad 补黑,多出边裁切(center crop 见 1.3)
- 此步同时完成"镜头时长按 manifest 校准":超长镜头用 `-t {duration}` 截断,过短镜头用 `tpad` 补帧

### 1.3 中心裁切(素材非 9:16 时)

```bash
ffmpeg -i shot_01.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" shot_01_crop.mp4
```

## 2. 转场

### 2.1 硬切(默认)

硬切无需额外 filter,拼接即可(见 §1)。

### 2.2 淡入淡出(≤0.5s,场景切换/情绪转折处)

```bash
# 单镜头:前 0.3s 淡入、后 0.3s 淡出
ffmpeg -i shot_03.mp4 -vf "fade=t=in:st=0:d=0.3,fade=t=out:st={dur-0.3}:d=0.3" -c:v libx264 -c:a copy shot_03_fade.mp4
```

### 2.3 叠化(xfade,两镜头间 0.5s 交叉淡化)

```bash
ffmpeg -i shot_03.mp4 -i shot_04.mp4 -filter_complex \
  "[0:v][1:v]xfade=transition=fade:duration=0.5:offset={dur3-0.5}[v]" \
  -map "[v]" -c:v libx264 -c:a copy xfade_03_04.mp4
```

> 转场总时长 ≤0.5s;叠化会吃掉两镜头各 0.25s,注意对白起点偏移。

## 3. 静态图运镜(zoompan)

静态图镜头(`shot_{XX}.png`)用缩放/平移模拟运镜:

```bash
# 缓慢推近:镜头时长 5s → d=150(30fps × 5s)
ffmpeg -loop 1 -t 5 -i shots/EP01/shot_05.png -vf \
  "scale=2160:3840,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920:fps=30" \
  -c:v libx264 -t 5 shot_05_motion.mp4
```

- 推近:zoom 递增;拉远:zoom 递减(`max(1.5-0.0015*on,1)`);平移:固定 zoom、x/y 递增
- 先放大 2 倍再 zoompan(减少抖动),输出 `-t 5` 强制时长
- 参数 `d=总帧数`;同参数镜头混入 concat 时须先统一帧率/分辨率(§1.2)

## 4. 混音(对白 + BGM ducking + 音效)

### 4.1 BGM sidechain ducking(首选,动态压 BGM)

```bash
ffmpeg -i video_silent.mp4 -i audio/EP01/bgm_tension.mp3 -i audio/EP01/line_01.mp3 -i audio/EP01/line_02.mp3 \
  -filter_complex \
  "[1:a]volume=1.0[bgm];\
   [2:a][3:a]concat=n=2:v=0:a=1,apad[voice];\
   [bgm][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[bgmd];\
   [voice][bgmd]amix=inputs=2:duration=first:dropout_transition=0[aout]" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k mixed_EP01.mp4
```

- threshold 越低 ducking 越敏感;对白密集可调 `threshold=0.05`
- 纯音乐段落(无对白轨)用静态电平:-10dB(高潮 -6dB):
  ```bash
  -filter_complex "[1:a]volume=-10dB[aout]"   # 或 -6dB
  ```

### 4.2 静态分段衰减(备选,按 AUDIO_SPEC 分段标注)

```bash
# 0-5s -10dB,5-12s -18dB(对白段),12-18s -6dB(卡点)
ffmpeg -i video.mp4 -i audio/EP01/bgm_tension.mp3 -filter_complex \
  "[1:a]volume='if(lt(t,5),-10,if(lt(t,12),-18,-6))':eval=frame[bgmd];\
   [2:a][bgmd]amix=inputs=2[aout]" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac mixed_EP01.mp4
```

### 4.3 音效混入(可选,约 -12dB)

```bash
ffmpeg -i mixed_EP01.mp4 -i audio/sfx_door.mp3 -filter_complex \
  "[1:a]volume=-12dB,adelay=3500|3500[sfx];[0:a][sfx]amix=inputs=2:duration=first[aout]" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac mixed_sfx_EP01.mp4
```

## 5. 字幕烧录(srt → ass → 烧录)

### 5.1 srt → ass(调整样式)

```bash
# ffmpeg 自动转换(默认样式,可选)
ffmpeg -i subtitles/EP01.srt -c:s ass -f ass subtitles/EP01.ass
```

或直接写 ass(竖屏安全区样式,卡点句高亮):

```ass
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Outline, Shadow, Alignment, MarginV
Style: Default,Noto Sans CJK SC,52,&H00FFFFFF,&H00000000,&H00000000,0,0,2,0,1,2,180
Style: Climax,Noto Sans CJK SC,62,&H0000D7FF,&H00000000,&H00000000,1,0,2,0,1,2,180

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.50,0:00:03.20,Default,,0,0,0,,你终于来了。
Dialogue: 0,0:01:39.80,0:01:42.50,Climax,,0,0,0,,可他……不是已经死了吗？
```

- MarginV=180 → 字幕下沿 y≈1920-180=1740(安全区内)
- Climax 样式:金色+加粗+大字号,对应 audio-forge 的 CLIMAX 注释条目
- 逐条时间轴与 srt 一致;不要逐条手抄,用脚本从 srt 生成(见 scripts/build_episodes.py)

### 5.2 烧录字幕

```bash
ffmpeg -i mixed_sfx_EP01.mp4 -vf "ass=subtitles/EP01.ass" -c:a copy final_EP01.mp4
```

> 烧录失败降级:不烧录,输出独立 `subtitles/EP01.srt` 并标注"未烧录,发布前需人工烧录"(SKILL.md §六)。

## 6. 导出(最终参数)

```bash
ffmpeg -i final_EP01.mp4 -c:v libx264 -b:v 6M -maxrate 8M -bufsize 12M \
  -r 30 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart \
  episodes/EP01.mp4
```

- 码率 4-8Mbps 区间:画面简单用 4M,特效/快速运动用 6-8M;`-maxrate 8M` 封顶
- `-movflags +faststart` 让 moov 前置(短视频平台秒开)

## 7. 验收命令(Gate 5 实跑门用)

```bash
# 时长/分辨率
ffprobe -v error -show_entries format=duration -of csv=p=0 episodes/EP01.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 episodes/EP01.mp4
# 静音段检测(astats 每 1s 统计,音量近 0 的段 >2s 判静音)
ffmpeg -i episodes/EP01.mp4 -af "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" -f null - 2>&1 | grep RMS
# 对白起点定位(音量峰值时间点,用于音画同步比对)
ffmpeg -i episodes/EP01.mp4 -af "silencedetect=noise=-35dB:d=0.3" -f null - 2>&1 | grep silence_start
```

## 8. 常见坑

1. **concat 参数不一致花屏**:先统一 scale/fps/pix_fmt 再拼接(§1.2)
2. **zoompan 抖动**:输入先放大 2 倍再 zoompan;zoom 用小数步进(0.0015/帧)
3. **sidechaincompress 无声**:确认对白轨在 amix 前存在且非静音;threshold 过小会全压
4. **字幕中文乱码**:ass 文件必须 UTF-8;字体用系统已装 CJK 字体(如 Noto Sans CJK/微软雅黑)
5. **卡点句被截断**:烧录前确认卡点字幕结束时间 < 片尾 ≥0.5s(Gate 5 卡点完整项)
6. **Windows 路径**:所有路径双引号包裹,list.txt 用相对路径(concat demuxer 相对 list 文件解析)
