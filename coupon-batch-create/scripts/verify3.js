// 核验：封面是否为本次新上传 URL + note 未被清空 + state 仍为 2
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
const H = { 'x-authorization': TOKEN };

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const coupons = JSON.parse(fs.readFileSync('coupons1.json', 'utf-8'));
  const idMap = JSON.parse(fs.readFileSync('id-map.json', 'utf-8'));
  const urls = JSON.parse(fs.readFileSync('cover-urls-api.json', 'utf-8'));
  const byName = new Map();
  for (const v of Object.values(idMap)) if (v.name && v.dbId) byName.set(v.name, v.dbId);

  const ids = [...new Set(coupons.map(c => byName.get(c['卡券名称'])).filter(Boolean))];
  const expect = new Map();
  for (const c of coupons) {
    const id = byName.get(c['卡券名称']);
    if (id && c['封面'] && urls[c['封面']]) expect.set(id, urls[c['封面']]);
  }

  let coverOk = 0, coverBad = 0, noteOk = 0, noteBad = 0, stateBad = 0;
  const bad = [];
  for (let i = 0; i < ids.length; i++) {
    const id = ids[i];
    const r = await fetch(`${BASE}/coupon-info/${id}`, { headers: H });
    const j = await r.json();
    if (j.code !== 0) { bad.push({ id, err: j.msg }); continue; }
    const d = j.data;
    const want = expect.get(id);
    if (want && d.listCoverImage === want) coverOk++; else { coverBad++; bad.push({ id, coverMismatch: d.listCoverImage }); }
    const p = (d.note || '').match(/<p[\s>]/g);
    if (p && p.length === 7) noteOk++; else { noteBad++; bad.push({ id, noteP: p ? p.length : 0 }); }
    if (Number(d.state) !== 2) { stateBad++; bad.push({ id, state: d.state }); }
    if (i % 40 === 39) await sleep(200);
  }
  console.log(`卡券数 ${ids.length}`);
  console.log(`封面正确: ${coverOk} | 不符: ${coverBad}`);
  console.log(`note 7段: ${noteOk} | 异常: ${noteBad}`);
  console.log(`state!=2: ${stateBad}`);
  if (bad.length) { console.log('异常明细(前10):'); bad.slice(0, 10).forEach(b => console.log('  ', JSON.stringify(b))); }
})();
