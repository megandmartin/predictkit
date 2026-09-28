---
name: select-solana-adapter
description: Plan a minimal Solana adapter from supplied requirements and evidence, with explicit compatibility gaps and operator verification steps.
---
# Plan the Solana boundary

Use when architecture must explain Solana's role in the founder's forecast product. This worker cannot browse documentation, inspect installed packages, query RPC, run tests, or send transactions. It can assess supplied text and propose a verifiable integration plan.

## Start from the capability
Separate reading external markets, creating a custom question, recording forecasts, trading positions, and resolving outcomes. They are different capabilities; support for one does not imply the others. Identify the smallest capability that changes this user's experience and what the app can do without it.

For this run, choose the existing off-chain simulation. Put the future adapter behind a small boundary with defined input, result, authority, and error states. Reusing a compatible provider may be smaller than a new program; a dedicated forecast registry may be appropriate when custom immutable questions matter. Neither choice is verified by this analysis.

## Check evidence for the proposed fit
If provider material is supplied, compare claimed support for networks, versions, read/create/forecast/trade/resolve operations, source/license, authentication, account ownership, question semantics, and restrictions. Preserve provenance and mark unverified cells unknown. If no material is supplied, provide a requirements matrix and candidate-selection criteria without inventing a winning provider.

Mainnet support does not establish devnet support. A readable market does not establish permission to create one. A token transfer or memo is not a forecast registry. Compiled host tests do not establish deployable chain behavior. Wallet connection does not establish any application transaction.

## Define a future integration test
Give the operator a bounded sequence with observable success and failure results: confirm the intended cluster/program/version; inspect the interface and ownership assumptions; create or find the permitted question; submit the intended action; read back its state; reject an unauthorized or invalid transition; record evidence with environment and limitations. Describe it as a plan, never a successful test.

Account for rejected signing, RPC failure, stale reads, duplicate action, and unsupported operations. Do not quietly replace a failing provider with synthetic data while retaining a live label. A failure should leave the existing forecast record understandable and avoid duplicate submission.

## Handoff
Deliver this-run architecture, proposed adapter inputs/outputs, unsupported capabilities, and evidence that must exist before enabling the connection. No mainnet funds, custody, autonomous trading, provider installation, or deployment is authorized by this skill.
