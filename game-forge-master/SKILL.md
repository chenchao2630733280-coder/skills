---
name: "game-forge-master"
description: "AI 生成游戏的通用编排总纲。包含引擎选择决策树、阶段裁剪规则、模板索引与失败回退策略。当用户要'用 AI 生成/制作一个游戏'、'端到端生成游戏工程'、'按流水线生成游戏'时调用。"
---

# Game Forge Master — AI 游戏生成总纲

本 skill 是整套"AI 生成游戏"流水线的**调度中枢**,本身不直接产出游戏文件,职责是:
1. 接收用户一句话需求,决定走哪条生成路径
2. 选择目标引擎(Phaser / Pixi / 纯 Canvas)
3. 裁剪阶段(简单游戏可跳过音频/网络/任务系统)
4. 串联下游 5 个阶段 skill 的执行顺序
5. 提供通用模板索引与失败回退策略

---

## 一、何时调用

满足以下任一条件即调用本 skill:
- 用户说"用 AI 生成/做一个游戏"
- 用户说"按流水线生成游戏工程"
- 用户给了游戏雏形需求,需要端到端产出可运行工程
- 用户调用了任意 `game-*` 系列 skill 但未先经过总纲

**不要**在以下场景调用:
- 用户只是问"游戏怎么做"(纯咨询,用对话回答即可)
- 用户要修改已有游戏的某一处代码(直接用 Edit/Write)
- 用户要做的是 3D 游戏(本方案只覆盖 2D)

---

## 二、流水线总览

```
用户一句话需求
       ↓
[本 skill] 引擎选择 + 阶段裁剪
       ↓
game-blueprint    → docs/GAME_BLUEPRINT.md
       ↓
game-spec         → docs/PRD.md + docs/TECH_DESIGN.md
       ↓
game-art-spec     → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json + docs/AUDIO_SPEC.md
       ↓
┌──────────────────┐  ┌──────────────────┐
│ game-asset-forge │  │ game-code-forge  │  (可并行)
│  生成 assets/    │  │  生成 src/       │
└──────────────────┘  └──────────────────┘
       ↓
game-integrate    → dist/ + 验收报告
       ↓
game-polish (可选) → 视觉/手感/反馈打磨 + docs/POLISH_REPORT.md
```

**阶段性质**:
- 阶段 1-5(蓝图→规格→美术→资源/代码→集成):**必走**,产出可玩游戏
- 阶段 6(game-polish):**可选**,在可玩游戏基础上叠加效果,不改玩法

**关键约束**:每阶段产物的路径与文件名固定,下游 skill 必须按固定路径读取上游产物,不允许自定义路径。

---

## 三、引擎选择决策树

根据游戏类型与复杂度自动选择引擎:

```
用户需求
   ├─ 2D 跑酷/平台/塔防/卡牌/消除 → 默认 Phaser 3
   ├─ 大量粒子/特效/自定义渲染 → Pixi.js
   ├─ 极简(纯文字/几何图形) → 纯 Canvas
   ├─ 3D 游戏 → 不支持,告知用户超范围
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

### 决策结果写入

引擎选择结果写入 `docs/GAME_BLUEPRINT.md` 的"3. 平台与引擎"章节,格式:
```
平台:Web H5
引擎:Phaser 3.80.x
依赖:phaser、axios(如需网络)
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

所有下游 skill 都引用一套**通用模板工程**,作为生成产物的基准骨架。模板路径随 skill 集合分发:

```
.trae/skills/game-template/   (随 skill 分发的模板参考)
├── phaser/                    # Phaser 默认模板
├── pixi/                      # Pixi 模板
├── canvas/                    # 纯 Canvas 模板
└── shared/                    # 三引擎共享文档模板
    ├── GAME_BLUEPRINT.md.tpl
    ├── PRD.md.tpl
    ├── TECH_DESIGN.md.tpl
    ├── ART_SPEC.md.tpl
    ├── ASSET_MANIFEST.schema.json
    └── AUDIO_SPEC.md.tpl
```

下游 skill 调用模板时,**先按引擎选目录,再按阶段选文件**。

---

## 六、失败回退策略

