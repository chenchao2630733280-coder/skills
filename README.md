# AI 游戏生成 Skill 集合

> 通过 8 个 skill 串联成一条流水线,让 AI 基于一句话需求端到端生成可一键运行的游戏工程。所有产物纯文本/二进制资源,**零编辑器依赖**。可选阶段 6 在可玩游戏基础上叠加视觉效果打磨。

---

## 一、Skill 清单

| 序号 | Skill 名 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| 0 | game-forge-master | 总纲/调度/引擎决策树/失败回退 | 用户一句话需求 | 调度下游 skill |
| 1 | game-blueprint | 游戏蓝图(类型/平台/引擎/范围) | 一句话需求 | `docs/GAME_BLUEPRINT.md` |
| 2 | game-spec | PRD + 技术设计 | 蓝图 | `docs/PRD.md` + `docs/TECH_DESIGN.md` |
| 3 | game-art-spec | 美术规范 + 资源清单 + 音频规范 | PRD + TECH_DESIGN | `docs/ART_SPEC.md` + `docs/ASSET_MANIFEST.json` + `docs/AUDIO_SPEC.md` |
| 4a | game-asset-forge | AI 生图 + 切图 + 音频占位 | ASSET_MANIFEST + ART_SPEC | `assets/**` |
| 4b | game-code-forge | 工程代码(三引擎) | PRD + TECH_DESIGN + ASSET_MANIFEST | `src/**` + 工程配置 |
| 5 | game-integrate | 集成构建联调 + 验收报告 | assets + src | `dist/**` + `docs/BUILD_REPORT.md` |
| 6 | game-polish(可选) | 视觉/手感/反馈效果打磨 | 可运行工程 + POLISH_REQUEST(可选) | `src/effects/**` + `docs/POLISH_REPORT.md` |

---

## 二、流水线总览

```
用户一句话需求
       ↓
[0] game-forge-master(调度)
       ↓ 引擎选择 + 阶段裁剪
[1] game-blueprint       → docs/GAME_BLUEPRINT.md
       ↓
[2] game-spec            → docs/PRD.md + docs/TECH_DESIGN.md
       ↓
[3] game-art-spec        → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json + docs/AUDIO_SPEC.md
       ↓
┌────────────────────┐  ┌────────────────────┐
│ [4a] game-asset-   │  │ [4b] game-code-    │  (可并行)
│      forge         │  │      forge         │
│  assets/**         │  │  src/**            │
└────────────────────┘  └────────────────────┘
       ↓
[5] game-integrate       → dist/** + docs/BUILD_REPORT.md
       ↓
[6] game-polish (可选)   → src/effects/** + docs/POLISH_REPORT.md
```

---

## 三、使用方式

### 方式 1:完整流程(推荐)
直接说"用 AI 生成一个游戏:..." 或 "按流水线生成游戏工程"。总纲 skill 会自动调度后续阶段。

### 方式 2:单阶段调用
跳过总纲,直接调用某个阶段 skill(适用于已有部分产物的增量生成):
- "生成游戏蓝图" → 调用 game-blueprint
- "生成游戏 PRD" → 调用 game-spec
- "生成美术规范" → 调用 game-art-spec
- "生成游戏资源" → 调用 game-asset-forge
- "生成游戏代码" → 调用 game-code-forge
- "集成构建游戏" → 调用 game-integrate
- "优化游戏效果/加特效/打磨动画" → 调用 game-polish

---

## 四、关键设计点

### 1. ASSET_MANIFEST.json 是中枢契约
美术 skill 与代码 skill 的唯一桥梁。代码 skill 只读 JSON,不读美术文档;美术 skill 只产出 JSON。两阶段完全解耦。

### 2. 三引擎支持
默认 Phaser 3,总纲根据游戏类型自动选择:
- Phaser 3:2D 跑酷/平台/塔防/卡牌/消除(默认)
- Pixi.js:大量粒子/特效/自定义渲染
- 纯 Canvas:极简游戏(2048/几何)

### 3. 失败不阻塞
所有失败都允许继续,降级方案:
- 生图失败 → 占位图(纯色 + 文字标识)
- 切图失败 → 散图降级
- 音频失败 → 静音占位
- typecheck 失败 → 降级 strict:false

失败项汇总到 `docs/ASSET_ISSUES.md` 和 `docs/BUILD_REPORT.md`,供人工后补。

### 4. 固定路径契约
所有 skill 必须按固定路径读写,不允许自定义。详见 game-forge-master 的"八、产物路径总表"。

---

## 五、产物路径总表

