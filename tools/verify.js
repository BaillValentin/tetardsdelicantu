// Load the live site in an iPhone viewport and check every card image, the manifest and the service worker.
const { chromium, devices } = require('playwright');
(async () => {
  const url = process.argv[2];
  const b = await chromium.launch();
  const p = await (await b.newContext({ ...devices['iPhone 13'] })).newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  const bad = []; p.on('response', r => { if (r.status() >= 400) bad.push(r.status() + ' ' + r.url()); });
  await p.goto(url, { waitUntil: 'networkidle' });
  await p.screenshot({ path: 'candidates/live-home.png' });
  const decks = await p.locator('.deck').count();
  await p.locator('.deck').nth(3).tap(); await p.waitForTimeout(300);
  await p.screenshot({ path: 'candidates/live-front.png' });
  await p.tap('#card'); await p.waitForTimeout(700);
  await p.screenshot({ path: 'candidates/live-back.png' });
  await p.tap('#mode'); await p.waitForTimeout(1500);
  await p.screenshot({ path: 'candidates/live-grid.png' });
  await p.locator('#grid img').nth(0).tap(); await p.waitForTimeout(400);
  const viewerName = await p.textContent('#vName');
  const zoomable = await p.locator('#zoom').count();
  await p.screenshot({ path: 'candidates/live-viewer.png' });
  const gridCount = await p.locator('#grid img').count();
  const imgs = await p.evaluate(() => Promise.all(CARDS.map(c => new Promise(r => {
    const i = new Image(); i.onload = () => r([c.img, i.naturalWidth]); i.onerror = () => r([c.img, 0]); i.src = c.img; }))));
  const manifest = await p.evaluate(() => fetch('manifest.json').then(r => r.json()).then(m => m.name));
  const sw = await p.evaluate(async () => { const r = await navigator.serviceWorker.ready; return r.active.state; });
  const cached = await p.evaluate(async () => { const k = await caches.keys(); const c = await caches.open(k[0]); return (await c.keys()).length; });
  console.log(JSON.stringify({ cards: imgs.length, loaded: imgs.filter(x => x[1] > 0).length,
    broken: imgs.filter(x => !x[1]), decks, gridCount, viewerName, zoomable, manifest, sw, cached, errs, bad }, null, 1));
  await b.close();
})();
