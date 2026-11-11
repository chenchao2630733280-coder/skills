---
name: "game-forge-master"
description: "AI 生成游戏的通用编排总纲。包含引擎选择决策树(Phaser 3/Pixi.js/纯 Canvas/Godot 4/Unity/Three.js)、阶段裁剪规则、模板索引、失败回退策略与质量门接入。当用户要'用 AI 生成/制作一个游戏'、'端到端生成游戏工程'、'按流水线生成游戏'时调用。"
---

# Game Forge Master — AI 游戏生成总纲

本 skill 是整套"AI 生成游戏"流水线的**调度中枢**,本身不直接产出游戏文件,职责是:
1. 接收用户一句话需求,决定走哪条生成路径
2. 选择目标引擎(Phaser 3 / Pixi.js / 纯 Canvas / Godot 4 / Unity / Three.js)
3. 裁剪阶段(简单游戏可跳过音频/网络/任务系统)
4. 串联下游各阶段 skill(蓝图→规格→关卡难度→美术→资源/代码→集成)+ 跨阶段质量门的执行顺序
5. 提供通用模板索引与失败回退策略 + 质量门阻断规则

---

## 一、何时调用

满足以下任一条件即调用本 skill:
- 用户说"用 AI 生成/做一个游戏"
- 用户说"按流水线生成游戏工程"
- 用户给了游戏雏形需求,需要端到端产出可运行工程
- 用户调用了任意 `game-*` 系列 skill 但未先经过总纲

**阶段 0 路由**:若用户需求模糊(如"做个小游戏"但未明确核心玩法),或明确要"脑暴选题/找点子",先调用 `game-topic-brainstorm` 产出 `docs/TOPIC_PROPOSAL.md`,用户确认推荐方案后再进入阶段 1。

**阶段 0.5 路由(复刻专线)**:若用户需求**含明确参考对象**(点名某款游戏 / 给录屏截图要求"按这个做" / 要求"复刻、对标、拆解竞品"),先调用 `game-teardown` 产出 `docs/GAME_TEARDOWN.md` + `docs/TEARDOWN_MATRIX.json` + `docs/NUMERIC_MODEL.csv`,再进入阶段 1。**复刻专线与选题脑暴互斥**,不要同时走。

**不要**在以下场景调用:
- 用户只是问"游戏怎么做"(纯咨询,用对话回答即可)
- 用户要修改已有游戏的某一处代码(直接用 Edit/Write)
- 用户要做的是 3D 游戏且明确不使用 Godot 4 / Unity / Three.js(流水线不覆盖其它 3D 引擎)

---

## 二、流水线总览

```
用户一句话需求
       ↓
(需求模糊?) ──是──→ game-topic-brainstorm → docs/TOPIC_PROPOSAL.md
       │ 否                                    ↓
       ↓ ←─────────────────────────────────────┘
(含参考对象/要复刻?) ──是──→ game-teardown → docs/GAME_TEARDOWN.md
       │ 否                                  + docs/TEARDOWN_MATRIX.json
       │                                     + docs/NUMERIC_MODEL.csv
       │                                        ↓
       │                            [Gate 0.5] 拆解门 → docs/GATE_0_5_REPORT.md
       │                                        ↓ (FAIL 则回 0.5 修复)
       ↓ ←─────────────────────────────────────┘
[本 skill] 引擎选择 + 阶段裁剪
       ↓
game-blueprint    → docs/GAME_BLUEPRINT.md
       ↓
[Gate 0] 蓝图门 → docs/GATE_0_REPORT.md (FAIL 则回 1 修复)
       ↓
⏸ 人工确认点 1 (AskUserQuestion: 进入规格 / 回退 / 终止)
       ↓
game-spec         → docs/PRD.md + docs/TECH_DESIGN.md
       ↓
[Gate 1] 规格门 → docs/GATE_1_REPORT.md (FAIL 则回 2 修复)
       ↓
⏸ 人工确认点 2 (AskUserQuestion: 进入关卡设计 / 回退 / 终止)
       ↓
game-level-design → docs/LEVEL_PLAN.md + docs/LEVEL_AUTHORING.md + config/levels.json + docs/DIFFICULTY_REPORT.md
       ↓
[Gate 2.5] 关卡门 → docs/GATE_2_5_REPORT.md (FAIL 则回 2.5 修复)
       ↓
game-art-spec     → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json + docs/AUDIO_SPEC.md
       ↓
[Gate 2] 美术门 → docs/GATE_2_REPORT.md (FAIL 则回 3 修复)
       ↓
⏸ 人工确认点 3 (AskUserQuestion: 进入资源+代码 / 回退 / 终止;简报含关卡难度摘要)
       ↓
┌──────────────────┐  ┌──────────────────┐
│ game-asset-forge │  │ game-code-forge  │  (可并行;后者读 config/levels.json)
│  生成 assets/    │  │  生成 src/       │
└──────────────────┘  └──────────────────┘
       ↓
[Gate 3] 产物门 → docs/GATE_3_REPORT.md (FAIL 则回 4 修复,L3 失败由 game-code-forge 接手修复≤3轮)
       ↓
⏸ 人工确认点 4 (AskUserQuestion: 进入集成 / 回退 / 终止)
       ↓
game-integrate    → dist/ + 验收报告 (内含 Gate 4 实跑门)
       ↓
⏸ 人工确认点 5 (AskUserQuestion: 进入打磨(可选) / 完成 / 回退)
       ↓
⏸ 人工确认点 6 (可选 Tool,AskUserQuestion: 提交 Git / 部署平台 / 跳过;Tool 前过 guardrail 前置检查)
       ↓
game-polish (可选) → 视觉/手感/反馈打磨 + docs/POLISH_REPORT.md
```

