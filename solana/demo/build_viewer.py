#!/usr/bin/env python3
"""Build an offline evidence viewer from an actual local-demo.json receipt.

From the repository root: python3 solana/demo/build_viewer.py
The output is a self-contained HTML file. It never runs a transaction or model.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def escape(value):
    return html.escape(str(value), quote=True)


def json_block(value):
    return escape(json.dumps(value, indent=2, ensure_ascii=False))


def validate(report):
    assert report['kind'] == 'compiled-program-local-demo', 'Not a compiled-program demo'
    assert report['environment'] == 'isolated-local-svm', 'Viewer requires local SVM evidence'
    assert report['public_network'] is False and report['wallet_files_read'] is False
    assert report['uses_synthetic_test_keys'] is True
    assert re.fullmatch(r'[0-9a-f]{64}', report['program_sha256'])
    assert report['question'] == report['final_account']['question']
    assert len(report['forecasts']) == 2
    assert all(type(f['probability_bps']) is int and 0 <= f['probability_bps'] <= 10000 for f in report['forecasts'])
    expected = [('create_question', True), ('submit_forecast', True), ('submit_forecast', True), ('submit_forecast', False), ('resolve_question', True)]
    assert [(t['instruction'], t['success']) for t in report['transactions']] == expected
    assert all(t['environment'] == 'isolated-local-svm' for t in report['transactions'])
    assert any('ForecastClosed' in log for log in report['transactions'][3]['logs'])
    assert report['after_forecasts']['outcome'] == 'OPEN'
    assert report['final_account']['outcome'] == 'YES'
    assert report['final_account']['forecastCount'] == '2'
    assert report['after_forecasts']['forecastCount'] == '2'


def build(source):
    raw = source.read_bytes()
    report = json.loads(raw)
    validate(report)
    digest = hashlib.sha256(raw).hexdigest()
    forecasts = ''
    for i, item in enumerate(report['forecasts'], 1):
        percent = item['probability_bps'] / 100
        forecasts += f'''<div class="forecast"><div class="forecast-heading"><span>Forecast {i}<small>YES probability</small></span><strong>{percent:g}<span>%</span></strong></div><div class="probability-track" role="img" aria-label="Forecast {i}: {percent:g} percent YES"><span style="width:{percent:g}%"></span></div><details class="forecast-account"><summary>Forecast account</summary><code>{escape(item['account'])}</code><button type="button" data-copy="{escape(item['account'])}">Copy account</button></details></div>'''
    labels = ['Create question', 'Record the first forecast', 'Record the second forecast', 'Reject a forecast after close', 'Resolve the question']
    descriptions = ['Question and resolution commitments recorded.', f"{report['forecasts'][0]['probability_bps']/100:g}% YES stored in its forecast account.", f"{report['forecasts'][1]['probability_bps']/100:g}% YES stored in its forecast account.", 'ForecastClosed returned; no third forecast was accepted.', f"Final account outcome is {report['final_account']['outcome']}."]
    transactions = ''
    for i, tx in enumerate(report['transactions']):
        state = 'accepted' if tx['success'] else 'rejected'
        status = 'Accepted' if tx['success'] else 'Expected rejection'
        transactions += f'''<details class="transaction {state}"><summary><span class="step-number">{i+1}</span><span class="step-description"><strong>{labels[i]}</strong><small>{descriptions[i]}</small></span><span class="result">{status}</span><span class="disclosure" aria-hidden="true">+</span></summary><div class="transaction-detail"><dl><div><dt>Compute units</dt><dd>{int(tx['computeUnits']):,}</dd></div><div><dt>Local signature</dt><dd><code>{escape(tx['signature'])}</code><button type="button" data-copy="{escape(tx['signature'])}">Copy signature</button></dd></div></dl><h3>Recorded program logs</h3><pre tabindex="0">{escape(chr(10).join(tx['logs']))}</pre></div></details>'''
    font = base64.b64encode((ROOT / 'web/fonts/spacegrotesk-variable.ttf').read_bytes()).decode()
    font_license = (ROOT / 'web/fonts/spacegrotesk-OFL.txt')
    if not font_license.exists():
        candidates = list((ROOT / 'web/fonts').glob('*space*OFL*'))
        if not candidates:
            candidates = list((ROOT / 'web/fonts').glob('*Space*'))
        font_license = candidates[0] if candidates else None
    license_text = font_license.read_text() if font_license and font_license.is_file() else 'Space Grotesk is distributed under the SIL Open Font License 1.1. See the project web/fonts license files.'
    values = {
        'FONT': font, 'FONT_LICENSE': escape(license_text),
        'QUESTION': escape(report['question']), 'FORECASTS': forecasts,
        'OUTCOME': escape(report['final_account']['outcome']),
        'COUNT': escape(report['final_account']['forecastCount']),
        'CLOSES': escape(report['final_account']['closesAt']),
        'RESOLVED': escape(report['final_account']['resolvedAt']),
        'TRANSACTIONS': transactions, 'PROGRAM': escape(report['program']),
        'PROGRAM_HASH': escape(report['program_sha256']),
        'QUESTION_ACCOUNT': escape(report['question_account']),
        'FINAL_ACCOUNT': json_block(report['final_account']),
        'FULL_JSON': escape(raw.decode()), 'SOURCE_HASH': digest,
        'DOWNLOAD': base64.b64encode(raw).decode(),
        'BOUNDARY': escape(report['boundary']),
    }
    output = (HERE / 'viewer.template.html').read_text()
    for key, value in values.items():
        output = output.replace('{{' + key + '}}', value)
    assert not re.search(r'\{\{[A-Z_]+\}\}', output), 'Unfilled template marker'
    (HERE / 'index.html').write_text(output)
    (HERE / 'viewer-source.json').write_text(json.dumps({'source': source.relative_to(ROOT).as_posix(), 'source_sha256': digest, 'program_sha256': report['program_sha256'], 'output': 'solana/demo/index.html', 'boundary': 'Static presentation of a recorded local SVM execution; no new execution.'}, indent=2) + '\n')
    print(json.dumps({'output': str(HERE / 'index.html'), 'source_sha256': digest, 'transactions': len(report['transactions'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'evidence/solana-execution-2026-09-28/local-demo.json')
    args = parser.parse_args()
    build(args.source.resolve())
