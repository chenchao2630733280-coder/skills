# Pixi.js 引擎特定检查

> 本文件供 game-quality-gate Gate 3 读取。当 PRD/TECH_DESIGN 的引擎字段为 `Pixi.js` 时,按本文件执行引擎特定的 L2 契约检查与 L3 实跑预检。
>
> 新增引擎时只需新建 `references/engine-checks-{engine}.md` 并在此处登记,SKILL.md 不动。

---

## L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.10 | AnimatedSheet 帧数一致 | 代码引用的帧数与 manifest 的 `totalFrames` 字段一致 | `G3-PIXI-FRAME-COUNT` | ERROR |

**检查方法**:扫描 `src/` 下所有 `.ts` 文件中 `new AnimatedSprite(textures)` 或 `AnimatedSheet` 的帧数引用,与 ASSET_MANIFEST 中对应 asset 的 `totalFrames` 字段比对。

**常见失败原因**:
- 代码硬编码帧数(如 `textures.slice(0, 8)`),与 manifest 的 totalFrames 不一致
- 多角色场景下帧数引用串号

**修复建议**:帧数从 manifest 配置读取,不硬编码;`textures.length` 应等于 manifest 的 totalFrames。

---

## L3 实跑预检

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.15 | typecheck | `npm run typecheck` 退出码 0 | `G3-TYPECHECK-FAILED` | ERROR |

**检查方法**:在工程根目录执行 `npm run typecheck`,捕获 stderr,退出码非 0 则 FAIL。

**失败处理**:本 skill 只读错误日志并归类到失败清单,返回给 game-code-forge 修复(沿用其 typecheck 修复策略,最多 3 轮)。

---

## 依赖检查(与 L3 并行)

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.18 | 依赖可解析 | `npm ls` 无 missing | `G3-DEP-MISSING` | ERROR |

> Pixi.js 共享 Web 引擎的依赖检查(与 Phaser 3 / 纯 Canvas 相同)。
