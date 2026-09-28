#!/usr/bin/env python3
"""One explicitly configured local live session; passwords never enter source files."""
import argparse
from datetime import date, datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import sys
import threading
import warnings
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from predictkit.contracts import canonical_hash, safe_path
from predictkit.http_provider import OpenAIResponsesProvider
from predictkit.spend import SpendPolicy

ENV_KEYS = {'PREDICTKIT_MODEL', 'PREDICTKIT_BUDGET_USD', 'PREDICTKIT_INPUT_USD_PER_MILLION',
            'PREDICTKIT_OUTPUT_USD_PER_MILLION', 'PREDICTKIT_PRICE_CHECKED_ON', 'PREDICTKIT_MAX_OUTPUT_TOKENS'}

def read_plan(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size > 20000:
        raise ValueError('Plan must be a small local regular file')
    plan=json.loads(path.read_text())
    if not isinstance(plan,dict) or set(plan) != {'id','approved_runs','environment','price_source','brief'}:
        raise ValueError('Unexpected live plan fields; never put an API key in a plan')
    if not isinstance(plan['id'],str) or not re.fullmatch(r'[a-z0-9-]{1,64}',plan['id']):
        raise ValueError('Invalid plan ID')
    if type(plan['approved_runs']) is not int or plan['approved_runs'] != 1:
        raise ValueError('This launcher permits exactly one approved run')
    env=plan['environment']
    if not isinstance(env,dict) or set(env)!=ENV_KEYS or not all(isinstance(v,str) for v in env.values()):
        raise ValueError('Plan must contain the exact non-secret model/spend settings')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}',env['PREDICTKIT_MODEL']):
        raise ValueError('Invalid selected model')
    policy=SpendPolicy.from_env(env)
    age=(date.today()-date.fromisoformat(policy.price_checked_on)).days
    if not 0 <= age <= 7:
        raise ValueError('Review pricing again: checked date must be within the last seven days')
    if not isinstance(plan['price_source'],str) or not plan['price_source'].startswith('https://developers.openai.com/'):
        raise ValueError('Record the official pricing source')
    from predictkit.contracts import validate_brief
    plan['brief']=validate_brief(plan['brief'])
    return plan,policy

def install_one_run_guard(provider, directory, plan):
    """Reserve one plan invocation atomically before the first provider dispatch."""
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('Authorization directory must not be symlinked')
    directory.mkdir(parents=True,exist_ok=True)
    marker=safe_path(directory,plan['id']+'.used.json')
    original=provider.begin_run
    def begin():
        record={'plan_id':plan['id'],'plan_sha256':canonical_hash(plan),
                'claimed_at':datetime.now(timezone.utc).isoformat(),
                'boundary':'One run claimed, not evidence of a successful provider response.'}
        try:
            with marker.open('x') as out:
                os.chmod(marker,0o600)
                json.dump(record,out,indent=2)
        except FileExistsError:
            raise ValueError('This one-run authorization has already been used. No automatic retry.') from None
        original()
    provider.begin_run=begin
    return marker

def prompt_key():
    if not sys.stdin.isatty():
        raise ValueError('Enter the key in a local interactive Terminal; never pipe it or put it in chat')
    with warnings.catch_warnings():
        warnings.simplefilter('error',getpass.GetPassWarning)
        key=getpass.getpass('OpenAI API key (hidden, memory only; Enter cancels): ').strip()
    if not key:raise ValueError('No key supplied; no calls made')
    return key

def preflight(plan,policy):
    provider=OpenAIResponsesProvider(plan['environment']['PREDICTKIT_MODEL'],policy,
        api_key='UNUSED-PREFLIGHT-SENTINEL',transport=lambda *_: (_ for _ in ()).throw(AssertionError('No preflight network')))
    from predictkit.contracts import ROLES
    roles=[]
    for role in ROLES:
        _,size,_=provider.prepare(role,plan['brief'],'')
        roles.append({'role':role,'request_bytes_without_upstream_artifacts':size})
    return {'kind':'local-live-preflight','model':provider.model,'spend':policy.view(),
            'price_source':plan['price_source'],'key_available_in_environment':bool(os.environ.get('OPENAI_API_KEY')),
            'roles':roles,'network_calls':0,'boundary':'Request assembly only. Later context adds input cost. Account access and model outputs unverified.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--check',action='store_true',help='Offline, no key read or network calls')
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    plan,policy=read_plan(args.plan)
    if args.check:
        print(json.dumps(preflight(plan,policy),indent=2));return
    if not 1024<=args.port<=65535:raise ValueError('Use a local port from 1024 through 65535')
    local=ROOT/'.local'
    if local.is_symlink():raise ValueError('Private runtime root must not be symlinked')
    local.mkdir(exist_ok=True)
    auth=safe_path(local,'live-authorizations');auth.mkdir(exist_ok=True)
    marker=safe_path(auth,plan['id']+'.used.json')
    if marker.exists():raise ValueError('This one-run plan was already used. Review its evidence before authorizing another.')
    print('PredictKit — one approved live sprint',flush=True)
    print('Model:',plan['environment']['PREDICTKIT_MODEL'],'| Local budget: US$'+str(policy.budget_usd),flush=True)
    print('A key enables the local server. No model call starts until Launch in Studio. Exact build memo approval remains required.',flush=True)
    key=os.environ.get('OPENAI_API_KEY','').strip() or prompt_key()
    os.environ.update(plan['environment']);os.environ['OPENAI_API_KEY']=key
    from predictkit.server import make_server
    run_root=safe_path(local,'live-runs');run_root.mkdir(exist_ok=True)
    server=make_server(args.port,'openai',run_root)
    os.environ.pop('OPENAI_API_KEY',None)
    key=None  # Provider retains its in-memory key for this server process only.
    install_one_run_guard(server.engine.provider,auth,plan)
    # Bind this authorization to the reviewed sanitized sample brief as well.
    original_start=server.engine.start
    def start(brief):
        from predictkit.contracts import validate_brief
        if canonical_hash(validate_brief(brief))!=canonical_hash(plan['brief']):
            raise ValueError('This approval covers the prepared sample brief only')
        return original_start(brief)
    server.engine.start=start
    url=f'http://127.0.0.1:{server.server_port}/studio'
    print('Ready:',url,flush=True)
    print('Keep this window open. Control-C stops the server. Never paste the key into chat.',flush=True)
    threading.Timer(.4,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:
        if server.engine.thread and server.engine.thread.is_alive():
            server.engine.stop();server.engine.thread.join(8)
    finally:server.server_close()

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,getpass.GetPassWarning) as exc:
        raise SystemExit('Live setup stopped: '+str(exc)) from None
