# _shared/references — 工作台共享参考文件（唯一事实来源）

本目录存放 AI Agent Skills 工作台多个 Skill 共用的参考文件，是这些文件的**唯一事实来源（Single Source of Truth）**，用于替代过去每个 Skill 各存一份拷贝导致的版本漂移问题。

## 目录内容

```text
_shared/references/
├── ui-design-standards.md          # 通用 UI 设计规范（移动端默认档案）
├── pc_admin_ui_spec.md             # PC 管理端权威设计规范（vue-admin-plus / Element Plus）
├── engineering-constraints.md      # 工程通用约束（10 条，plan-system-implementation / build-working-system 共用）
└── schemas/
    ├── acceptance-matrix.example.json  # 验收矩阵结构（plan-system-implementation 产出）
    ├── actions.example.json            # 页面动作结构
    ├── annotations.example.json        # 页面标注结构（SXX，generate-prototype 产出）
    ├── architecture.example.json       # 架构契约结构（plan-system-implementation 产出）
    ├── business-rules.example.json     # 业务规则结构（generate-system-prd 产出）
    ├── components.example.json         # 复用组件结构
    ├── data-model.example.json         # 数据模型结构（generate-system-prd 产出）
    ├── design-tokens.default.json      # 默认设计 Token（v1.3）
    ├── html-build-report.example.json  # HTML 构建报告结构
    ├── navigation.example.json         # 导航结构
    ├── overlays.example.json           # 弹层结构
    ├── pages.example.json              # 页面注册表（原型富化后完整结构）
    ├── permissions.example.json        # 权限结构（generate-system-prd 产出）
    ├── pipeline-context.example.json   # 流水线上下文（来源与置信度标记）
    ├── release-manifest.example.json   # 发布清单结构（plan-system-implementation 产出）
    ├── state-machines.example.json     # 状态机结构（generate-system-prd 产出）
    ├── task-board.example.json         # 任务板结构（plan-system-implementation 产出）
    └── traceability.example.json       # 追溯表结构（plan-system-implementation 产出）
```

## 使用规则

1. **编辑只在本目录进行**。修改本目录文件即对所有引用它的 Skill 生效；不要在任何 Skill 内重新创建同名文件。
2. **引用方式**：各 Skill 的 SKILL.md 使用相对路径引用，如 `../_shared/references/schemas/design-tokens.default.json`。
3. **阶段特有文件保留在产出方 Skill 内**，不进入本目录。例如：
   - `generate-system-prd/references/`：`prd-document-template.md`（13章+附录完整模板）、`pages.example.json`（PRD 阶段快照）、`business-rules`、`data-model`、`permissions`、`state-machines`、`validation-report`、`decision-log`、`project`、`prd-stage-boundary.md`、`brainstorming-gate.md`、`product-design-standards.md`
   - `generate-prototype/references/`：`prototype-design-standards.md`、`page-archetypes`、`prototype-output-profile`、`prototype-validation-report`
   - `generate-html-pages/references/`：`interaction-patterns.md`（双端通用交互模板，子skill通过 `../generate-html-pages/references/` 跨目录引用）
   - `generate-html-pc-admin/references/`：`pc-admin-navigation-style.md`、`examples/pc-admin-shell-demo.html`
   - `generate-html-mobile/references/`：`mobile-product-design-standards.md`、`schemas/mobile-page-patterns.example.json`、`examples/mobile-pattern-demo.html`
   - `generate-portal/references/`：`annotation-standards.md`、`schemas/portal-build-report.example.json`
   - `plan-system-implementation/references/schemas/`：`implementation-plan`、`task-board`、`traceability`、`acceptance-matrix`、`release-manifest`
4. **工件所有权不变**：本目录只统一"结构示例与默认规范"的存放位置，不改变各 JSON 工件的生产者归属（如 `annotations.json` 仍由 `generate-prototype` 创建）。
5. **单独分发某个 Skill 时**：将其 SKILL.md 中引用的本目录文件复制回该 Skill 的 `references/` 内，并把引用路径改回本地相对路径。

## 历史背景

此前 18 个 schema 示例与 `ui-design-standards.md` 在 3~4 个 Skill 中各存一份拷贝，曾发生 design-tokens v1.0/v1.1/v1.3 三版本并存、边框色与页面背景色不一致等实际漂移。2026-07 统一收敛至本目录。
