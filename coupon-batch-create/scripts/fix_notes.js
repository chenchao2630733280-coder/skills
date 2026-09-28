// 批量修复使用须知 note 格式：浏览器走 UEditor setContent + 保存（API 路径会被过滤）
// 用法：node fix_notes.js <id-json>
const fs = require('fs');
const path = require('path');
const { launch, BASE } = require('./lib');

const ROOT = process.cwd();
// 完整版使用须知（与 1037 一致，每行一个 <p>）
const GOOD_NOTE = '<p>权益名称：“知苏”乐游指南</p>' +
  '<p>活动提供单位全称：苏州市文化广电和旅游局</p>' +
  '<p>权益说明：</p>' +
  '<p>提供一定数量的剧院演出票，新生可在“苏周到”APP免费领取，领取成功后可至相应剧院观看演出。</p>' +
  '<p>使用时间：领取后至2026年11月30日。</p>' +
  '<p>使用说明：下载并注册登录“苏周到”APP，进入高校新生开学季专题页面，点击相关网页链接进行领取，领取成功后线下至相应剧院前台或票务中心核销使用。演出票数量有限，先到先得，领完即止。</p>' +
  '<p>咨询电话：苏州文化艺术中心0512-62899875或4008288299；苏州保利大剧院0512-65027666或0512-65027888；苏州湾大剧院19551012000（9:00-17:00）；苏州狮山大剧院4009282200；开明大戏院 17751132009（周一至周五9:00-17:00）；中国昆曲剧院 0512-69165602；光裕书厅0512-65233735；北部市民中心青橙剧场4008288299；苏州昆曲传习所13915411217。</p>';

async function fixOne(page, id) {
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      await page.goto(`${BASE}/platform/student-gift-bag/coupon-manage/coupon/${id}?type=edit`, { waitUntil: 'domcontentloaded' });
      // 等 UEditor 实例且 body 存在
      await page.waitForFunction(() => {
        const k = Object.keys(window.UE?.instants || {})[0];
        const inst = k ? window.UE.instants[k] : null;
        return inst && inst.body;
      }, { timeout: 20000 });
      await page.waitForTimeout(1500);   // 等 UEditor 内部 ready
      // 直接同步写入，不传复杂 html（防 page.evaluate 序列化问题）
      const ok = await page.evaluate(html => {
        const k = Object.keys(window.UE.instants)[0];
        const inst = window.UE.instants[k];
        if (!inst || !inst.setContent) return 'no-setcontent';
        try { inst.setContent(html); return 'ok'; } catch (e) { return 'err: ' + e.message; }
      }, GOOD_NOTE);
      if (ok !== 'ok') throw new Error('setContent: ' + ok);
      await page.waitForTimeout(500);
      await page.getByRole('button', { name: /保\s*存/ }).first().click();
      await page.waitForTimeout(4000);
      return;
    } catch (e) {
      lastErr = e;
      await page.waitForTimeout(2000);
    }
  }
  throw lastErr;
}

(async () => {
  const ids = JSON.parse(fs.readFileSync(process.argv[2] || 'id-map.json', 'utf-8'));
  const idList = (Array.isArray(ids) ? ids : Object.values(ids).map(v => v.dbId || v.id)).filter(Number.isFinite);
  console.log('待修复', idList.length, '条');
  const ctx = await launch(true);
  const page = ctx.pages()[0] || await ctx.newPage();
  // 刷新 token
  await page.goto(BASE + '/platform/student-gift-bag/setting/admin-manage', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  fs.writeFileSync('.token', await page.evaluate(() => localStorage.getItem('admin-platform-token-student-gift-bag')), 'utf-8');
  console.log('token 已刷新');
  const log = [];
  for (let i = 0; i < idList.length; i++) {
    const id = idList[i];
    try {
      await fixOne(page, id);
      log.push({ id, ok: true, t: Date.now() });
      if ((i + 1) % 10 === 0 || i === idList.length - 1) console.log(`[${i+1}/${idList.length}] id=${id} OK`);
    } catch (e) {
      log.push({ id, ok: false, err: e.message.slice(0, 80) });
      console.log(`[${i+1}/${idList.length}] id=${id} ✗ ${e.message.slice(0, 80)}`);
    }
  }
  fs.writeFileSync('fix-notes-log.json', JSON.stringify(log, null, 2), 'utf-8');
  const ok = log.filter(x => x.ok).length;
  console.log(`\n完成 ${ok}/${log.length}`);
  await ctx.close();
})();
