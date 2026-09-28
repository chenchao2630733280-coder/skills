// 纯 API 批量替换卡券封面（智能裁切版）
// 原理：PUT /coupon-info/{id}，payload 剔除 note 字段 → 服务端不清空富文本（实测 <p> 保持 7 个）
// 用法：node replace_covers.js coupons1.json
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

// UI 保存时的精简字段集（注意：故意不含 note）
const KEYS = ['couponType', 'couponName', 'listCoverImage', 'merchantName', 'tagCategoryId',
  'expiredType', 'openidType', 'openidLimit', 'quantity', 'usedMerchantType', 'datasource',
  'codeType', 'jumpType', 'isDynamicsCode', 'isAutoRecycle', 'jumpUrl', 'jumpText',
  'thirdMerchants', 'isNotice', 'beginTime', 'endTime', 'takeBeginAt', 'takeEndAt',
  'usedMerchantValue', 'giftTitle', 'giftNum', 'state'];
const INT_KEYS = ['couponType', 'tagCategoryId', 'expiredType', 'openidType', 'openidLimit',
  'quantity', 'usedMerchantType', 'datasource', 'codeType', 'isDynamicsCode', 'isAutoRecycle',
  'isNotice', 'giftNum', 'beginTime', 'endTime', 'takeBeginAt', 'takeEndAt', 'state'];

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getCoupon(id) {
  const r = await fetch(`${BASE}/coupon-info/${id}`, { headers: H });
  const j = await r.json();
  if (j.code !== 0) throw new Error('详情失败: ' + (j.msg || JSON.stringify(j)).slice(0, 60));
  return j.data;
}

function buildPayload(src, newCover) {
  const body = {};
  for (const k of KEYS) {
    let v = src[k];
    if (INT_KEYS.includes(k)) v = Number(v) || 0;
    if (k === 'jumpType') v = v ? 1 : 0;
    if (k === 'thirdMerchants' && !Array.isArray(v)) v = [];
    if (k === 'listCoverImage') v = newCover;
    body[k] = v;
  }
  return body;
}

async function updateCover(id, newCover) {
  const src = await getCoupon(id);
  if (src.listCoverImage === newCover) return { skipped: true };
  const body = buildPayload(src, newCover);
  const r = await fetch(`${BASE}/coupon-info/${id}`, { method: 'PUT', headers: H, body: JSON.stringify(body) });
  const j = await r.json();
  if (j.code !== 0) throw new Error('PUT 失败: ' + (j.msg || JSON.stringify(j)).slice(0, 80));
  return { ok: true, oldCover: src.listCoverImage };
}

async function main() {
  const srcFile = process.argv[2] || 'coupons1.json';
  const coupons = JSON.parse(fs.readFileSync(srcFile, 'utf-8'));
  const idMap = JSON.parse(fs.readFileSync('id-map.json', 'utf-8'));
  const urls = JSON.parse(fs.readFileSync('cover-urls-api.json', 'utf-8'));

  // 卡券名称 -> dbId
  const byName = new Map();
  for (const v of Object.values(idMap)) if (v.name && v.dbId) byName.set(v.name, v.dbId);

  const targets = [];
  const noId = [], noCover = [];
  for (const c of coupons) {
    const dbId = byName.get(c['卡券名称']);
    if (!dbId) { noId.push(c['卡券名称']); continue; }
    const rel = c['封面'];
    const url = rel ? urls[rel] : null;
    if (!url) { noCover.push(c['卡券名称']); continue; }
    targets.push({ dbId, name: c['卡券名称'], url });
  }

  console.log(`待替换 ${targets.length} 条` + (noId.length ? ` | 无ID ${noId.length}` : '') + (noCover.length ? ` | 无封面 ${noCover.length}` : ''));
  if (noCover.length) noCover.slice(0, 5).forEach(n => console.log('   ⚠ 无封面:', n));

  const log = [];
  let ok = 0, skip = 0, fail = 0;
  for (let i = 0; i < targets.length; i++) {
    const t = targets[i];
    try {
      const r = await updateCover(t.dbId, t.url);
      if (r.skipped) { skip++; log.push({ id: t.dbId, name: t.name, skipped: true }); console.log(`[${i + 1}/${targets.length}] = id=${t.dbId} 封面无变化`); }
      else { ok++; log.push({ id: t.dbId, name: t.name, ok: true }); console.log(`[${i + 1}/${targets.length}] ✓ id=${t.dbId} ${t.name.slice(0, 26)}`); }
    } catch (e) {
      fail++; log.push({ id: t.dbId, name: t.name, ok: false, err: e.message.slice(0, 100) });
      console.log(`[${i + 1}/${targets.length}] ✗ id=${t.dbId} ${e.message.slice(0, 70)}`);
    }
    if (i % 20 === 19) fs.writeFileSync('replace-covers-log.json', JSON.stringify(log, null, 2), 'utf-8');
    await sleep(250);
  }
  fs.writeFileSync('replace-covers-log.json', JSON.stringify(log, null, 2), 'utf-8');
  console.log(`\n=== 完成 ===\n替换成功: ${ok} | 无变化: ${skip} | 失败: ${fail}`);
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
