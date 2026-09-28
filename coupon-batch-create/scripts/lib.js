const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CHROME = 'C:/Users/26307/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe';
const USER_DATA = path.join(process.cwd(), '.browser-profile');
const STATE = path.join(process.cwd(), '.auth-state.json');
const BASE = 'https://szd-coupon.2500city.com';
const TARGET = BASE + '/platform/student-gift-bag/setting/admin-manage';

async function launch(headed = true) {
  const ctx = await chromium.launchPersistentContext(USER_DATA, {
    executablePath: fs.existsSync(CHROME) ? CHROME : undefined,
    headless: !headed,
    slowMo: 120,
    viewport: { width: 1600, height: 1000 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  return ctx;
}

module.exports = { launch, CHROME, USER_DATA, STATE, BASE, TARGET };
