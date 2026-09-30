# {剧名} - 资产基线锁定表（模板）

> 使用说明：复制为 `docs/ASSET_BASELINE.md` 后填写，去掉本说明。由阶段 4.5 short-drama-asset-forge 产出，是"这一集用的是哪版定妆图"的唯一追溯依据。每次资产变更追加一行，不覆盖历史。

## 一、锁定汇总

- 锁定时间：{ISO8601}
- 定妆确认人：{用户}
- 工具链：文生图 {即梦} / TTS {火山引擎} / 风格卡 {assets/style/baseline.json}
- 统计：角色 {N}（变体 {M}）/ 场景 {S}（其中 oneOff {K}）/ 道具 {P} / 音色 {V} / 降级 {D}

## 二、锁定表

### 角色定妆

| 角色 id | 角色名 | 变体 | 版本 | 文件路径 | seed | hash | 状态 | 引用集数 | 锁定时间 |
|---|---|---|---|---|---|---|---|---|---|
| linwan | 林晚 | default | v1 | assets/char/linwan/default.png | 20241 | {a1b2c3d4e5f6} | locked | EP01,EP02,EP11 | {ISO8601} |
| linwan | 林晚 | student | v1 | assets/char/linwan/student.png | 20242 | {b2c3d4e5f6a1} | locked | EP07 | {ISO8601} |
| chenmo | 陈默 | default | v1 | assets/char/chenmo/default.png | 20251 | {c1d2e3f4a5b6} | locked | EP01,EP03 | {ISO8601} |

### 场景定稿

| 场景 id | 场景名 | 版本 | 文件路径 | seed | hash | oneOff | 状态 |
|---|---|---|---|---|---|---|---|
| rainy_alley | 雨夜巷口 | v1 | assets/scene/rainy_alley.png | 30011 | {c3d4e5f6a1b2} | 否 | locked |
| rooftop_night | 天台夜 | — | —（一次性场景，免定妆） | — | — | 是 | skipped |

### 道具定稿

| 道具 id | 名称 | 剧情作用 | 首暗示集 | 版本 | 文件路径 | seed | hash | 状态 |
|---|---|---|---|---|---|---|---|---|
| prop_watch | 旧怀表 | 终极真相线索 | EP03 | v1 | assets/prop/prop_watch.png | 41002 | {d4e5f6a1b2c3} | locked |

### 音色资产

| voice id | 角色 | 音色描述 | TTS 音色名 | 基准语速 | 试音样本 | hash | 状态 |
|---|---|---|---|---|---|---|---|
| voice_linwan | 林晚 | 低沉磁性女声，略带沙哑 | zh-CN-XiaoxiaoNeural | 1.0 | assets/voice/linwan.mp3 | {f6a1b2c3d4e5} | locked |

### 风格基线

| 基线 id | 关键词 | 负面词 | 色彩倾向 | 版本 | hash | 状态 |
|---|---|---|---|---|---|---|
| style_main | 都市悬疑/冷色调/电影感 | 低质量/变形/多余手指/文字水印 | 冷蓝+霓虹点缀 | v1 | {e5f6a1b2c3d4} | locked |

## 三、变更记录（追加，不覆盖）

| 时间 | 资产 | 版本 | 变更原因 | 旧 hash → 新 hash | 影响镜头数 | 用户决策 | 执行结果 |
|---|---|---|---|---|---|---|---|
| {ISO8601} | char:linwan@default | v1→v2 | 脸型更贴合原著 | {旧} → {新} | 412（已生产 120） | 方案 A 全量重生成 | 120 镜头重跑完成 |

> 变更走 short-drama-asset-forge §五流程，影响面报告见 `docs/ASSET_IMPACT.md`。

## 四、已知风险签字

| 资产清单 | 风险描述 | 后果说明 | 签字人 | 时间 |
|---|---|---|---|---|
| —（无） | — | — | — | — |

> 只有在此栏列明并签字的 degraded 资产，Gate 3.5 才把对应 ERROR 降为 WARNING。签字不改变 `status=degraded`。

## 五、基线一致性自检

- [ ] 本表锁定行数 = `docs/ASSET_MANIFEST.json` 中 `status=locked` 的资产数
- [ ] 表中 hash 与清册逐条相等
- [ ] 同角色各变体 seed 互异
- [ ] 变体的引用集数与 STORYBOARD 实际引用一致
- [ ] 所有降级项已写入 `docs/ASSET_ISSUES.md`
