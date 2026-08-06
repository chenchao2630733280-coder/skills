# 数值平衡校验(关键踩坑)

> 本文件从 game-code-forge SKILL.md 抽离,作为跨引擎通用(跑酷类)数值配置的踩坑规范。生成跑酷类游戏数值配置时按需读取。

## 十三、数值平衡校验(关键踩坑)

### 13.1 问题背景

PRD §2.3 给出了跳跃/移动/障碍的物理平衡推导,但代码生成时容易:
- 漏抄 PRD 数值,直接拍脑袋写默认值
- 只填 GameConfig 字段,不做可玩性校验
- 没有把推导注释写进 GameConfig,后人调参无从下手

**PoC 踩坑**:gravityY=1200/jumpVelocity=-700/speed=300/interval=800ms 时,滞空期障碍移动 350px > 间距 240px,Hero 永远跳不过去。

### 13.2 强制规则

生成 GameConfig.ts 时:
1. **必须**从 PRD §2.3 读取推导表,直接抄入 GameConfig 字段值
2. **必须**在 GameConfig 顶部写推导注释块(公式 + 每档 D/M/R 余量)
3. **必须**自检四条可玩性约束(见 13.3),任一不满足 → 停止生成,回到 PRD §2.3 修正数值

### 13.3 可玩性约束(硬性,全部满足才可玩)

| 约束 | 公式 | 不满足处理 |
|---|---|---|
| 跳得过去 | `H > obstacle.height + 20` | 调大 jumpVelocity 或减小 gravityY |
| 落得下地 | `D > M` | 增大 interval 或减小 speed |
| 反应得及 | `R = D - M ≥ 100px` | 增大 interval |
| **穿越时间够**(关键!) | `T_above > T_cross + 0.3s` | 降低 obstacle.height / 减小 bodyW+obstacleW / 增大 jumpVelocity |

其中:
```
T = 2 * |jumpVelocity| / gravityY           (滞空时间)
H = jumpVelocity² / (2 * gravityY)          (跳跃高度)
D = speed * interval / 1000                  (障碍间距, interval 单位 ms)
M = speed * T                                (滞空期障碍移动距离)
T_above = 2 * sqrt(2*(H - obstacle.height) / gravityY)   (body高于障碍顶的持续时间)
T_cross = (bodyW + obstacleW) / speed        (障碍穿过body水平范围的时间)
```

**第 4 条是最容易漏的坑**(PoC 踩过):即使最高点能越过,但 body 在障碍上方的时间太短,
障碍还没穿过 body 水平范围 Hero 就降落了 → overlap → game over。
表现:玩家感觉"明明跳过去了但还是撞了"。

### 13.4 GameConfig 注释模板(必须照抄)

```typescript
// 全局游戏配置常量(对应 PRD 数值设计表)
//
// 数值平衡推导(关键 - 含穿越时间校验):
//   跳跃滞空时间   T = 2 * |jumpVelocity| / gravityY
//   跳跃最大高度   H = jumpVelocity² / (2 * gravityY)
//   障碍间距       D = speed * interval / 1000
//   滞空期移动距离 M = speed * T
//   body高于障碍顶持续时间 T_above = 2 * sqrt(2*(H - obstacle.height) / gravityY)
//   障碍穿过body水平范围时间 T_cross = (bodyW + obstacleW) / speed
//
// 可玩性约束(硬性,全部满足才可玩):
//   1. 跳得过去: H > obstacle.height + 20
//   2. 间距够宽: D > M + 100px (反应余量)
//   3. 时间够长: T_above > T_cross + 0.3s (穿越余量,关键!)
//
// 当前数值:
//   T = ...   H = ...   T_above = ...
//   档1: D=..., M=..., 反应余量=... ✓  T_cross=..., 穿越余量=... ✓
//   档2: ...
//   档3: ...

export const GameConfig = { ... } as const;
```

### 13.5 校验失败时的处理

若 PRD §2.3 的推导表本身就不满足约束(常见:PRD 阶段没算清楚):
1. 不要硬抄错误数值到 GameConfig
2. 在 GameConfig 顶部注释标注 `// ⚠️ 数值不可玩,详见 ASSET_ISSUES.md`
3. 在 ASSET_ISSUES.md 追加:
   ```
   ## 数值平衡问题
   - 档 X: 约束 N 不满足
     D=... M=..., R=...(反应余量不足/或 T_above=... T_cross=..., 穿越余量不足)
     建议: [具体调参方向]
   ```
4. 提示用户回到 game-spec 修正 PRD §2.3

**穿越时间不足的调参优先级**(PoC 经验):
1. 降低 obstacle.height → 增大 T_above(最有效)
2. 减小 bodyW + obstacleW → 减小 T_cross
3. 增大 jumpVelocity / 减小 gravityY → 增大 H → 增大 T_above

### 13.6 适用范围

- 跑酷/无尽奔跑(本 PoC 类型)
- 平台跳跃(超级马里奥式)
- 飞行躲避(Flappy Bird 式,把跳跃换成拍动)
- 任何含"移动障碍 + 角色位移"的游戏

**不适用**:
- 纯解谜(无实时移动)
- 回合制(无物理曲线)
- 三消/消除(无角色位移)

---

### 13.7 行为仿真验证（进阶：通用所有玩法）

纯公式推导（13.3）适合"移动障碍 + 角色位移"类。但**任何含 AI / 交互逻辑**的游戏（追逃、伪装、对战），仅靠静态公式无法验证"机制是否真的工作"。需把核心逻辑抽成**纯函数**，用 Node 跑真实场景仿真。

**方法（来自《变色龙乐园》实战，已验证有效）**：
1. 把待验证逻辑抽离成无 Phaser 依赖的纯函数/纯类（如 `CatAI` 的 `update(dt, playerPos)`、`DisguiseSystem.compute()`）。
2. 用 `esbuild` 打包成单文件 Node 脚本（`esbuild sim.ts --bundle --platform=node --outfile=sim.cjs`）。
3. 写一个 repro 场景，喂入"修复前 / 修复后"两种实现，跑同一段假输入，打印关键指标对比。

**实战证据（变色龙乐园）**：
| 验证项 | 修复前 | 修复后 |
|---|---|---|
| 猫贴身抓捕耗时（玩家静止贴脸） | 8s 不抓（抖） | 0.73s 即抓 ✓ |
| 吸色匹配分（绑定正确物体） | 0.18 | 1.0 ✓ |

**为什么有效**：仿真能**量化**"玩家感知的 bug"（点了没反应、吸色不对），比肉眼真机测试可复现、可回归。每次调参后跑一遍，防回归。

**适用**：追逃 / 潜行 / 伪装 / 对战 / Boss 战等任何"AI 或交互逻辑影响胜负"的游戏。
**不适用**：纯视觉 / 无逻辑的数值（用 13.3 公式即可）。
