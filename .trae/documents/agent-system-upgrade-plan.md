# 产品工作台 AI Agent 体系升级计划

> **范围**:第一阶段全部(Tool 层 + 工程 skill 缺口 + Evaluation 闭环 + Guardrail 层 + Memory 层)
> **集成方式**:编排末尾加可选 Tool 确认点
> **新建 skill 数**:12 个 | **扩展现有 skill**:4 个 | **更新索引文件**:3 个

---

## 一、现状分析(基于 Phase 1 探索)

### 1.1 已具备的基础设施

| 层 | 现状 | 证据 |
|---|---|---|
| Skill 层 | 38 个 skill,覆盖产品交付/游戏/文档/短剧 | `WORKBENCH.md` + `README.md` |
| 编排层 | 2 个总纲(product-pipeline-master + game-forge-master),已有质量门禁 + 人工确认点 | `product-pipeline-master/SKILL.md` §八/§九.1;`game-forge-master/SKILL.md` §七/§九.1 |
| 评测层(静态) | skill-auditor 4 模式 4 维度,只读不写 | `skill-auditor/SKILL.md` |
| 评测层(文档) | prd-quality-checker 有完整执行契约 | `prd-quality-checker/references/execution-contract.md` |
| 共享层 | _shared/references 唯一事实来源 + validate.ps1 防回归 | `_shared/validate.ps1` |
| skill 标准结构 | frontmatter(name+description) + SKILL.md + references/ + scripts/ + agents/openai.yaml | ruanzhu-doc-generator / pet-health-product-simulator / rd-init |
| scripts 集成模式 | `scripts/*.py` 封装确定性逻辑,SKILL.md 只写调用命令 | `rd-init/scripts/rd-init.py`、`ruanzhu-doc-generator/scripts/build_ruanzhu_doc.py` |

### 1.2 关键缺口(12 维度诊断结果)

| 维度 | 覆盖度 | 缺口 |
|---|---|---|
| Tool | ★☆☆☆☆ | 无 git/ci/deploy/db/monitor 工具封装,产物无法自动进入工程闭环 |
| Skill(工程类) | ★★★★☆ | 缺 code-review/debug-fix/refactor 三个研发 skill |
| Evaluation | ★★☆☆☆ | 仅静态审查,无执行后评测/产物自评 |
| Guardrail | ★☆☆☆☆ | 无敏感操作拦截/diff 审查 |
| Memory | ★★☆☆☆ | 仅会话级,无项目知识库/失败案例库 |

### 1.3 可复用的现有模式

- **skill 创建模式**:参照 `ruanzhu-doc-generator`(frontmatter + SKILL.md + scripts + references + agents/openai.yaml)
- **scripts 封装模式**:参照 `rd-init/scripts/rd-init.py`(Python 脚本 + SKILL.md 写调用命令)
- **评测报告模式**:参照 `skill-auditor` 的 4 维度 + Markdown 报告 + JSON 工件
- **编排接入模式**:参照现有"人工确认点"模式(⏸ 标注 + AskUserQuestion 三选项)
- **共享校验模式**:参照 `_shared/validate.ps1` 的防回归校验

---

## 二、改造方案总览

```
模块 A:Tool 层(5 个新 skill)
  tool-git-ops / tool-ci-ops / tool-deploy-ops / tool-db-ops / tool-monitor-ops
       ↓ 被编排总纲调用
模块 F:编排总纲接入(2 个 skill 扩展)
  product-pipeline-master 末尾加 Tool 确认点
  game-forge-master 末尾加 Tool 确认点
       ↓
模块 B:工程 skill 缺口(3 个新 skill)
  code-review / debug-fix / refactor
       ↓ 被模块 C 评测
模块 C:Evaluation 闭环(1 个 skill 扩展)
  skill-auditor 新增"执行后评测"模式 + 各 skill 加产物自评
       ↓ 受模块 D 保护
模块 D:Guardrail 层(2 个新 skill)
  guardrail / diff-reviewer
       ↓ 沉淀到模块 E
模块 E:Memory 层(2 个新 skill)
  project-knowledge-base / failure-casebook
       ↓
模块 G:工作台索引更新(3 个文件)
  WORKBENCH.md / README.md / _shared/validate.ps1
```

---

## 三、模块 A:Tool 层(新建 5 个 skill)

### 通用设计原则

- 每个 tool skill 遵循标准结构:`SKILL.md` + `scripts/` + `agents/openai.yaml`
- scripts 封装确定性逻辑(Python),SKILL.md 写调用命令 + 触发条件
- **只读优先**:查询类操作直接执行,变更类操作需用户确认
- **失败不阻塞**:Tool 失败时返回错误报告,不阻断流水线

### A1. tool-git-ops

**路径**:`tool-git-ops/`

**frontmatter**:
```yaml
name: "tool-git-ops"
description: "Git 工具层 skill。封装 git add/commit/branch/push/diff/log 操作,支持'只提交产物目录''自动生成 commit message''创建 PR 分支'。当编排总纲或其他 skill 要把产物提交到 Git 时调用。"
```

**职责**:
- 接收产物路径列表 + 可选 commit message
- 自动 git add 指定路径(不 add 全部,防误提交)
- 自动生成 commit message(基于产物类型 + 路径摘要)
- 可选创建新分支(避免直接提交 main)
- 可选 git push(需用户确认)
- 产出 `git-ops-report.json`(提交的文件清单 + commit hash + branch)

**scripts**:
- `scripts/git_ops.py`:核心封装,子命令 `commit` / `branch` / `push` / `diff` / `log`
- `scripts/generate_commit_message.py`:基于产物路径生成 commit message

**references**:
- `references/git-ops-contract.md`:输入/输出契约 + 安全规则(哪些路径禁止提交)

**关键约束**:
- 默认不 push(需用户明确确认)
- 默认不提交 `.env` / `credentials.json` / `*.key` 等敏感文件(硬编码黑名单)
- commit message 格式:`[skill:{skill名}] {动作描述} ({产物数量} files)`
- 失败时返回 `git-ops-report.json` 含 error 字段,不抛异常阻断调用方

### A2. tool-ci-ops

**路径**:`tool-ci-ops/`

**frontmatter**:
```yaml
name: "tool-ci-ops"
description: "CI/CD 工具层 skill。封装'触发 CI''查询构建状态''读取测试报告'操作。当编排总纲或其他 skill 要触发持续集成或查询构建结果时调用。"
```

**职责**:
- 接收仓库地址 + CI 平台(github-actions / gitlab-ci / jenkins)
- 触发 CI 流水线(可选分支)
- 查询构建状态(running / success / failed)
- 读取测试报告(测试通过率 / 失败用例)
- 产出 `ci-ops-report.json`

**scripts**:
- `scripts/ci_ops.py`:子命令 `trigger` / `status` / `report`
- 支持 github-actions(gh cli)/ gitlab-ci(glab cli)/ jenkins(jenkins-cli)

**references**:
- `references/ci-platforms.md`:各 CI 平台的接入方式 + 命令映射

**关键约束**:
- 触发 CI 需用户确认(变更类操作)
- 查询类直接执行
- CI 平台不可用时降级为"提示用户手动触发"

### A3. tool-deploy-ops

**路径**:`tool-deploy-ops/`

**frontmatter**:
```yaml
name: "tool-deploy-ops"
description: "部署工具层 skill。封装'部署到各平台''回滚''健康检查'操作,支持 GitHub Pages / Vercel / Netlify / CloudBase / COS。当编排总纲或其他 skill 要部署产物时调用。"
```

**职责**:
- 接收产物路径 + 目标平台
- 调用对应平台 CLI 部署
- 部署后健康检查(HTTP 状态码 + 响应时间)
- 支持回滚(回退到上一版本)
- 产出 `deploy-ops-report.json`(部署 URL + 版本号 + 健康检查结果)

**scripts**:
- `scripts/deploy_ops.py`:子命令 `deploy` / `rollback` / `healthcheck`
- 复用 `web-static-deploy` skill 的部署知识(references 引用,不重复)

**references**:
- `references/deploy-platforms.md`:各平台部署命令 + 配置模板(引用 `web-static-deploy/references/`)

**关键约束**:
- 部署需用户确认(变更类操作)
- 回滚需用户确认
- 健康检查失败时标 WARNING,不阻断
- 平台 CLI 不可用时降级为"输出部署指令供用户手动执行"

### A4. tool-db-ops

**路径**:`tool-db-ops/`

**frontmatter**:
```yaml
name: "tool-db-ops"
description: "数据库工具层 skill。封装'跑 migration''查询数据''回滚迁移'操作。当 implement-data-layer 或其他 skill 要执行数据库操作时调用。生产环境只读。"
```

**职责**:
- 接收迁移文件路径 + 数据库连接配置
- 执行 migration(up / down)
- 查询数据(只读 SELECT)
- 产出 `db-ops-report.json`

**scripts**:
- `scripts/db_ops.py`:子命令 `migrate` / `query` / `rollback`

**references**:
- `references/db-safety.md`:安全规则(生产环境只 SELECT / migration 需确认 / 回滚需确认)

**关键约束**:
- **生产环境只读**:检测到 production 连接串时,只允许 query,禁止 migrate/rollback
- migrate 需用户确认
- rollback 需用户确认 + 二次确认
- 连接串从环境变量读取,不写入产物

### A5. tool-monitor-ops

**路径**:`tool-monitor-ops/`

**frontmatter**:
```yaml
name: "tool-monitor-ops"
description: "监控工具层 skill。封装'查日志''查 metric''查 trace'操作。当 debug-fix 或其他 skill 要排查线上问题时调用。只读。"
```

**职责**:
- 接收服务名 + 时间范围
- 查询日志(支持关键词过滤)
- 查询 metric(CPU / 内存 / QPS / 错误率)
- 查询 trace(请求链路)
- 产出 `monitor-ops-report.json`

**scripts**:
- `scripts/monitor_ops.py`:子命令 `logs` / `metrics` / `trace`

**references**:
- `references/monitor-platforms.md`:各监控平台接入(ELK / Prometheus / Jaeger / 云厂商)

**关键约束**:
- 纯只读,无变更操作
- 日志默认返回最近 100 条,可配置
- 平台不可用时降级为"提示用户手动查询"

---

## 四、模块 B:工程 skill 缺口(新建 3 个 skill)

### B1. code-review

**路径**:`code-review/`

**frontmatter**:
```yaml
name: "code-review"
description: "代码审查 skill。接收 PR 或 diff,检查代码质量/安全/性能/可维护性问题,产出审查报告+修复建议。当用户要'审查代码/Review PR/检查代码质量'时调用。"
```

**职责**:
- 接收 git diff 或 PR 链接
- 按 4 维度审查:正确性 / 安全性 / 性能 / 可维护性
- 产出 `code-review-report.md` + `code-review-report.json`
- 标注严重级别(blocker / warning / suggestion)

**references**:
- `references/review-checklist.md`:4 维度检查项清单
- `references/review-report-template.md`:报告模板

**关键约束**:
- 只读不写,不直接改代码
- blocker 级问题需明确标红
- 复用 `skill-auditor` 的报告模式(Markdown + JSON 双产出)

### B2. debug-fix

**路径**:`debug-fix/`

**frontmatter**:
```yaml
name: "debug-fix"
description: "调试修复 skill。接收错误日志/堆栈/复现步骤,定位 Bug 根因并修复。当用户要'调试/修 Bug/排查错误'时调用。"
```

**职责**:
- 接收错误日志 + 堆栈 + 复现步骤
- 定位相关代码(调用 SearchCodebase)
- 分析根因
- 产出修复方案 + 直接修复
- 产出 `debug-report.md`(根因 + 修复方案 + 修复 diff)

**references**:
- `references/debug-patterns.md`:常见 Bug 模式(空指针 / 并发 / 资源泄漏 / 边界条件)
- `references/debug-workflow.md`:调试工作流(复现 → 定位 → 假设 → 验证 → 修复)

**关键约束**:
- 修复前需用户确认
- 最多重试 3 轮(失败后转人工)
- 修复后建议跑测试(联动 test-and-harden-system)

### B3. refactor

**路径**:`refactor/`

**frontmatter**:
```yaml
name: "refactor"
description: "代码重构 skill。在不改变功能的前提下改善代码结构/可读性/性能。当用户要'重构/优化代码结构/消除技术债'时调用。"
```

**职责**:
- 接收目标文件/模块 + 重构目标(可读性 / 性能 / 拆分 / 合并)
- 产出重构方案(变更前后对比)
- 执行重构(保持功能不变)
- 建议跑测试验证

**references**:
- `references/refactor-patterns.md`:重构模式(提取方法 / 内联 / 移动 / 重命名 / 提取类)
- `references/refactor-safety.md`:安全重构规则(小步 / 保测试 / 不混合功能变更)

**关键约束**:
- **不改变功能**(重构 + 功能变更必须分两次)
- 每步重构后建议跑测试
- 重构方案需用户确认才执行

---

## 五、模块 C:Evaluation 闭环(扩展 skill-auditor)

### C1. 扩展 skill-auditor

**改动文件**:`skill-auditor/SKILL.md` + 新增 `references/audit-execution.md`

**新增内容**:
1. §二四种审查模式后加第 5 种:**执行后评测模式**
   - 输入:skill 执行产物 + 标准测试集(可选)
   - 检查:产物质量评分 / 规范符合度 / 可运行性(对代码类)
   - 产出:`execution-eval-report.md` + JSON
2. §三四个维度后加第 5 维度:**执行质量**(`references/audit-execution.md`)
   - 产物完整性(是否缺失必填字段)
   - 产物规范符合度(是否符合 schema)
   - 可运行性(代码类产物能否跑起来)
   - 与声明的符合度(description 声称的能力 vs 实际产出)
