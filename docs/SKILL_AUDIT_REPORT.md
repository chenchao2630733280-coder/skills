# game 流水线 — 第二轮复审报告（修复后核验）

## 1. 总览

- 审查时间：2026-11-10T17:50:00+08:00
- 审查模式：**pipeline**（流水线审查 · 复审 / delta 审查）
- 审查范围：`game-forge-master` / `game-quality-gate` / `game-level-design`（主审）+ `game-code-forge` / `game-integrate`（消费方核验）
- 对照基线：`docs/SKILL_AUDIT_REPORT.round1.md`（19 条问题：4C / 10W / 5I）
- 审查维度：结构与体积 / 一致性与契约 / 健壮性 / 扩展性

### 本轮结论

| 项 | 结果 |
|---|---|
| 第一轮 4 个 CRITICAL | **0 残留**（逐条核验通过） |
| 第一轮 10 个 WARNING | **0 残留** |
| 第一轮 INFO | 3 修复 / 2 仍延后 |
| **本轮新发现** | **3 WARNING + 2 INFO（全部由本轮修复引入的"未闭环"）** |

**一句话结论**：修复本身没退化，但它只改了"上游声明"和"下游加载方式"，**门禁那一侧没跟着放宽**——`3.28` 仍假设只有一个 `config/levels.json`，而 `game-code-forge` 现在已经给出了四条等价路径；同时 code-forge 自己的输入校验还写着"4 份输入文档"。典型的"改了一半"。

---

## 2. 第一轮修复核验

| 编号 | 原问题 | 核验方式 | 结果 |
|---|---|---|---|
| ISSUE-001 | 阶段顺序三方打架 | `grep "Gate 2.5\|Gate 2]"` 五处文档 | ✅ 顺序统一，残留 0 |
| ISSUE-002 | `score` vs `difficulty_score` | 查 `export_levels.py` 输出键 + 文档 | ✅ 两侧均为 `difficulty_score` |
| ISSUE-003 | code-forge 未接 levels.json | `grep -rl levels.json --include=SKILL.md` | ✅ 5 个 SKILL.md 命中（原为 3） |
| ISSUE-004 | integrate 未消费目标带 | 查 §10.5 存在性 | ✅ 已加，含四行判定表 |
| ISSUE-005 | "四个检查点" | `grep 个检查点` | ✅ 12 行与 30 行均"六个" |
| ISSUE-006 | description 缺"关卡" | 读 frontmatter | ✅ 已含 `关卡后[Gate 2.5·关卡制]` |
| ISSUE-007 | 报告路径例外只列 0.5 | 查 §七 359 行 | ✅ "小数门一律用下划线" |
| ISSUE-008 | 归档份数未计 2.5 | `grep "基数 4"` | ✅ 改为基数 + 条件门 |
| ISSUE-009 | G25-01 判据不一致 | 比对 refs13:99 与 gate:117 | ✅ 均为 §0/§1/§2/§3/§5 |
| ISSUE-010 | 阶段枚举 6 项标 1~5 | 查 96 行 | ✅ 已去重 |
| ISSUE-011 | Gate 2.5 无基准 | 查 1.19 + 基准缺失降级 | ✅ 两处都在 |
| ISSUE-012 | 轻量模式无豁免 | `grep 轻量模式豁免` | ✅ 已加 |
| ISSUE-013 | 缺下游消费登记环节 | 查 §8.1 七项清单 + auditor §4.1.1 | ✅ 两处都在 |
| ISSUE-014 | 5 个文件称六引擎 | 查 245 行 | ✅ 已加括注 |
| ISSUE-017/018/019 | 错别字 / glob / 分类指引 | 逐项 grep | ✅ 均已修 |
| ISSUE-015/016 | 行数抽离 / description 压缩 | — | ⏸ 按计划延后 |

**结构红线复核**：master 438 / gate 433 / code-forge 445 / integrate **500** / level-design 181（均 ≤500）。

---

## 3. 本轮新发现

### WARNING

#### ISSUE-020 code-forge 的输入校验仍写"4 份输入文档"，新增的 levels.json 不在校验流程里

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：§一 已声明 `config/levels.json` 是"关卡制附加输入（必读）"，但 §十二 的读取前校验仍固定在 4 份文档上，既没说"存在则必读"，也没给缺失时的语义。执行者严格照 §十二 走，就会跳过关卡配置 → 直接踩 Gate 3 的 3.28。
- **证据**：
  - `game-code-forge/SKILL.md:370`：`逐个检查 4 份输入文档是否存在,缺失则报错并列出缺失文件后退出`
  - `game-code-forge/SKILL.md:375`：`读取 4 份输入文档后,**不要问用户**,直接生成`
  - 对照 `game-code-forge/SKILL.md:20`（关卡制附加输入，必读）
