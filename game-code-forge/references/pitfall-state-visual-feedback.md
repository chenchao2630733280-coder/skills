# 状态切换的可见反馈踩坑（通用）

> 来自《变色龙乐园》实战迭代。当游戏中存在"切换型玩法状态"（潜行 / 加速 / 变身 / 整活 / 开盾）时，仅改逻辑布尔或数值而无视觉反馈，玩家会误判为"按钮点了没反应"。生成任何含状态切换机制的游戏时默认知晓。

---

## 1. 现象

- 点击"潜行"按钮后，角色外观无任何变化，玩家以为按钮坏了。
- 点击"整活 / 跳舞 / 装死"按钮后，画面静止，玩家以为卡死。
- 切换型按钮（开 / 关）文字始终不变，玩家无法判断当前状态。

## 2. 根因

- 状态切换只改了逻辑层（如 `isSneaking = true`、`emote = 'dance'`），UI / 角色对象没有任何视觉变化。
- 在玩家认知里，"无反馈" 等价于 "无响应"。

## 3. 强制规范

任何影响玩法的状态切换，**至少**要有以下一种可见反馈：

- **视觉态**：潜行 → 角色 `alpha = 0.5` 半透明 + 按钮持续高亮（文字变 "潜行·开"）；变身 → 换贴图 / 换色。
- **动画态**：整活 / 跳舞 → tween 形变（scaleX / scaleY 拉伸旋转、摇摆旋转、压扁）；开盾 → 护盾光圈出现。
- **输入冻结提示**：整活类动作需 "冻结移动输入 + 播放动画"，避免玩家在动画期间还能移动导致画面乱跳。
- **按钮态**：切换型按钮文字 / 底色随状态变化（关 → 开），并持续高亮当前激活态。

## 4. 推荐模板

```typescript
// 潜行：半透明 + 按钮高亮（持续反映状态）
toggleSneak() {
  this.sneaking = !this.sneaking;
  this.setAlpha(this.sneaking ? 0.5 : 1);
  sneakBtn.setText(this.sneaking ? '潜行·开' : '潜行');
  sneakBtn.setStyle({ backgroundColor: this.sneaking ? '#2a6df4' : '#555555' });
}

// 整活：tween 形变 + 冻结输入（避免动画期间乱跳）
playEmote(kind: 'dance' | 'death' | 'swing') {
  this.freezeInput = true;                       // 冻结移动
  this.scene.tweens.add({
    targets: this,
    scaleY: kind === 'death' ? 0.6 : 1.3,
    scaleX: kind === 'death' ? 1.4 : 0.8,
    angle: kind === 'swing' ? 20 : 15,
    yoyo: true, repeat: 3, duration: 220,
    onComplete: () => { this.freezeInput = false; this.setScale(1).setAngle(0); }
  });
}
```

## 5. 自检清单

- [ ] 每个切换型按钮点击后，画面 / 角色有可见变化
- [ ] 按钮文字或底色反映当前状态（开 / 关）
- [ ] 动画型动作冻结输入，避免画面乱跳
- [ ] 反馈仅作用于表现层，不破坏核心数值平衡
