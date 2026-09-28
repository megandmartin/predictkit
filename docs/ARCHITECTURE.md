# Architecture and execution contract — v0.2

```text
Frozen founder brief
   ├── Research ────┐
   ├── Product ─────┤  independent requests, same frozen inputs
   └── Architect ───┘
          Chief of staff
          exact brief + memo approval
   ├── App engineer ────┐
   ├── Market designer ─┤  independent requests, same frozen inputs
   └── Submission ──────┘
          static artifact checks
          Reviewer: app code + accepted artifacts + check report
          Private draft pack + separate readiness gates
```

`server.py` owns loopback HTTP, host/origin and session checks. `runtime.py` owns dependencies, concurrency, approvals, input snapshots, events, acceptance and packaging. `http_provider.py` owns the fixed HTTPS request/response boundary. `spend.py` reserves estimated cost before dispatch. `skills.py` loads specific reviewed local files. `contracts.py` validates brief and outputs. `readiness.py` evaluates available evidence and verifies exported ZIP hashes without extraction. `web/` contains the Studio and Evidence Desk.

## Artifact handoff
Workers return complete files only at their declared paths. The coordinator rejects invalid paths, collisions, incomplete contracts and disallowed content before writing. Inputs to parallel siblings are frozen. Relevant accepted artifacts are checked against their recorded hash before being supplied to a downstream role. No worker edits the runtime or source registry.

## State and recovery
Run directories hold brief, state, event journal, artifacts, verification, manifest and readiness files. The journal is not tamper-proof against the machine owner. Pause holds new tasks; active calls may finish. Stop prevents new work and cancels local awaits; it cannot revoke or unbill an already accepted API request. Unknown billing retains a reservation. No automatic paid retry occurs. The local build restores the latest saved record for inspection after restart and marks unfinished work interrupted. History selection never resumes work or spends money; a new run needs a new explicit launch and approval.

## Spending
Budget and input/output token rates are owner-configured, with a checked date. Reservations deliberately overestimate ordinary input text, then reconcile to provider-reported token counts using those configured rates. Cached input is conservatively undiscounted. This is not a certified tokenizer, authoritative invoice or provider-side hard ceiling. Limit output, requests, concurrency and runtime separately. Use account-side safeguards where available.

## Execution boundary
The server does not execute generated code. App preview runs only in a restricted iframe with no same-origin privilege and no outbound network. The JavaScript Solana client is not injected into generated apps. Before any generated app gets execution privileges, build a disposable environment without inherited credentials and test its exact commands/network scope.
