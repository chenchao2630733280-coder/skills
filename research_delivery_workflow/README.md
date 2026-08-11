# Research Delivery Workflow Skill v2.2

这是一个**领域中立、项目无关**的“调研 → 业务分析 → 产品需求 → 技术交付 → 实施计划”工作流 Skill。

## 设计方式

- 对外：1 个 Skill；
- 对内：5 个 Stage；
- 末端：1 个统一 Quality Gate。

## 最重要的边界

业务分析阶段只负责恢复当前业务现状，不生成 PRD，不生成技术方案。

业务分析输出固定为十章《当前业务调研分析报告》。

产品阶段输出需求池、产品能力架构、终端策略、产品导航和页面结构完整的 PRD 初稿，并要求架构与页面节点可追溯、单端/多端约束明确、候选范围与已确认主线清晰区分。

## 目录

```text
SKILL.md
workflow.yaml
stages/
gates/
templates/
references/
schemas/
scripts/
```

## 使用建议

将整个目录作为一个 Skill 安装或纳入 Agent 工作区，由 `SKILL.md` 作为唯一入口。

用户可以只执行某个阶段，也可以请求完整交付链路。
