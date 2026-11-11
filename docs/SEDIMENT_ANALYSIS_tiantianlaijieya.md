# 《天天来解压》→ game-* skill 沉淀分析

> 分析时间：2026-11-11
> 被分析项目：`D:\work\AIGAME\天天来解压`
> 目标：找出可回流到 `game-*` 技能集的经验、资产与结构缺口
> 结论：**10 条值得沉淀（4 条 P0 结构缺口 + 4 条 P1 工程纪律 + 2 条 P2 数据样例），另 6 条判定为"不必沉"**
> 配套：`SEDIMENT_ANALYSIS_LGE.md`（关卡生成引擎专项）、`SEDIMENT_CAPABILITY_MAP.md`（**通用模块/能力/步骤/算法/方法论总图**，本文是"防错"视角，该文是"能力"视角）

---

## 1. 项目画像

| 项 | 值 |
|---|---|
| 玩法 | 竖屏解压消除：点线轴 → 毛线从底部卷走 → 露出拼豆图案 |
| 技术栈 | Phaser 3.90 + Vite 5 + TS strict，**纯程序化美术（零位图 / 零音频）** |
| 规模 | 100 关 + 102 个关卡 JSON；30 个 `_verify_*.mjs` 浏览器门禁脚本；`scripts/` 根下 77 个脚本 |
| 端 | Web（dev 5183）+ **微信小游戏**（`build:minigame` → IIFE 单文件） |
| 关卡形态 | **每关一个 JSON**（`src/data/levels/levelN.json`，字段 `id/cols/rows/slotMax/palette/legend/image/tray/occlusion`） |
| 最贵资产 | `ENGINEERING_RULES.md`（36 条"现象 → 判据 → 来源"约束）、`DIFFICULTY_DESIGN.md`（59 KB）、`LEVEL_GEN_ENGINE.md`（36 KB） |

**关键发现**：这个项目跑了我们的流水线（`docs/` 里有完整的 `GAME_BLUEPRINT`/`PRD`/`TECH_DESIGN`/`ART_SPEC`/`ASSET_MANIFEST`/`GATE_1~3_REPORT`/`POLISH_REPORT`/`LEVEL_PLAN`/`DIFFICULTY_REPORT`），所以它暴露的不是"没按流程走"，而是**流程本身的假设不成立**——尤其是"关卡=标量参数"和"美术=位图资源"这两条。

---

## 2. 结论速览

| 类别 | 条目 | 动作 |
|---|---|---|
| **P0 结构缺口** | 关卡数据双模（参数型 / 数据型） | 改 Phase 2.5 契约 + Gate 2.5 判据 |
| | 微信小游戏端 | game-integrate 增平台分支 + 适配 playbook |
| | 纯程序化美术模式 | game-art-spec 增 procedural 模式（内容复用 `procedural-art-forge`） |
| | 画稿 → 关卡 的生成链 | level-design 增 references（从美术图生成关卡配置） |
| **P1 工程纪律** | 门禁脚本"静默假绿"三件套 | game-integrate §10 / gate Gate 4 |
| | 源码 ↔ 构建产物 同步纪律 | game-code-forge + gate L3 |
| | 跨文件常量对账 | game-code-forge pitfall |
| | 样本门槛 + 数据集会变 | level-design 判读规则 |
| **P2 数据样例** | naive 0/100、human 57/100 的实证锚点 | level-design 的 calibrate 样例 |
| | "human 输 ≠ 无解（62% 有解）" | level-design 诊断判据 |
| **不必沉淀** | 美术六纪律 / 三级校验 / 端口 / NO_PROXY / 非 git / 具体像素参数 | 已覆盖或项目特异 |

---

## 3. P0：结构缺口（不补，同类项目会直接卡住）

### P0-1 关卡数据支持"双模"：参数型 vs 数据型

**问题**：阶段 2.5 的契约假设 `config/levels.json` 单文件、每关是一组**标量参数**（`params` + `target_win`）。
本作的关卡是**网格数据**：`image`（每格一个色键）、`legend`、`tray`、`occlusion`、`cols/rows/slotMax`，
且**每关一个文件**（102 个 json）。按现契约跑，2.5.2（`config/levels.json` 可解析）与 2.5.3（必填字段）都会 FAIL。

**证据**：
- `src/data/levels/level1.json` 顶层键：`id/name/cols/rows/slotMax/theme/tutorial/powerUps/palette/legend/image/tray/occlusion`
- 项目**没有** `config/` 目录（`ls config` → 不存在）
- 契约侧：`game-level-design/references/13_pipeline_integration.md` §2（产物清单只列 `config/levels.json`）

