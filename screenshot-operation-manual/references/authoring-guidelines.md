# Authoring Guidelines

## Output Tone

Write in formal, concise Chinese suitable for an enterprise/government operation manual. Prefer concrete UI labels over generic language.

Use these recurring blocks:

- `功能说明：` explain what the page/module is for and who uses it.
- `入口路径：` show navigation such as `托班报名 > 班级管理`.
- `筛选条件：` list filters visible on list pages.
- `功能按钮：` list top-level actions such as `查询、重置、导出、新建`.
- `列表字段：` list visible table/list columns.
- `表单字段说明：` document fields on create/edit/detail dialogs.
- `操作步骤：` write numbered actions using visible button labels.
- `注意：` include constraints, sync rules, permission limits, or status effects.

## Structure Learned From The Sample Manual

The 寒暑托班 sample manual uses this pattern:

- Heading 1: manual title, such as `寒暑托班报名系统操作手册`.
- Heading 2: major modules, such as `后台登录`、`平台看板`、`资源管理`、`托班报名`、`自习室预约`、`系统设置`、`常见操作流程`、`附录：常见问题`.
- Heading 3: pages within a module, such as `2.1 点位管理`.
- Heading 4: dialogs, subfeatures, and workflow steps, such as `新建/编辑点位` or `步骤一：新建班级`.
- Every important page/dialog has one screenshot and an `Image Caption`.
- List pages usually include `筛选条件`、`功能按钮`、`列表字段`.
- Form pages/dialogs include `表单字段说明` and sometimes `注意`.
- End-to-end use cases are grouped under `常见操作流程` with step headings and a short flow summary.

## Screenshot Analysis Checklist

For each screenshot, extract:

- Platform: PC admin, mobile app/miniprogram, or responsive web.
- Page/dialog name from title, breadcrumb, active sidebar item, navbar, or modal header.
- Entry path from visible navigation.
- Main purpose of the screen.
- Primary buttons and destructive actions.
- Filter/search fields.
- Table/list columns and status chips.
- Form fields, required marks, placeholders, dropdowns, upload controls, switches, date/time pickers, and validation hints.
- Permissions implied by disabled/hidden buttons or role-specific text.
- Empty, loading, success, failure, and confirmation states if visible.

If OCR is imperfect, use visible layout plus filenames to infer the page, but label uncertain details as `待确认`.

## PC Backend Writing Rules

For list pages:

1. Start with one-sentence purpose.
2. Insert screenshot.
3. Add `筛选条件` if filters exist.
4. Add `功能按钮` if actions exist.
5. Add `列表字段` if a table exists.
6. Add `操作步骤` only for important workflows.

For create/edit/detail dialogs:

1. Mention how the dialog is opened.
2. Insert screenshot.
3. Add `表单字段说明`.
4. Add save/cancel behavior.
5. Add notes about cascading updates, status changes, and required fields.

## Mobile Writing Rules

For mobile manuals, describe by user task rather than backend module:

- `进入页面` explains tab/menu/card entry.
- `查看信息` covers list/detail browsing and status meaning.
- `提交信息` covers form completion and upload requirements.
- `结果反馈` covers success pages, review status, cancellation, re-submit, or evaluation.

When mobile screenshots show the same flow on several screens, group them under one task section and write a continuous numbered procedure.

## Common Workflow Rules

Add `常见操作流程` when screenshots cover a full business process. Each workflow should include:

- Goal and roles, such as 管理员、家长、教师、现场工作人员.
- Preconditions, such as class/session/course already created.
- Step headings using `步骤一：...`.
- Per-step screenshot when available.
- Result after each step.
- A final `流程概览` line such as `新建班级 -> 家长报名 -> 后台审核 -> 审核通过`.

## Quality Checks

Before delivery:

- No screenshot should appear without a caption.
- No section should be only an image; each image needs explanatory text.
- Do not overclaim behavior that is not visible or provided.
- Keep operation steps short and executable.
- For mobile screenshots, avoid scaling so large that one phone screenshot dominates a page.
- For PC screenshots, keep image width near page width and preserve aspect ratio.
