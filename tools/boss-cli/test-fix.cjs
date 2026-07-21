const puppeteer = require('puppeteer-core');

(async () => {
  try {
    const wsRes = await fetch('http://127.0.0.1:53470/json/version');
    const wsData = await wsRes.json();
    const browser = await puppeteer.connect({ browserWSEndpoint: wsData.webSocketDebuggerUrl });
    const page = (await browser.pages()).find(p => p.url().includes('zhipin.com'));
    if (!page) { console.log('No zhipin page'); browser.disconnect(); return; }

    // Test the exact pattern from our fix
    console.log('--- Testing fixed sidebar nav pattern ---');
    const menuLabel = '推荐';
    const targetPath = '/web/chat/recommend';
    const argsJson = JSON.stringify({ label: menuLabel, path: targetPath });
    console.log('argsJson:', argsJson);

    // Build the full evaluate string and print it
    const evalStr = `((args) => {
      const label = args.label;
      const path = args.path;
      const norm = (v) => (v ?? "").replace(/\\s+/g, "");
      const links = Array.from(document.querySelectorAll(".menu-list a"));
      const target = links.find((a) => {
        const href = a.getAttribute("href") ?? "";
        if (href.includes(path)) return true;
        const text = norm(a.querySelector(".menu-item-content span")?.textContent ?? a.textContent);
        return text.includes(label);
      });
      if (!(target instanceof HTMLElement)) return false;
      target.scrollIntoView({ block: "center", inline: "nearest" });
      target.click();
      return true;
    })(${argsJson})`;
    console.log('evalStr length:', evalStr.length);
    console.log('evalStr first 200 chars:', evalStr.substring(0, 200));
    console.log('evalStr last 50 chars:', evalStr.substring(evalStr.length - 50));

    // Try evaluating
    try {
      const result = await page.evaluate(evalStr);
      console.log('Result:', result);
      await new Promise(r => setTimeout(r, 2000));
      console.log('URL after:', page.url());
    } catch(e) {
      console.log('Evaluate error:', e.message);
    }

    // Go back
    try {
      await page.evaluate(`((args) => {
        const links = Array.from(document.querySelectorAll(".menu-list a"));
        const target = links.find((a) => (a.getAttribute("href") ?? "").includes(args.path));
        if (target) target.click();
      })(${JSON.stringify({ path: '/web/chat/index' })})`);
      await new Promise(r => setTimeout(r, 1500));
      console.log('URL after going back:', page.url());
    } catch(e) {
      console.log('Go back error:', e.message);
    }

    // Test chat click pattern
    console.log('\n--- Testing fixed chat click pattern ---');
    const wraps = await page.$$('.geek-item-wrap');
    if (wraps.length > 0) {
      let targetWrap = null;
      for (const wrap of wraps) {
        const isSelected = await wrap.$eval('.geek-item', el => el.classList.contains('selected')).catch(() => false);
        if (!isSelected) { targetWrap = wrap; break; }
      }
      if (!targetWrap) targetWrap = wraps[0];
      const name = await targetWrap.$eval('.geek-name', el => (el.textContent ?? '').trim()).catch(() => 'unknown');
      console.log('Clicking on:', name);

      // Test function callback pattern (our fix)
      try {
        await targetWrap.evaluate((el) => {
          const row = el.querySelector('.geek-item') ?? el;
          row.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });
          row.click();
        });
        await new Promise(r => setTimeout(r, 1500));
        const selected = await page.evaluate(() => Array.from(document.querySelectorAll('.geek-item.selected')).map(i => i.querySelector('.geek-name')?.textContent?.trim()));
        console.log('Selected after click:', selected);
        const panel = await page.evaluate(() => ({
          hasBaseInfo: !!document.querySelector('.base-info-single-container'),
          hasMsgList: !!document.querySelector('.chat-message-list'),
          nameInPanel: document.querySelector('.base-info-single-container .name-box')?.textContent?.trim()
        }));
        console.log('Panel:', panel);
      } catch(e) {
        console.log('Chat click error:', e.message);
      }
    }

    browser.disconnect();
  } catch(e) { console.error('Error:', e.message); }
})();