**阶段性质**:
- 阶段 0(game-topic-brainstorm):**可选**,用户需求模糊或要脑暴选题时调用
- 阶段 0.5(game-teardown):**可选(复刻专线)**,需求含参考对象时调用;与阶段 0 互斥
- 阶段 1~5(蓝图→规格→美术→资源/代码→集成):**必走**,产出可玩游戏
- 阶段 2.5(game-level-design):**关卡制必走**,单局制可裁剪(仍需产出 LEVEL_PLAN 占位);产出关卡数值契约,早于代码生成
- 阶段 6(game-polish):**可选**,在可玩游戏基础上叠加效果,不改玩法
- **质量门 Gate 0~3:必走**,由 game-quality-gate 介入,FAIL 时硬阻断回原阶段修复;**复刻专线额外必走 Gate 0.5**(拆解门,在蓝图之前,FAIL 不进蓝图);**关卡制项目额外必走 Gate 2.5**(关卡门,在规格门之后、美术门之前)
- **质量门 Gate 4:实跑门**,内置于 game-integrate,沿用其现有裁剪规则
- **人工确认点 0.5 与 1~5:强制暂停**(0.5 仅复刻专线),每阶段 Gate PASS 后用 AskUserQuestion 确认,不允许自动进入下一阶段(见 §九.1)

**关键约束**:每阶段产物的路径与文件名固定,下游 skill 必须按固定路径读取上游产物,不允许自定义路径。
**workflow-runtime 驱动(可选)**:本流水线可由 `workflow-runtime` skill 编译为 `workflow.yaml` 自动驱动执行,详见 §七 末尾说明。

---

## 三、引擎选择决策树

根据游戏类型与复杂度自动选择引擎:

```
用户需求
   ├─ 2D 跑酷/平台/塔防/卡牌/消除 → 默认 Phaser 3
   ├─ 大量粒子/特效/自定义渲染 → Pixi.js
   ├─ 极简(纯文字/几何图形) → 纯 Canvas
   ├─ 2D 桌面游戏(需 exe/原生窗口) → Godot 4
   ├─ 2D + 高性能渲染需求(不需 exe,如重度 2D 手游/大量动态光影) → Godot 4
   ├─ 3D 游戏(中小型/开源优先) → Godot 4
   ├─ 3D Web H5(真透视/大量实例化单位/需浏览器直开) → Three.js
   ├─ 3D 复杂游戏/需 Unity 生态/跨平台工业级发布 → Unity
   └─ 用户明确指定 → 尊重用户选择
```

### 决策细则

