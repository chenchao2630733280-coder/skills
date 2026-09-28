// 通过 API 核验卡券创建结果
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

const f = t => {
  if (!t) return '—';
  const d = new Date(t * 1000 + 8 * 3600 * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

(async () => {
  // 拉取全部（分页）
  let all = [];
  for (let p = 1; p <= 20; p++) {
    const r = await fetch(`https://szd-coupon.2500city.com/platform/api/coupon-infos?currentPage=${p}&perPage=50&couponName=&merchantName=&state=`, { headers: { 'x-authorization': TOKEN } });
    const j = await r.json();
    const l = j.data?.list || [];
    all = all.concat(l);
    if (l.length < 50) break;
  }
  const byName = new Map(all.map(x => [x.couponName, x]));
  let ok = 0, bad = 0, miss = [];
  for (const c of DATA) {
    const x = byName.get(c['卡券名称']);
    if (!x) { miss.push(c['卡券名称']); continue; }
    const expBegin = Math.floor(new Date(c['有效开始'].replace(' ', 'T') + '+08:00').getTime() / 1000);
    const expEnd = Math.floor(new Date(c['有效结束'].replace(' ', 'T') + '+08:00').getTime() / 1000);
    const okTime = x.beginTime === expBegin && x.endTime === expEnd;
    const okQty = x.quantity === c['最大发行数量'];
    const okMer = String(x.usedMerchantValue) === String(c['可用商户id']);
    const okCover = c['封面'] ? !!x.listCoverImage : true;
    if (okTime && okQty && okMer && okCover) ok++;
    else { bad++; console.log('⚠ 字段不符:', x.couponName, { okTime, okQty, okMer, okCover }); }
  }
  console.log(`\n核验 ${DATA.length} 条：匹配成功 ${ok}，字段异常 ${bad}，未找到 ${miss.length}`);
  if (miss.length) {
    console.log('未找到清单:');
    miss.slice(0, 20).forEach(m => console.log('  -', m));
  }
  // 打印最新 5 条样例
  console.log('\n最新 5 条:');
  all.slice(0, 5).forEach(x => console.log(`  ${x.id} ${x.couponName} | ${x.merchantName} | ${x.leftNum}/${x.quantity} | ${f(x.beginTime)}~${f(x.endTime)} | 商户${x.usedMerchantValue} | ${(x.listCoverImage || '无封面').slice(-18)}`));
})();
