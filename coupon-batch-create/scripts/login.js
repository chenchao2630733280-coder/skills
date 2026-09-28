// 打开后台登录页（有头窗口），等待用户手动完成登录，然后保存登录态并退出
const fs = require('fs');
const { launch, BASE, STATE } = require('./lib');

const TARGET = BASE + '/platform/student-gift-bag/login?redirect=/setting/admin-manage';
const ADMIN = BASE + '/platform/student-gift-bag/setting/admin-manage';

(async () => {
  const ctx = await launch(true);
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 60000 });
  console.log('OPENED:', page.url());

  const deadline = Date.now() + 20 * 60 * 1000;
  let ok = false;
  while (Date.now() < deadline) {
    try {
      if (!page.url().includes('/login')) { ok = true; break; }
    } catch (e) {}
    await page.waitForTimeout(2000);
  }

  if (!ok) {
    console.log('TIMEOUT: 20 分钟内未检测到登录完成');
    try { await page.screenshot({ path: 'shots/login-timeout.png' }); } catch (e) {}
    await ctx.close();
    process.exit(2);
  }

  await page.waitForTimeout(2500);
  try { await ctx.storageState({ path: STATE }); } catch (e) {}
  console.log('LOGIN_OK');
  console.log('FINAL_URL:', page.url());
  try {
    await page.screenshot({ path: 'shots/after-login.png', fullPage: true });
    fs.writeFileSync('shots/after-login.txt', await page.evaluate(() => document.body.innerText), 'utf-8');
  } catch (e) {}
  await ctx.close();
})();