**建议**（改 2 处，约 30 分钟）：
1. `references/13` §2 增"关卡载体"二选一：
   - **参数型**：`config/levels.json` 单文件，每关 `params` 标量 + `target_win`
   - **数据型**：`config/levels/index.json`（关卡清单 + `level_id` 序）+ `config/levels/levelN.json`（网格/布局，体积大不适合塞单文件）
2. Gate 2.5 的 2.5.2/2.5.3 判据改为「按 `levels.json` 的 `mode` 字段或 `index.json` 存在性分支校验」；2.5.5 的集合比较改为对 `index.json` 的 `level_id` 序列（两种形态都成立）

> 这条正好是昨天刚写进 `game-forge-master §8.1` 的第 **④b 判据覆盖面** 的第二个实例：新阶段引入了形态差异，判据就必须逐形态覆盖。

### P0-2 微信小游戏端（平台分支）

**问题**：`game-integrate` 有 6 个引擎分支（Phaser/Pixi/Canvas/Godot/Unity/Three），但没有**平台分支**。
本作同一套 Phaser 代码，走 `vite.minigame.config.ts` 构建成 **IIFE 单文件**投小游戏，平台差异全在 `src/platform/` 适配层。
`docs/WECHAT_MINIGAME.md`（14.5 KB）已把这件事写成了完整 playbook。

**证据**：
- `docs/WECHAT_MINIGAME.md` 章节：平台 API 盘点 / 适配层设计（**用探测环境而非入口注入**、探测判据是 `createCanvas` 而非"有没有 wx"）/ IIFE 单文件为何必须 / storage 不吞异常 / 前后台语义差 / 已验证-未验证清单 / 落地清单
- pipeline 侧：`grep 微信` 只命中 `game-blueprint` 与 `game-topic-brainstorm`（只是"平台选项"），无任何构建/适配分支

**建议**（新建 1 个 references + 改 2 处，约 1 小时）：给 `game-integrate` 加"平台分支：Web / 微信小游戏"，references 提炼成 5 条硬约束：
1. 平台差异必须收敛到一个 `platform/` 适配层，业务代码不出现 `wx.*`
2. 环境探测用**能力探测**（`createCanvas`）而非**入口注入**——同一份 bundle 双端跑
3. 小游戏要求 **IIFE 单文件**，不能有动态 import/分包
4. storage 读写**不吞异常**（静默失败会让存档问题延后到线上）
5. 前后台事件语义与 Web 的 `visibilitychange` 不同，必须显式标注"未验证项"

### P0-3 纯程序化美术模式

**问题**：`game-art-spec` 的 `ASSET_MANIFEST` 假设每项资源有 `path/size/format/prompt`（AI 生图）。本作零位图：美术是**代码画的**，
`ART_SPEC.md §7` 叫「绘制配方（替代生图 prompt）」。Gate 2 的 2.1（8 字段）会误判。

**好消息**：内容侧**已经沉淀过了**——`procedural-art-forge` 就是从这个项目提炼的（五/六条可辨识度纪律、三级校验、曲线直径 ≥7×7）。
缺的只是**流水线没接上它**。

**证据**：
- `docs/ART_SPEC.md`：§7 绘制配方、§8 资源清单汇总、§10 已知风险
- `procedural-art-forge/SKILL.md`：description 已含"粒度预算/同色隔离/背景色不当前景/线宽≥2"，L3 实机截图纪律齐全
- `game-art-spec`：无 procedural 概念

**建议**（改 2 处，约 20 分钟）：
1. `game-art-spec` 增"两种出图模式"：**AI 生图**（现有）/ **程序化**（manifest 记 `drawRecipe` + `palette` + `gridSpec`，不记 `path/prompt`；绘制规范委派 `procedural-art-forge`）
2. Gate 2 的 2.1 判据按模式分支；程序化模式下 2.4「path 命名」不适用，改为「配方脚本存在且可复算」

### P0-4 关卡生成引擎（LGE）→ **已拆细为独立分析，见 `SEDIMENT_ANALYSIS_LGE.md`**

原先的判断是"画稿→关卡生成链强绑定本作机制，先观察"。这一判断**部分成立但颗粒度错了**：真正不可移的是生成算法本体（反向剥离/切轴/填盘拓扑），而引擎在打通流程时被迫回答的六个问题全部可移，且其中两条正好补上阶段 2.5 的真空缺：

- **D1 量尺自检**（p10/p50/p90/max → 分母过大/顶格/恒定三种病；固定阈值而非等分）——现有 `score.py` 无维度级分布检查；
- **D2 结构性必赢判据**（槽/色 ≥ 1 ⇒ 数学上不可能输；修复不得把难度买光）——现有实现只有统计信号 `BAND_MISS`，无结构信号；
- D3 修复阶梯代价序、D4 旋钮失效信号、D5 判据类型分层、D6 归因三条。

