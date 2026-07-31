---
name: "game-spec"
description: "AI 游戏生成流水线阶段 2。读取游戏蓝图,生成详细 PRD(玩法/数值/UI/关卡/状态机)和 TECH_DESIGN(目录/模块/类设计/接口契约)。当被 game-forge-master 调度到本阶段,或用户要'生成游戏 PRD/技术设计'时调用。"
---

# Game Spec — 游戏规格设计

本 skill 是 AI 游戏生成流水线的**阶段 2**,职责是把蓝图扩展成两份详细文档:
- `docs/PRD.md`:产品需求(给美术和代码 skill 共用)
- `docs/TECH_DESIGN.md`:技术架构(给代码 skill 用)

---

## 一、输入与输出

**输入**:
- `docs/GAME_BLUEPRINT.md`(必读)

**输出**(固定路径,2 份文档):
- `docs/PRD.md`
- `docs/TECH_DESIGN.md`

---

## 二、PRD 文档模板

严格按以下结构产出:

```markdown
# {游戏名} - 产品需求文档(PRD)

## 1. 玩法详述
### 1.1 玩家操作
{输入方式 + 响应行为 + 操作禁用条件}

### 1.2 游戏循环
{开始 → 进行 → 结束 的完整状态流转}

### 1.3 胜负条件
- 胜利:{...}
- 失败:{...}
- 中止:{...}

### 1.4 难度曲线
| 阶段 | 触发条件 | 参数变化 |
|---|---|---|
| 初期 | 0-20 分 | 速度 v |
| 中期 | 20-50 分 | 速度 1.2v |
| 后期 | 50+ 分 | 速度 1.5v + 障碍密度+30% |

## 2. 数值设计
### 2.1 核心数值表
| 参数 | 默认值 | 范围 | 说明 |
|---|---|---|---|

### 2.2 概率表
{掉落/抽奖/彩蛋等概率}

### 2.3 数值平衡推导(物理可行性校验,必填)

**所有含跳跃/移动/障碍的游戏必填本节**。PRD 必须给出物理推导,证明数值可玩。
game-code-forge 会读本节生成 GameConfig,game-integrate 会按本节验收。

#### 2.3.1 公式定义

```
跳跃滞空时间   T = 2 * |jumpVelocity| / gravityY
跳跃最大高度   H = jumpVelocity² / (2 * gravityY)
障碍间距       D = speed * interval / 1000          (interval 单位 ms)
滞空期移动距离 M = speed * T
反应余量       R = D - M                              (Hero 落地到下个障碍到达的缓冲)

