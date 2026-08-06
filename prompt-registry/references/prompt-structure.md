# prompt 结构规范(权威)

本文件定义 prompt 模板文件的结构规范,是注册前检查 prompt 是否合规的依据。
`prompt-registry/SKILL.md` §四 引用本文件。

## 一、文件格式

prompt 模板文件为 Markdown(`.md`),UTF-8 编码。文件由三部分组成:

1. **系统提示**(System Prompt)— 定义角色 / 约束 / 输出格式
2. **用户提示**(User Prompt)— 定义具体任务 / 输入
3. **占位符声明** — 列出模板中使用的占位符

## 二、结构模板

```markdown
<!-- SYSTEM PROMPT -->
你是 {{skill_name}} 的执行器。
约束:
- {{constraint_1}}
- {{constraint_2}}
输出格式:{{output_format}}

<!-- USER PROMPT -->
请执行以下任务:
{{task_description}}

输入:
{{input}}
```

## 三、占位符规范

占位符用双花括号包裹:`{{placeholder_name}}`

### 3.1 命名规则

- 小写 + 下划线(如 `{{skill_name}}`)
- 语义化命名(如 `{{input_file}}` 而非 `{{x}}`)

### 3.2 常用占位符

| 占位符 | 含义 | 填充方 |
|--------|------|--------|
| `{{skill_name}}` | skill 名称 | 运行时(skill 自身) |
| `{{input}}` | 输入内容 | 运行时(调用方传入) |
| `{{workspace_dir}}` | 工作台根目录 | 运行时(宿主) |
| `{{constraint_N}}` | 约束项 | 运行时(skill 配置) |
| `{{output_format}}` | 输出格式 | 运行时(skill 配置) |

### 3.3 占位符填充

- 占位符在运行时由 skill 填充,注册表中存的是模板(含占位符)
- 未填充的占位符在最终 prompt 中保留原样(`{{xxx}}`)
- 不建议在模板中硬编码路径 / 文件名(用占位符代替)

## 四、示例

### 4.1 简洁版(tag=concise)

```markdown
<!-- SYSTEM PROMPT -->
你是 {{skill_name}} 执行器。按约束执行,输出 {{output_format}}。

<!-- USER PROMPT -->
任务:{{task_description}}
输入:{{input}}
```

### 4.2 详细版(tag=detailed)

```markdown
<!-- SYSTEM PROMPT -->
你是 {{skill_name}} 的执行器,负责以下职责:
{{responsibilities}}

执行约束:
{{constraints}}

输出格式:
{{output_format}}

失败处理:
{{failure_handling}}

<!-- USER PROMPT -->
请执行以下任务:
{{task_description}}

输入参数:
{{input}}

上下文:
{{context}}
```

## 五、与注册表的关系

- 注册表存储的是**模板**(含占位符),不是最终 prompt
- 运行时由 skill 读取模板 + 填充占位符 + 交给模型执行
- 模型选择(用哪个模型)由宿主决定,本 skill 不涉及

## 六、与 SKILL.md 的关系

- 本文件是 prompt 结构规范的权威来源
- SKILL.md 不重复结构规范细节,仅引用本文件
- `skill-auditor` 审查 prompt 结构合规性时对照本文件
