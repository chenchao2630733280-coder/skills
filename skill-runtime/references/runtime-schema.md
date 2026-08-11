# runtime.yaml 字段规范(权威)

本文件定义 runtime.yaml 的完整字段规范,是 `validate_runtime.py` 校验时的唯一事实来源。
`skill-runtime/SKILL.md` §二 引用本文件,`skill-auditor` 第 6 维度审查时对照本文件。

## 一、顶层结构

runtime.yaml 是单个 YAML 文件,位于 skill 根目录(如 `game-asset-forge/runtime.yaml`)。顶层字段如下:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `timeout` | integer (秒) | 否 | 300 | 单次执行最大耗时(秒);超过则视为失败 |
| `retry` | object | 否 | `{max:0, backoff:fixed, interval:5}` | 重试策略对象 |
| `inputs` | array | 否 | `[]` | 输入参数校验列表 |
| `outputs` | array | 否 | `[]` | 产物声明列表 |
| `degrade` | array | 否 | `[]` | 降级策略列表 |
| `external_overrides` | string | 否 | null | 引用 adaptive-tuner 产出的 overrides 文件路径(相对 skill 根目录);Phase 4 新增,详见 §九 |

## 二、retry 子字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `max` | integer | 否 | 0 | 最大重试次数(非负整数);0=不重试 |
| `backoff` | string (enum) | 否 | `fixed` | 退避策略,取值 `fixed` / `exponential` |
| `interval` | integer (秒) | 否 | 5 | 重试间隔;`fixed` 模式为固定间隔,`exponential` 模式为初始间隔 |

约束:
- `max` 必须为非负整数;`max=0` 时 `backoff` / `interval` 字段允许缺省(不会被校验)
- `backoff` 取值必须在枚举集合内,其他值标 FAIL
- `interval` 必须为正整数(>0)

## 三、inputs[] 子字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | - | 输入参数名(如 `ASSET_MANIFEST.json`) |
| `schema` | string | 否 | null | JSON Schema 文件路径,相对 skill 根目录 |
| `required` | boolean | 否 | true | 是否必填 |

约束:
- `name` 必须为非空字符串
- `schema` 若声明,必须指向真实存在的 `.json` 文件(由 `validate_runtime.py` 检查路径存在性)
- `required` 必须为布尔值

## 四、outputs[] 子字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | string | 是 | - | 产物路径,相对 skill 根目录,支持 glob |
| `type` | string (enum) | 是 | - | 取值 `file` / `directory` |
| `optional` | boolean | 否 | false | 是否可选产物 |

约束:
- `path` 必须为非空字符串
- `type` 取值必须在 `file` / `directory` 枚举集合内
- `optional` 必须为布尔值

## 五、degrade[] 子字段

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `trigger` | string | 是 | - | 触发条件描述(如"生图失败") |
| `action` | string | 是 | - | 降级动作,建议引用 `degrade-patterns.md` 中的模式名 |
| `target` | string | 否 | null | 降级目标路径(glob 模式) |

约束:
- `trigger` / `action` 必须为非空字符串
- `target` 若声明,必须为合法 glob 模式
- `action` 建议在 `degrade-patterns.md` 列举的已知模式内(超出会标 WARNING,不 FAIL)

## 六、JSON Schema

以下 JSON Schema 可用于程序化校验 runtime.yaml:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "runtime.yaml",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "timeout": {
      "type": "integer",
      "minimum": 0,
      "description": "单次执行最大耗时(秒),默认 300"
    },
    "retry": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "max": { "type": "integer", "minimum": 0 },
        "backoff": { "type": "string", "enum": ["fixed", "exponential"] },
        "interval": { "type": "integer", "minimum": 1 }
      }
    },
    "inputs": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name"],
        "properties": {
          "name": { "type": "string", "minLength": 1 },
          "schema": { "type": ["string", "null"] },
          "required": { "type": "boolean" }
        }
      }
    },
    "outputs": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["path", "type"],
        "properties": {
          "path": { "type": "string", "minLength": 1 },
          "type": { "type": "string", "enum": ["file", "directory", "inline"] },
          "optional": { "type": "boolean" }
        }
      }
    },
    "degrade": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["trigger", "action"],
        "properties": {
          "trigger": { "type": "string", "minLength": 1 },
          "action": { "type": "string", "minLength": 1 },
          "target": { "type": ["string", "null"] }
        }
      }
    },
    "external_overrides": {
      "type": ["string", "null"],
      "description": "引用 adaptive-tuner 产出的 overrides 文件路径(相对 skill 根目录);Phase 4 新增"
    }
  }
}
```

## 七、字段示例

### 7.1 最小声明(仅 timeout)

```yaml
timeout: 120
```

### 7.2 含重试与降级

```yaml
timeout: 600
retry:
  max: 2
  backoff: exponential
  interval: 10
