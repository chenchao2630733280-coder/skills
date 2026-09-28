# 苏州卡券平台后台 API 参考

Base：`https://szd-coupon.2500city.com/platform/api`
认证：请求头 `x-authorization: <token>`
token 来源：浏览器 localStorage `admin-platform-token-student-gift-bag`
（用 playwright 打开任意后台页 `page.evaluate(() => localStorage.getItem('admin-platform-token-student-gift-bag'))`，或跑 `login.js`）

## 接口表

| 用途 | 方法 | 路径 |
|---|---|---|
| 卡券详情（payload 模板来源） | GET | `/coupon-info/{id}` |
| 创建 | POST | `/coupon-info`（JSON） |
| 更新 | PUT | `/coupon-info/{id}`（JSON，**剔除 note 才能保住原富文本**） |
| 列表 | GET | `/coupon-infos?currentPage=1&perPage=50&couponName=&merchantName=&state=` |
| 改状态 | POST | `/coupon-info/state` body `{ids:"1043,1044", state:2}` |
| 标签分类 | GET | `/coupon-tag-categories/list` |
| 商户树 | GET | `/sys-merchant/tree?level=1` |
| 取 uploadId | GET | `/file/uploadid?isPublic=1&isPart=2&suffix=png&fileSize=<字节>` → `data.uploadId` |
| 上传文件 | POST | `/file/upload` FormData `{file, uploadId}` → `data.fileUrl` |

状态码：`code === 0` 为成功，否则看 `msg`。

## 创建 payload

```js
{ couponType: 1, couponName, merchantName, merchantId: 0, tagCategoryId: 3,
  expiredType: 1, beginTime, endTime, fixedTerm: 0, openidLimit: 1, quantity,
  note: '<p>…</p>', giftTitle, giftNum: 1, usedMerchantType: 3, usedMerchantValue: '594',
  datasource: 0, codeType: 1, jumpType: false, openidType: 2, state: 2, isAllowPlatform: 0,
  thirdMerchants: [], isShow: true, takeBeginAt, takeEndAt, isAutoRecycle: 0,
  listCoverImage, isDynamicsCode: 1, isNotice: 0 }
```

- **必须带 `state: 2`**，否则落库 state=0（异常态，列表无启用/停用按钮）
- 时间戳为**秒级**，北京时间：`Math.floor(new Date('2026-09-04 00:00:00'.replace(' ','T')+'+08:00').getTime()/1000)`
- `usedMerchantType: 3` = 指定平台商户，`usedMerchantValue` 为商户 id 字符串

## 更新（PUT）字段集

用 UI 保存时的精简字段集，**故意不含 note**（含了会被 XSS 过滤）：

```
couponType, couponName, listCoverImage, merchantName, tagCategoryId,
expiredType, openidType, openidLimit, quantity, usedMerchantType, datasource,
codeType, jumpType, isDynamicsCode, isAutoRecycle, jumpUrl, jumpText,
thirdMerchants, isNotice, beginTime, endTime, takeBeginAt, takeEndAt,
usedMerchantValue, giftTitle, giftNum, state
```

整数字段需 `Number(v)`：`couponType, tagCategoryId, expiredType, openidType, openidLimit, quantity, usedMerchantType, datasource, codeType, isDynamicsCode, isAutoRecycle, isNotice, giftNum, beginTime, endTime, takeBeginAt, takeEndAt, state`。

## 商户 id（上级：苏州市文化广电和旅游局 586）

| id | 商户 |
|---|---|
| 594 | 苏州文化艺术中心 |
| 589 | 苏州保利大剧院 |
| 593 | 苏州湾大剧院 |
| 592 | 苏州狮山大剧院 |
| 590 | 苏州开明戏院 |
| 595 | 中国昆曲剧院 |
| 588 | 光裕书厅 |
| 591 | 苏州昆曲传习所 |
| 587 | 北部市民中心青橙剧场 |

## 前端行为备忘

- 上传组件 `VPicUpload`（chunk 866.js）：`isNeedCrop=true` 时非 gif 一律弹裁剪窗 → UI 路径无法免弹窗。
- UEditor 实例：`window.UE.instants` 首个实例，写内容用 `.setContent(html)`，需等 `inst.body` 存在。
- state 语义：1=启用，2=停用，0=异常态。
