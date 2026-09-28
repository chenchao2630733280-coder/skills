// 纯 API 上传封面：GET /file/uploadid → POST /file/upload → 拿到 fileUrl
// 完全不依赖浏览器，零弹窗、零裁剪
// 用法：node api_upload.js <cover-map.json> [output.json]
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
const HEADERS = { 'x-authorization': TOKEN };

const SUFFIX = { '.png':'png', '.jpg':'jpg', '.jpeg':'jpeg', '.gif':'gif' };

async function getUploadId(fileSize, suffix) {
  const u = `${BASE}/file/uploadid?isPublic=1&isPart=2&suffix=${suffix}&fileSize=${fileSize}`;
  const r = await fetch(u, { headers: HEADERS });
  const j = await r.json();
  if (j.code !== 0) throw new Error('uploadid 失败: ' + (j.msg || JSON.stringify(j)));
  return j.data.uploadId;
}

async function uploadOne(localPath) {
  const buf = fs.readFileSync(localPath);
  const ext = path.extname(localPath).toLowerCase();
  const suf = SUFFIX[ext] || 'png';
  const uploadId = await getUploadId(buf.length, suf);
  const fd = new FormData();
  fd.append('file', new Blob([buf], { type: 'image/' + suf }), Date.now() + ext);
  fd.append('uploadId', uploadId);
  const r = await fetch(BASE + '/file/upload', { method: 'POST', headers: HEADERS, body: fd });
  const j = await r.json();
  if (j.code !== 0) throw new Error('upload 失败: ' + (j.msg || JSON.stringify(j)));
  return j.data.fileUrl;
}

(async () => {
  const MAP = JSON.parse(fs.readFileSync(process.argv[2] || 'cover-map.json', 'utf-8'));
  const OUT = process.argv[3] || 'cover-urls-api.json';
  const urls = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf-8')) : {};
  let ok = 0, fail = 0;
  for (const [rel, local] of Object.entries(MAP)) {
    if (urls[rel]) { ok++; continue; }
    try {
      const url = await uploadOne(local);
      urls[rel] = url;
      ok++;
      console.log('↑', path.basename(rel), '->', url.slice(-30));
      fs.writeFileSync(OUT, JSON.stringify(urls, null, 2), 'utf-8');
    } catch (e) {
      fail++;
      console.log('✗', path.basename(rel), '|', e.message.slice(0, 100));
    }
  }
  console.log(`\n完成 ${ok}/${ok + fail}  (失败 ${fail})`);
})();
