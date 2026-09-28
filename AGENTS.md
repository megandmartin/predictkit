# PredictKit — agent operating contract

## Mission
Build one useful prediction application from a founder-approved brief, then assemble an honest, inspectable submission draft. PredictKit itself is the open-source product. The workshop is its pilot, not proof of demand until measured.

## Read first
Read PROJECT.md, SOUL.md, docs/IMPLEMENTATION_STATUS.md and your role file under agents/. For local engineering continuation also read prompts/START_LOCAL.md and docs/BUILD_PLAN.md. This file supplies instructions; it does not install or launch a worker. The Python runner must explicitly load your role and invoke the provider.

## Authority and file ownership
The founder sets the brief and approves its exact hash. The deterministic coordinator owns task dependencies, writes, validation and event records. Model agents cannot authorize themselves. Return only the complete files in your role's output contract; the coordinator rejects any other path, missing file, duplicate, oversized result or invalid JSON. Do not modify the runner, prompts, ownership map, policies, credentials or approval records through a generated artifact.

## Working method
Use the common brief and accepted artifacts, not another agent's hidden conversation. Independent discovery and build jobs can run in parallel; dependent work must wait. Reuse existing audited infrastructure only after inspecting its source, current API, license and deployment. Do not silently pull or execute third-party SKILL.md files. Prefer one complete flow over new features. Return summary, artifacts and limitations, each in the required structured output.

## Truthfulness
Distinguish specified, implemented, locally tested, provider-tested, chain-verified, deployed and measured. Never describe fixture outputs as live inference. Never invent tests, users, interviews, revenue, partner endorsements, chain signatures, market liquidity, audit status or competition acceptance. Static checks do not establish browser behavior or security. A mean forecast is not an executable exchange price. An approval is not a blockchain transaction. An evidence hash is not a prediction-market settlement.

## Tools and boundaries in this release
The live provider has no shell, wallet, web search or filesystem tools. It receives selected text and returns artifacts; the coordinator writes them. Do not claim to have browsed current sources. Analyze the supplied evidence and explicitly identify unanswered research questions. Generated code is never run on the server. HTML preview runs with a sandboxed iframe and network-blocking policy. No autonomous trading, custody, mainnet transactions, paid outreach, public repo creation or submission.

## Escalation
Fail closed on missing provider access, a bad output contract, unknown resolution semantics or a scope conflict. Do not switch to a fixture while retaining a live label. No automatic retries or spending escalation. A human reviews irreversible actions and official submissions. Concise findings and next actions are preferred to decorative status reports.

## v0.2 implementation precedence
The live provider is direct Responses HTTP, not an installed Agents SDK. Role-scoped local skills are loaded by predictkit/skills.py; filenames alone are not evidence of execution. The Solana program and SDK-dependent client are source-only, not compiled/deployed/connected. Use docs/IMPLEMENTATION_STATUS.md and evidence/VERIFICATION.md for current status. Approval binds the brief and memo hashes. Never upgrade fixture evidence, identifiers or hashes into claims of live execution.
