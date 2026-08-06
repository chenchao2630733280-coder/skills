# workflow.yaml 字段规范(权威)

本文件定义 workflow.yaml 的完整字段规范,是 `compile_workflow.py validate` 校验时的唯一事实来源。
`workflow-runtime/SKILL.md` §三 引用本文件;`run_workflow.py` 执行时按本规范解析步骤。

workflow.yaml 是把编排总纲(如 game-forge-master §七、product-pipeline-master §八)的执行顺序
编译为机读工作流的产物,由 `compile_workflow.py` 产出,由 `run_workflow.py` 消费。

## 一、顶层结构

workflow.yaml 是单个 YAML 文件,通常位于工作台根目录或项目目录。顶层字段如下:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | - | 工作流名称(如 `game-forge-pipeline`) |
| `source` | string | 否 | null | 来源说明(如 `game-forge-master §七`) |
| `version` | string | 否 | `"1.0"` | 工作流版本 |
| `steps` | array | 是 | - | 步骤数组,按执行顺序排列 |

约束:
- `name` 必须为非空字符串
- `steps` 必须为非空数组(至少 1 个步骤)
- 顶层不允许出现 `name`/`source`/`version`/`steps` 以外的字段

## 二、steps[] 子字段

每个 step 描述一个执行单元(调用 skill 或人工确认暂停点):

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | string | 是 | - | 步骤唯一标识(如 `s1`/`gate0`/`pause1`) |
| `type` | string (enum) | 否 | `skill` | 取值 `skill`(调用 skill) / `pause`(人工确认暂停点) |
| `skill` | string | type=skill 时必填 | - | 要调用的 skill 名(如 `game-blueprint`) |
| `args` | object | 否 | `{}` | 传给 skill 的参数键值对 |
| `outputs` | array | 否 | `[]` | 预期产物路径列表,每项为 string |
| `on_fail` | object | 否 | `{action:abort}` | 失败处理策略,见第四节 |
| `next` | string | 否 | (顺序下一个) | 下一步 step id;缺省时按数组顺序取下一个 |
| `parallel_with` | string | 否 | null | 与本步并行执行的 step id(双向声明) |
| `runtime` | string | 否 | null | 引用的 runtime.yaml 路径(相对 skill 根目录),见第五节 |
| `confirm` | object | type=pause 时必填 | - | AskUserQuestion 配置,见第三节 |
| `optional` | boolean | 否 | false | 仅 type=pause 时有意义;true 表示该暂停点可选(允许跳过,如可选 Tool 确认点);false 表示强制暂停 |
| `title` | string | 否 | null | 步骤标题(人读,便于简报) |

约束:
- `id` 在 steps 内必须唯一
- `type=skill` 时 `skill` 必填且为非空字符串
- `type=pause` 时 `confirm` 必填,且不应同时声明 `skill`/`args`/`outputs`
- `next` 若声明,必须指向 steps 内已存在的 step id
- `parallel_with` 若声明,必须指向 steps 内已存在的 id,且应为双向声明(A.parallel_with=B 且 B.parallel_with=A)
- `on_fail.action=back_to` 时,`on_fail.target` 必填且指向已存在的 step id

## 三、confirm 子字段(pause 节点专用)

`type=pause` 的步骤用 `confirm` 描述 AskUserQuestion 配置:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `question` | string | 是 | - | 向用户提问的文本 |
| `options` | array | 是 | - | 选项数组,每项含 label/next |
| `options[].label` | string | 是 | - | 选项文案(如"进入规格设计") |
| `options[].next` | string | 是 | - | 选该选项后跳转的 step id |

约束:
- `options` 至少 2 项,建议固定 3 项(进入下一阶段 / 回退修改 / 终止流水线)
- `options[].next` 必须指向 steps 内已存在的 step id
- 终止选项的 `next` 指向一个特殊的 `__end__` 标识(表示结束)

## 四、on_fail 子字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `action` | string (enum) | 是 | `abort` | 失败动作:`back_to`(回退重跑) / `skip`(跳过继续) / `abort`(终止) |
| `target` | string | action=back_to 时必填 | - | 回退目标 step id |
| `max_retries` | integer | 否 | 3 | 回退重跑最大次数,超过则升级为 abort |

语义详见 `references/execution-semantics.md`。

## 五、runtime 引用

`runtime` 字段引用 skill 的 runtime.yaml(由 `skill-runtime` 定义契约):

```yaml
runtime: ../game-asset-forge/runtime.yaml
```

- 路径相对 workflow.yaml 所在目录
- `run_workflow.py` 执行该 step 前,读取 runtime.yaml 获取 `timeout`/`retry`/`degrade` 等运行时元数据
- 若 runtime.yaml 不存在或未声明,按 `skill-runtime` §七 默认值处理(timeout=300, retry.max=0)
- runtime.yaml 的 schema 见 `../skill-runtime/references/runtime-schema.md`

