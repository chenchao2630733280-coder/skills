# Gate {N} 门禁报告 - {剧名}（模板）

> 使用说明：复制本文件为 `docs/GATE_{0..4}_REPORT.md` 或 `docs/GATE_3.5_REPORT.md` 后填写（N=0..4 或 3.5）。由 short-drama-quality-gate 产出，只读业务产物（**不得回写 docs/ASSET_MANIFEST.json**）。报告模板细则见 `short-drama-quality-gate/references/report-template.md`，检查项清单见 `short-drama-quality-gate/references/gate-checks.md`。

## 基本信息
- 项目:{剧名}
- 门禁:{Gate 0 立项门 / Gate 1 规格门 / Gate 2 剧本门 / Gate 3 分镜门 / **Gate 3.5 资产门** / Gate 4 生产门}
- 检查时间:{ISO8601}
- 被检产物:
  - Gate 0 → `docs/SHORT_DRAMA_BLUEPRINT.md`
  - Gate 1 → `docs/STORY_SPEC.md` + `docs/EPISODE_OUTLINE.md`
  - Gate 2 → `docs/scripts/EP*.md`
  - Gate 3 → `docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md` + `docs/ASSET_MANIFEST.json`
  - **Gate 3.5 → `docs/ASSET_MANIFEST.json` + `assets/**` + `docs/ASSET_BASELINE.md` + `docs/STORYBOARD.md`**
  - Gate 4 → `production/manifest.json` + `shots/` + `audio/` + `subtitles/`(+ `docs/ASSET_MANIFEST.json` 对照 hash)

## 结论
**{PASS / FAIL}**

- 统计：检查项 {M} 项 | PASS {P} | FAIL {F} | WARNING {W} | 无法校验 {U}

## 检查项明细

| 检查项 | 结果 | 证据 | 说明 |
|---|---|---|---|
| {} | PASS | {} | {} |
| {} | FAIL | {} | {} |
| {} | 无法校验 | {} | {} |

结果取值：`PASS` 通过 / `FAIL` 不通过 / `无法校验` 数据不足 / `WARNING` 软问题。

## FAIL 修复指引
- 回退到阶段:{对应阶段 skill 名}
  - Gate 0/1/2 → 对应阶段 skill（blueprint / spec / script）
  - Gate 3 → short-drama-storyboard
  - **Gate 3.5 → 实体层问题（图缺失/不达标/hash 不符/未锁定）回 short-drama-asset-forge；声明层问题（schema 非法/引用不闭合/漏声明）回 short-drama-storyboard**
  - Gate 4 → short-drama-video-forge / short-drama-audio-forge
- 修复要求:{}
- 引用总纲 §六.1 硬阻断规则:修复后必须重跑本 Gate,Gate PASS 前不允许进入下一阶段。

## 软问题 / 无法校验清单
- {}

## （仅 Gate 3.5）豁免签字核对
- 已签字放行的 degraded 资产:{资产 id / 版本 / 签字人 / 时间}（须同步进最终 BUILD_REPORT 的遗留问题清单）
- 未签字但降级的资产:{列表 → 按 ERROR 阻断}
