# 图集帧名格式匹配(关键踩坑)

> 本文件从 game-code-forge SKILL.md 抽离,作为 Phaser 帧动画图集生成的踩坑规范。生成 Phaser 帧动画图集时按需读取。

## 十五、图集帧名格式匹配(关键踩坑)

### 15.1 问题背景

Phaser 图集 JSON 有两种格式:
- **Hash 格式**:`frames` 是对象,帧以名称为 key(如 `"swim_001": { frame: {...} }`)
- **Array 格式**:`frames` 是数组,帧以索引为序

动画注册时必须用对应的 API,否则产生 "Frame not found" 警告:
- Hash 格式 → 必须用 `generateFrameNames`(按名称查找)
- Array 格式 → 必须用 `generateFrameNumbers`(按索引查找)

### 15.2 反例(禁止)

```typescript
// 反例:Hash 格式图集用 generateFrameNumbers,帧名不匹配
// 图集 JSON 帧名是 "swim_001",但 generateFrameNumbers 按索引 0/1/2/3 查找
this.anims.create({
  key: 'char_swim',
  frames: this.anims.generateFrameNumbers('char_atlas', { start: 0, end: 3 }),
  // ← 产生 "Frame not found" 警告!
});
```

### 15.3 正例(必须)

```typescript
// 正例:Hash 格式图集用 generateFrameNames,按名称匹配
this.anims.create({
  key: 'char_swim',
  frames: this.anims.generateFrameNames('char_atlas', {
    prefix: 'swim_',
    start: 1,
    end: 4,
    zeroPad: 3,
  }),
  // ← 正确匹配 "swim_001" 到 "swim_004"
});
```

### 15.4 判断图集格式

读取图集 JSON 的 `frames` 字段:
```javascript
const atlas = JSON.parse(fs.readFileSync('assets/atlases/char_atlas.json'));
const isHash = !Array.isArray(atlas.frames);  // true = Hash 格式
```

### 15.5 强制规则

1. game-asset-forge 打包图集时,**统一用 Hash 格式**(JSON Hash),便于按名称查找
2. game-code-forge 注册动画时,**必须先判断图集格式**:
   - Hash → `generateFrameNames(prefix, start, end, zeroPad)`
   - Array → `generateFrameNumbers(start, end)`
3. 帧名命名规范:`{prefix}_{index:03d}`(如 `swim_001`),zeroPad=3

### 15.6 排查方法

浏览器运行时检查纹理帧:
```javascript
const tex = game.textures.get('char_atlas');
console.log(tex.getFrameNames());  // 查看实际帧名
console.log(tex.has('swim_001'));  // 检查帧是否存在
```
