#!/usr/bin/env python3
"""PredictKit local launcher, Python 3.11+. No Python packages required."""
import argparse
import json
import sys
import time
import threading
import webbrowser
import zipfile
from pathlib import Path

if sys.version_info < (3, 11):
    raise SystemExit('PredictKit requires Python 3.11 or newer')
ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description='PredictKit local sprint')
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve', help='Start the local dashboard; model calls need per-run approval')
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--provider', choices=['rehearsal','openai'], default='rehearsal')
    serve.add_argument('--open', action='store_true', help='Open the local Studio in your browser')
    sub.add_parser('doctor', help='Local prerequisite checks; no network requests')
    capabilities = sub.add_parser('capabilities', help='Inspect packaged role capabilities and checks; no model calls')
    capabilities.add_argument('role', nargs='?', help='Role ID; omit for the complete source-backed catalog')
    rehearsal = sub.add_parser('rehearse', help='Automated SCRIPTED end-to-end smoke run; zero paid calls')
    rehearsal.add_argument('--out', type=Path, default=ROOT / '.local/rehearsals')
    verify = sub.add_parser('verify-pack', help='Check exported ZIP hashes without extracting/executing')
    verify.add_argument('path', type=Path)
    args = parser.parse_args()
    if args.command == 'doctor':
        from predictkit.diagnostics import environment_report
        print(json.dumps(environment_report(), indent=2)); return
    if args.command == 'capabilities':
        from predictkit.catalog import build_catalog
        catalog = build_catalog()
        if args.role:
            selected = next((role for role in catalog['roles'] if role['id'] == args.role), None)
            if selected is None:parser.exit(2, 'Unknown role. Choose: ' + ', '.join(r['id'] for r in catalog['roles']) + '\n')
            print(json.dumps(selected, indent=2))
        else:
            print(json.dumps(catalog, indent=2))
        return
    if args.command == 'verify-pack':
        from predictkit.readiness import verify_pack
        try:
            report = verify_pack(args.path)
        except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
            parser.exit(2, f'Pack rejected: {exc}\n')
        print(json.dumps(report, indent=2))
        if not report['integrity_passed']: raise SystemExit(1)
        return
    if args.command == 'rehearse':
        from predictkit.runtime import SprintEngine
        from predictkit.providers import RehearsalProvider
        from predictkit.readiness import verify_pack
        engine = SprintEngine(args.out, RehearsalProvider(.02))
        engine.start(json.loads((ROOT/'examples/launchlens.json').read_text()))
        end = time.monotonic()+30
        while time.monotonic()<end:
            state=engine.snapshot()
            if state['status']=='awaiting_approval':
                # Allowed only in this fixture-only command. No live provider option exists.
                engine.approve(state['brief_hash'],state['memo_hash'])
            if state['status'] in ('packaged','failed','needs_fixes','stopped'):break
            time.sleep(.02)
        else:
            engine.stop()
        engine.thread.join(5)
        if engine.snapshot()['status']!='packaged':raise SystemExit('Rehearsal failed; inspect local events')
        report = verify_pack(engine.directory/'submission-pack.zip')
        print(json.dumps({'mode':'SCRIPTED REHEARSAL, NOT AI OR CHAIN EXECUTION',
                          'export':str(engine.directory/'submission-pack.zip'), **report},indent=2));return
    from predictkit.server import make_server
    try:
        server=make_server(args.port,args.provider)
    except (ValueError,OSError) as exc:parser.exit(2,f'Cannot start: {exc}\n')
    print(f'PredictKit → http://127.0.0.1:{server.server_port}')
    print(f'Mode: {args.provider}. Loopback only. Ctrl-C stops the server.')
    if args.open:
        threading.Timer(.5, lambda: webbrowser.open(f'http://127.0.0.1:{server.server_port}')).start()
    try:server.serve_forever()
    except KeyboardInterrupt:
        if server.engine.thread and server.engine.thread.is_alive():
            server.engine.stop();server.engine.thread.join(timeout=8)
    finally:server.server_close()

if __name__=='__main__':main()