3. §五产出契约加第 3 种:`execution-eval-report.json`

**关键约束**:
- 执行后评测仍遵循"只读不写"
- 评测失败不阻断,标 WARNING 进报告

### C2. 各 skill 加产物自评步骤

**改动文件**:每个 skill 的 SKILL.md 末尾"质量检查清单"章节

**新增内容**:在每个 skill 的质量检查清单末尾加一条:
```
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
```

**范围**(优先加给高频 skill):
- generate-system-prd
- generate-prototype
- generate-html-pages
- game-spec
- game-art-spec
- game-code-forge
- implement-backend / implement-frontend / implement-data-layer

---

## 六、模块 D:Guardrail 层(新建 2 个 skill)

### D1. guardrail

**路径**:`guardrail/`

**frontmatter**:
```yaml
name: "guardrail"
description: "安全护栏 skill。在 skill 执行前后做安全检查:敏感路径保护/操作分级/diff 审查。当编排总纲或其他 skill 要执行变更操作时调用。"
```

**职责**:
- 执行前检查:目标路径是否在敏感清单(生产配置 / 数据库 / 核心代码)
- 操作分级:只读 / 低风险变更 / 高风险变更 / 禁止
- 执行后检查:diff 审查(是否删除了核心文件 / 是否改了配置)
- 产出 `guardrail-report.json`(检查结果 + 风险级别)

**scripts**:
- `scripts/check_paths.py`:检查路径是否在敏感清单
- `scripts/diff_review.py`:审查 diff(删除文件 / 大幅删减 / 配置变更)

**references**:
- `references/sensitive-paths.md`:敏感路径清单(可配置)
- `references/operation-levels.md`:操作分级规则

**关键约束**:
- **禁止级操作直接拦截**(返回 error,不允许执行)
- 高风险变更需用户二次确认
- 低风险变更记录到报告
- 敏感路径清单可由项目级配置覆盖

### D2. diff-reviewer

**路径**:`diff-reviewer/`

**frontmatter**:
```yaml
name: "diff-reviewer"
description: "变更审查 skill。审查产物变更的 diff,标红'删除核心文件''大幅删减''配置变更'等风险操作。当 skill 产出后或用户要'审查变更/检查 diff'时调用。"
```

**职责**:
- 接收变更前后的路径或 git diff
- 识别风险变更(删除文件 / 大幅删减 >30% / 配置文件变更 / 依赖变更)
- 产出 `diff-review-report.md`(风险变更清单 + 建议)

**references**:
- `references/diff-risk-rules.md`:风险变更识别规则

**关键约束**:
- 只读不写
- 与 `guardrail` 区别:`guardrail` 是前置拦截,`diff-reviewer` 是后置审查

---

## 七、模块 E:Memory 层(新建 2 个 skill)

### E1. project-knowledge-base

**路径**:`project-knowledge-base/`

**frontmatter**:
```yaml
name: "project-knowledge-base"
description: "项目知识库 skill。结构化存储团队规范/架构决策(ADR)/历史事故/代码规范,供其他 skill 执行前查询。当其他 skill 要获取项目上下文/历史决策/团队规范时调用。"
```

**职责**:
- 读写项目知识库(`.trae-cn/knowledge/`)
- 知识分类:team-conventions / adr / postmortems / code-standards
- 其他 skill 执行前可查询"该项目有哪些规范/历史事故"
- 产出/更新 `knowledge-base.json`(索引)+ 各知识文件

**scripts**:
- `scripts/kb_ops.py`:子命令 `query` / `add` / `update` / `list`

**references**:
- `references/kb-schema.md`:知识库 schema(分类 + 字段)

**关键约束**:
- 知识库为追加为主,删除需确认
- 查询接口供其他 skill 调用(如 `generate-system-prd` 执行前查团队规范)

### E2. failure-casebook

**路径**:`failure-casebook/`

**frontmatter**:
```yaml
name: "failure-casebook"
description: "失败案例库 skill。每次 skill 执行失败时自动记录'失败码+原因+修复方法',下次同名 skill 执行前先查避免重复踩坑。当 skill 执行失败或要查询历史失败案例时调用。"
```

**职责**:
- 接收失败信息(skill 名 + 失败码 + 原因 + 修复方法)
- 记录到 `.trae-cn/failures/`
- 其他 skill 执行前查询"该 skill 历史失败案例"
- 产出 `failure-casebook.json`(索引)+ 各案例文件

**scripts**:
- `scripts/casebook_ops.py`:子命令 `record` / `query` / `stats`

**references**:
- `references/casebook-schema.md`:案例 schema

**关键约束**:
- 自动记录(无需用户确认,失败即记)
- 查询接口供其他 skill 调用(如 `game-asset-forge` 执行前查历史生图失败)
- 案例保留 90 天,过期清理(可配置)

---

## 八、模块 F:编排总纲接入(扩展 2 个 skill)

### F1. product-pipeline-master 末尾加 Tool 确认点

**改动文件**:`product-pipeline-master/SKILL.md`

**改动位置**:§八执行顺序的阶段 5(门户)之后、阶段 6(实施规划)之前

**新增内容**:
```
5. 调用 `generate-portal`...
   - ⏸ 人工确认点 4(已有)
   - ⏸ **人工确认点 5(可选 Tool)**:门户完成后,AskUserQuestion 询问"是否自动提交产物到 Git / 部署到平台 / 跳过 Tool 操作"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit 产物目录,不 push)
     - 选"部署到平台" → 调用 `tool-deploy-ops`(需先 git commit)
     - 选"跳过" → 进入阶段 6
   - Tool 操作前过 `guardrail` 前置检查
6. (可选)调用 `plan-system-implementation`...
```

**同步更新**:
- §二流水线图加 Tool 确认点标注
- §九.1 加 Tool 确认点的规则(可选,不强制)
- §十质量门禁加 Tool 层检查项

### F2. game-forge-master 末尾加 Tool 确认点

**改动文件**:`game-forge-master/SKILL.md`

**改动位置**:§七执行顺序的阶段 5(集成)之后、阶段 6(polish)之前

**新增内容**:
```
5. 调用 `game-integrate`...
   - ⏸ 人工确认点 5(已有)
   - ⏸ **人工确认点 6(可选 Tool)**:集成完成后,AskUserQuestion 询问"是否自动提交产物到 Git / 部署到平台 / 跳过 Tool 操作"
     - 选"提交到 Git" → 调用 `tool-git-ops`
     - 选"部署到平台" → 调用 `tool-deploy-ops`
     - 选"跳过" → 进入阶段 6
   - Tool 操作前过 `guardrail` 前置检查
6. (可选)调用 `game-polish`...
```

**同步更新**:
- §二流水线图加 Tool 确认点标注
- §九.1 加 Tool 确认点的规则(可选,不强制)

---

## 九、模块 G:工作台索引更新(3 个文件)

### G1. WORKBENCH.md

**新增章节**:在"Skill 清单"后加"Agent 体系层"章节

**内容**:
```markdown
## Agent 体系层

除流水线 skill 外,工作台新增 AI Agent 体系层 skill:

### Tool 层(工具调用)
| Skill | 职责 |
|---|---|
| tool-git-ops | Git 操作封装(commit/branch/push/diff/log) |
| tool-ci-ops | CI/CD 操作(触发/查询/报告) |
| tool-deploy-ops | 部署操作(部署/回滚/健康检查) |
| tool-db-ops | 数据库操作(migrate/query/rollback,生产只读) |
| tool-monitor-ops | 监控查询(logs/metrics/trace,只读) |

### 工程 skill
| Skill | 职责 |
|---|---|
| code-review | 代码审查(4 维度 + 报告) |
| debug-fix | 调试修复(定位 + 修复) |
| refactor | 代码重构(不改功能) |

### 安全与评测
| Skill | 职责 |
|---|---|
| guardrail | 安全护栏(前置拦截) |
| diff-reviewer | 变更审查(后置审查) |
| skill-auditor | 质量审查(静态 + 执行后评测) |

### Memory 层
| Skill | 职责 |
|---|---|
| project-knowledge-base | 项目知识库(规范/ADR/事故) |
| failure-casebook | 失败案例库(避免重复踩坑) |
```

### G2. README.md

**同步更新**:
- "技能总览"加"6. Agent 体系层"
- "完整技能清单"表加 12 个新 skill 行

### G3. _shared/validate.ps1

**扩展校验范围**:
- 新增检查:`tool-*-ops` skill 必须有 `scripts/` 目录
- 新增检查:`guardrail` / `diff-reviewer` 不得修改被审查文件(检查 SKILL.md 含"只读"字样)
- 新增检查:新 skill 的 frontmatter 必须有 `name` + `description`

---

## 十、实施顺序与依赖

```
第 1 批(无依赖,可并行):
  A1. tool-git-ops
  A4. tool-db-ops
  A5. tool-monitor-ops
  D1. guardrail
  E2. failure-casebook

第 2 批(依赖第 1 批):
  A2. tool-ci-ops(依赖 tool-git-ops 模式参考)
  A3. tool-deploy-ops(依赖 tool-git-ops 模式参考)
  D2. diff-reviewer(依赖 guardrail 模式参考)
  E1. project-knowledge-base(依赖 failure-casebook 模式参考)

第 3 批(依赖第 2 批):
  B1. code-review
  B2. debug-fix
  B3. refactor

第 4 批(依赖第 3 批):
  C1. 扩展 skill-auditor(加执行后评测模式)
  C2. 各 skill 加产物自评步骤

第 5 批(依赖第 4 批):
  F1. product-pipeline-master 接入
  F2. game-forge-master 接入

第 6 批(最后):
  G1. WORKBENCH.md 更新
  G2. README.md 更新
  G3. _shared/validate.ps1 扩展
```

---

## 十一、验证步骤

### 11.1 每个 skill 的验证

新建 skill 后验证:
1. frontmatter 格式正确(name + description)
2. SKILL.md 行数 ≤500
3. scripts/ 下的脚本能运行(`python scripts/xxx.py --help`)
4. agents/openai.yaml 配置正确
5. 运行 `powershell -File _shared/validate.ps1` 通过

### 11.2 编排接入验证

product-pipeline-master / game-forge-master 改动后验证:
1. §二流水线图含 Tool 确认点标注
2. §七/§八执行顺序含 Tool 确认点描述
3. §九.1 含 Tool 确认点规则
4. 跑一次完整流水线,确认 Tool 确认点出现且可选"跳过"

### 11.3 整体验证

全部完成后:
1. `powershell -File _shared/validate.ps1` 全部通过
2. `skill-auditor` 流水线审查模式跑 product-pipeline-master 流水线,无 CRITICAL
3. WORKBENCH.md / README.md 索引与实际 skill 目录一致
4. 新 skill 能被宿主正确识别和调用

---

## 十二、假设与决策

### 12.1 假设

1. 宿主 Trae runtime 支持调用 scripts/ 下的 Python 脚本(已验证:rd-init / ruanzhu-doc-generator 均用此模式)
2. 宿主支持 AskUserQuestion 工具(已验证:编排总纲已用)
3. 新 skill 遵循现有 frontmatter 格式(name + description,无 version 字段——与现有 38 个 skill 一致)
4. Tool skill 的 scripts 用 Python(与现有 scripts 模式一致)
5. 编排总纲的 Tool 确认点是可选的(用户可选"跳过"),不破坏现有流水线

### 12.2 决策

1. **Tool 层用 skill 而非 MCP**:因为现有工作台全是 skill 模式,用 skill 保持一致性;MCP 是另一条路线,不在本次范围
2. **Tool 确认点是可选的**:避免强制每个项目都走 Git/部署,保持轻量
3. **guardrail 与 diff-reviewer 分两个 skill**:前置拦截 vs 后置审查职责不同,分开更清晰
4. **skill-auditor 扩展而非新建**:已有 4 模式 4 维度,加第 5 模式第 5 维度复用现有架构
5. **failure-casebook 自动记录**:失败即记,无需用户确认,避免遗漏
6. **各 skill 产物自评是可选的**:不强制每个 skill 都跑自评,高频 skill 优先
7. **不新建 model-router / task-planner / workflow-runtime / codebase-rag**:这些是第 2-4 阶段,本次不做

### 12.3 不做(明确排除)

- Model 层(model-router / prompt-registry):宿主已做路由,本次不做
- Planning 层(task-planner / replanner):成本高,第 3 阶段做
- Workflow 可执行化(抽 workflow.yaml):改造成本高,第 3 阶段做
- Agent Runtime(skill-runtime):依赖宿主能力,第 3 阶段做
- Context 层(codebase-rag):宿主已有 SearchCodebase,第 4 阶段做
- Data 层(skill-usage-tracker):依赖 Data 基础设施,第 4 阶段做

---

## 十三、剩余工作执行计划(2026-08-06 制定)

> **进度基准**:第 1-3 批已完成(12 个新 skill 创建 + skill-auditor 已扩展执行后评测模式);第 4 批 C1 已完成,C2 待执行;第 5-6 批未启动。

### 13.1 进度核对

