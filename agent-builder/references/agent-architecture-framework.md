# AI Agent 体系 12 维度架构框架(权威)

本文件定义 AI Agent 体系的 12 维度架构框架,是 `agent-builder/SKILL.md` §二 引用的详细文档。
新建 Agent 体系层 skill 时对照本框架定位,规划升级时对照本框架识别缺口。

来源:2026-08-06 产品工作台 AI Agent 体系 4 阶段升级的 23 个 skill 建设经验。

## 一、12 维度总览

| # | 维度 | 中文名 | 职责 | Phase | 代表 skill |
|---|------|--------|------|-------|-----------|
| 1 | Model | 模型层 | prompt 模板管理、版本化、变体对比 | 3 | `prompt-registry` |
| 2 | Skill | 技能层 | SKILL.md + references + scripts 标准结构 | 1 | 全部 skill |
| 3 | Tool | 工具调用层 | Git/CI/部署/DB/监控操作封装 | 1 | `tool-git-ops` 等 5 个 |
| 4 | Planning | 规划能力 | 任务拆解、失败重规划 | 2 | `task-planner` / `replanner` |
| 5 | Memory | 记忆系统 | 知识库、失败案例、会话快照 | 1+4 | `project-knowledge-base` 等 3 个 |
| 6 | Context | 上下文管理 | 代码库索引、语义检索 | 3 | `codebase-rag` |
| 7 | Workflow | 工作流编排 | 可执行 workflow.yaml | 2 | `workflow-runtime` |
| 8 | Agent Runtime | Agent 运行框架 | runtime.yaml 契约、多 Agent 执行器 | 2+4 | `skill-runtime` / `agent-runtime-exec` |
| 9 | Evaluation | 评测体系 | skill 质量审查、执行后评测 | 1+2 | `skill-auditor` |
| 10 | Data | 数据体系 | 调用统计、自适应参数优化 | 3+4 | `skill-usage-tracker` / `adaptive-tuner` |
| 11 | Guardrail | 安全护栏 | 前置拦截、敏感路径保护 | 1 | `guardrail` / `diff-reviewer` |
| 12 | Human Feedback | 人机协同 | 人工确认点、checkpoint 回退 | 1+4 | 编排总纲 + `session-snapshot` |

## 二、各维度详解

### 2.1 Model(模型层)

- **职责**:集中管理各 skill 的 prompt 模板,支持版本化、变体管理、A/B 对比。
- **代表 skill**:`prompt-registry`(Phase 3)
- **核心产物**:`prompt-registry.json`(索引) + `prompts/{skill}/{version}.md`
- **接入方式**:渐进式接入,先 game-*/implement-* 试点。
- **新建 skill 时**:若新 skill 含复杂 prompt,在 prompt-registry 注册版本。

### 2.2 Skill(技能层)

- **职责**:定义 skill 的标准结构(SKILL.md + references + scripts + agents)。
- **代表 skill**:全部 skill 本身都是该维度的实例。
- **核心约束**:SKILL.md ≤300 行优秀;references 懒加载;scripts 失败不阻塞。
- **新建 skill 时**:按 `references/skill-template.md` 的标准结构搭建。

### 2.3 Tool(工具调用层)

- **职责**:封装外部系统操作(Git/CI/部署/DB/监控),默认只读优先,变更类需用户确认。
- **代表 skill**:`tool-git-ops` / `tool-ci-ops` / `tool-deploy-ops` / `tool-db-ops` / `tool-monitor-ops`(Phase 1)
- **核心模式**:失败不阻塞 + 只读优先 + 变更确认。
- **新建 skill 时**:Tool 类 skill 必须有 `scripts/` 目录;在 validate.ps1 的 `$toolSkills` 列表注册。

### 2.4 Planning(规划能力)

- **职责**:把复杂需求拆解为子任务树+依赖关系+优先级;失败/变更时动态调整。
- **代表 skill**:`task-planner`(Phase 2) / `replanner`(Phase 2)
- **核心产物**:`task-tree.json` + `task-plan.md`
- **接入方式**:`task-planner` 产出 task-tree → `workflow-runtime` 消费 → `replanner` 失败时调整。

### 2.5 Memory(记忆系统)

- **职责**:结构化存储团队规范/ADR/历史事故/代码规范;记录失败案例;会话状态快照与跨会话恢复。
- **代表 skill**:`project-knowledge-base`(Phase 1) / `failure-casebook`(Phase 1) / `session-snapshot`(Phase 4)
- **核心模式**:失败案例保留 90 天;会话快照支持 save/restore/list/diff/clean。
- **接入方式**:其他 skill 执行前查 failure-casebook 注入预防提示;会话中断时用 session-snapshot 保存。

### 2.6 Context(上下文管理)

- **职责**:对代码库做持久化语义索引,支持跨会话检索;与宿主 SearchCodebase 互补(宿主实时,本 skill 持久化)。
- **代表 skill**:`codebase-rag`(Phase 3)
- **核心产物**:`codebase-index.json` + 检索结果
- **接入方式**:大型项目需持久化代码索引或跨会话检索时调用。

