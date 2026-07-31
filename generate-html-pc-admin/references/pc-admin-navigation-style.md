# PC 后台菜单与导航参考样式

本文件定义 `generate-html-pages` 在用户没有提供更高优先级 UI Token 时，PC 管理后台壳层的默认实现。所有色值、尺寸、圆角、阴影均遵循 `../../_shared/references/pc_admin_ui_spec.md`（基于 vue-admin-plus / Element Plus 的设计规范），采用纵向布局（`vertical`）：左侧深色菜单 + 顶部导航栏 + 工作区页签栏。

实现基准以本文 Token、结构约束和可运行示例为准：`examples/pc-admin-shell-demo.html`。分析用截图不打包进 Skill。

## 1. 导航层级

PC 业务页固定包含三层导航，登录页除外：

1. **左侧深色菜单**：品牌区（顶部 Logo + 系统名）+ 一级模块和二级页面入口。
2. **全局顶栏**：折叠按钮、面包屑、搜索、消息、全屏、用户头像。
3. **工作区页签栏**：显示当前页面页签，并预留应用入口。

采用 vue-admin-plus 纵向布局：侧边栏贯穿全高，顶栏位于侧边栏右侧、内容区上方。禁止在主内容区再次生成与顶栏重复的全局面包屑。页面内部的业务 Tab 不属于工作区页签，二者样式和语义必须区分。

## 2. 默认尺寸与颜色

> 以下值与 `../../_shared/references/pc_admin_ui_spec.md` 一致。调整时先修改 spec 原文，再同步此处。

| 项目 | 默认值 | 说明 |
|---|---:|---|
| 顶栏高度 | 60px | `$base-nav-height`，固定在视口顶部（侧边栏右侧） |
| 侧栏宽度 | 266px | `$base-left-menu-width`，允许 266/277/288 三档 |
| 折叠宽度 | 64px | `$base-left-menu-width-min`，仅显示图标 |
| 工作区页签栏 | 50px | `$base-tabs-height`，位于顶栏下方、主内容上方 |
| 菜单项高度 | 50px | `$base-menu-item-height` |
| 主内容内边距 | 20px | `$base-padding`，小于 1440px 可降至 16px |
| 顶栏背景 | `#FFFFFF` | 白底，使用细边框与侧栏分隔 |
| 侧栏背景 | `#282c34` | `$base-menu-background`，深色菜单 |
| 侧栏文字 | `hsla(0,0%,100%,0.95)` | 深色菜单下的统一文字色 |
| 选中项背景 | `#1890ff` | 主色，选中态背景 |
| 选中项文字 | `#ffffff` | 选中态纯白文字 |
| 页面背景 | `#f6f8f9` | `$base-color-background`，主工作区浅灰底 |
| 表头/斑马纹背景 | `#f5f7fa` | `$base-background-color-base` |
| 导航主文字 | `#303133` | `$base-color-text-primary` |
| 导航次文字 | `#909399` | `$base-color-text-secondary` |
| 边框 | `#e4e7ed` | `$base-border-color-light`，顶栏、侧栏和页签栏边框 |
| 表格内部分割线 | `#ebeef5` | `$base-border-color-lighter` |
| 圆角 | 2.5px | `$base-border-radius`，全局统一 |
| 阴影 | `0 1px 4px rgba(0,21,41,0.08)` | `$base-box-shadow`，全站唯一一级阴影 |
| 控件高度 | 32px | `$base-input-height`，Element Plus default 尺寸 |

## 3. DOM 骨架

纵向布局：侧边栏在左（全高），工作区在右（顶栏 + 页签 + 内容）。

