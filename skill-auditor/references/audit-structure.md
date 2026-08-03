# 维度 1:结构与体积审查规则

> 审查 skill 的文件组织、体积控制、懒加载可行性。本维度关注 skill 自身的"工程质量"。

---

## 1.1 SKILL.md 行数阈值

| 行数 | 评级 | 处理建议 |
|---|---|---|
| ≤300 | ✅ 优秀 | 符合懒加载原则,激活成本低 |
| 301-500 | ⚠️ 可接受 | 重内容可进一步抽离到 references |
| >500 | ❌ 必须拆分 | 强制要求抽离到 references/ 或拆分为子 skill |

**检查方法**:
```bash
# 读取 SKILL.md,统计行数
wc -l SKILL.md
```

**常见问题**:
- SKILL.md 包含完整代码模板(应抽到 references/engine-*-template.md)
- SKILL.md 包含详细踩坑规范(应抽到 references/pitfall-*.md)
- SKILL.md 包含大段重复内容(应合并或引用 _shared/)

**改造方案模板**:
```
问题:SKILL.md {N} 行,超过 500 行阈值
建议:将 §{X} 的 {内容类型} 抽离到 references/{filename}.md
方案:
1. 创建 references/{filename}.md,迁移 §{X} 内容
2. SKILL.md §{X} 替换为索引块:
   > 完整{内容类型}已抽离到 `references/{filename}.md`,{触发条件}时读取该文件。
3. 在 references 使用指引表添加该文件条目
4. 验证:行数降至 {目标值}
```

---

## 1.2 references 抽离完整性

**检查项**:
1. SKILL.md 中所有 `references/{filename}` 引用指向的文件实际存在
2. references/ 目录下的文件都在 SKILL.md 的"references 使用指引"表中有对应条目
3. 无孤立 references 文件(存在但未被 SKILL.md 引用)
4. 无幽灵引用(SKILL.md 引用但文件不存在)

**检查方法**:
```
1. 提取 SKILL.md 中所有 references/{filename} 引用 → 集合 A
2. 列出 references/ 目录实际文件 → 集合 B
3. A - B = 幽灵引用(CRITICAL)
4. B - A = 孤立文件(WARNING)
```

**严重级别**:
- 幽灵引用 → CRITICAL(激活时读取会失败)
- 孤立文件 → WARNING(维护负担,未被使用)

---

## 1.3 章节编号连续性

**检查项**:
1. 章节编号连续(一、二、三...无跳号)
2. 无重复编号(两个"五、")
3. references 内部章节编号与 SKILL.md 引用一致(如 SKILL.md 写"详见 §6.7",references 中确实有 §6.7)

**检查方法**:
```
1. 提取所有 ## 开头的章节标题
2. 按出现顺序提取编号(一/二/...或 1/2/...)
3. 验证连续性
4. 提取所有"§X.Y"引用,在对应 references 中验证存在
```

**严重级别**:
- 跳号或重号 → WARNING
- §引用指向不存在的章节 → CRITICAL

---

## 1.4 frontmatter description 质量

**检查项**:
1. 包含 **what**(skill 做什么)
2. 包含 **when**(何时调用/触发条件)
3. 长度 ≤200 字符(skill-creator 要求)
4. 语言与 skill 内容一致(中文 skill 用中文 description)

**质量评级**:
| 评级 | 标准 | 示例 |
|---|---|---|
| ✅ 优秀 | what + when + ≤200 字符 | "审查 skill 质量并给出优化建议。当用户要'审查/优化/分析 skill'时调用。" |
| ⚠️ 一般 | 有 what 缺 when | "AI 游戏生成流水线阶段 4b,生成游戏代码。" |
| ❌ 差 | 缺 what 或缺 when,或超长 | "代码生成 skill"(太简,缺 when) |

**改造方案**:
```
原:{原 description}
改:{what}。当用户要'{触发条件}'时调用。
```

---

## 1.5 重复内容检测

**检查项**:
1. 无与 `_shared/references/` 重复的本地拷贝
2. 同一 skill 集合内无跨 skill 重复内容(应抽到 _shared/)
3. SKILL.md 内无重复段落

**检查方法**:
```
1. 列出 _shared/references/ 下所有文件
2. 对被审查 skill 的 references/ 文件,检查是否有同名或内容高度相似的文件
3. 跨 skill 检查:对同前缀 skill(如 game-*),检查是否有重复的规范内容
```

**严重级别**:
- 与 _shared/ 重复 → CRITICAL(违反 DRY,维护时易不一致)
- 跨 skill 重复 → WARNING(应抽到 _shared/)

---

## 1.6 目录结构规范性

**检查项**:
1. SKILL.md 在 skill 根目录(不在子目录)
2. references/ 目录命名一致(不叫 refs/ 或 templates/)
3. 无临时文件/备份文件(*.bak、*.tmp、~*)
4. 文件命名用 kebab-case(不混用 camelCase 或 snake_case)

**严重级别**:
- 结构违反约定 → WARNING
- 临时文件残留 → INFO