| 游戏特征 | 推荐引擎 | 理由 |
|---|---|---|
| 默认 2D 游戏 | **Phaser 3** | 内置动画/碰撞/音频/场景/输入,AI 不用造轮子 |
| 需要自定义 shader/大量特效 | Pixi.js | 渲染性能最强,但需 AI 自补动画/碰撞 |
| 纯文字/几何(如 2048) | 纯 Canvas | 零依赖,AI 100% 可生成 |
| 复杂物理(真实重力/弹簧) | Phaser 3 + Matter.js | Phaser 内置 Matter 集成 |
| 网格类(消除/三消) | Phaser 3 | 用 Phaser 的 grid + tween 足够 |
| 弹幕类 | Pixi.js | 大量 sprite 需要 WebGL 高吞吐 |
| 2D 桌面游戏(需原生窗口/exe) | **Godot 4** | 原生导出 exe/pck,无需浏览器,性能优于 Web |
| 2D + 高性能渲染(不需 exe,如重度 2D 手游/大量动态光影) | **Godot 4** | 原生渲染性能优于 Web(Phaser 3/Pixi.js 受浏览器 WebGL 约束),适合高吞吐粒子/复杂着色器 |
| 3D 游戏(中小型/开源优先) | **Godot 4** | 内置 3D 物理/光照/骨骼动画,AI 可用 GDScript 生成 |
| 3D Web H5(真透视/数百实例化单位/纯代码可生成) | **Three.js** | InstancedMesh + 曲线路径 + 程序化几何,浏览器直开可自测,无需编辑器 |
| 复杂 2D+3D 混合 | **Godot 4** | 统一引擎,2D/3D 混合渲染无需切换 |
| 3D 复杂游戏/需 Unity 生态 | **Unity** | 工业级 3D 渲染、Asset Store 资源、跨平台发布最强 |
| 需要 C# 生态/现有 Unity 团队 | **Unity** | C# 生态成熟,团队技能复用 |
| 移动端重度 3D 游戏 | **Unity** | iOS/Android 3D 性能优化最成熟,发布链路最完整 |

### 决策结果写入

引擎选择结果写入 `docs/GAME_BLUEPRINT.md` 的"3. 平台与引擎"章节,格式:
```
平台:Web H5
引擎:Phaser 3.80.x
依赖:phaser、axios(如需网络)
理由:[一句话]
```

```
平台:Web H5
引擎:Three.js + TypeScript + Vite
依赖:three、vite、typescript
理由:[一句话]
```

```
平台:Web H5
引擎:Godot 4.3
依赖:godot(无需 npm 依赖)
理由:[一句话]
```

```
平台:Windows Desktop(或 iOS/Android/WebGL)
引擎:Unity 2022.3 LTS
依赖:unity(需宿主安装 Unity Editor,无 npm 依赖)
理由:[一句话]
```

---

## 四、阶段裁剪规则

不是所有游戏都要走完整 6 阶段。根据复杂度裁剪:

| 复杂度 | 特征 | 裁剪 |
|---|---|---|
| ★ 极简 | 单屏 + 无动画 + 无音效 | 跳过 art-spec/asset-forge,占位图直接进 code |
| ★★ 简单 | 单场景 + 简单动画 + 无网络 | 跳过 audio-spec(用静音占位) |
| ★★★ 中等 | 多场景 + 帧动画 + 简单 UI | 全流程,音频走静音占位 |
| ★★★★ 复杂 | 多场景 + 帧动画 + 弹窗 + 网络 + 任务 | 全流程,音频走 AI 生成 |
| ★★★★★ 极复杂 | 多场景 + 多角色 + 多动画 + 后端 + 商业化 | 全流程 + 建议人工 review |

**阶段 2.5(game-level-design)的裁剪规则**(独立判断,看是否有"关卡序列"):

| 触发条件 | 是否执行 |
|---|---|
| 三消/合成/解谜/塔防/跑酷关卡制、有难度递进或章节进度 | ✓ 必走 |
| 单局制、无关卡序列(2048 / 单屏街机 / 无尽模式无阶段目标) | ✗ 裁剪,但产出 `docs/LEVEL_PLAN.md` 占位(写明"无关卡序列 + 难度靠 X 机制") |
| 关卡数据已存在,只做微调 | ✓ 走轻量模式(只跑曲线+跳变,标注 `SIM_SKIPPED`) |
| 已接入线上通关数据 | ✓ 必走,并用真实数据校准后重跑 |

裁剪结果写入 `docs/GAME_BLUEPRINT.md` §10,追加一行:`2.5. game-level-design: 执行/裁剪(理由: ...)`。

**阶段 0.5(game-teardown)的深度裁剪**(按复刻档位,与上表复杂度无关):

