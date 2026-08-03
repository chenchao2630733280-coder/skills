---
name: "game-integrate"
description: "AI 游戏生成流水线阶段 5。读取 assets/ 和 src/(Web 引擎)或 Godot 工程(Godot 4)或 Unity 工程(Unity),执行 npm 构建或 godot --headless --export 或 unity -batchmode,产出 dist/ 或 export/ 或 Build/ 和验收报告。当被 game-forge-master 调度到本阶段,或用户要'集成构建/联调游戏'时调用。"
---

# Game Integrate — 集成与构建

本 skill 是 AI 游戏生成流水线的**阶段 5(最终阶段)**,职责是把 assets/ 与 src/ 集成,执行依赖安装、类型检查、构建、浏览器自测,产出 `dist/`(Web)/ `export/`(Godot)/ `Build/`(Unity)和 `docs/BUILD_REPORT.md`。

---

## 一、输入与输出

**输入**(必读):
- `assets/` 目录(由 game-asset-forge 产出)
- `src/`、`index.html`、`package.json` 等(由 game-code-forge 产出)
- `docs/ASSET_MANIFEST.json`(校验资源完整性)
- `docs/ASSET_ISSUES.md`(如有,了解已知问题)

**Godot 4 工程输入**(引擎为 Godot 4 时):
- `project.godot`:工程配置文件(校验存在性)
- `scenes/*.tscn`:场景文件
- `scripts/*.gd`:GDScript 脚本
- `export_presets.cfg`:导出预设
- `assets/`:复用 game-asset-forge 产出的资源目录

**Unity 工程输入**(引擎为 Unity 时):
- `ProjectSettings/ProjectVersion.txt`:Unity 版本标识(校验为 2022.3 LTS)
- `Assets/Scripts/Runtime/*.cs`:运行时脚本
- `Assets/Scripts/Editor/SceneBuilder.cs`:场景程序化构建脚本
- `Assets/Scripts/Editor/BuildScript.cs`:构建入口脚本
- `Assets/Scripts/Runtime/{ProjectName}.asmdef`:程序集定义
- `Packages/manifest.json`:包依赖
- `Assets/Resources/`:复用 game-asset-forge 产出的资源(放入 Resources 目录)
- 宿主环境需安装 Unity Editor(2022.3 LTS)

**输出**(固定路径):
- `dist/`(构建产物)
- `docs/BUILD_REPORT.md`(验收报告)
- Godot 4 工程:`export/*.{exe,pck,html,zip}`(导出产物)
- Unity 工程:`Build/*.{exe,html}`(导出产物)

---

## references 使用指引

| 文件 | 何时读取 |
|------|---------|
| `references/build-report-template.md` | 产出 BUILD_REPORT.md 验收报告时 |

---

## 二、执行流程

### 2.0 引擎判定

读取 `docs/GAME_BLUEPRINT.md` 的"3. 平台与引擎"章节,按引擎走不同分支:
- **Web 引擎(Phaser/Pixi/Canvas)**:走 npm/Vite 流程(§2.1-§2.6 原有步骤)
- **Godot 4**:走 Godot CLI 流程(§2.7 新增步骤)
- **Unity**:走 Unity CLI 流程(§2.8 新增步骤,需宿主安装 Unity Editor)

### 2.1-2.6 Web 引擎流程

```
(Web 引擎)
1. 校验工程结构完整性
   ├─ package.json 存在
   ├─ index.html 存在
   ├─ src/main.ts 存在
   └─ tsconfig.json 存在

2. 校验资源完整性
   ├─ 遍历 ASSET_MANIFEST.json 的 assets
   ├─ 每条 path 对应的文件存在
   └─ 不存在的用占位图替代(再次降级)

3. npm install
   ├─ 执行 npm install
   ├─ 失败重试 1 次(清缓存后)
   └─ 仍失败则告知用户检查网络

4. typecheck
   ├─ 执行 npm run typecheck
   ├─ 失败则 AI 自动修复(最多 3 轮)
   └─ 仍失败降级 tsconfig strict:false + 标记

5. dev server 启动 + 浏览器自测
   ├─ npm run dev(非阻塞后台运行)
   ├─ 等待 5 秒
   ├─ 用 browser_use agent 访问 http://localhost:5173
   ├─ 截图首屏
   ├─ 测试关键交互(点击/键盘)
   └─ 关闭 dev server

6. 构建
   ├─ npm run build → dist/
   └─ 校验 dist/index.html 存在

7. 输出 BUILD_REPORT.md
```

