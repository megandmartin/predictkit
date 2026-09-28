# Agent capability contracts

PredictKit's eight roles are specialized instruction sets in a fixed workflow. A live run sends separate requests to one explicitly configured model; rehearsal uses scripted fixtures. Neither mode gives the model a browser, shell, filesystem, wallet or research tool. The deterministic coordinator selects inputs, checks output contracts and writes accepted files.

The executable definitions are in [`predictkit/capabilities.py`](../predictkit/capabilities.py). These definitions describe what each role can draft, the files it can receive and return, the local skills mapped to it, narrow static acceptance checks, and questions that still require judgment. The catalog makes those definitions inspectable.

## Inputs follow the actual workflow

Every role receives the frozen founder brief. Each wave takes a snapshot before any peer starts, so concurrently running roles do not read one another's outputs.

| Wave | Roles | Accepted artifact inputs | Owned outputs |
|---|---|---|---|
| Discovery | Evidence lead, Product lead, Solana architect | None; the founder brief is their shared input | One document each |
| Decision | Chief of staff | All three discovery documents | One founder decision memo |
| Build, after founder approval | App engineer, Market designer, Submission lead | The three discovery documents and approved memo | App engineer: HTML; Market designer: JSON and resolution document; Submission lead: three drafts |
| Review | Independent reviewer | All ten accepted artifacts, including HTML; also the deterministic verification report | One review document |

“Independent reviewer” means a separate review role and request with its own instructions. It does not mean a different model, provider or external audit. The submission role cannot observe engineering work produced concurrently and must keep implementation claims pending.

Exact file names come from [`predictkit/contracts.py`](../predictkit/contracts.py); role-to-skill loading comes from [`predictkit/skills.py`](../predictkit/skills.py). `profile_for(role)` derives paths and skill IDs from those registries and returns a defensive JSON-safe copy. `profile_hash(role)` hashes the canonical profile. The hash identifies a definition; it cannot prove instruction compliance or output quality.

## Every shared skill has an accountable primary role

Skills remain reusable instruction text. Primary ownership identifies the role responsible for that skill's central output; it does not stop other mapped roles from using it.

| Packaged skill | Primary role |
|---|---|
| `frame-opportunity` | Product lead |
| `collect-evidence` | Evidence lead |
| `specify-market` | Market designer |
| `select-solana-adapter` | Solana architect |
| `parallel-build` | Chief of staff |
| `build-prediction-ui` | App engineer |
| `prepare-submission` | Submission lead |
| `verify-outcome` | Independent reviewer |

The separate `run-workshop` and `continue-sprint` guides are for an operator. They are not automatically loaded into role requests. Personal design skills installed elsewhere on a laptop are also separate from the packaged runtime skills.

## Static acceptance has a deliberately narrow meaning

`validate_role_output(role, raw, brief)` produces a `role-output-checks` report with a version, overall pass flag, per-check findings and explicit `not_tested` items. Invalid output produces a failed report without echoing the submitted content.

All roles must satisfy the existing structured-output and file-ownership contract: exact files, nonempty content, size limits and the credential-pattern guard. A short or weak Markdown document can pass these structural checks. The role's separate `review_questions` must still be answered by a reviewer; no word count or heading count stands in for sound reasoning.

The Market designer has additional deterministic checks:

- `market.json` must be a JSON object. Duplicate keys, non-finite values and numeric overflow are rejected, including in nested optional metadata.
- `question`, `resolution_rule` and `void_policy` must be strings that exactly match the frozen brief.
- `mode` must be `offchain-simulation`, and `outcomes` must be the ordered list `YES`, `NO`, `VOID`.

The App engineer has two additional source checks:

- A complete HTML document must have an explicit doctype, one HTML/head/body structure, a language, a nonempty title and a mobile viewport. No template-specific IDs, branding or visual layout is required.
- A parser inspects resource-loading attributes, CSS imports/URLs and obvious JavaScript import or network-call syntax. The intended output is embedded-only source. The indicator check is conservative and can reject inert examples in scripts or styles. It is **not** a JavaScript interpreter, a proof of no network access or a security audit. Computed, obfuscated and other unsupported syntax still requires review; browser preview restrictions are a separate boundary.

A passing report does not establish browser behavior, accessibility, forecast mathematics, factual correctness, live model quality, Solana execution or production security. Tests cover successful rehearsal outputs, invalid ownership, exact frozen-brief matching, wrong types, malformed/duplicate/non-finite JSON, resource imports and observable HTML omissions. They also show explicitly that weak prose and computed network expressions can pass the limited static checks.

## Acceptance and inspectable records

The coordinator freezes the profile and accepted inputs before dispatch. Missing required input or an artifact hash mismatch stops the role. It records provider usage before validating returned content; a failed acceptance report prevents **all** of that role's files from being published. The static report is visible in the Studio role dialog, with manual review questions kept separate.

Each dispatched job stores a `prepared-role-context` receipt containing the profile snapshot, brief and context hashes, input artifact hashes, provider/model identity and an empty executable-tool list. A successful live or injected-transport response additionally records `assembled-role-request`: source-file hashes, full instruction/input/schema hashes, and, for the App engineer, the rendered reference-app hash. Shared source inputs are `AGENTS.md`, `PROJECT.md`, `SOUL.md`, `docs/IMPLEMENTATION_STATUS.md`, the exact role prompt and only its mapped skills. All reads use the guarded local reader. Rehearsal supplies no assembled-request receipt because no model request is made.

New exported packs hash all role records and cross-check their provider/mode/model, profile/check identity, context artifact bytes and reports. A partial downgrade that removes only the aggregate hash is rejected. Genuine older metadata remains readable without invented records. These checks establish consistency, not authorship, historical source authenticity or model compliance.

Read capabilities in `/skills` or with `python3 predictkit.py capabilities frontend`. Open a Studio role for its recorded inputs and checks. For reproducible positive and adversarial evidence, see the [capability verification report](../evidence/PUBLICATION.md).

## Remaining capability work

The most useful next expansions are evidence-backed document review, an executable generated-app browser check, and a separately scoped tool/provider adapter. Each should have its own input, permission, evidence and failure contract before it is advertised as available. Adding a prompt or a catalog entry alone does not add those capabilities.
