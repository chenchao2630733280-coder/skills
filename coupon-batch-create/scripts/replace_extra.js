// 替换 coupon0 批次（1036-1043）封面，原理同 replace_covers.js：PUT 剔除 note 字段
const fs = require('fs');
const path = require('path');
// token：优先当前工作目录，其次脚本所在目录
function readToken() {
  const cands = [path.join(process.cwd(), '.token'), path.join(__dirname, '.token')];
  const f = cands.find(p => fs.existsSync(p));
  if (!f) throw new Error('未找到 .token（当前目录或脚本目录），请先运行 node login.js 登录');
  return fs.readFileSync(f, 'utf-8').trim();
}
const TOKEN = readToken();

const BASE = 'https://szd-coupon.2500city.com/platform/api';
const H = { 'x-authorization': TOKEN, 'content-type': 'application/json' };

const KEYS = ['couponType', 'couponName', 'listCoverImage', 'merchantName', 'tagCategoryId',
  'expiredType', 'openidType', 'openidLimit', 'quantity', 'usedMerchantType', 'datasource',
  'codeType', 'jumpType', 'isDynamicsCode', 'isAutoRecycle', 'jumpUrl', 'jumpText',
  'thirdMerchants', 'isNotice', 'beginTime', 'endTime', 'takeBeginAt', 'takeEndAt',
  'usedMerchantValue', 'giftTitle', 'giftNum', 'state'];
const INT_KEYS = ['couponType', 'tagCategoryId', 'expiredType', 'openidType', 'openidLimit',
  'quantity', 'usedMerchantType', 'datasource', 'codeType', 'isDynamicsCode', 'isAutoRecycle',
  'isNotice', 'giftNum', 'beginTime', 'endTime', 'takeBeginAt', 'takeEndAt', 'state'];

const TARGETS = [
  [1036, 'cover/中国昆曲剧院/实景版《游园惊梦》.jpg'],
  [1040, 'cover/中国昆曲剧院/实景版《游园惊梦》.jpg'],
  [1042, 'cover/中国昆曲剧院/实景版《游园惊梦》.jpg'],
  [1037, 'cover/苏州文化艺术中心/19吴门琴派古琴音乐会.jpg'],
  [1038, 'cover/苏州文化艺术中心/19吴门琴派古琴音乐会.jpg'],
  [1039, 'cover/苏州文化艺术中心/20姑苏笑林苑.jpg'],
  [1041, 'cover/苏州文化艺术中心/20姑苏笑林苑.jpg'],
  [1043, 'cover/苏州文化艺术中心/21悬疑剧《维罗妮卡的房间》.jpg'],
];

(async () => {
  const urls = JSON.parse(fs.readFileSync('cover-urls-api.json', 'utf-8'));
  let ok = 0, skip = 0, fail = 0;
  for (const [id, rel] of TARGETS) {
    const url = urls[rel];
    if (!url) { console.log('✗', id, '无URL', rel); fail++; continue; }
    try {
      const r0 = await fetch(`${BASE}/coupon-info/${id}`, { headers: H });
      const j0 = await r0.json();
      if (j0.code !== 0) throw new Error(j0.msg);
      const src = j0.data;
      if (src.listCoverImage === url) { console.log('=', id, '无变化'); skip++; continue; }
      const body = {};
      for (const k of KEYS) {
        let v = src[k];
        if (INT_KEYS.includes(k)) v = Number(v) || 0;
        if (k === 'jumpType') v = v ? 1 : 0;
        if (k === 'thirdMerchants' && !Array.isArray(v)) v = [];
        if (k === 'listCoverImage') v = url;
        body[k] = v;
      }
      const r = await fetch(`${BASE}/coupon-info/${id}`, { method: 'PUT', headers: H, body: JSON.stringify(body) });
      const j = await r.json();
      if (j.code !== 0) throw new Error(j.msg || JSON.stringify(j).slice(0, 80));
      console.log('✓', id, src.couponName.slice(0, 24));
      ok++;
    } catch (e) {
      console.log('✗', id, e.message.slice(0, 80));
      fail++;
    }
    await new Promise(r => setTimeout(r, 250));
  }
  console.log(`\n完成: 替换 ${ok} | 无变化 ${skip} | 失败 ${fail}`);
})();
