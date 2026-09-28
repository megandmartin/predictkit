import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
import io
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from predictkit.server import make_server

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_source',ROOT/'scripts/package_source.py')
pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)

class DesignRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.server=make_server(0,run_root=Path(cls.temp.name))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def test_public_entry_and_studio_are_distinct(self):
        home=urllib.request.urlopen(self.url).read().decode()
        studio=urllib.request.urlopen(self.url+'/studio').read().decode()
        self.assertIn('forecast-demo',home);self.assertIn('brief-form',studio)
        self.assertNotIn(self.server.session_token,home)
        self.assertIn(self.server.session_token,studio)
    def test_catalog_is_private_but_page_loads(self):
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(self.url+'/api/catalog')
        self.assertEqual(err.exception.code,403)
        req=urllib.request.Request(self.url+'/api/catalog',headers={'X-PredictKit-Token':self.server.session_token})
        data=json.load(urllib.request.urlopen(req))
        self.assertEqual(len(data['roles']),8);self.assertEqual(len(data['operator_guides']),2)
        self.assertIn('role_content',data['roles'][0])
    def test_font_files_are_real_and_paths_allowlisted(self):
        with urllib.request.urlopen(self.url+'/fonts/spacegrotesk-variable.ttf') as res:
            self.assertEqual(res.headers.get_content_type(),'font/ttf');self.assertEqual(res.read(4),b'\0\1\0\0')
        for path in ('/fonts/../../.env','/fonts/SOURCES.json','/agents/frontend.md'):
            with self.assertRaises(urllib.error.HTTPError) as err:urllib.request.urlopen(self.url+path)
            self.assertEqual(err.exception.code,404)
    def test_local_svm_viewer_is_static_and_has_no_network_permission(self):
        with urllib.request.urlopen(self.url+'/solana-demo') as res:
            body=res.read().decode()
            self.assertIn('Recorded local SVM execution',body)
            self.assertNotIn('__SERVER_TOKEN__',body)
            self.assertIn("default-src 'none'",res.headers['Content-Security-Policy'])

    def test_new_script_assets_and_csp(self):
        for path in ('/skills','/landing.js','/landing.css','/skills.js','/skills.css','/fonts.css'):
            with urllib.request.urlopen(self.url+path) as res:self.assertEqual(res.status,200)
        with urllib.request.urlopen(self.url+'/studio') as res:
            self.assertIn("frame-src 'self'",res.headers['Content-Security-Policy'])

class SourcePackage(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'README.md').write_text('Public starter')
        (self.root/'SOURCE_MANIFEST.json').write_text(json.dumps({'files':{'README.md':'baseline'}}))
    def tearDown(self):self.temp.cleanup()
    def test_extra_private_files_never_enter_archive(self):
        (self.root/'.env').write_text('PRIVATE_CANARY')
        (self.root/'private.md').write_text('PRIVATE_CANARY')
        (self.root/'.local').mkdir();(self.root/'.local/private-run.json').write_text('PRIVATE_CANARY')
        path,count=pack.package_source(self.root)
        with zipfile.ZipFile(path) as z:
            self.assertEqual(count,2)
            self.assertEqual(set(z.namelist()),{'PredictKit/README.md','PredictKit/SOURCE_MANIFEST.json','PredictKit/PACKAGE_MANIFEST.json'})
            self.assertNotIn(b'PRIVATE_CANARY',b''.join(z.read(n) for n in z.namelist()))
    def test_baseline_cannot_smuggle_private_paths(self):
        for name in ('../private.md','.local/run.json','.env','/tmp/private.md','web/../../secret'):
            (self.root/'SOURCE_MANIFEST.json').write_text(json.dumps({'files':{name:'x'}}))
            with self.assertRaises(ValueError):pack.source_paths(self.root)
    def test_symlinked_source_rejected(self):
        (self.root/'README.md').unlink();(self.root/'README.md').symlink_to('/etc/hosts')
        with self.assertRaises(ValueError):pack.source_paths(self.root)
    def test_symlinked_release_directory_rejected(self):
        (self.root/'.local').symlink_to(self.root)
        with self.assertRaises(ValueError):pack.package_source(self.root)
    def test_fresh_source_download_builds_once_for_simultaneous_requests(self):
        server=make_server(0,run_root=self.root/'runs')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('predictkit.server.ROOT',self.root):
                url=f'http://127.0.0.1:{server.server_port}/download/source.zip'
                with ThreadPoolExecutor(max_workers=3) as pool:
                    results=list(pool.map(lambda _:urllib.request.urlopen(url).read(),range(3)))
                self.assertTrue(all(result==results[0] for result in results))
                with zipfile.ZipFile(io.BytesIO(results[0])) as archive:
                    self.assertEqual(archive.read('PredictKit/README.md'),b'Public starter')
                self.assertFalse((self.root/'.local/releases/PredictKit-Local-Starter.zip.tmp').exists())
        finally:server.shutdown();server.server_close()
    def test_download_rejects_symlinked_release_parent(self):
        (self.root/'.local').symlink_to(self.root)
        server=make_server(0,run_root=self.root/'runs')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('predictkit.server.ROOT',self.root):
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/download/source.zip')
                self.assertEqual(error.exception.code,400)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
