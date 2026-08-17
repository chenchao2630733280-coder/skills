# 角色一致性控制

> 本文件对应 short-drama-video-forge SKILL.md §五,生成角色镜头与一致性检查时读取。

---

## 1. 三件套(所有角色镜头强制)

1. **参考图**:VISUAL_SPEC 中角色定稿图(如 `char/linwan.png`)
2. **固定 seed**:同角色全剧同 seed(写进 manifest.characters[].seed)
3. **风格关键词**:同角色同组(写进 manifest.characters[].styleKeywords)

---

## 2. 执行流程

```
文生图:prompt 带 reference + seed + 风格关键词
  → 生成后与参考图对比(见 §4 漂移检测)
  → 合格 → 作为图生视频起始图
  → 不合格 → 重生成(≤2 次)
```

---

## 3. 多角色同框

- 主视角角色带 reference;次视角角色完整文字描述
- 提示词显式声明人物数量与位置(左/右/前后),避免融合

---

## 4. 漂移检测(每镜头质检项)

| 维度 | 方法 | 阈值 |
|---|---|---|
| 发型/服装 | 人工目检或区域颜色采样 | 主色差 >10% 判漂移 |
| 脸型/五官 | 人脸特征对比(如有模型) | 相似度 <0.6 判漂移 |
| 比例 | 主体外接框宽高比 | 与参考图差 >15% 判漂移 |

漂移判定后:重生成 ≤2 次;仍漂移 → `degradeType:"character-drift"` + 建议人工选帧作为新参考图。

---

## 5. 同角色多情绪

- 改动作/表情/光线描述,**不改**服装/发型/seed/参考图
- 情绪关键词加在 prompt 尾部,避免影响主体外观

---

## 6. 记录

- 漂移镜头 id 记入 docs/ASSET_ISSUES.md
- manifest.characters[].refImage 更新时(人工换参考图)在 ASSET_ISSUES.md 追加变更记录
