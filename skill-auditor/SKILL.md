---
name: "skill-auditor"
description: "审查 skill 质量并给出优化建议(4 模式+4 维度,产出报告+JSON)。当用户要'审查/优化/分析 skill 质量'、'对比 skill 与基准'、'审查流水线一致性'时调用。"
---

# Skill Auditor — Skill 质量审查与优化建议

本 skill 是 skill 集合的**质量审查工具**,职责是:对单个 skill、skill 集合、整条流水线或对比基准进行结构化审查,从 4 个维度发现问题和优化点,产出 Markdown 报告 + JSON 工件,供人工或自动化改造消费。

本 skill **只读不写**:不直接修改被审查的 skill,所有优化建议以报告形式产出。

---

## 一、何时调用

满足以下任一条件即调用本 skill:
- 用户说"审查/检查/分析 skill 质量"
- 用户说"优化 skill"但需要先给出诊断建议(而非直接改)
- 用户说"对比 skill A 和 skill B"或"对比 skill 与基准模式"
- 用户说"审查流水线一致性/阶段衔接/产物契约"
- 用户在新增引擎/端类型后,想验证四位一体扩展是否完整

**不要**在以下场景调用:
- 用户要直接修改 skill(用 Edit/Write)
- 用户要创建新 skill(用 skill-creator)
- 用户只是问"skill 怎么写"(纯咨询,用对话回答)

---

## 二、四种审查模式

| 模式 | 输入 | 适用场景 | 产出粒度 |
|---|---|---|---|
| **单 skill 审查** | 1 个 skill 目录 | 深度诊断单个 skill 的结构与质量 | 该 skill 的问题清单 |
| **集合审查** | 一组相关 skill(如 game-forge-*) | 跨 skill 一致性、命名对齐、JSON 工件消费链 | 集合级 + 单 skill 级问题 |
| **流水线审查** | 编排总纲 + 全部下游 skill | 阶段衔接、产物契约、失败回退、裁剪规则 | 流水线级问题 |
| **对比基准审查** | 1 个目标 skill + 1 个基准 skill | 评估目标 skill 与基准模式的差距 | 差距清单 + 改造建议 |

### 模式选择决策

```
用户需求
├─ 给了 1 个 skill → 单 skill 审查
├─ 给了一组 skill(同前缀/同领域)→ 集合审查
├─ 给了"流水线/编排/总纲"关键词 → 流水线审查
├─ 给了"对比/差距/基准"关键词 → 对比基准审查
└─ 不确定 → 询问用户
```

---

## 三、四个审查维度

每个维度有详细的审查规则,抽离到 `references/` 按需读取。

### 维度 1:结构与体积(`references/audit-structure.md`)
审查 skill 的文件组织、体积控制、懒加载可行性。
- SKILL.md 行数阈值(≤300 推荐,300-500 可接受,>500 必须拆分)
- references 抽离完整性(索引块指向的文件都存在)
- 章节编号连续性(无跳号/重号)
- frontmatter description 质量(含 what + when,≤200 字符)
- 重复内容检测(无与 `_shared/references/` 重复的本地拷贝)

### 维度 2:一致性与契约(`references/audit-consistency.md`)
审查跨 skill 的路径、命名、CLI 命令、JSON 工件消费链对齐。
- 产物路径表与实际产物一致
- 命名规范(端类型/引擎命名跨 skill 一致)
- CLI 命令对齐(三 skill 间同一命令字符串一致)
- JSON 工件消费链(上游产出字段 ⊇ 下游消费字段)
- frontmatter 引擎/端类型声明与决策树一致

### 维度 3:健壮性(`references/audit-robustness.md`)
审查失败回退、降级路径、占位机制。
- 失败回退策略表(每类失败有对应回退)
- 降级层级(自动修复 N 轮 → 降级 → 占位 → 延后)
- 失败不阻塞(失败项进报告,允许继续)
- 错误处理边界(系统边界有校验,内部信任)

### 维度 4:扩展性(`references/audit-extensibility.md`)
审查新能力接入成本和四位一体模板覆盖。
- 四位一体覆盖(决策树+模板索引+产物路径表+集成分支)
- 新引擎/端类型接入成本评估
- 决策树完备度(覆盖所有声明场景,无遗漏分支)
- 模板索引与产物路径表同步

---

## 四、审查流程

### Step 1:确定审查模式与范围

1. 根据用户输入按 §二决策树选择审查模式
2. 确定被审查的 skill 目录(单个/集合/流水线)
3. 若对比基准审查,确定基准 skill(默认基准:`game-forge-master` 的四位一体模式)
4. 用 AskUserQuestion 确认审查维度(默认 4 维全审)

### Step 2:读取被审查 skill

1. 列出被审查 skill 的目录结构(SKILL.md + references/ + 其他文件)
2. 读取 SKILL.md 全文
3. 按审查维度按需读取 references/audit-*.md 获取详细审查规则
4. (集合/流水线审查)读取所有相关 skill 的 SKILL.md

