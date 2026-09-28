#!/usr/bin/env python3
"""Build the public, static PredictKit preview with Python's standard library.

No credentials, private runs, installed packages or runtime endpoints are copied.
Run from the repository root: python3 scripts/build_site.py
"""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from predictkit.catalog import build_catalog
from predictkit.providers import render_reference_app

GITHUB = 'https://github.com/megandmartin/predictkit'
DOWNLOAD = GITHUB + '/archive/refs/heads/main.zip'
PUBLIC_PROGRAM_PATH = 'solana/target/sbpfv3-solana-solana/release/predictkit_registry.so'
ASSETS = ('fonts.css', 'landing.css', 'landing.js', 'studio.css', 'skills.css',
          'fonts/spacegrotesk-variable.ttf', 'fonts/inter-variable.ttf',
          'fonts/spacegrotesk-OFL.txt', 'fonts/inter-OFL.txt', 'fonts/SOURCES.json')
FORBIDDEN = (b'/Users/', b'/home/', b'__SERVER_TOKEN__', b'X-PredictKit-Token',
             b'127.0.0.1:8765', b'localhost:8765')


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError('Hosted source adaptation no longer matches: ' + old[:70])
    return text.replace(old, new)


def public_demo(raw: bytes) -> dict:
    """Preserve transactions/account data and disclose the sole path redaction."""
    report = json.loads(raw)
    before = copy.deepcopy((report['transactions'], report['forecasts'], report['final_account'], report['after_forecasts']))
    original = report.get('publication', {}).get('original_sha256') or hashlib.sha256(raw).hexdigest()
    report['program_path'] = PUBLIC_PROGRAM_PATH
    report['publication'] = {
        'original_sha256': original,
        'redactions': ['program_path: replaced private absolute build path with repository-relative path'],
        'boundary': 'Public derivative of a recorded local SVM receipt. Transaction and account values are unchanged; this JSON has its own hash.',
    }
    assert before == (report['transactions'], report['forecasts'], report['final_account'], report['after_forecasts'])
    return report


