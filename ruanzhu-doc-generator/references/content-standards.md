# 软著产品说明书生成标准

## Document Skeleton

Use this structure for both PC management backend and mobile manuals:

1. Cover
   - `<软件名称>`
   - `产品说明书`
   - `V<版本号>版`
   - `<公司名称>`
   - `<YYYY年 M 月>`
2. 引言
   - 修改记录
   - 简述
   - 运行环境
   - 系统架构
3. 功能摘要
4. 界面设计
   - 用户界面设计规则
   - 字体
   - 风格
   - 色系
   - 控件
   - 尺寸
   - 布局
   - 交互
5. 功能展示及说明
   - `后台-管理端` for PC backend.
   - `移动端` for mobile app/miniprogram.
   - Each screenshot becomes a titled subsection with one or more explanatory paragraphs and a captioned image.

## Endpoint-Specific Distinction

PC management backend:
- Title should contain `管理后台` unless the user gives another exact suffix.
- Describe browser access, role-based permissions, admin data maintenance, list/table CRUD, audit, export, configuration, and operational management.
- Runtime should mention Windows/macOS browser clients, Chrome/Edge/Firefox, and common server stack.
- UI style should mention left navigation, breadcrumb/top bar, right content area, tables, forms, dialogs/drawers, pagination, filters, loading and confirmation states.

Mobile端:
- Title should contain `移动端`, `小程序端`, `用户端`, or the exact user-provided suffix.
- Describe user-facing service flows: browsing, search, reservation/registration, form submission, upload, status query, cancellation, notification, profile, help, and feedback.
- Runtime should mention iOS/Android, WeChat miniprogram or mobile browser as applicable.
- UI style should mention bottom tabs, card/list layout, large touch targets, page navigation, pull-to-refresh, toast/modal feedback, and phone-screen adaptation.

If screenshots contain both endpoint types, generate two separate documents. Do not put mobile user flows into the PC manual or admin maintenance functions into the mobile manual unless the screenshot explicitly belongs there.

## Metadata JSON Schema

The generator works without metadata, but a JSON file produces better text:

```json
{
  "project_name": "寒暑托班报名系统",
  "company": "苏州世纪飞越网络信息有限公司",
  "version": "1.0",
  "month": "2026年 5 月",
  "dev_completion_date": "2026年 5月 31日",
  "publish_date": "2026年 5月 31日",
  "purpose": "为解决寒暑假期间双职工家庭学生看护难、托管服务管理分散等问题...",
  "architecture": "系统采用前后端分离架构...",
  "targets": {
    "pc-admin": {
      "title_suffix": "管理后台",
      "features": ["账号登录", "平台看板", "点位管理"],
      "modules": [
        {
          "title": "后台登录",
          "image": "pc/login.png",
          "description": [
            "管理员在浏览器中输入管理后台地址，进入登录页面。",
            "输入正确账号密码后，系统校验身份并跳转至管理后台首页。"
          ]
        }
      ]
    },
    "mobile": {
      "title_suffix": "移动端",
      "features": ["首页浏览", "托班报名", "预约记录"],
      "modules": [
        {
          "title": "首页",
          "image": "mobile/home.png",
          "description": ["用户进入移动端首页后，可查看服务入口、公告和快捷操作。"]
        }
      ]
    }
  }
}
```

Notes:
- `targets.pc-admin.modules` and `targets.mobile.modules` are optional. If omitted, the script scans screenshots and creates module entries from filenames.
- `image` paths are resolved relative to the metadata file first, then the screenshot folder.
- A module can omit `image` to create a text-only feature subsection.
- Keep descriptions factual. If a screenshot does not prove a feature, phrase it as a visible interface operation rather than an unsupported system guarantee.

## Writing Style

- Use formal Chinese, avoiding marketing slogans.
- Prefer `【功能点】说明...` paragraph starts in the function section.
- Mention visible controls and likely user actions: 查询、重置、新增、编辑、删除、详情、导出、提交、取消、审核、保存.
- For each module, include purpose, key fields/controls, operation flow, validation/feedback, and business result where applicable.
- Keep paragraphs concise. Avoid one very long paragraph under a screenshot.
