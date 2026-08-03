# 维度 2:一致性与契约审查规则

> 审查跨 skill 的路径、命名、CLI 命令、JSON 工件消费链对齐。本维度关注 skill 间的"协作契约"。

---

## 2.1 产物路径表与实际产物一致

**检查项**:
1. 编排总纲(如 game-forge-master)的"产物路径总表"中声明的路径,与实际产出该产物的 skill 声明的输出路径一致
2. 路径格式一致(如 `Assets/Scripts/Runtime/**/*.cs` 在总纲和子 skill 中写法相同)
3. 产物归属 skill 正确(总纲声明由 skill A 产出,skill A 的输出确实包含该产物)

**检查方法**:
```
1. 从编排总纲提取产物路径表 → {产物, 路径, 归属 skill}
2. 从归属 skill 的"输出"章节提取路径
3. 对比两者:路径字符串是否完全一致
4. 检查路径中使用的通配符/变量是否一致(**/* vs *.{ext})
```

**严重级别**:
- 路径不一致 → CRITICAL(下游按总纲路径读取会 404)
- 通配符不一致 → WARNING(可能遗漏文件)

---

## 2.2 命名规范跨 skill 一致

**检查项**:
1. 引擎名称一致(如 "Godot 4" 不写成 "Godot4" 或 "Godot")
2. 端类型名称一致(如 "pc-admin" 不写成 "PCAdmin" 或 "pc_admin")
3. 变量占位符一致(如 `{ProjectName}` 不写成 `{projectName}` 或 `{项目名}`)
4. 文件命名规范一致(同一集合内用同一种 case)

**检查方法**:
```
1. 提取所有 skill 中出现的引擎/端类型名称 → 检查拼写统一
2. 提取所有 {占位符} → 检查命名统一
3. 对比同集合 skill 的文件命名风格
```

**示例**:
```
game-forge-master: "Godot 4" ✓
game-code-forge:   "Godot 4" ✓
game-integrate:    "Godot 4" ✓
---
product-pipeline-master: "pc-admin" ✓
generate-html-pc-admin:  "pc-admin" ✓
generate-html-mobile:    "mobile" ✓(端类型简写一致)
```

**严重级别**:
- 引擎/端类型命名不一致 → WARNING(影响检索和路由)
- 占位符不一致 → CRITICAL(自动化替换会遗漏)

---

## 2.3 CLI 命令对齐

**检查项**:
1. 同一 CLI 命令在不同 skill 中的写法完全一致
2. 命令的参数/标志一致(如 `--headless` 不写成 `-headless`)
3. 方法名引用一致(如 `{ProjectName}.Editor.BuildScript.BuildWindows` 在 code-forge 定义、integrate 调用、build-report 列出,三处一致)

**检查方法**:
```
1. 用 Grep 搜索关键 CLI 命令(如 "godot --headless"、"unity -batchmode")
2. 对比所有出现位置的字符串
3. 对 -executeMethod 的方法名,验证在定义文件中存在
```

**示例验证**:
```
grep -rn "BuildScript.BuildWindows" skills/
→ game-code-forge/references/engine-unity-template.md: 定义 BuildScript.BuildWindows()
→ game-integrate/SKILL.md: 调用 unity -executeMethod ...BuildScript.BuildWindows
→ game-integrate/references/build-report-template.md: 列出宿主执行命令
三处一致 ✓
```

**严重级别**:
- 命令字符串不一致 → CRITICAL(执行会失败)
- 方法名引用不存在 → CRITICAL(-executeMethod 找不到方法)

---

## 2.4 JSON 工件消费链

**检查项**:
1. 上游 skill 声明产出的 JSON 字段 ⊇ 下游 skill 声明消费的字段
2. 字段名拼写一致(如上游 `pageId` 下游不写成 `page_id`)
3. 字段类型一致(如上游 `string` 下游不期望 `number`)
4. JSON Schema(如有)与实际产出/消费一致

**检查方法**:
```
1. 从上游 skill 的"输出"章节提取 JSON 字段清单 → 集合 A
2. 从下游 skill 的"输入"章节提取 JSON 字段清单 → 集合 B
3. B - A = 下游消费但上游不产出的字段(CRITICAL)
4. 检查字段名/类型拼写
```

**示例**:
```
generate-html-pages 产出 build-report.json:
  - outputs[].pageId
  - outputs[].device
  - outputs[].path

generate-portal 消费 build-report.json:
  - outputs[].pageId ✓
  - outputs[].device ✓
  - outputs[].path ✓
  - outputs[].contentHash(上游未声明?)→ 需确认
```

**严重级别**:
- 下游消费上游不产出的字段 → CRITICAL
- 字段名拼写不一致 → CRITICAL
- 字段类型不匹配 → WARNING

---

## 2.5 frontmatter 与决策树一致

**检查项**:
1. frontmatter description 中声明的引擎/端类型数量,与决策树实际分支数一致
2. description 中列出的引擎名称与决策树中的名称一致
3. 编排总纲 description 声明的阶段数,与实际编排的阶段数一致

**示例**:
```
game-code-forge frontmatter: "支持 Phaser/Pixi/纯 Canvas/Godot 4/Unity 五引擎"
game-code-forge 决策树: 5 个引擎分支 ✓
game-code-forge 模板索引: 5 个 engine-*-template.md ✓
三者一致 ✓
```

**严重级别**:
- description 声明数与实际不一致 → WARNING(误导路由)
- 引擎名称拼写不一致 → WARNING

---

## 2.6 跨 skill 引用路径正确

**检查项**:
1. skill A 引用 skill B 的 references 文件时,路径正确
2. 引用的文件在 skill B 中实际存在
3. 引用的章节号(§X.Y)在目标文件中存在

**检查方法**:
```
1. 提取所有跨 skill 引用(如 "见 game-code-forge/references/xxx.md")
2. 验证被引用文件存在
3. 验证引用的章节号存在
```

**严重级别**:
- 引用路径不存在 → CRITICAL
- 章节号不存在 → WARNING
