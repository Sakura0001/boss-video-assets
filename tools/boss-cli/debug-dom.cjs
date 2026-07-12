const puppeteer = require('puppeteer-core');

(async () => {
  try {
    const wsRes = await fetch('http://127.0.0.1:53470/json/version');
    const wsData = await wsRes.json();
    const browser = await puppeteer.connect({ browserWSEndpoint: wsData.webSocketDebuggerUrl });
    const page = (await browser.pages()).find(p => p.url().includes('zhipin.com'));

    if (!page) { console.log('No zhipin page found'); browser.disconnect(); return; }
    console.log('Current URL:', page.url());

    // Get all geek-item-wrap elements
    const wraps = await page.$$('.geek-item-wrap');
    if (wraps.length === 0) { console.log('No geek-item-wrap found'); browser.disconnect(); return; }
    console.log('Found', wraps.length, 'geek-item-wrap elements');

    // Find first unselected item
    let targetWrap = null;
    for (const wrap of wraps) {
      const isSelected = await wrap.$eval('.geek-item', el => el.classList.contains('selected')).catch(() => false);
      if (!isSelected) { targetWrap = wrap; break; }
    }
    if (!targetWrap) targetWrap = wraps[0];

    const testName = await targetWrap.$eval('.geek-name', el => (el.textContent ?? '').trim()).catch(() => 'unknown');
    console.log('Testing click on:', testName);

    // Test 1: boss-cli's pattern (ElementHandle.evaluate with string expression)
    console.log('\n--- Test 1: boss-cli string pattern ---');
    try {
      const result1 = await targetWrap.evaluate('((el) => { const row = el.querySelector(".geek-item") ?? el; row.scrollIntoView({ block: "center", inline: "nearest" }); row.click(); return "clicked"; })');
      console.log('String pattern result:', result1);
    } catch(e) { console.log('String pattern error:', e.message); }

    await new Promise(r => setTimeout(r, 1500));
    const sel1 = await page.evaluate(() => Array.from(document.querySelectorAll('.geek-item.selected')).map(i => i.querySelector('.geek-name')?.textContent?.trim()));
    console.log('Selected after string pattern:', sel1);

    const panel1 = await page.evaluate(() => ({
      hasBaseInfo: !!document.querySelector('.base-info-single-container'),
      hasMsgList: !!document.querySelector('.chat-message-list'),
      nameInPanel: document.querySelector('.base-info-single-container .name-box')?.textContent?.trim()
    }));
    console.log('Panel after string pattern:', panel1);

    // Reset - deselect
    await page.evaluate(() => {
      document.querySelectorAll('.geek-item.selected').forEach(i => i.classList.remove('selected'));
    });

    // Find another unselected item
    let targetWrap2 = null;
    for (const wrap of wraps) {
      const isSelected = await wrap.$eval('.geek-item', el => el.classList.contains('selected')).catch(() => false);
      if (!isSelected) { targetWrap2 = wrap; break; }
    }
    if (!targetWrap2) { console.log('No more unselected items'); browser.disconnect(); return; }

    const testName2 = await targetWrap2.$eval('.geek-name', el => (el.textContent ?? '').trim()).catch(() => 'unknown');
    console.log('\n--- Test 2: page.evaluate function pattern ---');
    console.log('Testing click on:', testName2);

    // Test 2: page.evaluate with function + ElementHandle argument
    try {
      const result2 = await page.evaluate((el) => {
        const row = el.querySelector('.geek-item') ?? el;
        row.scrollIntoView({ block: 'center', inline: 'nearest' });
        row.click();
        return 'clicked';
      }, targetWrap2);
      console.log('Function pattern result:', result2);
    } catch(e) { console.log('Function pattern error:', e.message); }

    await new Promise(r => setTimeout(r, 1500));
    const sel2 = await page.evaluate(() => Array.from(document.querySelectorAll('.geek-item.selected')).map(i => i.querySelector('.geek-name')?.textContent?.trim()));
    console.log('Selected after function pattern:', sel2);

    const panel2 = await page.evaluate(() => ({
      hasBaseInfo: !!document.querySelector('.base-info-single-container'),
      hasMsgList: !!document.querySelector('.chat-message-list'),
      nameInPanel: document.querySelector('.base-info-single-container .name-box')?.textContent?.trim()
    }));
    console.log('Panel after function pattern:', panel2);

    // Test 3: Sidebar recommend click
    console.log('\n--- Test 3: Sidebar recommend click ---');
    const recResult = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('.menu-list a'));
      const target = links.find(a => {
        const text = (a.querySelector('.menu-item-content span')?.textContent ?? a.textContent)?.replace(/\s+/g, '').trim();
        return text.includes('推荐');
      });
      if (!target) return 'not_found';
      target.click();
      return 'clicked: ' + (target.querySelector('.menu-item-content span')?.textContent ?? target.textContent)?.trim();
    });
    console.log('Recommend click result:', recResult);

    await new Promise(r => setTimeout(r, 2000));
    console.log('URL after recommend click:', page.url());

    // Check what page looks like after recommend click
    const recPageInfo = await page.evaluate(() => ({
      hasGeekItems: !!document.querySelector('.geek-item-wrap'),
      hasMenuList: !!document.querySelector('.menu-list'),
      bodyClasses: document.body.className?.substring(0, 80),
      mainContent: document.querySelector('.main-content')?.className ?? 'no .main-content'
    }));
    console.log('Page after recommend:', recPageInfo);

    // Go back to chat index
    const backResult = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('.menu-list a'));
      const target = links.find(a => {
        const href = a.getAttribute('href') ?? '';
        return href.includes('/web/chat/index');
      });
      if (!target) return 'not_found';
      target.click();
      return 'clicked: ' + (target.querySelector('.menu-item-content span')?.textContent ?? target.textContent)?.trim();
    });
    console.log('Go back result:', backResult);

    await new Promise(r => setTimeout(r, 1500));
    console.log('URL after going back:', page.url());

    browser.disconnect();
  } catch(e) { console.error('Error:', e.message); }
})();
