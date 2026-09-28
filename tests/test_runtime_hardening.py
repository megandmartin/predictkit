"""Adversarial lifecycle and local HTTP checks for the restored original runtime."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from predictkit.contracts import canonical_hash
from predictkit.providers import RehearsalProvider
from predictkit.runtime import SprintEngine, atomic_json
from predictkit.server import make_server

ROOT = Path(__file__).resolve().parent.parent
BRIEF = json.loads((ROOT / 'examples/launchlens.json').read_text())


def wait_for(engine, expected, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        state = engine.snapshot()
        if state['status'] in expected:
            return state
        time.sleep(.01)
    raise AssertionError(engine.snapshot())


class RuntimeHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = SprintEngine(self.root, RehearsalProvider(.01))

    def tearDown(self):
        self.engine.stop()
        if self.engine.thread:
            self.engine.thread.join(5)
        self.temp.cleanup()

    def gate(self):
        self.engine.start(BRIEF)
        return wait_for(self.engine, {'awaiting_approval'})

    def finish(self):
        state = self.gate()
        self.engine.approve(state['brief_hash'], state['memo_hash'])
        state = wait_for(self.engine, {'packaged', 'failed'})
        self.engine.thread.join(3)
        self.assertEqual(state['status'], 'packaged')
        return state

    def test_rehearsal_approval_also_requires_exact_memo(self):
        state = self.gate()
        with self.assertRaises(ValueError):
            self.engine.approve(state['brief_hash'])

    def test_disk_brief_tamper_prevents_approval(self):
        state = self.gate()
        (self.engine.directory / 'brief.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.engine.approve(state['brief_hash'], state['memo_hash'])

    def test_provider_gets_isolated_brief(self):
        class MutatingProvider(RehearsalProvider):
            async def run(self, role, brief, context):
                brief['project_name'] = 'Changed by untrusted provider'
                return await super().run(role, brief, context)
        self.engine.provider = MutatingProvider(.01)
        state = self.gate()
        self.assertEqual(state['brief']['project_name'], BRIEF['project_name'])
        self.assertEqual(state['brief_hash'], canonical_hash(state['brief']))

    def test_tamper_after_approval_while_paused_prevents_build(self):
        state = self.gate()
        self.engine.pause()
        self.engine.approve(state['brief_hash'], state['memo_hash'])
        (self.engine.directory / 'artifacts/decisions/build-memo.md').write_text('Changed after approval')
        self.engine.resume()
        state = wait_for(self.engine, {'failed'})
        self.assertEqual(state['jobs']['frontend']['status'], 'queued')

    def test_artifact_read_checks_hash(self):
        self.gate()
        (self.engine.directory / 'artifacts/research/market.md').write_text('Tampered')
        with self.assertRaises(ValueError):
            self.engine.artifact('research/market.md')

    def test_export_revalidates_files(self):
        self.finish()
        self.assertTrue(self.engine.export().startswith(b'PK'))
        (self.engine.directory / 'artifacts/app/index.html').write_text('Tampered')
        with self.assertRaises(ValueError):
            self.engine.export()

    def test_export_rejects_corrupt_zip(self):
        self.finish()
        (self.engine.directory / 'submission-pack.zip').write_bytes(b'not a zip')
        with self.assertRaises(ValueError):
            self.engine.export()

    def test_inactive_resume_cannot_modify_finished_evidence(self):
        self.finish()
        before = self.engine.snapshot()
        with self.assertRaises(ValueError):
            self.engine.resume()
        self.engine.stop()  # idempotent: stopping a completed run must not corrupt it.
        self.assertEqual(before, self.engine.snapshot())

    def test_reload_preserves_completed_run_and_export(self):
        original = self.finish()
        restored = SprintEngine(self.root, RehearsalProvider())
        self.assertEqual(restored.snapshot(), original)
        self.assertEqual(restored.history()['selected_id'], original['id'])
        self.assertTrue(restored.export().startswith(b'PK'))

    def test_restart_interrupts_saved_active_state_without_dispatch(self):
        state = self.gate()
        self.engine.stop()
        self.engine.thread.join(3)
        state['status'] = 'building'
        state['jobs']['frontend']['status'] = 'running'
        atomic_json(self.engine.directory / 'state.json', state)
        restored = SprintEngine(self.root, RehearsalProvider())
        self.assertEqual(restored.snapshot()['status'], 'interrupted')
        self.assertEqual(restored.snapshot()['jobs']['frontend']['status'], 'interrupted')
        self.assertIsNone(restored.thread)
        with self.assertRaises(ValueError):
            restored.resume()

    def test_history_selection_rejects_traversal_and_active_run(self):
        state = self.gate()
        with self.assertRaises(ValueError):
            self.engine.select(state['id'])
        self.engine.stop()
        self.engine.thread.join(3)
        with self.assertRaises(ValueError):
            self.engine.select('../elsewhere')
        self.assertEqual(self.engine.select(state['id'])['id'], state['id'])

    def test_symlink_staging_cannot_escape_run(self):
        state = self.gate()
        staging = self.engine.directory / 'staging'
        # A role-specific destination that does not exist until the build wave.
        outside = self.root / 'outside'
        outside.mkdir()
        (staging / 'frontend').symlink_to(outside, target_is_directory=True)
        self.engine.approve(state['brief_hash'], state['memo_hash'])
        self.assertEqual(wait_for(self.engine, {'failed'})['status'], 'failed')
        self.assertEqual(list(outside.iterdir()), [])

    def test_corrupt_saved_job_does_not_crash_recovery(self):
        state = self.gate()
        self.engine.stop()
        self.engine.thread.join(3)
        state['jobs']['frontend'] = 'malformed'
        atomic_json(self.engine.directory / 'state.json', state)
        restored = SprintEngine(self.root, RehearsalProvider())
        self.assertEqual(restored.snapshot()['status'], 'idle')
        self.assertEqual(restored.history()['runs'], [])

    def test_stop_paused_gate_terminates_without_dispatch(self):
        self.gate()
        self.engine.pause()
        self.engine.stop()
        state = wait_for(self.engine, {'stopped'})
        self.assertEqual(state['calls_started'], 4)
        self.engine.thread.join(3)
        self.assertFalse(self.engine.thread.is_alive())


class HTTPHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = make_server(0, run_root=Path(self.temp.name))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.server.session_token

    def tearDown(self):
        self.server.engine.stop()
        if self.server.engine.thread:
            self.server.engine.thread.join(5)
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def request(self, path, headers=None, data=None):
        req = urllib.request.Request(self.url + path, data=data, headers=headers or {})
        return urllib.request.urlopen(req)

    def test_all_api_reads_require_token(self):
        for path in ('state', 'artifact?path=research/market.md', 'readiness', 'export', 'example', 'history'):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as failure:
                self.request('/api/' + path)
            self.assertEqual(failure.exception.code, 403)

    def test_authenticated_read_and_history(self):
        for path in ('state', 'readiness', 'history'):
            with self.request('/api/' + path, {'X-PredictKit-Token': self.token}) as response:
                self.assertEqual(response.status, 200)

    def test_cross_origin_get_with_token_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.request('/api/state', {'X-PredictKit-Token': self.token, 'Origin': 'https://attacker.test'})
        self.assertEqual(failure.exception.code, 403)

    def test_null_origin_post_with_token_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.request('/api/start', {'X-PredictKit-Token': self.token, 'Origin': 'null'}, b'{}')
        self.assertEqual(failure.exception.code, 403)

    def test_oversized_body_rejected_before_parse(self):
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.request('/api/start', {'X-PredictKit-Token': self.token}, b'x' * 50001)
        self.assertEqual(failure.exception.code, 400)

    def test_static_routes_do_not_serve_arbitrary_files(self):
        for path in ('/predictkit/runtime.py', '/.local/runs', '/../AGENTS.md'):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as failure:
                self.request(path)
            self.assertEqual(failure.exception.code, 404)

    def test_classic_retains_authenticated_api_and_download(self):
        with self.request('/classic') as response:
            page = response.read().decode()
        self.assertNotIn('__SERVER_TOKEN__', page)
        self.assertIn("headers:{'X-PredictKit-Token':TOKEN", page)
        self.assertNotIn("location.href='/api/export'", page)