```html
<div class="admin-shell">
  <aside class="admin-sidebar" aria-label="主菜单">
    <a class="brand-area" href="P02-dashboard.html">
      <span class="brand-logo" aria-hidden="true"><!-- SVG --></span>
      <span class="brand-name">系统名称</span>
    </a>
    <nav id="sidebar-container"></nav>
  </aside>

  <section class="admin-workspace">
    <header class="admin-header">
      <div class="header-main">
        <button class="header-icon-btn" id="sidebar-toggle" type="button" aria-label="折叠菜单">
          <span data-icon="menu" aria-hidden="true"></span>
        </button>
        <div class="header-breadcrumb" id="header-breadcrumb"></div>
        <div class="header-actions">
          <button class="header-icon-btn" type="button" aria-label="搜索">
            <span data-icon="search" aria-hidden="true"></span>
          </button>
          <button class="header-icon-btn msg-badge" type="button" aria-label="消息">
            <span data-icon="bell" aria-hidden="true"></span>
            <span class="dot"></span>
          </button>
          <button class="header-icon-btn" type="button" aria-label="全屏">
            <span data-icon="fullscreen" aria-hidden="true"></span>
          </button>
          <button class="user-trigger" type="button">
            <span>用户名</span>
            <span data-icon="chevron-down" aria-hidden="true"></span>
          </button>
        </div>
      </div>
    </header>

    <div class="workspace-tabs">
      <div class="workspace-tabs-list" id="workspace-tabs"></div>
      <button class="workspace-apps-btn" type="button" aria-label="应用入口">
        <span data-icon="grid" aria-hidden="true"></span>
      </button>
    </div>
    <main class="admin-main">
      <div class="page-surface"><!-- 页面内容 --></div>
    </main>
  </section>
</div>
```

## 4. common.css 核心样式

以下代码是生成时的基准，可按项目 Token 覆盖色值，但不得破坏壳层尺寸联动。色值与尺寸遵循 `../../_shared/references/pc_admin_ui_spec.md`。

