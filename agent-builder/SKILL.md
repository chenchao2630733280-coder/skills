---
name: "agent-builder"
description: "创建 AI Agent 体系层 skill 的元技能。提供 12 维度架构框架、标准创建流程、7 大设计模式和结构模板。当要新建 Agent 体系层 skill、设计 Agent 架构、或沉淀 Agent 建设经验时调用。"
---

# agent-builder — AI Agent 创建元技能

agent-builder 是 AI Agent 体系的 **Skill 工程化元技能**。它把 Agent 体系建设的经验沉淀为
可复用的架构框架、创建流程、设计模式和结构模板,让新建 Agent 体系层 skill 时有标准可依、
有模式可循,避免从零摸索。

- **元技能,不替代 skill-creator**:`skill-creator` 处理"skill 文件骨架怎么写"(目录/frontmatter/格式),
  本 skill 处理"Agent 体系层 skill 应该怎么设计"(架构定位/模式选择/契约对齐)。
- **经验沉淀,非凭空生成**:本 skill 的 12 维度框架和 7 大模式来自实际 4 阶段升级的 23 个 skill 建设经验。
- **只读不写**:本 skill 提供框架、流程、模式和模板的**指导**,不直接替用户写 SKILL.md。
  实际文件创建由用户或 `skill-creator` 执行。

---

## 一、何时调用

满足以下任一条件即调用本 skill:

1. **新建 Agent 体系层 skill**:要创建一个新的 Agent 体系层 skill(如 Tool 层 / Memory 层 / Data 层等),
   需要确定它在 12 维度框架中的定位、选择设计模式、对齐 runtime.yaml 契约。
2. **设计 Agent 架构**:要为一个新领域(如数据分析 Agent / 运维 Agent)设计整体架构,
   需要对照 12 维度框架检查覆盖度、确定分层结构。
3. **沉淀 Agent 建设经验**:完成一批 skill 建设后,要把经验沉淀为可复用模式,供后续建设参考。
4. **审查 skill 体系完备度**:要检查现有 skill 集合是否覆盖 12 维度,识别缺口。
5. **规划 Agent 体系升级**:要为现有 skill 集合制定分阶段升级计划。

**不要**在以下场景调用:
- 创建普通业务 skill(如 game-* / generate-* 系列,用 `skill-creator` 即可,无需架构框架)
- 修改某个已有 skill 的具体逻辑(直接编辑该 skill)
- 用户只是问"skill 怎么写"(纯格式问题,用 `skill-creator`)
- 要审查单个 skill 的质量(用 `skill-auditor`)

---

## 二、AI Agent 体系 12 维度架构框架(速查)

完整框架详解见 `references/agent-architecture-framework.md`,本节为速查表:

| 维度 | 中文名 | 职责 | 代表 skill |
|------|--------|------|-----------|
| Model | 模型层 | prompt 模板管理、版本化、变体对比 | `prompt-registry` |
| Skill | 技能层 | SKILL.md + references + scripts 的标准结构 | 全部 skill |
| Tool | 工具调用层 | Git/CI/部署/DB/监控操作封装,默认只读优先 | `tool-git-ops` 等 5 个 |
| Planning | 规划能力 | 任务拆解为 task-tree、失败时重规划 | `task-planner` / `replanner` |
| Memory | 记忆系统 | 项目知识库、失败案例、会话快照 | `project-knowledge-base` 等 3 个 |
| Context | 上下文管理 | 代码库持久化索引、语义检索 | `codebase-rag` |
| Workflow | 工作流编排 | 编译执行顺序为可执行 workflow.yaml | `workflow-runtime` |
| Agent Runtime | Agent 运行框架 | runtime.yaml 契约、多 Agent 执行器 | `skill-runtime` / `agent-runtime-exec` |
| Evaluation | 评测体系 | skill 质量审查、执行后评测 | `skill-auditor` |
| Data | 数据体系 | 调用统计、自适应参数优化 | `skill-usage-tracker` / `adaptive-tuner` |
| Guardrail | 安全护栏 | 前置拦截、敏感路径保护、操作分级 | `guardrail` / `diff-reviewer` |
| Human Feedback | 人机协同 | 人工确认点、checkpoint 回退 | 编排总纲 + 用户工作流 |

**4 阶段升级路径**(经验总结):

| 阶段 | 主题 | 补齐维度 | skill 数 |
|------|------|---------|---------|
| Phase 1 | 工具齐全 | Tool / 工程skill / Guardrail / Memory | 12 |
| Phase 2 | 自主运行 | Planning / Workflow / Agent Runtime / Evaluation | 4 |
| Phase 3 | 数据驱动+智能协作 | Context / Data / Model / Agent 协同 | 4 |
| Phase 4 | 智能自适应+协同运行 | Data 自适应 / Agent Runtime 执行 / Memory 持久化 | 3 |

---

## 三、Agent 创建标准流程(6 步)

### 步骤 1:架构定位

对照 12 维度框架(§二),确定新 skill 属于哪个维度:

- 该维度是否已有 skill?如有,新 skill 与之是互补 / 上下游 / 替代关系?
- 该维度是否为空?如是,新 skill 是该维度的首个 skill。

### 步骤 2:模式选择

根据 skill 类型选择设计模式(详见 `references/skill-creation-patterns.md`):

| skill 类型 | 推荐模式 | 示例 |
|-----------|---------|------|
| 编排总纲 | 编排总纲模式 | `game-forge-master` |
| 执行引擎 | 协议与执行分离 | `workflow-runtime` |
| 工具封装 | 失败不阻塞 + 只读优先 | `tool-git-ops` |
| 协议定义 | 协议与执行分离 | `agent-orchestrator` |
| 数据记录 | 失败不阻塞 + 纯记录 | `skill-usage-tracker` |
| 审查校验 | 只读不写 + 多维度 | `skill-auditor` |

