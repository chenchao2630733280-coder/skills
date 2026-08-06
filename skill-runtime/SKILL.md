---
name: "skill-runtime"
description: "Agent Runtime 层 skill。定义 runtime.yaml 运行时元数据契约(timeout/retry/degrade/external_overrides),被 workflow-runtime 与 skill-auditor 校验。所有 skill 渐进式接入 runtime.yaml。当要统一 skill 运行时行为或校验 skill 是否符合运行时契约时调用。"
---

# skill-runtime

## 一、何时调用

满足以下任一条件即调用本 skill:

- 用户说"统一 skill 运行时行为 / 定义运行时契约 / 加 runtime.yaml"
- 用户说"校验 skill 是否符合运行时契约 / 跑 runtime 契约检查"
- 用户说"扫描全部 skill 的 runtime.yaml 声明情况"
- `workflow-runtime` 在调度 skill 前,需要确认该 skill 是否声明了 runtime.yaml(读契约)
- `skill-auditor` 第 6 维度"运行时契约"审查时,需要对照本 skill 的 schema
- `_shared/validate.ps1` 扩展后,需要校验声明了 runtime.yaml 的 skill 是否符合 schema

**不要**在以下场景调用:
- 用户要直接修改某个 skill 的逻辑(本 skill 只定义契约,不改 skill 逻辑)
- 用户要创建新 skill(用 `skill-creator`)
- 用户只是问"runtime.yaml 怎么写"(纯咨询,直接读 `references/runtime-schema.md` 即可)

本 skill **只读不写**:不直接修改任何 skill 的 runtime.yaml,所有契约校验以报告形式产出。

---

## 二、runtime.yaml 规范

runtime.yaml 是每个 skill **可选**声明的运行时元数据文件,位于 skill 根目录(如 `game-asset-forge/runtime.yaml`)。一旦声明,必须符合本节 schema,否则 `validate_runtime.py` 标 FAIL。

完整字段规范见 `references/runtime-schema.md`,本节给出字段定义速查表:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `timeout` | integer (秒) | 否 | 300 | 单次执行最大耗时;超过则视为失败,触发降级或重试 |
| `retry` | object | 否 | `{max:0}` | 重试策略,见下表 `retry.*` |
| `retry.max` | integer | 否 | 0 | 最大重试次数;0=不重试 |
| `retry.backoff` | string | 否 | `fixed` | 退避策略:`fixed`(固定间隔) / `exponential`(指数退避) |
| `retry.interval` | integer (秒) | 否 | 5 | 重试间隔(fixed 模式)或初始间隔(exponential 模式) |
| `inputs` | array | 否 | `[]` | 输入参数校验列表,每项含 name/schema/required |
| `inputs[].name` | string | 是 | - | 输入参数名(如 ASSET_MANIFEST.json) |
| `inputs[].schema` | string | 否 | null | JSON Schema 文件路径(相对 skill 根目录) |
| `inputs[].required` | boolean | 否 | true | 是否必填 |
| `outputs` | array | 否 | `[]` | 产物声明列表,每项含 path/type/optional |
| `outputs[].path` | string | 是 | - | 产物路径(相对 skill 根目录,支持 glob) |
| `outputs[].type` | string | 是 | - | `file` / `directory` |
| `outputs[].optional` | boolean | 否 | false | 是否可选产物 |
| `degrade` | array | 否 | `[]` | 降级策略列表,每项含 trigger/action/target;模式见 `references/degrade-patterns.md` |
| `degrade[].trigger` | string | 是 | - | 触发条件描述(如"生图失败") |
| `degrade[].action` | string | 是 | - | 降级动作(如"占位图(纯色+文字标识)") |
| `degrade[].target` | string | 否 | null | 降级目标路径(glob 模式) |
| `external_overrides` | string | 否 | null | 引用 adaptive-tuner 产出的 overrides 文件路径(相对 skill 根目录);加载后覆盖本地 timeout/retry 字段(不覆盖 inputs/outputs/degrade,后者是 skill 声明契约)。覆盖优先级:external_overrides > 本地字段 > 默认值 |

