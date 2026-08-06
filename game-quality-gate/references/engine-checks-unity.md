# Unity 引擎特定检查

> 本文件供 game-quality-gate Gate 3 读取。当 PRD/TECH_DESIGN 的引擎字段为 `Unity` 时,按本文件执行引擎特定的 L2 契约检查与 L3 实跑预检。
>
> 新增引擎时只需新建 `references/engine-checks-{engine}.md` 并在此处登记,SKILL.md 不动。

---

## L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.13 | Resources.Load 路径一致 | `.cs` 中 `Resources.Load("path/noext")` 路径与 `Assets/Resources/` 下实际文件一致(去扩展名) | `G3-UNITY-RESOURCE-PATH` | ERROR |
| 3.14 | SceneBuilder 产出一致 | `Assets/Scenes/Main.unity` 由 SceneBuilder 程序化生成(非空且含基础节点) | `G3-UNITY-SCENE-BUILDER` | ERROR |

**3.13 检查方法**:扫描 `Assets/Scripts/Runtime/*.cs` 中所有 `Resources.Load<T>("path")` 调用,提取 path(去扩展名),与 `Assets/Resources/` 下实际文件(去 `.prefab`/`.asset`/`.png` 等扩展名)比对,路径不存在则 FAIL。

**3.13 常见失败原因**:
- `Resources.Load` 路径含扩展名(应为 `path/noext`,Unity 自动补扩展名)
- 资源放在 `Resources/` 子目录但 path 未含子目录前缀
- 资源未放在 `Assets/Resources/` 下(Unity 只能 Load 该目录)

**3.14 检查方法**:校验 `Assets/Scenes/Main.unity` 文件存在且非空,且含 `Editor/SceneBuilder.cs` 程序化生成的基础节点(Canvas、EventSystem 等)。若 `.unity` 不存在或为空,说明 SceneBuilder 未在 batchmode 首次导入时运行。

**修复建议**:`Resources.Load` 路径统一去扩展名;SceneBuilder 在 `Editor/BuildScript.cs` 的 batchmode 入口中显式调用,确保场景文件生成。

---

## L3 实跑预检

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.17 | Unity 编译检查 | 沙箱无 Unity 时跳过(标注 `G3-UNITY-SKIPPED`),由 game-integrate Gate 4 补 | `G3-UNITY-CHECK-FAILED` | SKIPPED |

**检查方法**:若沙箱有 Unity Editor,执行 `unity -batchmode -quit -projectPath . -logFile -` 检查编译;沙箱无 Unity 时标注 SKIPPED,延后到 Gate 4 由 game-integrate 补。

> **软阻断**:SKIPPED 不阻断流水线,允许进入 Gate 4,由 game-integrate 在构建时补编译检查。

---

## 依赖检查(与 L3 并行)

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.18 | 依赖可解析 | `ProjectSettings/ProjectVersion.txt` 存在且 `Assets/Scripts/Runtime/*.asmdef` + `Assets/Scripts/Editor/*.asmdef` 齐全 | `G3-DEP-MISSING` | ERROR |

> Unity 用 Package Manager,依赖检查改为程序集定义(.asmdef)与版本标识完整性校验。