body 高于障碍顶的持续时间   T_above = 2 * sqrt(2*(H - obstacle.height) / gravityY)
障碍穿过 body 水平范围时间  T_cross = (bodyW + obstacleW) / speed
穿越时间余量   R_time = T_above - T_cross
```

#### 2.3.2 可玩性约束(硬性,全部满足才可玩)

| 约束 | 公式 | 不满足的后果 |
|---|---|---|
| 跳得过去 | H > 障碍高度 + 20px | 撞障碍顶 |
| 落得下地 | D > M | Hero 还在空中下个障碍就到了(必死) |
| 反应得及 | R ≥ 100px | 玩家无反应时间,挫败感强 |
| **穿越时间够**(关键!) | T_above > T_cross + 0.3s | body 还在障碍水平范围内就降落了 → 撞障碍侧 |

**第 4 条是最容易漏的坑**:即使跳跃最高点能越过障碍,但"高于障碍顶"的持续时间不够长,
障碍物还没完全穿过 Hero body 水平范围,Hero 就降落了 → overlap 碰撞 → game over。

#### 2.3.3 推导表(每档难度一行)

| 难度档 | speed | interval(ms) | D(间距) | M(滞空移动) | R(反应余量) | T_above | T_cross | R_time(穿越余量) | 可玩 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | ✓/✗ |
| 2 | | | | | | | | | ✓/✗ |
| 3 | | | | | | | | | ✓/✗ |

任一档任一约束 ✗ → 回到 2.1 调整 gravityY/jumpVelocity/speed/interval/bodyW/obstacleW,直到全部 ✓。

#### 2.3.4 反例(PoC 踩过的坑,两个版本)

**反例 1:间距太近(必死)**
```
gravityY: 1200, jumpVelocity: -700  → T=1.167s, H=204px
档1: speed=300, interval=800ms     → D=240px, M=350px
M(350) > D(240) → 滞空期下个障碍就到了,永远跳不过
```

**反例 2:穿越时间不足(理论能过但实际撞侧)**
```
gravityY: 1800, jumpVelocity: -800  → T=0.889s, H=178px
障碍高度: 100, bodyW: 80, obstacleW: 60
T_above = 2*sqrt(2*(178-100)/1800) = 0.588s
T_cross = (80+60)/280 = 0.500s
R_time = 0.588 - 0.500 = 0.088s < 0.3s ✗
→ 虽然最高点能越过,但 body 在障碍上方的时间太短,容易撞侧
```

#### 2.3.5 填写示例(PoC 最终修复后)

```
gravityY: 1500, jumpVelocity: -1000 → T=1.333s, H=333px
障碍高度: 70, bodyW: 60, obstacleW: 50
T_above = 2*sqrt(2*(333-70)/1500) = 1.185s

| 难度 | speed | interval | D    | M    | R(反应) | T_above | T_cross | R_time | 可玩 |
| 1    | 250   | 2000     | 500  | 333  | 167     | 1.185   | 0.440   | 0.745  | ✓    |
| 2    | 320   | 1800     | 576  | 427  | 149     | 1.185   | 0.344   | 0.841  | ✓    |
| 3    | 400   | 1600     | 640  | 533  | 107     | 1.185   | 0.275   | 0.910  | ✓    |
```

**调参经验**:穿越时间不足时,优先级:
1. 降低 obstacle.height(增大 T_above,最有效)
2. 减小 bodyW + obstacleW(减小 T_cross)
3. 增大 jumpVelocity / 减小 gravityY(增大 H → 增大 T_above)

## 3. 关卡/进度设计
{如有,列出关卡数据 schema}

## 4. UI 全清单
### 4.1 首页(HomeScene)
节点树:
```
Canvas
├─ bg (Sprite)
├─ title (Text)
├─ startBtn (Sprite + Button)
└─ ...
```

### 4.2 HUD(GameScene)
...

### 4.3 弹窗(每个一份)
| 弹窗名 | 触发条件 | 节点树简述 | 关闭行为 |
|---|---|---|---|

## 5. 状态机
### 5.1 场景切换图
```
Boot → Home → Game → (Result/Lottery/Revive) → Home
```

### 5.2 状态转换表
| 当前状态 | 事件 | 目标状态 | 副作用 |
|---|---|---|---|

## 6. 音效清单
| ID | 触发点 | 时长 | 风格 | 循环 |
|---|---|---|---|---|

## 7. 外部接口契约(如需)
### 7.1 {接口名}
- URL:{}
- Method:{}
- Request:{}
- Response:{}
- 错误码:{}

## 8. 边界与异常处理
| 场景 | 处理 |
|---|---|
| 网络断开 | 本地继续,缓存重发 |
| 资源加载失败 | 占位图替代 |
| ... | ... |
```

---

## 三、TECH_DESIGN 文档模板

