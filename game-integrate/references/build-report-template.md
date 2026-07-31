# BUILD_REPORT.md 模板

> 本文件从 game-integrate SKILL.md 抽离,作为验收报告的完整模板。生成 BUILD_REPORT.md 时读取本文件。

```markdown
# {游戏名} - 构建验收报告

## 1. 总览
- 构建时间:{ISO timestamp}
- 构建结果:{成功/失败}
- 工程路径:{绝对路径}
- 引擎:{Phaser 3 / Pixi / Canvas / Godot 4}
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

## 3. 浏览器自测截图
- 首屏:docs/screenshots/01-home.png
- 游戏画面:docs/screenshots/02-game.png
- 跳跃交互:docs/screenshots/03-jump.png

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

## 7. 下一步建议
1. 替换占位美术资源(见 ASSET_ISSUES.md)
2. 修复 typecheck 降级项
3. 补充音频(默认静音占位)
4. (如需)接入 inject-cdn 部署 CDN
```
