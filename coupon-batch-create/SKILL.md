---
name: "coupon-batch-create"
description: 把「场次明细」Excel（剧目/演出日期/演出场地/每场票数/可用商户）批量创建为苏州卡券平台（szd-coupon.2500city.com）后台的兑换券卡券；也用于已建卡券的封面重裁、批量换封面、核验。当用户要「把 couponX 表格的卡券创建到管理后台」「批量建卡券」「补建演出票卡券」「重新裁切封面」「替换卡券封面」时使用。含封面递归匹配、智能裁切、纯 API 上传与批量提交、note 富文本补写、全量核验全流程。
agent_created: true
---

# 卡券批量创建 / 封面维护（苏州卡券平台后台）

后台：`https://szd-coupon.2500city.com/platform/student-gift-bag/coupon-manage/list`
新增页：`/coupon-manage/coupon/0?type=edit`

## 0. 准备

脚本按「当前工作目录」读写数据与 `.token`，**无需复制**——直接在工作目录调用即可：

```bash
cd <工作目录>                                   # 放 coupon1.xlsx、cover/、.token 的目录
node   <skill>/scripts/api_upload.js cover-map-smart.json cover-urls-api.json
python <skill>/scripts/build_coupons.py coupon1.xlsx coupons1.json
```

- 依赖：Python（openpyxl、Pillow）+ Node 18+（自带 fetch/FormData，无需 npm 安装）
- **首次或 token 失效**：`node login.js` → 有头浏览器打开后台，人工扫码/账密登录 → 脚本自动把 token 写入 `.token`；浏览器 profile 复用 `.browser-profile/`
- 数据文件放工作目录：`coupon1.xlsx`、`cover/<剧院>/…` 海报目录

> 所有脚本从**当前工作目录**读 `.token` / 数据文件（找不到才回退脚本目录），`build_coupons.py` 默认封面根目录为 `cover/`。

## 1. 主流程

### 路径 A：首次批量创建（Excel → 后台卡券）

```bash
python build_coupons.py coupon1.xlsx coupons1.json   # 1 Excel→JSON，输出缺封面/缺商户清单
python smart_crop.py coupons1.json cover-map-smart.json covers_smart crop-preview  # 2 智能裁切
python make_review.py cover-map-smart.json crop-preview crop-review.html           # 3 裁切预览页（人工抽查）
node api_upload.js cover-map-smart.json cover-urls-api.json   # 4 纯 API 上传封面 → fileUrl
node api_batch.js coupons1.json 0 1                            # 5 先跑 1 条验证
node api_batch.js coupons1.json                                # 6 全量创建
node fix_notes.js id-map.json                                  # 7 浏览器补写使用须知（~7s/条）
node verify3.js                                                # 8 全量核验
```

### 路径 B：只重裁 / 替换封面（已建卡券，不重建）

```bash
python build_coupons.py coupon1.xlsx coupons1.json             # 重新匹配封面（源图有增删改时必须）
rm -rf covers_smart crop-preview                               # 清空旧产物，保证全量重裁
python smart_crop.py coupons1.json cover-map-smart.json covers_smart crop-preview
python make_review.py cover-map-smart.json crop-preview crop-review.html
# 强制重传：先删掉已记录的 URL，否则 api_upload 会跳过
node -e "const fs=require('fs');const m=JSON.parse(fs.readFileSync('cover-map-smart.json','utf-8'));const u=JSON.parse(fs.readFileSync('cover-urls-api.json','utf-8'));Object.keys(m).forEach(k=>delete u[k]);fs.writeFileSync('cover-urls-api.json',JSON.stringify(u,null,2))"
node api_upload.js cover-map-smart.json cover-urls-api.json
node replace_covers.js coupons1.json                           # PUT 换封面（剔除 note，原 note 保留）
node verify3.js
```

### 路径 C：老批次 / 按 ID 定向换封面

不在 `id-map.json` 里的历史卡券（如早期手工建的 1035-1043），用 `replace_extra.js`：编辑脚本内 `TARGETS`（`[dbId, 封面相对路径]`），再 `node replace_extra.js`。

## 2. 脚本清单