```
{项目根}/
├── docs/
│   ├── GAME_BLUEPRINT.md       # [1] 产出
│   ├── PRD.md                  # [2] 产出
│   ├── TECH_DESIGN.md          # [2] 产出
│   ├── ART_SPEC.md             # [3] 产出
│   ├── ASSET_MANIFEST.json     # [3] 产出(中枢)
│   ├── AUDIO_SPEC.md           # [3] 产出
│   ├── ASSET_ISSUES.md         # [4a] 失败时产出
│   ├── BUILD_REPORT.md         # [5] 产出
│   ├── POLISH_REQUEST.md       # [6] 用户填写(可选)
│   ├── POLISH_REPORT.md        # [6] 产出(可选)
│   └── screenshots/            # [5] 浏览器自测截图
├── assets/
│   ├── role/{role}/{state}_{frame:03}.png   # [4a]
│   ├── ui/{page}/{element}.png              # [4a]
│   ├── bg/{scene}_{variant}.png             # [4a]
│   ├── atlases/{atlas_id}.png + .json       # [4a]
│   └── audio/*.{wav,mp3}                     # [4a]
├── src/                        # [4b]
│   ├── main.ts
│   ├── config/
│   ├── scenes/
│   ├── objects/
│   ├── managers/
│   ├── ui/
│   ├── effects/                # [6] game-polish 增量产出(可选)
│   ├── net/  (可选)
│   ├── utils/
│   └── types/
├── dist/                       # [5] 构建产物
├── index.html                  # [4b]
├── package.json                # [4b]
├── tsconfig.json               # [4b]
├── vite.config.ts              # [4b]
└── README.md                   # [4b]
```

---

## 六、典型场景示例

### 场景 1:新春赛马跑酷游戏
```
用户:用 AI 生成一个新春赛马跑酷小游戏,带 6 套皮肤和抽奖
[0] 总纲:复杂度 ★★★★,引擎 Phaser 3,音频走静音占位
[1] 蓝图:跑酷+皮肤+抽奖,Web H5,Phaser 3
[2] PRD:跳跃/障碍/计分/复活/抽奖状态机;TECH_DESIGN:6 场景+15 模块
[3] 美术:6 皮肤×16 帧=96 图 + UI + 背景,共 ~150 张;音频 6 个静音占位
[4a] 资源:AI 生图(首帧 reference)+ TexturePacker 打包 6 个图集
[4b] 代码:BootScene/HomeScene/GameScene + Horse/Obstacle/Popup
[5] 集成:npm install → typecheck → 浏览器自测 → build → dist/
```

### 场景 2:极简消除游戏
```
用户:做个三消游戏
[0] 总纲:复杂度 ★★,引擎 Phaser 3,跳过 audio
[1] 蓝图:网格消除,无网络,无皮肤
[2] PRD:8x8 网格,3 消除规则;TECH_DESIGN:单场景
[3] 美术:6 种宝石图 + 背景 + UI,共 ~20 张
[4a] 资源:AI 生图(快速)
[4b] 代码:BootScene + GameScene
[5] 集成:构建完成
```

---

## 七、约束与限制

### 1. 不支持的类型
- 3D 游戏(本方案只覆盖 2D)
- 强物理引擎游戏(如真实刚体碰撞,虽可加 Matter.js 但 AI 生成质量不稳)
- MMORPG 等大型多人游戏

### 2. AI 生图限制
- 逐帧动画跨帧风格一致性是主要难点,有降级路径但建议人工 review
- 复杂场景(多角色同框 + 复杂光影)成功率低
- 单游戏美术资源上限 200 张图,超出建议拆期

### 3. AI 音频限制
- 默认全部静音占位,需人工后补
- AI 生成音频质量不稳定,BGM 不建议 AI 生成

### 4. 网络与签名
- 网络层需用户提供接口契约(URL/参数/返回)
- 复杂签名(如双重 md5 + SM4)需用户给参考实现
- 私有 SDK(如 SZDApi)需用户提供 .d.ts 类型定义

---

## 八、各 Skill 详细规范

详见各 skill 目录下的 SKILL.md:
- [game-forge-master](./game-forge-master/SKILL.md)
- [game-blueprint](./game-blueprint/SKILL.md)
- [game-spec](./game-spec/SKILL.md)
- [game-art-spec](./game-art-spec/SKILL.md)
- [game-asset-forge](./game-asset-forge/SKILL.md)
- [game-code-forge](./game-code-forge/SKILL.md)
- [game-integrate](./game-integrate/SKILL.md)
- [game-polish](./game-polish/SKILL.md)