```css
:root {
  --sidebar-width: 266px;
  --sidebar-collapsed-width: 64px;
  --header-height: 60px;
  --workspace-tabs-height: 50px;
  --menu-item-height: 50px;

  /* 背景色 */
  --header-bg: #ffffff;
  --sidebar-bg: #282c34;
  --sidebar-text: hsla(0, 0%, 100%, 0.95);
  --sidebar-active-bg: #1890ff;
  --sidebar-active-text: #ffffff;
  --page-bg: #f6f8f9;
  --base-bg: #f5f7fa;

  /* 文字色 */
  --text-primary: #303133;
  --text-regular: #606266;
  --text-secondary: #909399;
  --text-placeholder: #c0c4cc;

  /* 边框 */
  --nav-border: #e4e7ed;
  --border-lighter: #ebeef5;

  /* 主色与功能色 */
  --primary: #1890ff;
  --primary-light: #e6f7ff;
  --success: #13ce66;
  --warning: #ffba00;
  --danger: #ff6700;
  --error: #ff4d4f;

  /* 圆角与阴影 */
  --radius: 2.5px;
  --shadow: 0 1px 4px rgba(0, 21, 41, 0.08);

  /* 过渡 */
  --transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}

* { box-sizing: border-box; }
html, body { min-width: 1280px; min-height: 100%; }
body { margin: 0; color: var(--text-primary); background: var(--page-bg); font: 14px/1.5 -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif; }
button, input, select, textarea { font: inherit; }
button { color: inherit; }

/* ---------- 侧边栏（深色，全高） ---------- */
.admin-sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: 900;
  width: var(--sidebar-width);
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--sidebar-bg);
  transition: width 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}

.brand-area {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  height: var(--header-height);
  padding: 0 20px;
  color: var(--sidebar-text);
  text-decoration: none;
  overflow: hidden;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.brand-logo { flex: 0 0 32px; width: 32px; height: 32px; border-radius: 2.5px; overflow: hidden; }
.brand-logo svg { display: block; width: 100%; height: 100%; }
.brand-name { overflow: hidden; font-size: 16px; font-weight: 600; white-space: nowrap; text-overflow: ellipsis; }

.sidebar-menu { padding: 8px 0 16px; }
.menu-group { margin: 0; }
.menu-group-toggle,
.menu-link {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--sidebar-text);
  text-align: left;
  text-decoration: none;
  transition: background 0.2s ease;
}
.menu-group-toggle {
  display: flex;
  align-items: center;
  height: var(--menu-item-height);
  padding: 0 16px;
  cursor: pointer;
  font-size: 14px;
}
.menu-group-title,
.menu-link-label { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.menu-caret { flex: 0 0 auto; margin-left: auto; transition: transform 0.18s ease; }
.menu-group.is-open .menu-caret { transform: rotate(180deg); }
.menu-submenu { overflow: hidden; }
.menu-group:not(.is-open) .menu-submenu { display: none; }
.menu-link {
  display: flex;
  align-items: center;
  height: var(--menu-item-height);
  padding: 0 16px 0 38px;
  cursor: pointer;
  font-size: 14px;
}
.menu-group-toggle:hover,
.menu-link:hover { background: rgba(255, 255, 255, 0.06); }
.menu-link.is-active {
  color: var(--sidebar-active-text);
  background: var(--sidebar-active-bg);
  font-weight: 500;
}

/* ---------- 工作区（右侧） ---------- */
.admin-workspace {
  min-width: 0;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}

.admin-header {
  position: fixed;
  top: 0;
  left: var(--sidebar-width);
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  height: var(--header-height);
  background: var(--header-bg);
  border-bottom: 1px solid var(--nav-border);
  transition: left 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
}

.header-main { display: flex; align-items: center; min-width: 0; width: 100%; padding: 0 16px 0 12px; }
.header-icon-btn,
.workspace-apps-btn,
.user-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  cursor: pointer;
  border-radius: var(--radius);
}
.header-icon-btn { width: 40px; height: 40px; }
.header-icon-btn:hover,
.workspace-apps-btn:hover,
.user-trigger:hover { background: var(--base-bg); }
.header-icon-btn:focus-visible,
.workspace-apps-btn:focus-visible,
.user-trigger:focus-visible,
.menu-group-toggle:focus-visible,
.menu-link:focus-visible { outline: 2px solid rgba(24, 144, 255, 0.35); outline-offset: 1px; }

.header-breadcrumb { display: flex; align-items: center; min-width: 0; margin-left: 6px; color: var(--text-secondary); font-size: 13px; }
.header-breadcrumb a { color: var(--text-secondary); text-decoration: none; }
.header-breadcrumb a:hover { color: var(--primary); }
.breadcrumb-separator { margin: 0 6px; color: var(--text-placeholder); }
.header-actions { display: flex; align-items: center; gap: 4px; margin-left: auto; }
.msg-badge { position: relative; }
.msg-badge .dot { position: absolute; top: 8px; right: 8px; width: 6px; height: 6px; border: 1px solid #fff; border-radius: 50%; background: var(--error); }
.user-trigger { gap: 7px; min-height: 40px; padding: 0 8px 0 12px; color: var(--text-regular); }

/* ---------- 工作区页签栏 ---------- */
.workspace-tabs {
  position: sticky;
  top: var(--header-height);
  z-index: 800;
  display: flex;
  height: var(--workspace-tabs-height);
  padding-left: 20px;
  background: #fff;
  border-bottom: 1px solid var(--nav-border);
}
.workspace-tabs-list { display: flex; align-items: flex-end; min-width: 0; overflow: hidden; }
.workspace-tab {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 20px;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius) var(--radius) 0 0;
  font-size: 13px;
}
.workspace-tab.is-active { color: var(--primary); background: var(--primary-light); }
.workspace-apps-btn { width: 50px; height: 49px; margin-left: auto; border-left: 1px solid transparent; }

/* ---------- 主内容区 ---------- */
.admin-main {
  min-height: calc(100vh - var(--header-height) - var(--workspace-tabs-height));
  padding: 20px;
  background: var(--page-bg);
}
.page-surface {
  min-height: 240px;
  padding: 20px;
  background: #fff;
  border: 1px solid var(--nav-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

/* ---------- 折叠态 ---------- */
body.sidebar-collapsed { --sidebar-width: var(--sidebar-collapsed-width); }
body.sidebar-collapsed .admin-header { left: var(--sidebar-collapsed-width); }
body.sidebar-collapsed .brand-name,
body.sidebar-collapsed .menu-group-title,
body.sidebar-collapsed .menu-link-label,
body.sidebar-collapsed .menu-caret { opacity: 0; pointer-events: none; }
body.sidebar-collapsed .brand-area { justify-content: center; padding-inline: 0; }
body.sidebar-collapsed .menu-group-toggle,
body.sidebar-collapsed .menu-link { justify-content: center; padding-inline: 0; }

@media (max-width: 1439px) {
  .admin-main { padding: 16px; }
  .page-surface { padding: 16px; }
}
```