| 复刻档位 | 拆解范围 |
|---|---|
| T0 学习原型 | 仅 Pass A(循环+规则 L1)+ 敏感度 Top3;数值只写区间 |
| T1 玩法克隆 | Pass A + Pass B(数值 L2/内容 L1)+ Pass C 的反馈清单 |
| T2 高保真复刻 | 全 4 个 Pass,关键项到 L3,交互到状态机级 |
| T3 商业产品 | T2 + 维度 12(运营与商业化)+ 合规风险评级 |

裁剪结果写入 `docs/GAME_TEARDOWN.md` §0 的"证据覆盖"行,并在蓝图 §10 标注。

**阶段 6(game-polish)的裁剪规则**(独立判断,不依赖上表复杂度):

| 触发条件 | 是否执行 polish |
|---|---|
| 用户明确要求"优化效果/加特效/打磨动画" | ✓ 执行 |
| 用户说"画面太单调/不够好看/手感差" | ✓ 执行 |
| 用户未提及,但游戏类型适合(跑酷/平台/养成) | 默认执行(可在 confirm 阶段跳过) |
| 纯文字/几何游戏(2048/数独) | ✗ 跳过(无动画可优化) |
| 回合制游戏 | ✗ 跳过(优化空间小) |
| 用户明确说"不用优化/够用了" | ✗ 跳过 |

裁剪结果写入 `docs/GAME_BLUEPRINT.md` 的"10. 阶段裁剪建议",追加一行:
```
6. game-polish: 执行/跳过 (理由: ...)
```

---

## 五、通用模板索引

各下游 skill 自带 `references/` 目录,维护本阶段所需的模板和规范文件,**无统一 game-template 工程**。各 skill 的 references 清单:

| skill | references 内容 |
|-------|----------------|
| game-topic-brainstorm | 无 references(复用 game-blueprint 的设计原则) |
| game-teardown | 5 份拆解手册(12 维逐维/数值反解/状态建模/解空间与难度/合规边界)+ TEARDOWN_MATRIX schema |
| game-blueprint | 7 个 design-principles-*.md(设计原则) |
| game-spec | 无 references(PRD+TECH_DESIGN 内联生成) |
| game-level-design | 13 份参考(难度模型库/评估框架/跳变分类/推荐引擎/流水线接入契约)+ campaign 与关卡评审模板 |
| game-art-spec | 2 个风格基线文件 + ASSET_MANIFEST schema |
| game-asset-forge | format-conversion-guide.md + card-bg-spec.md |
| game-code-forge | 6 个 engine-*-template.md(六引擎模板) + 6 个 pitfall 文件 + web-config-template.md |
| game-integrate | build-report-template.md |
| game-polish | asset-fix-recipes.md + overlay-spec.md |
| game-quality-gate | 5 个 engine-checks-*.md(六引擎中纯 Canvas 复用 Phaser 的 Web 通用检查) |

**跨 skill 引用**:game-topic-brainstorm 引用 `../game-blueprint/references/` 下的设计原则;game-blueprint 在复刻模式读取 game-teardown 的 `docs/GAME_TEARDOWN.md` §0 摘要;两总纲引用 `../workflow-runtime/references/execution-semantics.md`。

下游 skill 生成产物时,按引擎和阶段读取自身 references 目录中的模板文件。

---

## 六、失败回退策略

下游 skill 执行失败时的统一处理,分**硬阻断**与**软降级**两类:

### 6.1 硬阻断(质量门 FAIL)

由 `game-quality-gate` 在 Gate 0~3 检出,不允许进入下一阶段,回原产出 skill 修复后重跑 Gate:

| 失败场景 | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0.5 FAIL(拆解产物缺/X 无替代/推断无 falsifier/M 项未落地) | **硬阻断**,**不进蓝图** | game-teardown 补拆后重跑 Gate 0.5 |
| Gate 0/1/2 FAIL(静态/契约) | **硬阻断**,不允许进入下一阶段 | 对应阶段 skill 修复后重跑 Gate |
| Gate 2.5 FAIL(关卡产物缺失 / levels.json 与 PRD 关卡表不一致 / 参数越界 / 门禁结论无处置) | **硬阻断**,不允许进入美术+资源+代码生成 | game-level-design 修复后重跑 Gate 2.5(禁止调宽阈值放行) |
| Gate 3 L1/L2 FAIL(文件缺失/契约不符/代码内联复制关卡数值) | **硬阻断** | game-asset-forge / game-code-forge 修复后重跑 Gate 3 |
| Gate 3 L3 typecheck/Godot check FAIL | **硬阻断**,返回错误日志 | game-code-forge 接手修复(沿用其自身 typecheck 修复策略,≤3 轮)后重跑 Gate 3 |