| 批次 | 计划项 | 完成状态 | 证据 |
|---|---|---|---|
| 第 1 批 | A1 tool-git-ops / A4 tool-db-ops / A5 tool-monitor-ops / D1 guardrail / E2 failure-casebook | ✅ 已完成 | 5 个 skill 目录均存在(SKILL.md + scripts/ + agents/openai.yaml) |
| 第 2 批 | A2 tool-ci-ops / A3 tool-deploy-ops / D2 diff-reviewer / E1 project-knowledge-base | ✅ 已完成 | 4 个 skill 目录均存在 |
| 第 3 批 | B1 code-review / B2 debug-fix / B3 refactor | ✅ 已完成 | 3 个 skill 目录均存在 |
| 第 4 批 C1 | 扩展 skill-auditor 加执行后评测模式 + audit-execution.md | ✅ 已完成 | SKILL.md 已含第 5 模式 + 第 5 维度;references/audit-execution.md 存在 |
| 第 4 批 C2 | 9 个高频 skill 加产物自评步骤 | ⏳ 待执行 | 各目标 skill 的质量章节末尾未含自评项 |
| 第 5 批 | F1 product-pipeline-master 接入 + F2 game-forge-master 接入 | ⏳ 待执行 | 两个总纲均未含 Tool 确认点 |
| 第 6 批 | G1 WORKBENCH.md / G2 README.md / G3 _shared/validate.ps1 | ⏳ 待执行 | 索引文件未含 12 个新 skill;validate.ps1 未含新规则 |

### 13.2 批次 D1:第 4 批 C2 — 9 个 skill 加产物自评

**目标**:在每个目标 skill 的质量章节末尾追加自评项,形成 Evaluation 闭环的"自查"入口。

**目标 skill 与插入位置**:

| # | skill | 质量章节名 | 章节末尾行号 | 追加内容 |
|---|---|---|---|---|
| 1 | generate-system-prd | §五 质量标准 | 行 190 后 | `- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)` |
| 2 | generate-prototype | §五 质量标准 | 行 290 后 | 同上 |
| 3 | generate-html-pages | §8.4 通用质量标准 | 待确认 | 同上 |
| 4 | game-spec | §六 质量检查清单 | 行 401 后 | 同上 |
| 5 | game-art-spec | §八 质量检查清单 | 待确认 | 同上 |
| 6 | game-code-forge | §十二 质量检查清单 | 待确认 | 同上 |
| 7 | implement-backend | (无独立质量章节) | 末尾追加 | 追加 `## 末尾:质量检查清单` 章节 + 自评项 |
| 8 | implement-frontend | (无独立质量章节) | 末尾追加 | 同上 |
| 9 | implement-data-layer | (无独立质量章节) | 末尾追加 | 同上 |

**统一追加文案**(在每个 skill 质量章节末尾):

```markdown
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
```

**特殊情况处理**:
- implement-* 三个 skill 当前无独立"质量检查清单"章节,需在 SKILL.md 末尾新增章节 `## 末尾:质量检查清单`,内容含一条自评项 + (如已有其他质量约束则顺带整理)
- generate-html-pages 是路由器,主要质量标准在子 skill;只在 §8.4 通用质量标准末尾追加自评项(指向"调用本 skill 后,产物为 build-report.json,自评 build-report.json 的字段完整性")

**执行步骤**:
1. 依次读取 9 个目标 skill 的 SKILL.md,定位质量章节末尾行号
2. 用 Edit 工具在末尾追加自评项(对 implement-* 需新增章节)
3. 运行 `powershell -File _shared/validate.ps1` 确保不破坏现有结构

**验证**:
- 9 个 skill 的质量章节末尾均含"产物自评"项
- validate.ps1 退出码 0
- SKILL.md 行数未超阈值(各 skill ≤500 行)

### 13.3 批次 D2:第 5 批 — 编排总纲接入 Tool 确认点

**目标**:在两个编排总纲的"门户/集成"阶段后,加可选的 Tool 确认点,打通"产出→提交→部署"闭环。

#### D2.1 product-pipeline-master 接入

**改动文件**:`product-pipeline-master/SKILL.md`

**改动点 1:§二流水线图(行 56-58 区域)**

在阶段 5(generate-portal)与阶段 6(plan-system-implementation)之间插入:

```
       ↓
⏸ 人工确认点 5 (可选 Tool,AskUserQuestion: 提交 Git / 部署平台 / 跳过)
       ↓ Tool 操作前过 guardrail 前置检查
       ↓
plan-system-implementation → 实施蓝图 + 任务板 + 追溯表
```

**改动点 2:§八执行顺序(行 241-243 区域)**

在阶段 5 末尾、阶段 6 之前插入:

```markdown
   - ⏸ **人工确认点 5(可选 Tool)**:门户完成后,AskUserQuestion 询问"是否自动提交产物到 Git / 部署到平台 / 跳过 Tool 操作"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit 产物目录,默认不 push)
     - 选"部署到平台" → 调用 `tool-deploy-ops`(需先 git commit)
     - 选"跳过" → 进入阶段 6
   - Tool 操作前过 `guardrail` 前置检查(检查 output/ 路径是否在敏感清单)
```

**改动点 3:§九.1 人工确认机制(行 284-289 例外区域)**

在"例外"列表后追加:

```markdown
- 确认点 5(可选 Tool)是**可选**的:即使用户在确认点 4 选了"流水线完成",也可在产物已落地后单独触发 Tool 操作;反之,确认点 5 默认不强制出现,仅在用户明确要"提交/部署"时触发
```

**改动点 4:§十质量门禁(行 296-302 表格)**

在表格末尾追加一行:

```markdown
| Tool(可选) | `tool-git-ops` 产出 git-ops-report.json;`tool-deploy-ops` 产出 deploy-ops-report.json;guardrail 前置检查通过 |
```

#### D2.2 game-forge-master 接入

**改动文件**:`game-forge-master/SKILL.md`

**改动点 1:§二流水线图**

在阶段 5(game-integrate)与阶段 6(game-polish)之间插入 Tool 确认点标注(同 D2.1 模式)。

**改动点 2:§七执行顺序**

在阶段 5 末尾、阶段 6 之前插入(同 D2.1 模式)。

**改动点 3:§九.1 人工确认机制**

追加 Tool 确认点为可选项的说明。

**执行步骤**:
1. 读取 product-pipeline-master/SKILL.md 全文,定位 4 个改动点
2. 依次用 Edit 工具完成 4 处改动
3. 读取 game-forge-master/SKILL.md 全文,定位对应改动点
4. 用 Edit 工具完成 game-forge-master 改动
5. 运行 validate.ps1 验证

**验证**:
- 两个总纲 §二流水线图均含"⏸ 人工确认点 5(可选 Tool)"标注
- 两个总纲执行顺序章节均含 Tool 确认点描述
- 两个总纲 §九.1 均含 Tool 确认点为可选的说明
- product-pipeline-master §十质量门禁表含 Tool 行
- validate.ps1 退出码 0

### 13.4 批次 D3:第 6 批 — 索引与校验扩展

#### D3.1 WORKBENCH.md 更新

**改动**:在"Skill 清单"章节后新增"Agent 体系层"章节,列出 12 个新 skill。

**新增章节内容**(详见 §九 G1 的草稿,精确到表格):

```markdown
## Agent 体系层

除流水线 skill 外,工作台新增 AI Agent 体系层 skill:

### Tool 层(工具调用)
| Skill | 职责 |
|---|---|
| tool-git-ops | Git 操作封装(commit/branch/push/diff/log) |
| tool-ci-ops | CI/CD 操作(触发/查询/报告) |
| tool-deploy-ops | 部署操作(部署/回滚/健康检查) |
| tool-db-ops | 数据库操作(migrate/query/rollback,生产只读) |
| tool-monitor-ops | 监控查询(logs/metrics/trace,只读) |

### 工程 skill
| Skill | 职责 |
|---|---|
| code-review | 代码审查(4 维度 + 报告) |
| debug-fix | 调试修复(定位 + 修复) |
| refactor | 代码重构(不改功能) |

### 安全与评测
| Skill | 职责 |
|---|---|
| guardrail | 安全护栏(前置拦截) |
| diff-reviewer | 变更审查(后置审查) |
| skill-auditor | 质量审查(静态 + 执行后评测) |

### Memory 层
| Skill | 职责 |
|---|---|
| project-knowledge-base | 项目知识库(规范/ADR/事故) |
| failure-casebook | 失败案例库(避免重复踩坑) |
```

#### D3.2 README.md 更新

**改动 1**:在"技能总览"加第 6 层"Agent 体系层"。

**改动 2**:在"完整技能清单"表中加 12 行:

```markdown
| tool-git-ops | Git 工具层 | 封装 git add/commit/branch/push/diff/log |
| tool-ci-ops | CI/CD 工具层 | 触发 CI / 查询构建状态 / 读取测试报告 |
| tool-deploy-ops | 部署工具层 | 部署到 GitHub Pages/Vercel/Netlify/CloudBase/COS |
| tool-db-ops | 数据库工具层 | migrate/query/rollback,生产环境只读 |
| tool-monitor-ops | 监控工具层 | logs/metrics/trace 查询,纯只读 |
| code-review | 代码审查 | 4 维度审查 + 修复建议 |
| debug-fix | 调试修复 | 接收错误日志定位根因 + 修复 |
| refactor | 代码重构 | 不改功能的前提下改善结构 |
| guardrail | 安全护栏 | 敏感路径保护 + 操作分级 + diff 审查 |
| diff-reviewer | 变更审查 | 后置审查产物 diff 的风险变更 |
| project-knowledge-base | 项目知识库 | 团队规范/ADR/事故/代码规范 |
| failure-casebook | 失败案例库 | 自动记录失败码 + 修复方法 |
```

#### D3.3 _shared/validate.ps1 扩展

