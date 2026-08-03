# GitHub Pages 部署参考

适用于：仓库可设为 public、想要免费永久 URL、push 自动更新。

## 1. 工作流文件 `.github/workflows/deploy-pages.yml`

关键点：`permissions` 必须含 `pages: write` + `id-token: write`；`deploy` job 必须有
`environment: github-pages`；用 `upload-pages-artifact` + `deploy-pages@v4`。

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

## 2. ⚠️ 最常见的静默 404（都经历过）

- **仓库是 private**：免费账号下 Pages 要求仓库 public。Settings → General → 底部
  "Change repository visibility" → Make public。私有仓库会直接显示
  "Upgrade or make this repository public to enable Pages"。
- **Pages Source 没设成 "GitHub Actions"**：Settings → Pages → Build and deployment → Source
  默认是 "Deploy from a branch"。用上面的 Actions 工作流时，必须改成 **"GitHub Actions"**。
  漏掉这步 → `deploy` job 失败（environment 无法建立）→ 站点 404，但 `build` job 全绿，
  极具迷惑性。
- **有 `github-pages` environment 保护规则**：Settings → Environments → `github-pages` 若设了
  "required reviewers"，部署会卡住等你手动批准。清空保护规则即可。

## 3. 自定义域名（verified domain）

- 先加 **TXT** 验证所有权：主机记录 `_github-pages-challenge-<user>`（注意面板是否自动补后缀，
  避免拼成双层域名），记录类型 TXT，值为 GitHub 页面显示的验证码。
- 验证通过后，GitHub → Settings → Pages → Custom domain 填域名 → Save，等几分钟勾 Enforce HTTPS。
- 再生产 `dist/CNAME` 持久化域名（见 postbuild-snippet.md），否则重部署会重置域名设置。

## 4. 部署后必须实测（不要信"我配好了"）

```bash
# 仓库可见性 / Pages 是否启用
curl -s https://api.github.com/repos/<user>/<repo> \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('visibility=',d.get('visibility'),'has_pages=',d.get('has_pages'))"

# 最近 Actions 运行（看 deploy 是否 success，build 成功不够）
curl -s "https://api.github.com/repos/<user>/<repo>/actions/runs?per_page=5" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);[print(r['id'],r['status'],r['conclusion'],r['head_branch']) for r in d.get('workflow_runs',[])]"

# 实际 HTTP 状态
curl -s -o /dev/null -w "github.io -> %{http_code}\n" https://<user>.github.io/<repo>/
curl -s -o /dev/null -w "custom -> %{http_code}\n" https://<your.domain>/
```

判读：
- `github.io` 返回 301（跳转到自定义域名）+ 自定义域 404 = 已部署但自定义域名未生效/未传播。
- `github.io` 本身 404 = 根本没部署成功（看上面 Actions 的 deploy 结论）。
- 自定义域要等 DNS 传播（几分钟~几小时，看 TTL）。

## 5. 推送认证（无凭证时）

HTTPS 推送若 401（shell 无缓存凭证、无 gh/SSH）：向用户索取带 `repo` 权限的 GitHub PAT，
用 `https://<PAT>@github.com/<user>/<repo>.git` 临时推送，推完立刻
`git remote set-url origin https://github.com/<user>/<repo>.git` 还原，token 绝不落盘。
也可让用户本地自行推送。
