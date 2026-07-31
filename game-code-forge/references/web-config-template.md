# Web 引擎配置文件模板

> 本文件从 game-code-forge SKILL.md 抽离,作为 Web 引擎(Phaser/Pixi/Canvas)的配置文件模板。生成工程配置时按需读取。

## 八、配置文件生成(Web 引擎部分)

### 8.1 package.json
```json
{
  "name": "{game-name}",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview"
  },
  "dependencies": {
    "phaser": "^3.80.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

### 8.2 tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "lib": ["ES2020", "DOM"]
  },
  "include": ["src"]
}
```

### 8.3 vite.config.ts
```typescript
import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  server: { port: 5173, open: true },
  build: { outDir: 'dist', assetsInlineLimit: 0 }
});
```

### 8.4 index.html
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <title>{游戏名}</title>
  <style>
    * { margin: 0; padding: 0; }
    body { background: #000; display: flex; justify-content: center; }
    #game { display: block; }
  </style>
</head>
<body>
  <div id="game"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

### 8.5 README.md
```markdown
# {游戏名}

## 开发
npm install
npm run dev

## 构建
npm run build
产物在 dist/

## 技术栈
- 引擎:{...}
- 构建:Vite
- 语言:TypeScript strict

## 文档
见 docs/ 目录
```
