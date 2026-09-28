# Next build gates — v0.2

| Gate | Current state | Next acceptance evidence |
|---|---|---|
| Local workflow | Implemented and locally tested | Re-run on both host machines; preserve logs |
| Real model execution | Direct provider and fixture tests implemented | One authorized run; actual response IDs, usage, overlap, useful outputs |
| Compiled registry | Rust source and client supplied | Clean Anchor build, reproducible ID/IDL, actual program tests |
| Solana app integration | Not connected | Local-validator flow then approved devnet flow; wallet failures tested |
| Fresh builders | Not measured | Three independent attempts, elapsed times, assistance and failure denominator |
| Workshop release | Not ready | Fixed versions and smoke tests, one complete app journey |
| Competition submission | Drafts only | Current portal/eligibility check, truthful recorded demos, manual submission |

## Priority 1 — verify the live provider
Owner: runtime engineer. Run `docs/LIVE_RUN.md` without an SDK install. Do not mistake the injected transport tests for actual requests. Save an evidence record and fix model-specific request/schema incompatibility if found. No automatic paid retry. Confirm selected skill hashes and reviewer context. Independently test generated behavior.

## Priority 2 — compile and test the registry
Owner: a designated Solana engineer. Inspect `solana/README.md` and `solana/TEST_PLAN.md`. Install reviewed tooling only with authorization. Compile before deployment; verify the generated IDL matches handwritten account/instruction encoding. Build actual program tests, including adversarial account, signer and time checks. The included codec tests do not replace SVM execution.

## Priority 3 — connect one application
Connect Forecast Studio to one verified program identity, beginning with a local validator. Add explicit wallet/network/program state and an unsigned transaction review. Keep offline simulation separate. Test rejection, duplicate forecast, expired blockhash, wrong network, failed RPC, failed transaction and repeated resolution. Only then approve devnet deployment and record read-only inspection evidence.

## Defer
More orchestration backends, real-money trading, new AMMs, token economics, remote shell access, public hosting and automation of official submission. After the complete loop, consider a bounded disposable code/test runner and one controlled repair attempt.

No planning estimate is a guaranteed delivery date. The three hours describe the eventual participant experience, not all remaining engineering.