**新增检查项 1:Tool skill 必须有 scripts/**

在 validate.ps1 的"---------- 汇总 ----------"之前追加:

```powershell
# ---------- 5. Tool skill 必须有 scripts/ 目录 ----------
$toolSkills = @('tool-git-ops','tool-ci-ops','tool-deploy-ops','tool-db-ops','tool-monitor-ops')
$toolMissing = 0
foreach ($name in $toolSkills) {
    $dir = Join-Path $ws $name
    if (-not (Test-Path (Join-Path $dir 'scripts'))) {
        Fail "Tool skill 缺失 scripts/ 目录:$name"
        $toolMissing++
    }
}
if ($toolMissing -eq 0) { Pass "全部 Tool skill 含 scripts/ 目录(共 $($toolSkills.Count) 个)" }
```

**新增检查项 2:guardrail / diff-reviewer 含"只读"字样**

```powershell
# ---------- 6. 审查类 skill 必须声明"只读不写" ----------
$readonlySkills = @('guardrail','diff-reviewer','skill-auditor','code-review')
$roMissing = 0
foreach ($name in $readonlySkills) {
    $md = Join-Path $ws "$name/SKILL.md"
    if (Test-Path $md) {
        $c = Get-Content $md -Raw -Encoding UTF8
        if ($c -notmatch '只读不写|只读') {
            Fail "$name/SKILL.md 未声明'只读'约束"
            $roMissing++
        }
    }
}
if ($roMissing -eq 0) { Pass "全部审查类 skill 声明了'只读'约束(共 $($readonlySkills.Count) 个)" }
```

**新增检查项 3:新 skill frontmatter 必填**

```powershell
# ---------- 7. 新 skill frontmatter 必填 name + description ----------
$newSkills = @('tool-git-ops','tool-ci-ops','tool-deploy-ops','tool-db-ops','tool-monitor-ops','code-review','debug-fix','refactor','guardrail','diff-reviewer','project-knowledge-base','failure-casebook')
$fmMissing = 0
foreach ($name in $newSkills) {
    $md = Join-Path $ws "$name/SKILL.md"
    if (Test-Path $md) {
        $head = Get-Content $md -TotalCount 10 -Encoding UTF8 -ErrorAction SilentlyContinue
        $joined = $head -join "`n"
        if ($joined -notmatch '^name:\s*"?.+"?' -or $joined -notmatch '^description:\s*"?.+"?') {
            Fail "$name/SKILL.md frontmatter 缺失 name 或 description"
            $fmMissing++
        }
    }
}
if ($fmMissing -eq 0) { Pass "全部新 skill frontmatter 含 name + description(共 $($newSkills.Count) 个)" }
```

**执行步骤**:
1. 读取 WORKBENCH.md 全文,定位"Skill 清单"章节,在适当位置插入"Agent 体系层"章节
2. 读取 README.md 全文,完成 2 处改动
3. 读取 _shared/validate.ps1 全文,在"汇总"前插入 3 个新检查项
4. 运行扩展后的 validate.ps1 验证全部通过

**验证**:
- WORKBENCH.md 含"Agent 体系层"章节 + 12 个新 skill 行
- README.md 完整技能清单含 12 行新 skill
- validate.ps1 输出全部 PASS,退出码 0

### 13.5 批次 D4:整体验证与回归

**最终验证清单**:

1. 运行 `powershell -File _shared/validate.ps1`,退出码 0
2. 用 `skill-auditor` 跑流水线审查模式审查 `product-pipeline-master` 流水线,无 CRITICAL
3. 用 `skill-auditor` 跑流水线审查模式审查 `game-forge-master` 流水线,无 CRITICAL
4. WORKBENCH.md / README.md 索引与实际 skill 目录一致(对照 LS 输出)
5. 抽查 3 个新 skill 的 frontmatter 格式正确(name + description)
6. 抽查 product-pipeline-master §二/§八/§九.1/§十 均含 Tool 确认点内容
7. 抽查 9 个高频 skill 质量章节末尾均含"产物自评"项

### 13.6 执行顺序与依赖

```
批次 D1(第 4 批 C2):9 个 skill 加产物自评
       ↓ (无依赖,可独立完成)
批次 D2(第 5 批):两个总纲接入 Tool 确认点
       ↓ (无依赖,可独立完成)
批次 D3(第 6 批):WORKBENCH.md / README.md / validate.ps1
       ↓ (依赖 D1+D2 完成才能跑最终验证)
批次 D4:整体验证与回归
```

**说明**:D1 与 D2 之间无强依赖,可并行执行;D3 必须在 D1+D2 完成后,因为 validate.ps1 的新检查项要校验 D1+D2 的产物;D4 是最终回归,必须最后执行。

### 13.7 人工确认点

按用户偏好"每一步都要人工确认",本剩余工作执行计划设以下确认点:

| 确认点 | 触发时机 | 简报内容 | 选项 |
|---|---|---|---|
| ⏸ 确认点 A | D1(产物自评)完成 | 9 个 skill 已加自评项 + validate.ps1 结果 | 进入 D2 / 回退修复 / 终止 |
| ⏸ 确认点 B | D2(总纲接入)完成 | 两个总纲已含 Tool 确认点 + validate.ps1 结果 | 进入 D3 / 回退修复 / 终止 |
| ⏸ 确认点 C | D3(索引+校验)完成 | 索引文件已更新 + validate.ps1 全 PASS | 进入 D4 整体验证 / 回退修复 / 终止 |
| ⏸ 确认点 D | D4(整体验证)完成 | 流水线审查无 CRITICAL + 索引一致 | 升级完成 / 回退修复 |

每个确认点通过 AskUserQuestion 询问,不自动连续执行下一批次。

### 13.8 不在本次剩余计划范围

以下属于"第 2-4 阶段"工作,不在本剩余执行计划内:

- Model 层(model-router / prompt-registry)
- Planning 层(task-planner / replanner)
- Workflow 可执行化(workflow.yaml + workflow-runtime)
- Agent Runtime(skill-runtime)
- Context 层(codebase-rag)
- Data 层(skill-usage-tracker)

这些在本次升级完成后另行规划。

---

## 十四、第二阶段升级计划(Phase 2:自主运行能力)

> **进度基准**:
> - 第一阶段(§一~§十三)已完整闭环——12 个新 skill 已建 + skill-auditor 已扩展执行后评测 + 9 个 skill 已加产物自评 + 两个总纲已接入可选 Tool 确认点 + validate.ps1 已扩展 3 项检查;D4 整体验证全 PASS(2026-08-06)。
> - **第二阶段(§十四)已闭环(2026-08-06)**——4 个新 skill 已建(skill-runtime / task-planner / replanner / workflow-runtime)+ skill-auditor 加第 6 维度 + failure-casebook 加 auto-query 接口 + 两个总纲产出 workflow.yaml + 索引文件更新 + validate.ps1 扩展检查 8/9;P2 整体验证全 PASS(9 项检查通过,53 个 skill 目录就绪)。
>
> **第二阶段主题**:让 Agent 体系从"工具齐全"升级为"自主运行"——补齐 Planning / Workflow 可执行化 / Agent Runtime / Evaluation 深化 四大运行时能力。

### 14.1 12 维度覆盖度评估(第一阶段后)

| # | 维度 | 第一阶段前 | 第一阶段后 | 第二阶段目标 | 是否纳入 Phase 2 |
|---|---|---|---|---|---|
| 1 | Model | ★★☆☆☆(宿主路由) | ★★☆☆☆(不变) | 保持 | ✗ 宿主能力 |
| 2 | Skill | ★★★★☆(38个) | ★★★★★(50个) | 保持 | ✗ 已饱和 |
| 3 | Tool | ★☆☆☆☆ | ★★★★★(5个 tool-ops) | 保持 | ✗ 已闭环 |
| 4 | Planning | ★★☆☆☆(总纲裁剪) | ★★☆☆☆(不变) | ★★★★☆(task-planner + replanner) | ✓ **纳入** |
| 5 | Memory | ★★☆☆☆ | ★★★★☆(kb + casebook) | 保持 | ✗ 已闭环 |
| 6 | Context | ★★☆☆☆(宿主 SearchCodebase) | ★★☆☆☆(不变) | 保持 | ✗ 与宿主重叠,Phase 3 |
| 7 | Workflow | ★★★☆☆(文档型编排) | ★★★☆☆(不变) | ★★★★★(workflow-runtime 可执行化) | ✓ **纳入** |
| 8 | Agent Runtime | ★☆☆☆☆ | ★☆☆☆☆(不变) | ★★★★☆(skill-runtime 契约) | ✓ **纳入** |
| 9 | Evaluation | ★★☆☆☆ | ★★★★☆(执行后评测) | ★★★★★(加运行时契约维度) | ✓ **纳入(深化)** |
| 10 | Data | ★☆☆☆☆ | ★☆☆☆☆(不变) | ★★★☆☆(usage-tracker) | ✗ 依赖基础设施,Phase 3 |
| 11 | Guardrail | ★☆☆☆☆ | ★★★★☆(guardrail + diff-reviewer) | 保持 | ✗ 已闭环 |
| 12 | Human Feedback | ★★☆☆☆ | ★★★★☆(人工确认点) | 保持 | ✗ 已闭环 |

**结论**:第二阶段聚焦 4 个维度(Planning / Workflow / Agent Runtime / Evaluation 深化),新建 4 个 skill + 扩展 4 个现有 skill + 更新 3 个索引校验文件。

### 14.2 改造方案总览

```
模块 H:Agent Runtime 层(1 个新 skill,定义运行时契约)
  skill-runtime
       ↓ 契约被所有 skill 遵循,被 workflow-runtime 校验
模块 I:Planning 层(2 个新 skill)
  task-planner → task-tree.json
       ↓ 依赖
  replanner → 动态调整 task-tree
       ↓ 被 workflow-runtime 调度
模块 J:Workflow 可执行化(1 个新 skill + 2 个总纲扩展)
  workflow-runtime → 把编排总纲的执行顺序转为可执行 workflow.yaml
       ↓ 消费
  product-pipeline-master 扩展:产出 workflow.yaml
  game-forge-master 扩展:产出 workflow.yaml
       ↓ 受评测
模块 K:Evaluation 深化(2 个 skill 扩展)
  skill-auditor 加第 6 维度"运行时契约"
  failure-casebook 加"自动查询"接口(skill 执行前自动查历史失败)
       ↓
模块 L:索引与校验(3 个文件)
  WORKBENCH.md / README.md / validate.ps1
```

---

### 14.3 模块 H:Agent Runtime 层(新建 1 个 skill)

#### H1. skill-runtime

**路径**:`skill-runtime/`

**frontmatter**:
```yaml
name: "skill-runtime"
description: "Agent Runtime 层 skill。定义 skill 运行时元数据契约(输入校验 schema / 超时 / 重试策略 / 降级规则),所有 skill 声明 runtime.yaml,被 workflow-runtime 与 skill-auditor 校验。当要统一 skill 运行时行为或校验 skill 是否符合运行时契约时调用。"
```

**职责**:
- 定义 `runtime.yaml` 规范(每个 skill 可选声明,声明后受校验)
- 字段:`timeout`(秒) / `retry`(次数+退避策略) / `inputs`(JSON Schema 校验) / `outputs`(产物路径) / `degrade`(降级策略引用)
- 提供 `scripts/validate_runtime.py` 校验单个 skill 的 runtime.yaml 是否符合规范
- 产出 `runtime-contract-report.json`(校验结果)

**scripts**:
- `scripts/validate_runtime.py`:子命令 `check`(校验单 skill) / `scan`(扫描全部 skill)

**references**:
- `references/runtime-schema.md`:runtime.yaml 字段规范 + JSON Schema
- `references/degrade-patterns.md`:常见降级模式(占位图/静音/strict:false/跳过阶段)

**关键约束**:
- runtime.yaml 是**可选**的(不强制所有 skill 立即声明,渐进式接入)
- 但一旦声明,必须符合 schema,否则 validate.ps1 FAIL
- 不修改 skill 本身逻辑,只定义元数据契约
- 默认值:timeout=300s / retry=0 / 无输入校验 / 无降级

**runtime.yaml 示例**:
```yaml
# game-asset-forge/runtime.yaml
timeout: 600          # AI 生图较慢,10 分钟
retry:
  max: 2
  backoff: exponential  # 指数退避
inputs:
  - name: ASSET_MANIFEST.json
    schema: ../game-art-spec/references/asset-manifest.schema.json
    required: true
outputs:
  - path: assets/
    type: directory
  - path: docs/ASSET_ISSUES.md
    type: file
    optional: true
degrade:
  - trigger: 生图失败
    action: 占位图(纯色+文字标识)
    target: assets/role/*/*.png
```

---

### 14.4 模块 I:Planning 层(新建 2 个 skill)

#### I1. task-planner

**路径**:`task-planner/`

**frontmatter**:
```yaml
name: "task-planner"
description: "通用任务规划器 skill。把复杂需求拆解为子任务树+依赖关系+优先级,产出 task-tree.json。当编排总纲外有复杂需求需规划、或用户要'拆解任务/规划执行步骤'时调用。区别于编排总纲的'流水线阶段裁剪',本 skill 面向任意任务的通用规划。"
```

**职责**:
- 接收需求描述 + 可选上下文(已有产物/约束)
- 拆解为子任务树(WBS):根任务 → 子任务 → 叶子任务
- 标注依赖关系(前置/后置/并行)
- 标注优先级(P0/P1/P2)与预估复杂度
- 产出 `task-tree.json`(机读) + `task-plan.md`(人读)

**scripts**:
- `scripts/plan_tasks.py`:拆解算法 + 依赖拓扑排序

**references**:
- `references/wbs-patterns.md`:WBS 拆解模式(按功能/按层/按时序)
- `references/dependency-rules.md`:依赖识别规则(数据依赖/控制依赖/资源依赖)

**关键约束**:
- 拆解粒度:叶子任务可在 1 次 skill 调用内完成
- 不执行任务,只规划(执行交 workflow-runtime 或编排总纲)
- 与编排总纲的区别:总纲是"固定流水线裁剪",task-planner 是"任意需求动态拆解"
- 产出格式与 `plan-system-implementation` 的 task-board.json 兼容(可互转)

**task-tree.json schema 摘要**:
```json
{
  "root": { "id": "T0", "title": "...", "complexity": "..." },
  "tasks": [
    {
      "id": "T1", "title": "...", "priority": "P0",
      "depends_on": ["T2"], "parallel_with": ["T3"],
      "assigned_skill": "game-blueprint",
      "est_complexity": "★★"
    }
  ]
}
```

#### I2. replanner

**路径**:`replanner/`

**frontmatter**:
```yaml
name: "replanner"
description: "重规划器 skill。当子任务失败或上下文变化时,动态调整 task-tree(重排/跳过/拆分/合并)。当 workflow-runtime 检测到任务失败或用户变更需求时调用,产出调整后的 task-tree 与变更说明。"
```

**职责**:
- 接收原 task-tree.json + 失败信息(或变更需求)
- 识别受影响的子任务(直接依赖 + 间接依赖)
- 生成调整方案(重排/跳过/拆分/合并/降级)
- 产出 `task-tree.v2.json`(调整后) + `replan-report.md`(变更说明)

**references**:
- `references/impact-analysis.md`:影响传播分析(依赖图遍历)
- `references/replan-strategies.md`:重规划策略(回退N步/绕过/降级/人工接管)

**关键约束**:
- 只调整规划,不执行(执行交 workflow-runtime)
- 最多重规划 3 轮(超过转人工)
- 保留原 task-tree 版本(可回退)
- 失败信息来源:failure-casebook 查询 / workflow-runtime 上报

---

### 14.5 模块 J:Workflow 可执行化(新建 1 个 skill + 扩展 2 个总纲)

#### J1. workflow-runtime

**路径**:`workflow-runtime/`

**frontmatter**:
```yaml
name: "workflow-runtime"
description: "工作流执行器 skill。把编排总纲的执行顺序转为可执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度。当要把流水线从'文档描述'升级为'可执行工作流',或要驱动 task-tree 执行时调用。本身是执行引擎,不产出业务文件。"
```

**职责**:
- 读取编排总纲的执行顺序章节,转为 `workflow.yaml`(机读工作流定义)
- 或读取 task-planner 的 task-tree.json,转为 workflow.yaml
- 执行 workflow.yaml:按顺序调用各 skill,处理依赖/并行/暂停点
- 支持:暂停(人工确认点) / 恢复 / 跳过(裁剪) / 回退(失败重跑) / 并行调度
- 失败时调 replanner 重规划
- 产出 `workflow-exec-report.json`(执行轨迹 + 各阶段状态)

**scripts**:
- `scripts/compile_workflow.py`:把编排总纲的执行顺序章节编译为 workflow.yaml
- `scripts/run_workflow.py`:执行 workflow.yaml(按步骤调用 skill,处理暂停/恢复)

**references**:
- `references/workflow-yaml-schema.md`:workflow.yaml 规范
- `references/execution-semantics.md`:执行语义(暂停/恢复/跳过/回退/并行的定义)
- `references/skill-invocation.md`:skill 调用约定(如何触发下游 skill)

**关键约束**:
- 不替代编排总纲:总纲负责"做什么决策"(引擎选择/阶段裁剪),workflow-runtime 负责"怎么执行"(调度/暂停/恢复)
- 与人工确认点兼容:workflow.yaml 中的 pause 节点对应 AskUserQuestion
- 失败不阻塞:失败时记录 + 调 replanner + 继续或暂停(取决于失败严重度)
- 保留执行轨迹:每步执行结果写入 exec-report,可追溯

**workflow.yaml 示例**(由 game-forge-master §七编译而来):
```yaml
name: game-forge-pipeline
source: game-forge-master/SKILL.md §七
steps:
  - id: s1
    skill: game-blueprint
    outputs: [docs/GAME_BLUEPRINT.md]
    next: s1_gate
  - id: s1_gate
    skill: game-quality-gate
    args: { gate: 0 }
    on_fail: { action: back_to, target: s1 }
    next: s1_confirm
  - id: s1_confirm
    type: pause
    confirm: { question: "进入规格设计 / 回退修改蓝图 / 终止", options: [next, back, abort] }
    next: s2
  - id: s4a
    skill: game-asset-forge
    parallel_with: s4b
    runtime: game-asset-forge/runtime.yaml  # 引用运行时契约
  - id: s4b
    skill: game-code-forge
    parallel_with: s4a
  - id: s5_tool
    type: pause
    confirm: { question: "提交 Git / 部署平台 / 跳过", optional: true }
    on_select:
      git: { skill: tool-git-ops }
      deploy: { skill: tool-deploy-ops }
      skip: { next: s6 }
