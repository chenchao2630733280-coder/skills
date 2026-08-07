---
name: "rd-init"
description: "工作台加载器。扫描 skills 目录全部 skill，生成工作台索引和完整性报告，让 AI 快速掌握工作台全貌。仅用于工作台加载，不生成业务产物。"
---

# rd-init

## 一、定位

rd-init 是 skills 工作台的**加载入口**。首次使用工作台时调用，扫描全部 skill 目录，生成结构化索引，让 AI 一目了然地掌握：工作台有哪些 skill、分属哪条流水线、各 skill 的 frontmatter 元数据、工作台完整性状态。

**不是项目初始化器**：不创建业务目录结构、不生成 project.yaml、不拉取模板。业务目录由各 skill 写入产物时自动创建。

## 二、触发条件

当用户首次打开工作台，或要求"加载工作台""扫描 skill""列出全部 skill""工作台完整性检查"时调用。

## 三、产出契约

| 产物 | 路径 | 说明 |
|------|------|------|
| 工作台索引 | `.workbench-index.json` | 全部 skill 的结构化清单（名称/描述/分类/frontmatter） |
| 加载报告 | 对话输出 | 工作台概览：skill 总数、分类统计、完整性警告 |

## 四、执行流程

```bash
python .agents/skills/rd-init/scripts/rd-init.py --skills-dir .agents/skills
```

### 4.1 脚本动作

1. 扫描 `--skills-dir` 下所有子目录，识别包含 `SKILL.md` 的目录为 skill
2. 解析每个 skill 的 frontmatter（name / description）和 runtime.yaml（是否存在）
3. 按 WORKBENCH.md 的分类规则识别 skill 所属流水线
4. 校验完整性：frontmatter 是否规范、references 路径是否存在、runtime.yaml 是否声明
5. 生成 `.workbench-index.json`
6. 输出加载报告到对话

### 4.2 脚本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--skills-dir` | skills 工作台根目录 | `.agents/skills` |
| `--output` | 索引文件输出路径 | `.workbench-index.json` |
| `--quiet` | 只输出索引文件，不打印报告 | false |

## 五、skill 分类

工作台 skill 分为五大类：

| 分类 | 说明 | skill 数 |
|------|------|---------|
| 工作台元 skill | 工作台加载/索引/校验自身（rd-init） | 1 |
| 产研业务层 | 产研流水线全阶段（需求→PRD→原型→HTML→门户→实现→部署） | 22 |
| 游戏流水线 | game-forge 五引擎游戏生成（选题→蓝图→PRD→美术→代码→集成→打磨） | 11 |
| AI 短剧 | 短剧选题与项目开发 | 2 |
| Agent 体系层 | 12 维度支撑层（Tool/Planning/Memory/Context/Workflow/Runtime/Evaluation/Data/Guardrail/Engineering） | 25 |

> skill 数为声明值，实际以扫描结果为准。

## 六、完整性校验项

| 校验项 | 级别 | 说明 |
|--------|------|------|
| SKILL.md 存在 | CRITICAL | 每个 skill 目录必须有 SKILL.md |
| frontmatter name 存在 | CRITICAL | 无 name 无法识别 skill，frontmatter 必须在文件顶部 |
| frontmatter description 存在 | WARNING | SKILL.md 应有 frontmatter description 字段 |
| runtime.yaml 存在 | INFO | 有 runtime.yaml 的 skill 表示已接入运行时契约 |
| references 路径存在 | WARNING | SKILL.md 中引用的 references/*.md 应实际存在 |

## 七、与其他 skill 关系

rd-init 是工作台加载入口，不调度任何 skill，与各 skill 是"加载后可调用"关系，而非上下游工件消费关系。

| 关系 | skill | 说明 |
|------|-------|------|
| 加载后可调用 | product-pipeline-master | 产研流水线总纲，工作台加载后即可启动 |
| 加载后可调用 | game-forge-master | 游戏流水线总纲，工作台加载后即可启动 |
| 互补 | WORKBENCH.md | 人工维护的工作台说明，rd-init 生成机器可读的索引 |
