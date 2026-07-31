# 移动端 navbar.js 模板

> 本文件从 generate-html-mobile SKILL.md §3.3 抽离，作为移动端 navbar.js 的函数签名规范和 TAB_BAR_ITEMS 数据结构模板。生成移动端 navbar.js 时读取本文件。

## 一、建议导出的变量和函数

- `ACTIVE_TAB`：当前底部主导航标识；无底部主导航时为空。
- `MOBILE_PAGE_META`：页面标题、原型、顶部栏类型、是否展示底部主导航、是否有固定操作。
- `TAB_BAR_ITEMS`：仅在PRD定义4-5个稳定一级入口时配置，否则为空数组。
- `renderMobileHeader()`：按 `contextual / standard / search` 类型渲染头部。
- `renderTabBar()`：有配置且当前页允许时渲染，无配置时不占位。
- `bindLocalTabs()`：绑定页面局部Tab和 `aria-selected`。
- `bindContextPopover()`：绑定分类/筛选上下文展开层、遮罩和焦点恢复。
- `syncSafeAreaSpacing()`：根据底部主导航、固定操作栏更新内容底部占位。

## 二、TAB_BAR_ITEMS 数据结构

```javascript
var TAB_BAR_ITEMS = [
  { id: 'home', icon: 'home', label: '首页', href: 'P02-home.html' },
  { id: 'service', icon: 'grid', label: '服务', href: 'P03-service.html' },
  { id: 'order', icon: 'receipt', label: '订单', href: 'P04-order.html', badge: 2 },
  { id: 'mine', icon: 'user', label: '我的', href: 'P05-mine.html' }
];
```

> 底部主导航不是默认必选项。二级页、详情页、全屏表单和结算页通常隐藏它；辅助入口优先放在页面内、Drawer或底部面板。
