# 交互实现模式参考

本文件承接 SKILL.md §9.3~9.6 的代码模板，作为**模式参考**，不是可直接复制粘贴的完整实现。生成代码时必须按项目实际的字段名、选择器、弹窗 ID 等替换 `{占位符}`。所有约束均适用于 PC 端和移动端。

> **通用性边界**：仅当原型文档/`actions.json` 定义了交互函数或操作按钮时，才需要按本文件实现交互。纯展示页面（如关于我们、公司介绍、静态公告）无需强制添加 CRUD 或排序功能。若项目已有 `common.css`/`sidebar.js`/`navbar.js` 提供了基础函数（如 `showToast`、`openModal`），页面中**不得重复定义**，直接调用即可。

---

## 1. 基础函数：Toast / Modal / 确认 / escapeHtml

**弹窗显隐一致性原则（重要）：**

`openModal`/`closeModal` 必须使用 `classList` 操作 `.show` 类，配合 CSS `.modal-overlay { display:none }` / `.modal-overlay.show { display:flex }`。

- **禁止**在弹窗 HTML 上写 `style="display:none"`（内联样式优先级高于类选择器，`openModal` 加 `.show` 类无法覆盖，弹窗打不开）
- **禁止**在 JS 中用 `style.display = 'flex'/'none'` 直接操作内联 display

**兜底实现（当 common.css / sidebar.js / navbar.js 未提供时）：**

```javascript
function showToast(msg) {
  var toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(function () { toast.classList.add('show'); }, 10);
  setTimeout(function () {
    toast.classList.remove('show');
    setTimeout(function () { toast.remove(); }, 300);
  }, 2000);
}

function openModal(id) {
  var el = document.getElementById(id);
  if (el) el.classList.add('show');
}

function closeModal(id) {
  var el = document.getElementById(id);
  if (el) el.classList.remove('show');
}

function confirmAction(message, onConfirm) {
  if (window.confirmDialog) { window.confirmDialog(message, onConfirm); }
  else if (confirm(message)) { onConfirm(); }
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
```

---

## 2. 文件与图片上传

当原型文档定义了文件或图片上传功能时，必须实现完整的文件选择、校验和回填/预览逻辑。

### 2.1 文件上传（附件类）

**必须实现的逻辑：**

1. 页面中存在隐藏的 `<input type="file">` 元素，`handleUpload(field)` 触发其 `click()`
2. `onFileSelected(event)` 回调中校验文件类型和大小（按字段配置），成功后回填文件名到展示区域并 Toast
3. 已上传文件提供"预览""删除"操作（删除需二次确认）

**参考代码：**

```javascript
var currentUploadField = null;
// 按项目实际字段配置：{ 字段名: { accept, sizeLimit } }
var fieldConfig = {
  '{field_name}': { accept: '.pdf', sizeLimit: 20 * 1024 * 1024 }
};

function handleUpload(field) {
  currentUploadField = field;
  var fileInput = document.getElementById('fileInput');
  var cfg = fieldConfig[field] || {};
  fileInput.setAttribute('accept', cfg.accept || '');
  fileInput.value = '';
  fileInput.click();
}

function onFileSelected(event) {
  var file = event.target.files[0];
  if (!file) return;
  var cfg = fieldConfig[currentUploadField] || {};
  var sizeLimit = cfg.sizeLimit || 20 * 1024 * 1024;
  if (file.size > sizeLimit) {
    showToast('文件大小不能超过 ' + Math.round(sizeLimit / 1024 / 1024) + 'MB');
    return;
  }
  // 回填文件名到展示区域（选择器按项目实际结构调整）
  var nameEl = document.querySelector('[data-field="' + currentUploadField + '"] .file-name');
  if (nameEl) nameEl.textContent = file.name;
  showToast('文件上传成功');
}
```

```html
<input type="file" id="fileInput" style="display:none" onchange="onFileSelected(event)">
```

### 2.2 图片上传（预览类）

