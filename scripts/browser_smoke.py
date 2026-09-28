"""Optional, no-network browser smoke test of the standalone UI and reference apps.
Needs Playwright and Chromium. HTML is loaded with set_content so this test can
run in environments whose browser policy blocks file:// and loopback navigation.
The production files are not rewritten. Backend HTTP behavior is covered by
unit tests, not this browser test. No live models or blockchain are involved.
"""
from pathlib import Path
import json
import os
import shutil
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence'
checks, errors = [], []
def check(name, value):
    assert value, name
    checks.append({'name': name, 'passed': True})

with sync_playwright() as p:
    executable = os.getenv('CHROMIUM_PATH') or shutil.which('chromium')
    browser = p.chromium.launch(headless=True, executable_path=executable, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((ROOT / 'web/dashboard.html').read_text())
    check('Standalone UI identifies preview mode', page.locator('#mode').inner_text() == 'INTERACTIVE PREVIEW')
    page.screenshot(path=str(EVIDENCE / 'studio-desktop.png'), full_page=True)
    page.locator('#edit-brief').click()
    check('Brief navigation and loaded example', page.locator('#field-project_name').input_value() == 'LaunchLens')
    page.locator('#brief-launch').click()
    page.locator('#approval.visible').wait_for(timeout=15000)
    check('Preview pauses at human approval', page.locator('#phase').inner_text() == 'AWAITING APPROVAL')
    page.locator('#review-memo').click()
    check('Build memo viewer is readable', 'LaunchLens' in page.locator('#modalbody').inner_text())
    page.locator('#modal-close').click()
    page.screenshot(path=str(EVIDENCE / 'studio-approval.png'), full_page=True)
    page.locator('#approve').click()
    page.wait_for_function("document.getElementById('phase').textContent==='PACKAGED'", timeout=20000)
    check('Eight scripted roles complete', page.locator('#completed').inner_text() == '8 / 8')
    page.locator('.navbutton[data-tab="workbench"]').click()
    check('Eleven preview artifacts listed', page.locator('[data-file]').count() == 11)
    page.locator('[data-file="app/market.json"]').click()
    check('File viewer labels simulated output', 'SCRIPTED PREVIEW' in page.locator('#modalbody').inner_text())
    page.locator('#modal-close').click()
    page.locator('#preview-app').click()
    frame = page.frame_locator('#modalbody iframe')
    frame.locator('#submit').click()
    check('Isolated app records forecast', '1 forecasts' in frame.locator('#aggregate').inner_text())
    frame.locator('[data-view="resolve"]').click()
    check('Cannot resolve before closing', frame.locator('#yes').is_disabled())
    frame.locator('#close').click()
    frame.locator('#yes').click()
    check('Reference app resolves after closing', 'YES' in frame.locator('#outcome').inner_text())
    frame.locator('[data-view="explore"]').click()
    check('Reference app computes Brier score', '0.1225' in frame.locator('#calibration').inner_text())
    page.screenshot(path=str(EVIDENCE / 'studio-app-preview.png'), full_page=True)
    page.locator('#modal-close').click()
    page.locator('.navbutton[data-tab="submission"]').click()
    check('Offline export explicitly says preview state', 'preview state' in page.locator('#export').inner_text())
    with page.expect_download() as download_info:
        page.locator('#export').click()
    check('Preview download is JSON, not a claimed app pack', download_info.value.suggested_filename == 'predictkit-preview-state.json')
    page.locator('.navbutton[data-tab="log"]').click()
    check('Preview run history visible', 'sprint / finished' in page.locator('#full-log').inner_text())
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('.navbutton[data-tab="team"]').click()
    page.screenshot(path=str(EVIDENCE / 'studio-mobile.png'), full_page=True)
    check('Mobile has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
    for name, initial in [('forecast-studio', 'forecast'), ('market-explorer', 'explore'), ('resolution-desk', 'resolve')]:
        page.set_content((ROOT / f'examples/{name}.html').read_text())
        check(f'{name} opens intended local view', page.locator(f'#{initial}').is_visible())
    check('No uncaught page JavaScript errors', not errors)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'browser': browser.version,
              'mode': 'scripted-preview-rendered-via-set-content', 'checks': checks, 'page_errors': errors,
              'not_tested': ['Browser file:// navigation (blocked by environment policy)',
                'Browser-to-loopback HTTP navigation (blocked by environment policy; HTTP unit tests passed separately)',
                'Live model execution', 'Solana RPC or transactions', 'Production security', 'Safari and Firefox']}
    (EVIDENCE / 'browser-smoke.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    browser.close()
