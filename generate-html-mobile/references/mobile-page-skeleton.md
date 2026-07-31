# 移动端页面骨架模板

> 本文件从 generate-html-mobile SKILL.md §3.4 抽离，作为移动端业务页面通用 HTML 结构模板和结构约束。生成移动端 HTML 页面时读取本文件。

## 一、业务页面通用结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{页面标题} - {系统名称}</title>
  <link rel="stylesheet" href="common.css">
  <style>/* 页面专属样式 */</style>
</head>
<body>
  <script>
    var ACTIVE_TAB = '{tab-id-or-empty}';
    var MOBILE_PAGE_META = {
      title: '{页面标题}',
      archetype: '{service-home|media-list|commerce-category|detail|cart|orders|profile|public-account|realtime}',
      header: '{contextual|standard|search|immersive}',
      showTabBar: true,
      hasStickyAction: false
    };
  </script>

  <div class="m-layout">
    <header id="mobileHeaderContainer"></header>

    <main class="m-content" id="mainContent">
      <!-- 按页面原型生成内容 -->
    </main>

    <div id="stickyActionContainer"></div>
    <nav class="m-tab-bar" id="tabBarContainer" aria-label="主导航"></nav>
  </div>

  <script src="navbar.js"></script>
</body>
</html>
```

## 二、结构约束

- 一级首页可使用上下文头部，不强制传统标题栏。
- 二级列表和普通详情使用返回顶部栏；沉浸详情可让媒体区靠近顶部，但返回和操作必须可见。
- 页面局部Tab属于内容筛选，不与全局频道重复。
- 底部主导航只出现在一级页面；固定主操作存在时要判断是否隐藏底部主导航。
- 登录页使用全屏表单，不使用主导航。
- 禁止 `maximum-scale=1` 和 `user-scalable=no`。