**结论**：不再单独写 `14_art_to_level_pipeline.md`。D1/D2/D3/D4 落进 `game-level-design` 的代码与 references，D5 落进 `game-quality-gate`，生成算法本体继续观察（等第二个同类项目）。详见 `SEDIMENT_ANALYSIS_LGE.md` §2 总表与 §10 执行顺序。

---

## 4. P1：工程纪律（与本作无关，任何游戏都用得上）

### P1-1 门禁脚本"静默假绿"三件套 ⭐ 最高 ROI

这是 `ENGINEERING_RULES.md` 里最值钱的部分——**断言过了，但什么都没测**。

| 坑 | 现象 | 判据（可直接抄） |
|---|---|---|
| **门控吞点击** | 教程关的点击被门控吞掉，脚本点"可点元素"全部无效，断言在"什么都没发生"下继续跑 | 点击前先 `tutorialDone = true` 并 `clearSpotlight()`；**不能只清 `tutorialTargetId`**——每成功一步会重新装填下一步目标，清一次只骗过第一下 |
| **固定等待判就绪** | `restart()` 后 `waitForTimeout(900)`，埋点打在**正在销毁的旧对象**上：赋值静默成功、新对象没打桩、结果永远是空数组，最后死在超时且**零报错** | 改用 `waitForFunction` 等真实就绪谓词（对象 id 匹配 + 目标容器非空）；**埋点装好后立刻断言"埋点对象 === 当前对象"** |
| **拿可再生的数据当基线** | 断言 `L7 色数 > L6`，而 L6 每次重生都会逼近 L7 ⇒ 同一个原因假红三次，每次都"产品是好的" | 锁定样板写**绝对值**；生成器产出只能当参照物不当标尺；要比"升级关系"就比**结构量**不比规模 |

**落点**：`game-integrate` §十 新增 `10.6 浏览器自测的假绿防线`；`game-quality-gate` Gate 4 引用。
**成本**：约 40 分钟。**收益**：直接消灭"门禁全绿但线上是坏的"这类最贵故障。

### P1-2 源码 ↔ 构建产物 同步纪律

**现象**：仓库里的 `sim.mjs` 与 `sim.ts` 不同步，改了源码忘 build **不报任何错**，只是数字悄悄变了（妥协分布 77/22/1/0 → 54/36/9/1，星级整体位移）。
**判据**：三件一起做——`npm run build:sim` + `npm run check:sim`（逐字节确认产物与源码一致）+ 一个**行为对照脚本**（比任何单测都敏感）。
**落点**：`game-code-forge` §九 生成规则 或 pitfall；gate L3 增一条"派生产物与源一致"检查。
**泛化**：凡"源码 + 生成产物"并存的（`sim.ts→mjs`、`*.proto→ts`、图集→json），都要有 check 脚本。

### P1-3 跨文件常量对账

**现象**：`engine.mjs` 抄了 `MAX_CELLS = 900`，而 `core/validateLevel.ts` 实际是 2000 ⇒ 误拒合法尺寸（L13 就是 1222 格）。
**判据**：凡常量在两处出现，要么 `import`，要么注释写明出处并在改动时同步；维护一份"已知需对账"清单。
**落点**：`game-code-forge` pitfall（与现有 6 个 pitfall 并列）。
**成本**：10 分钟。

### P1-4 样本门槛 + 数据集会变

**现象**：三次误判都源于小样本（14 张样张 / 34 个变体 / 60 个切片），全量跑完结论全反。
**判据**：判断"某类素材/某档难度不够"之前跑全量；**文档里的分布数字必须带时间戳**，因为数据集本身会被别的脚本/会话改写。
**落点**：`game-level-design/SKILL.md` §七 判读规则（现有 11 条信号表）加两条元规则：`SAMPLE_TOO_SMALL`、`DATASET_DRIFT`。
**与本 skill 现有设计的关系**：诊断器已有 `DATA_GAP`（样本 <30 不下结论），这条是把它从"关卡通关数据"推广到"素材/变体/切片"。

---

## 5. P2：数据样例（可直接当校准锚点）

### P2-1 分层玩家实证：naive 0/100、human 57/100

本作 100 关实测：
- `naive`（看到亮的就点）**0/100 通关**
- `human`（挑"颜色在底面且抽得动"的那根）**57/100 通关**，剩余 43 关里 14 关超时、29 关死锁

这是**真实项目的分层通关分布**，比任何假设的 θ 值都可信。做法：作为 `game-level-design/examples/` 的第二个品类样例（现有示例全是 match3 参数型）。
**价值**：让"目标首通率 0.85"这类数字有现实感——一个设计得"不无脑"的关卡，对 naive 玩家就是 0%。

### P2-2 "human 输 ≠ 无解（62% 有解）"