### Step 3:按维度执行审查

对每个启用的维度,读取对应 `references/audit-{dimension}.md`,逐条检查审查项,记录:
- 问题编号
- 维度
- 严重级别(CRITICAL / WARNING / INFO)
- 问题描述
- 证据(文件路径 + 行号)
- 优化建议
- 改造方案(具体到文件/行/修改内容)

### Step 4:交叉验证

1. (集合/流水线审查)跨 skill 一致性检查:路径/命名/CLI 命令对齐
2. (对比基准审查)逐维度对比目标与基准,记录差距
3. 检查审查项之间是否有冲突或重复,合并

### Step 5:产出报告

按 `references/audit-report-template.md` 产出 Markdown 报告,按 `references/audit-report-schema.json` 产出 JSON 工件:

- `docs/SKILL_AUDIT_REPORT.md`:人读报告,含总览+问题清单+优化建议+优先级排序+改造方案
- `docs/skill-audit-report.json`:机读工件,供下游自动化改造 skill 消费

### Step 6:简报

向用户简报:
- 审查模式与范围
- 各维度问题数(CRITICAL/WARNING/INFO)
- Top 3 优化建议(按优先级)
- 报告与 JSON 工件路径
- 下一步建议(是否要按报告执行改造)

---

## 五、产出契约

### 5.1 Markdown 报告(`docs/SKILL_AUDIT_REPORT.md`)

> 完整模板见 `references/audit-report-template.md`。

**必填章节**:
1. 总览:审查模式、范围、时间、各维度问题统计
2. 问题清单:按严重级别排序,每条含编号/维度/级别/描述/证据/建议/方案
3. 优化建议 Top N:按 ROI(收益/成本)排序
4. 改造方案:每条建议对应的具体文件/行/修改内容
5. 优先级矩阵:横轴改造成本,纵轴收益,四象限

### 5.2 JSON 工件(`docs/skill-audit-report.json`)

> Schema 见 `references/audit-report-schema.json`。

**关键字段**:
- `auditMode`:审查模式(single/collection/pipeline/benchmark)
- `target`:被审查 skill 路径列表
- `benchmark`:基准 skill(对比基准审查时)
- `dimensions`:4 维度的审查结果
- `issues`:问题数组,每条含 id/dimension/severity/description/evidence/suggestion/plan
- `summary`:总览统计(CRITICAL/WARNING/INFO 计数)
- `topSuggestions`:按 ROI 排序的 Top 优化建议

---

## references 使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/audit-structure.md` | 审查维度 1(结构与体积)时 |
| `references/audit-consistency.md` | 审查维度 2(一致性与契约)时 |
| `references/audit-robustness.md` | 审查维度 3(健壮性)时 |
| `references/audit-extensibility.md` | 审查维度 4(扩展性)时 |
| `references/audit-report-template.md` | 产出 Markdown 报告时 |
| `references/audit-report-schema.json` | 产出 JSON 工件时 |

---

## 六、严重级别定义

| 级别 | 含义 | 示例 |
|---|---|---|
| **CRITICAL** | 导致 skill 无法正常工作或产出错误结果 | references 索引指向不存在的文件;产物路径表与实际产物不一致 |
| **WARNING** | 不阻塞但影响效率/可维护性 | SKILL.md >500 行未拆分;章节编号跳号;命名跨 skill 不一致 |
| **INFO** | 优化空间,不改也能工作 | description 未含触发条件;懒加载可进一步优化 |

---

## 七、交互约定

1. 默认全程中文输出
2. 审查前用 AskUserQuestion 确认模式与维度(除非用户已明确)
3. 审查过程**只读不写**,不修改被审查 skill
4. 每个维度审查完输出简短进度(用 TodoWrite 追踪)
5. 最终产出报告 + JSON,并向用户简报 Top 3 建议
6. 不自动执行改造(改造由用户决定后另行执行)
7. 若用户在审查后说"按报告改",则切换到 Edit/Write 模式执行改造

---

## 八、基准模式参考

对比基准审查的默认基准是 `game-forge-master` 的四位一体模式:

| 基准特征 | 说明 |
|---|---|
| 总纲+子 skill 编排 | 总纲只调度,具体逻辑下沉子 skill |
| 懒加载 + references 抽离 | SKILL.md ≤300 行,重内容抽到 references |
| 四位一体扩展 | 决策树+模板索引+产物路径表+集成分支同步更新 |
| JSON 工件驱动 | 上游产出 JSON,下游优先读 JSON |
| 失败回退 + 降级 | 每类失败有回退,不阻塞流水线 |
| 固定路径 + 自动校验 | 产物路径固定,validate 脚本检查一致性 |

若用户未指定基准,按此默认基准执行对比。
