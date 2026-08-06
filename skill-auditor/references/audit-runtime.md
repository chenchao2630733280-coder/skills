# 维度 6:运行时契约审查规则

> 本文件定义"运行时契约审查"模式的审查规则。仅当审查模式为"运行时契约审查"时读取本文件。
> runtime.yaml 字段规范的权威来源:`../skill-runtime/references/runtime-schema.md`。

---

## 一、适用场景

运行时契约审查模式用于:校验 skill 声明的 runtime.yaml 是否符合 `skill-runtime` 规范。与静态审查(维度 1~4)和执行后评测(维度 5)的区别:

| 对比项 | 静态审查(维度 1~4) | 执行后评测(维度 5) | 运行时契约审查(维度 6) |
|---|---|---|---|
| 审查对象 | skill 定义文件(SKILL.md/references) | skill 的实际产出物 | skill 的 runtime.yaml |
| 审查时机 | skill 设计/修改后 | skill 执行后 | skill 声明 runtime.yaml 后 |
| 核心问题 | skill 写得对不对 | skill 产出好不好 | runtime.yaml 契约合不合规 |
| 阻断权 | 无(建议性) | 无(标 WARNING 进报告) | FAIL 项阻断(validate.ps1 扩展后) |

> runtime.yaml 是可选的:未声明的 skill 不触发本维度,仅在"扫描全部 skill"时标记为 UNDECLARED(非 FAIL)。

---

## 二、四个检查项

### 2.1 runtime.yaml 存在性(R1)

检查声明了 runtime.yaml 的 skill 是否实际有该文件。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| R1.1 | 文件存在 | 若 SKILL.md 或其他文件显式引用了 runtime.yaml,则 skill 目录下必须存在该文件 | `R1-FILE-MISSING` |

> 注:runtime.yaml 整体是可选的。R1.1 仅在 SKILL.md **显式引用** runtime.yaml 时触发;否则跳过本项,标 UNDECLARED。

### 2.2 schema 符合度(R2)

检查 runtime.yaml 字段是否符合 `../skill-runtime/references/runtime-schema.md` 的 JSON Schema。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| R2.1 | 字段类型正确 | timeout/retry.max/retry.interval 为 integer;retry.backoff 为 string;inputs[].required/outputs[].optional 为 boolean | `R2-SCHEMA-INVALID` |
| R2.2 | 必填字段存在 | inputs[].name、outputs[].path、outputs[].type、degrade[].trigger、degrade[].action 均存在 | `R2-SCHEMA-INVALID` |
| R2.3 | 无未知字段 | 无 schema 未声明的顶层/嵌套字段(additionalProperties:false) | `R2-SCHEMA-INVALID` |
| R2.4 | 枚举值合法 | retry.backoff ∈ {fixed, exponential};outputs[].type ∈ {file, directory} | `R2-SCHEMA-INVALID` |

### 2.3 契约一致性(R3)

检查 runtime.yaml 与 SKILL.md 声明的一致性。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| R3.1 | timeout 合理 | timeout 值与 skill 实际耗时预期匹配(如 AI 生图类 >300s,纯校验类 <60s) | `R3-CONTRACT-MISMATCH` |
| R3.2 | retry 与失败回退一致 | retry.max 与 SKILL.md 失败回退策略表声明一致(若 SKILL.md 声明"不重试",retry.max 应为 0) | `R3-CONTRACT-MISMATCH` |
| R3.3 | inputs 与 SKILL.md 一致 | inputs[].name 与 SKILL.md 声明的输入参数一致(无遗漏/无多余) | `R3-CONTRACT-MISMATCH` |
| R3.4 | outputs 与产物路径表一致 | outputs[].path 与 SKILL.md 产物路径表声明的路径一致 | `R3-CONTRACT-MISMATCH` |

### 2.4 降级策略有效性(R4)

检查 degrade 字段引用的策略是否有效。

| # | 检查项 | 通过条件 | 失败码 |
|---|---|---|---|
| R4.1 | degrade 策略存在 | degrade[].action 在 `../skill-runtime/references/degrade-patterns.md` 列举的已知模式内(超出标 WARNING,不 FAIL) | `R4-DEGRADE-INVALID` |
| R4.2 | degrade target 路径有效 | degrade[].target 若声明,必须是合法 glob 模式,且与 outputs[].path 有交集 | `R4-DEGRADE-INVALID` |

---

## 三、严重级别

| 级别 | 含义 | 示例 |
|---|---|---|
| **CRITICAL** | runtime.yaml 无法被 workflow-runtime 消费 | runtime.yaml 不存在(声明后);schema 严重违反(类型错误/必填缺失) |
| **MAJOR** | 契约不一致,影响调度正确性 | retry 与 SKILL.md 失败回退矛盾;outputs 与产物路径表不一致 |
| **MINOR** | 优化空间,不阻断 | timeout 偏离预期;degrade action 不在已知模式内(WARNING) |
| **INFO** | 提示性 | 未声明 runtime.yaml(UNDECLARED);默认值兜底生效 |

---

## 四、评测流程

```
1. 读取 skill 目录,确认是否声明 runtime.yaml
   - 未声明且 SKILL.md 未引用 → 标 UNDECLARED,跳过 R2~R4
   - 声明了 → 读取 runtime.yaml 内容
2. R1 存在性:若 SKILL.md 引用 runtime.yaml 但文件缺失 → R1-FILE-MISSING(CRITICAL)
3. R2 schema 符合度:对照 ../skill-runtime/references/runtime-schema.md 的 JSON Schema 逐字段校验
4. R3 契约一致性:读取 SKILL.md 的失败回退策略表/产物路径表/输入声明,与 runtime.yaml 对照
5. R4 降级策略有效性:读取 ../skill-runtime/references/degrade-patterns.md,校验 degrade[].action 是否在已知模式内
6. 产出 runtime-audit-report.json
```

---

## 五、产出格式

### 5.1 JSON 工件(runtime-audit-report.json)

```json
{
  "auditMode": "runtime",
  "skill": "{skill 名}",
  "runtimeYamlPath": "{runtime.yaml 路径,若不存在为 null}",
  "declared": true,
  "timestamp": "{ISO8601}",
  "conclusion": "PASS|FAIL|UNDECLARED",
  "checks": [
    {
      "id": "R1.1",
      "name": "文件存在",
      "result": "PASS|FAIL|SKIP",
      "severity": "CRITICAL|MAJOR|MINOR|INFO",
      "detail": "{详情}",
      "code": "{失败码}"
    }
  ],
  "summary": {
    "total": 11,
    "passed": 10,
    "failed": 1,
    "skipped": 0,
    "critical": 1,
    "major": 0,
    "minor": 0,
    "info": 0
  },
  "errors": ["{错误描述}"]
}
```

### 5.2 与 skill-runtime/validate_runtime.py 的关系

- 本维度审查产出 `runtime-audit-report.json`(人读 + 机读)
- `../skill-runtime/scripts/validate_runtime.py` 产出 `runtime-contract-report.json`(机器校验)
- 两者结论应一致:本维度审查若标 FAIL,validate_runtime.py 也应标 FAIL
- 差异:本维度额外做 R3 契约一致性(与 SKILL.md 对照)和 R4 降级模式校验,validate_runtime.py 仅做 R1+R2
