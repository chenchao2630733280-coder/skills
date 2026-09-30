# 短剧项目模板（Short Drama Project Template）

本目录是 `short-drama-forge-master` 的**项目模板骨架**：把整个目录复制到新短剧项目根目录，即可获得与流水线固定路径契约完全一致的初始结构，再按流水线逐阶段填写/生成产物。

## 使用步骤（模板模式）

1. **复制骨架**：把 `templates/project/` 整个目录复制为项目根目录（如 `{你的项目名}/`）。
2. **填写蓝图**：按 `docs/SHORT_DRAMA_BLUEPRINT.template.md` 填写项目参数（剧名/类型/集数/工具链/资产规模/裁剪），并改名为 `docs/SHORT_DRAMA_BLUEPRINT.md`。
3. **走流水线**：从 `short-drama-forge-master` 总纲启动（或从 `short-drama-blueprint` 阶段 1 开始），后续阶段按固定路径覆盖/新增产物：
   - 阶段 2 → `docs/STORY_SPEC.md` + `docs/EPISODE_OUTLINE.md`
   - 阶段 3 → `docs/scripts/EP{01..NN}.md`（参考 `docs/scripts/EP01.example.md`）
   - 阶段 4 → `docs/STORYBOARD.md` + `docs/VISUAL_SPEC.md` + `docs/ASSET_MANIFEST.json`
   - **阶段 4.5（资产定妆）→ `assets/**` + `docs/ASSET_BASELINE.md`（+ 回写 ASSET_MANIFEST.json）**
   - 阶段 5 → `production/manifest.json` + `shots/{ep}/shot_{XX}.mp4`
   - 阶段 6 → `audio/{ep}/line_{XX}.mp3` + `audio/bgm_*.mp3` + `docs/AUDIO_SPEC.md` + `subtitles/{ep}.srt`
   - 阶段 7 → `episodes/EP{XX}.mp4` + `docs/BUILD_REPORT.md`
   - 质量门 → `docs/GATE_{0..4}_REPORT.md` + `docs/GATE_3.5_REPORT.md`

## 目录结构

```
{项目根}/
├── README.md                        # 本文件（项目说明，可改写）
├── docs/
│   ├── SHORT_DRAMA_BLUEPRINT.template.md   # 阶段1 蓝图模板
│   ├── STORY_SPEC.template.md              # 阶段2 故事规格模板
│   ├── EPISODE_OUTLINE.template.md         # 阶段2 分集大纲模板
│   ├── STORYBOARD.template.md              # 阶段4 分镜模板(12 必填 + 1 可选字段)
│   ├── VISUAL_SPEC.template.md             # 阶段4 视觉规范模板(角色母卡+变体子表/场景/道具/风格/字幕)
│   ├── ASSET_MANIFEST.template.json        # 阶段4 资产需求清册模板(阶段4.5 回写锁定)
│   ├── ASSET_BASELINE.template.md          # 阶段4.5 资产基线锁定表模板
│   ├── AUDIO_SPEC.template.md              # 阶段6 音频规格模板
│   ├── GATE_0_REPORT.template.md           # 质量门报告模板(0~4 + 3.5 通用)
│   ├── BUILD_REPORT.template.md            # 阶段7 验收报告模板
│   └── scripts/
│       └── EP01.example.md                 # 单集剧本示例(阶段3)
├── assets/                                 # 阶段4.5 资产基线（空，由 4.5 写入）
│   ├── char/{charId}/{variantId}.png       # 角色定妆图（含变体）
│   ├── scene/{sceneId}.png                 # 场景定稿图
│   ├── prop/{propId}.png                   # 剧情道具定稿图
│   ├── voice/{charId}.mp3                  # 音色试音
│   └── style/baseline.json                 # 风格基线卡（locked token）
├── production/
│   └── manifest.example.json               # 生产清单示例(阶段5 产物格式，只引用资产)
├── shots/                                  # 阶段5 镜头视频/占位图(空)
├── audio/                                  # 阶段6 配音/BGM(空)
├── subtitles/                              # 阶段6 字幕 srt(空)
└── episodes/                               # 阶段7 成片(空)
```

## 命名与路径契约

- 模板文件名带 `.template.md` / `.template.json` 后缀，**复制后使用前必须去掉后缀**，变为流水线固定路径文件名。
- `ASSET_MANIFEST.template.json` 是纯 JSON，**无法写注释**；填写时按字段占位符（`{剧名}` / `{ISO8601}` 等）替换，字段含义见 `short-drama-asset-forge/references/asset-manifest-schema.md`。多余的说明性字段会被 Gate 3.5.1 判为 schema 非法。
- 空目录（`assets/` `shots/` `audio/` `subtitles/` `episodes/`）由各阶段 skill 写入产物时自动创建，模板中仅作结构占位（含 `.gitkeep`）。
- **不要手工往 `assets/` 丢图**：未经阶段 4.5 定妆确认与 hash 登记的图，会在 Gate 3.5 被判为未锁定/无登记而硬阻断。
- 禁止自定义产物路径，全部按 `short-drama-forge-master/SKILL.md` §八 固定路径表。

## 资产层速查（本模板新增的核心概念）

```
阶段 4 分镜 ──声明──→ docs/ASSET_MANIFEST.json    要哪些资产（status=declared）
阶段 4.5 定妆 ─实产─→ assets/**                    资产长什么样
              └确认→ 人工确认点 4.5                用户选定才 lock
Gate 3.5 资产门 ─校验→ 文件存在 + 已锁定 + hash 一致 不通过不许批量生产
阶段 5 生产 ─引用─→ production/manifest.json       只写 id+variant+hash
阶段 7 出现 ─→ docs/BUILD_REPORT.md                 遗留降级资产清单
```

**单一真源**：资产定义只在 `docs/ASSET_MANIFEST.json`；`production/manifest.json` 只准引用（Gate 4.9 阻断定义副本）。
