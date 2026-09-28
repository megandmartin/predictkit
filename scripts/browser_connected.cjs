/* Actual loopback browser QA. Creates its own rehearsal-only server and temporary
   run directory; never touches a user's run or reads credentials. Requires Playwright. */
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'output/playwright');
const EVIDENCE = path.resolve(process.env.PREDICTKIT_EVIDENCE_DIR || path.join(ROOT, 'evidence/local-2026-09-28'));
for (const dir of [OUT, EVIDENCE, path.join(ROOT, '.local')]) fs.mkdirSync(dir, { recursive: true });
const runRoot = fs.mkdtempSync(path.join(ROOT, '.local/browser-qa-'));
const checks = [], errors = [], externalRequests = [];
const check = (name, condition) => { assert(condition, name); checks.push({ name, passed: true }); };
let server, browser;
async function startServer() {
  const code = "from pathlib import Path; import sys; from predictkit.server import make_server; s=make_server(0, 'rehearsal', Path(sys.argv[1])); print(s.server_port,flush=True); s.serve_forever()";
  server = spawn(process.env.PREDICTKIT_PYTHON || 'python3', ['-u', '-c', code, runRoot], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
  return await new Promise((resolve, reject) => {
    let output = '', stderr = '';
    const timer = setTimeout(() => reject(Error('Local test server did not start')), 15000);
    server.stderr.on('data', c => stderr += c);
    server.on('error', e => { clearTimeout(timer); reject(e); });
    server.on('exit', code => { if (!output.includes('\n')) { clearTimeout(timer); reject(Error('Server failed: ' + stderr)); } });
    server.stdout.on('data', chunk => {
      output += chunk;
      if (/^\d+\n/.test(output)) { clearTimeout(timer); resolve('http://127.0.0.1:' + output.trim().split('\n')[0]); }
    });
  });
}
async function main() {
  const origin = await startServer();
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', req => { if (/^https?:/.test(req.url()) && !req.url().startsWith(origin + '/')) externalRequests.push(req.url()); });
  const response = await page.goto(origin + '/studio');
  await page.waitForFunction(() => !document.querySelector('#brief-launch').disabled);
  const token = await page.locator('meta[name="predictkit-token"]').getAttribute('content');
  const api = async (route, data) => {
    const result = await fetch(origin + route, { method: data ? 'POST' : 'GET', headers: { 'X-PredictKit-Token': token, ...(data ? { 'Content-Type': 'application/json' } : {}) }, ...(data ? { body: JSON.stringify(data) } : {}) });
    const value = await result.json();
    if (!result.ok) throw Error(value.error || result.status);
    return value;
  };
  check('Actual browser connects to loopback Studio', response.ok());
  check('Explicit rehearsal mode with no configured live provider', (await api('/api/state')).server_provider === 'rehearsal');
  check('Private API rejects unauthenticated reads', (await fetch(origin + '/api/state')).status === 403);
  check('Initial app fits desktop viewport', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(OUT, 'studio-desktop.png'), fullPage: true });
  await page.locator('#field-project_name').fill('Signal Lab');
  await page.locator('#field-market_question').fill('Will our public test build pass its review by 8 October 2026?');
  await page.reload();
  await page.waitForFunction(() => !document.querySelector('#brief-launch').disabled);
  check('Editable founder draft survives reload', await page.locator('#field-project_name').inputValue() === 'Signal Lab');
  await page.locator('#brief-launch').click();
  await page.locator('#approval').waitFor({ state: 'visible', timeout: 15000 });
  let state = await api('/api/state');
  check('Server pauses build for founder approval', state.status === 'awaiting_approval' && state.jobs.frontend.status === 'queued');
  check('Three discovery tasks really overlap', Math.max(...['research','product','architect'].map(r=>Date.parse(state.jobs[r].started_at))) < Math.min(...['research','product','architect'].map(r=>Date.parse(state.jobs[r].ended_at))));
  await page.screenshot({ path: path.join(OUT, 'studio-team-approval.png'), fullPage: true });
  await page.locator('#approve').click();
  await page.locator('#memo-confirm').waitFor();
  check('Approval displays personalized exact memo', (await page.locator('#modalbody').innerText()).includes('Signal Lab'));
  check('Approval requires explicit review checkbox', await page.locator('#memo-submit').isDisabled());
  await page.keyboard.press('Escape');
  check('Escape closes dialog and restores initiating focus', await page.locator('#approve').evaluate(e=>document.activeElement===e));
  await page.locator('#approve').click();
  await page.locator('#memo-confirm').check();
  await page.locator('#memo-submit').click();
  await page.waitForFunction(() => document.querySelector('#phase').textContent.toLowerCase() === 'packaged', { timeout: 20000 });
  state = await api('/api/state');
  check('Full eight-role graph completes with eleven accepted artifacts', Object.values(state.jobs).every(j=>j.status==='done') && state.artifacts.length === 11);
  check('Rehearsal never reports paid model requests', state.usage.requests === 0);
  check('Exact brief and memo approval persisted', state.approved_brief_hash === state.brief_hash && state.approved_memo_hash === state.memo_hash);
  await page.locator('.nav-button[data-tab="workbench"], .navbutton[data-tab="workbench"], nav [data-tab="workbench"]').first().click();
  await page.locator('#preview-app').click();
  const frame = page.frameLocator('#modalbody iframe');
  await frame.locator('#submit').waitFor();
  check('Generated application uses the custom founder brief', (await frame.locator('h1').innerText()).includes('public test build'));
  check('Preview has no same-origin privilege', await page.locator('#modalbody iframe').getAttribute('sandbox') === 'allow-scripts');
  await frame.locator('#slider').fill('70');
  await frame.locator('#slider').dispatchEvent('input');
  await frame.locator('#submit').click();
  check('Forecast accepted inside generated app', (await frame.locator('#notice').innerText()).includes('recorded'));
  await frame.locator('[data-view="resolve"]').click();
  check('Resolving before close is disabled', await frame.locator('#yes').isDisabled());
  await frame.locator('#close').click();
  await frame.locator('#yes').click();
  check('Outcome locks repeat resolution', await frame.locator('#yes').isDisabled() && (await frame.locator('#outcome').innerText()).includes('YES'));
  await frame.locator('[data-view="explore"]').click();
  check('Brier score calculated for known 70 percent YES forecast', (await frame.locator('#calibration').innerText()).includes('0.0900'));
  await page.screenshot({ path: path.join(OUT, 'generated-app.png'), fullPage: false });
  await page.locator('#modal-close').click();
  for (const outcome of ['no', 'void']) {
    await page.locator('#preview-app').click();
    await frame.locator('#submit').waitFor();
    await frame.locator('#submit').click();
    await frame.locator('[data-view="resolve"]').click();
    await frame.locator('#close').click();
    await frame.locator('#' + outcome).click();
    await frame.locator('[data-view="explore"]').click();
    const score = await frame.locator('#calibration').innerText();
    check(outcome === 'void' ? 'VOID excludes forecasts from calibration' : 'NO has the expected calibration score', outcome === 'void' ? score.includes('excluded') : score.includes('0.4225'));
    await page.locator('#modal-close').click();
  }
  await page.locator('nav [data-tab="submission"]').click();
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#export').click();
  const download = await downloadPromise;
  const packPath = path.join(runRoot, 'browser-export.zip');
  await download.saveAs(packPath);
  const verification = JSON.parse(execFileSync(process.env.PREDICTKIT_PYTHON || 'python3', ['predictkit.py', 'verify-pack', packPath], { cwd: ROOT, encoding: 'utf8' }));
  check('Browser-exported ZIP passes whole-pack verification', verification.integrity_passed && verification.artifacts_checked === 11);
  check('Rehearsal export never claims workshop readiness', !verification.readiness.workshop_ready);
  await page.locator('#history').click();
  await page.locator('[data-run]').first().waitFor();
  check('Saved-run history names real project', (await page.locator('#modalbody').innerText()).includes('Signal Lab'));
  await page.locator('#modal-close').click();
  await page.goto(origin + '/readiness');
  await page.waitForFunction(() => document.querySelector('#checks')?.textContent.includes('Static artifact'));
  check('Evidence Desk loads from same connected runtime', (await page.locator('#checks').innerText()).includes('Founder'));
  await page.screenshot({ path: path.join(OUT, 'evidence-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  check('Evidence Desk fits 390px mobile', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: path.join(OUT, 'evidence-mobile.png'), fullPage: true });
  await page.goto(origin + '/studio');
  await page.waitForFunction(() => document.querySelector('#mode')?.textContent.includes('rehearsal'));
  check('Reload restores real run and artifacts', (await page.locator('#crumb').innerText()).includes('Signal Lab'));
  await page.screenshot({ path: path.join(OUT, 'studio-mobile.png'), fullPage: true });
  check('Connected workbench fits 390px mobile', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  for (const theme of ['solana-signal','trust-layer','studio-classic']) {
    await page.locator('#theme').selectOption(theme);
    check('Theme ' + theme + ' preserves state and layout', await page.evaluate(t => document.documentElement.dataset.theme === t && document.documentElement.scrollWidth <= innerWidth, theme));
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('#theme').selectOption('trust-layer');
  await page.waitForTimeout(350); // Allow the documented 160ms theme transitions to settle before visual capture.
  await page.screenshot({ path: path.join(OUT, 'studio-light.png'), fullPage: true });
  await page.locator('#theme').selectOption('solana-signal');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  check('Reduced-motion preference is available to code-based artwork', await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches));
  check('Core Studio requires no raster images', await page.locator('img').count() === 0);
  await context.setOffline(true);
  await page.waitForFunction(() => document.querySelector('#retry-connection')?.hidden === false, { timeout: 8000 });
  check('Lost connection exposes recovery and blocks new runs', await page.locator('#launch').isDisabled());
  await context.setOffline(false);
  await page.locator('#retry-connection').click();
  await page.waitForFunction(() => document.querySelector('#mode').textContent.includes('rehearsal'));
  check('Connection recovers without silently starting another run', (await api('/api/state')).id === state.id);
  await page.locator('nav [data-tab="brief"]').click();
  await page.locator('#brief-launch').click();
  await page.locator('#approval').waitFor({ state: 'visible', timeout: 15000 });
  const newState = await api('/api/state');
  check('Same-brief second run has a distinct identity without approval', newState.id !== state.id && !newState.approved_memo_hash);
  await page.locator('nav [data-tab="submission"]').click();
  check('Prior run approval cannot leak into second-run display', await page.locator('#submission-checks .check').filter({has: page.getByRole('heading', { name: 'Exact build approval', exact: true })}).evaluate(e=>!e.classList.contains('pass')));
  await page.locator('nav [data-tab="workbench"]').click();
  check('Prior static check results cannot leak into second run', await page.locator('#checks .check.pass').count() === 0);
  await api('/api/stop', {});
  await page.goto(origin + '/classic');
  await page.waitForFunction(() => document.querySelector('#mode')?.textContent === 'LOCAL REHEARSAL');
  check('Original Studio remains connected at /classic', true);
  check('No uncaught browser errors', errors.length === 0);
  check('No external assets or telemetry requested', externalRequests.length === 0);
  const report = { checked_at: new Date().toISOString(), browser: browser.version(), method: 'Real browser navigation to temporary loopback Python server', checks, errors, externalRequests, boundary: 'Scripted provider and reference app only. No authenticated model run, wallet, Solana transaction or participant validation.' };
  fs.writeFileSync(path.join(EVIDENCE, 'browser-connected.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
}
main().catch(error => {
  fs.writeFileSync(path.join(EVIDENCE, 'browser-failure.json'), JSON.stringify({ checked_at: new Date().toISOString(), checks, errors, failure: String(error.stack || error) }, null, 2));
  console.error(error); process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (server && server.exitCode === null) { server.kill('SIGTERM'); await new Promise(r=>server.once('exit',r)); }
  fs.rmSync(runRoot, { recursive: true, force: true });
});
