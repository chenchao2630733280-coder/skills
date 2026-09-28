// 收尾：抽样核验封面 + 统一把新建卡券状态置为 2（停用，与手动创建一致）
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

const FILE = process.argv[2] || 'coupons1.json';
const DATA = JSON.parse(fs.readFileSync(path.join(process.cwd(), FILE), 'utf-8'));
const B = 'https://szd-coupon.2500city.com/platform/api';
const H = { 'x-authorization': TOKEN, 'content-type': 'application/json' };
const get = u => fetch(B + u, { headers: { 'x-authorization': TOKEN } }).then(r => r.json());

(async () => {
  // 1. 拉取全部卡券建名称索引
  let all = [];
  for (let p = 1; p <= 30; p++) {
    const j = await get(`/coupon-infos?currentPage=${p}&perPage=50&couponName=&merchantName=&state=`);
    const l = j.data?.list || [];
    all = all.concat(l);
    if (l.length < 50) break;
  }
  const byName = new Map();
  for (const x of all) if (!byName.has(x.couponName)) byName.set(x.couponName, x);

  // 2. 找到本次创建的 id
  const ids = [], missing = [];
  for (const c of DATA) {
    const x = byName.get(c['卡券名称']);
    if (x) ids.push(x.id); else missing.push(c['卡券名称']);
  }
  console.log(`匹配到 ${ids.length} 条，未找到 ${missing.length} 条`);
  if (missing.length) missing.forEach(m => console.log('  ✗', m));

  // 3. 抽样核验封面（8 条，覆盖有封面与无封面）
  const withCover = DATA.filter(c => c['封面']);
  const noCover = DATA.filter(c => !c['封面']);
  const sample = [withCover[0], withCover[Math.floor(withCover.length / 2)], withCover[withCover.length - 1], noCover[0]].filter(Boolean);
  console.log('\n--- 抽样详情核验 ---');
  for (const c of sample) {
    const x = byName.get(c['卡券名称']);
    const d = (await get('/coupon-info/' + x.id)).data;
    const expB = Math.floor(new Date(c['有效开始'].replace(' ', 'T') + '+08:00').getTime() / 1000);
    const expE = Math.floor(new Date(c['有效结束'].replace(' ', 'T') + '+08:00').getTime() / 1000);
    console.log(`${x.id} ${c['卡券名称'].slice(0, 20)}`);
    console.log(`   封面:${d.listCoverImage ? '有' : '无'}(期望${c['封面'] ? '有' : '无'}) 库存:${d.leftNum}/${d.quantity} 有效:${d.beginTime === expB && d.endTime === expE ? 'OK' : 'BAD'} 商户:${d.usedMerchantValue}(期望${c['可用商户id']}) 须知:${(d.note || '').length}字 state:${d.state}`);
  }

  // 4. 统一状态：state=0 -> 2
  const zero = ids.filter(id => (byName.get([...byName.values()].find(v => v.id === id)?.couponName) || {}).state === 0);
  const idsZero = [];
  for (const c of DATA) {
    const x = byName.get(c['卡券名称']);
    if (x && x.state === 0) idsZero.push(x.id);
  }
  console.log(`\n需置为停用(state=2)的卡券: ${idsZero.length} 条`);
  if (idsZero.length) {
    for (let i = 0; i < idsZero.length; i += 50) {
      const batch = idsZero.slice(i, i + 50);
      const r = await fetch(B + '/coupon-info/state', { method: 'POST', headers: H, body: JSON.stringify({ ids: batch.join(','), state: 2 }) });
      console.log('  批量设置', batch.length, '条 ->', (await r.text()).slice(0, 80));
    }
  }
  // 复核
  let stillZero = 0;
  for (const c of DATA) {
    const x = byName.get(c['卡券名称']);
    if (!x) continue;
    const d = (await get('/coupon-info/' + x.id)).data;
    if (d.state !== 2) { stillZero++; console.log('  ⚠ 状态仍非2:', x.id, d.state); }
  }
  console.log(`复核完成，状态异常 ${stillZero} 条`);
})();
