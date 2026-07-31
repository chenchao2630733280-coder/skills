# Content Patterns

## Functional说明 Formula

Use one sentence:

```text
提供<对象/业务>功能，支持<关键动作1>、<关键动作2>及<关键场景/约束>。
```

Good examples:

- 提供医院列表展示、查询及详情展示功能，支持按区域、等级等多维度筛选。
- 提供体检服务预约功能，支持套餐浏览、在线预约、支付、记录查询及报告查看。
- 提供管理后台安全登录功能，支持账号密码校验、密码策略、错误锁定、超时退出和强制改密。

Avoid:

- `用户登录后选择医院→科室→专家...`
- `用例描述：...`
- Long paragraphs copied from requirements.

## Functional描述 Bullet Types

Use bullets that describe deliverable capabilities:

- Navigation and entry: 首页入口、菜单入口、快捷入口、底部导航
- Display fields: 名称、等级、地址、状态、时间、联系人、订单号
- Query/filter: 按区域、等级、时间、关键字、状态筛选
- State labels: 号源充足、紧张、无号、已预约、已取消、无数据
- Detail pages: 基本信息、简介、联系方式、科室列表、记录详情
- Operations: 新增、编辑、删除、发布、上下架、排序、刷新、导出
- Validation: 登录校验、实名认证、短信验证码、必填项校验、防重复提交
- Integration: 接口获取、数据同步、缓存更新、第三方平台对接
- Exceptions: 无数据提示、接口异常提示、验证码错误提示

## Rewrite From Use Case Table

Map requirement fields like this:

- `用例描述` -> capability summary or first bullet
- `正常事件流` -> extract only capabilities, not every step
- `可选事件流` -> optional features or extension bullets
- `异常事件流` -> exception/validation bullets
- `规则说明` -> constraints and interface rules
- `参与者`、`前置条件`、`后置条件`、`使用频度` -> usually omit from bid module unless requested

## Style Rules

- Start bullets with nouns or verbs, not actors.
- Keep bullets short enough for scanning.
- Use `支持` for configurable or optional actions.
- Use `展示` for visible page content.
- Use `维护` for management backend CRUD.
- Use `对接` or `同步` for external data or platform integration.
- Keep terminology consistent across client and backend modules.

## Exclusion Rewrite Example

If removing `候补` and `排队叫号`:

- Replace `预约记录、候补记录入口` with `预约记录入口`
- Replace `支持退号确认、候补预约、候补提交、候补详情和就诊后评价` with `支持退号确认、预约详情查看和就诊后评价`
- Remove `排队叫号` module headings, overview rows, screenshots, captions, and bullets
- Search final document for both terms
