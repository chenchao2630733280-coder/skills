# {剧名} - 分镜脚本（模板）

> 使用说明：复制本文件为 `docs/STORYBOARD.md` 后填写。由阶段 4 short-drama-storyboard 产出，每镜头 12 必填字段 + 1 可选字段（道具），细则见 `short-drama-storyboard/references/shot-language.md` 与 `visual-prompt-engine.md`。

## 镜头表（按集分节）

### EP{XX}（目标时长 {1-3 分钟}，镜头数 {10-25}）

| 镜头号 | 景别 | 运镜 | 时长 | 画面描述 | 角色 | 场景 | 对白/字幕 | 情绪 | 音效 | 文生图 prompt | 图生视频 prompt | 道具(可选) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EP{XX}-S{01} | 近景 | 固定 | 4s | {} | {角色id} | {场景id} | {} | 紧张 | {} | {主体+动作+环境+光线+风格+9:16+reference} | {画面主体+运动+镜头运动+时长} | {} |
| EP{XX}-S{02} | 特写 | 推 | 3s | {} | linwan(student) | {} | {} | {} | {} | {} | {} | {} |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

> 每集结尾镜头 = 卡点镜头（特写/大反差），与剧本结尾卡点对应。

## 字段写法约定

- **角色**：默认变体直接写 `linwan`；非默认变体写 `linwan(student)`（`角色id(变体id)`）；多人同框用 `+` 连接（`linwan + chenmo`）
- **场景**：写场景 id（`rainy_alley`）
- **道具**：线索类道具出现的镜头必须标 id（`prop_watch`）；无道具可留空
- **文生图 prompt 的 reference 路径**：统一写 `assets/char/{charId}/{variantId}.png`（该文件由阶段 4.5 定妆产出）
- **非 default 变体必须在 `docs/VISUAL_SPEC.md` 的变体子表中有定义**，且必须在 `docs/ASSET_MANIFEST.json` 中声明

## 镜头语言规则自检

- [ ] 单集镜头 10-25，镜头数 × 平均时长 ≈ 单集时长
- [ ] 每集至少 1 个特写/近景强化情绪
- [ ] 对话场景用正反打（过肩/单侧）
- [ ] 结尾镜头是卡点镜头
- [ ] 每个镜头有可执行的文生图 + 图生视频 prompt（无模糊词，带负面词）
- [ ] 角色/场景/变体引用与 `docs/VISUAL_SPEC.md` + `docs/ASSET_MANIFEST.json` 一致
- [ ] 角色一致性三件套（锁定参考图 + 该变体固定 seed + 风格关键词）全剧贯穿
- [ ] 变体标记（`id(variant)`）与清册 `variants[]` 一一对应，无未定义变体