```

#### J2. product-pipeline-master 扩展

**改动文件**:`product-pipeline-master/SKILL.md`

**新增内容**:
- §八执行顺序末尾新增:"可选产出 workflow.yaml,交 workflow-runtime 驱动执行"
- 新增产物:`workflow.yaml`(可选,由 workflow-runtime 编译总纲执行顺序生成)
- §九.1 人工确认机制加说明:"workflow-runtime 模式下,pause 节点自动触发 AskUserQuestion,与现有人工确认点一一对应"

#### J3. game-forge-master 扩展

**改动文件**:`game-forge-master/SKILL.md`

**新增内容**(同 J2 模式):
- §七执行顺序末尾新增 workflow.yaml 产出说明
- 新增产物:`workflow.yaml`(可选)
- §九.1 加 workflow-runtime 兼容说明

---

### 14.6 模块 K:Evaluation 深化(扩展 2 个 skill)

#### K1. skill-auditor 加第 6 维度"运行时契约"

**改动文件**:`skill-auditor/SKILL.md` + 新增 `references/audit-runtime.md`

**新增内容**:
1. §二审查模式后加说明:"运行时契约审查(校验 runtime.yaml 是否符合 skill-runtime 规范)"
2. §三四维度后加第 6 维度:**运行时契约**(`references/audit-runtime.md`)
   - runtime.yaml 存在性(声明的 skill 是否有 runtime.yaml)
   - schema 符合度(字段是否符合 skill-runtime 规范)
   - 契约一致性(timeout/retry/inputs/outputs 与 SKILL.md 声明一致)
   - 降级策略有效性(degrade 引用的策略是否存在)
3. §五产出契约加第 4 种:`runtime-audit-report.json`

#### K2. failure-casebook 加"自动查询"接口

**改动文件**:`failure-casebook/SKILL.md`

**新增内容**:
- 新增子命令 `auto-query`:skill 执行前自动查询该 skill 的历史失败案例
- 接入点:workflow-runtime 在调用 skill 前先调 failure-casebook auto-query,有匹配失败码时注入到 skill 上下文
- 新增字段:`preventive_hints`(预防提示,基于历史失败给当前执行的建议)

---

### 14.7 模块 L:索引与校验更新(3 个文件)

#### L1. WORKBENCH.md / README.md

新增"Phase 2 运行时层"章节,列出 4 个新 skill:
- skill-runtime(Agent Runtime)
- task-planner / replanner(Planning)
- workflow-runtime(Workflow 可执行化)

#### L2. _shared/validate.ps1 扩展

新增检查项:
- 检查 8:声明了 runtime.yaml 的 skill,其内容必须符合 skill-runtime schema
- 检查 9:编排总纲若产出 workflow.yaml,必须可被 workflow-runtime 解析

---

### 14.8 实施顺序与依赖

```
第 1 批(无依赖,可并行):
  H1. skill-runtime(定义契约,先行)
  I1. task-planner(独立)

第 2 批(依赖第 1 批):
  I2. replanner(依赖 task-planner 的 task-tree 格式)
  J1. workflow-runtime(依赖 skill-runtime 契约 + task-planner 格式)

第 3 批(依赖第 2 批):
  J2. product-pipeline-master 扩展(产出 workflow.yaml)
  J3. game-forge-master 扩展(产出 workflow.yaml)

第 4 批(依赖第 2 批):
  K1. skill-auditor 加运行时契约维度
  K2. failure-casebook 加自动查询接口

第 5 批(最后):
  L1. WORKBENCH.md / README.md 更新
  L2. validate.ps1 扩展
  L3. 最终验证(skill-auditor 流水线审查 + workflow-runtime 试跑)
```

---

### 14.9 人工确认点

按用户偏好"每一步都要人工确认",第二阶段设以下确认点:

| 确认点 | 触发时机 | 简报内容 | 选项 |
|---|---|---|---|
| ⏸ P2-A | 第 1 批完成 | skill-runtime 契约定义 + task-planner 拆解能力 + validate.ps1 结果 | 进入第 2 批 / 回退修复 / 终止 |
| ⏸ P2-B | 第 2 批完成 | replanner 重规划 + workflow-runtime 执行引擎 + 试跑结果 | 进入第 3 批 / 回退修复 / 终止 |
| ⏸ P2-C | 第 3 批完成 | 两个总纲已产出 workflow.yaml + workflow-runtime 驱动试跑 | 进入第 4 批 / 回退修复 / 终止 |
| ⏸ P2-D | 第 4 批完成 | skill-auditor 第 6 维度 + failure-casebook 自动查询 | 进入第 5 批 / 回退修复 / 终止 |
| ⏸ P2-E | 第 5 批完成 | 索引更新 + validate.ps1 全 PASS + 流水线审查无 CRITICAL | 第二阶段完成 / 回退修复 |

每个确认点通过 AskUserQuestion 询问,不自动连续执行下一批次。

---

### 14.10 验证步骤

#### 每个 skill 的验证
1. frontmatter 格式正确(name + description)
2. SKILL.md 行数 ≤500
3. scripts/ 下的脚本能运行(`python scripts/xxx.py --help`)
4. agents/openai.yaml 配置正确
5. 运行 `powershell -File _shared/validate.ps1` 通过

#### 运行时契约验证
1. skill-runtime 的 runtime.yaml schema 自洽(validate_runtime.py scan 全部 PASS)
2. 抽查 3 个 skill 声明 runtime.yaml 后校验通过

#### workflow 可执行化验证
1. workflow-runtime 能把 game-forge-master §七编译为 workflow.yaml
2. workflow.yaml 可被 run_workflow.py 解析
3. 试跑 workflow.yaml(干跑模式,不实际调用 skill),暂停点正确触发

#### 编排总纲扩展验证
1. 两个总纲 §二/§七/§八 含 workflow.yaml 产出说明
2. 产出的 workflow.yaml 能被 workflow-runtime 解析

#### 整体验证
1. validate.ps1 全 PASS
2. skill-auditor 流水线审查模式审查两个总纲,无 CRITICAL
3. WORKBENCH.md / README.md 索引与实际 skill 目录一致(54 个 skill)

---

### 14.11 假设与决策

#### 假设
1. 宿主支持调用 scripts/ 下的 Python 脚本(已验证)
2. workflow-runtime 是"编排器之上的执行引擎",不替代编排总纲的决策逻辑
3. runtime.yaml 是可选的,渐进式接入(先在高风险 skill 如 game-asset-forge / tool-deploy-ops 试点)
4. task-planner 与 plan-system-implementation 的 task-board.json 格式兼容(可互转,不重复)

#### 决策
1. **第二阶段聚焦 4 维度**:Planning / Workflow / Agent Runtime / Evaluation 深化;Context 与 Data 放 Phase 3(Context 与宿主 SearchCodebase 重叠,Data 依赖基础设施)
2. **workflow-runtime 不替代编排总纲**:总纲做决策(引擎选择/裁剪),runtime 做执行(调度/暂停/恢复),职责分离
3. **runtime.yaml 渐进式接入**:不强制所有 skill 立即声明,先试点高风险 skill
4. **task-planner 通用化**:与 plan-system-implementation(工程实施蓝图)区分,前者任意任务,后者专精工程实施
5. **replanner 最多 3 轮**:超过转人工,避免无限循环
6. **failure-casebook 自动查询**:执行前注入预防提示,不阻塞执行

#### 不做(明确排除,Phase 3+)
- Model 层(model-router / prompt-registry):宿主已做路由
- Context 层(codebase-rag):与宿主 SearchCodebase 重叠,Phase 3 评估
- Data 层(skill-usage-tracker):依赖数据基础设施,Phase 3
- 真正的 Agent Runtime(skill-runtime 仅定义契约,实际运行时由宿主提供)
- 跨 skill 状态持久化(Phase 3,需宿主支持)

---

### 14.12 不在第二阶段范围

以下属于 Phase 3+ 工作,不在第二阶段内:

- Context 层(codebase-rag):代码库持久化索引
- Data 层(skill-usage-tracker):skill 调用统计与优化
- Model 层(model-router / prompt-registry):模型路由与 prompt 注册
- 跨会话状态持久化:需宿主支持
- skill-marketplace:skill 发现与分发
- agent-orchestrator:多 Agent 协同

这些在第二阶段完成后另行规划。

---

## 十五、第三阶段升级计划(Phase 3:数据驱动与智能协作)

> **进度基准**:第一阶段(§一~§十三)+ 第二阶段(§十四)均已闭环。53 个 skill 就绪,validate.ps1 9 项全 PASS,12 维度中 9 个已达目标水位,剩余 3 个维度(Context / Data / Model)为低水位。
>
> **第三阶段主题**:让 Agent 体系从"自主运行"升级为"数据驱动 + 智能协作"——补齐 Context 持久化索引 / Data 调用统计 / Model prompt 注册 / 多 Agent 协同协议 四大能力。

### 15.1 12 维度覆盖度评估(第二阶段后)

| # | 维度 | 第一阶段后 | 第二阶段后 | 第三阶段目标 | 是否纳入 Phase 3 |
|---|---|---|---|---|---|
| 1 | Model | ★★☆☆☆(宿主路由) | ★★☆☆☆(不变) | ★★★☆☆(prompt-registry) | ✓ **纳入(部分)** |
| 6 | Context | ★★☆☆☆(宿主 SearchCodebase) | ★★☆☆☆(不变) | ★★★★☆(codebase-rag 持久化) | ✓ **纳入** |
| 10 | Data | ★☆☆☆☆ | ★☆☆☆☆(不变) | ★★★☆☆(usage-tracker) | ✓ **纳入** |
| - | 多 Agent 协同 | ★☆☆☆☆(无协议) | ★☆☆☆☆(不变) | ★★★☆☆(agent-orchestrator 协议) | ✓ **纳入** |
| 其余 9 维度 | - | 已达目标 | 保持 | 保持 | ✗ 已闭环/宿主能力 |

**结论**:第三阶段聚焦 3 个低水位维度 + 1 个协同能力,新建 4 个 skill + 扩展 2 个现有 skill + 更新 3 个索引校验文件。

### 15.2 改造方案总览

```
模块 M:Context 层(1 个新 skill)
  codebase-rag → 持久化代码库索引,语义检索
       ↓ 与宿主 SearchCodebase 互补(宿主实时,本 skill 持久化+跨会话)
模块 N:Data 层(1 个新 skill)
  skill-usage-tracker → 记录每次 skill 调用,统计高频/慢/失败率
       ↓ 被 workflow-runtime 写入,被 failure-casebook 关联
模块 O:Model 层部分(1 个新 skill)
  prompt-registry → 集中管理各 skill 的 prompt 模板,版本化
       ↓ (model-router 依赖宿主,不做)
模块 P:多 Agent 协同(1 个新 skill)
  agent-orchestrator → 定义 Agent 间通信协议 + 任务委派
       ↓
模块 Q:现有 skill 扩展(2 个)
  workflow-runtime 扩展:执行时记录调用数据到 usage-tracker
  failure-casebook 扩展:失败记录关联 usage-tracker 调用 ID
       ↓
模块 R:索引与校验(3 个文件)
  WORKBENCH.md / README.md / validate.ps1
