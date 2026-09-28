# Compiled-program test matrix

**28 actual SVM execution tests pass** against the SBPFv3 build in LiteSVM 1.5.0. These are distinct from 27 codec/synthetic-inspector tests and 9 installed-SDK tests with synthetic transports. Prior host serialization and IDL comparisons remain separate evidence. Reproduction: [LOCAL_SVM_GUIDE.md](LOCAL_SVM_GUIDE.md). Results: [execution verification](../evidence/solana-execution-2026-09-28/VERIFICATION.md).

| Test | Observed coverage |
|---|---|
| Valid create | Exact PDA/owner, immutable fields, 406-byte account and decoded values checked in SVM |
| Empty/over-200-byte question | Empty, whitespace, ASCII and UTF-8 overflow rejected with `InvalidQuestion`; exact 200-byte UTF-8 accepted |
| Zero rule hash/default resolver | Separate exact `InvalidHash` and `InvalidResolver` rejection checks |
| Past/current close, resolve before close | Rejected with `InvalidSchedule` |
| Duplicate creator/question ID | System-program allocation `Custom(0)` plus `already in use`; original bytes unchanged |
| Same ID, different creator | Distinct correct PDA and stored authority |
| Missing signer meta / invalid signatures | Creator non-signer rejected by Anchor; corrupted creator/forecaster/resolver signatures rejected by SVM `SignatureFailure` |
| Forecast 0 and 10000 bps | Accepted into distinct 83-byte forecast accounts; count increments exactly twice |
| Forecast >10000 | Raw instruction bypasses client guard; Rust rejects with `InvalidProbability`; account/count unchanged |
| Forecast just before close | Controlled clock at close minus one second accepts |
| Forecast at/after close | Controlled clocks reject with `ForecastClosed`; count unchanged |
| Duplicate wallet/question | Exact duplicate-init rejection; original forecast and count unchanged |
| Wrong question owner, PDA or discriminator | Exact owner, seed and discriminator constraint failures |
| Forged forecast PDA | `ConstraintSeeds`; question count unchanged |
| Unauthorized resolver | `ConstraintHasOne`; original account unchanged |
| Authorized resolution too early | `TooEarly`; outcome remains OPEN |
| YES / NO / VOID | Each accepted on a separate question at exact permitted time |
| Unknown outcome / zero evidence | Codes 0, 4 and 255 rejected with `InvalidOutcome`; zero commitment rejected with `InvalidHash` |
| Repeated resolution | `AlreadyResolved`; original outcome/evidence unchanged |
| Forecast after resolution | `ForecastClosed`; account/count unchanged |
| Counter overflow | Artificial maximum counter produces `Overflow`; forecast creation and mutation roll back |
| Expired blockhash | Actual SVM `BlockhashNotFound`, with no question created |
| Client decoding | Handwritten codec decodes the actual program-created account bytes; forecast bytes compared directly |
| Wallet rejection or reviewed-message mutation | Installed SDK synthetic-transport tests: no send, no fallback signing |
| Wrong cluster / nonexecutable program | SDK synthetic-transport tests: stops before signing |
| RPC error / failed confirmation | SDK synthetic-transport tests: visible rejection and no retry |
| Unrelated valid signature | Existing synthetic inspector test rejects it as registry proof |

The omitted-signature form is rejected by the installed `@solana/kit` wrapper before VM entry. SVM signature tests therefore supply deliberately corrupted nonzero signatures to prove the VM's cryptographic rejection, and the signer-meta test proves Anchor's role signer constraint. Initial tests that confused those boundaries were repaired; their failing log is retained.

All positive and negative program cases load actual `.so` bytes. The test harness never invokes a host implementation as a substitute. Synthetic account injection is used only to construct adversarial owner/PDA/discriminator/overflow cases and to fund ephemeral test accounts. The SVM clock is deliberately controlled. These facilities are not exposed as user capabilities.

## Remaining integration gates

- A reviewed public deployment identity, upgrade authority, source-to-bytecode comparison and actual devnet account/transaction inspection.
- Human-wallet create/forecast/resolve UX, including missing signatures, rejection, mutation and disconnect in an actual browser wallet.
- Real RPC errors, confirmation expiry and transaction failures on the selected network; no automatic resubmission.
- Browser presentation, accessibility and public-network evidence tied to the final app's actual inputs.
- Dependency remediation, security review, outcome-authority design and any economic/legal requirements before broader release.

A local SVM signature is not a public chain receipt. A passing contract test is not a production security audit or proof that the forecast outcome is true.
