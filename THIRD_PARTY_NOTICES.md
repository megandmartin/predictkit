# Third-party notices and provenance

This repository's original source is provided under the root MIT license. No official sponsor affiliation, trademark clearance or competition eligibility is implied.

Python is the runtime prerequisite; the v0.2 workflow uses the standard library rather than redistributing a third-party agent SDK. Model/API service use requires its own account and terms.

The optional Solana source declares Anchor 1.2.0 and its transitive build dependencies. The optional client declares @solana/web3.js 1.98.4 and LiteSVM for local tests. Lockfiles pin the reviewed dependency graph; dependency packages, compiler toolchains and build caches are not redistributed in the source release. Browser QA uses Playwright/Chromium when separately available; those binaries are not bundled.

The interface bundles Inter and Space Grotesk variable fonts under the SIL Open Font License 1.1. Copyright notices and license terms accompany them in `web/fonts/inter-OFL.txt` and `web/fonts/spacegrotesk-OFL.txt`. Exact upstream URLs, source revisions and file hashes are recorded in `web/fonts/SOURCES.json`. The recorded Solana viewer embeds Space Grotesk and its license text. Preserve these notices when redistributing the fonts or viewer. System fonts remain fallbacks. No remote images are bundled. External design-skill repositories are development references, not redistributed runtime dependencies.

A reference URL or a package declaration is not proof of installation, working integration, permission, audit or endorsement. See docs/SOURCES.md and evidence/VERIFICATION.md.