def build_public_viewer(root: Path, output: Path) -> None:
    # Build in a miniature temporary project so the original evidence and viewer
    # are never rewritten as a side effect of a public-site build.
    with tempfile.TemporaryDirectory(prefix='predictkit-public-viewer-') as tmp:
        scratch = Path(tmp)
        demo_dir = scratch / 'solana/demo'
        demo_dir.mkdir(parents=True)
        font_dir = scratch / 'web/fonts'
        font_dir.mkdir(parents=True)
        for name in ('spacegrotesk-variable.ttf', 'spacegrotesk-OFL.txt'):
            shutil.copyfile(root / 'web/fonts' / name, font_dir / name)
        shutil.copyfile(root / 'solana/demo/viewer.template.html', demo_dir / 'viewer.template.html')
        source_dir = scratch / 'evidence/solana-execution-2026-09-28'
        source_dir.mkdir(parents=True)
        raw = (root / 'evidence/solana-execution-2026-09-28/local-demo.json').read_bytes()
        public = public_demo(raw)
        source = source_dir / 'local-demo.json'
        source.write_text(json.dumps(public, indent=2, ensure_ascii=False) + '\n')
        spec = importlib.util.spec_from_file_location('predictkit_public_demo_builder', root / 'solana/demo/build_viewer.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT, module.HERE = scratch, demo_dir
        # The builder's print contains its temporary path; public builds emit only
        # the final, repository-relative summary below.
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            module.build(source)
        (output / 'solana-demo').mkdir()
        html = (demo_dir / 'index.html').read_text()
        if 'Public receipt: one private compiler path' not in html:
            note = '<p>Public receipt: one private compiler path was replaced with a repository-relative path. Transaction and account values are unchanged. The JSON includes redaction provenance and this derivative has its own fingerprint.</p>'
            html = replace_required(html, '<div class="evidence-inner">', '<div class="evidence-inner">' + note)
        html = html.replace('Download the source receipt', 'Download the public receipt')
        (output / 'solana-demo/index.html').write_text(html)
        shutil.copyfile(source, output / 'solana-demo/receipt.json')


def header(current: str) -> str:
    links = [('Overview', '/'), ('Studio', '/studio'), ('Agents & skills', '/skills'), ('Evidence', '/readiness')]
    nav = ''.join(f'<a href="{url}"' + (' aria-current="page"' if url == current else '') + f'>{label}</a>' for label, url in links)
    return '<header class="hosted-header"><a class="wordmark" href="/" aria-label="PredictKit home"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M14 3 3 16l13 13 13-13-8-8M12 16l4 4 12-13"/></svg><span>predictkit<span class="brand-slash">/</span></span></a><nav aria-label="Site navigation">' + nav + '</nav><label class="hosted-theme">Appearance<select id="hosted-theme"><option value="solana-signal">Solana Signal</option><option value="trust-layer">Trust Layer</option><option value="studio-classic">Studio Classic</option></select></label></header>'


def banner() -> str:
    return '<div class="hosted-banner"><strong>Hosted preview.</strong> Explore the examples and source. <a href="/studio#run-locally">Run the full Studio locally</a>.</div>'


def footer() -> str:
    return f'<footer class="hosted-footer"><a href="{GITHUB}">Open-source on GitHub</a><span>Hosted preview · local runtime</span><a href="/readiness">Release evidence</a></footer>'


def adapt_landing(text: str) -> str:
    text = replace_required(text, '</head>', '<link rel="stylesheet" href="/hosted.css"></head>')
    text = replace_required(text, '</header>', '</header>' + banner())
    text = replace_required(text, 'href="/download/source.zip" download', f'href="{DOWNLOAD}"')
    text = text.replace('Open Studio', 'Explore Studio').replace('Enter your local Studio', 'Explore the Studio preview')
    text = text.replace('Local development preview · source ZIP', 'GitHub source archive · run locally')
    text = text.replace('v0.2 · Local source', 'v0.2 · Hosted preview')
    return text


def adapt_skills(html: str, javascript: str) -> tuple[str, str]:
    html = replace_required(html, '<meta name="predictkit-token" content="__SERVER_TOKEN__">', '')
    html = replace_required(html, '</head>', '<link rel="stylesheet" href="/hosted.css"></head>')
    html = replace_required(html, '</header>', '</header>' + banner())
    html = html.replace('And the design skills on this laptop?', 'Where do design skills fit?')
    html = html.replace('Impeccable, Emil’s design-engineering guidance and Taste help the coding assistant improve PredictKit itself. They are separate from the starter’s bundled role skills shown above. Installing PredictKit does not install those personal packages or add them to model requests.', 'Design guidance such as Impeccable, Emil’s design-engineering principles and Taste can help a coding assistant develop the project. Those development tools are separate from the bundled role skills shown here; this starter does not install or load them automatically.')
    html = html.replace('Open the Studio', 'Explore the Studio').replace('Reading the actual files from this local starter.', 'Reading the bundled source catalog for this release.')
    javascript = replace_required(javascript, '  const token = document.querySelector(\'meta[name="predictkit-token"]\').content;\n', '')
    javascript = replace_required(javascript, "fetch('/api/catalog',{headers:{'X-PredictKit-Token':token},credentials:'same-origin',cache:'no-store',signal:controller.signal})", "fetch('/catalog.json',{cache:'no-store',signal:controller.signal})")
    javascript = javascript.replace('The local catalog could not be loaded', 'The release catalog could not be loaded').replace('The local server took too long to respond.', 'The release catalog took too long to load.').replace('Check that PredictKit is running, then try again.', 'Check your connection, then try again.')
    return html, javascript


def validate_public_output(output: Path) -> None:
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError('Public output contains a symlink')
        if not path.is_file() or path.suffix in ('.ttf', '.woff', '.woff2'):
            continue
        raw = path.read_bytes()
        if any(marker in raw for marker in FORBIDDEN) or re.search(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}', raw):
            raise ValueError('Private path, credential or runtime token in public output: ' + path.relative_to(output).as_posix())
        if path.suffix == '.js' and b'/api/' in raw:
            raise ValueError('Static site references a runtime API')
        if path.suffix == '.html':
            for encoded in re.findall(rb'data:application/json;base64,([A-Za-z0-9+/=]+)', raw):
                decoded = base64.b64decode(encoded, validate=True)
                if any(marker in decoded for marker in FORBIDDEN):
                    raise ValueError('Private path or token in an encoded public receipt')


def build_site(output: Path | None = None, *, root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    output = Path(output or root / 'dist').absolute()
    if output.is_symlink():
        raise ValueError('Site output cannot be a symlink')
    if output.exists() and not (output / 'SITE_BUILD.json').is_file():
        raise ValueError('Refusing to replace a directory without the site-build marker')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.predictkit-site-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'dist'
        stage.mkdir()
        for asset in ASSETS:
            target = stage / asset
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'web' / asset, target)
        for name in ('hosted.css', 'hosted.js', 'favicon.ico'):
            shutil.copyfile(root / 'hosted' / name, stage / name)
        (stage / 'index.html').write_text(adapt_landing((root / 'web/landing.html').read_text()))
        skills_html, skills_js = adapt_skills((root / 'web/skills.html').read_text(), (root / 'web/skills.js').read_text())
        (stage / 'skills').mkdir()
        (stage / 'skills/index.html').write_text(skills_html)
        (stage / 'skills.js').write_text(skills_js)
        (stage / 'catalog.json').write_text(json.dumps(build_catalog(root), indent=2, ensure_ascii=False) + '\n')
        for route in ('studio', 'readiness'):
            page = (root / 'hosted' / (route + '.html')).read_text()
            for key, value in {'HEADER': header('/' + route), 'FOOTER': footer(), 'GITHUB': GITHUB, 'DOWNLOAD': DOWNLOAD}.items():
                page = page.replace('{{' + key + '}}', value)
            (stage / route).mkdir()
            (stage / route / 'index.html').write_text(page)
        brief = json.loads((root / 'examples/launchlens.json').read_text())
        (stage / 'example').mkdir()
        example = render_reference_app(brief)
        # The sandbox remains isolated; the parent accepts only this frame's
        # bounded height message. Fitting the content removes nested scrolling.
        resize = '<script>(()=>{if(parent===window)return;const size=()=>parent.postMessage({type:"predictkit-example-height",height:Math.ceil(document.body.getBoundingClientRect().height)},"*");new ResizeObserver(size).observe(document.body);addEventListener("load",size);size();})();</script>'
        (stage / 'example/index.html').write_text(replace_required(example, '</body>', resize + '</body>'))
        build_public_viewer(root, stage)
        (stage / '404.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found · PredictKit</title><body><h1>This page is not part of the preview.</h1><p><a href="/">Return to PredictKit</a></p></body></html>')
        (stage / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#080D16"/><path d="M13 5 4 16l12 11 12-11-7-7M12 16l4 4L27 6" fill="none" stroke="#62E8CE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
        icon = '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
        for page in stage.rglob('*.html'):
            text = page.read_text().replace("img-src data:;", "img-src 'self' data:;")
            text = re.sub(r'<link\b[^>]*\brel=[\"\']icon[\"\'][^>]*>', '', text, flags=re.IGNORECASE)
            if '</head>' in text:
                text = text.replace('</head>', icon + '</head>', 1)
            else:
                text = replace_required(text, '<title>', icon + '<title>')
            page.write_text(text)
        validate_public_output(stage)
        files = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.rglob('*')) if p.is_file()}
        manifest = {'kind': 'predictkit-static-preview', 'version': 1, 'runtime': 'Static hosted preview; full Python runtime runs locally.', 'github': GITHUB, 'files': files}
        (stage / 'SITE_BUILD.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(stage), str(output))
    return {'output': output.name, 'files': len(files), 'routes': ['/', '/studio', '/skills', '/readiness', '/solana-demo', '/example']}


if __name__ == '__main__':
    print(json.dumps(build_site(), indent=2))
