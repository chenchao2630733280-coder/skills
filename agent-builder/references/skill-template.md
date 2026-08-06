# 标准 skill 结构模板(权威)

本文件定义 Agent 体系层 skill 的标准结构模板,是 `agent-builder/SKILL.md` §三步骤 3 引用的详细文档。
新建 skill 时套用本模板,确保结构规范、章节完整、风格一致。

## 一、目录结构

```
<skill-name>/
├── SKILL.md          # 主入口(frontmatter + 正文,≤300 行优秀)
├── references/        # 懒加载详细文档(SKILL.md 引用)
│   ├── <ref-1>.md
│   └── <ref-2>.md
├── scripts/           # 可执行脚本(Tool skill 必须;其他按需)
│   └── <main>.py
└── agents/
    └── openai.yaml    # 平台配置
```

### 各目录职责

| 目录 | 必填 | 说明 |
|------|------|------|
| SKILL.md | 是 | 主入口,frontmatter + 正文 |
| references/ | 否 | 详细文档,懒加载;SKILL.md ≤300 行时可不拆 |
| scripts/ | Tool skill 必须 | 可执行脚本;非 Tool skill 按需 |
| agents/openai.yaml | 是 | 平台配置(display_name / short_description / default_prompt) |

## 二、SKILL.md frontmatter 模板

```markdown
---
name: "<skill-name>"
description: "<职责一句话>。<何时调用>。当要<场景>时调用。"
---
```

### description 质量要求

- **必须包含两部分**:做什么 + 何时调用
- **格式**:`<职责>。当要<场景>时调用。`
- **长度**:≤200 字符(含中英文)
- **示例**:
  - 好:`"工作流执行引擎 skill。把编排总纲的执行顺序转为可执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度。当要把流水线从'文档描述'升级为'可执行工作流'时调用。"`
  - 差:`"工作流引擎"`(缺少何时调用)

## 三、SKILL.md 正文章节模板

```markdown
# <skill-name> — <一句话标题>

<skill-name> 是 AI Agent 体系的 **<层名> skill**。<2-3 句概述:职责 + 核心特点>。

- **<特点 1>**:<说明>
- **<特点 2>**:<说明>
- **<特点 3>**:<说明>

---

## 一、何时调用

满足以下任一条件即调用本 skill:

1. **<场景 1>**:<说明>
2. **<场景 2>**:<说明>
3. **<场景 3>**:<说明>

**不要**在以下场景调用:
- <不要场景 1>
- <不要场景 2>
- <不要场景 3>

<若有"只读不写"等约束,在此声明>

---

## 二、<核心规范 / 职责 / 契约>

<速查表或概览,详细内容引用 references/>

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `<字段>` | <类型> | <是/否> | <说明> |

> **<特殊说明>**:<补充说明>

---

## 三、<示例 / 规范示例>

<一个完整的示例>

---

## 四、scripts 调用方式

### 4.1 <script-1>.py — <用途>

```
python scripts/<script-1>.py <子命令> [选项]
```

#### <子命令 1>

```
python scripts/<script-1>.py <子命令> --<参数> <值>
```

- <说明>

### 4.N 退出码

| 场景 | 退出码 |
|------|--------|
| 成功 | 0 |
| 有错误 | 1 |
| 参数错误 | 2 |

---

## 五、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/<ref-1>.md` | (1) <时机 1>;(2) <时机 2> |
| `references/<ref-2>.md` | (1) <时机 1>;(2) <时机 2> |

<若有多份 references,声明懒加载>

---

## 六、关键约束

1. **<约束 1>**:<说明>
2. **<约束 2>**:<说明>
3. **<约束 3>**:<说明>

---

## 七、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `<skill-a>` | <关系> | <说明> |
| `<skill-b>` | <关系> | <说明> |

---

## 八、质量检查清单

### 8.1 <约束类自评>

- [ ] SKILL.md 已声明<约束>。

### 8.2 产物自评项

- [ ] `python scripts/<script>.py --help` 不报错。
- [ ] <其他自评项>
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
```

## 四、agents/openai.yaml 模板

```yaml
interface:
  display_name: <Display Name>
  short_description: <一句话中文描述>
  default_prompt: |
    <默认提示词,告诉 AI 这个 skill 做什么>
```

### 示例

```yaml
interface:
  display_name: Agent Builder
  short_description: 创建 AI Agent 体系层 skill 的元技能
  default_prompt: |
    我要创建一个新的 AI Agent 体系层 skill。请提供 12 维度架构框架对照、标准创建流程和设计模式指导。
```

## 五、runtime.yaml 模板(高风险 skill)

```yaml
# <skill-name>/runtime.yaml
timeout: <秒数>
retry:
  max: <次数>
  backoff: <fixed|exponential>
  interval: <秒数>
inputs:
  - name: <输入名>
    schema: <schema 路径>
    required: true
outputs:
  - path: <产物路径>
    type: <file|directory>
  - path: <可选产物路径>
    type: <file|directory>
    optional: true
degrade:
  - trigger: <触发条件>
    action: <降级动作>
    target: <目标路径 glob>
```

### 含 external_overrides(接入自适应闭环后)

```yaml
timeout: <秒数>
retry:
  max: <次数>
  backoff: <fixed|exponential>
  interval: <秒数>
external_overrides: ../../<path>/runtime-overrides.yaml
degrade:
  - trigger: <触发条件>
    action: <降级动作>
    target: <目标路径>
```

## 六、references 文件模板

```markdown
# <文档标题>(权威)

本文件定义 <内容>,是 `<skill-name>/SKILL.md` §<章节> 引用的详细文档。
<一句话说明消费方>。

## 一、<总览>

<表格或概览>

## 二、<详解>

### 2.1 <子项 1>

- **职责**:<说明>
- **代表 skill**:<skill 名>
- **核心产物**:<产物列表>
- **接入方式**:<说明>

### 2.2 <子项 2>

...

## 三、<补充章节>

...
```

## 七、行数控制与懒加载策略

| SKILL.md 行数 | 评级 | 策略 |
|--------------|------|------|
| ≤300 | 优秀 | 正文可直接含速查表,references 按需 |
| 301-500 | 可接受 | 速查表留正文,详细内容已拆 references |
| >500 | 必须拆分 | 识别可抽离章节,移到 references,正文只留入口 |

### 懒加载原则

1. SKILL.md 只放**速查表 + 流程入口 + 约束**,详细内容放 references
2. references 文件按**读取时机**组织(不是按内容类型)
3. SKILL.md 的 references 使用指引表明确每个文件的读取时机
4. 调用方按需读取 references,不强制一次性全读

### 拆分判断标准

- 该章节内容 >80 行 → 考虑拆到 references
- 该章节是"详细规范"而非"速查" → 拆到 references
- 该章节只在特定场景需要 → 拆到 references
- 该章节是"速查表 / 流程 / 约束" → 留 SKILL.md