- **优化建议**：把校验拆成"必读 4 份（缺失即报错）"+"条件 1 份（存在则必读，缺失则在报告标注 `LEVELS_SKIPPED`）"。
- **改造方案**：
  1. 第 370 行改为"逐个检查 **4 份必读** 文档 …；再检查 `config/levels.json`：存在则纳入必读，缺失则标注 `LEVELS_SKIPPED` 并继续（单局制项目合法）"
  2. 第 375 行"4 份"→"4 份必读 + 可选的关卡配置"
  3. 该判据与 Gate 3 的 3.28「关卡制项目」条件保持一致
- **预期效果**：可选输入不会被流程吞掉，也不会因缺失而误报错。

#### ISSUE-021 Gate 3 的 3.28 只认一个路径，未覆盖 code-forge 新增的三条等价副本

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：我给了 code-forge 四条合法加载路径（根 `config/levels.json` import / `public/config/levels.json` fetch / Godot `res://config/levels.json` / Unity `Assets/StreamingAssets/config/levels.json`），但 3.28 的判据仍写"代码通过 `config/levels.json` 加载关卡"。字面理解只认第一种，Unity 的 `StreamingAssets` 与 Godot 的 `res://` 属"路径不同但语义相同"，可能被判 `G3-LEVEL-DATA-DRIFT` 误伤。
- **证据**：
  - `game-quality-gate/SKILL.md:315`：`代码通过 config/levels.json 加载关卡;src/ 中出现的关卡数值字面量与 levels.json 不一致即失败`
  - 对照 `game-code-forge/SKILL.md:295-303`（四条路径表）
- **优化建议**：判据改为"加载源必须是 `levels.json` 的**引擎内等价副本**，具体位置按引擎白名单"，并列出白名单。
- **改造方案**：
  1. 3.28 判据改为：`代码的关卡数据来自 config/levels.json 或其引擎内等价副本（Web: 根路径 import 或 public/config/levels.json；Godot: res://config/levels.json；Unity: Assets/StreamingAssets/config/levels.json）；除该文件外 src/ 不得出现关卡数值字面量`
  2. 失败码不变（`G3-LEVEL-DATA-DRIFT`），另加一句"副本必须与源文件内容一致（可比 contentHash）"
- **预期效果**：合规实现不误杀；同时堵住"复制一份到 src/ 再手改"的规避路径。

#### ISSUE-022 Gate 3 的输入清单未列 levels.json（3.28 要查它，输入节却没声明）

- **维度**：一致性与契约
- **严重级别**：WARNING
- **问题描述**：§6.1 输入只列了 manifest / PRD / ASSET_ISSUES / prev / `assets/` / `src/`，没有 `config/levels.json`。3.28 要拿它做基准比对，执行者按输入节准备材料时会漏读 → 该检查项实际会被跳过或空转。
- **证据**：`game-quality-gate/SKILL.md:287-293`（§6.1 输入）vs `:315`（3.28）
- **优化建议**：把 levels.json 作为条件输入列入 §6.1。
- **改造方案**：§6.1 追加一行：`- config/levels.json（如有，3.28 关卡数据走样比对基准；单局制项目不存在）`
- **预期效果**：3.28 的输入有明确来源，不再依赖执行者记忆。

### INFO

#### ISSUE-023 master 路径表未登记 levels.json 的引擎内派生副本

- **维度**：一致性与契约
- **严重级别**：INFO
- **问题描述**：§八 只登记了 `config/levels.json`（阶段 2.5 产出）。但为了让运行时读到它，Web 需复制到 `public/`、Godot 复制进工程根、Unity 复制到 `StreamingAssets`——这些是 code-forge 的构建期派生文件，路径表没登记。
- **证据**：`game-forge-master/SKILL.md:358`
- **优化建议**：追加一行"关卡配置副本（构建期派生）"，或注明"由 game-code-forge 按引擎复制，不单独登记"。
- **预期效果**：查产物时不会以为"只有一份"。

#### ISSUE-024 game-integrate 恰好 500 行，已贴红线

- **维度**：结构与体积
- **严重级别**：INFO
- **问题描述**：为上轮 10.5 压缩后刚好 500 行。任何后续新增都会越线，且没有余量做措辞修订。
- **证据**：`wc -l` → 500
- **优化建议**：下次触碰该文件时，先把 §十 的踩坑部分（10.1/10.2 的长篇叙述）抽到 `references/`，腾出 30-50 行余量。
- **预期效果**：恢复改造余量。