```

---

### 15.3 模块 M:Context 层(新建 1 个 skill)

#### M1. codebase-rag

**路径**:`codebase-rag/`

**frontmatter**:
```yaml
name: "codebase-rag"
description: "Context 层 skill。对代码库做持久化语义索引,支持跨会话检索与大型项目分块索引。与宿主 SearchCodebase 互补(宿主实时索引,本 skill 持久化+跨会话+支持分块策略)。当大型项目需持久化代码索引或跨会话检索代码时调用。"
```

**职责**:
- 对项目代码分块(按文件/按函数/按语义边界)并生成嵌入向量
- 持久化索引到 `.trae-cn/codebase-index/`(跨会话可用)
- 语义检索:接收自然语言查询,返回相关代码块 + 文件位置 + 相关度评分
- 增量更新:文件变更时只重新索引变更部分
- 产出 `codebase-index.json`(索引清单:文件数/分块数/嵌入模型/最后更新时间)

**scripts**:
- `scripts/index_codebase.py`:子命令 `build`(全量索引) / `update`(增量) / `stats`(统计)
- `scripts/search.py`:子命令 `query`(语义检索) / `locate`(定位符号)

**references**:
- `references/indexing-strategy.md`:分块策略(按文件/按函数/按语义边界/混合)
- `references/embedding-models.md`:嵌入模型选择(本地 vs API / 维度 / 成本)

**关键约束**:
- **与宿主 SearchCodebase 互补不替代**:宿主负责实时索引,本 skill 负责持久化+跨会话+大型项目优化
- 索引文件不提交 Git(加入 .gitignore),仅本地或团队共享盘
- 增量更新基于文件 mtime/hash 对比,不全量重建
- 嵌入模型默认用本地模型(隐私+成本),可选 API 模型
- 索引大小超阈值时提示用户清理或分项目索引

**codebase-index.json schema 摘要**:
```json
{
  "project": "项目名",
  "indexed_at": "2026-08-06T...",
  "embedding_model": "local-xxx",
  "stats": { "files": 120, "chunks": 450, "tokens": 89000 },
  "files": [
    { "path": "src/main.ts", "hash": "...", "chunks": 5, "mtime": "..." }
  ]
}
```

---

### 15.4 模块 N:Data 层(新建 1 个 skill)

#### N1. skill-usage-tracker

**路径**:`skill-usage-tracker/`

**frontmatter**:
```yaml
name: "skill-usage-tracker"
description: "Data 层 skill。记录每次 skill 调用数据(名称/耗时/成败/产物),统计高频/慢/失败率 skill,产出优化建议。当 workflow-runtime 执行 skill 时自动记录,或用户要'看 skill 使用统计/优化建议'时调用。纯记录不阻塞执行。"
```

**职责**:
- 记录每次 skill 调用:skill 名 / 开始结束时间 / 耗时 / 成功失败 / 失败码 / 产物路径 / 调用 ID
- 统计:调用次数排名 / 平均耗时 / 失败率 / 慢 skill(耗时>P95)
- 产出优化建议:高频失败 skill 关联 failure-casebook / 慢 skill 建议优化 / 未使用 skill 建议归档
- 产出 `usage-stats.json`(机读统计) + `optimization-suggestions.md`(人读建议)

**scripts**:
- `scripts/track_usage.py`:子命令 `record`(记录单次调用) / `query`(按 skill/时间查询)
- `scripts/stats.py`:子命令 `summary`(汇总) / `top`(排名) / `slow`(慢 skill)
- `scripts/suggest.py`:基于统计数据生成优化建议

**references**:
- `references/metrics-definition.md`:指标定义(调用次数/耗时分布/失败率/P95/P99)
- `references/retention-policy.md`:数据保留策略(默认 90 天,可配置)

**关键约束**:
- **纯记录不阻塞**:记录失败不影响 skill 执行
- 调用 ID 贯穿链路:workflow-runtime 分配调用 ID,failure-casebook 关联该 ID
- 数据存储在 `.trae-cn/usage/`(不提交 Git)
- 统计可按时间范围/skill 名/流水线过滤
- 保留 90 天,过期清理(可配置)

**usage-stats.json schema 摘要**:
```json
{
  "period": "2026-08-01~2026-08-31",
  "total_calls": 320,
  "by_skill": [
    { "skill": "game-asset-forge", "calls": 45, "avg_ms": 120000, "fail_rate": 0.11, "p95_ms": 180000 }
  ],
  "slow_skills": ["game-asset-forge"],
  "high_fail_skills": ["tool-deploy-ops"]
}
```

---

### 15.5 模块 O:Model 层部分(新建 1 个 skill)

#### O1. prompt-registry

**路径**:`prompt-registry/`

**frontmatter**:
```yaml
name: "prompt-registry"
description: "Model 层 skill(部分)。集中管理各 skill 的 prompt 模板,支持版本化+变体管理+对比。当要统一管理 prompt、做 A/B 测试、或检索某 skill 的 prompt 时调用。不负责模型路由(依赖宿主)。"
```

**职责**:
- 注册:各 skill 的 prompt 模板写入注册表(关联 skill 名 + 版本 + 变体标签)
- 检索:按 skill 名 / 版本 / 标签获取 prompt
- 版本化:每次修改 prompt 保留历史版本(可回退)
- 变体管理:同一 skill 可有多个 prompt 变体(如"简洁版"/"详细版")
- 对比:diff 两个版本/变体的 prompt
- 产出 `prompt-registry.json`(索引) + `prompts/{skill}/{version}.md`(各模板)

**scripts**:
- `scripts/register_prompt.py`:子命令 `add` / `update` / `list`
- `scripts/get_prompt.py`:子命令 `by-skill` / `by-tag` / `latest`
- `scripts/diff_prompts.py`:对比两个版本/变体

**references**:
- `references/prompt-versioning.md`:版本规则(语义化版本 + 变体标签)
- `references/prompt-structure.md`:prompt 结构规范(系统提示/用户提示/占位符)

**关键约束**:
- **渐进式接入**:不强制所有 skill 立即注册 prompt,先在 game-* 和 implement-* 试点
- prompt 文件是模板(含占位符),运行时由 skill 填充
- 版本回退需用户确认
- model-router(模型选择)依赖宿主能力,本 skill 不做
- 注册表存储在 `.trae-cn/prompts/`(可团队共享)

**prompt-registry.json schema 摘要**:
```json
{
  "skills": [
    {
      "skill": "game-blueprint",
      "versions": [
        { "version": "1.0.0", "tag": "stable", "path": "prompts/game-blueprint/1.0.0.md", "updated_at": "..." },
        { "version": "1.1.0-beta", "tag": "detailed", "path": "prompts/game-blueprint/1.1.0-beta.md", "updated_at": "..." }
      ]
    }
  ]
}
```

---

### 15.6 模块 P:多 Agent 协同(新建 1 个 skill)

#### P1. agent-orchestrator

**路径**:`agent-orchestrator/`

**frontmatter**:
```yaml
name: "agent-orchestrator"
description: "多 Agent 协同 skill。定义 Agent 间通信协议(消息格式/任务委派/结果汇总),支持主从与对等模式。当任务超出单 skill 范围需多 Agent 协作、或要编排多个子 Agent 并行/串行时调用。本身定义协议与编排逻辑,实际多 Agent 运行依赖宿主。"
```

**职责**:
- 定义 Agent 通信协议:消息格式(发送方/接收方/类型/负载/关联 ID)
- 任务委派:主 Agent 把子任务委派给子 Agent,收集结果
- 协同模式:主从模式(一主多从) / 对等模式(多 Agent 协商)
- 结果汇总:聚合多 Agent 结果,处理冲突/合并
- 产出 `orchestration-protocol.md`(协议规范) + `agent-messages.json`(消息日志)

**scripts**:
- `scripts/orchestrate.py`:子命令 `delegate`(委派) / `collect`(收集) / `merge`(合并)
- `scripts/message_bus.py`:子命令 `send` / `receive` / `history`

**references**:
- `references/agent-protocol.md`:通信协议规范(消息格式/握手/确认/超时)
- `references/delegation-patterns.md`:委派模式(扇出/扇入/管道/协商)
- `references/conflict-resolution.md`:结果冲突解决(优先级/投票/人工裁决)

**关键约束**:
- **定义协议不运行**:实际多 Agent 调度依赖宿主,本 skill 提供协议 + 编排逻辑
- 与 workflow-runtime 区别:workflow-runtime 编排"skill 调用",agent-orchestrator 编排"Agent 协同"(Agent 可包含多 skill)
- 委派有超时(默认 300s),超时转人工
- 结果冲突时默认按优先级,可配置投票或人工裁决
- 消息日志保留 30 天

**orchestration-protocol 消息格式**:
```json
{
  "msg_id": "M001",
  "from": "master-agent",
  "to": "sub-agent-1",
  "type": "delegate",
  "correlation_id": "T0",
  "payload": { "task": "...", "assigned_skill": "...", "deadline": "..." },
  "ack_required": true
}
```

---

### 15.7 模块 Q:现有 skill 扩展(2 个)

#### Q1. workflow-runtime 扩展:接入 usage-tracker

**改动文件**:`workflow-runtime/SKILL.md`

**新增内容**:
- 执行 workflow.yaml 时,每步 skill 调用前后记录到 skill-usage-tracker
- 分配调用 ID,贯穿该步执行链路
- 在 SKILL.md 加"数据记录"章节:说明记录的字段 + 调用 ID 生成规则

#### Q2. failure-casebook 扩展:关联 usage-tracker 调用 ID

**改动文件**:`failure-casebook/SKILL.md`

**新增内容**:
- 记录失败案例时,关联 skill-usage-tracker 的调用 ID(若存在)
- 查询失败案例时,可选返回关联的调用上下文(耗时/输入摘要)
- 在 auto-query 输出加 `related_call_id` 字段

---

### 15.8 模块 R:索引与校验更新(3 个文件)

#### R1. WORKBENCH.md / README.md

新增"Phase 3 数据与协作层"章节,列出 4 个新 skill:
- codebase-rag(Context 持久化索引)
- skill-usage-tracker(Data 调用统计)
- prompt-registry(Model prompt 注册)
- agent-orchestrator(多 Agent 协同协议)

#### R2. _shared/validate.ps1 扩展

新增检查项:
- 检查 10:prompt-registry 注册的 prompt 文件必须存在(路径一致性)
- 检查 11:agent-orchestrator 的 references/agent-protocol.md 必须存在(协议文件完整性)

---

### 15.9 实施顺序与依赖

```
第 1 批(无依赖,可并行):
  M1. codebase-rag(Context 层)
  N1. skill-usage-tracker(Data 层)

第 2 批(无依赖,可并行):
  O1. prompt-registry(Model 层部分)
  P1. agent-orchestrator(多 Agent 协同)

第 3 批(依赖第 1 批):
  Q1. workflow-runtime 扩展(接入 usage-tracker)
  Q2. failure-casebook 扩展(关联调用 ID)

第 4 批(最后):
  R1. WORKBENCH.md / README.md 更新
  R2. validate.ps1 扩展
  R3. 最终验证
