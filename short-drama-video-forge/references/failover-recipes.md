# 失败降级配方(与总纲 §6.2 一致)

> 本文件对应 short-drama-forge-master §6.2 软降级策略。原则:资源类问题软降级,不阻塞流水线;所有降级写入 docs/ASSET_ISSUES.md,不允许静默。

---

## 1. 图生视频失败 → 静态图 + 模拟运镜

流程:保留质检通过的文生图 → ffmpeg zoompan 模拟运镜 → 落盘 `.png`(阶段 7 合成时叠加运镜)。

```bash
# 推镜头(缓慢放大)
ffmpeg -loop 1 -i shot.png -vf "zoompan=z='min(zoom+0.0015,1.15)':d=125:s=1080x1920:fps=25" -t 5 -c:v libx264 out.mp4
# 平移(自左向右)
ffmpeg -loop 1 -i shot.png -vf "crop=w=972:h=1728:x='min(108*t,108)':y=96,scale=1080:1920" -t 5 out.mp4
```

- manifest 标记:`status:"degraded", degradeType:"static-image"`
- 输出路径:`shots/{ep}/shot_{XX}.png`

---

## 2. 文生图失败 → 占位图

- 纯色底(如 #2A2A3A)+ 中央白字:镜头号 + "待人工出图"
- 尺寸 1080x1920,PNG
- 生成方式:代码直接写 PNG(PIL / ffmpeg color source),不调 AI
- manifest 标记:`degradeType:"placeholder"`

---

## 3. 视频生成接口全部不可用 → 整剧图文短剧模式

- 所有镜头降级为静态图(文生图正常)/占位图(文生图也失败)
- manifest 顶层标记:`project.mode:"image-text-drama"`
- 阶段 7(short-drama-edit)按"图+卡点+字幕+BGM"合成图文卡点成片
- 记入 ASSET_ISSUES.md 说明模式变更原因

---

## 4. 角色一致性漂移

- 检测:与参考图对比(发型/服装/肤色),或模型人脸相似度 < 阈值
- 处理:用参考图重生成(≤2 次);仍漂移 → manifest 标记 `degradeType:"character-drift"`,建议人工挑选后重生成
- 记入 ASSET_ISSUES.md 列出受影响镜头 id

---

## 5. 批量超时

- 分批执行(每批一集),批间暂停 ≥30s
- 超时镜头标记 `status:"failed"` + 原因,继续下一批,不整体重跑
- 重跑时 status=done 且文件存在的镜头跳过(增量)

---

## 6. ASSET_ISSUES.md 模板

```markdown
# 资源生成问题清单

生成时间:{ISO}
总镜头数:{N} | 成功:{S} | 降级:{D} | 占位:{P} | 失败:{F}

## 失败/降级清单

| 镜头 id | 类型 | 原因 | degradeType | 建议处理 |
|---|---|---|---|---|
| EP01-S03 | 图生视频失败 | API 超时×3 | static-image | 已出 png,阶段 7 模拟运镜 |
| EP02-S07 | 文生图失败 | 内容审核 | placeholder | 待人工出图 |

## 待人工处理

- [ ] EP02-S07 替换真实图
- [ ] EP05 角色漂移镜头重生成(见 character-drift 标记)
```

---

## 7. 原则

- 内容质量类(分镜/契约)问题 → 阻断,回上游;资源类(图/视频/音频)问题 → 软降级继续
- 降级必须可见:manifest degradeType + ASSET_ISSUES.md 双记录
