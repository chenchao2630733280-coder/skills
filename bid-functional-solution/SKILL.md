---
name: "bid-functional-solution"
description: "Create or revise bid/tender functional construction方案 documents from PRDs, requirement specifications, screenshot folders, prototype image sets, flowcharts, or existing DOCX files. Use when you need to turn a requirements document or a folder of screenshots into a 标书功能建设方案 module, reorganize content by 图片、功能说明、功能描述, infer functions from UI images, polish requirement language into bid-ready capability statements, remove out-of-scope functions, or generate/update a professional Word deliverable."
---

# Bid Functional Solution

## Purpose

Transform product requirements into a bid-ready 功能建设方案. The output should read like an implementation capability proposal, not like copied use cases.

Use the document skill for `.docx` work when available. Preserve source facts and screenshots, infer missing structure from screenshot folders when no PRD exists, and rewrite the prose into construction-scope language.

## Input Modes

Choose the mode from the user's source material:

- **Requirements document mode**: use when the user provides a PRD, 需规, Word file, PDF, use-case tables, or mixed text plus screenshots.
- **Screenshot folder mode**: use when the user provides a directory of UI screenshots, flowchart images, exported prototype screens, or loose image files and asks for a bid document directly.
- **Revision mode**: use when the user provides an existing bid document and asks to remove, add, or reorganize functions.

## Core Workflow

1. **Read the source.** Extract headings, function sections, use-case tables, rules, prototype images, flowcharts, and any user-specified exclusions. For screenshot folders, read `references/screenshot-folder.md`.
2. **Normalize the scope.** Build a function inventory grouped by client端、管理后台、接口/数据/运维等 natural modules. In screenshot folder mode, infer modules from folder names, file names, visible page titles, navigation labels, tab names, buttons, table headers, empty states, and repeated layouts. Remove any function the user excludes, including text, headings, table rows, image captions, and related images.
3. **Reorganize each function.** Use this fixed order:
   - `图片`
   - `功能说明`
   - `功能描述`
4. **Rewrite, do not dump.** Convert source use-case language into bid-ready capability language. Avoid labels such as `建设目标`、`服务对象`、`业务流程` unless the user explicitly asks for them.
5. **Use images as evidence.** Insert flowcharts and prototype screenshots near the corresponding function. Keep captions concise and remove screenshots whose content belongs to an excluded function.
6. **Generate the deliverable.** Prefer Word `.docx` for bid documents. Use professional proposal styling, clear heading levels, readable image sizing, and stable page layout.
7. **Validate.** Check for source coverage, excluded-term residue, broken image relationships, malformed DOCX packages, and old use-case labels. Render visually if LibreOffice/soffice is available.

## Content Rules

Read `references/content-patterns.md` before drafting or revising functional prose.

Read `references/screenshot-folder.md` when the source is a folder of screenshots rather than a written requirements document.

For each function:

- `功能说明`: one concise sentence describing the construction capability and scope.
- `功能描述`: bullets listing user-visible or administrator-visible functions, data fields, statuses, controls, validation, and interface behavior.
- Include rules only as functional constraints, not as raw requirement notes.
- Prefer verbs such as `提供`、`支持`、`展示`、`查询`、`维护`、`配置`、`校验`、`同步`、`推送`.
- Remove raw actor-step text like `用户进入...系统返回...用例结束` unless the document explicitly needs a process section.
- In screenshot folder mode, state inferred capabilities conservatively. Do not invent backend rules, permissions, integrations, or validations unless visible in the screenshots or specified by the user.

Example:

```text
功能说明：
提供医院列表展示、查询及详情展示功能，支持按区域、等级等多维度筛选。

功能描述：
- 当前位置定位显示
- 医院列表展示，包含医院名称、等级、地址、预约号源状态
- 号源充足/紧张标识
- 医院详情页面，展示医院基本信息、科室列表、联系方式等
```

## Scope Removal Rules

When the user says to remove a function, remove it everywhere:

- Headings and subsections
- Overview/scope tables
- Function说明 and function描述 bullets
- Use-case-derived descriptions
- Captions and screenshots
- Cross-references in other modules

After regenerating, search the final document text for the removed terms. If any remain, decide whether they are legitimate unrelated uses; otherwise remove them.

## Image Rules

- Keep flowcharts and prototypes attached to the nearest function section.
- If a screenshot contains only an excluded feature, drop it.
- If a screenshot contains a mixed menu/list, edit or replace the image when the user asks for a new graphic.
- For deterministic diagram edits, prefer local image editing or redrawing over image generation so Chinese text remains exact.
- Cap tall screenshots by height and wide screenshots by width to avoid page overflow.

## QA Checklist

Before final delivery:

- Final document opens as a valid DOCX.
- Heading inventory matches the intended function scope.
- `图片 / 功能说明 / 功能描述` appears consistently.
- Excluded feature terms have no unintended residue.
- Old analysis labels such as `建设目标`、`服务对象`、`前置条件`、`业务流程` are absent unless requested.
- Image relationships are intact.
- Visual render QA has passed, or state clearly that rendering could not be completed because `soffice` is unavailable.

## Reference Case

Read `references/session-case.md` when you need a concrete example of transforming a 12320预约挂号系统需规 into a bid-ready function construction方案.
