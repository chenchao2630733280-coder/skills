---
name: "ruanzhu-doc-generator"
description: "Generate Chinese software copyright application documentation DOCX files from product screenshots for PC management backends and mobile apps/miniprograms. Use when asked to create, draft, or package 软著文档, 产品说明书, 操作说明书, 软件著作权材料, or screenshot-based documentation, especially when screenshots may contain both PC后台 and 移动端 and must be split into separate DOCX deliverables."
---

# 软著文档生成器

Use this skill to turn screenshots into complete Chinese software copyright product manuals. Always distinguish PC management backend and mobile端. If screenshots include both, generate two separate DOCX files: one for `pc-admin`, one for `mobile`.

## Workflow

1. Collect screenshots and optional product facts.
   - Accept a folder of `.png`, `.jpg`, `.jpeg`, `.webp`, or `.bmp` screenshots.
   - If the user provides only screenshots, infer modules from filenames, visible UI, screenshot dimensions, and ordering.
   - If the user provides PRD text, README, route names, or business notes, use them to enrich descriptions.
2. Classify endpoints.
   - PC management backend: wide screenshots, browser/admin/table/form layouts, filenames containing `pc`, `admin`, `后台`, `管理端`, `web`.
   - Mobile端: portrait screenshots, phone/miniprogram layouts, filenames containing `mobile`, `app`, `mini`, `小程序`, `移动端`, `家长端`, `用户端`.
   - Never combine endpoints into one soft-copyright manual. Mixed screenshots must produce two DOCX files.
3. Build a metadata file when richer output is needed.
   - Read `references/content-standards.md` for the document skeleton, endpoint-specific wording, and metadata schema.
   - Create a small JSON metadata file if screenshots need corrected titles, custom feature descriptions, dates, company name, or project name.
4. Run the generator.
   - Use the bundled workspace Python when available.
   - Dependencies: the script requires `python-docx` and `Pillow` (see `requirements.txt`). Before running, verify with `python -c "import docx, PIL"`; if it fails, run `pip install -r requirements.txt` first.
   - Command:

```bash
python scripts/build_ruanzhu_doc.py --screenshots <screenshot-folder> --output-dir <output-folder> --project-name "<软件名称>" --company "<公司名称>"
```

   - Optional:

```bash
python scripts/build_ruanzhu_doc.py --screenshots <screenshot-folder> --metadata <metadata.json> --output-dir <output-folder> --force-target both
```

5. Verify output.
   - Open the generated DOCX files or render them with the documents skill if visual fidelity matters.
   - Check that each screenshot has a caption and a functional explanation.
   - Check that PC and mobile manuals have different title, runtime, architecture, UI rules, and feature sections.

## Output Rules

- Generate `软件名称(管理后台)产品说明书.docx` for PC backend screenshots.
- Generate `软件名称(移动端)产品说明书.docx` for mobile screenshots.
- If only one endpoint exists, generate only that endpoint.
- Use Chinese headings and formal soft-copyright prose.
- Include cover, change record, introduction, runtime environment, system architecture, UI design rules, and function display/description.
- Insert screenshots in the function section, scaled to page width, with captions based on endpoint and module title.
- For screenshots that show list/table pages, describe search, filtering, pagination, add/edit/delete/detail/export operations when visible or implied.
- For screenshots that show forms, describe required fields, validation, submit/cancel behavior, and business effects.
- For mobile screenshots, describe user-facing flows such as browse, search, booking, registration, submission, payment if applicable, status query, profile, and message feedback.

## Resources

- `scripts/build_ruanzhu_doc.py`: deterministic DOCX generator. It can classify screenshots, split endpoints, and create one or two manuals.
- `references/content-standards.md`: document skeleton, writing standards, endpoint distinction rules, and metadata JSON schema.
- `assets/sample-pc-admin-template.docx`: sample PC management backend soft-copyright manual used only as a style/content reference.
