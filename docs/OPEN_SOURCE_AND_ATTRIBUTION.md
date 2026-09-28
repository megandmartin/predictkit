# Open-source and participant policy

PredictKit's original starter code is released under the included MIT license. Maintain copyright and license notices. Third-party dependencies keep their own licenses. External skills and protocol code require a source URL, pinned commit/version, license and modification record before inclusion. Do not assume a public GitHub repository grants reuse rights.

## Repository split
One toolkit repository contains the runtime, domain adapters, skills, examples and workshop pack. Each participant team creates its own project repository, discloses the toolkit version and documents its original work. A shared base does not make the host a coauthor of every participant product. Do not take participant IP or prize rights by default.

## Required provenance record
For the toolkit: original files built during this effort; reused public dependencies; any imported code; AI assistance; measured test evidence; actual live integrations. For a participant: starting release/commit, new files/changes, original design decisions, collaborators and licenses. Preserve Git history rather than backdating work.

## Public / private separation
Public: sanitized source, synthetic examples, reviewed skills, architecture, tests and an honest capabilities table. Private: API secrets, participant briefs unless consented, raw user interviews, internal decisions, authentication, real wallet keys and run logs with confidential content. `.local/` stays private unless deliberately reviewed and exported.

## GitHub publication checklist
Review name/owner and visibility; review LICENSE and THIRD_PARTY_NOTICES.md; scan staged files for secrets; exclude .local/.venv; run tests; record limitations; create repository under the agreed account; push; verify clone-and-run from a clean machine; tag the workshop release. Publication is not performed in this package. Do not publish to a guessed account or organization.