本作用 `look` 裁判会把可解关误判成死关；换 `human` 后：**human 赢 ⇒ 一定可解（零反例），human 输 ≠ 无解（62% 仍有解）**。
**落点**：`game-level-design/references/07_player_skill_and_calibration.md` + `diagnose.py` 的 `NEAR_UNWINNABLE` 判读——现在 skill 里说"先跑求解器确认可解性"，这条给出了**求解器的判定偏置方向**（保守裁判会假阳性）。

---

## 6. 判定"不必沉淀"的 6 条

| 项 | 为什么不必沉 |
|---|---|
| 美术六纪律（同色隔离/背景色/线宽/粒度/曲线直径） | **已沉淀**在 `procedural-art-forge`，内容比本文件更完整 |
| 三级校验（字符图→PNG→实机） | 同上，已在 `procedural-art-forge` §L1/L2/L3 |
| 端口 5183 / `NO_PROXY` / 后台起 dev / playwright install | 本机环境坑，除 `NO_PROXY` 外无跨项目价值（且属 agent 运行环境，不属游戏知识） |
| 项目非 git、交付靠文件 | 项目特异；若泛化成"无版本控制时先备份"意义太薄 |
| 具体像素参数（36 列 16px、ΔE ≥34、色距 ≥110） | 与本作"36×20 画布 + 拼豆"强绑定，硬搬会误导其他品类 |
| `regrain` 色阶颗粒化三条纪律 | 属具体美术技法，`procedural-art-forge` 的"变体"章节已覆盖上层原则 |

> 判据沿用本作 `ENGINEERING_RULES.md §6` 的分流原则：**"这条知识问『它会不会被我下次再踩』——会，才值得进约束；只是讲清现状，进 docs。"**

---

## 7. 建议执行顺序

| 顺序 | 动作 | 成本 | 理由 |
|---|---|---|---|
| 1 | **P1-1 假绿三件套** → game-integrate §10.6 | 40 min | ROI 最高，与项目无关，立刻可用 |
| 2 | **P0-1 关卡双模** → refs13 + Gate 2.5 判据 | 30 min | 不补则任何"网格类"关卡项目都会卡在 Gate 2.5 |
| 3 | **P0-3 程序化美术模式** → game-art-spec + Gate 2 | 20 min | 内容已有，只差接上引用 |
| 4 | **P1-2 + P1-3** → code-forge pitfall | 30 min | 便宜，防"改了源码数字悄悄变" |
| 5 | **P0-2 微信小游戏端** → integrate references | 1 h | 有完整 playbook 可提炼，但只影响小游戏项目 |
| 6 | **P2-1 / P2-2** → level-design examples + refs07 | 40 min | 校准锚点，提升"目标首通率"的现实感 |
| 7 | ~~P0-4 画稿→关卡 references~~ → 改为 **LGE D1+D2**（见 `SEDIMENT_ANALYSIS_LGE.md` §10） | 6 文件 | 量尺自检 + 结构性必赢判据，均为阶段 2.5 真空缺；生成算法本体继续观察 |

**一句话**：前 4 条就能把这个项目最有价值的部分吃干净；第 7 条的生成链本体继续观察，但 LGE 的判定纪律（D1–D4）已单列成 `SEDIMENT_ANALYSIS_LGE.md`，其中 D1/D2 值得排在 P0-1 之后立刻做。

---

## 附：证据索引

| 结论 | 证据位置 |
|---|---|
| 关卡是网格数据、每关一文件 | `src/data/levels/*.json`（102 个），字段 `image/legend/tray/occlusion` |
| 无 `config/levels.json` | `ls config` → 不存在 |
| 微信小游戏完整 playbook | `docs/WECHAT_MINIGAME.md`（8 章） |
| 程序化美术配方替代 prompt | `docs/ART_SPEC.md §7` |
| 假绿三件套 | `ENGINEERING_RULES.md` R-05 / R-41 / R-42 |
| 产物同步 | 同上 R-19；`docs/LEVEL_GEN_ENGINE.md §16` |
| 常量对账 | 同上 R-20（`MAX_CELLS` 900 vs 2000） |
| 样本门槛 | 同上 R-23 |
| 分层实测 | `README.md`（naive 0/100、human 57/100）；`docs/LEVELS_100_REPORT.md §5` |
| human 输 ≠ 无解 | `ENGINEERING_RULES.md` R-11；`docs/DIFFICULTY_DESIGN.md §8.7` |
| 画稿→关卡链 | `docs/LEVEL_GEN_ENGINE.md`（17 章，含公平修复阶梯 / 星级标定 / 能力探测） |
| 美术纪律已沉淀 | `procedural-art-forge/SKILL.md` 六纪律 + 三级校验 |
