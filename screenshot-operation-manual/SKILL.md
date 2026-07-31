---
name: "screenshot-operation-manual"
description: "Generate complete PC web admin and mobile app operation manuals from screenshots, screen recordings, or screenshot folders. Use when you must analyze provided UI screenshots and produce a professional user guide/manual in DOCX/PDF/Markdown/HTML, including module descriptions, screenshots with captions, filters, buttons, list fields, form fields, operation steps, workflow use cases, mobile-specific flows, and FAQ-style appendices."
---

# Screenshot Operation Manual

## Overview

Use this skill to turn UI screenshots into a complete operation manual. It supports PC management backends and mobile apps/miniprograms, including mixed manuals where a backend operation triggers a mobile-side user flow.

The default final deliverable is a `.docx` manual generated from a structured JSON spec using `scripts/build_manual_docx.py`; also provide PDF or Markdown when the user asks.

## Workflow

1. Collect all screenshots and preserve their source order.
   - Prefer filenames like `01-login.png`, `02-class-list.png`, `m-03-submit-form.png`.
   - If filenames are vague, infer order from folder order, timestamps, visible navigation, and screen transitions.
   - Separate platforms into `PC管理后台`, `移动端`, or `PC+移动端联动`.

2. Analyze each screenshot visually.
   - Identify page title, navigation path, key buttons, filter fields, table/list columns, forms, dialogs, empty/error states, and visible status values.
   - For mobile screenshots, identify tab bar entry, page state, primary CTA, form fields, validation hints, and result pages.
   - Read `references/authoring-guidelines.md` before drafting content.

3. Build a `manual_spec.json`.
   - Use `references/manual-spec-format.md` for the expected structure.
   - Do not invent hidden business rules. Mark uncertain behavior as `待确认` or write conservative user-facing text.
   - Prefer concise operation steps that match visible UI labels.

4. Generate the document.
   - Dependencies: the script requires `python-docx` (see `requirements.txt`). Before running, verify with `python -c "import docx"`; if it fails, run `pip install -r requirements.txt` first.
   - Run `python scripts/build_manual_docx.py --spec manual_spec.json --output 操作手册.docx`.
   - Use the bundled workspace Python when available.
   - If output needs PDF, render/convert the DOCX with the available document tooling and visually verify pages.

5. Validate the manual before delivery.
   - Confirm every supplied screenshot is either used or intentionally excluded.
   - Check heading numbering, screenshot captions, table readability, mobile screenshot sizing, and whether cross-platform flows are clear.
   - For Chinese government/enterprise systems, use formal but readable Chinese: `功能说明`、`操作步骤`、`字段说明`、`注意事项`、`常见操作流程`.

## Manual Shape

For PC management backends, organize by sidebar/module:

1. Title page
2. Directory
3. Login and homepage/dashboard
4. Business modules
5. System settings
6. Common operation workflows
7. FAQ/appendix

For mobile manuals, organize by user journey:

1. Login/authorization
2. Home/tab navigation
3. Browse/search
4. Create/submit/reserve/register
5. Detail/status/result pages
6. Cancellation/modification/evaluation
7. FAQ/appendix

For mixed PC/mobile manuals, keep platform chapters separate, then add `常见操作流程` showing end-to-end flows across roles.

## Resources

- `references/authoring-guidelines.md`: Read before drafting manual text; includes screenshot analysis and writing rules based on the provided寒暑托班 sample.
- `references/manual-spec-format.md`: Read before creating `manual_spec.json`.
- `scripts/build_manual_docx.py`: Generate a formatted DOCX manual from `manual_spec.json` and image files.
