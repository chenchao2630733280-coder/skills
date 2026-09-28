/**
 * harvest.js — 无 API 的图片批量采集器（必应图库）
 *
 * 用法:
 *   node harvest.js --queries queries.json --out ./assets/img --per 4 --conc 6 [--only id1,id2]
 *
 * queries.json 形如:
 *   { "entry-id": { "zh": "中文检索词", "en": "english query" } }
 *   { "entry-id": "单个检索词" }
 *
 * 可选的 overrides.json（同目录或与 queries 同目录）:
 *   { "entry-id": ["更精确的中文词", "more precise english query"] }
 *
 * 产出: <out>/<id>-1.jpg ... <out>/<id>-<per>.jpg  +  <out>/manifest.json
 */
const fs = require('fs');
const path = require('path');

/* ---------------- 参数 ---------------- */
const argv = process.argv.slice(2);
const arg = (k, d) => {
  const i = argv.indexOf('--' + k);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : (process.env[k.toUpperCase()] || d);
};
const QUERIES_PATH = arg('queries', 'queries.json');
const OUT_DIR = arg('out', './assets/img');
const PER_TRIP = Number(arg('per', 4));
const CONCURRENCY = Number(arg('conc', 6));
const ONLY = arg('only', '') ? String(arg('only', '')).split(',') : null;
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

const raw = JSON.parse(fs.readFileSync(QUERIES_PATH, 'utf8'));
const entries = Object.entries(raw).map(([id, v]) => ({
  id,
  zh: typeof v === 'string' ? v : v.zh,
  en: typeof v === 'string' ? null : v.en
}));
const ovPath = [path.join(path.dirname(QUERIES_PATH), 'overrides.json'), 'overrides.json']
  .find((p) => fs.existsSync(p));
const overrides = ovPath ? JSON.parse(fs.readFileSync(ovPath, 'utf8')) : {};

/* ---------------- 来源站点分级 ---------------- */
const BLOCK = [
  'nipic', '699pic', 'redocn', '616pic', 'huitu', 'ntimg', 'huaban', 'qunarzz', 'vjshi',
  'zcool', '58pic', 'chuangkit', 'veer', 'gaoding', 'aigei', '51yuansu', 'pngtree',
  'alamy', 'gettyimages', 'freepik', 'shutterstock', 'dreamstime', 'istockphoto', '123rf',
  'tuchong', '500px', 'photophoto', '17qq', '88tph', 'tuxi', 'quanjing', 'hippopx',
  'pconline', 'chinaz', 'ssyer', 'zhimg', 'duitang'
];
const ALLOW = [
  'wikimedia', 'wikipedia', 'flickr', 'unsplash', 'pexels', 'pixabay', 'lonelyplanet',
  'nationalgeographic', 'natgeo', 'cntraveler', 'cntraveller', 'tripadvisor', 'atlasobscura',
  'chinadaily', 'cgtn', 'china.cn', 'xinhuanet', 'news.cn', 'gov.cn', 'globaltimes',
  'scmp', 'bbc.', 'cnn.', 'nytimes', 'theguardian', 'timeout', 'travelandleisure',
  'wanderinchina', 'exploringkiwis', 'tripsavvy', 'trip.com', 'ctrip', 'qyer', 'mafengwo',
  'booking.com', 'agoda', 'airbnb', 'blogspot', 'wordpress', 'medium.com'
];
const hostOf = (u) => { try { return new URL(u).host.toLowerCase(); } catch { return ''; } };
function score(u) {
  if (!u) return 2;
  const s = (hostOf(u) + u).toLowerCase();
  if (BLOCK.some((b) => s.includes(b))) return 3;
  if (ALLOW.some((a) => s.includes(a))) return 0;
  return 1;
}

/* ---------------- 工具 ---------------- */
fs.mkdirSync(OUT_DIR, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const isImage = (b) =>
  (b.length > 8 && b[0] === 0xff && b[1] === 0xd8) ||
  (b.length > 8 && b[0] === 0x89 && b[1] === 0x50) ||
  (b.length > 12 && b.slice(8, 12).toString('ascii') === 'WEBP');

async function search(q, first) {
  const url = `https://cn.bing.com/images/search?q=${encodeURIComponent(q)}`
    + `&qft=%2Bfilterui%3Aimagesize-large&form=IRFLTR&first=${first}`;
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8' },
    signal: AbortSignal.timeout(25000)
  });
  if (!res.ok) throw new Error('search ' + res.status);
  const html = await res.text();
  const clean = (s) => s.replace(/\\u002f/gi, '/').replace(/\\\//g, '/').replace(/&amp;/g, '&');
  const murls = [...html.matchAll(/murl&quot;:&quot;(.*?)&quot;/g)].map((m) => clean(m[1]));
  const oips = [...new Set([...html.matchAll(/OIP\.[A-Za-z0-9_-]{10,}/g)].map((m) => m[0]))];
  const out = [];
  for (let i = 0; i < Math.max(murls.length, oips.length); i++) out.push({ murl: murls[i] || null, oip: oips[i] || null });
  return out;
}

