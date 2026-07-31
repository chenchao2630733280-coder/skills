# Simulated Risk Model

## Important

Assign an **action level**, not a diagnosis. Use the owner's answers and explicitly show uncertainty. Hard emergency triggers override all scoring.

## Levels

### L1 — 日常健康咨询

Use when the request is preventive or routine and no acute abnormality is described.

Typical action:

- provide reviewed general information;
- record or schedule routine care;
- suggest a routine appointment when appropriate.

### L2 — 可以短期观察

Use when signs are mild, short-lived, and the pet's mental state, eating, drinking, urination, and mobility are largely normal.

Typical action:

- short observation window;
- symptom log;
- clear escalation signs;
- optional veterinarian consultation.

### L3 — 建议咨询兽医

Use when signs are repeated or persistent, or when appetite, mental state, or activity is mildly affected without a clear emergency signal.

Typical action:

- veterinarian consultation within a defined, conservative period;
- continue monitoring;
- prepare a structured summary.

### L4 — 建议尽快就医

Use when signs are significant or worsening, the pet cannot eat normally, pain is obvious, mobility is impaired, or the pet is in a high-risk life stage or has relevant chronic disease.

Typical action:

- arrange prompt in-person veterinary assessment;
- avoid extended home observation;
- explain immediate escalation triggers.

### L5 — 建议立即就医

Use when any hard emergency signal is present.

Typical action:

- stop ordinary interview;
- recommend emergency veterinary contact and transport;
- show conservative transport guidance.

## Evidence presentation

For every assigned level, list:

- `raises_risk`: facts that increase urgency;
- `reduces_immediate_risk`: confirmed absence of selected emergency signs;
- `unknowns`: missing facts that could change the action level.

Do not let `reduces_immediate_risk` become reassurance that veterinary care is unnecessary.

## Escalation modifiers

Treat the following as reasons to raise concern or shorten the recommended time to care:

- very young or elderly pet;
- pregnancy or lactation;
- chronic disease;
- ongoing medication;
- repeated or rapidly worsening symptoms;
- complete refusal of food or water;
- marked pain;
- inability to move normally;
- uncertain toxic or foreign-body exposure.

## Example result shape

```json
{
  "risk": "L3",
  "action_label": "建议咨询兽医",
  "raises_risk": [
    "症状重复出现",
    "食欲下降"
  ],
  "reduces_immediate_risk": [
    "暂未描述呼吸困难",
    "仍可饮水"
  ],
  "unknowns": [
    "是否可能误食",
    "症状是否继续加重"
  ],
  "next_actions": [
    "联系兽医",
    "记录变化",
    "出现红旗信号立即就医"
  ]
}
```
