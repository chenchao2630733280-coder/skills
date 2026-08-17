---
name: "short-drama-blueprint"
description: "Turn a confirmed short-drama topic (or docs/TOPIC_PROPOSAL.md) into a one-page project blueprint (pipeline stage 1). Defines genre/tags, platform & form, core selling point & viewing motivation, production type, scope, monetization, toolchain, complexity, stage trimming, and estimated artifact scale. Use when asked to make a blueprint, start the short-drama pipeline, or dispatched by short-drama-forge-master."
---

# Short Drama Blueprint — 短剧立项蓝图

本 skill 是 AI 短剧制作流水线（short-drama-forge-master）的**阶段 1**，职责是把用户需求（或 TOPIC_PROPOSAL.md 确认的选题）扩展成一页纸短剧立项蓝图，作为后续规格（short-drama-spec）/剧本（short-drama-script）/分镜（short-drama-storyboard）的总纲。

---

## 一、输入与输出

**输入**：
- 用户一句话需求（如"做一部战神逆袭竖屏短剧，全 AI 生成"）
- 或 `docs/TOPIC_PROPOSAL.md` 的"推荐方案"章节（阶段 0 产物）
- 可选：用户提供的参考短剧名/已有素材

**输出**（固定路径，与总纲 §八 一致，1 份文档）：
- `docs/SHORT_DRAMA_BLUEPRINT.md`

项目根目录为用户指定的短剧项目工作目录 `{project}/`。**禁止自定义输出路径**。

---

## 二、文档模板（11 章，严格按此结构，不增不减章节）

```markdown
# {短剧名} - 立项蓝图

> 一句话定义：{用户需求扩展后的精炼描述}

## 1. 一句话定义
{30 字以内的短剧核心定义}

## 2. 类型标签
- 题材：{都市/古装/悬疑/甜宠/逆袭/...}
- 核心情绪：{爽/虐/甜/惊/燃/...}
- 受众：{女性向/男性向/全年龄，年龄段}

## 3. 平台与形式
- 屏幕：{竖屏/横屏}（默认竖屏）
- 设计分辨率：1080x1920
- 单集时长：{1-3 分钟}
- 总集数：{60-100}
- 平台：{抖音/快手/视频号/红果/...}

## 4. 核心卖点与观看动力
- 核心卖点：{一句话，人无我有}
- 观看动力：{主动力 + 辅助动力}
- 四时间尺度卡点（简表）：
| 尺度 | 卡点设计 |
|---|---|
| 第一集 | ... |
| 前十集 | ... |
| 中段 | ... |
| 终局 | ... |

## 5. 制作类型
{全 AI 生成 / 图文短剧 / AI 数字人 / 真人实拍辅助}
判定规则见总纲 §3.1 与 references/production-type-decision.md

## 6. 范围边界
**做什么**：
- ...
**不做**（≥3 项）：
- ...
- ...
- ...

## 7. 商业化模式
{IAA 广告 / 分账 / 版权 / IP 联运，可组合，标注主次}

## 8. 工具链选型
制作类型：{...}
文生图：{即梦 / ...}
图生视频：{可灵 / ...}
TTS：{火山引擎 / ...}
音乐：{Suno / ...}
剪辑：{FFmpeg / ...}
理由：{一句话}

## 9. 复杂度评估
评级：{★~★★★★★}
| 维度 | 打分 |
|---|---|
| 场景数 | {...} |
| 角色数 | {...} |
| 特效量 | {...} |
| 镜头数 | {...} |
| 外部依赖 | {...} |
理由：{一句话}

## 10. 阶段裁剪建议
- short-drama-spec：执行 / 跳过（理由：...）
- short-drama-script：执行 / 跳过（理由：...）
- short-drama-storyboard：执行 / 跳过（理由：...）
- short-drama-video-forge：执行 / 跳过（理由：...）
- short-drama-audio-forge：执行 / 跳过（理由：...）
- short-drama-edit：执行（阶段 7 不裁剪，总纲 §四）
- 质量门 Gate 0~4：执行（必走，总纲 §四）

## 11. 估算产物规模
- 镜头总数：~{N} 个
- 音频文件数：~{N} 个（配音 + BGM）
- 成片总时长：{N} 分钟（{集数} × {单集分钟}）
```

---

## references 使用指引（懒加载）

| 文件 | 何时读取 |
|------|---------|
| `references/production-type-decision.md` | 填写"5. 制作类型"前必读 |
| `references/toolchain-selection.md` | 填写"8. 工具链选型"前必读 |

---

## 三、生成规则

### 1. 一句话定义
≤30 字，必须包含"主角 + 冲突 + 卖点"三要素之一以上。

### 2. 制作类型判定
读 `references/production-type-decision.md` 与总纲 §3.1，自上而下判定：
- 有真人演员/实拍素材 → 真人实拍辅助型
- 有真实人物肖像素材/口播台本 → AI 数字人型
- 需要完整剧情画面但无实拍 → 全 AI 生成型
- 低成本/快速验证 → 图文短剧型
- 用户明确指定 → 尊重用户选择（仍需做可行性检查）

