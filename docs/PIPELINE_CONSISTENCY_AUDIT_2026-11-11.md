# 流水线一致性审计（2026-11-11，第 3 轮）

> 触发：批次 1–3 共 24 项改动落地后，按"每轮真正出问题的都是改了一处、其他三处没跟着改"的规律做回归。
> 范围：`game-*` 九个 skill + `_shared`。方法：产物登记对齐、门禁编号唯一性、行数/描述体检、交叉引用有效性。

## 1 结论

4 处不一致已修，1 处红线超标已解，5 项检查通过。`validate.ps1` 新增第 14 项体检（WARN 不阻断），
把"超 500 行 / 描述超 200 字符"从靠记忆变成每次校验都可见。

## 2 已修

| # | 问题 | 性质 | 处置 |
|---|---|---|---|
| A1 | `game-teardown` **640 行**，超 500 红线 140 行 | 结构性 | 抽 §十四 产物格式（125 行）→ `references/teardown-doc-template.md`；抽 §8.2–8.5 判定细则（40 行）→ `references/evidence-grading.md`；§8.6 顺延为 §8.3。**640 → 491** |
| A2 | 总纲路径总表**未登记截图基线** | 产物遗漏（"③ 产物路径登记"违规） | `game-forge-master` §八 加一行：`docs/screenshots/*.png` + `baseline/manifest.json` |
| A3 | `game-integrate/runtime.yaml` **未登记** baseline 产物 | 契约缺失 | outputs 增 `docs/screenshots/baseline/`（optional，理由写在 description 里：缺基线是合法状态，但不能自动收录） |
| A4 | 4 个 description 超 200 字符（integrate 266 / code-forge 245 / teardown 212 / spec 208） | 路由精度 | 逐个精简至 ≤200，保留阶段号 + 输入 + 产出 + 复刻模式 + 触发词 |

## 3 检查通过（无需改）

| 检查项 | 结果 |
|---|---|
| `docs/LEVEL_AUTHORING.md` 四处登记（master ×3 / runtime / SKILL / gate 2.5.10） | 一致 |
| Gate 2.5 L1 条数表述（"6 项"）与实际条目 | 一致（2.5.1–4 + 2.5.9 + 2.5.10） |
| 失败码唯一性（G25-01..10 / G1-1.20,1.21 / G3-3.29） | 无重复定义；重复出现处均为合法回指 |
| `§九.7` / `§九.8` 在 art-spec、hint-solver 的交叉引用 | 指向的标题实际存在 |
| 全部 `game-*` SKILL.md 行数与 description | 现在全部 ≤500 行、≤200 字符 |

## 4 新增回归工具

`_shared/validate.ps1` 第 14 项：遍历全库 SKILL.md，报"超 500 行"与"description 超 200 字符"。
**只 WARN 不 FAIL**——历史遗留量大（2 个短剧 skill 超千行、31 个描述超限），一次拦死会让校验失去意义；
但每次校验都会刷出来，新增 skill 自己保持在红线内，这个列表就会逐步归零。

## 5 仍欠（明确不在本轮范围）

- 2 个短剧 skill 超 500 行（`ai-short-drama-project-development` 1055 / `ai-short-drama-topic-planner` 1246）
- 31 个 skill 的 description 超 200 字符（清单见 `validate.ps1` 输出）
- ISSUE-015（把 `game-forge-master` / `game-quality-gate` 压到 ≤300 行）——优先级低于上面两项

> 判定原则：**红线是规范，不是建议**。但清零要按批次走，不能靠一次性大改（改动面太大时，单次审计无法验证）。
