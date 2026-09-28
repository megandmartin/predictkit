#!/usr/bin/env python3
"""Package the reviewed starter source. Never collect private runs or caches.

The supplied release manifest supplies the baseline allowlist. Additions below
are explicit: adding an unrelated file to the project cannot include it in ZIPs.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXTRA = (
    'PRODUCT.md', 'DESIGN.md', '.impeccable/design.json',
    'predictkit/catalog.py', 'tests/test_catalog.py', 'tests/test_readiness_hardening.py',
    'tests/test_runtime_hardening.py', 'tests/test_design_routes.py',
    'web/studio.html', 'web/studio.js', 'web/studio.css',
    'web/landing.html', 'web/landing.js', 'web/landing.css',
    'web/skills.html', 'web/skills.js', 'web/skills.css',
    'web/evidence-modern.html', 'web/evidence-modern.js', 'web/fonts.css',
    'web/fonts/inter-variable.ttf', 'web/fonts/spacegrotesk-variable.ttf',
    'web/fonts/inter-OFL.txt', 'web/fonts/spacegrotesk-OFL.txt', 'web/fonts/SOURCES.json',
    'scripts/check_local.py', 'scripts/browser_connected.cjs', 'scripts/browser_design.cjs',
    'scripts/package_source.py', 'scripts/verify_source_package.py', 'docs/HOW_PREDICTKIT_WORKS.md', 'docs/SOURCE_AUDIT.md',
    'solana/.gitignore', 'solana/Cargo.lock', 'solana/programs/predictkit_registry/tests/host_contract.rs',
    'solana/tests/compare-host-idl.mjs', 'evidence/solana-2026-09-28/VERIFICATION.md',
    'evidence/solana-2026-09-28/host-generated-idl-sections.json',
    'evidence/local-2026-09-28/VERIFICATION.md', 'evidence/local-2026-09-28/INDEPENDENT_REVIEW.md',
    'evidence/design-2026-09-28/VERIFICATION.md', 'evidence/design-2026-09-28/INDEPENDENT_REVIEW.md',
)
EXTRA += tuple('evidence/design-2026-09-28/' + name for name in (
    'FUNCTIONAL_REVIEW.md', 'VISUAL_REVIEW.md', 'VISUAL_VERDICT.md', 'DETECTOR_REVIEW.md',
    'python-tests.txt', 'browser-connected.txt', 'browser-design.json', 'browser-design.txt',
    'fresh-download-rehearsal.txt', 'impeccable-detector.json',
))
EXTRA += tuple('evidence/local-2026-09-28/' + name for name in (
    'python-tests.txt', 'codec-tests.txt', 'check-summary.json', 'rehearsal.txt',
    'browser-connected.json', 'independent-probes.json', 'independent-a11y.json',
))
EXTRA += tuple('evidence/solana-2026-09-28/' + name for name in (
    'cargo-host-test.log', 'cargo-host-test.json', 'cargo-host-contract-tests.log',
    'cargo-host-contract-tests.json', 'cargo-host-idl.log', 'cargo-host-idl.json',
    'host-idl-comparison.json',
))
EXTRA += tuple('output/playwright/' + name + '.png' for name in (
    'studio-desktop', 'studio-team-approval', 'studio-mobile', 'studio-light',
    'evidence-desktop', 'evidence-mobile', 'generated-app',
))
REVIEW_CAPTURES = tuple(f'.impeccable/review/{page}-{theme}-{width}.png'
    for page in ('landing', 'studio', 'skills', 'evidence')
    for theme in ('solana-signal', 'trust-layer', 'studio-classic') for width in (1440, 390))
EXTRA += REVIEW_CAPTURES

# Reviewed capability, live-setup, pilot and local SVM source/evidence. Fixed names only.
EXTRA += ('docs/CAPABILITY_CONTRACT.md',
 'docs/LIVE_PREPARED.md',
 'evidence/capabilities-2026-09-28/INDEPENDENT_FAILURE_UI_REVIEW.md',
 'evidence/capabilities-2026-09-28/INDEPENDENT_REVIEW.md',
 'evidence/capabilities-2026-09-28/PILOT_PROTOCOL_REVIEW.md',
 'evidence/capabilities-2026-09-28/ROLE_FAILURE_UI_REVIEW.md',
 'evidence/capabilities-2026-09-28/SKILL_FORWARD_TEST.md',
 'evidence/capabilities-2026-09-28/VERIFICATION.md',
 'evidence/capabilities-2026-09-28/browser-connected.json',
 'evidence/capabilities-2026-09-28/browser-connected.txt',
 'evidence/capabilities-2026-09-28/document-links.json',
 'evidence/capabilities-2026-09-28/forward-test/MANIFEST.json',
 'evidence/capabilities-2026-09-28/forward-test/after/browser-case-c.cjs',
 'evidence/capabilities-2026-09-28/forward-test/after/browser-results.json',
 'evidence/capabilities-2026-09-28/forward-test/after/reference-desktop.png',
 'evidence/capabilities-2026-09-28/forward-test/after/reference-launchbet.html',
 'evidence/capabilities-2026-09-28/forward-test/after/reference-mobile.png',
 'evidence/capabilities-2026-09-28/forward-test/after/reference-template.html',
 'evidence/capabilities-2026-09-28/forward-test/after/reset-confirmation-sandbox.png',
 'evidence/capabilities-2026-09-28/forward-test/after/source-manifest.json',
 'evidence/capabilities-2026-09-28/forward-test/before/browser-case-c.cjs',
 'evidence/capabilities-2026-09-28/forward-test/before/browser-results.json',
 'evidence/capabilities-2026-09-28/forward-test/before/reference-desktop.png',
 'evidence/capabilities-2026-09-28/forward-test/before/reference-launchbet.html',
 'evidence/capabilities-2026-09-28/forward-test/before/reference-mobile.png',
 'evidence/capabilities-2026-09-28/forward-test/before/source-manifest.json',
 'evidence/capabilities-2026-09-28/forward-test/brief.json',
 'evidence/capabilities-2026-09-28/forward-test/case-a-response.json',
 'evidence/capabilities-2026-09-28/forward-test/case-a/app/market.json',
 'evidence/capabilities-2026-09-28/forward-test/case-a/domain/resolution.md',
 'evidence/capabilities-2026-09-28/forward-test/case-b-response.json',
 'evidence/capabilities-2026-09-28/forward-test/case-b/qa/review.md',
 'evidence/capabilities-2026-09-28/forward-test/contract-validation.json',
 'evidence/capabilities-2026-09-28/independent-capability-tests.txt',
 'evidence/capabilities-2026-09-28/independent-contrast.json',
 'evidence/capabilities-2026-09-28/independent-hardening-tests.txt',
 'evidence/capabilities-2026-09-28/independent-provider-tests.txt',
 'evidence/capabilities-2026-09-28/independent-receipts-after.json',
 'evidence/capabilities-2026-09-28/independent-receipts-repair-in-progress.json',
 'evidence/capabilities-2026-09-28/independent-reviewed-source-hashes.json',
 'evidence/capabilities-2026-09-28/independent-role-failure-browser.cjs',
 'evidence/capabilities-2026-09-28/independent-role-failure-browser.json',
 'evidence/capabilities-2026-09-28/independent_receipt_probe.py',
 'evidence/capabilities-2026-09-28/package-tests.txt',
 'evidence/capabilities-2026-09-28/python-tests.txt',
 'evidence/capabilities-2026-09-28/role-failure-before.json',
 'evidence/capabilities-2026-09-28/role-failure-browser.cjs',
 'evidence/capabilities-2026-09-28/role-failure-browser.json',
 'evidence/capabilities-2026-09-28/runtime-tests.txt',
 'evidence/capabilities-2026-09-28/skill-validation.json',
 'evidence/live-setup-2026-09-28/INDEPENDENT_REVIEW.md',
 'evidence/live-setup-2026-09-28/VERIFICATION.md',
 'evidence/live-setup-2026-09-28/launcher-tests.txt',
 'evidence/live-setup-2026-09-28/offline-review-results.json',
 'evidence/live-setup-2026-09-28/offline_review_probes.py',
 'evidence/live-setup-2026-09-28/preflight.json',
 'evidence/live-setup-2026-09-28/python-tests.txt',
 'evidence/live-setup-2026-09-28/source-hashes.json',
 'evidence/solana-execution-2026-09-28/HANDOFF_FILES.json',
 'evidence/solana-execution-2026-09-28/INDEPENDENT_REVIEW.md',
 'evidence/solana-execution-2026-09-28/SUMMARY.json',
 'evidence/solana-execution-2026-09-28/VERIFICATION.md',
 'evidence/solana-execution-2026-09-28/all-node-tests.log',
 'evidence/solana-execution-2026-09-28/client-tests.log',
 'evidence/solana-execution-2026-09-28/independent-execution-initial.json',
 'evidence/solana-execution-2026-09-28/independent-execution.json',
 'evidence/solana-execution-2026-09-28/independent-local-demo.json',
 'evidence/solana-execution-2026-09-28/independent-local-demo.log',
 'evidence/solana-execution-2026-09-28/independent-source-hashes.json',
 'evidence/solana-execution-2026-09-28/independent-svm-tests-initial.log',
 'evidence/solana-execution-2026-09-28/independent-svm-tests.log',
 'evidence/solana-execution-2026-09-28/local-demo.json',
 'evidence/solana-execution-2026-09-28/local-demo.log',
 'evidence/solana-execution-2026-09-28/npm-audit.json',
 'evidence/solana-execution-2026-09-28/npm-install.log',
 'evidence/solana-execution-2026-09-28/platform-archive.json',
 'evidence/solana-execution-2026-09-28/platform-download.log',
 'evidence/solana-execution-2026-09-28/platform-ranges.log',
 'evidence/solana-execution-2026-09-28/sbf-build-initial-offline.json',
 'evidence/solana-execution-2026-09-28/sbf-build-initial-offline.log',
 'evidence/solana-execution-2026-09-28/sbf-build-summary.log',
 'evidence/solana-execution-2026-09-28/sbf-build.json',
 'evidence/solana-execution-2026-09-28/sbf-build.log',
 'evidence/solana-execution-2026-09-28/sbf-target-fetch.log',
 'evidence/solana-execution-2026-09-28/svm-tests-initial.log',
 'evidence/solana-execution-2026-09-28/svm-tests.log',
 'evidence/solana-execution-2026-09-28/tool-install.log',
 'evidence/solana-execution-2026-09-28/toolchain-sources.json',
 'evidence/solana-execution-2026-09-28/viewer-VERIFICATION.md',
 'evidence/solana-execution-2026-09-28/viewer-browser.cjs',
 'evidence/solana-execution-2026-09-28/viewer-browser.json',
 'evidence/solana-execution-2026-09-28/viewer-detector.json',
 'evidence/solana-execution-2026-09-28/viewer-independent-browser.log',
 'evidence/solana-execution-2026-09-28/viewer-independent-review.md',
 'output/playwright/capability-catalog-solana-signal-1440.png',
 'output/playwright/capability-catalog-solana-signal-390.png',
 'output/playwright/capability-catalog-studio-classic-1440.png',
 'output/playwright/capability-catalog-studio-classic-390.png',
 'output/playwright/capability-catalog-trust-layer-1440.png',
 'output/playwright/capability-catalog-trust-layer-390.png',
 'output/playwright/capability-receipt-solana-signal-1440.png',
 'output/playwright/capability-receipt-solana-signal-390.png',
 'output/playwright/capability-receipt-studio-classic-1440.png',
 'output/playwright/capability-receipt-studio-classic-390.png',
 'output/playwright/capability-receipt-trust-layer-1440.png',
 'output/playwright/capability-receipt-trust-layer-390.png',
 'output/playwright/capability-ui-checks.json',
 'output/playwright/independent-failure-ui/interrupted-role-mobile.png',
 'output/playwright/independent-failure-ui/receipt-bearing-provider-error-mobile.png',
 'output/playwright/independent-failure-ui/role-failure-after-solana-signal-1440.png',
 'output/playwright/independent-failure-ui/role-failure-after-solana-signal-390.png',
 'output/playwright/independent-failure-ui/role-failure-after-studio-classic-1440.png',
 'output/playwright/independent-failure-ui/role-failure-after-studio-classic-390.png',
 'output/playwright/independent-failure-ui/role-failure-after-trust-layer-1440.png',
 'output/playwright/independent-failure-ui/role-failure-after-trust-layer-390.png',
 'output/playwright/independent-failure-ui/role-legacy-after-mobile.png',
 'output/playwright/independent-failure-ui/role-provider-error-fixture-mobile.png',
 'output/playwright/independent-failure-ui/role-queued-after-mobile.png',
 'output/playwright/role-failure-after-solana-signal-1440.png',
 'output/playwright/role-failure-after-solana-signal-390.png',
 'output/playwright/role-failure-after-studio-classic-1440.png',
 'output/playwright/role-failure-after-studio-classic-390.png',
 'output/playwright/role-failure-after-trust-layer-1440.png',
 'output/playwright/role-failure-after-trust-layer-390.png',
 'output/playwright/role-failure-before-mobile.png',
 'output/playwright/role-legacy-after-mobile.png',
 'output/playwright/role-provider-error-fixture-mobile.png',
 'output/playwright/solana-viewer-1440.png',
 'output/playwright/solana-viewer-390.png',
 'output/playwright/solana-viewer-834.png',
 'predictkit/capabilities.py',
 'scripts/live_session.py',
 'solana/.gitignore',
 'solana/LOCAL_SVM_GUIDE.md',
 'solana/README.md',
 'solana/TEST_PLAN.md',
 'solana/client/client.mjs',
 'solana/client/package-lock.json',
 'solana/client/package.json',
 'solana/demo/README.md',
 'solana/demo/build_viewer.py',
 'solana/demo/index.html',
 'solana/demo/viewer-source.json',
 'solana/demo/viewer.template.html',
 'solana/programs/predictkit_registry/src/lib.rs',
 'solana/scripts/build-sbf-local.py',
 'solana/scripts/run-local-demo.mjs',
 'solana/tests/client.test.mjs',
 'solana/tests/svm-harness.mjs',
 'solana/tests/svm.test.mjs',
 'tests/test_capabilities.py',
 'tests/test_capability_runtime.py',
 'tests/test_live_setup.py',
 'workshop/PILOT_RESULTS.csv',
 'workshop/THREE_BUILDER_PILOT.md')

def source_paths(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    names = set(manifest['files']) | {'SOURCE_MANIFEST.json'}
    names.update(name for name in EXTRA if (root / name).exists())
    selected = []
    for name in sorted(names):
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or any(x in ('.local', '.tools', '.git', 'target', 'node_modules', '__pycache__') for x in rel.parts):
            raise ValueError('Unsafe source inventory entry')
        if any(x.startswith('.') for x in rel.parts) and name not in ('.env.example', '.gitignore', '.vercelignore', 'solana/.gitignore', '.impeccable/design.json', *REVIEW_CAPTURES):
            raise ValueError('Unreviewed hidden source entry')
        path=root
        for part in rel.parts:
            path=path/part
            if path.is_symlink():
                raise ValueError('Symlinked source cannot be packaged')
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError('Missing or oversized source file: ' + name)
        selected.append((name,path))
    return selected

def package_source(root=ROOT):
    root=Path(root).resolve()
    files=source_paths(root)
    out=root/'.local/releases'
    for part in (root/'.local',out):
        if part.is_symlink(): raise ValueError('Release directory must not be symlinked')
    out.mkdir(parents=True,exist_ok=True)
    destination=out/'PredictKit-Local-Starter.zip'
    staged=out/'PredictKit-Local-Starter.zip.tmp'
    if destination.is_symlink() or staged.is_symlink(): raise ValueError('Release file must not be symlinked')
    entries={}
    with zipfile.ZipFile(staged,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,path in files:
            data=path.read_bytes()
            archive.writestr('PredictKit/'+name,data)
            entries[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        archive.writestr('PredictKit/PACKAGE_MANIFEST.json',json.dumps({'kind':'local-development-preview','files':entries,'boundary':'Source only. No private runs, credentials, model access, wallet or deployment included.'},indent=2)+'\n')
    staged.replace(destination)
    return destination, len(entries)

if __name__=='__main__':
    path,count=package_source()
    print(f'{path}\n{count} source files; {path.stat().st_size} bytes')
