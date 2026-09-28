"""Adversarial export tests: no extraction, execution, model or chain access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from predictkit.contracts import ROLES
from predictkit.providers import RehearsalProvider
from predictkit.readiness import evaluate_run, verify_pack
from predictkit.runtime import SprintEngine
from test_predictkit import BRIEF, wait_for


class ReadinessTests(unittest.TestCase):
    def live_state(self):
        return {'provider': 'openai-responses', 'jobs': {
            role: {'status': 'done', 'usage': {'provider': 'openai-responses', 'requests': 1,
                'input_tokens': 42, 'output_tokens': 80, 'response_ids': ['resp_' + role]}}
            for role in ROLES}}

    def passed(self, state, check):
        return next(c['passed'] for c in evaluate_run(state)['checks'] if c['id'] == check)

    def test_complete_unique_observations_pass_only_model_gate(self):
        state = self.live_state()
        self.assertTrue(self.passed(state, 'models'))
        self.assertFalse(evaluate_run(state)['workshop_ready'])

    def test_response_ids_cannot_be_reused_for_eight_roles(self):
        state = self.live_state()
        for job in state['jobs'].values():
            job['usage']['response_ids'] = ['resp_same']
        self.assertFalse(self.passed(state, 'models'))

    def test_missing_or_mock_usage_cannot_promote_live(self):
        for alteration in ({'provider': 'contract-test-responses'}, {'output_tokens': None},
                           {'response_ids': ['']}, {'input_tokens': True}, {'requests': 0}):
            state = self.live_state()
            state['jobs']['research']['usage'].update(alteration)
            self.assertFalse(self.passed(state, 'models'))

    def test_matching_brief_alone_cannot_approve_changed_memo(self):
        state = {'brief_hash': 'abc', 'approved_brief_hash': 'abc',
                 'memo_hash': 'current', 'approved_memo_hash': 'previous'}
        self.assertFalse(self.passed(state, 'approval'))
        state['approved_memo_hash'] = 'current'
        self.assertTrue(self.passed(state, 'approval'))


class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        engine = SprintEngine(cls.root / 'runs', RehearsalProvider(.001))
        engine.start(BRIEF)
        state = wait_for(engine, {'awaiting_approval'})
        engine.approve(state['brief_hash'], state['memo_hash'])
        wait_for(engine, {'packaged', 'failed'})
        engine.thread.join(3)
        with zipfile.ZipFile(engine.directory / 'submission-pack.zip') as archive:
            cls.original = {n: archive.read(n) for n in archive.namelist()}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def pack(self, change):
        files = copy.deepcopy(self.original)
        change(files)
        path = self.root / (self.id().split('.')[-1] + '.zip')
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return path

    @staticmethod
    def modify(files, name, operation):
        data = json.loads(files[name])
        operation(data)
        files[name] = json.dumps(data).encode()

    def test_valid_complete_pack(self):
        self.assertTrue(verify_pack(self.pack(lambda _: None))['integrity_passed'])

    def test_unlisted_executable_cannot_hide_in_pack(self):
        with self.assertRaisesRegex(ValueError, 'contents'):
            verify_pack(self.pack(lambda f: f.update({'install.sh': b'not executed'})))

    def test_empty_manifest_cannot_claim_integrity(self):
        with self.assertRaisesRegex(ValueError, 'inventory'):
            verify_pack(self.pack(lambda f: self.modify(f, 'manifest.json', lambda m: m.update(artifacts=[]))))

    def test_duplicate_manifest_artifact_rejected(self):
        def change(files):
            def edit(m): m['artifacts'][1] = m['artifacts'][0]
            self.modify(files, 'manifest.json', edit)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            verify_pack(self.pack(change))

    def test_file_size_tamper_detected(self):
        def change(files):
            def edit(m): m['artifacts'][0]['bytes'] += 1
            self.modify(files, 'manifest.json', edit)
        self.assertFalse(verify_pack(self.pack(change))['integrity_passed'])

    def test_promoted_workshop_gate_is_rejected(self):
        result = verify_pack(self.pack(lambda f: self.modify(f, 'readiness.json', lambda r: r.update(workshop_ready=True))))
        self.assertIn('readiness.json', result['mismatches'])
        self.assertFalse(result['readiness']['workshop_ready'])

    def test_state_brief_tamper_is_rejected(self):
        result = verify_pack(self.pack(lambda f: self.modify(f, 'state.json', lambda s: s.update(brief={'injected': True}))))
        self.assertIn('state.json', result['mismatches'])

    def test_approval_tamper_is_rejected(self):
        result = verify_pack(self.pack(lambda f: self.modify(f, 'state.json', lambda s: s.update(approved_memo_hash='forged'))))
        self.assertIn('approval', result['mismatches'])

    def test_event_log_tamper_is_rejected(self):
        result = verify_pack(self.pack(lambda f: f.update({'events.jsonl': b'{}\n'})))
        self.assertIn('events.jsonl', result['mismatches'])

    def test_unsafe_archive_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe ZIP'):
            verify_pack(self.pack(lambda f: f.update({'../escape': b'no'})))

    def test_malformed_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_pack(self.pack(lambda f: f.update({'manifest.json': b'[]'})))


if __name__ == '__main__':
    unittest.main()
