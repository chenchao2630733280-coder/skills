// 用浏览器 UI 上传所有 180x180 封面，收集返回的 fileUrl -> cover-urls.json
const fs = require('fs');
const path = require('path');
const { launch, BASE } = require('./lib');

const ROOT = process.cwd();
const MAP = JSON.parse(fs.readFileSync(path.join(ROOT, 'cover-map.json'), 'utf-8'));
const OUT = path.join(ROOT, 'cover-urls.json');

(async () => {
  const urls = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf-8')) : {};
  const ctx = await launch(true);
  const page = ctx.pages()[0] || await ctx.newPage();

  let pending = null;
  page.on('response', async r => {
    if (r.url().includes('/api/file/upload')) {
      try { pending = (await r.json()).data.fileUrl; } catch (e) {}
    }
  });

  await page.goto(BASE + '/platform/student-gift-bag/coupon-manage/coupon/0?type=edit', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  for (const [rel, local] of Object.entries(MAP)) {
    if (urls[rel]) { console.log('skip', path.basename(rel)); continue; }
    pending = null;
    await page.locator('input[type=file].el-upload__input').setInputFiles(path.join(ROOT, local));
    await page.waitForTimeout(2200);
    try {
      await page.locator('.el-dialog:visible').getByRole('button', { name: /确\s*认/ }).first().click({ timeout: 12000 });
    } catch (e) { console.log('⚠ 无裁剪弹窗:', path.basename(rel)); }
    await page.waitForTimeout(3500);
    if (pending) {
      urls[rel] = pending;
      console.log('↑', path.basename(rel), '->', pending.slice(-28));
      fs.writeFileSync(OUT, JSON.stringify(urls, null, 2), 'utf-8');
    } else {
      console.log('✗ 未拿到 URL:', path.basename(rel));
    }
  }
  console.log(`\n完成 ${Object.keys(urls).length}/${Object.keys(MAP).length}`);
  await ctx.close();
})();
