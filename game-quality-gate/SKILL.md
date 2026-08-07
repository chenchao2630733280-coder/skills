---
name: "game-quality-gate"
description: "AI 游戏生成流水线的跨阶段质量门。在 4 个关键节点(规格后/美术后/资源代码后/集成前)介入做契约校验与实跑预检,不通过则阻断流水线并给出修复建议。当被 game-forge-master 调度到检查点,或用户要'校验/门禁/质量检查/实跑验证游戏产物'时调用。"
---

# 游戏流水线质量门

## 一、定位与职责

本 skill 是 AI 游戏生成流水线的**跨阶段质检员**,解决"各 skill 自检宽松 + 实跑验证只在最后 + 错误累积到集成阶段才爆发"的结构性风险。

**核心机制**:三层门禁 × 四个检查点。

| 层 | 名称 | 职责 | 不通过行为 |
|---|---|---|---|
| L1 | 静态门(Static) | 字段完整性 / 格式 / 命名 / 路径 | **阻断**,返回修复建议,不允许进入下一阶段 |
| L2 | 契约门(Contract) | 跨阶段一致性(PRD 节点树 vs 代码、manifest vs 实际文件) | **阻断**,返回差异清单 + 修复建议 |
| L3 | 实跑门(Runtime) | typecheck / 构建预检 / 浏览器启动自测 | **阻断**,返回错误日志供 game-code-forge 修复(本 skill 不修复) |

**与现有"质量检查清单"的区别**:
- 现有清单是各 skill 的**自我声明**,标准宽松,无阻断权
- 本 skill 是**独立第三方校验**,有阻断权,标准统一

**只读原则**:本 skill 不修改任何产物文件,只读 + 校验 + 输出报告。FAIL 即返回失败清单与修复建议,**修复由原产出 skill 重跑完成**,本 skill 不接管修复职责(避免职责越界与"自审自修"的伦理风险)。

**质量门范围**:本 skill 只管 **Gate 0~3**(规格/美术/资源代码/集成前)。**Gate 4 实跑门**(typecheck+构建+浏览器自测+数值平衡)是 game-integrate 的内置最终验收,不属于本 skill 阻断体系,本 skill 仅在 §七引用其 `docs/BUILD_REPORT.md` 作为最终判定参考。

---

## 二、四个检查点

```
game-blueprint
    ↓
[Gate 0] 蓝图门 ──────────────────────────── L1 静态
    ↓
game-spec
    ↓
[Gate 1] 规格门 ──────────────────────────── L1 + L2(PRD ↔ TECH_DESIGN)
    ↓
game-art-spec
    ↓
[Gate 2] 美术门 ──────────────────────────── L1 + L2(manifest ↔ PRD 节点树)
    ↓
┌──────────────────┐  ┌──────────────────┐
│ game-asset-forge │  │ game-code-forge  │  (并行)
└──────────────────┘  └──────────────────┘
    ↓
[Gate 3] 产物门 ──────────────────────────── L1 + L2 + L3 预检
    ↓
game-integrate (内含 Gate 4 实跑门,由其自检)
    ↓
game-polish (可选)
```

| 检查点 | 时机 | 层 | 检查内容 | 输出 |
|---|---|---|---|---|
| Gate 0 蓝图门 | game-blueprint 后 | L1 | 蓝图字段完整性 / 引擎选择合理性 / 范围可行 | `docs/GATE_0_REPORT.md` |
| Gate 1 规格门 | game-spec 后 | L1+L2 | PRD 节点树完整性 + TECH_DESIGN 与 PRD 引擎/目录一致 | `docs/GATE_1_REPORT.md` |
| Gate 2 美术门 | game-art-spec 后 | L1+L2 | manifest 字段 + manifest 的 UI asset 与 PRD 节点树 1:1 对齐 | `docs/GATE_2_REPORT.md` |
| Gate 3 产物门 | game-asset-forge + game-code-forge 后 | L1+L2+L3 | manifest ↔ 实际文件 + 代码 UI 节点 ↔ PRD 节点树 + typecheck 预检 | `docs/GATE_3_REPORT.md` |