| 脚本 | 作用 | 备注 |
|---|---|---|
| `login.js` | 人工登录、刷新 `.token` | 有头浏览器，profile 复用 |
| `build_coupons.py` | Excel → 卡券 JSON，封面匹配、商户映射 | 输出缺封面/缺商户清单；**递归扫描** cover 目录 |
| `smart_crop.py` | 显著性+顶部偏置智能裁切 → 180×180 | `TOP_BIAS=0.15`；同步产出红框对比图 |
| `make_review.py` | 裁切结果打包成单文件 HTML 预览页 | 图片 base64 内嵌，便于给用户抽查 |
| `api_upload.js` | 纯 API 上传封面（uploadId→upload→fileUrl） | **已记录的 URL 会跳过**，需强制重传先清 key |
| `api_batch.js` | 批量创建卡券（POST，不含 note） | 支持 `起始 条数` 试跑 |
| `fix_notes.js` | 浏览器补写使用须知（UEditor） | 唯一能写富文本 note 的路径，~7s/条 |
| `replace_covers.js` | 按卡券名批量换封面（PUT，剔除 note） | 需 `id-map.json` |
| `replace_extra.js` | 按 dbId 定向换封面（老批次） | 改 `TARGETS` 常量 |
| `finalize.js` / `verify2.js` | 抽样核验 + 统一 state | |
| `verify3.js` | **全量核验**：封面URL + note 段数 + state | 推荐最终收尾用 |
| `prepare_covers.py` / `upload_covers.js` | 中心裁剪 + UI 上传 | 仅 fallback，UI 必弹裁剪窗 |

## 3. 关键规则（踩过的坑）

1. **创建 payload 必须带 `state: 2`**（停用）。不带会落库 `state=0`——列表无启用/停用按钮的异常态。
2. **改状态只能走** `POST /coupon-info/state` body `{ids:"1043,1044", state:2}`（ids 为逗号串，可批量）。POST 详情接口带 id 改 state 返回 success 但不生效。
3. **note 的三种行为**：
   - payload **带** note → HTML 被 XSS 过滤，只剩纯文本；
   - payload **不带** note → 原值完整保留；
   - 要**写入/重写** note → 只能走 UI（`fix_notes.js`：UEditor `setContent(html)` → 保存）。
   → 所以换封面一律用「剔除 note 的 PUT」，又快又不破坏富文本。
4. **上传 uploadId 必须服务端下发**：`GET /file/uploadid?...` 自造会报"uploadId已经失效"。upload 请求头只带 `x-authorization`，**不要手动设 Content-Type**（FormData 自带 boundary）。
5. **UI 上传必然弹裁剪窗**：前端 `VPicUpload` 的 `isNeedCrop=true`，即使图已是 180×180。纯 API 上传是唯一免弹窗方案。
6. **封面匹配顺序**（`build_coupons.py`）：`COVER_OVERRIDE` → **日期前缀**（`10.2-3玉蜻蜓.jpg` → 10月2/3日场次共用）→ 序号前缀 → 剧目名子目录 → 文件名关键词；**递归**扫描子目录（海报常被放进 `海报/` 子目录）。
   `COVER_OVERRIDE` 的值**不写扩展名**（源图可能在 .jpg/.png 间变动），运行时自动解析。
7. **强制重传**：`api_upload.js` 对已有 URL 直接跳过，重裁后必须清掉 json 里的旧 key 才能真正换新图。
8. **别用 UI 逐条创建**（~40s/条），商户 checkbox 树点击不稳定。

详细 API 契约、字段表、商户 ID 见 `references/api-reference.md`；历史案例与排错见 `references/case-2026-09.md`。

## 4. 业务字段规则（每次与用户确认）

| 表单项 | 取值 |
|---|---|
| 卡券类型 | 兑换券（couponType=1） |
| 卡券/商品名称 | 剧目名称 + 演出日期时间，如 `剧目X9月4日19:30` |
| 列表封面 | cover 目录对应海报，裁成 180×180 |
| 商家名称 | 演出场地（含子剧场） |
| 标签分类 | 新生礼包（tagCategoryId=3） |
| 兑换数量 / 单人限领 | 1 / 1（openidType=2, openidLimit=1） |
| 领取时间 | 9月1日 00:00:00 ~ 演出次日 00:00:00 |
| 有效时间 | 演出当日 00:00:00 ~ 次日 00:00:00 |
| 最大发行数量 | 每场票数 |
| 使用须知 | 固定文案（7 个 `<p>`） |
| 可用商户 | 指定平台商户（usedMerchantType=3），取 Excel「可用商户」列 |

## 5. 注意事项

- 新建后默认停用，**上线需人工在后台列表「启用」——不要擅自批量启用**。
- 多人并行操作同一后台，token 会被顶下线，重跑 `login.js` 即可。
- 幂等性：`replace_covers.js` / `replace_extra.js` 对封面已一致的自动跳过，可重复执行。
- 老批次卡券可能不在 `id-map.json`，用 `replace_extra.js` 或直接按 dbId 处理。
