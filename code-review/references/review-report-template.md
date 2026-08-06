# 代码审查报告模板

> 复制本模板填写。所有 `<...>` 为占位符,填写后删除占位符标记。

---

# 代码审查报告

| 项目 | 内容 |
|------|------|
| 审查范围 | `<PR #123 / commit a1b2c3..d4e5f6 / 文件列表>` |
| 审查时间 | `<2026-08-06T10:30:00+08:00>` |
| 审查者 | code-review skill |
| 变更文件数 | `<N>` |
| 合并建议 | `<阻断合并 / 可合并(建议跟进 warning)/ 可合并>` |

## 一、总览

| 严重级别 | 数量 |
|----------|------|
| blocker | `<N>` |
| warning | `<N>` |
| suggestion | `<N>` |
| **合计** | `<N>` |

按维度分布:

| 维度 | blocker | warning | suggestion | 小计 |
|------|---------|---------|------------|------|
| 正确性 | `<N>` | `<N>` | `<N>` | `<N>` |
| 安全性 | `<N>` | `<N>` | `<N>` | `<N>` |
| 性能 | `<N>` | `<N>` | `<N>` | `<N>` |
| 可维护性 | `<N>` | `<N>` | `<N>` | `<N>` |

## 二、问题清单

> 按严重级别降序(blocker → warning → suggestion),同级按维度顺序排列。

| ID | 维度 | 严重级别 | 文件:行 | 描述 |
|----|------|----------|---------|------|
| CR-001 | security | blocker | `src/auth/login.ts:42` | 硬编码 API Key |
| CR-002 | correctness | blocker | `src/utils/calc.ts:18` | 除零未判空导致崩溃 |
| CR-003 | performance | warning | `src/api/list.ts:67` | 循环内 N+1 查询 |
| ... | ... | ... | ... | ... |

## 三、修复建议

> 对每条 issue 给出可执行的修复方案。含代码示例时用对应语言代码块。

### CR-001 — 硬编码 API Key(blocker, security)
- **位置**:`src/auth/login.ts:42`
- **问题**:`const API_KEY = "sk-xxxxxx"` 直接硬编码,泄露后可被滥用。
- **建议**:从环境变量读取,生产环境接入密钥管理服务。

```ts
// 修复前
const API_KEY = "sk-xxxxxx";

// 修复后
const API_KEY = process.env.API_KEY;
if (!API_KEY) throw new Error("API_KEY 未配置");
```

### CR-002 — 除零未判空导致崩溃(blocker, correctness)
- **位置**:`src/utils/calc.ts:18`
- **问题**:`return total / count;` 当 `count === 0` 时返回 `Infinity` 或抛错。
- **建议**:增加零值保护并明确返回语义。

```ts
// 修复后
if (count === 0) return 0;
return total / count;
```

### CR-003 — 循环内 N+1 查询(warning, performance)
- **位置**:`src/api/list.ts:67`
- **问题**:在 `for` 循环内对每个 item 查询用户信息,共 N 次查询。
- **建议**:改为一次性批量查询,按 ID 映射。

```ts
// 修复后
const userIds = items.map(i => i.userId);
const users = await userRepo.findByIds(userIds);
const userMap = new Map(users.map(u => [u.id, u]));
items.forEach(i => (i.user = userMap.get(i.userId)));
```

## 四、通过项摘要

> 明确指出哪些维度 / 文件未发现问题,避免"沉默通过"。

- **正确性**:本次变更的核心逻辑(登录流程、计算工具)在边界条件、异常处理方面未发现 blocker 级问题。
- **安全性**:除上述 CR-001 外,其他接口的鉴权中间件齐全,未发现 SQL 注入 / XSS 风险。
- **性能**:除 CR-003 外,其他改动未引入 N+1 或大对象拷贝。
- **可维护性**:新增代码命名清晰、函数长度合理,未发现重复代码。

## 五、合并结论

- [ ] 存在 blocker → **阻断合并**,需修复 CR-001、CR-002 后重新审查。
- [ ] 无 blocker,仅 warning / suggestion → **可合并**,建议在下一迭代跟进 CR-003。

**最终建议**:`<阻断合并 / 可合并>`