```

**说明**:第 1 批与第 2 批无依赖可合并执行;第 3 批依赖第 1 批的 usage-tracker;第 4 批是索引与回归,必须最后。

---

### 15.10 人工确认点

按用户偏好"每一步都要人工确认",第三阶段设以下确认点:

| 确认点 | 触发时机 | 简报内容 | 选项 |
|---|---|---|---|
| ⏸ P3-A | 第 1 批完成 | codebase-rag 索引能力 + usage-tracker 统计能力 + validate.ps1 结果 | 进入第 2 批 / 回退修复 / 终止 |
| ⏸ P3-B | 第 2 批完成 | prompt-registry 注册能力 + agent-orchestrator 协议 + 试跑结果 | 进入第 3 批 / 回退修复 / 终止 |
| ⏸ P3-C | 第 3 批完成 | workflow-runtime 记录调用数据 + failure-casebook 关联调用 ID | 进入第 4 批 / 回退修复 / 终止 |
| ⏸ P3-D | 第 4 批完成 | 索引更新 + validate.ps1 全 PASS + 11 项检查通过 | 进入最终验证 / 回退修复 / 终止 |
| ⏸ P3-E | 最终验证完成 | 12 维度覆盖度提升 + 流水线审查无 CRITICAL + 索引一致(57 个 skill) | 第三阶段完成 / 回退修复 |

每个确认点通过 AskUserQuestion 询问,不自动连续执行下一批次。

---

### 15.11 验证步骤

#### 每个 skill 的验证
1. frontmatter 格式正确(name + description)
2. SKILL.md 行数 ≤500
3. scripts/ 下的脚本能运行(`python scripts/xxx.py --help`)
4. agents/openai.yaml 配置正确
5. 运行 `powershell -File _shared/validate.ps1` 通过

#### Context 层验证
1. codebase-rag 能对当前 skills 目录建索引
2. 语义检索能定位到目标代码块
3. 增量更新只重索引变更文件

#### Data 层验证
1. skill-usage-tracker 能记录单次调用
2. 统计汇总正确(次数/耗时/失败率)
3. 优化建议能关联 failure-casebook

#### Model 层验证
1. prompt-registry 能注册/检索/对比 prompt
2. 版本回退正确
3. 占位符在运行时被填充

#### 多 Agent 协同验证
1. agent-orchestrator 协议文件完整
2. 委派/收集/合并逻辑可运行(干跑模式)
3. 冲突解决按配置生效

#### 整体验证
1. validate.ps1 全 PASS(11 项检查)
2. WORKBENCH.md / README.md 索引与实际 skill 目录一致(57 个 skill)
3. 12 维度覆盖度:Context ★★★★☆ / Data ★★★☆☆ / Model ★★★☆☆ / 多 Agent 协同 ★★★☆☆

---

### 15.12 假设与决策

#### 假设
1. 宿主支持本地嵌入模型或 API 嵌入(codebase-rag 依赖)
2. skill-usage-tracker 的记录接口不阻塞 skill 执行(异步或快速写入)
3. prompt-registry 渐进式接入(先试点 game-* 和 implement-*)
4. agent-orchestrator 定义协议,实际多 Agent 调度依赖宿主能力

#### 决策
1. **第三阶段聚焦 3 低水位维度 + 1 协同能力**:Context / Data / Model(部分) / 多 Agent 协同
2. **codebase-rag 与宿主互补**:宿主实时索引,本 skill 持久化+跨会话+大型项目优化,不替代
3. **skill-usage-tracker 纯记录不阻塞**:记录失败不影响执行
4. **prompt-registry 不做 model-router**:模型路由依赖宿主,本 skill 只管 prompt 模板
5. **agent-orchestrator 定义协议不运行**:实际多 Agent 运行依赖宿主
6. **渐进式接入**:codebase-rag / prompt-registry 先试点,不强制全量

#### 不做(明确排除,Phase 4+)
- model-router(模型路由):依赖宿主能力
- 跨会话状态持久化:依赖宿主支持
- skill-marketplace(skill 发现与分发):价值未充分验证,Phase 4 评估
- 真正的 Agent Runtime 运行时(skill-runtime 仅定义契约,运行时由宿主提供)
- 自适应学习(skill 根据使用数据自动调整):Phase 4+

---

### 15.13 不在第三阶段范围

以下属于 Phase 4+ 工作,不在第三阶段内:

- model-router:模型智能路由(依赖宿主)
- 跨会话状态持久化:需宿主支持
- skill-marketplace:skill 发现与分发(价值待验证)
- 自适应学习:skill 根据使用数据自动优化 prompt/参数
- 跨项目知识迁移:不同项目间共享经验
- 真正的多 Agent 运行时:agent-orchestrator 定义协议,运行时依赖宿主

这些在第三阶段完成后另行规划。

---

## 十六、Phase 3 执行计划（基于当前进度）

> **制定背景**:会话上下文丢失后重新盘点。Phase 3 设计(§十五)已完整,本节为"执行视图",聚焦剩余工作与已识别问题。

### 16.1 当前进度盘点

| 批次 | 任务 | 状态 | 说明 |
|---|---|---|---|
| 第1批 | codebase-rag | ✅ 已验证 | scripts --help 全 PASS + references(2) + agents |
| 第1批 | skill-usage-tracker | ✅ 已补全 | references(2) 已创建 + scripts --help 验证(stats 因 sandbox exit 1,逻辑正确) |
| 第1批 | validate.ps1 | ✅ 9项全PASS | exit 0 |
| 第1批 | P3-A 确认点 | ⏸ 触发中 | 待用户确认 |
| 第2批 | prompt-registry | ❌ 未开始 | Model 层部分 |
| 第2批 | agent-orchestrator | ❌ 未开始 | 多 Agent 协同 |
| 第2批 | P3-B 确认点 | ❌ 未触发 | - |
| 第3批 | workflow-runtime 扩展 | ❌ 未开始 | 接入 usage-tracker |
| 第3批 | failure-casebook 扩展 | ❌ 未开始 | 关联调用 ID |
| 第3批 | P3-C 确认点 | ❌ 未触发 | - |
| 第4批 | WORKBENCH.md / README.md | ❌ 未开始 | 索引更新 |
| 第4批 | validate.ps1 扩展 | ❌ 未开始 | 检查 7/10/11 |
| 第4批 | P3-D / P3-E 确认点 | ❌ 未触发 | - |

### 16.2 已识别的问题

1. **skill-usage-tracker 缺 references 目录**(P0 阻塞)
   - SKILL.md 第46行引用 `references/metrics-definition.md` 与 `references/retention-policy.md`
   - 目录下无 references 子目录
   - **影响**:validate.ps1 检查 2 会 FAIL(引用路径不存在)
   - **修复**:创建两份 references 文件

2. **脚本可运行性未验证**(P0 阻塞)
   - 5 个脚本未跑 --help:codebase-rag 2 个 + skill-usage-tracker 3 个
   - **风险**:可能有语法错误或依赖缺失
   - **验证**:逐个运行 --help

3. **validate.ps1 未扩展**(P1,第4批统一处理)
   - 当前 9 项检查,Phase 3 需扩展到 11 项
   - 检查 7 的 $newSkills 列表未含 Phase 3 新 skill(codebase-rag/skill-usage-tracker/prompt-registry/agent-orchestrator)

### 16.3 剩余工作清单

#### 第1批收尾(P3-A 前置)

| 步骤 | 任务 | 交付物 | 验证标准 |
|---|---|---|---|
| 1.1 | 补 skill-usage-tracker references | metrics-definition.md / retention-policy.md | 文件存在 + 内容完整 |
| 1.2 | 验证 codebase-rag 脚本 | --help 输出 | build/update/stats + query/locate 子命令可见 |
| 1.3 | 验证 skill-usage-tracker 脚本 | --help 输出 | record/query + summary/top/slow + suggest 可见 |
| 1.4 | 运行 validate.ps1 | 9 项全 PASS | exit 0 |
| 1.5 | ⏸ P3-A 确认点 | AskUserQuestion 三选项 | 进入第2批 / 回退修复 / 终止 |

#### 第2批(P3-B)

| 步骤 | 任务 | 交付物 | 验证标准 |
|---|---|---|---|
| 2.1 | 创建 prompt-registry | SKILL.md + scripts(3) + references(2) + agents | frontmatter + --help + 版本化逻辑 |
| 2.2 | 创建 agent-orchestrator | SKILL.md + scripts(2) + references(3) + agents | frontmatter + --help + 协议文件 |
| 2.3 | 运行 validate.ps1 | 9 项全 PASS | exit 0 |
| 2.4 | ⏸ P3-B 确认点 | AskUserQuestion 三选项 | 进入第3批 / 回退修复 / 终止 |

#### 第3批(P3-C)

| 步骤 | 任务 | 交付物 | 验证标准 |
|---|---|---|---|
| 3.1 | workflow-runtime 扩展 | SKILL.md 加"数据记录"章节 | 引用 skill-usage-tracker record |
| 3.2 | failure-casebook 扩展 | SKILL.md 加 related_call_id | auto-query 输出含字段 |
| 3.3 | 运行 validate.ps1 | 9 项全 PASS | exit 0 |
| 3.4 | ⏸ P3-C 确认点 | AskUserQuestion 三选项 | 进入第4批 / 回退修复 / 终止 |

#### 第4批(P3-D / P3-E)

| 步骤 | 任务 | 交付物 | 验证标准 |
|---|---|---|---|
| 4.1 | WORKBENCH.md 加 Phase 3 章节 | 新增"数据与协作层" | 4 个新 skill 列出 |
| 4.2 | README.md 更新 skill 清单 | 57 个 skill | 索引一致 |
| 4.3 | validate.ps1 扩展 | 检查 7 加 4 新 skill + 检查 10/11 | 11 项全 PASS |
| 4.4 | 最终验证 | validate.ps1 + 索引一致性 | 57 skill + 12 维度提升 |
| 4.5 | ⏸ P3-D 确认点 | AskUserQuestion 三选项 | 进入最终验证 / 回退修复 / 终止 |
| 4.6 | ⏸ P3-E 确认点 | AskUserQuestion 三选项 | 第三阶段完成 / 回退修复 |

### 16.4 执行原则

1. **每步人工确认**:每个批次末尾的 P3-x 确认点不可跳过,通过 AskUserQuestion 询问
2. **失败回退**:任一步骤失败则回退到上一步修复,不强行推进
3. **验证先行**:每批结束前运行 validate.ps1 确保无回归
4. **文档同步**:每批完成后同步更新 §16.1 进度表
5. **渐进式接入**:codebase-rag / prompt-registry 先试点,不强制全量

### 16.5 12 维度目标水位

| # | 维度 | Phase 2 后 | Phase 3 目标 | 关键 skill |
|---|---|---|---|---|
| 1 | Model | ★★☆☆☆ | ★★★☆☆ | prompt-registry |
| 6 | Context | ★★☆☆☆ | ★★★★☆ | codebase-rag |
| 10 | Data | ★☆☆☆☆ | ★★★☆☆ | skill-usage-tracker |
| - | 多 Agent 协同 | ★☆☆☆☆ | ★★★☆☆ | agent-orchestrator |

---

## 十七、第四阶段升级计划（Phase 4：智能自适应与协同运行）

> **进度基准**：Phase 1-3 已全部闭环（57 个 skill + validate.ps1 11 项全 PASS，2026-08-06）。12 维度中 4 个达 ★★★★★，6 个达 ★★★★☆，剩余 Model ★★★☆☆ / Data ★★★☆☆ 待提升，Agent Runtime 缺执行器（仅契约）。
>
> **第四阶段主题**：让 Agent 体系从"数据驱动 + 智能协作"升级为"智能自适应 + 协同运行"——补齐 **Data 自适应优化闭环** / **Agent Runtime 执行器** / **会话状态持久化** 三大能力。

### 17.1 12 维度覆盖度评估（Phase 3 后）

| # | 维度 | Phase 3 后 | Phase 4 目标 | 是否纳入 Phase 4 |
|---|---|---|---|---|
| 1 | Model | ★★★☆☆ | 保持 | ✗ 依赖宿主 |
| 2 | Skill | ★★★★★(57个) | 保持 | ✗ 已饱和 |
| 3 | Tool | ★★★★★ | 保持 | ✗ 已闭环 |
| 4 | Planning | ★★★★☆ | 保持 | ✗ 已够用 |
| 5 | Memory | ★★★★☆ | ★★★★☆(加会话持久化) | ✓ **部分纳入** |
| 6 | Context | ★★★★☆ | 保持 | ✗ 已够用 |
| 7 | Workflow | ★★★★★ | 保持 | ✗ 已闭环 |
| 8 | Agent Runtime | ★★★★☆(仅契约) | ★★★★★(加执行器) | ✓ **纳入** |
| 9 | Evaluation | ★★★★★ | 保持 | ✗ 已闭环 |
| 10 | Data | ★★★☆☆(记录统计) | ★★★★☆(加自适应优化) | ✓ **纳入** |
| 11 | Guardrail | ★★★★☆ | 保持 | ✗ 已够用 |
| 12 | Human Feedback | ★★★★☆ | 保持 | ✗ 已够用 |

**结论**：第四阶段聚焦 2 个核心维度（Data 自适应优化 + Agent Runtime 执行器）+ 1 个支撑能力（会话状态持久化），新建 3 个 skill + 扩展 3 个现有 skill + 更新 3 个索引校验文件。

### 17.2 改造方案总览

```
模块 S：Data 自适应优化层（1 个新 skill）
  adaptive-tuner → 基于 usage-tracker 数据自动优化 skill 参数
       ↓ 产出 runtime-overrides.yaml
模块 T：Agent Runtime 执行层（1 个新 skill）
  agent-runtime-exec → 多 Agent 运行时执行器，基于 agent-orchestrator 协议实现实际调度
       ↓ 消费
模块 U：会话持久化层（1 个新 skill）
  session-snapshot → 会话状态快照与恢复，跨会话状态持久化
       ↓
模块 V：现有 skill 扩展（3 个）
  workflow-runtime 扩展：执行时调 adaptive-tuner 获取参数覆盖
  skill-runtime 扩展：runtime.yaml 支持 external_overrides 字段
  agent-orchestrator 扩展：接入 agent-runtime-exec 作为执行后端
       ↓
模块 W：索引与校验更新（3 个文件）
  WORKBENCH.md / README.md / validate.ps1
```

---

### 17.3 模块 S：Data 自适应优化层（新建 1 个 skill）

#### S1. adaptive-tuner

**路径**：`adaptive-tuner/`

**frontmatter**：
```yaml
name: "adaptive-tuner"
description: "Data 自适应优化层 skill。基于 skill-usage-tracker 的调用统计数据，自动生成 skill 参数优化建议（timeout/retry/降级阈值），产出 runtime-overrides.yaml 供 workflow-runtime 应用。当要基于历史数据优化 skill 运行时参数、或用户要'看 skill 调优建议'时调用。不自动应用，需用户确认。"
```

**职责**：
- 读取 skill-usage-tracker 的 `usage-stats.json`（调用次数/耗时分布/失败率/P95/P99）
- 分析每个 skill 的运行特征，识别优化点：
  - 慢 skill（P95 > timeout 的 80%）→ 建议提高 timeout
  - 高失败率 skill（fail_rate > 10%）→ 建议增加 retry 或调整降级策略
  - 频繁降级 skill → 建议调整降级阈值
  - 冷启动 skill（调用次数 < 5）→ 标记"数据不足，保持默认"
- 产出 `tuning-suggestions.json`（机读建议清单）+ `runtime-overrides.yaml`（可应用的参数覆盖）
- 支持应用建议：把 runtime-overrides.yaml 合并到各 skill 的 runtime.yaml（需用户确认）

**scripts**：
- `scripts/analyze_usage.py`：子命令 `analyze`（分析统计数据） / `suggest`（生成建议） / `apply`（应用覆盖，需确认） / `revert`（回退覆盖）
- `scripts/generate_overrides.py`：生成 runtime-overrides.yaml

**references**：
- `references/tuning-rules.md`：调优规则（timeout/retry/降级阈值的调整算法）
- `references/override-format.md`：runtime-overrides.yaml 格式规范

**关键约束**：
- **不自动应用**：建议生成后需用户确认才应用到 runtime.yaml
- **数据驱动**：所有建议必须基于 usage-tracker 的实际数据，非臆测
- **保守调整**：timeout 调整幅度不超过默认值的 2 倍；retry 上限 5 次
- **白名单**：部分关键 skill（如 guardrail / skill-auditor）不参与自动调优（安全考虑）
- **可回退**：应用覆盖前备份原 runtime.yaml，支持 revert 子命令回退
- **置信度标注**：每条建议含 confidence 字段（基于样本量，<10 次标"低置信度"）

**runtime-overrides.yaml 示例**：
```yaml
# 由 adaptive-tuner 生成，供 workflow-runtime 应用
generated_at: "2026-08-06T..."
data_source: "skill-usage-tracker/usage-stats.json"
overrides:
  - skill: game-asset-forge
    timeout: 900          # 原 600 → 900（P95=580s，余量不足）
    retry:
      max: 3              # 原 2 → 3（失败率 12%）
      backoff: exponential
    reason: "P95=580s 接近 timeout 600s;fail_rate=12% 建议增加重试"
    confidence: 0.85      # 基于样本量 45 次调用
  - skill: tool-deploy-ops
    timeout: 600          # 原 300 → 600（P95=280s）
    reason: "P95=280s 接近 timeout 300s"
    confidence: 0.72     # 基于样本量 18 次调用
