# PRD Quality Review

## Review Scope

- PRD:
- Rule version:
- Interaction mode: Audit / Improve
- Mode: Full / Quick / Incremental
- Target downstream stage:
- Reviewed materials:
- Missing materials:
- Output formats: Markdown / Markdown + JSON
- Optional extensions: Domain risk prompts / AI readiness / None

## Review Profile

- Change type: New product / Existing iteration / Fix or compliance change
- Product type: User product / Internal tool / Platform capability / Data or AI product
- Risk level: Normal / High
- Delivery target: Human development / AI assisted / AI code generation
- Profile assumptions:

## Gate

- Result: READY / CONDITIONAL / NOT_READY
- Total score:
- Blocking reasons:
- Downstream action: Continue / Continue after confirmation / Stop and revise
- Review confidence: High / Medium / Low

## Scorecard

| Category | Dimension | Evidence location and excerpt | Score | Finding | Confidence |
|---|---|---|---:|---|---|
| Product clarity | Objective and problem | File > section > shortest useful excerpt | 0/1/2/N/A/N/R | | High/Medium/Low |

## Findings

| Priority | Dimension | Evidence | Problem | Impact | Required change or decision |
|---|---|---|---|---|---|
| P0/P1/P2/P3 | | | | | |

## Requirement Traceability

至少列出 P0 和高风险 P1；没有固定需求 ID 时使用功能名、用户故事或章节标题。

| Requirement key | Goal or problem | User scenario | Function or requirement | Key rules | Acceptance criteria | Trace result |
|---|---|---|---|---|---|---|
| | | | | | | Complete / Partial / Broken |

## Cross-section Consistency

| Source A | Source B | Consistency result | Conflict or orphan reference | Impact |
|---|---|---|---|---|
| Scope / feature list / flow / rule / state / permission / acceptance / metric | | Consistent / Conflict / Orphan | | |

## Scope Boundary

- Included:
- Excluded:
- Deferred:
- Existing behavior retained:
- External system or team boundary:
- Unclear boundary:

## Acceptance Quality

| Requirement key | Preconditions | Trigger or action | Expected result | Failure result | Boundary values | Result |
|---|---|---|---|---|---|---|
| | | | | | | Complete / Partial / Missing |

## Confirmed Decisions

- Confirmed:
- User-confirmed during Improve:
- Reasonable assumptions:
- Open questions:
- N/A decisions and reasons:
- Not reviewed dimensions and scope reason:

## Recommended PRD Changes

列出具体章节、应补充的内容和建议文本方向。不要替用户决定尚未确认的重大业务规则。

## Optional AI Readiness Appendix

仅在启用时输出：

- Result: READY / PARTIAL / NOT_READY
- Target generation scope:
- Available downstream inputs:
- Missing downstream inputs:
- Product ambiguities that block generation:
- Design or technical artifacts still required:

## Handoff

- Constraints that downstream work must preserve:
- Items allowed to be resolved later:
- Next review trigger:
- Evidence inherited from a previous review:

## Machine-readable Output

- JSON requested: Yes / No
- JSON and Markdown consistency checked: Yes / No / N/A
