"""Offline checks for the opt-in, one-run local launcher. Never contact a provider."""
import concurrent.futures
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from predictkit.http_provider import OpenAIResponsesProvider
from test_v02 import policy
from test_predictkit import BRIEF
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('live_session',ROOT/'scripts/live_session.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)

def plan():
    return {'id':'fixture-one-run','approved_runs':1,'environment':{
        'PREDICTKIT_MODEL':'contract-test-model','PREDICTKIT_BUDGET_USD':'5',
        'PREDICTKIT_INPUT_USD_PER_MILLION':'2.5','PREDICTKIT_OUTPUT_USD_PER_MILLION':'10',
        'PREDICTKIT_PRICE_CHECKED_ON':date.today().isoformat(),'PREDICTKIT_MAX_OUTPUT_TOKENS':'12000'},
        'price_source':'https://developers.openai.com/api/docs/pricing','brief':BRIEF}

class LiveSetupTests(unittest.TestCase):
    def load(self,value):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';p.write_text(json.dumps(value));return live.read_plan(p)
    def test_private_plan_requires_exact_nonsecret_fields(self):
        value=plan();self.assertEqual(self.load(value)[1].budget_usd,5)
        for place in ('root','environment'):
            value=plan();(value if place=='root' else value['environment'])['OPENAI_API_KEY']='sentinel'
            with self.subTest(place=place),self.assertRaises(ValueError):self.load(value)
    def test_invalid_budget_old_prices_and_extra_runs_reject(self):
        for field,value in [('PREDICTKIT_BUDGET_USD','NaN'),('PREDICTKIT_PRICE_CHECKED_ON',(date.today()-timedelta(days=8)).isoformat()),('PREDICTKIT_MAX_OUTPUT_TOKENS','20000')]:
            data=plan();data['environment'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.load(data)
        for n in (0,2,True):
            data=plan();data['approved_runs']=n
            with self.assertRaises(ValueError):self.load(data)
    def test_preflight_never_calls_transport_or_reads_key_value_into_report(self):
        data,p=self.load(plan())
        with patch.dict('os.environ',{'OPENAI_API_KEY':'private-sentinel'}),patch('predictkit.http_provider.post_response',side_effect=AssertionError('network')):
            report=live.preflight(data,p)
        self.assertEqual(report['network_calls'],0);self.assertEqual(len(report['roles']),8)
        self.assertNotIn('private-sentinel',json.dumps(report))
    def test_one_run_guard_survives_recreated_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=OpenAIResponsesProvider('fixture',policy(),api_key='unused',transport=lambda *_:None)
            second=OpenAIResponsesProvider('fixture',policy(),api_key='unused',transport=lambda *_:None)
            live.install_one_run_guard(first,Path(tmp),plan());live.install_one_run_guard(second,Path(tmp),plan())
            first.begin_run()
            with self.assertRaisesRegex(ValueError,'already been used'):first.begin_run()
            with self.assertRaisesRegex(ValueError,'already been used'):second.begin_run()
            self.assertNotIn('unused',(Path(tmp)/'fixture-one-run.used.json').read_text())
    def test_atomic_guard_allows_only_one_concurrent_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            def claim(_):
                p=OpenAIResponsesProvider('fixture',policy(),api_key='unused',transport=lambda *_:None)
                live.install_one_run_guard(p,Path(tmp),plan())
                try:p.begin_run();return True
                except ValueError:return False
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                self.assertEqual(sum(executor.map(claim,range(4))),1)
    def test_auth_symlink_and_path_traversal_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=OpenAIResponsesProvider('fixture',policy(),api_key='unused',transport=lambda *_:None)
            dest=Path(tmp)/'actual';dest.mkdir();link=Path(tmp)/'link';link.symlink_to(dest,target_is_directory=True)
            with self.assertRaises(ValueError):live.install_one_run_guard(p,link,plan())
            data=plan();data['id']='../escape'
            with self.assertRaises(ValueError):self.load(data)
    def test_password_prompt_refuses_noninteractive_echo_fallback(self):
        with patch.object(live.sys.stdin,'isatty',return_value=False),patch.object(live.getpass,'getpass') as prompt:
            with self.assertRaises(ValueError):live.prompt_key()
            prompt.assert_not_called()
    def test_payload_pins_standard_service_tier(self):
        p=OpenAIResponsesProvider('fixture',policy(),api_key='unused',transport=lambda *_:None)
        payload,_,_=p.prepare('frontend',BRIEF,'')
        self.assertEqual(payload['service_tier'],'default')
        self.assertFalse(payload['store']);self.assertNotIn('tools',payload)

if __name__=='__main__':unittest.main()
