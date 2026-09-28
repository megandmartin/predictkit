# Product and UX specification

## The design
A focused builder studio using the supplied code-first visual identity. The connected interface offers three reversible themes: Solana Signal (dark, mint signal accents), Trust Layer (light, blue accents) and Studio Classic (warm off-white, ink and lime). Solana Signal is the current default, not a final owner-approved rebrand. The original interface remains available at `/classic`. Artwork uses CSS/SVG and local system font fallbacks; no external font or image service is required. Domain and evidence are more important than agent spectacle.

## Five surfaces
**Project brief:** an example already filled, eleven short fields, three template choices and a one-screen explanation. In live mode expose model-data transfer and spend authorization. Never request a seed phrase or API key inside browser form fields.

**Live team:** human decision owner at the top; discovery, synthesis, build and review groups; actual queued/running/done/failed/cancelled states. Clicking a role shows its output contract, summary and limitations. Show measured requests/tokens and current parallelism. Do not show a fake engineering-completion percentage.

**Workbench:** accepted file list with ownership, an isolated app preview, readable artifacts and clearly scoped check results. Users should be able to inspect code rather than only see a chat message saying it exists.

**Submission:** drafts, evidence and unresolved blockers. A generated script is not a video. A locally exported ZIP is not a platform submission. Keep missing chain proof and participant outcomes visible.

**Run log:** operational events and UTC timestamps. Do not display hidden chain of thought. Show failures, rejections and pauses, not just successes.

## First-run path
Open → understand rehearsal/live distinction → review or edit the example → launch → inspect overlapping tasks → read memo → approve → preview an app → export. Opening the standalone HTML must work without a server; live and filesystem behavior requires the Python service.

## Acceptance criteria
All navigation and primary buttons work. No dead links or image dependencies. The interface fits mobile and laptop widths. Errors are surfaced in a readable dialog. A live run cannot silently fall back to rehearsal. A failed task stays failed. The generated app cannot use the Studio's API token. One question can receive a forecast, close, resolve or void, and display the result; voids must not be scored as incorrect forecasts.

## Deliberate omissions
No account onboarding, company org-chart editor, drag-and-drop graph, billing UI or generic workflow builder before the narrow prediction-app path proves useful. Participant privacy is local-first. Hosted classrooms need separate tenant isolation and access controls before launch.