**Gate 4 实跑门**已由 game-integrate 内置(typecheck + 构建 + 浏览器自测 + 数值平衡),本 skill 不重复,只引用其 `docs/BUILD_REPORT.md` 作为最终判定依据。

---

## 三、Gate 0 蓝图门

### 3.1 输入
- `docs/GAME_BLUEPRINT.md`

### 3.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 0.1 | 必填字段 | 类型/平台/引擎/玩法/范围/复杂度 6 项齐全 | `G0-MISSING-FIELD` |
| 0.2 | 引擎枚举 | 值 ∈ {Phaser 3, Pixi.js, 纯 Canvas, Godot 4, Unity} | `G0-INVALID-ENGINE` |
| 0.3 | 引擎-类型匹配 | 3D 类型 → Godot 4 / Unity;2D → 任意 | `G0-ENGINE-TYPE-MISMATCH` |
| 0.4 | 范围可行 | 核心机制 ≤ 8 项 | `G0-SCOPE-OVER` |
| 0.5 | 一句话定义 | ≤ 30 字 | `G0-DEFINITION-TOO-LONG` |
| 0.6 | 玩家动机 | 蓝图 §4.5 三行(自主/胜任/关联)齐全且主导动机已选 | `G0-MOTIVATION-MISSING` |

### 3.3 输出格式

```markdown
# Gate 0 蓝图门报告

- 检查时间:{ISO8601}
- 结论:{PASS | FAIL}
- 失败数:{N}(ERROR:{N1} / WARNING:{N2})
- 阻断规则:ERROR > 0 则 FAIL;WARNING 仅标记到报告,不阻断

## 失败清单
| # | 检查项 | 失败码 | 严重度 | 详情 | 修复建议 |
|---|---|---|---|---|---|

## 警告清单(WARNING,不阻断)
| # | 检查项 | 失败码 | 详情 | 建议处理 |
|---|---|---|---|---|

## 通过项摘要
{N} 项通过
```

---

## 四、Gate 1 规格门

### 4.1 输入
- `docs/GAME_BLUEPRINT.md`
- `docs/PRD.md`
- `docs/TECH_DESIGN.md`

### 4.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 1.1 | PRD 章节完整 | 玩法/数值/UI/关卡/状态机/系统清单/MDA/心流 8 章齐全 | `G1-PRD-SECTION-MISSING` |
| 1.2 | TECH_DESIGN 章节完整 | 引擎/目录/类设计/接口契约 4 章齐全 | `G1-TECH-SECTION-MISSING` |
| 1.3 | PRD UI 节点树 | 每个 UI 页面有节点树 | `G1-UI-TREE-MISSING` |
| 1.4 | TECH_DESIGN 引擎 | 与蓝图引擎一致 | `G1-ENGINE-MISMATCH` |