**必须实现的逻辑：**

1. 页面中存在隐藏的 `<input type="file" accept="image/jpeg,image/png,image/gif,image/webp">`
2. `onImageSelected(event)` 校验图片类型（jpg/png/gif/webp）和大小（≤5MB），使用 `FileReader.readAsDataURL` 读取后赋值到预览 `<img>` 的 `src`
3. 已上传图片提供"移除"操作（二次确认），移除后预览区清空

**参考代码：**

```javascript
var currentUploadField = null;
// 按项目实际字段配置：{ 字段名: 预览元素ID }
var previewIdMap = {
  '{field_name}': '{previewElementId}'
};

function handleUploadImage(field) {
  currentUploadField = field;
  var fileInput = document.getElementById('imageFileInput');
  fileInput.value = '';
  fileInput.click();
}

function onImageSelected(event) {
  var file = event.target.files[0];
  if (!file) return;
  var validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  if (validTypes.indexOf(file.type) === -1) { showToast('仅支持 jpg/png/gif/webp 格式'); return; }
  if (file.size > 5 * 1024 * 1024) { showToast('图片大小不能超过 5MB'); return; }
  var reader = new FileReader();
  reader.onload = function (e) {
    var previewBox = document.getElementById(previewIdMap[currentUploadField]);
    if (previewBox) {
      var img = previewBox.querySelector('img');
      if (img) { img.src = e.target.result; img.style.display = 'block'; }
    }
    showToast('图片上传成功');
  };
  reader.readAsDataURL(file);
}

function handleRemoveImage(field) {
  confirmAction('确认移除该图片？', function () {
    var previewBox = document.getElementById(previewIdMap[field]);
    if (previewBox) {
      var img = previewBox.querySelector('img');
      if (img) { img.src = ''; img.style.display = 'none'; }
    }
    showToast('已移除');
  });
}
```

> 注：`<input type="file">` 的 `style="display:none"` 是隐藏 input 元素（不是弹窗），与第 1 节的弹窗禁用内联样式不冲突。

---

## 3. 弹窗与操作

当原型文档定义了查看、编辑、删除、状态切换或导出操作时，按以下模式实现。

### 3.1 详情/编辑弹窗

**必须实现的逻辑：**

1. 弹窗 HTML 默认由 CSS `.modal-overlay { display:none }` 隐藏（禁用内联样式，见第 1 节）
2. 详情弹窗：从被点击行的单元格中读取数据，填充到弹窗的展示元素
3. 编辑弹窗：从行中读取数据回填到表单字段；新增模式清空表单
4. 弹窗内表单提交时校验必填项，成功后关闭弹窗并 Toast

```javascript
function openDetailModal(btn) {
  var row = btn.closest('tr');
  var cells = row.querySelectorAll('td');
  document.getElementById('{detailNameId}').textContent = cells[{colIndex}].textContent.trim();
  // ... 其他字段
  openModal('{detailModalId}');
}

function openEditModal(btn) {
  if (btn) {
    // 编辑模式：从行读取数据回填表单
    editingRow = btn.closest('tr');
    var cells = editingRow.querySelectorAll('td');
    // 回填表单字段...
  } else {
    // 新增模式：清空表单
    editingRow = null;
  }
  openModal('{editModalId}');
}
```

### 3.2 删除等危险操作

调用 `confirmAction(message, callback)` 二次确认，确认后执行回调并 Toast。禁止直接 `showToast('已删除')` 而无确认步骤。

### 3.3 状态切换 / 导出下载

- **状态切换**（启用/停用/归档）：`confirmAction` 二次确认，确认后更新行内状态标签（`textContent` 和 `className`），并 Toast。
- **导出/下载**：Toast "导出中..."，1-2 秒后 Toast "导出成功"（模拟异步）。如原型文档定义了真实下载，可使用 `window.open(downloadUrl)` 或创建 `<a download>` 触发。

---

## 4. 列表 CRUD 与排序

