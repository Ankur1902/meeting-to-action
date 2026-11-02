const { chromium } = require('playwright');
const fs = require('fs');
const K = 2;                                      // slow-motion factor; output is sped back up by K
const sleep = (ms) => new Promise(r => setTimeout(r, ms * K));
const NOTES = `Priya: Quick sync on the 4.2 release.
Marcus: I'll fix the checkout bug on mobile by Friday, it's blocking the release.
Dana: I'll update the release notes by Thursday.
Priya: Sam needs to review the payment API pull request by Monday.
Priya: We decided to freeze the feature list for the 4.2 release.
Alex: I'll ask legal about the data processing addendum next week.`;

(async () => {
  const browser = await chromium.launch({ args: ['--force-device-scale-factor=1'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('http://localhost:4000/stage.html');
  await page.evaluate((k) => stage.setK(k), K);
  const app = page.frameLocator('#app');
  const frame = () => page.frames().find(f => f.url().startsWith('http://localhost:3000'));
  await app.getByLabel('Meeting notes').waitFor();
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 1500));

  // ---- capture ----
  fs.rmSync('frames', { recursive: true, force: true }); fs.mkdirSync('frames');
  const cdp = await page.context().newCDPSession(page);
  const stamps = []; let n = 0;
  cdp.on('Page.screencastFrame', async (f) => {
    const name = `frames/${String(n++).padStart(6, '0')}.jpg`;
    fs.writeFileSync(name, Buffer.from(f.data, 'base64'));
    stamps.push([name, f.metadata.timestamp]);
    try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {}
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });

  const S = (fn, ...a) => page.evaluate(([fn, a]) => stage[fn](...a), [fn, a]);
  const rect = (loc) => loc.evaluate(e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
  const pad = (r, p) => ({ x: r.x - p, y: r.y - p, w: r.w + 2 * p, h: r.h + 2 * p });
  const moveTo = async (loc, dx = 0.5, dy = 0.55) => { const r = await rect(loc); await S('cursor', r.x + r.w * dx, r.y + r.h * dy); await sleep(800); };
  const click = async (loc) => { await moveTo(loc); await S('click'); await loc.dispatchEvent('click'); await sleep(350); };
  const scrollTo = async (loc, offset = 90) => {
    await loc.evaluate((el, [offset, dur]) => new Promise(res => {
      const start = window.scrollY, end = Math.max(0, start + el.getBoundingClientRect().top - offset), t0 = performance.now();
      const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      const step = (now) => { const t = Math.min(1, (now - t0) / dur); window.scrollTo(0, start + (end - start) * ease(t)); t < 1 ? requestAnimationFrame(step) : res(); };
      requestAnimationFrame(step);
    }), [offset, 1000 * K]);
  };

  // ---- intro ----
  await sleep(300);
  await S('show', '#intro', true); await sleep(3400);
  await S('show', '#intro', false); await sleep(500);
  await S('win', true); await sleep(1300);

  // ---- 01 capture ----
  const notes = app.getByLabel('Meeting notes');
  const notesCard = notes.locator('xpath=ancestor::div[contains(@class,"bg-card")][1]');
  await S('cap', '01', 'Capture any meeting', 'Paste notes or drop in a TXT / PDF transcript');
  await S('cam', pad(await rect(notes), 30), 1.6); await moveTo(notes, 0.3, 0.3); await sleep(500);
  await S('click'); await notes.focus();
  await notes.pressSequentially(NOTES, { delay: 9 * K });
  await sleep(500);
  const gen = app.getByRole('button', { name: /Generate tasks/ }).first();
  await S('cam', pad(await rect(notesCard), 20), 1.3); await sleep(700);
  await click(gen);
  await app.getByText('ask legal about the data processing').first().waitFor({ timeout: 20000 });
  await sleep(600);

  // ---- 02 grounded extraction ----
  await S('cap', '02', 'Grounded extraction', 'Owners, deadlines and priorities, each traced to a verbatim quote');
  await S('cam', null, 1); await sleep(300);
  const board = app.getByRole('heading', { name: 'Board' });
  await scrollTo(board, 100); await sleep(300);
  const boardArea = board.locator('xpath=..');
  await S('cam', pad(await rect(boardArea), 10), 1.15); await sleep(1500);
  const firstCard = app.locator('div.border-l-4').filter({ hasText: 'fix the checkout bug on mobile' }).first();
  const show = firstCard.getByRole('button', { name: /Show source/ });
  await S('cam', pad(await rect(firstCard), 40), 2.0); await sleep(900);
  await click(show); await sleep(500);
  await S('cam', pad(await rect(firstCard), 30), 2.1); await sleep(2600);

  // ---- 03 memory ----
  await S('cam', null, 1); await sleep(400);
  const ask = app.getByLabel('Question about past meetings');
  const askCard = ask.locator('xpath=ancestor::div[contains(@class,"bg-card")][1]');
  await scrollTo(askCard, 100); await sleep(200);
  await S('cap', '03', 'Memory across every meeting', 'Ask in plain English — answers cite the meetings they came from');
  await S('cam', pad(await rect(askCard), 20), 1.75); await sleep(700);
  await click(ask); await ask.focus();
  await ask.pressSequentially('Who is fixing the checkout bug?', { delay: 45 * K });
  await sleep(300);
  await click(app.getByRole('button', { name: 'Ask', exact: true }));
  await app.getByText(/^\[1\]$/).first().waitFor({ timeout: 15000 }).catch(() => {});
  await sleep(400);
  await S('cam', pad(await rect(askCard), 20), 1.75); await sleep(3000);

  // ---- 04 insights ----
  const ins = app.getByText('Across your meetings').locator('xpath=ancestor::div[contains(@class,"bg-card")][1]');
  await S('cap', '04', 'Proactive insights', 'Overdue carry-overs and conflicting assignments surface automatically');
  await S('cam', pad(await rect(ins), 20), 1.75); await S('cursor', ...(await rect(ins).then(r => [r.x + r.w * .55, r.y + 80])));
  await sleep(3400);

  // ---- 05 agent ----
  await S('cam', null, 1); await sleep(400);
  const agentTitle = app.getByText('Agent actions (need your approval)');
  const agentCard = agentTitle.locator('xpath=ancestor::div[contains(@class,"bg-card")][1]');
  await scrollTo(agentCard, 100); await sleep(200);
  await S('cap', '05', 'Human-in-the-loop agent', 'Drafts follow-ups and GitHub issues — nothing runs until you approve');
  const draft = app.getByRole('button', { name: 'Draft follow-ups' });
  await S('cam', pad(await rect(agentCard.locator('xpath=./div[1]')), 30), 1.7); await sleep(800);
  await click(draft);
  await app.getByRole('button', { name: /Approve/ }).first().waitFor({ timeout: 10000 });
  await sleep(500);
  const issueBox = app.getByText(/^GitHub issue:/).first().locator('xpath=ancestor::div[contains(@class,"border-border")][1]');
  await S('cam', pad(await rect(issueBox), 30), 1.8); await sleep(1600);
  await click(issueBox.getByRole('button', { name: /Approve/ }));
  await sleep(400);
  await S('cam', pad(await rect(issueBox), 30), 1.8); await sleep(2200);

  // ---- outro ----
  await S('cap', '', ''); await S('cam', null, 1); await sleep(1200);
  await S('fadeWin'); await sleep(700);
  await S('show', '#outro', true); await sleep(4800);
  await S('show', '#outro', false); await sleep(600);
  await S('show', '#end', true); await sleep(4200);

  const stopAt = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  await new Promise(r => setTimeout(r, 500));
  // concat list with real timestamps, compressed by K
  const lines = [];
  for (let i = 0; i < stamps.length; i++) {
    const d = i + 1 < stamps.length ? (stamps[i + 1][1] - stamps[i][1]) / K : Math.max(1 / 30, (stopAt - stamps[i][1]) / K);
    lines.push(`file '${stamps[i][0]}'`, `duration ${Math.max(d, 0.001).toFixed(4)}`);
  }
  lines.push(`file '${stamps[stamps.length - 1][0]}'`);
  fs.writeFileSync('frames.txt', lines.join('\n'));
  const total = (stopAt - stamps[0][1]) / K;
  console.log(`frames=${stamps.length} output_seconds=${total.toFixed(1)} capture_fps=${(stamps.length / (total * K)).toFixed(1)}`);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