### 4.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 1.5 | PRD ↔ BLUEPRINT 类型 | PRD 的主类型与蓝图一致 | `G1-PRD-BLUEPRINT-TYPE-MISMATCH` |
| 1.6 | PRD ↔ TECH_DESIGN 引擎 | TECH_DESIGN 的引擎字段 = 蓝图引擎 | `G1-PRD-TECH-ENGINE-MISMATCH` |
| 1.7 | PRD ↔ TECH_DESIGN 目录 | TECH_DESIGN 目录结构与 PRD 引擎适配章节一致 | `G1-DIR-MISMATCH` |
| 1.8 | PRD UI 节点树命名 | 节点 id 命名规范(`page_element` 格式) | `G1-NODE-NAMING` |
| 1.9 | PRD MDA 框架 | PRD §1.0 三行(Mechanics/Dynamics/Aesthetics)齐全且因果链声明存在 | `G1-MDA-MISSING` |
| 1.10 | PRD 心流平衡 | PRD §2.4 心流区间定义 + 难度-技能对照表齐全且与蓝图主导动机一致(胜任主导→窄带,自主/关联主导→宽带) | `G1-FLOW-MISMATCH` |
| 1.11 | PRD 系统清单 | PRD §5 每个核心系统有输入/边界/依赖三字段 | `G1-SYSTEM-FIELD-MISSING` |
| 1.12 | PRD 数值表 ↔ TECH_DESIGN 数据结构 | PRD 中每个数值条目在 TECH_DESIGN 有对应 interface/字段 | `G1-NUMBER-STRUCT-MISMATCH` |
| 1.13 | PRD 关卡清单 ↔ TECH_DESIGN 关卡配置 | PRD 关卡数量与 TECH_DESIGN 关卡配置类支持数量一致 | `G1-LEVEL-CONFIG-MISMATCH` |
| 1.14 | PRD 状态机 ↔ TECH_DESIGN 类设计 | PRD 每个状态在 TECH_DESIGN 有对应状态字段/枚举/方法 | `G1-STATE-MACHINE-MISMATCH` |
| 1.15 | PRD 实体清单 ↔ TECH_DESIGN 类清单 | PRD 中定义的实体(角色/敌人/道具)在 TECH_DESIGN 有对应类 | `G1-ENTITY-CLASS-MISMATCH` |
| 1.16 | PRD 系统边界 ↔ TECH_DESIGN 类边界 | PRD §5"边界"列的"不做"项在 TECH_DESIGN 类设计中无对应实现(防越界) | `G1-SYSTEM-BOUNDARY-VIOLATED` |

> **核心价值**:1.9~1.16 把原本要拖到 Gate 4 数值平衡实测才暴露的"数值/关卡/状态机/系统边界不一致"提前到规格阶段。MDA 保证"机制-体验"因果链显式;心流保证"物理可玩≠心理好玩";系统边界防止范围蔓延到代码层。

---

## 五、Gate 2 美术门

### 5.1 输入
- `docs/PRD.md`(读 UI 节点树)
- `docs/ASSET_MANIFEST.json`
- `docs/ART_SPEC.md`
- `docs/AUDIO_SPEC.md`

### 5.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 2.1 | manifest 必填字段 | id/category/type/path/size/format/prompt/contentHash 8 项齐全 | `G2-MANIFEST-FIELD-MISSING` |
| 2.2 | contentHash 合法 | 每个 asset 有非空 contentHash | `G2-CONTENTHASH-MISSING` |
| 2.3 | predecessorId 规则 | id 首次出现时为 null,改名时填旧 id | `G2-PREDECESSOR-INVALID` |
| 2.4 | path 命名 | 与 game-forge-master §八路径表一致 | `G2-PATH-NAMING` |

> 风格基线声明检查移至 §5.3 的 2.14(条件检查,未命中基线时跳过)。

### 5.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| 2.6 | manifest UI asset ↔ PRD 节点树 | manifest 中 category=ui 的 asset 与 PRD 每个 UI 节点对齐(1:1 或改名见 §5.4) | `G2-UI-NODE-MISMATCH` |
| 2.7 | manifest 无幽灵 UI asset | manifest 的 UI asset 都能在 PRD 节点树找到对应节点(含 predecessorId 追溯,见 §5.4) | `G2-UI-ORPHAN-ASSET` |
| 2.8 | manifest 无遗漏 UI 节点 | PRD 节点树的每个 UI 节点都有对应 manifest asset(含被 predecessorId 指向的旧节点) | `G2-UI-NODE-MISSING-ASSET` |
| 2.9 | 风格基线 prompt 引用 | 命中基线时,asset prompt 以 `[GAME ASSET]` 等标签开头 | `G2-PROMPT-NO-TAG` |
| 2.10 | manifest role asset ↔ PRD 实体清单 | manifest 中 category=role 的 asset 与 PRD 定义的角色/敌人实体对齐 | `G2-ROLE-ENTITY-MISMATCH` |
| 2.11 | manifest bg asset ↔ PRD 场景清单 | manifest 中 category=bg 的 asset 与 PRD 定义的背景/场景对齐 | `G2-BG-SCENE-MISMATCH` |
| 2.12 | manifest effect asset ↔ PRD 特效清单 | manifest 中 category=effect 的 asset 与 PRD 定义的特效事件对齐 | `G2-EFFECT-MISMATCH` |
| 2.13 | manifest audio asset ↔ AUDIO_SPEC 事件映射表 | manifest 中 category=audio 的 asset 与 AUDIO_SPEC §2.5 SFX 事件映射表对齐(每个事件 ID 有对应 audio asset,每个 asset 被至少一个事件引用) | `G2-AUDIO-EVENT-MISMATCH` |
| 2.14 | ART_SPEC 风格基线声明(条件) | **仅当 PRD/TECH_DESIGN 命中已收录风格基线时检查** ART_SPEC 顶部有声明;未命中基线时跳过 | `G2-BASELINE-DECLARATION-MISSING` |