### 2.7 Godot 4 构建流程(引擎为 Godot 4 时执行)

**步骤 1:校验工程结构完整性**
- 校验 `project.godot` 存在且 `config_version=5`(Godot 4 格式)
- 校验 `scenes/Main.tscn` 存在(主场景)
- 校验 `scripts/main.gd` 或对应入口脚本存在
- 校验 `export_presets.cfg` 存在(至少一个 runnable 预设)

**步骤 2:校验资源完整性**
- 对照 `docs/ASSET_MANIFEST.json` 检查 `assets/` 下资源文件存在
- Godot 资源用 `res://` 协议引用,确认 .tscn/.gd 中的资源路径与实际文件一致

**步骤 3:脚本检查(Godot 的 typecheck)**
```bash
godot --headless --check-only --script scripts/main.gd
```
- 失败时 AI 自动修复最多 3 轮(检查 GDScript 4.x 语法:@onready/@export/await/typed variables)
- 仍失败则降级:在 BUILD_REPORT.md 标记"脚本检查未通过,需手动 review",不阻塞导出

**步骤 4:导出构建(替代 npm run build)**

Windows Desktop 导出:
```bash
godot --headless --export-release "Windows Desktop" export/Game.exe
```

HTML5 导出(用于浏览器自测):
```bash
godot --headless --export-release "HTML5" export/Web/index.html
```

- 导出产物校验:检查 `export/Game.exe`(Windows)或 `export/Web/index.html`(HTML5)存在
- 导出失败时检查 export_presets.cfg 的 preset name 与命令行参数是否一致

**步骤 5:浏览器自测(HTML5 导出时)**
- 用 `python -m http.server 8080 --directory export/Web` 启动本地服务
- browser_use agent 访问 `http://localhost:8080/index.html`
- 截图首页 + 执行基本交互(点击/按键)
- 记录 Console 错误和警告

**步骤 6:桌面端自测(Windows 导出时)**
- 直接运行 `export/Game.exe`
- 等待 5 秒后检查进程是否存活(未崩溃)
- 如有崩溃,记录退出码和 Godot 错误日志
- 无法自动化截图时,标记"需手动运行验证"

**步骤 7:输出 BUILD_REPORT.md**
- 同 Web 引擎流程的验收报告格式,但引擎字段标注 "Godot 4"
- 导出产物路径记录为 `export/` 而非 `dist/`

### 2.8 Unity 构建流程(引擎为 Unity 时执行)

> **前置条件**:宿主环境已安装 Unity Editor 2022.3 LTS,且 `unity`(Windows 为 `Unity.exe`)在 PATH 中。AI 不在沙箱内运行 Unity,构建命令由宿主执行;若沙箱无 Unity,产出代码与配置,在 BUILD_REPORT 标记"构建需在宿主执行"。

**步骤 1:校验工程结构完整性**
- 校验 `ProjectSettings/ProjectVersion.txt` 存在且版本为 `2022.3 LTS`
- 校验 `Assets/Scripts/Runtime/{ProjectName}.asmdef` 存在(运行时程序集定义)
- 校验 `Assets/Scripts/Editor/SceneBuilder.cs` 存在(场景构建脚本)
- 校验 `Assets/Scripts/Editor/BuildScript.cs` 存在(构建入口脚本)
- 校验 `Packages/manifest.json` 存在(包依赖)

**步骤 2:校验资源完整性**
- 对照 `docs/ASSET_MANIFEST.json` 检查 `Assets/Resources/` 下资源文件存在
- Unity 资源用 `Resources.Load("path/noext")` 引用(无扩展名),确认 .cs 中的资源路径与实际文件一致(去扩展名)

