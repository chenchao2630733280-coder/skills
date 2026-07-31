# Manual Spec Format

Create a UTF-8 JSON file named `manual_spec.json`. The generator accepts missing optional fields, but richer specs produce better manuals.

## Minimal Example

```json
{
  "title": "寒暑托班报名系统操作手册",
  "platform": "PC管理后台",
  "version": "V1.0",
  "audience": "系统管理员、业务审核人员",
  "sections": [
    {
      "title": "托班报名",
      "description": "托班报名模块用于维护班级、预约记录和报名审核数据。",
      "pages": [
        {
          "title": "班级管理",
          "nav_path": "托班报名 > 班级管理",
          "purpose": "班级管理用于新建、查看、公开和维护托班班级信息。",
          "screenshot": "screenshots/班级管理列表.png",
          "caption": "班级管理列表",
          "filters": ["所属区县", "所属街道", "班级名称", "服务模式", "状态"],
          "actions": ["查询", "重置", "导出", "新建"],
          "columns": ["班级编号", "企业名称", "点位名称", "报名时间", "名额情况", "联系人", "状态", "操作"],
          "steps": [
            "在筛选区输入查询条件。",
            "点击【查询】刷新班级列表。",
            "点击【新建】进入班级新建页面。"
          ],
          "notes": ["公开后，移动端用户可查看并进行报名。"]
        }
      ]
    }
  ],
  "workflows": [
    {
      "title": "新建托班班级 -> 家长报名 -> 审核通过",
      "summary": "管理员创建班级并公开后，家长在移动端提交报名，后台完成审核。",
      "steps": [
        {"title": "步骤一：新建班级", "actor": "管理员", "action": "在班级管理中点击【新建】并保存班级。", "result": "生成待公开班级。"},
        {"title": "步骤二：家长端报名", "actor": "家长", "action": "在移动端选择班级并提交报名信息。", "result": "生成待审核报名记录。"}
      ],
      "flow": ["新建班级", "公开班级", "家长报名", "后台审核", "审核通过"]
    }
  ],
  "faq": [
    {"question": "为什么移动端看不到班级？", "answer": "请检查班级是否已公开、报名时间是否开始，以及是否存在角色或区域权限限制。"}
  ]
}
```

## Top-Level Fields

- `title`: Manual title.
- `subtitle`: Optional subtitle.
- `platform`: `PC管理后台`, `移动端`, or `PC+移动端联动`.
- `version`: Manual version.
- `audience`: Intended users.
- `owner`: System owner or project name.
- `generated_date`: Date text.
- `screenshot_root`: Optional base folder for relative screenshot paths.
- `sections`: Major chapters.
- `workflows`: End-to-end common operation flows.
- `faq`: Appendix questions.

## Section Fields

- `title`: Chapter title.
- `description`: Chapter overview.
- `pages`: Screens, dialogs, or tasks in the chapter.

## Page Fields

- `title`: Page/dialog/task title.
- `nav_path`: Entry path.
- `purpose`: Functional description.
- `screenshot`: String or array of screenshot paths.
- `caption`: String or array matching screenshots.
- `filters`: List of filters.
- `actions`: List of buttons/actions.
- `columns`: List of table/list columns.
- `fields`: List of strings or objects like `{"name": "班级名称", "required": true, "description": "填写班级展示名称"}`.
- `steps`: List of step strings.
- `notes`: List of notes.
- `warnings`: List of warnings.
- `subpages`: Nested dialogs or subfeatures with the same fields as `page`.

## Workflow Fields

- `title`: Workflow title.
- `summary`: Workflow purpose.
- `steps`: Objects with `title`, `actor`, `action`, `result`, and optional `screenshot`.
- `flow`: Ordered short labels for a final overview.

## Image Paths

Relative image paths are resolved in this order:

1. Relative to `screenshot_root` if provided.
2. Relative to the spec file location.
3. Relative to the current working directory.

Use PNG/JPG screenshots. Keep original screenshots unchanged.
