# 数值可玩性实测 —— 采集脚本与字段含义

> 本文件从 game-integrate SKILL.md §10.2 抽离。做"代码跑起来了但玩不了"的判定时读取本文件。
> 背景:PRD §2.3 与 GameConfig 注释都声明了数值可玩,但实际会出现 Hero 跳不过障碍、
> 障碍不生成、collider 未生效。这三类问题 typecheck 全绿、截图也"有画面",只能靠状态采集抓。

## 1. 采集脚本(Phaser 3)

在浏览器自测中,用 `browser_evaluate` 连续采集 8 帧(约 1 秒),每帧返回:

```js
(() => {
  const game = window.game;
  const scene = game?.scene?.keys?.['Game'] || game?.scene?.getScene('Game');
  const hero = scene?.hero, body = hero?.body;
  return {
    heroY: Math.round(hero?.y),
    bodyBottom: Math.round(body?.y + (body?.height || 0)),
    blockedDown: body?.blocked?.down,
    velocityY: Math.round(body?.velocity?.y),
    obstacles: scene?.obstacles?.length,
  };
})()
```

连续采 8 次而不是 1 次,是因为**单帧看不出一条稳定态**:下坠中的 Hero 也可能恰好
`velocityY == 0`(抛物线顶点),只有连续多帧 `heroY` 不变才证明站住了。

## 2. 字段含义与它能抓住的 bug

| 字段 | 含义 | 抓什么 bug |
|---|---|---|
| `heroY` | Hero 世界坐标 y | 逐帧不变 = 站住了;单调增大 = 在穿透下坠 |
| `bodyBottom` | 物理体底边(不是精灵底边) | 与 `heroY` 差值恒定偏离预期 → Sprite/Body 偏移没设对 |
| `blockedDown` | 物理体下侧是否被阻挡 | `false` 而画面看着"在地上" → collider 没生效,靠贴图假装 |
| `velocityY` | 竖直速度 | 站地时应为 0;恒非 0 → 重力/阻尼在持续作用 |
| `obstacles` | 障碍对象数量 | `0` → 生成逻辑没跑(通常是被引导层或暂停态吞掉了 tick) |

## 3. 判定标准

- `blockedDown === true` 且 `velocityY === 0` 且 8 帧 `heroY` 一致 → 物理正常
- `obstacles >= 1` → 生成逻辑正常
- Hero 在障碍到达前能跳过去(手动 pointerdown 或比对跳跃最高点 H 与障碍高度)

## 4. 兜底:采集不到时先怀疑"没暴露",不是"没问题"

1. `window.game` 为 undefined → 引擎实例没挂到 window。在入口处补 `window.game = game`
   (仅 dev 构建),**不要**改成"看截图判断"。
2. `scene.hero` 为 undefined → 命名不一致。先打印 `Object.keys(scene)` 确认真实字段名,
   再把脚本改成实际命名,而不是把 `?.` 链一路吃空返回 `undefined` ——
   全 undefined 的采集结果**看起来像是"没有异常"**,这是静默假绿。
3. 采集结果里所有字段都是 `undefined` → 立即判 FAIL 并回到第 1/2 条,不许当通过。

## 5. 失败处理路径

| 现象 | 回到哪 |
|---|---|
| Hero 持续下坠 | game-code-forge §十四 Sprite/Body 偏移安全 |
| 障碍太密跳不过 | game-spec §2.3 调 interval / speed |
| 障碍太高跳不过 | game-spec §2.3 调 obstacle.height 或 jumpVelocity |
| 障碍数为 0 | 先查 tick 是否被暂停/引导层拦截,再查生成器初始化顺序 |