### 6.2 软降级(允许继续,标记到报告)

沿用原策略,失败项汇总到 `docs/BUILD_REPORT.md` 与 `docs/ASSET_ISSUES.md`,不阻塞流水线:

| 失败场景 | 回退策略 |
|---|---|
| AI 生图失败 | 占位图(纯色 + 文字标识) + 标记到 `docs/ASSET_ISSUES.md` |
| 切图/图集打包失败 | 降级用散图(性能略差但能跑) |
| 音频生成失败 | 1 秒静音 wav 占位 + 标记 |
| Gate 3 L3 Unity 跳过(沙箱无 Editor) | 标注 `G3-UNITY-SKIPPED`,允许进入 Gate 4,由 game-integrate 补 |
| 浏览器自测失败(Gate 4) | 输出失败清单 + 截图,不阻塞构建 |
| 资源加载 404 | 自动用占位图替代 + 标记 |
| Unity Editor 未安装 | 标记"需宿主安装 Unity 2022.3 LTS",代码与配置仍产出,构建延后到宿主环境 |
| Unity .unity 场景生成失败 | 降级:SceneBuilder 仅生成 Main 场景,BootScene 用代码动态创建 |

**原则**:质量类问题(设计/契约/类型)硬阻断;资源类问题(图/音/场景)软降级。

---

## 七、执行顺序(必须严格遵循,每阶段人工确认)

调用本 skill 后,必须按以下顺序执行下游 skill 与质量门。**每个阶段完成后必须暂停,用 AskUserQuestion 向用户确认后再进入下一阶段**(见 §九 确认规则):

0. **(可选)** 若需求模糊或用户要脑暴选题,调用 `game-topic-brainstorm`,产出 `docs/TOPIC_PROPOSAL.md`,用户确认推荐方案后进入下一步
0.5 **(可选·复刻专线)** 若需求含参考对象(点名游戏/录屏截图/"做个像 XX 的"),调用 `game-teardown`,产出 `docs/GAME_TEARDOWN.md` + `docs/TEARDOWN_MATRIX.json` + `docs/NUMERIC_MODEL.csv`
   - 与步骤 0 互斥;档位 T0~T3 与材料一次性问清(AskUserQuestion 1 轮)
   - **调用 `game-quality-gate` Gate 0.5 拆解门**,产出 `docs/GATE_0_5_REPORT.md`;FAIL 则回 0.5 补拆,**不进蓝图**
   - ⏸ **人工确认点 0.5**:Gate 0.5 PASS 后,简报"档位 / 证据覆盖 N/12 / 决定性变量 / X 项替代情况 / 灰盒 MVP 一句话",AskUserQuestion 询问"进入蓝图 / 重新拆解 / 终止"
1. 调用 `game-blueprint`,产出 `docs/GAME_BLUEPRINT.md`
   - 复刻模式下蓝图**必须**读取 `docs/GAME_TEARDOWN.md` §0 摘要,并按 `game-teardown` §15.1 交接映射填写,不得跳章
   - **调用 `game-quality-gate` Gate 0 蓝图门**,产出 `docs/GATE_0_REPORT.md`;FAIL 则回 1 修复
   - ⏸ **人工确认点 1**:Gate 0 PASS 后,简报蓝图摘要,AskUserQuestion 询问"进入规格设计 / 回退修改蓝图 / 终止流水线"
2. 调用 `game-spec`,读取蓝图,产出 `docs/PRD.md` + `docs/TECH_DESIGN.md`
   - **调用 `game-quality-gate` Gate 1 规格门**,产出 `docs/GATE_1_REPORT.md`;FAIL 则回 2 修复
   - ⏸ **人工确认点 2**:Gate 1 PASS 后,简报 PRD 关键数值/UI 节点树,AskUserQuestion 询问"进入美术规范 / 回退修改规格 / 终止流水线"