> **核心价值**:Gate 2 是防止"布局调整后 manifest 与 PRD 脱节"的关键。若 PRD 节点树新增按钮但 manifest 没对应 asset,会在本门暴露,不会等到 game-integrate 才发现"代码引用了不存在的资源"。2.10~2.13 把校验范围从单一 UI 类扩展到全 5 类 asset(role/bg/effect/audio),覆盖所有跨阶段契约。

### 5.4 增量更新场景下的 1:1 校验规则

当 manifest 含 `predecessorId`(布局调整导致 asset 改名)时,2.6/2.7/2.8 的"1:1 对齐"按以下规则放宽,避免把改名 asset 误判为幽灵:

```
对于 manifest 中每条 asset A:
  若 A.predecessorId == null:
    → A.id 必须在 PRD 节点树找到对应节点(原 1:1 规则)
  若 A.predecessorId != null:
    → A.id 找不到对应节点是允许的(改名后新 id)
    → 但 A.predecessorId 必须能在上一版 manifest + PRD 节点树找到来源
    → 且 A.id 应能在 PRD 节点树找到"改名后的新节点"(通过节点 id 与 A.id 一致)

对于 PRD 节点树中每个节点 N:
  → N.id 在 manifest 找到对应 asset(直接命中,或被某 asset 的 predecessorId 指向)
  → 若两者都不命中,才是 G2-UI-NODE-MISSING-ASSET
```

**字段约束**:
- 本 skill 校验时,若 manifest 含 predecessorId,需同时读取上一版 manifest(命名为 `ASSET_MANIFEST.prev.json`,由 game-asset-forge 在增量 diff 时备份)做追溯
- 若 `ASSET_MANIFEST.prev.json` 不存在(首次生成或未做增量),predecessorId 字段应为 null,走原 1:1 规则

---

## 六、Gate 3 产物门

### 6.1 输入
- `docs/ASSET_MANIFEST.json`
- `docs/PRD.md`(UI 节点树 + 实体/场景/特效/音频事件清单)
- `docs/ASSET_ISSUES.md`(如有,识别降级为占位图的 asset)
- `docs/ASSET_MANIFEST.prev.json`(如有,用于 predecessorId 追溯)
- `assets/` 目录
- `src/` 目录(Web 引擎)或 Godot/Unity 工程

### 6.2 L1 静态检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.1 | manifest asset 文件存在 | manifest 每个 asset 的 path/actualPath 对应文件存在 | `G3-FILE-MISSING` | ERROR |
| 3.2 | manifest actual* 回写 | game-asset-forge 已回写 actualFormat/actualPath | `G3-ACTUAL-NOT-WRITTEN` | ERROR |
| 3.3 | 无幽灵文件 | assets/ 下文件都能在 manifest 找到对应 id | `G3-ORPHAN-FILE` | WARNING(允许 .DS_Store/.gitkeep 等系统文件) |
| 3.4 | 工程入口存在 | Web:index.html;Godot:project.godot + Main.tscn;Unity:Assets/Scenes/Main.unity | `G3-ENTRY-MISSING` | ERROR |
| 3.5 | 占位图降级 asset 标注 | 读取 `docs/ASSET_ISSUES.md`,对降级为占位图(纯色+文字)的 asset 标 WARNING,不阻断 | `G3-PLACEHOLDER-DEGRADED` | WARNING |

