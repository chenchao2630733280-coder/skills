# 角色一致性控制(使用锁定资产)

> 本文件对应 short-drama-video-forge SKILL.md §五,生成角色镜头与一致性检查时读取。
> **前提**:角色形象已在阶段 4.5 定妆锁定。本阶段只"消费"资产,不"决定"资产 —— 没有换参考图的权限。

---

## 1. 三件套(所有角色镜头强制,取自 ASSET_MANIFEST.json)

1. **参考图**:`assets/char/{charId}/{variantId}.png`(锁定定妆图,按变体路由)
2. **固定 seed**:该**变体**的 seed(同角色各变体 seed 互异;**不是**同角色全剧同 seed)
3. **风格关键词 + 负面词**:角色 `styleKeywords` × 风格基线 `negativeKeywords`

> 取数来源是 `docs/ASSET_MANIFEST.json`,不是 VISUAL_SPEC(人读版)也不是 manifest 的副本。三件套里的每一项都可追溯到清册中的 (id, variant, assetVersion, hash)。

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

漂移判定后:用**同一把锁定参考图 + 同一 seed** 重生成 ≤2 次;仍漂移 → `degradeType:"character-drift"`。

**单镜头漂移 vs 系统性漂移(关键分流)**:

| 现象 | 判断 | 处理 |
|---|---|---|
| 个别镜头不像 | 生成波动 | 本阶段重试 ≤2 次;仍不行标 degraded(单镜头瑕疵可接受) |
| 同一资产多镜头持续不像 | **定妆图本身不好用** | **不得**逐镜头硬凑、**不得**换参考图;**报错并回阶段 4.5 走资产变更流程**(影响面报告 + 用户决策 → assetVersion+1 → 受影响镜头重跑) |

> 这条分流是资产层的核心价值:把"越修越乱"的逐镜头微调,收敛成一次可评估成本的资产变更。

---

## 5. 同角色多情绪

- 改动作/表情/光线描述,**不改**服装/发型/seed/参考图
- 情绪关键词加在 prompt 尾部,避免影响主体外观
- **跨集形象变化必须走变体**(如回忆线用 `student` 变体),不允许在同一变体里临时改服装描述

---

## 6. 变体路由速查

| STORYBOARD 写法 | manifest 字段 | 取的参考图 | 取的 seed |
|---|---|---|---|
| `linwan` | `charVariants` 缺省 | `assets/char/linwan/default.png` | default 的 seed |
| `linwan(student)` | `{"linwan":"student"}` | `assets/char/linwan/student.png` | student 的 seed |

**禁止**:用 default 的参考图渲染非 default 变体(会把回忆线画成现在时)。

---

## 7. 记录

- 漂移镜头 id 记入 docs/ASSET_ISSUES.md
- 每镜头落盘后写 `assetSnapshot`(所用资产的 assetVersion + hash),保证成片可追溯到具体定妆图版本
- 资产本身变更(换图/调风格/改音色)**不在本阶段执行** —— 走阶段 4.5 §五变更流程,变更记录写在 `docs/ASSET_BASELINE.md` 与 `docs/ASSET_IMPACT.md`