下游 skill 执行失败时的统一处理:

| 失败场景 | 回退策略 |
|---|---|
| AI 生图失败 | 占位图(纯色 + 文字标识) + 标记到 `docs/ASSET_ISSUES.md` |
| 切图/图集打包失败 | 降级用散图(性能略差但能跑) |
| 音频生成失败 | 1 秒静音 wav 占位 + 标记 |
| 代码 typecheck 失败 | AI 自动修复 3 轮,仍失败则降级 strict:false + 标记 |
| 浏览器自测失败 | 输出失败清单 + 截图,不阻塞构建 |
| 资源加载 404 | 自动用占位图替代 + 标记 |

**所有失败都允许继续往下走**,失败项汇总到 `docs/BUILD_REPORT.md` 的"已知问题"章节,供人工后补。

---

## 七、执行顺序(必须严格遵循)

调用本 skill 后,必须按以下顺序执行下游 skill:

1. 调用 `game-blueprint`,产出 `docs/GAME_BLUEPRINT.md`
2. 调用 `game-spec`,读取蓝图,产出 `docs/PRD.md` + `docs/TECH_DESIGN.md`
3. 调用 `game-art-spec`,读取 PRD + TECH_DESIGN,产出 `docs/ART_SPEC.md` + `docs/ASSET_MANIFEST.json` + `docs/AUDIO_SPEC.md`
4. **并行**调用 `game-asset-forge` 和 `game-code-forge`,分别产出 `assets/` 和 `src/`
5. 调用 `game-integrate`,读取 assets + src,产出 `dist/` + `docs/BUILD_REPORT.md`
6. (可选)若阶段 6 未被裁剪,调用 `game-polish`,读取可运行工程 + `docs/POLISH_REQUEST.md`(如有),产出 `src/effects/` 增量 + `docs/POLISH_REPORT.md`

**不允许跳步**:即使某阶段被裁剪,也必须产出对应的占位文档(如音频裁剪也要写一个最小 AUDIO_SPEC.md 标注"全部静音占位")。
**阶段 6 例外**:game-polish 被裁剪时**不产出占位文档**(它是可选增量,无占位概念)。

---

## 八、产物路径总表

所有 skill 必须遵守的固定路径:

| 产物 | 路径 | 由哪个 skill 产出 |
|---|---|---|
| 蓝图 | `docs/GAME_BLUEPRINT.md` | game-blueprint |
| PRD | `docs/PRD.md` | game-spec |
| 技术设计 | `docs/TECH_DESIGN.md` | game-spec |
| 美术规范 | `docs/ART_SPEC.md` | game-art-spec |
| 资源清单 | `docs/ASSET_MANIFEST.json` | game-art-spec |
| 音频规范 | `docs/AUDIO_SPEC.md` | game-art-spec |
| 角色帧 | `assets/role/{role}/{state}_{frame:03}.png` | game-asset-forge |
| UI 图 | `assets/ui/{page}/{element}.png` | game-asset-forge |
| 背景 | `assets/bg/{scene}_{variant}.png` | game-asset-forge |
| 图集 | `assets/atlases/{atlas_id}.png` + `.json` | game-asset-forge |
| 音频 | `assets/audio/{type}_{name}.{ext}` | game-asset-forge |
| 代码 | `src/**/*.ts`、`index.html`、`package.json` | game-code-forge |
| 构建产物 | `dist/**` | game-integrate |
| 验收报告 | `docs/BUILD_REPORT.md` | game-integrate |
| 效果优化需求(可选) | `docs/POLISH_REQUEST.md` | 用户填写 |
| 效果代码(可选) | `src/effects/*.ts` | game-polish |
| 效果优化报告(可选) | `docs/POLISH_REPORT.md` | game-polish |
| 已知问题 | `docs/ASSET_ISSUES.md` | 任意(失败时写) |

---

## 九、用户交互约定

- 默认全程中文输出
- 每阶段完成后向用户简报产物路径与下一步
- 遇到选择(如引擎、裁剪)用 AskUserQuestion 确认,不擅自决定
- 全流程不依赖任何可视化编辑器,所有产物纯文本/二进制资源
