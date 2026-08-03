# postbuild 片段：自动写 dist/.nojekyll 与 dist/CNAME

GitHub Pages 用 Jekyll 二次处理站点，会忽略 `_` 开头的文件（Vite 产物常含此类文件名），
并会在重新部署时清空自定义域名设置。在 `package.json` 的 build 脚本后挂一个 postbuild 修复：

```js
// scripts/postbuild.mjs
import { writeFileSync, resolve } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// 1) 防 Jekyll 处理 Vite 产物
writeFileSync(resolve(root, 'dist', '.nojekyll'), '');

// 2) 持久化自定义域名（无自定义域名时把这一行删掉或置空）
writeFileSync(resolve(root, 'dist', 'CNAME'), 'fish.example.com');

console.log('[postbuild] 已写入 dist/.nojekyll 与 dist/CNAME');
```

`package.json`：
```json
{
  "scripts": {
    "build": "vite build && node scripts/postbuild.mjs"
  }
}
```

注意：CloudBase / Vercel / Netlify 不需要 `.nojekyll` 和 `CNAME`，仅 GitHub Pages 需要。
若同一份构建要跨平台，可让 postbuild 仅在 CI 环境变量（如 `GITHUB_PAGES=1`）存在时写这两个文件。
