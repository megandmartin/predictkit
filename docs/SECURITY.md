# Safety and security model
This is a local prototype, not an audited hosted service.

## Enforced in code
Loopback binding; Host allowlist; same-origin API checks; per-process request token; request-size limits; validated brief; fixed role outputs; path-traversal/symlink rejection; bounded artifact sizes; no worker ownership of runtime/policy; no shell tools; generated HTML in a sandboxed iframe with external network access blocked; no generated server code execution; no automatic retries; max concurrency, call, output and elapsed limits.

The 28 September local build requires a session token for API reads as well as writes. The child CSP restricts preview subresources; a parent CSP also confines iframe navigation to the loopback origin. The external-navigation boundary was tested using a synthetic local canary. This is not an audited hosted service or a general-purpose secure runner. Never open unreviewed generated HTML outside the supplied preview.

## Explicitly not guaranteed
Hard dollar spend limits; adversarial security against the local machine owner; durable recovery; multi-tenant isolation; malicious model/provider resistance beyond the narrow tool boundary; complete secret detection; smart-contract correctness; regulatory permission; cancellation of an already accepted billable request. The regex secret check is defense-in-depth, not a general data-loss-prevention system.

## Private data
`.local/` is excluded from Git. A paid run sends its brief and selected artifact text to the provider. Do not put confidential customer or personal information in a shareable demo. Rehearsal fixtures are synthetic. Never bundle API credentials, auth caches, keypairs, private chat records, provider tokens or participants' unapproved projects.

## External actions
No blockchain write, real-money trade, publish, email, account change, public repo creation or official submission is implemented by the runtime. Adding one requires a separate narrowly scoped tool and execution-time authorization; a model's recommendation is not that authorization.

## Operating the demo
Do not use `0.0.0.0`, an open tunnel or a public VPS for this service without authentication and tenant hardening. Do not run generated tests on the host until a disposable execution boundary is supplied. Inspect a generated HTML export before opening it outside the supplied isolated preview.

## Reporting and response
Stop the run; preserve the local event evidence; revoke affected credentials at their provider; identify the scope; fix and add a regression test; re-run from clean inputs. No telemetry is automatically uploaded by this starter; provider inference is the only external path in configured live mode. No SDK tracing runs. The separate read-only Solana inspector makes public RPC reads only when its --allow-network flag is supplied; it does not run automatically.