> **占位图豁免**:game-asset-forge 失败时会降级为占位图(文件写到原 path,contentHash 重算),3.1/3.7 仍会 PASS,但语义错位(代码以为加载"开始按钮"实际是占位)。3.5 通过读 ASSET_ISSUES.md 识别这些 asset,在报告中标 WARNING 供人工后补,不阻断流水线。

### 6.3 L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.6 | 代码 UI 节点 ↔ PRD 节点树 | 代码中创建的 UI 节点与 PRD 节点树 1:1 对齐 | `G3-CODE-UI-NODE-MISMATCH` | ERROR |
| 3.7 | 代码资源引用 ↔ manifest | 代码中引用的资源 id 都能在 manifest 找到 | `G3-CODE-REF-MISSING` | ERROR |
| 3.8 | manifest contentHash 一致 | assets/ 下文件与 manifest contentHash 一致(内容指纹校验) | `G3-CONTENTHASH-MISMATCH` | ERROR |

> **引擎特定 L2 检查(3.9+)**:按 PRD/TECH_DESIGN 的引擎字段读取对应 references 文件执行,检查项编号与失败码见各文件:
>
> | 引擎 | references 文件 | L2 检查项 |
> |---|---|---|
> | Phaser 3 | `references/engine-checks-phaser.md` | 3.9 anims key 一致 |
> | Pixi.js | `references/engine-checks-pixi.md` | 3.10 AnimatedSheet 帧数一致 |
> | Godot 4 | `references/engine-checks-godot.md` | 3.11 NodePath 一致 / 3.12 信号连接一致 |
> | Unity | `references/engine-checks-unity.md` | 3.13 Resources.Load 路径 / 3.14 SceneBuilder 产出 |
> | 纯 Canvas | 无(无引擎特定 L2 检查) | — |
>
> **新增引擎时**:只需新建 `references/engine-checks-{engine}.md` 并在上方表格登记,SKILL.md 不动。
>
> 这些错误在 Gate 4 才会以运行时 404/NullReference 爆发,本门提前静态拦截。

### 6.4 L3 实跑预检

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.18 | 依赖可解析 | Web 引擎:`npm ls` 无 missing;Godot/Unity:工程配置完整 | `G3-DEP-MISSING` | ERROR |

> **引擎特定 L3 实跑预检**:按引擎读取对应 references 文件的 §L3 小节执行,检查项编号与失败码见各文件:
>
> | 引擎 | references 文件 | L3 检查项 |
> |---|---|---|
> | Phaser 3 | `references/engine-checks-phaser.md` §L3 | 3.15 `npm run typecheck` |
> | Pixi.js | `references/engine-checks-pixi.md` §L3 | 3.15 `npm run typecheck` |
> | 纯 Canvas | 回退到 `references/engine-checks-phaser.md` §L3(Web 引擎通用 typecheck) | 3.15 `npm run typecheck` |
> | Godot 4 | `references/engine-checks-godot.md` §L3 | 3.16 `godot --headless --check-only --script scripts/main.gd` |
> | Unity | `references/engine-checks-unity.md` §L3 | 3.17 Unity 编译检查(沙箱无 Unity 时 SKIPPED,延后 Gate 4) |
>
> **新增引擎时**:只需在对应 `references/engine-checks-{engine}.md` 中补充 §L3 小节,SKILL.md 不动。

> **严重度分级**:ERROR = 硬阻断;WARNING = 标记到报告,继续流水线;SKIPPED = 软阻断,延后到 Gate 4 补。
>
> **L3 只检测不修复**:typecheck/Godot check 失败时,本 skill 只读错误日志并归类到失败清单,返回给 game-code-forge 修复。本 skill 不修改任何代码,避免"自审自修"的伦理风险与职责越界。自动修复由 game-code-forge 重跑时按其自身的修复策略执行(沿用其 §typecheck 修复策略,最多 3 轮)。