判定后做可行性检查；不可行时降级并标注（见 runtime.yaml degrade 第 2 条）。

### 3. 工具链选型
读 `references/toolchain-selection.md` 与总纲 §3.2 决策树，按制作类型从选型表选"默认推荐"，每环节标注备选。决策依据四因素：**预算 / 质量要求 / 风格 / 宿主能力**。写入蓝图"8. 工具链选型"（格式见 §二 模板）。

### 4. 复杂度评级
按以下表打分，累计定级：

| 维度 | 1 分 | 2 分 | 3 分 | 4 分 | 5 分 |
|---|---|---|---|---|---|
| 场景数 | 1-2 | 3-4 | 5-8 | 9-15 | >15 |
| 角色数 | ≤3 | 4-6 | 7-10 | 11-20 | >20 |
| 特效量 | 无 | 少量 | 常规 | 较多 | 重度 |
| 镜头数 | <100 | 100-300 | 300-600 | 600-1200 | >1200 |
| 外部依赖 | 0 | 1 | 2 | 3 | >3 |

总分 5-8 → ★；9-12 → ★★；13-17 → ★★★；18-22 → ★★★★；23+ → ★★★★★

### 5. 范围边界
"做什么"必须可执行，"不做"≥3 项。常见"不做"项：
- 不做横屏版本（本期专注竖屏）
- 不做真人实拍（全 AI 生成）
- 不做多语言字幕
- 不做 100 集全量制作（先做 60 集验证）
- 不做 IP 衍生（本期只做正片）

### 6. 阶段裁剪建议
按总纲 §四"阶段裁剪规则"自动填，逐阶段标注执行/跳过 + 理由：
- 口播/数字人：跳过 storyboard/video-forge
- 图文短剧：跳过 video-forge，storyboard 只出图 prompt
- 全 AI 生成：全流程
- 真人实拍辅助：script/storyboard/edit 必走，其余裁剪
- 阶段 7（short-drama-edit）**不裁剪**：任何类型都要合成成片

### 7. 估算产物规模
按集数与单集镜头数估算：一集约 10-25 个镜头（总纲 §八）；音频文件数 = 每集对白条数 + BGM 数；成片总时长 = 集数 × 单集分钟。

---

## 四、交互约定

1. 用户输入需求后，**先用 AskUserQuestion 确认 1-2 个关键点**（如制作类型、是否需要实拍、预算），不要一次问太多
2. 确认后直接产出 `docs/SHORT_DRAMA_BLUEPRINT.md`
3. 产出后向用户简报："蓝图已生成，路径 docs/SHORT_DRAMA_BLUEPRINT.md。类型 {}，复杂度 {}，工具链 {}。下一步可调用 short-drama-spec 生成故事规格与分集大纲"
4. **不要**自行调用下游 skill，让用户决定是否继续
5. 用户需求矛盾时用 AskUserQuestion 澄清（见 runtime.yaml degrade 第 1 条）

---

## 五、质量检查清单

产出前自检：

- [ ] 一句话定义 ≤30 字
- [ ] 类型标签含题材/核心情绪/受众
- [ ] 平台与形式含竖屏/1080x1920/单集 1-3 分钟/总集数 60-100
- [ ] 核心卖点一句话清晰，观看动力含主动力+辅助动力
- [ ] 四时间尺度卡点简表完整
- [ ] 制作类型判定有依据（总纲 §3.1 / production-type-decision.md）
- [ ] 范围边界"不做"≥3 项
- [ ] 商业化模式明确（IAA/分账/版权/IP 联运，标注主次）
- [ ] 工具链选型按总纲 §3.2，每环节含默认+备选+理由
- [ ] 复杂度评级与各维度打分一致
- [ ] 阶段裁剪建议逐阶段标注执行/跳过+理由
- [ ] 估算产物规模含镜头总数/音频文件数/成片总时长
- [ ] 文档无 TODO/占位文字
- [ ] 自检未通过项已局部重做（≤2 轮）或标注交人工

---

## 六、与其他 skill 的关系

```
short-drama-topic-brainstorm → docs/TOPIC_PROPOSAL.md
    ↓ 用户确认
[本 skill] 立项蓝图
    ↓ 产出
docs/SHORT_DRAMA_BLUEPRINT.md
    ↓ Gate 0 立项门（short-drama-quality-gate）
docs/GATE_0_REPORT.md
    ↓ ⏸ 人工确认点 1
short-drama-spec → short-drama-script → ...
```

**关键约束**：
- 本 skill 不生成规格/剧本（职责边界）
- 本 skill 的产出是 short-drama-spec 的输入（契约化交接，路径见总纲 §八）
- 下游 skill 以 §八 固定路径读取本蓝图