## 六、JSON Schema

以下 JSON Schema 可用于程序化校验 workflow.yaml:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "workflow.yaml",
  "type": "object",
  "additionalProperties": false,
  "required": ["name", "steps"],
  "properties": {
    "name": { "type": "string", "minLength": 1 },
    "source": { "type": ["string", "null"] },
    "version": { "type": "string" },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "type": { "type": "string", "enum": ["skill", "pause"] },
          "skill": { "type": ["string", "null"] },
          "args": { "type": "object" },
          "outputs": { "type": "array", "items": { "type": "string" } },
          "on_fail": {
            "type": "object",
            "additionalProperties": false,
            "required": ["action"],
            "properties": {
              "action": { "type": "string", "enum": ["back_to", "skip", "abort"] },
              "target": { "type": ["string", "null"] },
              "max_retries": { "type": "integer", "minimum": 0 }
            }
          },
          "next": { "type": ["string", "null"] },
          "parallel_with": { "type": ["string", "null"] },
          "runtime": { "type": ["string", "null"] },
          "optional": { "type": "boolean" },
          "title": { "type": ["string", "null"] },
          "confirm": {
            "type": "object",
            "additionalProperties": false,
            "required": ["question", "options"],
            "properties": {
              "question": { "type": "string", "minLength": 1 },
              "options": {
                "type": "array",
                "minItems": 2,
                "items": {
                  "type": "object",
                  "additionalProperties": false,
                  "required": ["label", "next"],
                  "properties": {
                    "label": { "type": "string", "minLength": 1 },
                    "next": { "type": "string", "minLength": 1 }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## 七、完整示例

以下示例由 game-forge-master §七 的阶段 1~2 编译而来(含 Gate 0 + 人工确认点 1):

```yaml
# workflow.yaml — 游戏生成流水线(片段)
name: game-forge-pipeline
source: game-forge-master §七执行顺序
version: "1.0"
steps:
  - id: s1-blueprint
    type: skill
    title: 生成游戏蓝图
    skill: game-blueprint
    outputs:
      - docs/GAME_BLUEPRINT.md
    on_fail:
      action: abort
    next: s1-gate0

  - id: s1-gate0
    type: skill
    title: Gate 0 蓝图门
    skill: game-quality-gate
    args:
      gate: 0
    outputs:
      - docs/GATE_0_REPORT.md
    on_fail:
      action: back_to
      target: s1-blueprint
      max_retries: 3
    next: pause1

  - id: pause1
    type: pause
    title: 人工确认点 1
    confirm:
      question: Gate 0 已 PASS,是否进入规格设计?
      options:
        - label: 进入规格设计
          next: s2-spec
        - label: 回退修改蓝图
          next: s1-blueprint
        - label: 终止流水线
          next: __end__

  - id: s2-spec
    type: skill
    title: 生成 PRD + 技术设计
    skill: game-spec
    outputs:
      - docs/PRD.md
      - docs/TECH_DESIGN.md
    on_fail:
      action: abort
    next: s2-gate1

  - id: s2-gate1
    type: skill
    title: Gate 1 规格门
    skill: game-quality-gate
    args:
      gate: 1
    outputs:
      - docs/GATE_1_REPORT.md
    on_fail:
      action: back_to
      target: s2-spec
      max_retries: 3
    next: pause2

  - id: pause2
    type: pause
    title: 人工确认点 2
    confirm:
      question: Gate 1 已 PASS,是否进入美术规范?
      options:
        - label: 进入美术规范
          next: s3-art-spec
        - label: 回退修改规格
          next: s2-spec
        - label: 终止流水线
          next: __end__
```

## 八、并行步骤示例

game-forge-master §七 阶段 4 的"并行调用 game-asset-forge 和 game-code-forge"编译为:

```yaml
steps:
  - id: s4-asset
    type: skill
    title: 生成游戏美术资源
    skill: game-asset-forge
    runtime: ../game-asset-forge/runtime.yaml
    outputs:
      - assets/
    parallel_with: s4-code
    next: s4-gate3

  - id: s4-code
    type: skill
    title: 生成游戏工程代码
    skill: game-code-forge
    outputs:
      - src/
    parallel_with: s4-asset
    next: s4-gate3

  - id: s4-gate3
    type: skill
    title: Gate 3 产物门
    skill: game-quality-gate
    args:
      gate: 3
    on_fail:
      action: back_to
      target: s4-asset
      max_retries: 3
    next: pause4
```

## 九、与 SKILL.md 的关系

- workflow.yaml 是机器可读的工作流执行计划,`compile_workflow.py` 产出、`run_workflow.py` 消费
- SKILL.md 是人读文档,描述 workflow-runtime 的"做什么"和"怎么做"
- 两者互补:workflow.yaml 不替代 SKILL.md,SKILL.md 引用本规范文件而不重复字段表
