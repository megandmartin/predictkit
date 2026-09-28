# Forecast registry — compiled and executed locally

The registry now compiles to **SBPFv3** and passes **28 adversarial tests against the actual compiled program in LiteSVM**. A connected offline demo creates a question, records two forecasts, rejects a post-close forecast and resolves the question to YES. This is local Solana VM execution; no devnet/mainnet deployment or public transaction has occurred.

The registry makes the question, rules commitment, deadline, forecasts and authorized outcome inspectable. It is an educational forecasting registry, not an exchange: there are no tokens, collateral, custody, AMM or payouts.

## What is verified

| Layer | Evidence as of 28 September 2026 |
|---|---|
| Byte codec and read-only inspector | 27 tests using constructed bytes and synthetic RPC responses |
| Installed `@solana/web3.js` 1.98.4 client | 9 tests of PDA construction, approval, cluster/program checks, wallet rejection/mutation, RPC failure and no-retry behavior; transports are synthetic |
| Rust host contract | Five prior compiled serialization/layout tests; 13 prior generated host-IDL comparisons |
| SBPFv3 build | Anchor 1.2.0, official Anza platform-tools 1.57, Rust 1.95.0-dev; ELF flags 3; exact hash recorded in the build report |
| Compiled program execution | 28 tests in LiteSVM 1.5.0, including controlled clock boundaries, invalid signatures, account owner/PDA constraints, duplicate and immutable records, all three outcomes and overflow rollback |
| Connected local demo | Five actual SVM transactions: four successful operations and one expected rejection, with logs and decoded final state |
| Public network and wallet integration | Not deployed or verified |

See the [execution verification report](../evidence/solana-execution-2026-09-28/VERIFICATION.md), [local setup and reproduction guide](LOCAL_SVM_GUIDE.md), and [test matrix](TEST_PLAN.md). Prior host evidence is summarized in the [publication report](../evidence/PUBLICATION.md).

## Program contract

| Instruction | Enforced invariant |
|---|---|
| `create_question` | Creator signs; nonempty question no longer than 200 UTF-8 bytes; nonzero rules hash; future close and valid resolve schedule; nondefault resolver; deterministic question PDA |
| `submit_forecast` | Forecaster signs; probability is 0–10000 basis points; question is open and time is strictly before close; one immutable record per wallet/question |
| `resolve_question` | Designated resolver signs; time is at or after resolution time; exactly one YES/NO/VOID outcome; nonzero evidence hash; no replacement resolution |

A hash commits to supplied evidence, not its truth. A signer proves key control, not one-person-one-vote. There is no independent oracle, challenge window, privacy or commit/reveal mechanism. Test fixtures inject synthetic balances, manipulate the VM clock and sometimes construct invalid account states to probe rejection paths; these are test setup actions, not product capabilities.

## Run the local checks

After the one-time setup in the [guide](LOCAL_SVM_GUIDE.md), from the repository root:

```bash
node --test solana/tests/codec.test.mjs solana/tests/client.test.mjs solana/tests/svm.test.mjs
node solana/scripts/run-local-demo.mjs evidence/my-local-demo.json
```

The SVM tests require a real `.so` build and fail if it is missing. They do not silently switch to host functions, mocked program behavior or fixtures. All transaction keys are generated in memory for that process; the harness never reads a wallet file or sends RPC requests. Test signatures are local evidence only and have no public explorer meaning.

The build tool cache, `node_modules` and `target` are local development outputs, not starter-source contents. The Node lockfile pins installed dependencies. The recorded dependency audit has four moderate transitive advisories and zero high/critical advisories; this local verification does not certify the dependency tree for a public wallet application.

## Client and integration boundaries

`client/codec.mjs` encodes instructions and decodes accounts. `client/client.mjs` builds unsigned SDK instructions; those builders are now exercised against the compiled program in LiteSVM. Its `send` convenience method still requires individual approval and verifies devnet before requesting a connected wallet signature. That path has synthetic transport tests, not live-wallet proof.

`client/inspect-devnet.mjs` reads a configured public program, question and optional transaction. It checks cluster, executable flag, owner/discriminator and relevant instruction/signer. It does not prove source-to-deployment equality or outcome truth. Its raw RPC validator does not derive PDA curves; `RegistryClient.read` adds that check.

The program ID in source is a valid-format **local test identity**, not a verified public deployment. The local demo does not connect the generated Forecast Studio UI to a public cluster. The next integration gate is an explicitly authorized dedicated devnet program identity, deployment/source verification, real account inspection and one human-approved create/forecast/resolve journey with wallet rejection and RPC failure handling. Do not use a production wallet or silently discover a wallet elsewhere on the machine.

## Read-only inspection after a real deployment

Only use actual public identifiers supplied by the owner:

```bash
node solana/client/inspect-devnet.mjs \
  --allow-network \
  --program REAL_DEPLOYED_PROGRAM_ID \
  --question REAL_QUESTION_ACCOUNT \
  --signature REAL_TRANSACTION_SIGNATURE \
  --out /absolute/path/to/new-devnet-observation.json
```

The command performs reads only, uses the fixed devnet endpoint and refuses to overwrite an existing output. The identifiers above are placeholders. Never replace missing receipts with synthetic test signatures or label a failed RPC request as live evidence.