```

---

### 17.4 模块 T：Agent Runtime 执行层（新建 1 个 skill）

#### T1. agent-runtime-exec

**路径**：`agent-runtime-exec/`

**frontmatter**：
```yaml
name: "agent-runtime-exec"
description: "Agent Runtime 执行层 skill。基于 agent-orchestrator 定义的通信协议，实现多 Agent 实际调度执行器（委派/收集/合并/冲突解决）。当要把多 Agent 协同从'协议定义'升级为'实际运行'，或要并行调度多个子 Agent 执行任务时调用。本身是执行器，依赖宿主提供 Agent 实例。"
```

**职责**：
- 读取 agent-orchestrator 的 `orchestration-protocol.md`（协议规范）
- 实现多 Agent 调度执行器：
  - `delegate`：主 Agent 把子任务委派给子 Agent，分配 deadline
  - `collect`：收集所有子 Agent 的结果，处理超时/失败
  - `merge`：聚合结果，按 conflict-resolution 策略解决冲突
  - `monitor`：监控执行中 Agent 的状态，支持取消
- 支持协同模式：主从模式（一主多从）/ 对等模式（多 Agent 协商）/ 管道模式（串行接力）
- 产出 `agent-exec-report.json`（执行轨迹 + 各 Agent 状态 + 结果汇总）

**scripts**：
- `scripts/execute_agents.py`：子命令 `delegate` / `collect` / `merge` / `monitor`
- `scripts/resolve_conflicts.py`：按优先级/投票/人工裁决解决结果冲突

**references**：
- `references/execution-modes.md`：执行模式（主从/对等/管道/扇出扇入）
- `references/conflict-strategies.md`：冲突解决策略（优先级/投票/人工裁决/最近优先）
- `references/timeout-handling.md`：超时处理（取消/降级/转人工）

**关键约束**：
- **依赖宿主提供 Agent 实例**：本 skill 是执行器，不创建 Agent，只调度
- **协议兼容**：严格遵循 agent-orchestrator 定义的消息格式（msg_id/from/to/type/payload）
- **超时默认 300s**：子 Agent 超时后转人工裁决，不无限等待
- **冲突默认按优先级**：可配置投票或人工裁决
- **执行轨迹保留 30 天**：便于复盘与 failure-casebook 关联
- **失败不阻塞**：单个子 Agent 失败不中断整体，标记失败后继续 collect 其他结果

**与 agent-orchestrator 的区别**：
- agent-orchestrator：定义协议（消息格式/委派模式/冲突规则）—— 是"规则"
- agent-runtime-exec：实现执行器（实际调度/收集/合并）—— 是"运行"
- 关系：agent-orchestrator 是"宪法"，agent-runtime-exec 是"政府"

---

### 17.5 模块 U：会话持久化层（新建 1 个 skill）

#### U1. session-snapshot

**路径**：`session-snapshot/`

**frontmatter**：
```yaml
name: "session-snapshot"
description: "会话持久化层 skill。把当前会话的关键状态（任务进度/已产出文件/上下文摘要）快照保存，支持跨会话恢复。当会话上下文将丢失、或要在新会话继续未完成任务时调用。与宿主内置记忆互补（宿主会话级，本 skill 显式快照+跨会话恢复）。"
```

**职责**：
- **快照保存**：把当前会话的关键状态序列化为 `session-snapshot.json`
  - 任务进度（task-tree 当前状态：已完成/进行中/待执行）
  - 已产出文件清单（路径 + hash + 摘要）
  - 上下文摘要（关键决策/用户偏好/失败记录）
  - workflow.yaml 执行状态（当前步骤/暂停点）
- **恢复**：从快照恢复会话状态，注入到新会话上下文
- **自动快照**：在关键节点（人工确认点/阶段完成/失败回退）自动触发快照
- **对比**：diff 两个快照，展示状态差异
- 产出 `session-snapshot.json`（快照文件） + `snapshots-index.json`（索引）

**scripts**：
- `scripts/snapshot_ops.py`：子命令 `save`（保存快照） / `restore`（恢复） / `list`（列出快照） / `diff`（对比快照） / `clean`（清理过期）

**references**：
- `references/snapshot-schema.md`：快照 JSON schema（任务/文件/上下文/workflow 状态）
- `references/restore-strategy.md`：恢复策略（全量恢复/选择性恢复/增量恢复）

**关键约束**：
- **与宿主记忆互补**：宿主负责会话级记忆，本 skill 负责显式快照+跨会话
- **快照不提交 Git**：存储在 `.trae-cn/sessions/`（本地或团队共享盘）
- **自动快照触发点**：人工确认点 / 阶段完成 / 失败回退 / 用户手动
- **快照保留 30 天**：过期清理（可配置 `SESSION_SNAPSHOT_RETENTION_DAYS`）
- **恢复需用户确认**：恢复前展示快照摘要，用户确认后注入
- **文件 hash 校验**：恢复时校验已产出文件的 hash，若文件被修改则提示冲突

**session-snapshot.json schema 摘要**：
```json
{
  "snapshot_id": "snap-20260806-001",
  "session_id": "原会话ID",
  "created_at": "2026-08-06T...",
  "trigger": "manual | auto-confirm | auto-stage | auto-fail",
  "task_tree": { "current_task": "T3", "completed": ["T1","T2"], "pending": ["T4"] },
  "artifacts": [
    { "path": "docs/PRD.md", "hash": "sha256:...", "summary": "产品需求文档" }
  ],
  "context_summary": {
    "key_decisions": ["使用 Phaser 3 引擎", "目标平台 Web"],
    "user_preferences": ["每步人工确认"],
    "failures": [{"skill": "game-asset-forge", "code": "TIMEOUT"}]
  },
  "workflow_state": { "current_step": "s3", "paused_at": "pause1" }
}
```

---

### 17.6 模块 V：现有 skill 扩展（3 个）

#### V1. workflow-runtime 扩展：接入 adaptive-tuner

**改动文件**：`workflow-runtime/SKILL.md`

**新增内容**：
- 执行 workflow.yaml 前，可选调 adaptive-tuner 获取 `runtime-overrides.yaml`
- 把 overrides 合并到 step 的 `runtime` 字段（覆盖原 runtime.yaml 的 timeout/retry）
- 新增"自适应优化"章节：说明接入方式 + 覆盖优先级
- 覆盖优先级：`external_overrides` > `runtime.yaml` 本地字段 > 默认值

#### V2. skill-runtime 扩展：runtime.yaml 支持 external_overrides

**改动文件**：`skill-runtime/SKILL.md` + `references/runtime-schema.md`

**新增内容**：
- runtime.yaml 新增可选字段 `external_overrides`：引用 adaptive-tuner 产出的 overrides 文件路径
- `validate_runtime.py` 新增校验：external_overrides 引用的文件存在且格式正确
- 覆盖优先级规则文档化：external_overrides > runtime.yaml 本地 > 默认值

#### V3. agent-orchestrator 扩展：接入 agent-runtime-exec

**改动文件**：`agent-orchestrator/SKILL.md`

**新增内容**：
- 新增"执行后端"章节：说明 agent-runtime-exec 作为协议的执行实现
- 协议与执行器关系：agent-orchestrator 定义"怎么通信"，agent-runtime-exec 实现"怎么执行"
- 调用方式：用户要"实际运行多 Agent"时，agent-orchestrator 委托 agent-runtime-exec 执行

---

### 17.7 模块 W：索引与校验更新（3 个文件）

#### W1. WORKBENCH.md / README.md

新增"Phase 4 智能自适应与协同运行层"章节，列出 3 个新 skill：
- adaptive-tuner（Data 自适应优化）
- agent-runtime-exec（Agent Runtime 执行器）
- session-snapshot（会话持久化）

#### W2. _shared/validate.ps1 扩展

新增检查项：
- 检查 12：adaptive-tuner 的 references（tuning-rules.md + override-format.md）必须存在
- 检查 13：agent-runtime-exec 的 references（execution-modes.md + conflict-strategies.md + timeout-handling.md）必须存在
- 检查 14：session-snapshot 的 references（snapshot-schema.md + restore-strategy.md）必须存在
- 扩展检查 7：newSkills 列表加 3 个新 skill（adaptive-tuner / agent-runtime-exec / session-snapshot）

---

### 17.8 实施顺序与依赖

```
第 1 批（无依赖，可并行）：
  S1. adaptive-tuner（Data 优化层，依赖 usage-tracker 数据格式，不依赖其运行）
  U1. session-snapshot（会话持久化，独立）

第 2 批（依赖第 1 批）：
  T1. agent-runtime-exec（依赖 agent-orchestrator 协议定义）

第 3 批（依赖第 1-2 批）：
  V1. workflow-runtime 扩展（接入 adaptive-tuner）
  V2. skill-runtime 扩展（支持 external_overrides）
  V3. agent-orchestrator 扩展（接入 agent-runtime-exec）

第 4 批（最后）：
  W1. WORKBENCH.md / README.md 更新
  W2. validate.ps1 扩展（检查 12/13/14 + 扩展检查 7）
  W3. 最终验证
```

**说明**：第 1 批与第 2 批无强依赖可合并执行；第 3 批依赖前两批的 skill 存在；第 4 批是索引与回归，必须最后。

---

### 17.9 人工确认点

按用户偏好"每一步都要人工确认"，第四阶段设以下确认点：

| 确认点 | 触发时机 | 简报内容 | 选项 |
|---|---|---|---|
| ⏸ P4-A | 第 1 批完成 | adaptive-tuner 优化建议能力 + session-snapshot 快照能力 + validate.ps1 结果 | 进入第 2 批 / 回退修复 / 终止 |
| ⏸ P4-B | 第 2 批完成 | agent-runtime-exec 执行器 + 干跑试跑结果 | 进入第 3 批 / 回退修复 / 终止 |
| ⏸ P4-C | 第 3 批完成 | workflow-runtime 自适应接入 + skill-runtime overrides + agent-orchestrator 执行后端 | 进入第 4 批 / 回退修复 / 终止 |
| ⏸ P4-D | 第 4 批完成 | 索引更新 + validate.ps1 全 PASS（14 项）+ 索引一致（60 个 skill） | 进入最终验证 / 回退修复 / 终止 |
| ⏸ P4-E | 最终验证完成 | 12 维度覆盖度提升 + 流水线审查无 CRITICAL | 第四阶段完成 / 回退修复 |

每个确认点通过 AskUserQuestion 询问，不自动连续执行下一批次。

---

### 17.10 验证步骤

#### 每个 skill 的验证
1. frontmatter 格式正确（name + description）
2. SKILL.md 行数 ≤500
3. scripts/ 下的脚本能运行（`python scripts/xxx.py --help`）
4. agents/openai.yaml 配置正确
5. 运行 `powershell -File _shared/validate.ps1` 通过

#### Data 自适应优化验证
1. adaptive-tuner 能读取 skill-usage-tracker 的 usage-stats.json
2. 能生成 tuning-suggestions.json + runtime-overrides.yaml
3. apply 子命令需用户确认，应用后备份原 runtime.yaml
4. revert 子命令能回退到备份

#### Agent Runtime 执行器验证
1. agent-runtime-exec 能解析 agent-orchestrator 协议
2. delegate/collect/merge 逻辑可运行（干跑模式）
3. 冲突解决按配置生效（优先级/投票）
4. 超时处理正确（超时转人工，不无限等待）

#### 会话持久化验证
1. session-snapshot 能保存当前会话状态
2. restore 能恢复到新会话
3. diff 能对比两个快照差异
4. 自动快照在人工确认点触发
5. 文件 hash 校验能检测冲突

#### 整体验证
1. validate.ps1 全 PASS（14 项检查）
2. WORKBENCH.md / README.md 索引与实际 skill 目录一致（60 个 skill）
3. 12 维度覆盖度：Data ★★★★☆ / Agent Runtime ★★★★★ / Memory ★★★★☆

---

### 17.11 假设与决策

#### 假设
1. skill-usage-tracker 已积累足够数据供 adaptive-tuner 分析（至少 10 次调用；不足时标"低置信度"）
2. 宿主支持 Agent 实例创建与调度（agent-runtime-exec 依赖）
3. 宿主允许跨会话读写文件（session-snapshot 依赖）
4. adaptive-tuner 的建议不破坏 skill 安全性（白名单机制保障）

#### 决策
1. **第四阶段聚焦 2 核心维度 + 1 支撑能力**：Data 自适应优化 + Agent Runtime 执行器 + 会话持久化
2. **adaptive-tuner 不自动应用**：建议生成后需用户确认，避免破坏稳定性
3. **agent-runtime-exec 依赖宿主**：本 skill 是执行器，不创建 Agent，只调度
4. **session-snapshot 与宿主记忆互补**：宿主负责会话级，本 skill 负责显式快照+跨会话
5. **渐进式接入**：adaptive-tuner 先在 game-*/tool-* 试点，不强制全量
6. **保守调整原则**：timeout 调整幅度不超过默认值 2 倍，retry 上限 5 次

#### 不做（明确排除，Phase 5+）
- model-router（模型智能路由）：依赖宿主能力
- skill-marketplace（skill 发现与分发）：价值待验证
- 跨项目知识迁移：需积累更多项目数据
- prompt 自适应优化（基于使用数据自动优化 prompt）：风险较高，Phase 5 评估
- 真正的 Agent 自主决策（Agent 自主选择 skill 与策略）：依赖宿主能力

---

### 17.12 不在第四阶段范围

以下属于 Phase 5+ 工作，不在第四阶段内：

- model-router：模型智能路由（依赖宿主）
- skill-marketplace：skill 发现与分发（价值待验证）
- 跨项目知识迁移：不同项目间共享经验（需积累数据）
- prompt 自适应优化：基于使用数据自动优化 prompt（风险高）
- Agent 自主决策：Agent 自主选择 skill 与策略（依赖宿主）

这些在第四阶段完成后另行规划。

---

### 17.13 Phase 4 12 维度目标水位

| # | 维度 | Phase 3 后 | Phase 4 目标 | 关键 skill | 提升点 |
|---|---|---|---|---|---|
| 8 | Agent Runtime | ★★★★☆ | ★★★★★ | agent-runtime-exec | 加执行器 |
| 10 | Data | ★★★☆☆ | ★★★★☆ | adaptive-tuner | 加自适应优化闭环 |
| 5 | Memory | ★★★★☆ | ★★★★☆ | session-snapshot | 加会话持久化（支撑） |
| 其余 9 维度 | - | 已达目标 | 保持 | - | - |

**Phase 4 完成后**：12 维度中 5 个达 ★★★★★，7 个达 ★★★★☆，Agent 体系从"数据驱动 + 智能协作"升级为"智能自适应 + 协同运行"。
