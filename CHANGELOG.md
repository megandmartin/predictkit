# Changelog

## 0.2.0 — development release
- Replaced unverified Agents SDK prerequisite with fixed direct Responses HTTP transport; no pip install for the Python runtime.
- Corrected SDK detection: a role directory is not an installed distribution.
- Loaded reviewed, role-specific skills and recorded their hashes.
- Added conservative local price-based reservations; recorded usage even when an artifact is rejected.
- Bound founder approval to both the brief and exact memo; detected post-acceptance artifact changes.
- Froze parallel contexts and supplied actual app code/static findings to the reviewer.
- Added automated fixture rehearsal, read-only export verification and Evidence Desk.
- Added source-only Anchor forecast registry, JavaScript instruction client, byte codec and read-only devnet observation validator.
- Expanded tests: 59 Python, 24 Node, 25 browser-rendering checks.
- Preserved v0.1 evidence under evidence/archive-v0.1; published no repository and submitted no competition entry.

Remaining: actual API run, compiled/SVM-tested registry, connected wallet/app, verified devnet flow and participant validation. A failed read-only devnet network attempt is recorded, not treated as a successful chain check.
