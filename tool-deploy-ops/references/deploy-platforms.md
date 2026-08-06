# 各平台部署命令与配置模板

本文件给出 `tool-deploy-ops` 支持的五个平台(github-pages / vercel / netlify / cloudbase / cos)
的部署命令与配置模板。**详细的平台背景、认证流程、域名配置、静默 404 排查等内容不在此重复**,
一律引用 `web-static-deploy` skill 已有的 references,保持单一事实来源。

> 引用基准路径:本文件位于 `tool-deploy-ops/references/`,web-static-deploy 位于同级目录,
> 因此引用路径统一写作 `../../web-static-deploy/references/<文件>` 与 `../../web-static-deploy/SKILL.md`。

---

## 1. github-pages

**部署命令**(本 skill 直接 CLI 发布到 `gh-pages` 分支):

```bash
# 直接把 dist/ 发布到 gh-pages 分支(走 npx,无需全局安装)
npx gh-pages -d dist
```

- `--target` 语义:形如 `user/repo`,用于本 skill 推断部署后 URL `https://user.github.io/repo/`。
- CLI 工具检测:`npx`(随 Node 安装)。

**回滚命令**:`git revert HEAD --no-edit`(随后 `git push` 触发 CI 重部署)。

**详细参考**(工作流 YAML、Pages Source="GitHub Actions" 陷阱、TXT/CNAME 域名步骤、API 验证命令、
推送认证)见:

- `../../web-static-deploy/references/github-pages.md`

> ⚠️ web-static-deploy 推荐 GitHub Actions(CI)而非直接 push `gh-pages` 分支。本 skill 的 `npx gh-pages`
> 是"直接 CLI 部署"路线;若仓库已配置 Actions 工作流,部署动作应改为 `git push origin main` 让 CI 构建,
> 详见上述引用文件的"工作流文件"小节。

---

## 2. vercel

**部署命令**:

```bash
# --prod 发布到生产;--yes 跳过交互确认;--name 指定项目名
vercel deploy dist --prod --yes --name <project>
```

- `--target` 语义:项目名(`--name`)。
- CLI 工具检测:`vercel`(需 `vercel login` 已登录)。
- 部署成功后 CLI stdout 会含 `https://<hash>.vercel.app`,本 skill 据此自动健康检查。

**回滚命令**:`vercel rollback <deployment-id>`(`--target` 作为 deployment id)。

**配置模板**:`vercel.json`(可选,覆盖默认行为):

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": null
}
```

**详细参考**(平台选型、私有仓库支持、自定义域名绑定)见 web-static-deploy 主文档的 Step 2 / Step 3:

- `../../web-static-deploy/SKILL.md`

---

## 3. netlify

**部署命令**:

```bash
# --prod 发布到生产;--dir 指定产物目录;--site 指定站点
netlify deploy --prod --dir=dist --site <site-id>
```

- `--target` 语义:站点 id / 名称(`--site`)。
- CLI 工具检测:`netlify`(需 `netlify login` 已登录)。
- 部署成功后 CLI stdout 会含 `https://<hash>.netlify.app`,本 skill 据此自动健康检查。

**回滚命令**:Netlify 无直接 CLI 回滚子命令,本 skill 走降级路径,输出手动指令:

```bash
# 用 Netlify API 回滚到指定 deploy(需 site-id 与 deploy-id)
netlify api restoreSiteDeploy --data '{"site_id":"<site-id>","deploy_id":"<deploy-id>"}'
```

**配置模板**:`netlify.toml`(可选):

```toml
[build]
  command = "npm run build"
  publish = "dist"
```

**详细参考**(平台选型、自定义域名)见 web-static-deploy 主文档 Step 2 / Step 3:

- `../../web-static-deploy/SKILL.md`

---

## 4. cloudbase(腾讯云 CloudBase 静态网站托管)

**部署命令**:

```bash
# target 为 CloudBase envId
tcb hosting deploy dist -e <envId>
```

- `--target` 语义:CloudBase 环境 id(`envId`)。
- CLI 工具检测:`tcb`(需 `tcb login` 或 `tcb env:login --secretId/--secretKey` 已登录)。
- 默认域名:`xxx.tcloudbase.com`(国内可达、免 ICP 备案)。本 skill 不自动推断该域名,需另跑 healthcheck。

**回滚命令**:CloudBase 无直接 CLI 回滚,本 skill 走降级路径(重新部署上一版本产物)。

**详细参考**(CloudBase 环境创建、SecretId/SecretKey 作用域、自定义域名 CNAME、带数据库架构改造)见:

- `../../web-static-deploy/references/cloudbase.md`

---

## 5. cos(腾讯云 COS 桶 + 静态网站托管)

**部署命令**:

```bash
# target 为 COS 桶名(全局唯一)
coscli cp dist cos://<bucket>/ -r
```

- `--target` 语义:COS 桶名。
- CLI 工具检测:`coscli`(需配置密钥)。
- 默认域名:`<bucket>.cos-website.ap-<region>.myqcloud.com`(地区按桶所在选)。本 skill 不自动推断,需另跑 healthcheck。

**回滚命令**:COS 默认无版本回滚,本 skill 走降级路径(重新上传上一版本产物)。

**详细参考**(COS 桶创建、静态网站托管开启、coscli 配置、自定义域名)见:

- `../../web-static-deploy/references/cloudbase.md`(COS 与 CloudBase 共用同一参考文件的"方法 B"小节)

---

## 引用一览(单一事实来源)

| 平台 | 引用路径 | 内容 |
|------|---------|------|
| github-pages | `../../web-static-deploy/references/github-pages.md` | 工作流 YAML、Source 陷阱、域名、API 验证 |
| vercel | `../../web-static-deploy/SKILL.md` (Step 2/3) | 选型、私有仓库、自定义域名 |
| netlify | `../../web-static-deploy/SKILL.md` (Step 2/3) | 选型、自定义域名 |
| cloudbase | `../../web-static-deploy/references/cloudbase.md` | 环境创建、密钥作用域、域名、带 DB |
| cos | `../../web-static-deploy/references/cloudbase.md` (方法 B) | 桶创建、静态网站托管、coscli |
| postbuild | `../../web-static-deploy/references/postbuild-snippet.md` | 生成 `dist/.nojekyll` 与 `dist/CNAME` 的 postbuild 片段 |

> 维护原则:平台命令或配置若有变更,优先更新 `web-static-deploy/references/` 中的源文件,
> 本文件只同步"本 skill 使用的命令片段与 target 语义",避免内容重复导致漂移。