当原型文档定义了"新增/编辑/删除/排序"操作时，必须实现完整的 DOM 增删改查，禁止仅 Toast 提示。

**核心原则：通过按钮 `this` 定位所属行/卡片，用 DOM API 完成真实增删改。**

### 4.1 通用约定

| 要素 | 卡片列表 | 表格行 |
|------|---------|--------|
| 容器选择器 | `.{containerClass}` | `.data-table tbody` |
| 行元素选择器 | `.{cardClass}` | `tr` |
| 编辑/删除按钮 | 必须传 `this` | 必须传 `this` |
| 新增按钮 | 不传 `this` | 不传 `this` |
| 编辑模式 | `editingContext` 记录卡片元素 | `editingRow` 记录行元素 |
| 排序后 | `refreshRanks(container, rankSelector)` | `refreshTableRanks(tbody)` |

**共有 JS 函数：**

```javascript
// 移动卡片（卡片列表）
function moveCard(handle, direction) {
  var card = handle.closest('.{cardClass}');
  if (!card) return;
  var parent = card.parentNode;
  var siblings = Array.prototype.slice.call(parent.children);
  var idx = siblings.indexOf(card);
  var target = idx + direction;
  if (target < 0 || target >= siblings.length) { showToast('已在边界'); return; }
  if (direction < 0) { parent.insertBefore(card, siblings[target]); }
  else { parent.insertBefore(card, siblings[target + 1] || null); }
  refreshRanks(parent, '.{rankClass}');
  showToast('已移动');
}

// 移动行（表格）
function moveRow(handle, direction) {
  var row = handle.closest('tr');
  if (!row) return;
  var tbody = row.parentNode;
  var rows = Array.prototype.slice.call(tbody.children);
  var idx = rows.indexOf(row);
  var target = idx + direction;
  if (target < 0 || target >= rows.length) { showToast('已在边界'); return; }
  if (direction < 0) { tbody.insertBefore(row, rows[target]); }
  else { tbody.insertBefore(row, rows[target + 1] || null); }
  refreshTableRanks(tbody);
  showToast('已移动');
}

// 刷新序号（卡片列表）
function refreshRanks(container, rankSelector) {
  var cards = container.children;
  for (var i = 0; i < cards.length; i++) {
    var rankEl = cards[i].querySelector(rankSelector);
    if (rankEl) rankEl.textContent = (i + 1);
  }
}

// 刷新序号（表格行）
function refreshTableRanks(tbody) {
  var rows = tbody.children;
  for (var i = 0; i < rows.length; i++) {
    var rankEl = rows[i].querySelector('.row-rank');
    if (rankEl) rankEl.textContent = (i + 1);
  }
}
```

> `escapeHtml` 见第 1 节基础函数。

### 4.2 卡片列表变体

适用于：卡片形式的可排序内容列表（如单位、嘉宾、合作伙伴、产品等）。

**布局规范（涉及排序时必用单列横向）：**

当卡片列表涉及排序（上移/下移）操作时，**必须采用单列横向布局**，禁止使用多列 grid。理由：多列布局中卡片按行排列，上移/下移的视觉方向与实际 DOM 顺序不一致；单列布局中每行一条数据，序号从上到下递增，排序箭头上下移动与视觉方向一致。

**卡片结构（从左到右）：**

```
[序号] [排序箭头▲▼] [Logo/头像] [名称+描述(flex:1)] [编辑|删除]
```

**CSS 参考：**

