# Public release verification — 28 September 2026

This release publishes the local starter and a static hosted preview. Hosting does not prove a genuine model run, public-chain execution or participant success.

## Maker verification

| Check | Observed result |
|---|---|
| Local runtime Python suite | 168 tests passed in the sanitized public checkout. |
| Combined suite before final favicon repair | 176 tests passed: 168 runtime and eight site-build tests. |
| Final site-build regression tests | Nine passed after adding the favicon regression, including deterministic build hashes, internal links, source-backed catalog, privacy canaries, decoded receipt checks and safe output handling. |
| JavaScript codec | 27 fixtures passed. No RPC or wallet requests. |
| Complete rehearsal | All eleven artifacts produced and exported; integrity verification passed. Output mode is explicitly scripted. |
| Fresh source extraction | Doctor, role catalog and full eleven-artifact rehearsal passed from a newly unpacked source archive. |
| Hosted maker browser pass | 49 checks passed across six routes, three themes and 390/834/1440px viewports. Forecast, close, YES calibration, reset and command-copy behavior were exercised. |
| Vercel input inventory | A dry run excluded environment files, private runtime state, Git/Vercel machine metadata, compiler caches and installed dependencies. |

The final build emits 24 static files plus its SHA-256 inventory. The Python worker server is not deployed. The hosted catalog is generated from the bundled roles and skills. Fonts, examples and the recorded Solana viewer are served locally with no third-party runtime scripts.

## Independent review and repairs

An independent public-release reviewer checked source privacy, decoded receipt downloads, font-license hashes, source manifest consistency, preserved governance, Markdown links and hosted navigation. The review prompted removal of internal handoff data and inherited spending authorization, correction of font notices, and a safe example-file ignore-rule repair. The public source keeps the MIT license and both SIL OFL notices.

A separate reviewer checked the local hosted preview with the Vercel response security headers applied. Its missing-favicon finding was repaired with a valid local ICO and SVG; all generated pages now declare the icon. The maker also repaired nested example scrolling with an isolated iframe height message. The receiver validates the source frame, message type, finite numeric value and a bounded height; it does not grant same-origin access.

## Earlier program-execution evidence

Earlier local engineering in this project verified five Rust host tests, 13 host-generated interface comparisons, nine SDK transport tests and 28 tests executing the actual compiled registry in LiteSVM. These are prior execution results, not reruns performed by a static deployment.

Compiled SBPFv3 SHA-256: `218c05107cce14107db43f232ba92cf9142084bbbd23be606d5aeffd2421efec`.

The [local demo receipt](solana-execution-2026-09-28/local-demo.json) records create, 68% and 42% forecasts, expected late rejection and YES resolution using synthetic test keys in an isolated local SVM. The public derivative replaces only the private compiler path and adds provenance metadata; transaction and account values are unchanged.

Public receipt SHA-256: `aceee174d8a8921a8140ad38616df6d8740224309c7cca76ee5838134b28d917`. Its original receipt hash is provenance metadata, not the hash of this derivative. The viewer's download and displayed fingerprint match the public JSON.

## Limits and next improvements

1. Complete one explicitly budgeted genuine API run, capture provider usage and independently test its generated app. No paid calls were made by this publication.
2. Connect the registry to an app and verify an individually approved wallet/devnet journey. No public Solana deployment or real-money feature is included.
3. Observe three new builders using the supplied pilot protocol. No participant outcomes or demand claims are made.

Source and pattern scans are scoped checks, not security certification. Historical raw working logs and personal screenshots are not redistributed. Local browser verification and Vercel build/status verification are separate: the deployment URL is not fetched by the publication agent. See [hosting](../docs/HOSTING.md) for the static/local architecture and repeatable preview command.
