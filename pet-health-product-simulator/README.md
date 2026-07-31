# pet-health-product-simulator

Codex-compatible skill for simulating and testing a general pet-owner health-triage chatbot.

## Install for one repository

Copy the skill folder to:

```text
<repo>/.agents/skills/pet-health-product-simulator/
```

## Install for the current user

Copy the skill folder to:

```text
$HOME/.agents/skills/pet-health-product-simulator/
```

Restart Codex if it does not appear.

## Invoke

In Codex CLI or IDE, use:

```text
$pet-health-product-simulator 模拟一轮宠物主人完整问诊，显示聊天文案、快捷选项和后台状态。
```

For a pure end-user experience:

```text
$pet-health-product-simulator 进入互动模拟，但不要显示后台状态。我的狗今天精神不好。
```

For product QA:

```text
$pet-health-product-simulator 审查这个宠物问诊流程，找出急症筛查、文案和状态机问题。
```

## Validate

```bash
python scripts/validate_skill.py .
python scripts/validate_session.py assets/session-template.json
```

## Medical safety

This package is a product simulation and prototyping aid. It is not a clinically validated veterinary triage protocol. Production use requires licensed-veterinarian review and jurisdiction-appropriate safety, privacy, and escalation controls.
