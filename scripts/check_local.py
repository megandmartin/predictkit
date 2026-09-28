#!/usr/bin/env python3
"""Repeatable local checks. Never runs live models, wallets or deployment."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true', help='Also run the connected Playwright check (optional local dependency)')
    args = parser.parse_args()
    out = ROOT / 'evidence' / 'local-2026-09-28'
    out.mkdir(parents=True, exist_ok=True)
    commands = [
        ('doctor', [sys.executable, 'predictkit.py', 'doctor']),
        ('python-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
        ('codec-tests', ['node', '--test', 'solana/tests/codec.test.mjs']),
        ('syntax-python', [sys.executable, '-m', 'compileall', '-q', 'predictkit', 'predictkit.py', 'tests', 'scripts']),
        ('syntax-studio', ['node', '--check', 'web/studio.js']),
        ('syntax-evidence', ['node', '--check', 'web/evidence-modern.js']),
        ('rehearsal', [sys.executable, 'predictkit.py', 'rehearse']),
    ]
    if args.browser:
        commands.append(('browser-connected', ['node', 'scripts/browser_connected.cjs']))
    results = []
    for name, command in commands:
        print(f'Checking {name}…', flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
            log = result.stdout + result.stderr
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            log, code = str(exc), 1
        (out / f'{name}.txt').write_text(log)
        results.append({'name': name, 'command': command, 'exit_code': code, 'passed': code == 0,
                        'log': f'evidence/local-2026-09-28/{name}.txt'})
        print(f'  {"PASS" if code == 0 else "FAIL"} — {out / (name + ".txt")}', flush=True)
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': results,
              'passed': all(r['passed'] for r in results),
              'boundary': 'Local rehearsal and fixture contracts only; no paid API, SVM, wallet, deployment or participant proof.'}
    (out / 'check-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
