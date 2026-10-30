const { chromium } = require('playwright');
const NOTES = `Priya: Quick sync on the 4.2 release.
Marcus: I'll fix the checkout bug on mobile by Friday, it's blocking the release.
Dana: I'll update the release notes by Thursday.
Priya: Sam needs to review the payment API pull request by Monday.
Priya: We decided to freeze the feature list for the 4.2 release.
Alex: I'll ask legal about the data processing addendum next week.`;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: 'raw', size: { width: 1280, height: 720 } }, colorScheme: 'light' });
  const page = await ctx.newPage();
  await page.goto('http://localhost:3000');
  await page.waitForSelector('textarea');

  const overlay = (html, full) => page.evaluate(([html, full]) => {
    let el = document.getElementById('__ov');
    if (!el) { el = document.createElement('div'); el.id = '__ov'; document.body.appendChild(el); }
    el.style.cssText = full
      ? 'position:fixed;inset:0;z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0b1220;color:#fff;font-family:Inter,system-ui,sans-serif;text-align:center;transition:opacity .4s'
      : 'position:fixed;left:0;right:0;bottom:0;z-index:99999;padding:16px 24px;background:rgba(11,18,32,.92);color:#fff;font:600 22px Inter,system-ui,sans-serif;text-align:center;pointer-events:none';
    el.innerHTML = html;
  }, [html, full]);
  const clear = () => page.evaluate(() => { const e = document.getElementById('__ov'); if (e) e.remove(); });
  const cap = (t) => overlay(t, false);
  const card = (h, s, foot = '') => overlay(`<div style="font-size:54px;font-weight:700;letter-spacing:-1px">${h}</div><div style="font-size:26px;color:#9fb3d1;margin-top:16px;max-width:900px">${s}</div><div style="font-size:18px;color:#6f86a8;margin-top:36px">${foot}</div>`, true);

  await card('Minutes → Action', 'Grounded meeting intelligence: every task traced to evidence, remembered across meetings, and actioned only with your approval.');
  await sleep(4500); await clear();

  await cap('1 · Paste a transcript or upload a PDF');
  await page.getByLabel('Meeting notes').click(); await page.keyboard.type(NOTES, { delay: 6 });
  await sleep(600);
  await cap('2 · A traced pipeline extracts tasks, owners, deadlines and priorities');
  await page.getByRole('button', { name: /Generate tasks/ }).first().click();
  await page.waitForSelector('text=Board', { timeout: 20000 });
  await page.waitForSelector('text=fix the checkout bug', { timeout: 20000 });
  await sleep(1500);
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));
  await sleep(1500);

  await cap('3 · Every task links to the exact quote it came from — unverifiable ones are flagged');
  const src = page.getByRole('button', { name: /Show source/ }).first();
  await src.scrollIntoViewIfNeeded(); await src.hover(); await src.click();
  await sleep(1200);
  const src2 = page.getByRole('button', { name: /Show source/ }).first();
  if (await src2.count()) await src2.click();
  await sleep(2500);

  await cap('4 · Ask across all your meetings — answers cite their sources');
  const ask = page.getByLabel('Question about past meetings');
  await ask.scrollIntoViewIfNeeded();
  await ask.click(); await page.keyboard.type('Who is fixing the checkout bug?', { delay: 40 });
  await page.getByRole('button', { name: 'Ask', exact: true }).click();
  await page.waitForSelector('text=/\\[1\\]/', { timeout: 15000 });
  await sleep(3500);

  await cap('5 · Overdue carry-overs, duplicates and conflicts surface automatically');
  await page.getByText('Across your meetings').scrollIntoViewIfNeeded();
  await sleep(4000);

  await cap('6 · The agent drafts follow-ups — nothing runs until you approve');
  await page.getByRole('button', { name: 'Draft follow-ups' }).click();
  await page.waitForSelector('text=Approve', { timeout: 10000 });
  await page.getByText('Agent actions').scrollIntoViewIfNeeded();
  await sleep(2500);
  await page.getByRole('button', { name: /Approve/ }).nth(1).click();
  await sleep(2500);

  await clear();
  await card('Built to be trusted', 'Grounded evidence · cited memory · human-approved actions<br>Eval harness + CI regression gate · 51 tests · prompt-injection & PII guardrails', 'FastAPI · Gemini · Next.js · TypeScript &nbsp;|&nbsp; Demo mode: offline rule-based model (swap in Gemini with one env var)');
  await sleep(5000);

  const vpath = await page.video().path();
  await ctx.close(); await browser.close();
  console.log(vpath);
})().catch(e => { console.error(e); process.exit(1); });