### 步骤 3:结构搭建

按标准结构创建 skill(详见 `references/skill-template.md`):

```
<skill-name>/
├── SKILL.md          # 主入口(frontmatter + 正文,≤300 行优秀)
├── references/        # 懒加载详细文档(SKILL.md 引用)
├── scripts/           # 可执行脚本(Tool skill 必须有)
└── agents/
    └── openai.yaml    # 平台配置
```

### 步骤 4:契约对齐

- 声明 `runtime.yaml`(高风险 skill 必须,其他可选):timeout / retry / inputs / outputs / degrade
- 若该 skill 参与自适应闭环,声明 `external_overrides` 字段
- 在 SKILL.md 的"与其他 skill 的关系"表中声明上下游依赖

### 步骤 5:质量自评

创建完成后,按以下顺序验证:

1. `python scripts/<script>.py --help` 不报错(若有 scripts)
2. `python skill-runtime/scripts/validate_runtime.py check --skill <skill-name>`(若声明了 runtime.yaml)
3. `powershell -File _shared/validate.ps1`(全工作台防回归)
4. 按 `skill-auditor` 的 6 维度自评(可选)

### 步骤 6:索引更新 + checkpoint

1. 在 `WORKBENCH.md` 的对应 Phase 章节添加 skill 条目
2. 在 `README.md` 的完整技能清单添加表行 + §五链接
3. 在 `_shared/validate.ps1` 的 `$newSkills` 列表添加新 skill 名(若需要 frontmatter 校验)
4. 提交 git checkpoint:`git commit -m "checkpoint(...): ..."`,支持 `git reset --hard HEAD~1` 回退

---

## 四、可复用设计模式(速查)

7 大模式详解见 `references/skill-creation-patterns.md`,本节为速查:

| # | 模式 | 一句话 | 适用 |
|---|------|--------|------|
| 1 | skill 结构模式 | SKILL.md + references + scripts + agents | 所有 skill |
| 2 | 编排总纲模式 | 何时调用+决策树+裁剪+路径表+回退+确认点 | 编排总纲类 |
| 3 | 人工确认机制 | 关键阶段后 AskUserQuestion 三选项 | 流水线/升级 |
| 4 | checkpoint 回退 | 每任务提交,commit 以 checkpoint 开头 | 所有变更 |
| 5 | 防回归校验 | validate.ps1 多维度校验 | 变更后必跑 |
| 6 | 协议与执行分离 | 协议方定义规则,执行方实现运行 | 协议类 skill |
| 7 | 渐进式接入 | 高风险先试点,再推广 | runtime.yaml 等 |

---

## 五、关键约束

1. **元技能不替 skill-creator**:本 skill 提供架构和模式指导,文件骨架由 `skill-creator` 处理。
2. **SKILL.md 行数控制**:≤300 行优秀,301-500 可接受,>500 必须拆分到 references。
3. **references 懒加载**:SKILL.md 只放速查表和流程入口,详细内容放 references,按需读取。
4. **失败不阻塞**:所有脚本失败时返回 error 字段 + exit 1,不抛异常阻断调用方。
5. **只读不写**:本 skill 不直接创建/修改任何 skill 文件,只提供指导。
6. **经验来源可追溯**:12 维度框架和 7 大模式来自实际建设经验,引用时注明来源 Phase。

---

## 六、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/agent-architecture-framework.md` | (1) 对照 12 维度定位新 skill;(2) 检查体系完备度;(3) 规划升级 |
| `references/skill-creation-patterns.md` | (1) 选择设计模式;(2) 理解模式适用场景和示例;(3) 组合多个模式 |
| `references/skill-template.md` | (1) 创建新 skill 时套用模板;(2) 检查已有 skill 结构规范性 |

三份 references 均为**懒加载**:仅在需要时读取,不强制调用方一次性全读。

---

## 七、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `skill-creator` | 互补 | skill-creator 处理"文件骨架怎么写",本 skill 处理"Agent skill 怎么设计" |
| `skill-auditor` | 下游 | 本 skill 的创建流程§步骤 5 产出后,skill-auditor 做 6 维度审查 |
| `skill-runtime` | 契约方 | 本 skill §步骤 4 指导声明 runtime.yaml,skill-runtime 定义 schema |
| `_shared/validate.ps1` | 校验方 | 本 skill §步骤 5 指导运行 validate.ps1 做防回归校验 |
| `workflow-runtime` | 消费方 | 新 skill 若参与流水线,由 workflow-runtime 调度执行 |
| `agent-orchestrator` | 协作方 | 新 skill 若为 Agent 协同类,参考 agent-orchestrator 的协议定义 |

---

## 八、质量检查清单

- [ ] SKILL.md 行数 ≤300,frontmatter 含 name + description。
- [ ] 12 维度框架对照已完成,新 skill 维度定位明确。
- [ ] 至少选择 1 个设计模式,并在 SKILL.md 中体现。
- [ ] 标准结构(SKILL.md + references + scripts + agents)已搭建。
- [ ] runtime.yaml 契约已声明(高风险 skill)或确认不需要。
- [ ] 与其他 skill 的关系表已填写上下游依赖。
- [ ] `validate.ps1` 全部 PASS(含新 skill 的 frontmatter 校验)。
- [ ] WORKBENCH.md / README.md 索引已更新。
- [ ] git checkpoint 已提交,commit message 以 `checkpoint(...)` 开头。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