async function tryFetch(url, timeout = 22000) {
  const res = await fetch(url, {
    headers: { 'User-Agent': UA, Referer: 'https://cn.bing.com/' },
    redirect: 'follow',
    signal: AbortSignal.timeout(timeout)
  });
  if (!res.ok) throw new Error('http ' + res.status);
  const buf = Buffer.from(await res.arrayBuffer());
  if (!isImage(buf) || buf.length < 40000) throw new Error('bad ' + buf.length);
  return buf;
}

// 首选：必应缩略图 CDN（无防盗链、格式统一）
async function grabThumb(oip) {
  for (const host of [1, 2, 3, 4]) {
    try { return await tryFetch(`https://tse${host}.mm.bing.net/th?id=${oip}&w=1500&h=1000&c=7&rs=1&p=0`); }
    catch (e) { /* 换下一个 CDN 节点 */ }
  }
  return null;
}

async function collectCandidates(e) {
  const ov = overrides[e.id];
  const qs = ov ? ov.slice() : [e.en, e.zh].filter(Boolean);
  const list = [];
  for (const q of qs) {
    for (const first of [1, 36]) {
      try {
        for (const c of await search(q, first)) list.push(c);
      } catch (err) { /* 忽略单次失败 */ }
      await sleep(120);
    }
  }
  const seen = new Set();
  const uniq = [];
  for (const c of list) {
    if (!c.oip || seen.has(c.oip)) continue;
    seen.add(c.oip);
    c.score = score(c.murl);
    uniq.push(c);
  }
  uniq.sort((a, b) => a.score - b.score);
  // 同站点最多 2 张，保证多样性
  const byHost = new Map();
  const out = [];
  for (const c of uniq) {
    const h = hostOf(c.murl || '') || 'x';
    const n = byHost.get(h) || 0;
    if (n >= 2) continue;
    byHost.set(h, n + 1);
    out.push(c);
  }
  return out.filter((c) => c.score < 3).concat(out.filter((c) => c.score >= 3));
}

async function harvestOne(e) {
  const files = [];
  const cands = await collectCandidates(e);
  if (!cands.length) return { id: e.id, files, error: 'no candidates' };
  for (const c of cands) {
    if (files.length >= PER_TRIP) break;
    let buf = await grabThumb(c.oip);
    if (!buf && c.murl && /^https?:\/\//.test(c.murl) && score(c.murl) < 3) {
      try { buf = await tryFetch(c.murl); } catch (err) { /* skip */ }
    }
    if (!buf) continue;
    const file = `${e.id}-${files.length + 1}.jpg`;
    fs.writeFileSync(path.join(OUT_DIR, file), buf);
    files.push(file);
    await sleep(100);
  }
  return { id: e.id, files };
}

/* ---------------- 主流程 ---------------- */
(async () => {
  const todo = ONLY ? entries.filter((e) => ONLY.includes(e.id)) : entries;
  console.log(`采集 ${todo.length} 条 × ${PER_TRIP} 张，并发 ${CONCURRENCY}`);
  const results = [];
  let cursor = 0;
  const t0 = Date.now();

  async function worker() {
    while (cursor < todo.length) {
      const e = todo[cursor++];
      let r;
      try { r = await harvestOne(e); }
      catch (err) { r = { id: e.id, files: [], error: String(err.message || err) }; }
      results.push(r);
      if (results.length % 5 === 0 || results.length === todo.length) {
        console.log(`[${results.length}/${todo.length}] ${((Date.now() - t0) / 1000).toFixed(0)}s ${r.id} -> ${r.files.length}${r.error ? ' ERR:' + r.error : ''}`);
      }
    }
  }
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));

  const mPath = path.join(OUT_DIR, 'manifest.json');
  const manifest = fs.existsSync(mPath) ? JSON.parse(fs.readFileSync(mPath, 'utf8')) : {};
  for (const r of results) if (r.files.length) manifest[r.id] = r.files;
  fs.writeFileSync(mPath, JSON.stringify(manifest, null, 2), 'utf8');

  const bad = results.filter((r) => !r.files.length);
  const partial = results.filter((r) => r.files.length && r.files.length < PER_TRIP);
  console.log(`\n完整 ${results.filter((r) => r.files.length >= PER_TRIP).length} / 部分 ${partial.length} / 失败 ${bad.length}`);
  if (partial.length) console.log('部分:', partial.map((r) => `${r.id}(${r.files.length})`).join(' '));
  if (bad.length) console.log('失败:', bad.map((r) => r.id).join(' '));
  console.log(`耗时 ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})();