**步骤 3:编译检查(Unity 的 typecheck,隐式)**
```bash
unity -batchmode -quit -projectPath . -logFile build-compile.log -stackTrace
```
- 此命令会导入工程并编译所有 .cs,编译失败会在日志中报 CS#### 错误
- 读取 `build-compile.log`,定位 `Compilation failed` 与 `error CS` 行
- 失败时 AI 自动修复最多 3 轮(检查 C# 语法:命名空间、using、类型、特性 [SerializeField]/[RequireComponent])
- 仍失败则降级:在 BUILD_REPORT.md 标记"编译未通过,需手动 review",不阻塞后续步骤(但导出可能失败)

**步骤 4:场景构建(首次执行)**
```bash
unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.SceneBuilder.BuildAll -logFile build-scene.log
```
- 此命令调用 SceneBuilder 程序化生成 `Assets/Scenes/Main.unity` 与 `Assets/Scenes/BootScene.unity`
- 校验 `Assets/Scenes/Main.unity` 存在(场景生成成功)
- 若 SceneBuilder 执行失败:降级仅保留 Main 场景,BootScene 用 UnityMain 在运行时动态加载

**步骤 5:导出构建(替代 npm run build)**

Windows Desktop 导出:
```bash
unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.BuildScript.BuildWindows -logFile build-windows.log
```

WebGL 导出(用于浏览器自测):
```bash
unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.BuildScript.BuildWebGL -logFile build-webgl.log
```

- 导出产物校验:检查 `Build/Game.exe`(Windows)或 `Build/Web/index.html`(WebGL)存在
- 导出失败时读取对应 log,常见原因:平台模块未安装(WebGL/Windows Build Support 模块)、SceneBuilder 未生成场景、.asmdef 引用错误
- 失败回退:降级只导出 WebGL(跳过桌面导出),或只生成工程不导出(标记"需宿主手动导出")

**步骤 6:浏览器自测(WebGL 导出时)**
- 用 `python -m http.server 8080 --directory Build/Web` 启动本地服务
- browser_use agent 访问 `http://localhost:8080/index.html`
- 截图首页 + 执行基本交互(点击/按键)
- 记录 Console 错误和警告(Unity WebGL 的 console 输出在 `console.log` 中)

**步骤 7:桌面端自测(Windows 导出时)**
- 直接运行 `Build/Game.exe`
- 等待 5 秒后检查进程是否存活(未崩溃)
- 如有崩溃,记录退出码和 `Player.log`(Windows 路径:`%USERPROFILE%/AppData/LocalLow/{CompanyName}/{ProductName}/Player.log`)
- 无法自动化截图时,标记"需手动运行验证"

**步骤 8:输出 BUILD_REPORT.md**
- 同 Web 引擎流程的验收报告格式,但引擎字段标注 "Unity 2022.3 LTS"
- 导出产物路径记录为 `Build/` 而非 `dist/`
- 若沙箱无 Unity Editor,标注"代码与配置已产出,构建需在宿主执行"并列出宿主执行命令

---

## 三、类型检查与自动修复

### 1. 执行 typecheck
```bash
npm run typecheck 2>&1 | tee /tmp/typecheck.log
```

### 2. 自动修复策略
读取 typecheck 错误,按类型分类修复:

| 错误类型 | 修复策略 |
|---|---|
| Property 'xxx' does not exist | 加 interface 字段或用类型断言 |
| Type 'X' is not assignable to 'Y' | 加类型转换或修复类型定义 |
| Cannot find module | 检查 import 路径,补 .js 后缀或调整 |
| Cannot find name 'XXX' | 补 import 或声明 |
| Expected N arguments but got M | 修复调用方参数 |

### 3. 修复循环
```
for (let i = 0; i < 3; i++) {
  const errors = runTypecheck();
  if (errors.length === 0) break;
  fixErrors(errors);  // 用 Edit 工具修复
}
if (stillErrors) {
  setTsConfigStrictFalse();
  markIssue('typecheck-failed-degraded');
}
```

### 4. 降级
3 轮修复后仍失败,修改 tsconfig.json `strict: false`,在 BUILD_REPORT 标记。

---

## 四、浏览器自测

### 1. 启动 dev server
```bash
npm run dev  # 非阻塞,后台运行
```

### 2. 等待就绪
通过 CheckCommandStatus 监听输出,等待 "Local: http://localhost:5173" 出现。

### 3. 调用 browser_use agent
启动 browser_use subagent,任务:
1. 导航到 http://localhost:5173
2. 等待 2 秒让资源加载
3. 截图首屏 → 保存到 `docs/screenshots/01-home.png`
4. 检查 console errors,记录到报告
5. 执行关键交互:
   - 点击开始按钮(如有)
   - 等待 3 秒看是否进入游戏
   - 截图游戏画面 → `docs/screenshots/02-game.png`
   - 触发跳跃(点击/空格)
   - 截图 → `docs/screenshots/03-jump.png`
6. 返回:
   - 各阶段截图路径
   - console errors 清单
   - 关键交互是否成功

### 4. 关闭 dev server
用 StopCommand 停止 npm run dev。

---

## 五、构建

### 1. 执行构建
```bash
npm run build
```

### 2. 校验产物
- `dist/index.html` 存在
- `dist/assets/` 存在(打包后的 JS/CSS)
- 若有 inject-cdn 需求,在此步骤后执行

### 3. 失败处理
构建失败:
- 读取 vite 错误日志
- AI 自动修复(最多 2 轮)
- 仍失败则在 BUILD_REPORT 标记,不阻塞报告输出

---

## 六、BUILD_REPORT.md 模板

> 完整模板已抽离到 `references/build-report-template.md`,产出验收报告时读取该文件。

**必填字段概要**:
- 总览:游戏名称、引擎、构建结果、自测结果
- 各阶段结果表:资源/代码/构建/自测的 PASS/FAIL/SKIP
- 浏览器自测截图(HTML5 导出时)
- Console 错误清单
- 已知问题
- 运行指引(Web/Godot/Unity 分别说明)
- 下一步建议

---

## 七、交互约定

1. 读取工程结构后,**不要问用户**,直接执行流水线
2. 每个阶段完成输出简短进度(用 TodoWrite 追踪)
3. 失败时不阻塞,继续往下走,失败项进报告
4. 最终输出 BUILD_REPORT 路径并简报结果
5. 不要自动调用其他 skill(本 skill 是流水线终点)

---

## 八、关键决策点

### 1. 浏览器自测失败时
- 首屏白屏:可能是资源加载失败,检查 ASSET_MANIFEST 路径
- JS 报错:读取 console,尝试修复
- 资源 404:用占位图替代后重测
- **重测上限 2 轮**,仍失败则标记后跳过

### 2. typecheck 修复策略
优先修复**类型缺失**和**参数不匹配**,这是最常见问题。`any` 类型可暂时容忍(降级 strict)。

### 3. 资源路径不一致
若 ASSET_MANIFEST 的 path 与 game-code-forge 引用不一致:
- 以 ASSET_MANIFEST 为准
- 修改代码中的引用路径
- 不修改 manifest

### 4. Godot 4 失败回退

| 场景 | 回退策略 |
|---|---|
| Godot 导出失败 | 检查 export_presets.cfg 格式;降级只导出 HTML5(跳过桌面导出) |
| Godot 脚本检查失败 | 标记需手动 review,不阻塞导出(GDScript 运行时错误不影响编译) |
| Godot 资源 404 | 检查 res:// 路径;自动用占位图替代 + 标记 |

### 5. Unity 失败回退

| 场景 | 回退策略 |
|---|---|
| 沙箱无 Unity Editor | 产出代码与配置,标注"构建需在宿主执行",列宿主执行命令 |
| Unity 编译失败(CS####) | AI 自动修复 3 轮(检查 using/命名空间/类型/特性);仍失败标记需手动 review |
| SceneBuilder 场景生成失败 | 降级仅生成 Main 场景,BootScene 用 UnityMain 运行时动态加载 |
| Unity 导出失败(平台模块缺失) | 降级只导出 WebGL(跳过桌面);或只产出工程不导出 |
| Unity 资源 404 | 检查 Resources.Load 路径(去扩展名);自动用占位图替代 + 标记 |
| WebGL 自测白屏 | 检查 Build/Web/index.html 与 Build/Web/Build/ 资源;读取浏览器 Console 的 Unity 错误 |

---

## 九、质量检查清单

> 下方默认为 Web 引擎清单;Godot 4 见 §2.7、Unity 见 §2.8 的对应检查项。

**Web 引擎(Phaser/Pixi/Canvas)**:
- [ ] npm install 成功
- [ ] typecheck 通过或已降级
- [ ] dev server 能启动
- [ ] 浏览器能加载首屏
- [ ] 至少 1 个关键交互能响应
- [ ] build 产出 dist/index.html

**Godot 4**:
- [ ] project.godot 存在且 config_version=5
- [ ] godot --check-only 通过或已标记
- [ ] export/ 下存在 Game.exe 或 Web/index.html

**Unity**:
- [ ] ProjectVersion.txt 为 2022.3 LTS
- [ ] Unity 编译通过(CS#### 错误已清零)或已标记
- [ ] Assets/Scenes/Main.unity 已由 SceneBuilder 生成
- [ ] Build/ 下存在 Game.exe 或 Web/index.html
- [ ] (沙箱无 Unity 时)宿主执行命令已列入 BUILD_REPORT

**通用**:
- [ ] BUILD_REPORT.md 完整
- [ ] 已知问题全部列出
- [ ] 截图至少 1 张
- [ ] **数值平衡实测通过**(见 十)

---

## 十、数值平衡实测(关键踩坑)

### 10.1 问题背景

PRD §2.3 与 GameConfig 顶部注释都声明了数值可玩,但:
- 浏览器实测时 Hero 跳不过障碍(间距太近/障碍太高/重力太大)
- 数值推导正确但代码逻辑 bug(如障碍 y 算错、collider 未生效)

本节强制在浏览器自测中验证数值可玩性,避免"代码跑起来但玩不了"。

### 10.2 实测步骤

1. 导航到 dev server URL,等待 5 秒(让障碍生成)
2. 用 browser_evaluate 采集连续 8 帧 Hero 状态:
   ```js
   (() => {
     const game = window.game;
     const scene = game?.scene?.keys?.['Game'] || game?.scene?.getScene('Game');
     const hero = scene?.hero, body = hero?.body;
     return {
       heroY: Math.round(hero?.y),
       bodyBottom: Math.round(body?.y + (body?.height || 0)),
       blockedDown: body?.blocked?.down,
       velocityY: Math.round(body?.velocity?.y),
       obstacles: scene?.obstacles?.length,
     };
   })()
   ```
3. **判定标准**:
   - `blockedDown === true` 且 `velocityY === 0` → Hero 稳定站地面(物理正常)
   - `obstacles >= 1` → 障碍在生成(逻辑正常)
   - Hero 在障碍到达前能跳跃越过(手动 pointerdown 测试或看跳跃曲线)
4. **失败处理**:
   - Hero 持续下坠 → 回到 game-code-forge §十二 Sprite/Body 偏移排查
   - 障碍太密跳不过 → 回到 game-spec §2.3 调整 interval/speed
   - 障碍太高跳不过 → 回到 game-spec §2.3 调整 obstacle.height 或 jumpVelocity

### 10.3 验收报告必填项

BUILD_REPORT.md 必须包含一节:
```
## 数值平衡实测
- Hero 落地稳定: [✓/✗] (blockedDown=true, velocityY=0)
- 障碍正常生成: [✓/✗] (obstacles>=1)
- 跳跃可越过障碍: [✓/✗] (手动测试或跳跃高度 H > 障碍高度)
- 结论: [可玩/需调参]
```