### 2.7 Workflow(工作流编排)

- **职责**:把编排总纲的执行顺序编译为可执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度。
- **代表 skill**:`workflow-runtime`(Phase 2)
- **核心产物**:`workflow.yaml` + `workflow-exec-report.json`
- **接入方式**:编排总纲的执行顺序章节 → `compile_workflow.py` 编译 → `run_workflow.py` 执行。
- **关键机制**:pause 节点对应人工确认点;runtime 层重试用尽后上升到 workflow 层 on_fail。

### 2.8 Agent Runtime(Agent 运行框架)

- **职责**:定义 runtime.yaml 运行时元数据契约(timeout/retry/inputs/outputs/degrade);实现多 Agent 实际调度执行器。
- **代表 skill**:`skill-runtime`(Phase 2) / `agent-runtime-exec`(Phase 4)
- **核心产物**:`runtime-contract-report.json` + `agent-exec-report.json`
- **三层覆盖优先级**:`external_overrides`(adaptive-tuner 产出) > runtime.yaml 本地字段 > 默认值。
- **接入方式**:skill 声明 runtime.yaml → workflow-runtime 读契约调度 → agent-runtime-exec 执行多 Agent。

### 2.9 Evaluation(评测体系)

- **职责**:审查 skill 质量(6 模式 6 维度),含执行后评测。
- **代表 skill**:`skill-auditor`(Phase 1+2 扩展)
- **6 模式**:结构审查 / 一致性审查 / 健壮性审查 / 扩展性审查 / 执行后评测 / 运行时契约审查。
- **接入方式**:skill 产出后按 skill-auditor 执行后评测模式自查。

### 2.10 Data(数据体系)

- **职责**:记录 skill 调用数据(耗时/状态/产物);基于数据自动生成参数优化建议。
- **代表 skill**:`skill-usage-tracker`(Phase 3) / `adaptive-tuner`(Phase 4)
- **自适应闭环**:记录 → 分析 → 覆盖 → 执行 → 再记录。
- **接入方式**:workflow-runtime 每步调 skill-usage-tracker record → adaptive-tuner analyze → suggest → workflow-runtime 合并。

### 2.11 Guardrail(安全护栏)

- **职责**:前置拦截(敏感路径保护+操作分级);后置审查(变更 diff 风险标记)。
- **代表 skill**:`guardrail`(Phase 1) / `diff-reviewer`(Phase 1)
- **接入方式**:编排总纲末尾 Tool 确认点前过 guardrail 前置检查;变更后过 diff-reviewer 审查。

### 2.12 Human Feedback(人机协同)

- **职责**:在流水线关键阶段设置强制暂停点,通过 AskUserQuestion 向用户确认后再进入下一阶段。
- **代表 skill**:编排总纲(`game-forge-master` / `product-pipeline-master`)的人工确认点 + `session-snapshot`(Phase 4)
- **三选项**:进入下一阶段(推荐) / 回退修改 / 终止。
- **接入方式**:每个阶段产出后 → 质量门禁 PASS → AskUserQuestion 三选项 → 按选择执行。

## 三、4 阶段升级路径

| 阶段 | 主题 | 补齐维度 | 新增 skill | 扩展 skill |
|------|------|---------|-----------|-----------|
| Phase 1 | 工具齐全 | Tool/工程/Guardrail/Memory/Evaluation | 12 | skill-auditor(5模式5维度) |
| Phase 2 | 自主运行 | Planning/Workflow/Agent Runtime/Evaluation深化 | 4 | 总纲+skill-auditor+failure-casebook |
| Phase 3 | 数据驱动+智能协作 | Context/Data/Model/Agent协同 | 4 | workflow-runtime+failure-casebook |
| Phase 4 | 智能自适应+协同运行 | Data自适应/Agent Runtime执行/Memory持久化 | 3 | skill-runtime+workflow-runtime+agent-orchestrator |

## 四、分层调度框架

```
编排总纲(决策大脑):引擎选择+阶段裁剪+阶段定义
  ↓
workflow-runtime(执行引擎):编译执行顺序为 workflow.yaml
  ↓
agent-orchestrator(Agent 协同):定义通信协议+任务委派(粒度=Agent)
  ↓
agent-runtime-exec(执行器):实际多 Agent 调度执行
  ↓
各 skill(具体能力):执行具体任务,产出业务文件
```

## 五、数据驱动自适应框架

```
skill-usage-tracker 记录调用数据(耗时/失败率)
  → adaptive-tuner analyze 分析数据,生成 tuning-suggestions.json
  → adaptive-tuner suggest 产出 runtime-overrides.yaml(需用户确认)
  → skill-runtime 的 external_overrides 字段引用 overrides
  → workflow-runtime 执行时读取 external_overrides,合并覆盖 timeout/retry
  → 执行结果再次被 skill-usage-tracker 记录 → (循环)
```

覆盖优先级:`external_overrides` > runtime.yaml 本地字段 > 默认值。
失败不阻塞:overrides 缺失或解析失败时回退本地值并标 WARNING。
