"""Capability controls are runtime behavior, not merely catalog copy."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from predictkit.capabilities import profile_for
from predictkit.contracts import ROLES, canonical_hash
from predictkit.http_provider import OpenAIResponsesProvider
from predictkit.providers import RehearsalProvider
from predictkit.readiness import verify_pack
from predictkit.runtime import SprintEngine
from predictkit.skills import load_role_instructions
from test_predictkit import BRIEF, wait_for
from test_v02 import policy, response_for, raw_for

ROOT=Path(__file__).resolve().parents[1]

class CapabilityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.engine=SprintEngine(Path(self.temp.name),RehearsalProvider(.01))
    def tearDown(self):
        if self.engine.thread and self.engine.thread.is_alive():
            self.engine.stop();self.engine.thread.join(5)
        self.temp.cleanup()
    def build(self,expected='packaged'):
        self.engine.start(BRIEF)
        state=wait_for(self.engine,{'awaiting_approval','failed'})
        self.assertEqual(state['status'],'awaiting_approval')
        self.engine.approve(state['brief_hash'],state['memo_hash'])
        state=wait_for(self.engine,{'packaged','failed','needs_fixes'})
        self.engine.thread.join(3)
        self.assertEqual(state['status'],expected)
        return self.engine.snapshot()
    def test_receipts_match_real_frozen_contexts_without_claiming_skill_execution(self):
        contexts={}
        class Capture(RehearsalProvider):
            async def run(self,role,brief,context):
                contexts[role]=context
                return await super().run(role,brief,context)
        self.engine.provider=Capture(.01)
        state=self.build()
        for role,job in state['jobs'].items():
            receipt=job['capability_receipt']
            self.assertEqual(receipt['mode'],'scripted-rehearsal')
            self.assertIsNone(receipt['model']);self.assertEqual(receipt['tools'],[])
            self.assertEqual(receipt['profile_hash'],canonical_hash(profile_for(role)))
            self.assertEqual(receipt['brief_hash'],state['brief_hash'])
            self.assertEqual(receipt['context_sha256'],hashlib.sha256(contexts[role].encode()).hexdigest())
            self.assertEqual([x['path'] for x in receipt['input_artifacts']],profile_for(role)['input_paths'])
            self.assertNotIn('instruction_receipt',job['usage'])
            self.assertTrue(job['quality_report']['passed'])
        self.assertEqual(set(state['verification']['role_outputs']),set(ROLES)-{'reviewer'})
        self.assertTrue(verify_pack(self.engine.directory/'submission-pack.zip')['integrity_passed'])
    def test_invalid_market_semantics_block_entire_role_before_publication(self):
        class Changed(RehearsalProvider):
            async def run(self,role,brief,context):
                raw,usage=await super().run(role,brief,context)
                if role=='domain':
                    market=json.loads(raw['artifacts'][0]['content']);market['question']='An unapproved replacement question'
                    raw['artifacts'][0]['content']=json.dumps(market)
                    usage.update(requests=1,input_tokens=20,output_tokens=30)
                return raw,usage
        self.engine.provider=Changed(.01)
        state=self.build('failed')
        self.assertFalse(state['jobs']['domain']['quality_report']['passed'])
        self.assertEqual(state['jobs']['domain']['usage']['requests'],1)
        self.assertFalse(any(a['owner']=='domain' for a in state['artifacts']))
        self.assertFalse((self.engine.directory/'artifacts/domain/resolution.md').exists())
        self.assertEqual(state['jobs']['reviewer']['status'],'queued')
    def test_external_app_dependency_blocks_publication(self):
        class Remote(RehearsalProvider):
            async def run(self,role,brief,context):
                raw,usage=await super().run(role,brief,context)
                if role=='frontend':raw['artifacts'][0]['content']=raw['artifacts'][0]['content'].replace('</head>','<script src="https://example.invalid/widget.js"></script></head>')
                return raw,usage
        self.engine.provider=Remote(.01)
        state=self.build('failed')
        check=next(x for x in state['jobs']['frontend']['quality_report']['checks'] if x['id']=='html-resources')
        self.assertFalse(check['passed'])
        self.assertFalse((self.engine.directory/'artifacts/app/index.html').exists())
    def test_later_state_cannot_expand_discovery_inputs(self):
        self.engine.start(BRIEF);wait_for(self.engine,{'awaiting_approval'})
        self.assertEqual(self.engine._context('research'),'')
        chief=self.engine._context('chief')
        self.assertIn('FILE research/market.md',chief)
        self.assertNotIn('FILE decisions/build-memo.md',chief)
    def test_missing_required_context_fails_closed(self):
        self.engine.start(BRIEF);wait_for(self.engine,{'awaiting_approval'})
        with self.engine.lock:
            self.engine.state['artifacts']=[a for a in self.engine.state['artifacts'] if a['path']!='research/market.md']
        with self.assertRaisesRegex(ValueError,'Required role input'):
            self.engine._context('frontend')
    def test_context_tamper_is_detected_even_if_aggregate_hash_is_rewritten(self):
        self.build();source=self.engine.directory/'submission-pack.zip';altered=self.engine.directory/'changed.zip'
        with zipfile.ZipFile(source) as src:
            files={name:src.read(name) for name in src.namelist()}
        state=json.loads(files['state.json']);state['jobs']['frontend']['capability_receipt']['context_sha256']='0'*64
        manifest=json.loads(files['manifest.json'])
        manifest['capability_evidence_hash']=canonical_hash({role:{'capability_receipt':job.get('capability_receipt'),'quality_report':job.get('quality_report'),'instruction_receipt':job.get('usage',{}).get('instruction_receipt')} for role,job in state['jobs'].items()})
        files['state.json']=json.dumps(state).encode();files['manifest.json']=json.dumps(manifest).encode()
        with zipfile.ZipFile(altered,'w') as dst:
            for name,data in files.items():dst.writestr(name,data)
        result=verify_pack(altered)
        self.assertFalse(result['integrity_passed']);self.assertIn('role-receipts',result['mismatches'])
    def test_old_pack_shape_stays_readable_without_inventing_receipts(self):
        self.build();source=self.engine.directory/'submission-pack.zip';legacy=self.engine.directory/'legacy.zip'
        with zipfile.ZipFile(source) as src:files={name:src.read(name) for name in src.namelist()}
        state=json.loads(files['state.json'])
        for job in state['jobs'].values():job.pop('capability_receipt');job.pop('quality_report')
        verification=json.loads(files['verification.json']);verification.pop('role_outputs')
        state['verification']=verification;files['verification.json']=json.dumps(verification).encode()
        manifest=json.loads(files['manifest.json']);manifest.pop('capability_evidence_hash')
        files['state.json']=json.dumps(state).encode();files['manifest.json']=json.dumps(manifest).encode()
        with zipfile.ZipFile(legacy,'w') as dst:
            for name,data in files.items():dst.writestr(name,data)
        self.assertTrue(verify_pack(legacy)['integrity_passed'])
        self.assertTrue(all('capability_receipt' not in job for job in state['jobs'].values()))
    def test_pack_rejects_contradictory_receipts_and_partial_legacy_downgrade(self):
        self.build()
        with zipfile.ZipFile(self.engine.directory/'submission-pack.zip') as src:
            original={name:src.read(name) for name in src.namelist()}
        for mutation in ('provider','mode','model','kind','version','checks','report','missing-hash'):
            with self.subTest(mutation=mutation):
                files=copy.deepcopy(original);state=json.loads(files['state.json']);manifest=json.loads(files['manifest.json'])
                job=state['jobs']['frontend'];receipt=job['capability_receipt']
                if mutation in ('provider','mode','model','kind'):receipt[mutation]='fabricated'
                elif mutation=='version':receipt['version']=999
                elif mutation=='checks':job['quality_report']['checks']=[{'id':'fake','label':'Fake','passed':True}]
                elif mutation=='report':job['quality_report']['checks'][0]['detail']='Changed after verification'
                else:receipt['context_sha256']='0'*64
                if mutation=='missing-hash':manifest.pop('capability_evidence_hash')
                else:manifest['capability_evidence_hash']=canonical_hash({role:{'capability_receipt':j.get('capability_receipt'),'quality_report':j.get('quality_report'),'instruction_receipt':j.get('usage',{}).get('instruction_receipt')} for role,j in state['jobs'].items()})
                files['state.json']=json.dumps(state).encode();files['manifest.json']=json.dumps(manifest).encode()
                altered=self.engine.directory/'changed.zip'
                with zipfile.ZipFile(altered,'w') as dst:
                    for name,data in files.items():dst.writestr(name,data)
                self.assertFalse(verify_pack(altered)['integrity_passed'])

class InstructionReceiptsTests(unittest.TestCase):
    def test_receipt_hashes_the_actual_assembled_request_and_local_files(self):
        sent=[]
        def transport(payload,key):
            sent.append(copy.deepcopy(payload));return response_for(raw_for()),'request_fixture'
        provider=OpenAIResponsesProvider('contract-test-model',policy(),api_key='private-test-sentinel',transport=transport)
        _,usage=asyncio.run(provider.run('research',BRIEF,''))
        receipt=usage['instruction_receipt'];payload=sent[0]
        self.assertEqual(receipt['instructions_sha256'],hashlib.sha256(payload['instructions'].encode()).hexdigest())
        self.assertEqual(receipt['input_sha256'],hashlib.sha256(payload['input'].encode()).hexdigest())
        for record in [receipt['common'],receipt['role_prompt'],*receipt['skills'],*receipt['project_context']]:
            self.assertEqual(record['sha256'],hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest())
            self.assertIn((ROOT/record['path']).read_text(),payload['instructions'])
        self.assertIn('ROLE CAPABILITY CONTRACT',payload['instructions'])
        self.assertNotIn('private-test-sentinel',json.dumps(receipt))
        self.assertNotIn('tools',payload)
    def test_parent_symlinks_cannot_substitute_runtime_role_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'AGENTS.md').write_text('Local contract')
            shutil.copytree(ROOT/'agents',root/'actual-agents')
            (root/'agents').symlink_to(root/'actual-agents',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):load_role_instructions('research',root)
    def test_parent_symlinks_cannot_substitute_runtime_skill_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'AGENTS.md').write_text('Local contract')
            shutil.copytree(ROOT/'agents',root/'agents');shutil.copytree(ROOT/'skills',root/'skills')
            folder=root/'skills/frame-opportunity';folder.rename(root/'skills/alternate')
            folder.symlink_to(root/'skills/alternate',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):load_role_instructions('research',root)

if __name__=='__main__':unittest.main()
