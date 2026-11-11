# BUILD_REPORT.md 模板

> 本文件从 game-integrate SKILL.md 抽离,作为验收报告的完整模板。生成 BUILD_REPORT.md 时读取本文件。

```markdown
# {游戏名} - 构建验收报告

## 1. 总览
- 构建时间:{ISO timestamp}
- 构建结果:{成功/失败}
- 工程路径:{绝对路径}
- 引擎:{Phaser 3 / Pixi / Canvas / Godot 4 / Unity / Three.js}
- 代码文件数:{N}
- 资源文件数:{M}

## 2. 各阶段结果

| 阶段 | 状态 | 耗时 | 备注 |
|---|---|---|---|
| 结构校验 | ✅ | 1s | |
| 资源校验 | ⚠️ | 2s | 2 个缺失,已用占位图替代 |
| npm install | ✅ | 45s | |
| typecheck | ✅ | 3s | 修复 2 轮后通过 |
| 浏览器自测 | ⚠️ | 15s | 首屏正常,1 个 console warning |
| 构建 | ✅ | 8s | dist/ 产出正常 |

## 3. 视觉验收与截图基线

**三步**：建基线 → 跑对比 → 逐项确认差异。

| 步 | 做什么 | 判据 |
|---|---|---|
| 建基线 | `JUICE=0`（去动画噪声）+ 固定视口尺寸 + 固定种子跑一次，存 `docs/screenshots/baseline/` | 同版本连跑两次**字节一致**，否则基线本身就不稳 |
| 跑对比 | 改完同条件再跑，逐张比对 | 只允许出现"预期内"的差异 |
| 确认 | 每处差异写一句"为什么变" | 没有理由的一律当回归 |

截图清单（每张带 `{关卡id} / {视口} / {JUICE系数}` 三项元信息）：

- 首屏:docs/screenshots/01-home.png
- 游戏画面:docs/screenshots/02-game.png
- 关键交互后稳定态:docs/screenshots/03-{交互名}.png

**工具（把"看起来差不多"变成数字）**：`python scripts/visual_diff.py baseline|check|list`，纯标准库，支持 RGB / RGBA / 调色板 PNG，清单落在 `docs/screenshots/baseline/manifest.json`（每条含 `name/width/height/sha256/note`）。

- `check` 输出 `diff_ratio`（差异像素占比）、`bbox`（差异外接矩形）、`hot_tiles`（8×8 网格差异排行），超阈退出码 1 —— 报告里要贴 bbox 与热点 tile，才能判断"是哪一层变了"
- 动态区（计时器／分数／粒子）用 `--mask x,y,w,h` 排除；**不许靠调大 `--max-diff` 让结果变绿**
- 缺基线时 `check` 退出码 2 而不是自动收录：自动收录等于"首次运行永远绿"

报告里对应记一张表：

### 基线对比结果
| 基线名 | 差异占比 | bbox | 判定 | 为什么变 |
|---|---|---|---|---|
| 02-game_l01_1280x720_juice0 | 0.00% | - | 一致 | - |
| 03-jump_l01_1280x720_juice0 | 1.74% | [420,180,96,64] | 超阈 | 新增落地烟尘粒子，预期内 |

**四条硬规矩**：

1. **等状态，不等时间**：截图前断言"某个状态标志位已置位"，不许 `waitForTimeout(800)`。时间驱动的截图在慢机器上会拍到上一帧，而且**看起来全绿**——这是静默假绿最常见的一种形态。
2. **断言 id/参数，不断言"场景就绪"**：自动发现机制失效时，程序倾向**静默回退到默认值**（新关卡没加载 → 跑的还是第 1 关）。只等"场景已启动"会全绿。断言 `{运行时关卡id === 目标id}`。
3. **基线跟内容版本走**：关卡/素材/字体改了要重建基线并随 commit 提交，否则每次都是"有差异但不知道该不该有"。
4. **差异必须解释**：允许"预期内的变化"，不允许"说不上来但看着差不多"。

**差异清单至少覆盖四类**：布局位移 / 字体替换 / 颜色与透明度 / 遮挡层级。

## 4. Console 错误/警告
| 级别 | 信息 | 来源 |
|---|---|---|
| warning | Texture 'skin0' not found | BootScene.ts:23 |

## 5. 已知问题(汇总自 ASSET_ISSUES.md)
- [ ] skin2-jump-3 用占位图,需人工替换
- [ ] bg-game-parallax 未生成,用纯色背景
- [ ] typecheck 降级 strict:false(原 5 处 any 未修复)

## 6. 运行指引
开发:
\`\`\`bash
npm install
npm run dev
\`\`\`
访问 http://localhost:5173

构建:
\`\`\`bash
npm run build
\`\`\`
产物在 dist/

### Godot 4 运行指引
- 桌面端:双击 `export/Game.exe` 或 `godot --path .` 在编辑器中运行
- 浏览器:`python -m http.server 8080 --directory export/Web` 后访问 `http://localhost:8080`
- 编辑器调试:用 Godot 编辑器打开工程,按 F5 运行主场景

### Unity 运行指引
- 桌面端:双击 `Build/Game.exe` 运行
- 浏览器(WebGL):`python -m http.server 8080 --directory Build/Web` 后访问 `http://localhost:8080`
- 编辑器调试:用 Unity Editor 打开工程,Tools > Build Scenes 生成场景后按 ▶ 运行 Main 场景
- 宿主构建命令(沙箱无 Unity 时):
  - `unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.SceneBuilder.BuildAll`
  - `unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.BuildScript.BuildWindows`

## 7. 下一步建议
1. 替换占位美术资源(见 ASSET_ISSUES.md)
2. 修复 typecheck 降级项
3. 补充音频(默认静音占位)
4. (如需)接入 inject-cdn 部署 CDN
```