> **类型约定**:`integer (秒)` 表示非负整数,单位秒;`string` 表示非空字符串;`boolean` 为 true/false;`array` 缺省为 `[]`,`object` 缺省为对应空对象。
>
> **external_overrides 说明**(Phase 4 新增):引用 `adaptive-tuner` 产出的 `runtime-overrides.yaml`,实现"数据驱动的运行时参数自适应优化"。workflow-runtime 执行前若发现该字段,优先读 overrides 文件中的 timeout/retry 值覆盖本地声明。详见 `references/runtime-schema.md` §九。

---

## 三、runtime.yaml 示例

以 `game-asset-forge` 为例(AI 生图较慢,需重试 + 降级):

```yaml
# game-asset-forge/runtime.yaml
timeout: 600          # AI 生图较慢,10 分钟
retry:
  max: 2
  backoff: exponential  # 指数退避
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

### 含 external_overrides(Phase 4 新增)

```yaml
# game-asset-forge/runtime.yaml(接入 adaptive-tuner 后)
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

`external_overrides` 引用 adaptive-tuner 产出的 overrides 文件,workflow-runtime 执行时优先用 overrides 中的 timeout/retry 覆盖本地值(数据驱动自适应)。

未声明 runtime.yaml 的 skill(如 `game-blueprint`)走默认值(见 §七),`validate_runtime.py scan` 会标"未声明"而非 FAIL。

---

## 四、scripts 调用方式

通用调用格式:

```
python scripts/validate_runtime.py <子命令> [选项]
```

### check(校验单个 skill)

```
python scripts/validate_runtime.py check --skill game-asset-forge
```

- 读取 `<skill 目录>/runtime.yaml`
- 不存在则标 `undeclared`(不 FAIL,因 runtime.yaml 是可选的)
- 存在则用 schema 校验,字段缺失或类型错误标 FAIL
- 在当前工作目录产出 `runtime-contract-report.json`

### scan(扫描全部 skill)

```
python scripts/validate_runtime.py scan
```

- 扫描 `<工作台根>/` 下全部 skill 子目录
- 对每个 skill 跑 check 逻辑,汇总为一份报告
- 在当前工作目录产出 `runtime-contract-report.json`

### 输出报告字段

```json
{
  "command": "check | scan",
  "skills": [
    {
      "skill": "game-asset-forge",
      "declared": true,
      "status": "PASS | FAIL | UNDECLARED",
      "errors": ["字段 timeout 类型错误:期望 integer,实际 string"]
    }
  ],
  "summary": { "total": 54, "declared": 3, "pass": 3, "fail": 0 },
  "error": null,
  "timestamp": "2026-08-06T10:00:00+08:00"
}
```

退出码:`0`=全部通过(含 UNDECLARED);`1`=有 FAIL 项。

---

## 五、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/runtime-schema.md` | (1) 用户问"runtime.yaml 字段怎么写";(2) `validate_runtime.py` 校验时内嵌该 schema;(3) `skill-auditor` 第 6 维度审查时对照 |
| `references/degrade-patterns.md` | (1) skill 作者声明 `degrade` 字段前查阅模式清单;(2) `skill-auditor` 校验 `degrade[].action` 是否在已知模式内 |

两份 references 均为**懒加载**:仅在需要时读取,不强制调用方一次性全读。

---

## 六、关键约束

