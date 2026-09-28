// 通过后台 API 批量创建卡券
// 用法: node api_batch.js <coupons.json> [起始序号1-based] [条数] [--dry]
const fs = require('fs');
const path = require('path');

const FILE = process.argv[2] || 'coupons1.json';
const START = parseInt(process.argv[3] || '1', 10);
const N = process.argv[4] && process.argv[4] !== '--dry' ? parseInt(process.argv[4], 10) : 9999;
const DRY = process.argv.includes('--dry');
const BASE = 'https://szd-coupon.2500city.com';
const ROOT = process.cwd();
const TOKEN_FILE = path.join(ROOT, '.token');

const TOKEN = fs.readFileSync(TOKEN_FILE, 'utf-8').trim();
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, FILE), 'utf-8'));
const COVER_MAP = JSON.parse(fs.readFileSync(path.join(ROOT, 'cover-map.json'), 'utf-8'));
const URL_FILE = path.join(ROOT, 'cover-urls.json');
const RESULT_FILE = path.join(ROOT, `result-${FILE.replace('.json', '')}.json`);

const tz = s => Math.floor(new Date(s.replace(' ', 'T') + '+08:00').getTime() / 1000);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const noteHtml = txt => txt.split('\n').map(l => `<p>${l}</p>`).join('');

// 1. 上传封面（按文件去重）
async function uploadCover(rel) {
  const local = path.join(ROOT, COVER_MAP[rel]);
  const buf = fs.readFileSync(local);
  const fd = new FormData();
  fd.append('file', new Blob([buf], { type: 'image/png' }), Date.now() + '.png');
  fd.append('uploadId', Array.from({ length: 32 }, () => '0123456789abcdef'[Math.floor(Math.random() * 16)]).join(''));
  const r = await fetch(`${BASE}/platform/api/file/upload`, {
    method: 'POST',
    headers: { 'x-authorization': TOKEN },
    body: fd,
  });
  const j = await r.json();
  if (j.code !== 0) throw new Error('upload fail: ' + JSON.stringify(j));
  return j.data.fileUrl;
}

async function create(c, coverUrl) {
  const payload = {
    couponType: 1,
    couponName: c['卡券名称'],
    merchantName: c['商家名称'],
    merchantId: 0,
    tagCategoryId: 3,
    expiredType: 1,
    beginTime: tz(c['有效开始']),
    endTime: tz(c['有效结束']),
    fixedTerm: 0,
    openidLimit: c['单人限领'],
    quantity: c['最大发行数量'],
    note: noteHtml(c['使用须知']),
    giftTitle: c['商品名称'],
    giftNum: c['兑换数量'],
    usedMerchantType: 3,
    usedMerchantValue: String(c['可用商户id']),
    datasource: 0,
    datasourceUrl: '',
    codeType: 1,
    jumpType: false,
    jumpUrl: '',
    jumpText: '',
    openidType: 2,
    state: 2,
    isAllowPlatform: 0,
    thirdMerchants: [],
    isShow: true,
    takeBeginAt: tz(c['领取开始']),
    takeEndAt: tz(c['领取结束']),
    isAutoRecycle: 0,
    listCoverImage: coverUrl || '',
    isDynamicsCode: 1,
    isNotice: 0,
  };
  if (DRY) return { dry: true, payload };
  const r = await fetch(`${BASE}/platform/api/coupon-info`, {
    method: 'POST',
    headers: { 'x-authorization': TOKEN, 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return await r.json();
}

(async () => {
  const list = DATA.slice(START - 1, START - 1 + N);
  console.log(`处理 ${list.length} 条（第 ${START} ~ ${START + list.length - 1} 条） DRY=${DRY}`);

  // 封面 URL：优先用已上传的 cover-urls.json，否则现传
  const coverUrls = fs.existsSync(URL_FILE) ? JSON.parse(fs.readFileSync(URL_FILE, 'utf-8')) : {};
  const rels = [...new Set(list.map(c => c['封面']).filter(Boolean))];
  for (const rel of rels) {
    if (coverUrls[rel]) continue;
    if (!COVER_MAP[rel]) { console.log('⚠ 封面未预处理:', rel); continue; }
    coverUrls[rel] = await uploadCover(rel);
    console.log('↑ 封面', path.basename(rel), '->', coverUrls[rel].slice(-30));
  }

  const results = fs.existsSync(RESULT_FILE) ? JSON.parse(fs.readFileSync(RESULT_FILE, 'utf-8')) : [];
  let ok = 0, fail = 0;
  for (let i = 0; i < list.length; i++) {
    const c = list[i];
    const url = c['封面'] ? coverUrls[c['封面']] : '';
    try {
      const res = await create(c, url);
      const success = res.dry || res.code === 0;
      success ? ok++ : fail++;
      console.log(`${START + i}. [${success ? 'OK' : 'FAIL'}] ${c['卡券名称']}${success ? '' : ' ' + JSON.stringify(res)}`);
      results.push({ idx: START + i, name: c['卡券名称'], ok: success, res });
    } catch (e) {
      fail++;
      console.log(`${START + i}. [ERR] ${c['卡券名称']} ${e.message}`);
      results.push({ idx: START + i, name: c['卡券名称'], ok: false, err: e.message });
    }
    fs.writeFileSync(RESULT_FILE, JSON.stringify(results, null, 2), 'utf-8');
    await sleep(300);
  }
  console.log(`\n完成: 成功 ${ok} / 失败 ${fail}`);
})();