```css
.{containerClass} { display: flex; flex-direction: column; gap: 8px; }
.{cardClass} {
  background: #FAFAFA; border: 1px solid var(--border); border-radius: 8px;
  padding: 12px 16px; display: flex; align-items: center; gap: 12px;
}
.{cardClass} .{rankClass} { width: 28px; flex-shrink: 0; text-align: center;
  color: var(--text-auxiliary); font-size: 13px; font-weight: 600; }
.{cardClass} .{sortClass} { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
.{cardClass} .{sortClass} .sort-handle { width: 24px; height: 20px; display: flex;
  align-items: center; justify-content: center; cursor: pointer; font-size: 11px; border-radius: 4px; }
.{cardClass} .{sortClass} .sort-handle:hover { background: var(--primary-light); color: var(--primary); }
.{cardClass} .{logoClass} { width: 48px; height: 48px; flex-shrink: 0; }
.{cardClass} .{nameClass} { flex: 1; font-size: 14px; font-weight: 500; }
.{cardClass} .{actionsClass} { display: flex; gap: 8px; flex-shrink: 0; }
```

**参考代码：**

```javascript
var editingContext = null; // { type, cardEl }  cardEl 为 null 表示新增

function openEditModal(type, id, btn) {
  var cardEl = null;
  var nameVal = '';
  if (id && btn) {
    cardEl = btn.closest('.{cardClass}');
    if (cardEl) {
      var nameEl = cardEl.querySelector('.{nameClass}');
      if (nameEl) nameVal = nameEl.textContent.trim();
    }
  }
  editingContext = { type: type, cardEl: cardEl };
  // 切换弹窗标题、回填表单字段...
  openModal('{editModalId}');
}

function handleSave() {
  var name = document.getElementById('{nameInputId}').value.trim();
  if (!name) { showToast('请输入名称'); return; }
  var ctx = editingContext;
  if (ctx && ctx.cardEl) {
    // 编辑模式：更新现有卡片
    var nameEl = ctx.cardEl.querySelector('.{nameClass}');
    if (nameEl) nameEl.textContent = name;
    showToast('保存成功');
  } else {
    // 新增模式：创建新卡片并插入
    var newCard = createCard(ctx ? ctx.type : type, name);
    var list = document.querySelector('.{containerClass}');
    if (list) { list.appendChild(newCard); refreshRanks(list, '.{rankClass}'); }
    showToast('新增成功');
  }
  closeModal('{editModalId}');
  editingContext = null;
}

function deleteCard(btn) {
  confirmAction('确认删除该记录？', function () {
    var cardEl = btn.closest('.{cardClass}');
    if (cardEl && cardEl.parentNode) {
      var list = cardEl.parentNode;
      list.removeChild(cardEl);
      refreshRanks(list, '.{rankClass}');
      showToast('已删除');
    }
  });
}

function createCard(type, name) {
  var card = document.createElement('div');
  card.className = '{cardClass}';
  card.innerHTML =
    '<div class="{rankClass}"></div>' +
    '<div class="{sortClass}">' +
      '<span class="sort-handle" title="上移" onclick="moveCard(this, -1)">▲</span>' +
      '<span class="sort-handle" title="下移" onclick="moveCard(this, 1)">▼</span>' +
    '</div>' +
    '<div class="{logoClass}">LOGO</div>' +
    '<div class="{nameClass}">' + escapeHtml(name) + '</div>' +
    '<div class="{actionsClass}">' +
      '<button class="btn-text" onclick="openEditModal(\'' + type + '\', ' + Date.now() + ', this)">编辑</button>' +
      '<button class="btn-text danger" onclick="deleteCard(this)">删除</button>' +
    '</div>';
  return card;
}
```

### 4.3 表格行变体

适用于：表格形式的可排序内容列表（如站点、联系人、FAQ、产品等）。

**布局规范：** 排序手柄**禁止混在"操作"列中**，必须独立成列，配合序号列一起使用：

```
表头：| 序号 | 排序 | 字段1 | 字段2 | ... | 操作 |
每行：|  1   | ▲▼  | 数据  | 数据  | ... | 编辑 删除 |
```

- **序号列**：`.row-rank`，固定宽度 56px，居中，数字从 1 递增
- **排序列**：`.row-sort`，固定宽度 56px，居中，上下两个箭头按钮
- **操作列**：仅放"编辑""删除"按钮，不再混入排序手柄

