# Structured Output

用户要求机器可读结果时，在 Markdown 报告之外输出 JSON。不得只输出 JSON 而省略面向产品经理的结论，除非用户明确要求。

## JSON Contract

```json
{
  "schema_version": "1.0",
  "rule_version": "1.1.0",
  "review": {
    "interaction_mode": "audit",
    "scope": "full",
    "downstream_stage": "development",
    "confidence": "high"
  },
  "profile": {
    "change_type": "existing_iteration",
    "product_type": "internal_tool",
    "risk_level": "normal",
    "delivery_target": "human_development"
  },
  "gate": {
    "result": "CONDITIONAL",
    "total_score": 76,
    "blocking_reasons": [],
    "downstream_action": "continue_after_confirmation"
  },
  "category_scores": [],
  "findings": [],
  "traceability": [],
  "consistency_checks": [],
  "scope_boundary": {},
  "acceptance_quality": [],
  "open_questions": [],
  "assumptions": [],
  "reviewed_materials": [],
  "missing_materials": [],
  "optional_extensions": {}
}
```

## 枚举约束

- `interaction_mode`: `audit` / `improve`
- `scope`: `full` / `quick` / `incremental`
- `gate.result`: `READY` / `CONDITIONAL` / `NOT_READY`
- 单项状态：`complete` / `partial` / `missing` / `conflict` / `not_applicable` / `not_reviewed`
- 优先级：`P0` / `P1` / `P2` / `P3`
- 证据来源：`document` / `user_confirmed` / `inherited` / `inferred`

## Finding 最小字段

每个问题至少包含：

- `id`
- `priority`
- `dimension`
- `status`
- `evidence`
- `problem`
- `impact`
- `required_change_or_decision`

## 一致性要求

- JSON 中的门禁、分数和问题必须与 Markdown 报告一致。
- 不输出无法从证据或明确规则得到的字段值。
- 缺失值使用空数组、空对象或 `null`，不要编造。
- Quick 模式必须保留 `not_reviewed` 维度。
- Incremental 模式必须区分本次证据与历史沿用证据。
