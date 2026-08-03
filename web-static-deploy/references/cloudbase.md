# 腾讯云 CloudBase / COS 部署参考

适用于：面向国内玩家、免 ICP 备案（默认域名）、用户有腾讯云账号。

## 前置条件（必须由用户持有）
- 腾讯云账号 + **SecretId / SecretKey**（访问管理 CAM 中创建，建议只授予 CloudBase 权限）。
- 一个 CloudBase 环境（开通"静态网站托管" + 可选"文档数据库" + "云函数"）。
- 或仅用 COS 桶（对象存储）→ 开启静态网站托管。

> 代理/沙箱环境**无法**替用户登录其腾讯云账号。要么用户给密钥（用完不落盘），要么用户在
> 控制台手动上传。CloudStudio 沙箱（见主 SKILL.md Step 2）是另一条零配置、代理可直接跑的路线。

## 方法 A：CloudBase 静态网站（推荐，自带 DB/鉴权/云函数）

1. 控制台创建环境（按量计费或免费额度），记下 `envId`。
2. 本地安装 CLI：`npm i -g @cloudbase/cli`（或用 `tcb`）。
3. 登录：`tcb login`（浏览器授权）或用密钥：
   `tcb env:login --secretId <ID> --secretKey <KEY>`。
4. 部署静态文件：
   ```bash
   tcb hosting deploy dist -e <envId>
   ```
5. 控制台"静态网站托管"会给出一个 `xxx.tcloudbase.com` 默认域名（国内可达、免备案）。
6. 如需自定义域名：控制台绑定 `fish.example.com`，再去 DNS 加 CNAME 指向该默认域名，开启 HTTPS。

## 方法 B：COS 桶 + 静态网站托管

1. 对象存储 COS → 建桶（名称全局唯一，如 `godfish-125xxxxxxx`）→ 开启"静态网站托管"，
   索引文档 `index.html`。
2. 上传 `dist/` 到桶根（控制台拖拽，或 CLI）：
   ```bash
   # coscli（需配置密钥）
   coscli cp dist/ cos://godfish-125xxxxxxx/ -r
   ```
3. 默认访问域名：`godfish-125xxxxxxx.cos-website.ap-guangzhou.myqcloud.com`（地区按桶所在选）。
   默认域名免备案；若要绑自定义域名才需 ICP。

## 自定义域名共用步骤
- DNS 加 CNAME：`fish` → `xxx.tcloudbase.com` 或 `*.cos-website.*.myqcloud.com`。
- 等传播后开启 HTTPS（CloudBase/COS 控制台申请免费证书）。

## 带数据库（NEEDS A DATABASE 分类时）
CloudBase 一步到位：
- **鉴权**：`tcb` 提供匿名/微信登录，拿 `uid`。
- **文档 DB**：用 `@cloudbase/js-sdk` 把 `localStorage` 的存档读写迁到 `cloud.database()`
  集合（建议本地缓存 + 云端同步 + 冲突合并）。
- **云函数**：抽卡/商城/月卡等经济逻辑放云函数校验，防前端伪造。
这是架构改造，单独排期，不在"部署"步骤内完成。
