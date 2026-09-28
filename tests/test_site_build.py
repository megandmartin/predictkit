"""The hosted build must stay static, reproducible and free of local secrets."""
import base64
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('site_builder', ROOT / 'scripts/build_site.py')
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value and value.startswith('/'):
                self.paths.append(urlsplit(value).path)


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / 'site'
        site.build_site(cls.output)
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def test_no_runtime_tokens_or_private_paths_including_encoded_receipt(self):
        site.validate_public_output(self.output)
        script = (self.output / 'skills.js').read_text()
        self.assertIn("fetch('/catalog.json'", script)
        self.assertNotIn('/api/', script)
        self.assertFalse((self.output / 'studio.js').exists())
    def test_private_canaries_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ('/Users/private-person/project', '__SERVER_TOKEN__', 'sk-proj-' + 'a' * 30):
                (root / 'canary.json').write_text(json.dumps({'bad': text}))
                with self.assertRaises(ValueError):
                    site.validate_public_output(root)
            (root / 'canary.json').unlink()
            encoded = base64.b64encode(b'{"program_path":"/Users/private/path"}').decode()
            (root / 'canary.html').write_text('<a href="data:application/json;base64,' + encoded + '">Receipt</a>')
            with self.assertRaises(ValueError):
                site.validate_public_output(root)
    def test_public_derivative_preserves_execution_and_discloses_redaction(self):
        source = json.loads((ROOT / 'evidence/solana-execution-2026-09-28/local-demo.json').read_text())
        public = json.loads((self.output / 'solana-demo/receipt.json').read_text())
        for name in ('transactions', 'forecasts', 'after_forecasts', 'final_account', 'program', 'program_sha256'):
            self.assertEqual(public[name], source[name])
        self.assertEqual(public['program_path'], site.PUBLIC_PROGRAM_PATH)
        self.assertRegex(public['publication']['original_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(public['publication']['redactions'])
        self.assertEqual(public['boundary'], source['boundary'])
        self.assertIn('Public receipt: one private compiler path', (self.output / 'solana-demo/index.html').read_text())
    def test_public_derivative_retains_existing_original_hash(self):
        raw = (ROOT / 'evidence/solana-execution-2026-09-28/local-demo.json').read_bytes()
        first = site.public_demo(raw)
        second = site.public_demo(json.dumps(first).encode())
        self.assertEqual(first, second)
    def test_all_internal_links_and_assets_resolve(self):
        for page in self.output.rglob('*.html'):
            parser = Links()
            parser.feed(page.read_text())
            for link in parser.paths:
                target = self.output / link.lstrip('/')
                self.assertTrue(target.is_file() or (target / 'index.html').is_file(), (page.name, link))
    def test_every_page_declares_a_real_local_favicon(self):
        self.assertTrue((self.output / 'favicon.svg').is_file())
        self.assertEqual((self.output / 'favicon.ico').read_bytes()[:6], b'\x00\x00\x01\x00\x01\x00')
        for page in self.output.rglob('*.html'):
            self.assertIn('<link rel="icon" type="image/svg+xml" href="/favicon.svg">', page.read_text())
    def test_catalog_is_source_backed_and_studio_is_explicitly_hosted(self):
        catalog = json.loads((self.output / 'catalog.json').read_text())
        self.assertEqual(len(catalog['roles']), 8)
        self.assertEqual(len(catalog['skills']), 8)
        for role in catalog['roles']:
            self.assertEqual(role['role_content'], (ROOT / role['role_path']).read_text())
        studio = (self.output / 'studio/index.html').read_text()
        self.assertIn('hosted preview', studio)
        self.assertIn('sandbox="allow-scripts"', studio)
        self.assertIn('python3 predictkit.py serve --open', studio)
        self.assertNotIn('approve_model_spend', studio)
    def test_build_manifest_matches_files_and_repeat_build_is_identical(self):
        before = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        manifest = json.loads(before['SITE_BUILD.json'])
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256(before[name]).hexdigest(), digest)
        site.build_site(self.output)
        after = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
    def test_refuses_to_replace_unmarked_directory_or_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            unmarked = Path(tmp) / 'user-files'
            unmarked.mkdir()
            (unmarked / 'keep.txt').write_text('keep')
            with self.assertRaises(ValueError):
                site.build_site(unmarked)
            link = Path(tmp) / 'linked'
            link.symlink_to(unmarked, target_is_directory=True)
            with self.assertRaises(ValueError):
                site.build_site(link)
            self.assertEqual((unmarked / 'keep.txt').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
