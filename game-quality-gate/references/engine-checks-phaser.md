# Phaser 3 引擎特定检查

> 本文件供 game-quality-gate Gate 3 读取。当 PRD/TECH_DESIGN 的引擎字段为 `Phaser 3` 时,按本文件执行引擎特定的 L2 契约检查与 L3 实跑预检。
>
> 新增引擎时只需新建 `references/engine-checks-{engine}.md` 并在此处登记,SKILL.md 不动。

---

## L2 契约检查

| # | 检查项 | 通过条件 | 失败码 | 严重度 |
|---|---|---|---|---|
| 3.9 | anims key 一致 | `this.anims.create` 的 key 与 ART_SPEC/manifest 状态名一致 | `G3-PHASER-ANIM-KEY` | ERROR |

**检查方法**:扫描 `src/` 下所有 `.ts` 文件中 `this.anims.create({ key: '...' })` 的 key 值,与 TECH_DESIGN §7 帧动画定义表、ASSET_MANIFEST 的 `animKey` 字段逐一比对。

**常见失败原因**:
- 代码中写死 key 字符串,与 manifest 的 animKey 拼写不一致(如 `run` vs `skin0-run`)
- 多皮肤场景下 key 未带 skin 前缀,导致动画覆盖

**修复建议**:key 命名统一为 `{skinId}-{state}` 格式,与 manifest 的 animKey 对齐。

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

> Phaser 3 共享 Web 引擎的依赖检查(与 Pixi.js / 纯 Canvas 相同)。
