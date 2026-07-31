# Phaser 中文文字换行(关键踩坑)

> 本文件从 game-code-forge SKILL.md 抽离,作为 Phaser 含中文文字渲染的踩坑规范。生成 Phaser 中文文字时按需读取。

## 十四、Phaser 中文文字换行(关键踩坑)

### 14.1 问题背景

Phaser 的 `wordWrap` 配置默认按**空格分词**,中文文本无空格不会换行,导致:
- 对话框内长句不换行,文字溢出对话框边界
- 卡片描述文字超出卡片范围
- 这在纯英文游戏中不会暴露,但中文游戏是**必现问题**

### 14.2 反例(禁止)

```typescript
// 反例:wordWrap 不带 useAdvancedWrap,中文不换行
this.add.text(0, 0, '这是一段很长的中文描述文字...', {
  fontSize: '22px',
  wordWrap: { width: 440 },  // ← 中文不会在此换行!
});
```

### 14.3 正例(必须)

```typescript
// 正例:加 useAdvancedWrap: true 启用字符级换行
this.add.text(0, 0, '这是一段很长的中文描述文字...', {
  fontSize: '22px',
  wordWrap: { width: 440, useAdvancedWrap: true },  // ← 中文会按字符换行
});
```

### 14.4 强制规则

**所有**含 `wordWrap` 的 text 配置**必须**加 `useAdvancedWrap: true`。

常见位置(逐一检查):
- 对话框/打字机组件(Typewriter)
- 卡片描述文字(各类卡片组件)
- 弹窗提示文字
- 剧情叙述文字
- 任何可能出现中文长文本的 Text 对象

### 14.5 适用范围

- 所有 Phaser 3.x 版本
- 所有含中文/日文/韩文(无空格分词语言)的文本
- 纯英文文本不受影响(加 useAdvancedWrap 也无副作用)