```markdown
# {游戏名} - 技术架构设计

## 1. 引擎与依赖
- 引擎:{Phaser 3.80.x}
- 包管理:npm
- 构建:Vite
- 语言:TypeScript(strict:true)
- 依赖清单:
  - phaser ^3.80
  - axios(如需网络)

## 2. 工程目录结构
```
{项目名}/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.ts
│   ├── config/
│   ├── scenes/
│   ├── objects/
│   ├── managers/
│   ├── ui/
│   ├── net/(可选)
│   └── utils/
├── assets/
└── docs/
```

## 3. 场景划分
| 场景类 | 文件 | 职责 |
|---|---|---|

## 4. 模块清单与依赖图
```
{关键模块依赖关系 ASCII 图}
```

| 模块 | 文件 | 职责 | 依赖 |
|---|---|---|---|

## 5. 类设计
### 5.1 {ClassName}
```typescript
class Horse extends Phaser.Physics.Arcade.Sprite {
  // 属性
  // 方法签名
}
```

## 6. 配置数据结构
### 6.1 SkinConfig
```typescript
interface SkinConfig {
  id: number;
  name: string;
  animKeys: { run: string; jump: string; bling: string };
}
```

### 6.2 LevelConfig
...

## 7. 帧动画定义表
| anim_key | atlas | frames | fps | repeat | 用途 |
|---|---|---|---|---|---|

## 8. 资源加载清单
引用 docs/ASSET_MANIFEST.json 的 schema,列出场景级 preload 清单。

## 9. 状态管理与事件总线
- 事件总线:Phaser.EventEmitter
- 关键事件清单

## 10. 构建与部署
- dev: vite
- build: vite build → dist/
- 部署:静态托管 + 可选 inject-cdn
```

---

## 四、生成规则

### 1. 引擎适配
TECH_DESIGN 必须按蓝图选择的引擎写模板:
- **Phaser**:用 `Phaser.Scene`、`this.add.sprite`、`this.anims.create`、`this.physics.add.collider` 等
- **Pixi**:用 `PIXI.Application`、`PIXI.AnimatedSprite`、自建碰撞/场景管理
- **纯 Canvas**:用 `requestAnimationFrame`、自建游戏循环、自建渲染

### 2. 严格 TypeScript
TECH_DESIGN 的所有类设计必须:
- 标注返回类型
- 用 interface 定义数据结构
- 禁用 any(除非是外部 API 返回)

### 3. UI 节点树与代码对应
PRD 中每个 UI 的"节点树"必须能被 game-code-forge 直接翻译成代码:
```
Canvas
├─ bg (Sprite)           → this.add.sprite(0, 0, 'bg_home')
├─ title (Text)          → this.add.text(0, 0, '一马当先', {...})
└─ startBtn (Container)  → this.add.container(0, 0, [bg, label])
```

### 4. 资源 ID 规约
所有 PRD 中提到的资源(图/音)必须用 ID 引用,不写死路径:
- `startBtn` 引用图集 `ui-home` 的 `btn_start` 帧
- 跳跃音效引用 `audio/sfx_jump.wav`

实际路径由 game-art-spec 的 ASSET_MANIFEST.json 决定。

### 5. 数值与配置分离
所有数值(速度/概率/上限)必须抽到配置对象,不写在代码逻辑里。PRD 的"数值设计"章节直接对应代码 `config/GameConfig.ts`。

---

## 五、交互约定

1. 读取蓝图后,**不要问用户问题**,直接产出两份文档(蓝图已含决策)
2. 产出后简报:"PRD 与技术设计已生成。下一步可调用 game-art-spec 生成美术规范与资源清单"
3. 不要自行调用下游 skill

---

## 六、质量检查清单

PRD:
- [ ] 玩法循环完整(开始→进行→结束)
- [ ] 胜负条件明确
- [ ] 难度曲线有数值
- [ ] UI 节点树可被代码翻译
- [ ] 状态机覆盖所有场景切换

TECH_DESIGN:
- [ ] 引擎与蓝图一致
- [ ] 目录结构完整
- [ ] 所有类都有属性+方法签名
- [ ] 帧动画表与 PRD 玩法对应
- [ ] 接口契约(如有)字段完整
- [ ] 无 any 滥用