2.5 调用 `game-level-design`,读取 `docs/PRD.md` + `docs/TECH_DESIGN.md`(+ 可选 `docs/NUMERIC_MODEL.csv`、线上 attempts.csv),产出 `docs/LEVEL_PLAN.md` + `docs/LEVEL_AUTHORING.md` + `config/levels.json` + `docs/DIFFICULTY_REPORT.md` + `docs/DIFFICULTY_REVIEW.json`
   - 关卡制必走;单局制裁剪但产出 `docs/LEVEL_PLAN.md` 占位
   - **调用 `game-quality-gate` Gate 2.5 关卡门**,产出 `docs/GATE_2_5_REPORT.md`;FAIL 则回 2.5 修复(不得靠调宽阈值放行)
   - 关卡表会作为美术场景/主题数量的输入,不要跳过就进美术
3. 调用 `game-art-spec`,读取 PRD + TECH_DESIGN + 可选 `config/levels.json`(关卡主题/场景清单),产出 `docs/ART_SPEC.md` + `docs/ASSET_MANIFEST.json` + `docs/AUDIO_SPEC.md`
   - **调用 `game-quality-gate` Gate 2 美术门**,产出 `docs/GATE_2_REPORT.md`;FAIL 则回 3 修复
   - ⏸ **人工确认点 3**:Gate 2 PASS 后,简报"manifest 资源数量/风格基线 + 关卡难度摘要(N 关 / 各阶段目标首通率 / HIGH 数)",AskUserQuestion 询问"进入资源+代码生成 / 回退修改美术或关卡 / 终止流水线"
4. **并行**调用 `game-asset-forge` 和 `game-code-forge`,分别产出 `assets/` 和 `src/`
   - **调用 `game-quality-gate` Gate 3 产物门**,产出 `docs/GATE_3_REPORT.md`;FAIL 则回 4 修复(L3 失败由 game-code-forge 接手修复,≤3 轮)
   - ⏸ **人工确认点 4**:Gate 3 PASS 后,简报资源/代码产物统计,AskUserQuestion 询问"进入集成构建 / 回退修复产物 / 终止流水线"
5. 调用 `game-integrate`,读取 assets + src(Web 引擎)或 Godot/Unity 工程,产出 `dist/`(Web)或 `export/`(Godot)或 `Build/`(Unity) + `docs/BUILD_REPORT.md`(内含 Gate 4 实跑门)
   - ⏸ **人工确认点 5**:集成完成后,简报构建产物路径 + 浏览器自测结果,AskUserQuestion 询问"进入效果打磨(可选) / 流水线完成 / 回退修复构建问题"
   - ⏸ **人工确认点 6（可选 Tool）**：集成完成后(或确认点 5 选"流水线完成"后),若用户明确要"提交/部署",AskUserQuestion 询问"提交产物到 Git / 部署到平台 / 跳过 Tool 操作"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit dist/export/Build/ + docs/,默认不 push)
     - 选"部署到平台" → 调用 `tool-deploy-ops`(需先 git commit;Web 引擎可部署 dist/,Godot/Unity 需先导出)
     - 选"跳过" → 进入阶段 6(若尚未进入)或结束
   - Tool 操作前过 `guardrail` 前置检查(检查 dist/export/Build/ + docs/ 路径是否在敏感清单)
6. (可选)若阶段 6 未被裁剪且用户确认进入,调用 `game-polish`,读取可运行工程 + `docs/POLISH_REQUEST.md`(如有),产出 `src/effects/` 增量 + `docs/POLISH_REPORT.md`

**不允许跳步**:即使某阶段被裁剪,也必须产出对应的占位文档(如音频裁剪也要写一个最小 AUDIO_SPEC.md 标注"全部静音占位"),且**质量门不可跳过**(裁剪阶段跑 Gate 时,占位文档通过即可)。
**阶段 0 / 0.5 / 6 例外**:game-topic-brainstorm、game-teardown 和 game-polish 被跳过时**不产出占位文档**(它们是可选增量,无占位概念)。
**人工确认不可跳过**:确认点 1~5 是强制暂停点(复刻专线另加确认点 0.5),即使用户此前已表达"全流程执行",也必须在每个确认点等待用户明确选择后才继续。

**可选:产出 workflow.yaml 交 workflow-runtime 驱动执行**

本总纲的执行顺序(§七)可由 `workflow-runtime` skill 编译为可执行 `workflow.yaml`,支持暂停/恢复/跳过/回退/并行调度。编译命令:

```
python ../workflow-runtime/scripts/compile_workflow.py compile-from-master --master SKILL.md --section "§七" --output workflow.yaml
```

