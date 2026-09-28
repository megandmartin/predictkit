from __future__ import annotations
import asyncio
import copy
from datetime import datetime
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
import zipfile

from predictkit.contracts import validate_brief, safe_path, validate_result, canonical_hash, ROLES
from predictkit.providers import RehearsalProvider, render_reference_app
from predictkit.runtime import SprintEngine
from predictkit.server import make_server

ROOT = Path(__file__).resolve().parent.parent
BRIEF = json.loads((ROOT / 'examples/launchlens.json').read_text())


def wait_for(engine, expected, seconds=5):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        state = engine.snapshot()
        if state['status'] in expected:
            return state
        time.sleep(.01)
    raise AssertionError(f"Timed out: {engine.snapshot()['status']}, expected {expected}")


class ContractsTest(unittest.TestCase):
    def test_brief_valid(self):
        self.assertEqual(validate_brief(BRIEF)['network'], 'offchain-simulation')
    def test_brief_missing(self):
        with self.assertRaises(ValueError): validate_brief({})
    def test_brief_bad_template(self):
        with self.assertRaises(ValueError): validate_brief({**BRIEF,'template':'mainnet-casino'})
    def test_brief_ignores_privilege_fields(self):
        result=validate_brief({**BRIEF,'network':'mainnet','allow_payments':True})
        self.assertNotIn('allow_payments', result)
        self.assertEqual(result['network'], 'offchain-simulation')
    def test_canonical_hash(self):
        self.assertEqual(canonical_hash({'x':1,'y':2}),canonical_hash({'y':2,'x':1}))
        self.assertNotEqual(canonical_hash({'x':1}),canonical_hash({'x':2}))
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            for bad in ['../x','/etc/passwd','a/../../x','a\\b','.env','a/./b','a//../b','x\x00']:
                with self.subTest(bad=bad),self.assertRaises(ValueError): safe_path(Path(temp),bad)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError):safe_path(root,'link/file')
    def test_safe_nested_path(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(safe_path(Path(temp),'research/market.md'),Path(temp).resolve()/'research/market.md')
    def result(self):
        return {'summary':'Useful','artifacts':[{'path':'research/market.md','content':'Evidence pending'}],'limitations':['No browsing']}
    def test_valid_result(self):
        self.assertEqual(validate_result('research',self.result())['summary'],'Useful')
    def test_role_cannot_write_runtime(self):
        value=self.result();value['artifacts'][0]['path']='predictkit/runtime.py'
        with self.assertRaises(ValueError):validate_result('research',value)
    def test_missing_artifact(self):
        value=self.result();value['artifacts']=[]
        with self.assertRaises(ValueError):validate_result('research',value)
    def test_secret_rejected(self):
        value=self.result();value['artifacts'][0]['content']='sk-proj-'+('a'*35)
        with self.assertRaises(ValueError):validate_result('research',value)
    def test_size_rejected(self):
        value=self.result();value['artifacts'][0]['content']='a'*150001
        with self.assertRaises(ValueError):validate_result('research',value)
    def test_invalid_json_rejected(self):
        value={'summary':'x','limitations':[],'artifacts':[{'path':'app/market.json','content':'{broken'},{'path':'domain/resolution.md','content':'test'}]}
        with self.assertRaises(ValueError):validate_result('domain',value)
    def test_reference_escapes_input(self):
        text=render_reference_app({**BRIEF,'project_name':'<img src=x onerror=alert(1)>'})
        self.assertNotIn('<img src=x',text)
        self.assertIn('&lt;img',text)


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=SprintEngine(Path(self.temp.name),RehearsalProvider(.04))
    def tearDown(self):
        if self.engine.thread and self.engine.thread.is_alive():
            self.engine.stop();self.engine.thread.join(3)
        self.temp.cleanup()
    def test_gate_parallelism_and_pack(self):
        self.engine.start(BRIEF)
        state=wait_for(self.engine,{'awaiting_approval'})
        self.assertEqual(state['jobs']['frontend']['status'],'queued')
        starts=[datetime.fromisoformat(state['jobs'][r]['started_at']) for r in ['research','product','architect']]
        ends=[datetime.fromisoformat(state['jobs'][r]['ended_at']) for r in ['research','product','architect']]
        self.assertLess(max(starts),min(ends),'Independent jobs must overlap')
        self.engine.approve(state['brief_hash'],state['memo_hash'])
        state=wait_for(self.engine,{'packaged','failed','needs_fixes'})
        self.engine.thread.join(2)
        self.assertEqual(state['status'],'packaged')
        self.assertEqual(state['usage']['requests'],0)
        self.assertEqual(state['calls_started'],8)
        self.assertEqual(len(state['artifacts']),11)
        with zipfile.ZipFile(self.engine.directory/'submission-pack.zip') as z:
            self.assertIn('artifacts/app/index.html',z.namelist())
            manifest=json.loads(z.read('manifest.json'))
            self.assertFalse(manifest['chain_verified'])
    def test_stale_approval_rejected(self):
        self.engine.start(BRIEF);wait_for(self.engine,{'awaiting_approval'})
        with self.assertRaises(ValueError):self.engine.approve('wrong-hash')
    def test_approval_before_gate_rejected(self):
        with self.assertRaises(ValueError):self.engine.approve('none')
    def test_duplicate_start_rejected(self):
        self.engine.start(BRIEF)
        with self.assertRaises(ValueError):self.engine.start(BRIEF)
    def test_stop_at_gate(self):
        self.engine.start(BRIEF);wait_for(self.engine,{'awaiting_approval'})
        self.engine.stop();state=wait_for(self.engine,{'stopped'})
        self.assertEqual(state['jobs']['frontend']['status'],'queued')
    def test_pause_holds_build(self):
        self.engine.start(BRIEF);state=wait_for(self.engine,{'awaiting_approval'})
        self.engine.pause();self.engine.approve(state['brief_hash'],state['memo_hash']);time.sleep(.15)
        self.assertEqual(self.engine.snapshot()['jobs']['frontend']['status'],'queued')
        self.engine.resume();self.assertEqual(wait_for(self.engine,{'packaged','failed'})['status'],'packaged')
    def test_call_limit_blocks_new_wave(self):
        self.engine.max_calls=4;self.engine.start(BRIEF);state=wait_for(self.engine,{'awaiting_approval'})
        self.engine.approve(state['brief_hash'],state['memo_hash']);state=wait_for(self.engine,{'failed'})
        self.assertEqual(state['calls_started'],4)
    def test_timeout(self):
        self.engine.timeout=.001;self.engine.start(BRIEF)
        self.assertEqual(wait_for(self.engine,{'failed'})['status'],'failed')
    def test_malformed_result_rejected_before_write(self):
        class BadProvider(RehearsalProvider):
            async def run(self,role,brief,context):
                raw,usage=await super().run(role,brief,context)
                if role=='research':raw['artifacts'][0]['path']='runtime.py'
                return raw,usage
        self.engine.provider=BadProvider(.01);self.engine.start(BRIEF)
        wait_for(self.engine,{'failed'})
        self.assertFalse((self.engine.directory/'artifacts/runtime.py').exists())
        self.assertEqual(self.engine.snapshot()['jobs']['research']['status'],'failed')
    def test_concurrency_is_bounded(self):
        with self.assertRaises(ValueError):SprintEngine(Path(self.temp.name),RehearsalProvider(),concurrency=7)


class HTTPTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=make_server(0,run_root=Path(self.temp.name))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def test_health(self):
        self.assertTrue(json.load(urllib.request.urlopen(self.url+'/health'))['ok'])
    def test_post_needs_token(self):
        request=urllib.request.Request(self.url+'/api/start',data=json.dumps({'brief':BRIEF}).encode(),headers={'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(request)
        self.assertEqual(err.exception.code,403)
    def test_host_rebinding_rejected(self):
        request=urllib.request.Request(self.url+'/api/state',headers={'Host':'attacker.test'})
        with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(request)
        self.assertEqual(err.exception.code,403)
    def test_html_token_is_injected(self):
        text=urllib.request.urlopen(self.url+'/studio').read().decode()
        self.assertNotIn('__SERVER_TOKEN__',text)
        self.assertIn(self.server.session_token,text)
        self.assertIn('PredictKit',text)
    def test_export_before_run_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(urllib.request.Request(self.url+'/api/export',headers={'X-PredictKit-Token':self.server.session_token}))
        self.assertEqual(err.exception.code,400)

if __name__=='__main__':unittest.main()
