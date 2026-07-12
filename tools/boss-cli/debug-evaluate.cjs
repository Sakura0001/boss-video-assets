// Test how Puppeteer 24 handles page.evaluate with string + args
const puppeteer = require('puppeteer-core');

(async () => {
  try {
    const wsRes = await fetch('http://127.0.0.1:53470/json/version');
    const wsData = await wsRes.json();
    const browser = await puppeteer.connect({ browserWSEndpoint: wsData.webSocketDebuggerUrl });
    const page = (await browser.pages()).find(p => p.url().includes('zhipin.com'));
    if (!page) { console.log('No zhipin page'); browser.disconnect(); return; }

    // Test 1: IIFE pattern (boss list style) - should work
    console.log('--- Test IIFE pattern (what boss list uses) ---');
    const result1 = await page.evaluate(`(() => {
      const items = document.querySelectorAll('.geek-item');
      return items.length;
    })()`);
    console.log('IIFE result:', result1);

    // Test 2: Arrow function expression + args (what clickBossSidebarMenuToPath uses)
    console.log('\n--- Test Arrow function + args (what sidebar nav uses) ---');
    const result2 = await page.evaluate(`(({ label, path }) => {
      const norm = (v) => (v ?? "").replace(/\\s+/g, "");
      const links = Array.from(document.querySelectorAll(".menu-list a"));
      const target = links.find((a) => {
        const href = a.getAttribute("href") ?? "";
        if (href.includes(path)) return true;
        const text = norm(a.querySelector(".menu-item-content span")?.textContent ?? a.textContent);
        return text.includes(label);
      });
      if (!(target instanceof HTMLElement)) return false;
      target.click();
      return true;
    })`, { label: '沟通', path: '/web/chat/index' });
    console.log('Arrow+args result:', result2);
    console.log('URL after:', page.url());

    // Wait for page to settle
    await new Promise(r => setTimeout(r, 1000));

    // Test 3: IIFE with manual arg injection (fix pattern)
    console.log('\n--- Test IIFE with manual arg injection ---');
    const label3 = '推荐';
    const path3 = '/web/chat/recommend';
    const result3 = await page.evaluate(`((args) => {
      const norm = (v) => (v ?? "").replace(/\\s+/g, "");
      const links = Array.from(document.querySelectorAll(".menu-list a"));
      const target = links.find((a) => {
        const href = a.getAttribute("href") ?? "";
        if (href.includes(args.path)) return true;
        const text = norm(a.querySelector(".menu-item-content span")?.textContent ?? a.textContent);
        return text.includes(args.label);
      });
      if (!(target instanceof HTMLElement)) return false;
      target.click();
      return true;
    })(${JSON.stringify({ label: label3, path: path3 })})`);
    console.log('IIFE+injected result:', result3);
    await new Promise(r => setTimeout(r, 2000));
    console.log('URL after recommend:', page.url());

    // Go back to chat index
    await page.evaluate(`((args) => {
      const links = Array.from(document.querySelectorAll(".menu-list a"));
      const target = links.find((a) => (a.getAttribute("href") ?? "").includes(args.path));
      if (target) target.click();
    })(${JSON.stringify({ path: '/web/chat/index' })})`);
    await new Promise(r => setTimeout(r, 1000));
    console.log('URL after going back:', page.url());

    // Test 4: ElementHandle.evaluate patterns
    console.log('\n--- Test ElementHandle.evaluate patterns ---');
    const wraps = await page.$$('.geek-item-wrap');
    if (wraps.length > 0) {
      const wrap = wraps[0];
      const name = await wrap.$eval('.geek-name', el => (el.textContent ?? '').trim()).catch(() => 'unknown');
      console.log('Target:', name);

      // Pattern A: boss-cli style (string arrow function - NOT called)
      try {
        const resA = await wrap.evaluate('((el) => { el.querySelector(".geek-item").click(); return "clicked_A"; })');
        console.log('Pattern A (string arrow fn):', resA);
      } catch(e) { console.log('Pattern A error:', e.message); }

      // Pattern B: IIFE with manual element reference
      try {
        const resB = await wrap.evaluate('((el) => { el.querySelector(".geek-item")?.click(); return "clicked_B"; })(this)');
        console.log('Pattern B (IIFE with this):', resB);
      } catch(e) { console.log('Pattern B error:', e.message); }

      // Pattern C: function callback (what Puppeteer recommends)
      try {
        const resC = await wrap.evaluate((el) => {
          el.querySelector('.geek-item')?.click();
          return 'clicked_C';
        });
        console.log('Pattern C (function callback):', resC);
      } catch(e) { console.log('Pattern C error:', e.message); }

      await new Promise(r => setTimeout(r, 1000));
      const sel = await page.evaluate(() => Array.from(document.querySelectorAll('.geek-item.selected')).map(i => i.querySelector('.geek-name')?.textContent?.trim()));
      console.log('Currently selected:', sel);
    }

    browser.disconnect();
  } catch(e) { console.error('Error:', e.message); }
})();