产出 `workflow.yaml`(可选产物,见 §八 路径总表)。workflow-runtime 模式下,pause 节点自动触发 AskUserQuestion,与本文 §九.1 的人工确认点(确认点 1~6)一一对应。详见 `../workflow-runtime/SKILL.md`。

---

## 八、产物路径总表

所有 skill 必须遵守的固定路径:

| 产物 | 路径 | 由哪个 skill 产出 |
|---|---|---|
| 选题方案(可选) | `docs/TOPIC_PROPOSAL.md` | game-topic-brainstorm |
| 复刻拆解报告(可选) | `docs/GAME_TEARDOWN.md` | game-teardown |
| 复刻矩阵(可选) | `docs/TEARDOWN_MATRIX.json` | game-teardown |
| 数值模型(可选) | `docs/NUMERIC_MODEL.csv` | game-teardown |
| 拆解门报告(可选) | `docs/GATE_0_5_REPORT.md` | game-quality-gate(仅复刻专线) |
| 蓝图 | `docs/GAME_BLUEPRINT.md` | game-blueprint |
| PRD | `docs/PRD.md` | game-spec |
| 技术设计 | `docs/TECH_DESIGN.md` | game-spec |
| 美术规范 | `docs/ART_SPEC.md` | game-art-spec |
| 资源清单 | `docs/ASSET_MANIFEST.json` | game-art-spec |
| 资源清单(上一版备份) | `docs/ASSET_MANIFEST.prev.json` | game-asset-forge(增量更新时产出) |
| 音频规范 | `docs/AUDIO_SPEC.md` | game-art-spec |
| 关卡设计说明 | `docs/LEVEL_PLAN.md` | game-level-design |
| 关卡作者手册 | `docs/LEVEL_AUTHORING.md` | game-level-design(人读;改关说明书,单局制可裁剪) |
| 关卡配置(运行期) | `config/levels.json` | game-level-design |
| 关卡配置副本(构建期派生) | Web:`public/config/levels.json`(或同级 import 根文件);Godot:`res://config/levels.json`;Unity:`Assets/StreamingAssets/config/levels.json` | game-code-forge(复制,内容与源一致,不手改) |
| 难度评审报告 | `docs/DIFFICULTY_REPORT.md` | game-level-design |
| 难度评审判定(机读) | `docs/DIFFICULTY_REVIEW.json` | game-level-design |
| 关卡门报告 | `docs/GATE_2_5_REPORT.md` | game-quality-gate |
| 角色帧 | `assets/role/{role}/{state}_{frame:03}.png` | game-asset-forge |
| UI 图 | `assets/ui/{page}/{element}.png` | game-asset-forge |
| 背景 | `assets/bg/{scene}_{variant}.png` | game-asset-forge |
| 图集 | `assets/atlases/{atlas_id}.png` + `.json` | game-asset-forge |
| 音频 | `assets/audio/{type}_{name}.{ext}` | game-asset-forge |
| 代码 | `src/**/*.ts`、`index.html`、`package.json` | game-code-forge |
| Godot 场景 | `scenes/**/*.tscn` | game-code-forge |
| Godot 脚本 | `scripts/**/*.gd` | game-code-forge |
| Godot 工程 | `project.godot`、`export_presets.cfg` | game-code-forge |
| Godot 导出产物 | `export/*.{exe,pck,html,zip}` | game-integrate |
| Unity 脚本 | `Assets/Scripts/Runtime/**/*.cs` | game-code-forge |
| Unity Editor 脚本 | `Assets/Scripts/Editor/**/*.cs` | game-code-forge |
| Unity 场景 | `Assets/Scenes/*.unity` | game-code-forge(由 SceneBuilder 生成) |
| Unity 工程配置 | `ProjectSettings/ProjectVersion.txt`、`Packages/manifest.json`、`*.asmdef` | game-code-forge |
| Unity 导出产物 | `Build/*.{exe,html}` | game-integrate |
| 构建产物 | `dist/**` | game-integrate |
| 验收报告 | `docs/BUILD_REPORT.md` | game-integrate |
| 截图与基线 | `docs/screenshots/*.png` + `docs/screenshots/baseline/manifest.json` | game-integrate(基线随内容版本一起提交,差异解释写进验收报告) |
| 质量门报告 | `docs/GATE_{0,1,2,3}_REPORT.md` | game-quality-gate |
| 效果优化需求(可选) | `docs/POLISH_REQUEST.md` | 用户填写 |
| 效果代码(可选) | `src/effects/*.ts` | game-polish |
| 效果优化报告(可选) | `docs/POLISH_REPORT.md` | game-polish |
| 已知问题 | `docs/ASSET_ISSUES.md` | 任意(失败时写) |
| workflow.yaml(可选) | `workflow.yaml` | workflow-runtime(编译本总纲 §七 执行顺序生成) |

