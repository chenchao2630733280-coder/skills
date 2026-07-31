# Screenshot Folder Mode

Use this reference when the user provides a folder of screenshots or prototype images and asks Codex to directly generate a 标书功能建设方案.

## Goal

Infer a function construction方案 from visible UI evidence. The output should still use:

1. 图片
2. 功能说明
3. 功能描述

## Intake Procedure

1. List all image files in the provided folder recursively.
2. Preserve the original order when filenames are numbered. Otherwise sort by natural filename order and group by folder.
3. Inspect screenshots visually when possible. Use filenames and folder names as secondary evidence.
4. Extract visible signals:
   - Page title
   - Navigation/menu path
   - Tabs and filters
   - Buttons and actions
   - Form fields and required markers
   - Table columns
   - Cards, status badges, empty states
   - Dialogs, confirmations, success/failure states
   - Mobile vs backend layout
5. Group screenshots into functions. One function may contain several screenshots when they show list/detail/create/edit/confirm states of the same capability.
6. Ask a short clarification only when screenshots cannot reveal the business domain or when a wrong grouping would materially damage the bid document. Otherwise proceed with conservative assumptions.

## Function Inference Patterns

Use these patterns to name and describe functions:

- Screenshot with list/table + search fields -> 查询/列表管理功能
- Screenshot with form fields + save/submit button -> 新增/编辑/提交功能
- Screenshot with detail card + readonly fields -> 详情展示功能
- Screenshot with dashboard cards/charts -> 数据看板/统计分析功能
- Screenshot with upload/image/banner controls -> 内容配置/信息发布功能
- Screenshot with status toggle/up-down shelf/sort -> 上下架/排序/状态管理功能
- Screenshot with modal confirmation -> 删除/退订/解绑/确认操作功能
- Screenshot with login/password/captcha -> 登录认证/安全校验功能
- Mobile page with bottom nav/my page/service grid -> 移动端服务入口/个人中心功能

## Writing Rules For Inferred Content

Use cautious language:

- Prefer `提供...展示功能` when screenshots show only read-only display.
- Prefer `支持...查询/筛选` when filters or search fields are visible.
- Prefer `支持...新增/编辑/删除` only when corresponding buttons or forms are visible.
- Prefer `可展示...状态` when badges, tags, or columns indicate state.
- Do not claim interfaces, real-time synchronization, payment, audit, role permissions, or message push unless visible or provided by the user.

Good inferred example:

```text
功能说明：
提供医院信息列表查询及详情展示功能，支持按关键字和状态筛选医院信息。

功能描述：
- 医院信息列表展示，包含医院名称、等级、地址、状态等字段
- 支持按医院名称、区域、状态等条件查询
- 支持查看医院详情信息
- 支持无数据状态和列表分页展示
```

## Image Placement

- Put the most representative screenshot first.
- Keep related states together: list -> search result -> detail -> create/edit -> confirmation.
- Caption screenshots using inferred page names, not generic filenames, unless the filename is clearer.
- Drop duplicate screenshots unless they show different states.

## Traceability Note

When source material is only screenshots, avoid saying the document is based on a full requirements specification. Use phrasing such as:

```text
本方案依据原型截图及页面功能信息整理。
```

If screenshots are incomplete, add a restrained note in the final response, not necessarily inside the bid document:

```text
部分接口规则和权限规则未在截图中体现，已按可见页面能力进行保守整理。
```