## 5. sidebar.js 行为模板

```javascript
(function () {
  var STORAGE_KEY = 'pc-admin-sidebar-collapsed';

  function icon(name) {
    var paths = {
      menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
      chevron: '<path d="m7 10 5 5 5-5"/>',
      'chevron-down': '<path d="m7 10 5 5 5-5"/>',
      bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
      grid: '<path d="M4 4h5v5H4zM15 4h5v5h-5zM4 15h5v5H4zM15 15h5v5H15z"/>',
      search: '<path d="M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35"/>',
      fullscreen: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>'
    };
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (paths[name] || '') + '</svg>';
  }

  function renderStaticIcons() {
    document.querySelectorAll('[data-icon]').forEach(function (node) {
      node.innerHTML = icon(node.getAttribute('data-icon'));
    });
  }

  function renderSidebar() {
    var root = document.getElementById('sidebar-container');
    var menus = Array.isArray(window.SIDEBAR_MENUS) ? window.SIDEBAR_MENUS : [];
    var activeMenu = window.ACTIVE_MENU || '';
    if (!root) return;

    root.innerHTML = '<div class="sidebar-menu">' + menus.map(function (group) {
      var children = Array.isArray(group.children) ? group.children : [];
      var isOpen = children.some(function (item) { return item.id === activeMenu; });
      return '<section class="menu-group ' + (isOpen ? 'is-open' : '') + '">' +
        '<button class="menu-group-toggle" type="button" aria-expanded="' + isOpen + '" title="' + escapeHtml(group.label) + '">' +
          '<span class="menu-group-title">' + escapeHtml(group.label) + '</span>' +
          '<span class="menu-caret">' + icon('chevron') + '</span>' +
        '</button>' +
        '<div class="menu-submenu">' + children.map(function (item) {
          var active = item.id === activeMenu;
          return '<a class="menu-link ' + (active ? 'is-active' : '') + '" href="' + escapeHtml(encodeURI(item.href || '#')) + '"' +
            (active ? ' aria-current="page"' : '') + ' title="' + escapeHtml(item.label) + '">' +
            '<span class="menu-link-label">' + escapeHtml(item.label) + '</span>' +
          '</a>';
        }).join('') + '</div>' +
      '</section>';
    }).join('') + '</div>';

    root.querySelectorAll('.menu-group-toggle').forEach(function (button) {
      button.addEventListener('click', function () {
        var group = button.closest('.menu-group');
        var open = group.classList.toggle('is-open');
        button.setAttribute('aria-expanded', String(open));
      });
    });
  }

  function renderHeaderBreadcrumb() {
    var root = document.getElementById('header-breadcrumb');
    var meta = window.PAGE_META || {};
    var items = Array.isArray(meta.breadcrumbs) ? meta.breadcrumbs : [];
    if (!root) return;

    root.innerHTML = items.map(function (item, index) {
      var data = typeof item === 'string' ? { label: item } : item;
      var current = index === items.length - 1;
      var content = current || !data.href
        ? '<span>' + escapeHtml(data.label) + '</span>'
        : '<a href="' + escapeHtml(encodeURI(data.href)) + '">' + escapeHtml(data.label) + '</a>';
      return (index ? '<span class="breadcrumb-separator">&gt;</span>' : '') + content;
    }).join('');
  }

  function renderWorkspaceTabs() {
    var root = document.getElementById('workspace-tabs');
    var meta = window.PAGE_META || {};
    if (!root || !meta.tab) return;

    root.innerHTML = '<a class="workspace-tab is-active" href="' + escapeHtml(encodeURI(meta.tab.href || '#')) + '" aria-current="page">' +
      escapeHtml(meta.tab.label || meta.title || '') + '</a>';
  }

  function readCollapsed() {
    try { return localStorage.getItem(STORAGE_KEY) === '1'; }
    catch (error) { return false; }
  }

  function saveCollapsed(value) {
    try { localStorage.setItem(STORAGE_KEY, value ? '1' : '0'); }
    catch (error) { /* file:// 或隐私模式下忽略持久化失败 */ }
  }

  function bindSidebarToggle() {
    var button = document.getElementById('sidebar-toggle');
    if (!button) return;

    var collapsed = readCollapsed();
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    button.setAttribute('aria-expanded', String(!collapsed));
    button.addEventListener('click', function () {
      var next = !document.body.classList.contains('sidebar-collapsed');
      document.body.classList.toggle('sidebar-collapsed', next);
      saveCollapsed(next);
      button.setAttribute('aria-expanded', String(!next));
    });
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>'"]/g, function (char) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char];
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderStaticIcons();
    renderSidebar();
    renderHeaderBreadcrumb();
    renderWorkspaceTabs();
    bindSidebarToggle();
  });

  window.renderSidebar = renderSidebar;
  window.renderHeaderBreadcrumb = renderHeaderBreadcrumb;
  window.renderWorkspaceTabs = renderWorkspaceTabs;
  window.bindSidebarToggle = bindSidebarToggle;
}());
```

