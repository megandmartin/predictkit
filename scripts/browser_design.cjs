/* Connected design QA: disposable local server, no provider/wallet calls. */
const {chromium}=require('playwright');
const {spawn,execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..'), OUT=path.join(ROOT,'.impeccable/review'), EVIDENCE=path.join(ROOT,'evidence/design-2026-09-28');
fs.mkdirSync(OUT,{recursive:true});fs.mkdirSync(EVIDENCE,{recursive:true});
const temp=fs.mkdtempSync(path.join(ROOT,'.local/design-qa-'));
const checks=[],renders=[],errors=[],external=[],failed=[];
let server,browser;
function check(name,value){assert(value,name);checks.push({name,passed:true});}
async function start(){
  server=spawn('python3',['-u','-c',"from pathlib import Path; import sys; from predictkit.server import make_server; s=make_server(0,'rehearsal',Path(sys.argv[1])); print(s.server_port,flush=True); s.serve_forever()",temp],{cwd:ROOT,stdio:['ignore','pipe','pipe']});
  return await new Promise((resolve,reject)=>{let text='',err='';const timer=setTimeout(()=>reject(Error('Server timeout '+err)),15000);server.stderr.on('data',c=>err+=c);server.stdout.on('data',c=>{text+=c;if(text.includes('\n')){clearTimeout(timer);resolve('http://127.0.0.1:'+text.trim().split('\n')[0]);}});server.on('error',reject);});
}
async function main(){
 const origin=await start();browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',acceptDownloads:true});
 const page=await context.newPage();
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))external.push(r.url());});
 page.on('response',r=>{if(r.status()>=400)failed.push({url:r.url(),status:r.status()});});
 const themes=['solana-signal','trust-layer','studio-classic'];
 const routes=[['landing','/','#hero-title','#theme'],['studio','/studio','#brief-launch','#theme'],['skills','/skills','#role-detail .role-card','#catalog-theme'],['evidence','/readiness','#refresh','#evidence-theme']];
 for(const [name,route,ready,themeSelector] of routes){
  for(const theme of themes){
   for(const width of [1440,390]){
    await page.setViewportSize({width,height:width===390?844:1000});
    const response=await page.goto(origin+route);await page.waitForSelector(ready);
    if(name==='studio')await page.waitForFunction(()=>!document.querySelector('#brief-launch').disabled);
    await page.locator(themeSelector).selectOption(theme);
    await page.reload();await page.waitForSelector(ready);
    if(name==='studio')await page.waitForFunction(()=>!document.querySelector('#brief-launch').disabled);
    await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(300);
    const layout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,space:document.fonts.check('600 24px "Space Grotesk"'),inter:document.fonts.check('400 14px Inter'),theme:document.documentElement.dataset.theme}));
    check(`${name}/${theme}/${width} loads and fits`,response.ok()&&layout.scroll<=layout.width+1&&layout.theme===theme);
    check(`${name}/${theme}/${width} uses bundled typefaces`,layout.space&&layout.inter);
    const undersized=await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(el=>el.getClientRects().length&&[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(el).fontSize)<12).map(el=>el.textContent.trim().slice(0,40)));
    check(`${name}/${theme}/${width} keeps visible text at least 12px`,undersized.length===0);
    if(name==='studio')check(`${theme}/${width} shows the complete loaded brief`,await page.locator('#brief-form textarea').evaluateAll(fields=>fields.every(field=>field.scrollHeight<=field.clientHeight+1)));
    if(name==='skills'&&width===390)check(`${theme} mobile execution options show all columns`,await page.locator('.runtime-table').evaluate(table=>table.scrollWidth<=table.clientWidth+1));
    const file=`${name}-${theme}-${width}.png`;
    if(!process.env.PREDICTKIT_REUSE_CAPTURES&&(!process.env.PREDICTKIT_CAPTURE_PAGES||process.env.PREDICTKIT_CAPTURE_PAGES.split(',').includes(name)))await page.screenshot({path:path.join(OUT,file),fullPage:true});
    renders.push({name,route,theme,width,file:'.impeccable/review/'+file,...layout});
   }
  }
 }
 await page.setViewportSize({width:1440,height:1000});await page.goto(origin+'/');
 await page.locator('#theme').selectOption('solana-signal');
 await page.locator('#probability').focus();await page.keyboard.press('End');
 check('Forecast slider responds to keyboard',await page.locator('#probability').inputValue()==='99');
 await page.locator('[data-outcome="yes"]').click();check('Illustrative YES has correct Brier score',(await page.locator('#forecast-result').textContent()).includes('0.0001'));
 await page.locator('[data-outcome="no"]').click();check('Illustrative NO has correct Brier score',(await page.locator('#forecast-result').textContent()).includes('0.9801'));
 await page.locator('[data-outcome="void"]').click();check('Illustrative VOID does not count as incorrect',/not scored|excluded|no score/i.test(await page.locator('#forecast-result').textContent()));
 await page.locator('[data-scenario="hackathon"]').click();check('Scenario picker changes the question',/hackathon|judg|demo|submission/i.test(await page.locator('#forecast-title').textContent()));
 check('Homepage labels synthetic data',await page.getByText('Synthetic data',{exact:true}).isVisible());
 const downloadPromise=page.waitForEvent('download');await page.locator('a[href="/download/source.zip"]').click();const download=await downloadPromise;
 const archive=path.join(temp,'starter.zip');await download.saveAs(archive);
 const fresh=path.join(temp,'fresh');fs.mkdirSync(fresh);
 const validation=execFileSync('python3',['-c',"import zipfile,sys,json,hashlib,pathlib; z=zipfile.ZipFile(sys.argv[1]); names=z.namelist(); assert all(not any(x in p.split('/') for x in ['.local','.git','node_modules','target','__pycache__']) for p in names); m=json.loads(z.read('PredictKit/PACKAGE_MANIFEST.json')); assert all(hashlib.sha256(z.read('PredictKit/'+n)).hexdigest()==v['sha256'] for n,v in m['files'].items()); z.extractall(sys.argv[2]); print(len(m['files']))",archive,fresh],{encoding:'utf8'}).trim();
 check('Downloaded source matches its manifest and excludes private paths',Number(validation)>100);
 const freshRoot=path.join(fresh,'PredictKit');execFileSync('python3',['predictkit.py','doctor'],{cwd:freshRoot,stdio:'pipe',timeout:20000});
 const rehearse=execFileSync('python3',['predictkit.py','rehearse'],{cwd:freshRoot,encoding:'utf8',timeout:30000});fs.writeFileSync(path.join(EVIDENCE,'fresh-download-rehearsal.txt'),rehearse);
 const rehearsalResult=JSON.parse(rehearse);
 check('Downloaded starter runs its own rehearsal without added packages',rehearsalResult.integrity_passed===true&&rehearsalResult.artifacts_checked===11&&rehearsalResult.export.endsWith('submission-pack.zip'));
 await page.goto(origin+'/skills?role=frontend');await page.waitForSelector('#role-detail .role-card');
 const token=await page.locator('meta[name="predictkit-token"]').getAttribute('content');
 const res=await fetch(origin+'/api/catalog',{headers:{'X-PredictKit-Token':token}});const catalog=await res.json();
 check('Catalog shows eight roles, eight mapped skills and two guides',catalog.roles.length===8&&catalog.skills.length===8&&catalog.operator_guides.length===2);
 for(const role of catalog.roles){await page.locator(`[data-role="${role.id}"]`).click();check(`Role ${role.id} exposes its actual output contract and assignments`,await page.locator('#role-detail h2').textContent()===role.title && await page.locator('#role-detail .role-skills details').count()===role.skills.length);}
 await page.locator('[data-role="frontend"]').click();await page.locator('#role-detail [data-source="build-prediction-ui"] summary').click();
 check('Full skill text matches the bundled file',await page.locator('[data-source="build-prediction-ui"] pre').textContent()===catalog.skills.find(s=>s.id==='build-prediction-ui').content);
 await page.locator('[data-source="role-frontend"] summary').click();check('Full role prompt is inspectable',await page.locator('[data-source="role-frontend"] pre').textContent()===catalog.roles.find(s=>s.id==='frontend').role_content);
 await page.locator('#catalog-theme').selectOption('trust-layer');await page.locator('.catalog-nav a[href="/studio"]').click();await page.waitForSelector('#brief-launch');
 check('Theme carries from catalog into Studio',await page.locator('html').getAttribute('data-theme')==='trust-layer');
 check('A single primary launch is visible in the brief header',await page.locator('#hero-actions').isHidden()&&await page.locator('#brief-launch').isVisible());
 await page.locator('[data-tab="team"]').first().click();await page.locator('[data-role="frontend"]').click();
 check('Role details link to the matching skills',await page.locator('#modal a[href="/skills?role=frontend"]').isVisible());await page.keyboard.press('Escape');
 await page.route('**/api/catalog',route=>route.abort());await page.goto(origin+'/skills');await page.waitForSelector('#catalog-error:not([hidden])');
 check('Catalog failure has a visible retry',await page.locator('#catalog-retry').isVisible());await page.unroute('**/api/catalog');await page.locator('#catalog-retry').click();await page.waitForSelector('#role-detail .role-card');
 check('Catalog retry recovers real content',await page.locator('#role-detail h2').textContent()==='App engineer');
 for(const [name,route,ready] of routes){await page.setViewportSize({width:834,height:1112});await page.goto(origin+route);await page.waitForSelector(ready);check(`${name} fits tablet`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
 check('Reduced motion preference is honored by browser',await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches));
 check('No uncaught browser errors',errors.length===0);check('No external assets requested',external.length===0);check('All normal HTTP responses succeeded',failed.length===0);
 fs.writeFileSync(path.join(EVIDENCE,'browser-design.json'),JSON.stringify({checked_at:new Date().toISOString(),browser:browser.version(),checks,renders,errors,external,failed,boundary:'Local scripted rehearsal, source catalog and design controls. No live provider, login, wallet, trading or deployed chain execution.'},null,2)+'\n');
 console.log(JSON.stringify({passed:checks.length,renders:renders.length,errors,external,failed}));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server)server.kill('SIGTERM');fs.rmSync(temp,{recursive:true,force:true});});
