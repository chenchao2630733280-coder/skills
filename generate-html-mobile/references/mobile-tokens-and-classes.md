# 移动端视觉 Token 与组件类名规范

> 本文件从 generate-html-mobile SKILL.md §3.2 抽离，作为移动端 CSS 变量体系、组件类名索引和默认视觉约束的完整规范。生成移动端 common.css 和页面专属样式时读取本文件。

## 一、CSS 变量体系

```css
:root {
  /* 品牌色与语义色与 PC 端 pc-admin-navigation-style.md 保持一致（双端共享） */
  --m-primary: #1890ff;
  --m-primary-hover: #40a9ff;
  --m-primary-soft: #e6f7ff;
  --m-success: #13ce66;
  --m-warning: #ffba00;
  --m-danger: #ff6700;
  --m-info: #1890ff;
  --m-bg: #F5F7F6;
  --m-card-bg: #FFFFFF;
  --m-text-primary: #202523;
  --m-text-regular: #626A67;
  --m-text-auxiliary: #8B9390;
  --m-text-placeholder: #B7BDBA;
  --m-border: #E7ECE9;
  --m-mask: rgba(0, 0, 0, 0.48);

  --m-edge-padding: 16px;
  --m-section-gap: 12px;
  --m-card-padding: 14px;
  --m-card-radius: 12px;
  --m-control-radius: 10px;
  --m-pill-radius: 999px;

  --m-nav-bar-height: 46px;
  --m-search-height: 40px;
  --m-tab-bar-height: 56px;
  --m-primary-action-height: 48px;
  --m-touch-target: 44px;

  --m-safe-top: env(safe-area-inset-top, 0px);
  --m-safe-bottom: env(safe-area-inset-bottom, 0px);
}
```

## 二、按实际页面需要覆盖的样式模块

| 模块 | 类名 | 说明 |
|------|------|------|
| 页面骨架 | `.m-layout` `.m-page` `.m-content` `.m-safe-bottom` | 单列内容区，支持安全区和固定底栏占位 |
| 上下文头部 | `.m-context-header` `.m-channel-tabs` `.m-weather` `.m-header-actions` | 一级首页使用的天气/定位、频道、消息和搜索组合 |
| 普通顶部栏 | `.m-nav-bar` `.m-nav-bar-left/right/title` `.m-icon-btn` | 二级页返回、标题和操作 |
| 搜索 | `.m-search` `.m-search-input` `.m-search-submit` | 36-40px 高；按任务配置占位文案 |
| 底部主导航 | `.m-tab-bar` `.m-tab-bar-item` `.active` `.m-tab-badge` | 仅用于4-5个稳定一级入口 |
| 局部Tab | `.m-local-tabs` `.m-local-tab` `.active` | 页面内筛选；支持横向滚动 |
| 运营位 | `.m-hero` `.m-hero-copy` `.m-hero-action` `.m-carousel-dots` | 使用项目资产或CSS/SVG，不复制参考图 |
| 服务宫格 | `.m-service-grid` `.m-service-item` `.m-service-icon` `.m-service-badge` | 默认4列或5列，超过15项提供"全部" |
| 模块标题 | `.m-section-head` `.m-section-title` `.m-section-more` | 标题16-17px，右侧可放"更多" |
| 内容卡片 | `.m-card` `.m-card-list` `.m-feature-grid` `.m-media-card` | 12px圆角、轻边界、低阴影 |
| 图文列表 | `.m-media-list` `.m-media-item` `.m-thumb` `.m-item-main/meta` | 景点、专家、活动、新闻等 |
| 分类检索 | `.m-category-strip` `.m-sort-bar` `.m-category-rail` `.m-result-pane` | 横向一级分类 + 排序 + 左侧二级分类 |
| 上下文展开层 | `.m-context-popover` `.m-context-grid` `.m-mask-layer` | 分类或筛选在当前页展开，保留上下文 |
| 商品条目 | `.m-product-item` `.m-product-price` `.m-add-cart` `.m-promo` | 横向商品卡和加购按钮 |
| 数量步进器 | `.m-stepper` `.m-stepper-btn` `.m-stepper-value` | 按钮至少40×40px |
| 购物车 | `.m-merchant-group` `.m-cart-item` `.m-cart-summary` | 按商家分组，底部结算栏 |
| 订单 | `.m-order-tabs` `.m-order-card` `.m-order-status` `.m-order-actions` | 状态Tab、订单卡和主次操作 |
| 个人中心 | `.m-profile-hero` `.m-profile-avatar` `.m-shortcut-card` `.m-menu-group` | 渐变头部、状态快捷卡、分组菜单 |
| 公共账户 | `.m-institution-bar` `.m-account-card` `.m-sensitive-value` `.m-service-query-grid` | 机构身份、脱敏余额、办理入口 |
| 实时信息 | `.m-realtime-hero` `.m-live-card` `.m-live-value` `.m-inline-expand` | 公交、排队、物流等实时状态 |
| 表单 | `.m-form-section` `.m-form-row` `.m-form-label/input` | 单列分组表单 |
| 详情 | `.m-detail-hero` `.m-detail-summary` `.m-detail-section` `.m-detail-row` | 媒体区、核心信息、纵向分区 |
| 标签 | `.m-tag` `.m-tag-primary/success/warning/danger/info` | 浅色胶囊，文字表达状态 |
| 固定操作 | `.m-sticky-action` `.m-bottom-actions` | 考虑底部导航和安全区 |
| Drawer/面板 | `.m-drawer` `.m-bottom-sheet` `.m-action-sheet` | 轻量选择使用；复杂任务进入全屏页 |
| 状态 | `.m-skeleton` `.m-empty-state` `.m-error-state` `.m-offline-state` | 按页面适用性生成 |
| 反馈 | `.m-toast` `.m-dialog` `.m-alert` | 成功轻提示，风险操作明确确认 |

## 三、移动端默认视觉约束

- 以 `375×812` 为最低设计基准，同时在 390-430px 宽度下验证；内容最大宽度建议 480px。
- 页面左右边距默认 12-16px；模块间距 12-16px；卡片内边距 12-16px。
- 页面背景使用浅灰绿或项目浅色，容器为白色；优先靠层级和留白分组，不大量使用边框。
- 卡片默认圆角12px，小控件8-10px，胶囊999px；只有悬浮卡、底部栏和叠层卡使用轻阴影。
- 页面标题18-20px/600，模块标题16-17px/600，正文14px，辅助文字12-13px。
- 关键金额、余额、到站时间、数量等使用18-24px/600-700和等宽数字。
- 点击区域不小于44×44px；相邻小按钮间距至少8px。
- 底部固定区域必须加安全区，并为内容增加等高 `padding-bottom`。
- viewport 必须允许缩放：`width=device-width, initial-scale=1, viewport-fit=cover`。
- 项目内只使用一套SVG图标；不得使用Emoji充当业务图标。
- 分析截图只用于提炼规则，不进入 Skill 包和最终页面。无授权资产时用本地SVG、CSS渐变、几何图形或中性占位。
