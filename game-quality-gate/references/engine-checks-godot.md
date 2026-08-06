# Godot 4 引擎特定检查

> 本文件供 game-quality-gate Gate 3 读取。当 PRD/TECH_DESIGN 的引擎字段为 `Godot 4` 时,按本文件执行引擎特定的 L2 契约检查与 L3 实跑预检。
>
> 新增引擎时只需新建 `references/engine-checks-{engine}.md` 并在此处登记,SKILL.md 不动。

---

## L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.11 | NodePath 一致 | `.gd` 中 `$NodePath` 与 `.tscn` 节点树实际路径一致 | `G3-GODOT-NODEPATH` | ERROR |
| 3.12 | 信号连接一致 | `.gd` 中 `connect("signal", ...)` 的信号在 `.tscn` 有对应节点定义 | `G3-GODOT-SIGNAL` | ERROR |

**3.11 检查方法**:扫描 `scripts/` 下所有 `.gd` 文件中 `$NodePath` 或 `%UniqueNode` 引用,与 `scenes/*.tscn` 的节点树(解析 `[node name="..." parent="..."]` 行)比对,路径不存在则 FAIL。

**3.11 常见失败原因**:
- `.tscn` 节点改名后 `.gd` 未同步更新 `$NodePath`
- 场景嵌套层级与 `$` 路径不匹配(如 `$VBox/Label` 但实际是 `$Margin/VBox/Label`)

**3.12 检查方法**:扫描 `.gd` 中所有 `.connect("signal_name", ...)` 调用,确认对应 `.tscn` 的节点定义含该 signal(或节点类型内置该 signal)。

**3.12 常见失败原因**:
- 自定义信号未在 `.gd` 中 `signal` 声明就 connect
- connect 的目标节点在 `.tscn` 中不存在

**修复建议**:NodePath 用 `%UniqueNode`(Godot 4 unique name)替代长路径,减少层级耦合;自定义信号在节点脚本顶部显式 `signal my_signal` 声明。

---

## L3 实跑预检

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.16 | Godot 类型检查 | `godot --headless --check-only --script scripts/main.gd` 退出码 0 | `G3-GODOT-CHECK-FAILED` | ERROR |

**检查方法**:在工程根目录执行 `godot --headless --check-only --script scripts/main.gd`,捕获 stderr,退出码非 0 则 FAIL。

> **`--script` 参数必填**:Godot 4 的 `--check-only` 需配合 `--script` 指定主脚本才生效,否则仅校验空脚本(假阳性)。

**失败处理**:本 skill 只读错误日志并归类到失败清单,返回给 game-code-forge 修复(沿用其 GDScript 修复策略,最多 3 轮)。

---

## 依赖检查(与 L3 并行)

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.18 | 依赖可解析 | `project.godot` 存在且 `[application]` 段配置完整 | `G3-DEP-MISSING` | ERROR |

> Godot 4 无 npm 依赖,依赖检查改为工程配置完整性校验。