1. **只读不写**:本 skill 不修改任何 skill 的 runtime.yaml,所有问题以报告形式产出。
2. **runtime.yaml 是可选的**:不强制所有 skill 立即声明,渐进式接入(先在 `game-asset-forge` / `tool-deploy-ops` 等高风险 skill 试点)。
3. **声明后必符 schema**:一旦声明 runtime.yaml,必须符合 `references/runtime-schema.md` 的 JSON Schema,否则 `validate_runtime.py` 标 FAIL。
4. **不修改 skill 逻辑**:runtime.yaml 只定义元数据契约(timeout/retry/inputs/outputs/degrade),不改变 skill 的实际执行逻辑;真正的执行由 `workflow-runtime` 或宿主负责。
5. **默认值兜底**:未声明的字段按 §七 默认值处理。
6. **失败不阻塞**:`validate_runtime.py` 失败时回填 `error` 字段并返回 exit 1,但不会中断调用方流程(由调用方决定是否继续)。
7. **external_overrides 覆盖优先级**(Phase 4 新增):`external_overrides` > runtime.yaml 本地字段 > 默认值。`external_overrides` 引用的文件必须存在且为合法 YAML,否则 `validate_runtime.py` 标 FAIL。覆盖合并由 `workflow-runtime` 在执行前完成(见 `../workflow-runtime/SKILL.md` §十三)。

---

## 七、默认值表

未声明 runtime.yaml 或字段缺省时,按以下默认值处理:

| 字段 | 默认值 | 含义 |
|------|--------|------|
| `timeout` | `300` | 5 分钟超时 |
| `retry.max` | `0` | 不重试 |
| `retry.backoff` | `fixed` | 固定间隔退避 |
| `retry.interval` | `5` | 重试间隔 5 秒 |
| `inputs` | `[]` | 无输入校验(信任调用方传入) |
| `outputs` | `[]` | 无产物声明(由 SKILL.md 文本描述) |
| `degrade` | `[]` | 无降级策略(失败即失败,交调用方处理) |
| `external_overrides` | `null` | 无外部覆盖(使用本地字段 + 默认值) |

---

## 八、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `workflow-runtime` | 消费方 | 调度 skill 前读 runtime.yaml,按 `timeout` 设定超时、按 `retry` 决定重试、按 `degrade` 决定降级 |
| `skill-auditor` | 校验方 | 第 6 维度"运行时契约"对照本 skill 的 schema 审查(见 `skill-auditor/references/audit-runtime.md`) |
| `_shared/validate.ps1` | 校验方 | 扩展后检查"声明了 runtime.yaml 的 skill 内容必须符合 skill-runtime schema" |
| `failure-casebook` | 协作方 | 降级触发后,失败时显式调用 `failure-casebook` record 子命令记录失败码 + 修复方法,下次同名 skill 执行前注入预防提示 |
| `adaptive-tuner` | 覆盖方 | 产出 `runtime-overrides.yaml`;runtime.yaml 的 `external_overrides` 字段引用该文件,实现数据驱动的参数自适应优化(Phase 4 新增) |
| `skill-creator` | 上游 | 新建 skill 时可参考本 skill 的 schema 决定是否声明 runtime.yaml |

---

## 九、质量检查清单

### 9.1 只读不写约束

- [ ] SKILL.md 已声明"只读不写",`validate_runtime.py` 仅读 runtime.yaml、写报告,不修改任何 skill 文件。

### 9.2 产物自评项

- [ ] `python scripts/validate_runtime.py --help` 不报错,`check` / `scan` 子命令均可见。
- [ ] `python scripts/validate_runtime.py check --help` / `scan --help` 子命令 help 正常。
- [ ] check 缺失 runtime.yaml 时标 `UNDECLARED`(非 FAIL),exit 0。
- [ ] check 存在 runtime.yaml 但字段类型错误时标 `FAIL`,exit 1。
- [ ] scan 能扫描工作台全部 skill,汇总 `summary` 字段含 total/declared/pass/fail。
- [ ] 报告写入当前目录 `runtime-contract-report.json`,字段齐全(command/skills/summary/error/timestamp)。
- [ ] `references/runtime-schema.md` 含完整字段规范表 + JSON Schema,可被 `validate_runtime.py` 内嵌引用。
- [ ] `references/degrade-patterns.md` 含 7 类降级模式清单,每类含触发条件/动作/适用 skill。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