---

## 七、报告输出

每个 Gate 产出 `docs/GATE_{N}_REPORT.md`,格式统一见 §3.3。

**阻断规则**:
- Gate 报告结论为 `FAIL` → game-forge-master 不允许进入下一阶段
- 失败清单含失败码 + 详情 + 修复建议,供原产出 skill 重跑时参考
- 修复后重跑本 Gate,直到 PASS 才放行

**报告归档**:
- 4 份 Gate 报告随项目保留,作为质量追溯依据
- game-integrate 的 `docs/BUILD_REPORT.md` 应引用 Gate 0~3 报告的结论

---

## 八、与 game-forge-master 的契约

### 8.1 接入位置

game-forge-master §七执行顺序修订为:

```
0. (可选) game-topic-brainstorm
1. game-blueprint
   → [Gate 0] 蓝图门(失败则回到 1 修复)
2. game-spec
   → [Gate 1] 规格门(失败则回到 2 修复)
3. game-art-spec
   → [Gate 2] 美术门(失败则回到 3 修复)
4. game-asset-forge + game-code-forge(并行)
   → [Gate 3] 产物门(失败则回到 4 修复)
5. game-integrate(内含 Gate 4 实跑门)
6. (可选) game-polish
```

### 8.2 失败回退策略修订

原 game-forge-master §六"所有失败都允许继续往下走"修订为**分级阻断**:

| 失败层级 | 阻断行为 | 回退到 |
|---|---|---|
| Gate 0/1/2 FAIL | **硬阻断**,不允许进入下一阶段 | 原产出 skill 修复后重跑 Gate |
| Gate 3 L1/L2 FAIL | **硬阻断** | game-asset-forge / game-code-forge 修复后重跑 Gate 3 |
| Gate 3 L3 typecheck/Godot check FAIL | **硬阻断**,返回错误日志 | game-code-forge 接手修复(沿用其自身 typecheck 修复策略,≤3 轮)后重跑 Gate 3 |
| Gate 3 L3 Unity 跳过 | **软阻断**(标注 SKIPPED),允许进入 Gate 4,由 game-integrate 补 | — |
| Gate 4 实跑(数值/浏览器) | **不属于本 skill**,沿用 game-integrate 现有策略(输出清单 + 截图,不阻塞构建) | 人工后补 |

### 8.3 裁剪规则

- **不可裁剪**:Gate 0/1/2/3 是流水线必走检查点,即使对应阶段被裁剪(如音频裁剪),也要跑 Gate 校验(音频裁剪时 Gate 2 检查 AUDIO_SPEC.md 标注"全部静音占位"即可通过)
- **可裁剪**:Gate 4 的浏览器自测与数值平衡实测,沿用 game-integrate 现有裁剪规则

---

## 九、质量检查清单

本 skill 自身的质量检查:

- [ ] 4 个 Gate 的检查项无遗漏(对照本 skill §三~§六)
- [ ] 每个 Gate 都输出 `docs/GATE_{N}_REPORT.md`
- [ ] 报告含失败码 / 详情 / 修复建议三要素
- [ ] FAIL 时有阻断,无"默认通过"
- [ ] **只读原则:本 skill 不修改任何产物文件,L3 失败仅返回日志交 game-code-forge 修复**
- [ ] **质量门范围:Gate 0~3 由本 skill 管,Gate 4 归 game-integrate 内置**
- [ ] Unity 跳过场景有降级路径(延后到 Gate 4)
- [ ] 增量更新场景下 predecessorId 改名不被误判为幽灵 asset(见 §5.3)
- [ ] 占位图降级 asset 在 Gate 3 标 WARNING 而非 ERROR(见 §6.2)
- [ ] **引擎特定检查(3.9+/3.15+)在 `references/engine-checks-{engine}.md` 维护,新增引擎只加文件不改 SKILL.md(见 §6.3/§6.4)**
