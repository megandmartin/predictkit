from __future__ import annotations
import asyncio
from decimal import Decimal
import importlib.metadata
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import re
import threading
import zipfile

from predictkit.http_provider import OpenAIResponsesProvider, ProviderFailure
from predictkit.spend import SpendPolicy, SpendLedger
from predictkit.skills import load_skills, ROLE_SKILLS
from predictkit.runtime import SprintEngine
from predictkit.providers import RehearsalProvider
from predictkit.readiness import evaluate_run, verify_pack
from predictkit.diagnostics import sdk_distribution_version
from predictkit.contracts import ROLES
from predictkit.server import make_server
from test_predictkit import BRIEF, wait_for


def policy(budget='10'):
    return SpendPolicy(Decimal(budget),Decimal('1'),Decimal('2'),'2026-09-28',8000)
def response_for(raw, **overrides):
    return {'id':'resp_CONTRACT_TEST_ONLY', 'status':'completed',
            'usage':{'input_tokens':200,'output_tokens':100},
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(raw)}]}], **overrides}
def raw_for(role='research'):
    return asyncio.run(RehearsalProvider(0).run(role,BRIEF,''))[0]

class BudgetTests(unittest.TestCase):
    def test_missing_prices_fail_closed(self):
        with self.assertRaises(ValueError): SpendPolicy.from_env({})
    def test_nan_negative_zero_prices_rejected(self):
        for bad in ('NaN','Infinity','0','-1'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                SpendPolicy.from_env({'PREDICTKIT_BUDGET_USD':'5','PREDICTKIT_INPUT_USD_PER_MILLION':bad,
                    'PREDICTKIT_OUTPUT_USD_PER_MILLION':'1','PREDICTKIT_PRICE_CHECKED_ON':'2026-09-28'})
    def test_budget_blocks_dispatch(self):
        ledger=SpendLedger(policy('.0001'))
        with self.assertRaises(ValueError):ledger.reserve('research',200)
        self.assertFalse(ledger.entries)
    def test_duplicate_role_cannot_spend_again(self):
        ledger=SpendLedger(policy());ledger.reserve('research',200)
        with self.assertRaises(ValueError):ledger.reserve('research',200)
    def test_unknown_billing_retains_reservation(self):
        ledger=SpendLedger(policy());ledger.reserve('research',200);before=ledger.snapshot()['charged_or_held_usd']
        ledger.mark_uncertain('research');self.assertEqual(before,ledger.snapshot()['charged_or_held_usd'])
        self.assertIn('unknown',ledger.snapshot()['entries']['research']['status'])
    def test_usage_reconciles_known_tokens(self):
        ledger=SpendLedger(policy());ledger.reserve('research',200)
        self.assertEqual(Decimal(ledger.reconcile('research',{'input_tokens':100,'output_tokens':100})),Decimal('.0003'))
    def test_token_limit_rejected(self):
        with self.assertRaises(ValueError):SpendPolicy.from_env({'PREDICTKIT_BUDGET_USD':'1','PREDICTKIT_INPUT_USD_PER_MILLION':'1','PREDICTKIT_OUTPUT_USD_PER_MILLION':'1','PREDICTKIT_PRICE_CHECKED_ON':'2026-09-28','PREDICTKIT_MAX_OUTPUT_TOKENS':'1'})

class ProviderTests(unittest.TestCase):
    def provider(self,transport):return OpenAIResponsesProvider('contract-test-model',policy(),api_key='test-key-not-real',transport=transport)
    def test_success_records_ids_usage_and_loaded_skills(self):
        provider=self.provider(lambda p,k:(response_for(raw_for()),'request_fixture'))
        raw,usage=asyncio.run(provider.run('research',BRIEF,''))
        self.assertEqual(usage['requests'],1);self.assertEqual(len(usage['skills_loaded']),2)
        self.assertEqual(usage['provider'],'contract-test-responses');self.assertEqual(usage['request_id'],'request_fixture')
    def test_payload_schema_store_and_no_tools(self):
        p=self.provider(None);payload,_,_=p.prepare('product',BRIEF,'')
        self.assertFalse(payload['store']);self.assertNotIn('tools',payload)
        self.assertTrue(payload['text']['format']['strict']);self.assertEqual(payload['max_output_tokens'],8000)
    def test_refusal_has_usage_and_no_retry(self):
        calls=[]
        def transport(p,k):
            calls.append(1);return response_for(raw_for(),output=[{'type':'message','content':[{'type':'refusal'}]}]),None
        p=self.provider(transport)
        with self.assertRaises(ProviderFailure) as e:asyncio.run(p.run('research',BRIEF,''))
        self.assertEqual(len(calls),1);self.assertEqual(e.exception.usage['requests'],1)
    def test_incomplete_response_fails(self):
        p=self.provider(lambda p,k:(response_for(raw_for(),status='incomplete'),None))
        with self.assertRaises(ProviderFailure):asyncio.run(p.run('research',BRIEF,''))
    def test_missing_usage_not_reported_as_zero(self):
        p=self.provider(lambda p,k:(response_for(raw_for(),usage=None),None))
        with self.assertRaises(ProviderFailure):asyncio.run(p.run('research',BRIEF,''))
        self.assertIn('unknown',p.ledger.snapshot()['entries']['research']['status'])
    def test_transport_failure_not_leaked_or_retried(self):
        calls=[]
        def transport(p,k):calls.append(1);raise RuntimeError('sensitive prompt secret')
        p=self.provider(transport)
        with self.assertRaises(ProviderFailure) as e:asyncio.run(p.run('research',BRIEF,''))
        self.assertNotIn('sensitive',str(e.exception));self.assertEqual(len(calls),1)
    def test_json_failure_keeps_observed_usage(self):
        p=self.provider(lambda p,k:(response_for(raw_for(),output=[{'type':'message','content':[{'type':'output_text','text':'{bad'}]}]),None))
        with self.assertRaises(ProviderFailure) as e:asyncio.run(p.run('research',BRIEF,''))
        self.assertEqual(e.exception.usage['input_tokens'],200)
    def test_budget_failure_never_reaches_transport(self):
        calls=[];p=self.provider(lambda p,k:calls.append(1));p.ledger=SpendLedger(policy('.00001'))
        with self.assertRaises(ValueError):asyncio.run(p.run('research',BRIEF,''))
        self.assertFalse(calls)

class SkillsAndDiagnosticsTests(unittest.TestCase):
    def test_each_role_has_reviewed_skills_with_hashes(self):
        for role in ROLES:
            text,records=load_skills(role);self.assertIn('REVIEWED SKILL',text)
            self.assertTrue(all(len(x['sha256'])==64 for x in records))
    def test_missing_skill_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(FileNotFoundError):load_skills('research',Path(tmp))
    def test_sdk_detection_uses_distribution_not_prompts_folder(self):
        with patch('importlib.metadata.version',side_effect=importlib.metadata.PackageNotFoundError):
            self.assertIsNone(sdk_distribution_version())

class RuntimeV2Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.engine=SprintEngine(Path(self.temp.name),RehearsalProvider(.02))
    def tearDown(self):
        if self.engine.thread and self.engine.thread.is_alive():self.engine.stop();self.engine.thread.join(5)
        self.temp.cleanup()
    def finish(self):
        self.engine.start(BRIEF);s=wait_for(self.engine,{'awaiting_approval'});self.engine.approve(s['brief_hash'],s['memo_hash'])
        s=wait_for(self.engine,{'packaged','failed','needs_fixes'});self.engine.thread.join(3);self.assertEqual(s['status'],'packaged');return s
    def test_changed_memo_cannot_be_approved(self):
        self.engine.start(BRIEF);s=wait_for(self.engine,{'awaiting_approval'})
        (self.engine.directory/'artifacts/decisions/build-memo.md').write_text('Changed')
        with self.assertRaises(ValueError):self.engine.approve(s['brief_hash'],s['memo_hash'])
    def test_wrong_memo_hash_cannot_be_approved(self):
        self.engine.start(BRIEF);s=wait_for(self.engine,{'awaiting_approval'})
        with self.assertRaises(ValueError):self.engine.approve(s['brief_hash'],'wrong')
    def test_reviewer_receives_code_and_deterministic_checks(self):
        captured={}
        class Capture(RehearsalProvider):
            async def run(self,role,brief,context):captured[role]=context;return await super().run(role,brief,context)
        self.engine.provider=Capture(.02);self.finish()
        self.assertIn('FILE app/index.html',captured['reviewer']);self.assertIn('DETERMINISTIC VERIFICATION',captured['reviewer'])
        self.assertNotIn('FILE app/index.html',captured['submission'])
    def test_parallel_wave_context_is_frozen(self):
        captured={}
        class Capture(RehearsalProvider):
            async def run(self,role,brief,context):captured[role]=context;return await super().run(role,brief,context)
        self.engine.provider=Capture(.01);self.finish()
        self.assertEqual(captured['research'],captured['product']);self.assertEqual(captured['frontend'],captured['domain'])
    def test_invalid_output_still_records_paid_usage(self):
        class Bad(RehearsalProvider):
            async def run(self,role,brief,context):
                r,u=await super().run(role,brief,context)
                if role=='research':r['artifacts'][0]['path']='unauthorized';u.update(requests=1,input_tokens=20,output_tokens=10)
                return r,u
        self.engine.provider=Bad(.01);self.engine.start(BRIEF);s=wait_for(self.engine,{'failed'})
        self.assertGreaterEqual(s['usage']['requests'],1)
    def test_export_includes_readiness_but_never_fake_chain_success(self):
        s=self.finish();report=verify_pack(self.engine.directory/'submission-pack.zip')
        self.assertTrue(report['integrity_passed']);self.assertFalse(report['readiness']['workshop_ready'])
        self.assertFalse(next(x for x in report['readiness']['checks'] if x['id']=='models')['passed'])
    def test_tampered_artifact_detected_in_export(self):
        self.finish();original=self.engine.directory/'submission-pack.zip';altered=self.engine.directory/'changed.zip'
        with zipfile.ZipFile(original) as src,zipfile.ZipFile(altered,'w') as dst:
            for name in src.namelist():dst.writestr(name,b'tampered' if name=='artifacts/app/index.html' else src.read(name))
        self.assertFalse(verify_pack(altered)['integrity_passed'])
    def test_mock_responses_can_run_whole_graph_without_live_label(self):
        def transport(payload,key):
            paths=json.loads(re.search(r'Return only complete artifacts for these exact paths: (.+)',payload['instructions'])[1])
            role=next(r for r,v in ROLES.items() if v['paths']==paths)
            time.sleep(.03);return response_for(raw_for(role)), 'request_fixture'
        self.engine.provider=OpenAIResponsesProvider('contract-test-model',policy(),api_key='fixture',transport=transport)
        s=self.finish();self.assertEqual(s['usage']['requests'],8);self.assertEqual(s['provider'],'contract-test-responses')
        self.assertFalse(next(c for c in evaluate_run(s)['checks'] if c['id']=='models')['passed'])

class HTTPV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=make_server(0,run_root=Path(self.temp.name))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.token=self.server.session_token
    def tearDown(self):self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def test_non_object_post_returns_error_not_handler_crash(self):
        req=urllib.request.Request(self.url+'/api/start',data=b'[]',headers={'X-PredictKit-Token':self.token})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,400)
    def test_readiness_is_real_empty_state_not_pretend_pass(self):
        result=json.load(urllib.request.urlopen(urllib.request.Request(self.url+'/api/readiness',headers={'X-PredictKit-Token':self.token})))
        self.assertFalse(result['workshop_ready']);self.assertTrue(all(not c['passed'] for c in result['checks']))
    def test_evidence_page_is_served(self):
        self.assertIn('Prove the run',urllib.request.urlopen(self.url+'/classic-readiness').read().decode())
