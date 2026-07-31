---
name: "game-integrate"
description: "AI 游戏生成流水线阶段 5。读取 assets/ 和 src/,执行 npm install、typecheck、构建、浏览器自测,产出 dist/ 和验收报告。当被 game-forge-master 调度到本阶段,或用户要'集成构建/联调游戏'时调用。"
---

# Game Integrate — 集成与构建

本 skill 是 AI 游戏生成流水线的**阶段 5(最终阶段)**,职责是把 assets/ 与 src/ 集成,执行依赖安装、类型检查、构建、浏览器自测,产出 `dist/` 和 `docs/BUILD_REPORT.md`。

---

## 一、输入与输出

**输入**(必读):
- `assets/` 目录(由 game-asset-forge 产出)
- `src/`、`index.html`、`package.json` 等(由 game-code-forge 产出)
- `docs/ASSET_MANIFEST.json`(校验资源完整性)
- `docs/ASSET_ISSUES.md`(如有,了解已知问题)

**输出**(固定路径):
- `dist/`(构建产物)
- `docs/BUILD_REPORT.md`(验收报告)

---

## 二、执行流程

```
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

```markdown
# {游戏名} - 构建验收报告

## 1. 总览
- 构建时间:{ISO timestamp}
- 构建结果:{成功/失败}
- 工程路径:{绝对路径}
- 引擎:{Phaser 3 / Pixi / Canvas}
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

## 7. 下一步建议
1. 替换占位美术资源(见 ASSET_ISSUES.md)
2. 修复 typecheck 降级项
3. 补充音频(默认静音占位)
4. (如需)接入 inject-cdn 部署 CDN
```

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

---

## 九、质量检查清单

- [ ] npm install 成功
- [ ] typecheck 通过或已降级
- [ ] dev server 能启动
- [ ] 浏览器能加载首屏
- [ ] 至少 1 个关键交互能响应
- [ ] build 产出 dist/index.html
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
   - Hero 持续下坠 → 回到 game-code-forge §十一 Sprite/Body 偏移排查
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
