# Examples

## Interactive simulation

User:

> 使用这个 skill 进入模拟模式。我的猫今天不吃东西，一直躲着，走路有点奇怪。

Response:

```text
[步骤 1/5：问题描述]

助手：
我理解到目前主要有：
1. 食欲下降；
2. 持续躲藏或精神行为异常；
3. 行走异常。

这些情况是否准确？

可选：
- 准确，继续
- 修改
- 补充其他问题

[模拟状态]
state: CONFIRM_EXTRACTED_ISSUES
known: 猫；食欲下降；持续躲藏；行走异常
unknown: 年龄、精神程度、是否能站立、是否外伤或误食
emergency_flags: none confirmed
risk: UNASSESSED
next: GLOBAL_EMERGENCY_SCREEN
```

## Emergency interruption

User:

> 它一直张嘴喘，舌头发紫。

Response:

```text
⚠️ 这可能属于呼吸急症。

助手：
请立即联系宠物医院或急诊，不建议继续在家等待。前往医院途中尽量减少搬动和应激，不要强行喂食、喂水或自行用药。

可选：
- 联系宠物医院
- 查找附近医院
- 查看途中注意事项
- 继续补充信息

[模拟状态]
state: HANDOFF
known: 张口呼吸；舌头发紫
unknown: none required before routing
emergency_flags: respiratory_distress, abnormal_mucous_membrane_color
risk: L5
next: emergency veterinary care
```

## QA review

When asked to review an existing flow:

1. Map every screen or message to a product state.
2. Check whether emergency screening can be bypassed.
3. Check repeated questions and conflicting controls.
4. Check whether the result explains its evidence.
5. Check diagnosis-like, medication, or false-reassurance language.
6. Return:
   - blocking issues;
   - high-priority improvements;
   - copy revisions;
   - missing states;
   - suggested test cases.
