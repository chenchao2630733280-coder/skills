# Execution Engine Contract

执行层把产品配置转换为稳定的审核过程。

## 运行配置

内部至少维护：

- `interaction_mode`: `audit` 或 `improve`
- `review_scope`: `full`、`quick` 或 `incremental`
- `downstream_stage`
- `profile`
- `optional_extensions`
- `custom_rules`
- `output_formats`
- `rule_version`

这些字段是执行层内部表示，不要求产品经理填写。

## Audit 状态流

`CONFIGURE → PROFILE → COLLECT → SCAN → TRACE → SCORE → GATE → REPORT → COMPLETE`

- 材料不足但仍可评审时继续，并降低置信度。
- 核心材料不足导致无法可靠判断时，直接进入 `GATE = NOT_READY`。
- Audit 默认不在中途提问；将未决项集中写入报告。

## Improve 状态流

`CONFIGURE → PROFILE → COLLECT → SCAN → TRACE → PRIORITIZE → ASK_ONE → RECORD → RESCAN → SCORE → GATE → REPORT → COMPLETE`

规则：

1. 先完成预扫描，再提问。
2. 只询问会改变门禁、评分或高优先级结论的问题。
3. 每轮只问一个问题，并显示已确认和待确认数量。
4. 用户回答记录为 `user_confirmed`，不能替换或伪造 PRD 原文。
5. 最多连续追问 5 个；其余问题进入开放项。
6. 每次回答后只重检受影响维度。

## 证据来源

- `document`: PRD 或关联材料中的可定位内容。
- `user_confirmed`: Improve 对话中由用户明确确认。
- `inherited`: 增量审核中仍有效的历史证据。
- `inferred`: 合理推断，只能支持提问或建议，不能单独支撑 `Complete`。

## 规则选择

1. 始终加载核心清单、评分和证据纪律。
2. 根据画像决定 `N/A`、风险级别和可选规则包。
3. 高风险领域按需加载行业风险提示。
4. AI 代码生成目标按需加载 AI 开发准备度。
5. 自定义规则只能增加检查或提高严格度；降低核心门禁需明确记录为风险接受，且不得生成虚假证据。

## 终止条件

- `READY`、`CONDITIONAL` 或 `NOT_READY` 已确定。
- 所有输出与同一规则版本一致。
- Markdown 与 JSON 中的门禁、分数和问题数量一致。
