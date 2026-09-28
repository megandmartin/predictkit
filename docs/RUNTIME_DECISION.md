# Runtime decisions — v0.2

## 001: keep the company workflow bounded
Preserve the earlier design's useful principles: separate coordination, agent execution and authority/evidence; narrow ownership; three concurrent workers; human approval. Other orchestration integrations are not installed or represented as working here.

## 002: replace the unverified SDK prerequisite
v0.1 selected an optional Agents SDK provider. Installation could not be verified in the authoring environment. A separate diagnostics bug could mistake the local `agents/` prompts directory for an installed Python package.

v0.2 uses a small, direct, fixed-endpoint Responses API adapter for this one-turn-per-role workflow. Python's standard library handles HTTPS and the coordinator handles the fixed graph. No agent SDK is required. Package diagnostics now use distribution metadata, not the existence of a same-named directory.

This is not a judgment that direct HTTP is generally better than the SDK. It minimizes installation work for this specific no-tools prototype. Revisit a supported SDK or sandbox worker when genuinely needed for tool execution, streaming, sessions or bounded repair.

## 003: freeze inputs; review actual outputs
Parallel-wave contexts are frozen before dispatch. Prior artifacts are hash-checked and passed in full within a size envelope. Exceeding the envelope fails explicitly rather than silently truncating the source. Approval binds the exact founder brief and generated memo. The reviewer sees generated application code and the static verification report.

## 004: evidence before animation
Actual skill files are loaded per role and recorded by hash. Response identifiers and usage are recorded even when returned files fail validation. A custom transport for testing cannot label its output as live provider evidence. The Evidence Desk separates static checks, approval, provider usage, overlap, browser behavior, chain and builder validation.

## Agent capability boundary
These roles analyze supplied information and generate files. They do not browse, run shell commands, install dependencies, test their code in a browser, sign a transaction or repair code autonomously. More roles and a company-shaped UI do not change this boundary.
