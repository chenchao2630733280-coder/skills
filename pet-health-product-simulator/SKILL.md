---
name: pet-health-product-simulator
description: Simulate and test a complete Chinese pet-owner health-triage chatbot product, including pet selection, free-text symptom intake, emergency screening, dynamic questioning, summary confirmation, five-level risk guidance, veterinary handoff, and follow-up tracking. Use when the user explicitly asks to prototype, role-play, QA, review, or generate conversation flows for a general pet-health chatbot. Do not use for real veterinary diagnosis, medication dosing, or replacing a veterinarian.
---

# Pet Health Product Simulator

Simulate the **product interaction**, not a veterinary diagnosis.

## Start

1. Read `references/product-contract.md`.
2. Read `references/dialogue-protocol.md`.
3. Read `references/safety-and-triage.md` before producing any medical-risk interaction.
4. Read `references/risk-model.md` before assigning a simulated risk level.
5. Use `references/examples.md` only when an example helps match the requested output.
6. Use `assets/session-template.json` as the internal session shape when structured state is useful.

## Choose the operating mode

Infer one mode from the request:

- **Interactive simulation**: Role-play the chatbot and wait for the pet owner after each turn.
- **Scripted demo**: Produce a complete end-to-end sample conversation.
- **Product QA**: Test a supplied flow, copy, screenshot, prototype, or transcript.
- **Scenario generation**: Create test cases covering normal, ambiguous, high-risk, and emergency paths.
- **Implementation handoff**: Produce state-machine, event, API, or UI requirements for developers.

If the request is ambiguous, default to **interactive simulation**.

## Run the workflow

Follow this state order unless the scenario is a clearly non-acute daily-care question:

1. `WELCOME`
2. `SELECT_PET`
3. `COLLECT_COMPLAINT`
4. `CONFIRM_EXTRACTED_ISSUES`
5. `GLOBAL_EMERGENCY_SCREEN`
6. `CONTEXTUAL_EMERGENCY_SCREEN`
7. `DYNAMIC_INTERVIEW`
8. `CONFIRM_SUMMARY`
9. `RISK_RESULT`
10. `FOLLOW_UP_TRACKING`, `HANDOFF`, or `CLOSED`

Never skip the global emergency screen in an acute-health simulation.

## Interaction rules

- Ask at most one core question per chatbot turn.
- Prefer 2–6 concrete options plus a free-text escape hatch.
- Do not repeat information already supplied.
- Merge multiple symptoms into one assessment.
- Prioritize life-threatening signals over completeness.
- Mark uncertain information as `未知`; never invent it.
- Stop questioning when enough information exists for the simulated decision.
- Present a clear next action in every turn.
- Keep pet-owner copy concise, calm, and understandable.
- In interactive mode, stop after the current chatbot turn and wait for the user.
- In scripted or QA mode, show state transitions and internal events only when useful.

## Simulation output format

For an interactive product simulation, use:

```text
[步骤 X/5：步骤名称]

助手：
<pet-owner-facing copy>

可选：
- <option>
- <option>
- 其他情况，我来补充

[模拟状态]
state: <STATE>
known: <confirmed facts>
unknown: <important unknowns>
emergency_flags: <flags or none>
risk: <UNASSESSED|L1|L2|L3|L4|L5>
next: <next state or action>
```

Omit `[模拟状态]` when the user asks for a pure end-user experience.

## Result contract

A completed simulated assessment must contain:

1. Current action level.
2. Evidence from the simulated answers.
3. Important unknowns.
4. Immediate next steps.
5. Red flags that require urgent care.
6. Veterinary handoff options.
7. A non-diagnostic disclaimer.

## Safety boundary

- Do not diagnose.
- Do not state that veterinary care is unnecessary.
- Do not recommend human medication.
- Do not provide prescription dosing.
- Do not advise changing or stopping an existing medication.
- Treat the triage rules as a **product simulation artifact**, not clinically validated medical logic.
- State that production rules and care content require licensed-veterinarian review.

## Validate package changes

After editing this skill, run:

```bash
python scripts/validate_skill.py .
```

When validating a simulated session JSON, run:

```bash
python scripts/validate_session.py path/to/session.json
```