degrade:
  - trigger: 生图失败
    action: 占位图(纯色+文字标识)
    target: assets/role/*/*.png
```

### 7.3 完整声明(含 inputs/outputs)

```yaml
timeout: 600
retry:
  max: 2
  backoff: exponential
  interval: 10
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
  - trigger: 音频生成失败
    action: 静音占位
    target: assets/audio/*.wav
```

### 7.4 含 external_overrides(Phase 4 新增)

```yaml
timeout: 600
retry:
  max: 2
  backoff: exponential
  interval: 10
external_overrides: ../../.trae-cn/tuner-backups/runtime-overrides.yaml
degrade:
  - trigger: 生图失败
    action: 占位图(纯色+文字标识)
    target: assets/role/*/*.png
```

`external_overrides` 引用 adaptive-tuner 产出的 overrides 文件。执行时 workflow-runtime 优先用 overrides 中的值覆盖本地 timeout/retry。

## 八、与 SKILL.md 的关系

- runtime.yaml 是机器可读的运行时契约,`workflow-runtime` / `skill-auditor` / `validate.ps1` 消费
- SKILL.md 是人读文档,描述 skill 的"做什么"和"怎么做"
- 两者互补:runtime.yaml 不替代 SKILL.md,SKILL.md 也不重复 runtime.yaml 的字段表(只引用本文件)

## 九、覆盖优先级与 external_overrides(Phase 4 新增)

### 9.1 三层覆盖优先级

runtime 参数按以下优先级决定最终值(高 → 低):

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1(最高) | `external_overrides` 引用的 overrides 文件 | adaptive-tuner 基于 skill-usage-tracker 数据自动生成的优化参数 |
| 2 | runtime.yaml 本地字段 | skill 作者声明的默认运行时参数 |
| 3(最低) | 默认值(见 §七) | 未声明时的兜底值(timeout=300 等) |

### 9.2 覆盖规则

- `external_overrides` 仅覆盖 `timeout` 和 `retry` 字段,不覆盖 `inputs`/`outputs`/`degrade`(后者是 skill 声明契约,不应被数据驱动修改)。
- overrides 文件中不存在的字段,回退到本地 runtime.yaml 字段。
- overrides 文件中的字段类型必须与本地字段一致(否则 workflow-runtime 标 WARNING 并回退到本地值)。

### 9.3 overrides 文件格式

adaptive-tuner 产出的 `runtime-overrides.yaml` 格式:

```yaml
# adaptive-tuner 产出,勿手动编辑
version: "1.0"
generated_at: "2026-08-06T10:00:00+08:00"
data_source: "skill-usage-tracker usage-stats.json"
overrides:
  game-asset-forge:
    timeout: 900
    retry:
      max: 3
      backoff: exponential
      interval: 15
  game-code-forge:
    timeout: 600
    retry:
      max: 1
      backoff: fixed
      interval: 5
```

### 9.4 校验规则

`validate_runtime.py` 对 `external_overrides` 的校验:
- 字段类型必须为 `string` 或 `null`(null=不使用外部覆盖)
- 若为 string,引用的文件路径必须存在(相对 skill 根目录解析)
- 引用的文件必须是合法 YAML(可被 PyYAML 解析)
- 文件不存在或解析失败标 FAIL

> 注:`workflow-runtime` 的 `run_workflow.py` 解析 `external_overrides` 时,以 runtime.yaml 所在目录
> (即 skill 根目录)为基准。若 runtime.yaml 位于 skill 根目录,则与"相对 skill 根目录"语义一致;
> 若 runtime.yaml 位于子目录,则以 runtime.yaml 所在目录为基准解析(以 `validate_runtime.py` 行为为准)。

### 9.5 合并流程(workflow-runtime 负责)

1. workflow-runtime 执行 step 前,读取 step.skill 的 runtime.yaml
2. 若 runtime.yaml 含 `external_overrides`,读取引用的 overrides 文件
3. 从 overrides 文件中筛选当前 skill 名对应的 overrides
4. 用 overrides 的 timeout/retry 覆盖本地值
5. 最终参数用于执行(设超时、决定重试次数)
6. 若 overrides 文件不存在或解析失败,标 WARNING 并回退到本地值