**CSS 参考：**

```css
.row-sort { display: flex; flex-direction: column; gap: 2px; align-items: center; }
.row-sort .sort-handle {
  width: 24px; height: 18px; display: flex; align-items: center;
  justify-content: center; cursor: pointer; font-size: 11px; line-height: 1;
  color: var(--text-auxiliary); border-radius: 4px;
}
.row-sort .sort-handle:hover { background: var(--primary-light); color: var(--primary); }
.row-rank { color: var(--text-auxiliary); font-weight: 600; }
```

**表头与行参考：**

```html
<thead>
  <tr>
    <th class="text-center" style="width:56px;">序号</th>
    <th class="text-center" style="width:56px;">排序</th>
    <th>{字段1}</th>
    <!-- 其他字段列 -->
    <th class="text-right">操作</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td class="text-center row-rank">1</td>
    <td class="text-center">
      <div class="row-sort">
        <span class="sort-handle" title="上移" onclick="moveRow(this, -1)">▲</span>
        <span class="sort-handle" title="下移" onclick="moveRow(this, 1)">▼</span>
      </div>
    </td>
    <td>数据</td>
    <!-- 其他字段 -->
    <td class="text-right">
      <div class="table-actions">
        <button class="btn-text" onclick="openEditModal(this)">编辑</button>
        <button class="btn-text danger" onclick="deleteRow(this)">删除</button>
      </div>
    </td>
  </tr>
</tbody>
```

**参考代码：**

```javascript
var COUNT_UNIT = '条记录'; // 按项目实际设置单位（如：个/家/位/条），优先从 PRD 读取
var editingRow = null;     // 当前编辑的行，null 表示新增

function openEditModal(btn) {
  if (btn) {
    editingRow = btn.closest('tr');
    var cells = editingRow.querySelectorAll('td');
    // 从 cells 读取数据回填表单
    // 注意跳过序号和排序列：cells[0]=序号 cells[1]=排序 cells[2]起为数据
  } else {
    editingRow = null;
    // 清空表单
  }
  openModal('{editModalId}');
}

function handleSave() {
  // 校验必填
  if (editingRow) {
    // 更新现有行单元格
  } else {
    // 创建新行并 appendChild，然后 refreshTableRanks + updateToolbarCount
  }
  closeModal('{editModalId}');
  editingRow = null;
}

function deleteRow(btn) {
  confirmAction('确认删除该记录？删除后不可恢复。', function () {
    var row = btn.closest('tr');
    if (row && row.parentNode) {
      var tbody = row.parentNode;
      tbody.removeChild(row);
      refreshTableRanks(tbody);
      updateToolbarCount();
      showToast('已删除');
    }
  });
}

function updateToolbarCount() {
  var tbody = document.querySelector('.data-table tbody');
  var count = tbody ? tbody.children.length : 0;
  var hint = document.getElementById('{toolbarCountId}');
  if (hint) hint.textContent = '共 ' + count + ' ' + COUNT_UNIT + '，使用排序箭头调整展示顺序';
}
```

### 4.4 关键检查点

- 新增按钮不传 `id` 和 `this`；编辑按钮必须传 `this`
- 编辑模式必须从卡片/行**读取现有数据回填表单**，不能只清空表单
- 保存后必须**真实更新/创建 DOM**，不能只 Toast
- 删除必须**真实移除 DOM 节点**，不能只 Toast
- 新建元素的按钮 `onclick` 必须与现有元素保持一致的调用约定（传 `this`）
- **涉及排序的卡片列表必须用单列横向布局**，禁止多列 grid
- **展示性内容表格必须有独立的序号列和排序列**，禁止将排序手柄混在"操作"列中
- **排序/新增/删除后必须刷新序号**（`refreshRanks` / `refreshTableRanks`）
- **表格回填时注意列偏移**：有序号和排序列后，数据字段从 `cells[2]` 开始
- 分组标题计数 / 工具栏计数在增删后同步更新
