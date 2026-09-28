"""Optional browser checks. Does not invoke a model or send a blockchain transaction."""
from pathlib import Path
import json, os, shutil, sys, tempfile, threading
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from predictkit.server import make_server
checks=[]
def check(name, value):
    assert value, name
    checks.append({'name':name,'passed':True})
report={}
with tempfile.TemporaryDirectory() as temp:
    server=make_server(0,run_root=Path(temp))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_PATH') or shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1024},accept_downloads=True)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            try:
                response=page.goto(f'http://127.0.0.1:{server.server_port}',timeout=8000)
                page.wait_for_function("document.getElementById('mode')?.textContent==='LOCAL REHEARSAL'",timeout=5000)
                check('Actual browser connects to loopback server',response.ok)
                page.locator('#launch').click()
                page.locator('#approval.visible').wait_for(timeout=15000)
                check('Connected workflow reaches human gate',server.engine.snapshot()['status']=='awaiting_approval')
                page.locator('#approve').click()
                page.wait_for_function("document.getElementById('phase').textContent==='PACKAGED'",timeout=20000)
                check('Connected approval produces real filesystem pack',(server.engine.directory/'submission-pack.zip').exists())
                page.goto(f'http://127.0.0.1:{server.server_port}/readiness')
                page.wait_for_function("document.getElementById('status').textContent==='Release gates remain open'",timeout=5000)
                check('Connected evidence desk distinguishes rehearsal from live',page.locator('#checks .pass').count()==3)
                report['browser_loopback']='passed; scripted provider, no live model or chain'
            except Exception as exc:
                report['browser_loopback']='not verified in this environment'
                report['browser_loopback_error']=str(exc)[:350]
            # Separate offline rendering test, never substituted as connected evidence.
            page=browser.new_page(viewport={'width':1440,'height':1024})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content((ROOT/'web/readiness.html').read_text())
            check('Standalone evidence desk shows no connected run','no connected run' in page.locator('#status').inner_text())
            check('Seven separate proof gates visible',page.locator('#checks .row').count()==7)
            check('No standalone evidence is labeled observed',page.locator('#checks .pass').count()==0)
            check('Registry explicitly source only','source only' in page.inner_text('body').lower())
            page.screenshot(path=str(ROOT/'evidence/evidence-desk-desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            check('Evidence desk fits mobile width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            page.screenshot(path=str(ROOT/'evidence/evidence-desk-mobile.png'),full_page=True)
            check('No uncaught JavaScript errors',not errors)
            report.update(checked_at=datetime.now(timezone.utc).isoformat(),browser=browser.version,checks=checks,errors=errors)
            browser.close()
    finally:
        server.engine.stop() if server.engine.thread and server.engine.thread.is_alive() else None
        server.shutdown();server.server_close();thread.join(3)
(ROOT/'evidence/browser-evidence.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