---

### 8.1 阶段新增检查清单(新增/重排阶段时必做)

往流水线里加一个阶段(或调整阶段顺序),以下 7 项**逐项确认**,漏任一项都会产生单边契约:

| # | 检查项 | 落点 | 漏掉的后果 |
|---|---|---|---|
| ① | 流程图与执行顺序 | 本文 §二 总览图 + §七 步骤 | 执行者按旧图跑,顺序错 |
| ② | 阶段性质与裁剪规则 | 本文 §四 裁剪表 | 该走的不走 / 该剪的硬跑 |
| ③ | 产物路径登记 | 本文 §八 路径总表 | 下游按猜的路径读,404 |
| ④ | 门禁检查项 | `game-quality-gate` 新增/改 Gate + `runtime.yaml` outputs | 产物没人校验,质量靠自觉 |
| ④b | **判据覆盖面** | **若本阶段引入"多种合法形态"(多路径/多引擎/多格式),门禁判据必须逐形态覆盖,并给白名单** | **判据只认一种形态 → 合规实现被误杀(改完 A 侧没改 B 侧的典型)** |
| ⑤ | **下游消费登记** | **逐个改下游 skill 的"输入/上游契约"节** | **上游写了契约、下游不知道 → 单边契约(最常见的漏项)** |
| ⑥ | references 索引 | 本文 §五 + 新 skill 的 §文件索引 | 模板/规范找不到 |
| ⑦ | 示例产物与自检 | 新 skill 的 `examples/` + selftest | 工具坏了没人知道 |

**⑤ 的具体做法**:列出新阶段的全部产物,对每个产物问"谁读它";对每个读者,去它的 SKILL.md 里加一节说明**怎么读**(用哪个字段、放哪个目录、走什么加载方式)。只在自己的文档里写"下游会用 X"不算数——下游没写就等于没有。

> 反向核对:`grep -rn "<新产物文件名>" */SKILL.md`,命中数应 ≥ 2(产出方 + 至少一个消费方)。

---

## 九、用户交互约定

- 默认全程中文输出
- 每阶段完成后向用户简报产物路径与下一步
- 遇到选择(如引擎、裁剪)用 AskUserQuestion 确认,不擅自决定
- 全流程不依赖任何可视化编辑器,所有产物纯文本/二进制资源

### 9.1 人工确认机制(强制,见 §七 确认点 0.5 与 1~6)

每个阶段(阶段 1~5)完成且对应质量门 PASS 后,**必须暂停流水线**,用 AskUserQuestion 向用户确认下一步。**不允许自动连续执行下一阶段**,即使用户在启动时说过"全流程跑完"或类似话术。

**确认点标准动作**:

1. **简报**:用 2-3 句话汇报本阶段产物路径 + 关键指标(如资源数/代码行数/构建产物大小)
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
- 阶段 0.5(复刻拆解)有独立确认点 0.5:拆解质量直接决定后续"像不像",必须让用户看档位、证据覆盖与 MVP 范围后再进蓝图
- 阶段 6(polish)是可选增量,由确认点 5 的用户选择决定是否进入,进入后不再设确认点(直接执行到底)
- 质量门 FAIL 时无需确认,直接回退修复(修复后重跑 Gate,Gate PASS 再走确认点)
- 确认点 6（可选 Tool）是**可选**的：即使用户在确认点 5 选了"流水线完成",也可在产物已落地后单独触发 Tool 操作;反之,确认点 6 默认不强制出现,仅在用户明确要"提交/部署"时触发

**workflow-runtime 兼容**:在 workflow-runtime 模式下,本文的人工确认点(确认点 1~6)对应 workflow.yaml 中的 pause 节点,pause 节点自动触发 AskUserQuestion,选项与本文一致("进入下一阶段"/"回退修改"/"终止流水线")。可选 Tool 确认点(确认点 6)对应 workflow.yaml 中 optional=true 的 pause 节点。详见 `../workflow-runtime/references/execution-semantics.md`。