## 6. 菜单配置示例

```javascript
var SIDEBAR_MENUS = [
  {
    id: 'overview',
    label: '数据概览',
    children: [
      { id: 'data-overview', label: '数据概览', href: 'P02-dashboard.html' },
      { id: 'traffic-analysis', label: '流量分析', href: 'P03-traffic.html' }
    ]
  },
  {
    id: 'operations',
    label: '运营管理',
    children: [
      { id: 'content', label: '资讯管理', href: 'P04-content.html' },
      { id: 'tickets', label: '景点门票', href: 'P05-tickets.html' }
    ]
  }
];
```

## 7. 验收清单

- 侧边栏深色背景 `#282c34`，文字 `hsla(0,0%,100%,0.95)`，选中项背景主色 `#1890ff`、文字纯白。
- 顶栏、侧栏、工作区页签栏在滚动时保持固定或粘性，不随内容消失。
- 品牌区位于侧边栏顶部，高度与顶栏一致（60px），宽度与侧栏共享 CSS 变量。
- 顶栏位于侧边栏右侧，折叠时 `left` 跟随 `--sidebar-collapsed-width` 变化。
- 当前菜单选中项为主色整行背景，不出现右侧色条。
- 一级菜单箭头可折叠，当前页面所属分组默认展开。
- 头部面包屑与工作区当前页签内容一致。
- 折叠状态刷新后保持，键盘焦点可见，按钮具有 `aria-label`。
- 全站圆角 2.5px，阴影 `0 1px 4px rgba(0,21,41,0.08)`，控件高度 32px。
- 所有导航图标来自同一套内联 SVG，不使用 Emoji 或外部 CDN。
