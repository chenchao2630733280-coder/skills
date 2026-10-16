# A~H 八类门禁 · 落地写法

> 语言无关，示例用 Python / JS。所有片段都是**只读**的，门禁不改产物。

## A 四方一致

```python
spec_ids   = {p['id'] for p in json.loads(T('spec/pages.json'))['pages']}
html_ids   = {fn.split('-')[0] for fn in os.listdir('site/mobile') if fn.endswith('.html')}
doc_ids    = set(re.findall(r'^\|\s*(P\d+\w?)\s*\|', doc_a1_section, re.M))
portal_ids = {pg['id'] for m in PROJECT_MAP for pg in m['pages']}

# 双向差集，两个都必须为空
assert spec_ids - html_ids == set(), 'spec 有而 HTML 缺失'
assert html_ids - spec_ids == set(), 'HTML 有而 spec 未登记'
```

**要点**：不要只查一个方向。只查「spec 里的都存在于 HTML」会漏掉「HTML 里多出来的孤儿页」。

## B 单源副本逐字节相同

```python
a = open('site/pc/sidebar.js', 'rb').read()
b = open('site/mobile/navbar.js', 'rb').read()
block_a = extract_between(a, b'/* @shared:begin */', b'/* @shared:end */')
block_b = extract_between(b, b'/* @shared:begin */', b'/* @shared:end */')
assert block_a == block_b, '共享块不一致 @%d' % first_diff(block_a, block_b)
print('① 共享块 %d B，逐字节相同 = %s' % (len(block_a), block_a == block_b))
```

**加载期漂移自检**（防未来漂移，放进运行时）：

```js
// 加载时遍历「固定枚举」断言两处一致
if (window.WH && window.WH.suborderLabel) {
  FIXED_CODES.forEach(function (k) {
    need(window.WH.suborderLabel(k) === SUBORDER_LABELS[k], '标签漂移：' + k);
  });
}
```

> ⚠️ **动态项要刻意排除**：若某个标签是按参数动态生成的，把它写进这个自检会**恒失败**。

## C 投影契约（按值互校）

```python
# 同一实体在 ≥2 端出现时，字段必须一致
LEFT  = {r['no']: r for r in rows_of_end_a}
RIGHT = {r['no']: r for r in rows_of_end_b}
for no in set(LEFT) & set(RIGHT):
    for f in ('amount', 'status', 'channel', 'voucherNo', 'counterparty'):
        assert LEFT[no][f] == RIGHT[no][f], '%s.%s 跨端不一致' % (no, f)
print('已比对 %d 项' % len(set(LEFT) & set(RIGHT)))
```

**反例（不要这么写）**：

```python
# ❌ 键序敏感 ⇒ 假失败
assert json.dumps(LEFT[no]) == json.dumps(RIGHT[no])
```

## D 派生不变量（含反向覆盖）

```python
# 正向：有子记录的父，其金额 == 子记录求和
for p in parents:
    subs = [s for s in subs if s['parent'] == p['id']]
    if subs:
        assert round(sum(s['amount'] for s in subs), 2) == p['amount']

# 反向覆盖：该有子记录的父，必须都有（防漏数据）
for p in parents:
    if p['stage'] in INVOICE_STAGES:
        assert [s for s in subs if s['parent'] == p['id']], '%s 在开票环节却无子记录' % p['id']

# 状态约束：某类凭证只允许挂特定状态
for v in vouchers:
    assert v['ownerStatus'] in ('DECLARED', 'PAID')
```

**反向覆盖是必需项**：只写「有子记录的父存在」永远发现不了「该有子记录的父缺记录」。

## E 陈旧术语三层扫描（±N 窗口 + 白名单）

```python
HARD  = [r'废弃能力名', r'旧状态名']
QUOTE = r'\[标签调整\][^\n]{0,60}正名为[^\n]{0,40}'   # 只允许出现在文档
CANON = {'待局办确认': ['site/pc/sidebar.js', 'docs/xx.md'], ...}   # 合法位置清单

for f in files:
    text = T(f)
    for pat in HARD:
        assert not re.search(pat, text), '%s 命中硬禁词' % f
    for m in re.finditer(pat_old, text):
        window = text[max(0, m.start() - 60): m.end() + 60]
        assert re.search(QUOTE, window), '%s 出现陈旧引用且非迁移说明' % f
```

> ⚠️ **正则里刻意保留的特殊符号（如全角箭头）不要顺手统一掉** —— 换掉它会让
> `window` 判据恒真，QUOTE 检查从此**静默空转**。改门禁本身也要过负向自检。

## F 负向自检（门禁的牙齿）

```python
def run_scanner(rows): ...          # 扫描器内核，返回 {契约: 命中数}

# 基线：应全 0
base = run_scanner(clean_rows)
assert all(v == 0 for v in base.values())

# 造错：把一个实体的对手方改成另一个
broken = copy.deepcopy(clean_rows)
broken[0]['counterparty'] = '不存在的对手方'
res = run_scanner(broken)
assert res['对方一致性'] == 1, '造错未被报出 —— 扫描器没牙齿'
assert res['金额一致性'] == 0 and res['状态一致性'] == 0, '误伤其他契约'
print('负向自检：全部报出（扫描器有牙齿）')
```

## G 覆盖面对照（防静默空转）

```python
print('覆盖率对照：')
for f in candidate_files:
    n = count_literals(f)          # 该文件里有多少可静态比对的数据字面量
    print('  %-40s 字面量 %d %s' % (f, n, '← 由运行时断言兜底' if n == 0 else ''))
print('总账实体 %d 个 · 被页面字面量覆盖 %d 个 · 仅有共享块镜像 %d 个'
      % (total, covered, total - covered))
```

**判读规则**：`字面量 0` 的文件不是「没事」，而是**这个门禁查不到它** ⇒ 必须另有运行时断言兜底，
否则写明「本门禁对本文件无覆盖」。

## H 构建报告（规模 + 指纹）

```python
import hashlib
def h(b):
    return hashlib.md5(b.replace(b'\r\n', b'\n')).hexdigest()[:12]   # 归一化后再摘要

report = {
    'items': [{'id': pid, 'path': rel, 'contentHash': h(open(rel, 'rb').read()),
               'lines': text.count('\n') + 1} for pid, rel in pages],
    'total': len(pages),
    'totalLines': sum(...),
    'result': 'PASS',
}
```

**要点**：摘要前**归一化行尾**，否则同一份内容在不同平台会得到不同指纹；
`totalLines` 是否排除索引页要固定口径并写明。
