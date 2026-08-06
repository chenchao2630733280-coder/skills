# 7 大可复用设计模式(权威)

本文件定义 AI Agent 体系建设中沉淀的 7 大可复用设计模式,是 `agent-builder/SKILL.md` §四 引用的详细文档。
新建 skill 时根据类型选择模式,在 SKILL.md 中体现。

来源:2026-08-06 产品工作台 AI Agent 体系 4 阶段升级的 23 个 skill 建设经验。

## 模式 1:skill 结构模式

**一句话**:SKILL.md(frontmatter+正文) + references(懒加载) + scripts(可执行) + agents/openai.yaml。

**适用**:所有 skill。

**结构**:
```
<skill-name>/
├── SKILL.md          # 主入口,≤300 行优秀
├── references/        # 懒加载详细文档,SKILL.md 引用
├── scripts/           # 可执行脚本(Tool skill 必须)
└── agents/
    └── openai.yaml    # 平台配置
```

**SKILL.md 章节标准**:
1. 何时调用(满足条件 + 不要场景)
2. 核心职责/规范(速查表)
3. scripts 调用方式(子命令 + 示例 + 退出码)
4. references 使用指引(读取时机表)
5. 关键约束(编号列表)
6. 与其他 skill 的关系(关系表)
7. 质量检查清单(checkbox)

**示例**:`skill-runtime` / `workflow-runtime` / `adaptive-tuner`。

## 模式 2:编排总纲模式

**一句话**:何时调用 + 决策树 + 阶段裁剪 + 产物路径表 + 失败回退策略 + 人工确认点。

**适用**:编排总纲类 skill(如 `game-forge-master` / `product-pipeline-master`)。

**核心要素**:
- **何时调用**:满足条件 + 不要场景 + 本 skill 不产出文件声明
- **决策树**:引擎选择 / 端类型判定(条件→结论表)
- **阶段裁剪规则**:哪些阶段可选 / 跳过条件 / 并行条件
- **产物路径表**:固定路径契约,所有 skill 按固定路径读写
- **失败回退策略表**:FAIL 则回 N 阶段重跑,超过 max_retries 升级为 abort
- **人工确认点**:每阶段产出后 ⏸ AskUserQuestion 三选项

**示例**:`game-forge-master`(5 确认点) / `product-pipeline-master`(4 确认点)。

## 模式 3:人工确认机制

**一句话**:关键阶段后用 AskUserQuestion 三选项(进入下一阶段/回退修改/终止),不允许自动连续执行。

**适用**:流水线类 skill / 分阶段升级计划。

**标准动作**:
1. 阶段产出完成 → 质量门禁 PASS → 简报(产出清单 + 验证结果)
2. AskUserQuestion 三选项:
   - 进入下一阶段(推荐)
   - 回退修改(说明回退到哪一步)
   - 终止(停止,保留当前状态)
3. 按用户选择执行

**例外**:
- 阶段 1(脑暴/蓝图)可选不设确认点(产出简单,用户可直接进入下一阶段)
- 旁线流程(如文档交付)不参与主线确认点

**示例**:`game-forge-master` §七确认点 1~5 / `product-pipeline-master` §八确认点 1~4。

## 模式 4:checkpoint 回退

**一句话**:每完成一个任务提交 git checkpoint,commit message 以 `checkpoint(...)` 开头,支持 `git reset --hard HEAD~1` 回退。

**适用**:所有变更操作(新建 skill / 扩展 skill / 批量修改)。

**标准流程**:
1. 完成任务 → `git add -A`
2. commit message 格式:`checkpoint(<批次标识>): <简述>`
   - 示例:`checkpoint(phase4-batch3): 完成 Phase 4 第3批 - 自适应优化闭环`
3. commit message 正文含:产出清单 + 验证结果 + 回退方式
4. 回退:`git reset --hard HEAD~1` 回退到上一个 checkpoint

**关键约束**:
- 不使用 `&&` / `||` 连接(PowerShell 不支持)
- commit message 含中文时用 `git commit -F <文件>` 避免引号转义问题
- 提交前确认 `.gitignore` 排除了临时文件(`.tmp_*` / 报告 JSON 等)

## 模式 5:防回归校验

**一句话**:validate.ps1 多维度校验,每次变更后必跑。

**适用**:任何 skill 变更后(新建 / 修改 / 删除)。

**校验维度(14 项)**:
1. 共享文件无本地重复拷贝
2. SKILL.md references 引用路径存在
3. 全部 JSON 可解析
4. design-tokens 单点且版本正确
5. Tool skill 含 scripts/ 目录
6. 审查类 skill 声明"只读"约束
7. 新 skill frontmatter 含 name + description
8. runtime.yaml schema 校验(skill-runtime scan)
9. workflow.yaml 可解析(若存在)
10. prompt-registry references 完整
11. agent-orchestrator references 完整
12. adaptive-tuner references 完整
13. agent-runtime-exec references 完整
14. session-snapshot references 完整

**扩展规则**:新建 skill 若有专属 references 需校验,在 validate.ps1 新增检查项(检查 N+1)。

## 模式 6:协议与执行分离

**一句话**:协议定义方(规则) + 执行实现方(运行),两者职责分离,互不替代。

**适用**:协议类 skill(如 `agent-orchestrator` + `agent-runtime-exec`)。

**职责分工**:
| 维度 | 协议定义方 | 执行实现方 |
|------|-----------|-----------|
| 角色 | 规则 | 运行 |
| 产出 | 协议规范、模式、策略 | 执行轨迹、状态、结果 |
| 关心 | "怎么通信" | "怎么执行" |
| 文件 | references/ | scripts/ |
| 是否替代对方 | 否 | 否 |

**调用方式**:
- 用户要"设计协议"→ 只调协议方
- 用户要"实际运行"→ 协议方委托执行方
- 执行方失败不阻塞协议方,错误回填 error 字段

**示例**:`agent-orchestrator`(协议) + `agent-runtime-exec`(执行器)。

## 模式 7:渐进式接入

**一句话**:高风险 skill 先试点,再推广;不强制所有 skill 立即接入。

**适用**:跨 skill 的契约/机制推广(如 runtime.yaml / external_overrides / prompt-registry)。

**推广路径**:
1. **试点阶段**:在 1-3 个高风险 skill 声明契约(如 `game-asset-forge` / `tool-deploy-ops`)
2. **验证阶段**:跑 validate.ps1 确认 schema 正确,跑实际执行确认契约有效
3. **推广阶段**:逐步在其他 skill 声明,每次变更后跑 validate.ps1
4. **默认阶段**:新 skill 默认声明,老 skill 渐进补齐

**关键约束**:
- 试点 skill 选择标准:高风险(超时常见 / 失败率高 / 降级需求强)
- 未声明的 skill 走默认值,标 UNDECLARED(非 FAIL)
- 不阻塞:未声明的 skill 不影响其他 skill 执行

**示例**:`runtime.yaml` 先在 game-asset-forge 试点 → 验证 → 逐步推广到全部高风险 skill。

## 模式组合示例

### 创建编排总纲

组合:模式 1(结构) + 模式 2(编排总纲) + 模式 3(人工确认) + 模式 4(checkpoint)

### 创建协议类 skill

组合:模式 1(结构) + 模式 6(协议与执行分离) + 模式 4(checkpoint)

### 创建工具类 skill

组合:模式 1(结构) + 模式 7(渐进式接入,声明 runtime.yaml) + 模式 4(checkpoint)

### 创建审查类 skill

组合:模式 1(结构) + 模式 5(防回归校验,新增检查项) + 模式 4(checkpoint)