---

## 4. 优化建议 Top 3

### Top 1：把"加载路径白名单"写进 3.28（ISSUE-021 + ISSUE-022）
- **ROI**：⭐⭐⭐⭐⭐（判据改 2 行，避免 Unity/Godot 项目被误杀）
- **成本**：低（约 5 分钟）
- **关联**：ISSUE-021、ISSUE-022
- **做法**：3.28 判据补白名单 + §6.1 输入补 `config/levels.json`

### Top 2：code-forge 输入校验拆"必读 / 条件"（ISSUE-020）
- **ROI**：⭐⭐⭐⭐（否则 3.28 仍可能因输入被跳过而失败）
- **成本**：低（2 行）
- **关联**：ISSUE-020
- **做法**：§十二 第 370/375 行改写 + `LEVELS_SKIPPED` 标注约定

### Top 3：路径表登记派生副本（ISSUE-023）+ integrate 腾余量（ISSUE-024）
- **ROI**：⭐⭐（维护性收益）
- **成本**：低
- **关联**：ISSUE-023、ISSUE-024

---

## 5. 优先级矩阵

```
高收益 │ ②快速赢(优先做)              │ ①重大改造(计划做)
       │  Top1 3.28 白名单            │  （无）
       │  Top2 输入校验拆分           │
       │──────────────────────────────│──────────────────
       │  Top3 派生副本/行数余量      │
低收益 │ ④低优先(有空做)              │ ③暂缓(不建议做)
       低成本                         高成本
```

---

## 6. 下一步建议

1. **立即执行**：Top1 + Top2（合计 4 行改动，约 10 分钟），把"修复未闭环"补上
2. **然后**：跑一次 `_shared/validate.ps1` 确认全绿
3. **观察点**：本轮 3 条 WARNING 属于同一类——**改了 A 侧契约没改 B 侧判据**。以后再动"产物位置/加载方式"，固定做一次"三向核对"：产出方怎么写 → 消费方怎么读 → 门禁怎么判
4. **可选**：Top3

---

## 7. 第二轮修复记录（2026-11-10 17:55）

**3 WARNING 全修，1 INFO 顺手修，1 INFO 延后。**

| 编号 | 修复内容 | 改动文件 |
|---|---|---|
| ISSUE-021 | 3.28 判据改为「`config/levels.json` **或其引擎内等价副本**」，并列白名单（Web 根 import / `public/config/`、Godot `res://`、Unity `Assets/StreamingAssets/`），追加「副本内容须与源一致（contentHash）」——顺带堵住"复制到 src/ 手改"的规避路径 | `game-quality-gate/SKILL.md:316` |
| ISSUE-022 | §6.1 输入补 `config/levels.json`（条件输入，3.28 比对基准） | `game-quality-gate/SKILL.md:294` |
| ISSUE-020 | §十二 输入校验拆为「**4 份必读**（缺失报错）+ **1 份条件**（存在则纳入必读 / 缺失标 `LEVELS_SKIPPED` 并继续 / 非法 JSON 则报错退出）」 | `game-code-forge/SKILL.md:370-376` |
| ISSUE-023 | §八 路径表新增「关卡配置副本（构建期派生）」行，按引擎列三种位置，注明"内容与源一致，不手改" | `game-forge-master/SKILL.md:359` |
| ISSUE-024 | integrate 抽离 §10.1/10.2 腾余量 | ⏸ 延后（仍 500 行未越线） |

**顺带加固根因**：`game-forge-master` §8.1 阶段新增检查清单新增第 **④b 判据覆盖面** 一项——

> 若本阶段引入"多种合法形态"（多路径/多引擎/多格式），门禁判据必须逐形态覆盖并给白名单；否则判据只认一种形态，合规实现被误杀。这正是本轮 3 条 WARNING 的共同成因（改完 A 侧没改 B 侧）。

**修复后验证**：

```text
行数          439 / 434 / 447 / 500（均 ≤500）
落点核对      引擎内等价副本 ✓  §6.1 条件输入 ✓  LEVELS_SKIPPED ✓  派生副本行 ✓
validate.ps1  校验结果：全部通过（97 skill / 29 JSON / 125 references 路径 / runtime.yaml schema）
```

---

## 附：审查元数据

- 审查工具：skill-auditor v1.0（pipeline 模式 + delta 复审）
- 上一轮报告：`docs/SKILL_AUDIT_REPORT.round1.md`（19 条：4C/10W/5I，已修 17）
- 报告生成时间：2026-11-10T17:50:00+08:00
- JSON 工件：`docs/skill-audit-report.json`
