# First real multi-agent run — explicit local authorization

## What this can prove
One bounded run can prove eight distinct role requests, overlapping independent task intervals, structured artifact generation, exact founder approval and a useful private submission draft. It cannot prove autonomous coding/testing, live research, Solana execution or production safety.

The direct provider uses Python's standard library. Do not install `openai-agents` for this release. The API contract follows the official Responses/structured-output documentation; actual selected-model compatibility still needs this first live check.

## Before starting
Choose an API model available to your account that supports Responses and strict JSON-schema outputs. Check its current input/output token prices on the official pricing page; no price/model default is silently selected. Use a dedicated, limited API account/project where possible. Approve the spend yourself. ChatGPT subscription access is not treated as API authorization by this program.

Use only a sanitized sample brief: the provider receives the brief, relevant accepted artifacts and role/skill instructions. `store:false` is sent; this is not a blanket promise of zero provider retention. No provider key goes into a brief, browser file or downloadable evidence. Do not paste keys in chat.

See [LIVE_PREPARED.md](LIVE_PREPARED.md) for the reusable one-run launcher. Approve your own model, current rates and budget before use.

## Configure locally
In a shell in the project folder, set these values after replacing the placeholders:
```bash
export PREDICTKIT_MODEL='MODEL_YOU_SELECTED'
export PREDICTKIT_BUDGET_USD='YOUR_APPROVED_NUMERIC_BUDGET'
export PREDICTKIT_INPUT_USD_PER_MILLION='VERIFIED_NUMERIC_INPUT_RATE'
export PREDICTKIT_OUTPUT_USD_PER_MILLION='VERIFIED_NUMERIC_OUTPUT_RATE'
export PREDICTKIT_PRICE_CHECKED_ON='YYYY-MM-DD'
export PREDICTKIT_MAX_OUTPUT_TOKENS='8000'
```
The first four numeric placeholders are deliberately not runnable as-is. Unknown prices must not become zero dollars. A too-small budget refuses a request before dispatch; do not increase it automatically.

Use a password-style prompt so the key does not appear in shell history:
```bash
python3 - <<'PYCODE'
import getpass, os
key = getpass.getpass('API key (local, not saved): ')
if not key:
    raise SystemExit('No key supplied; no calls made.')
os.environ['OPENAI_API_KEY'] = key
os.execvp('python3', ['python3', 'predictkit.py', 'serve', '--provider', 'openai'])
PYCODE
```
`getpass` needs an interactive terminal; do not redirect this into an unattended process. Existing credentials are not searched or copied. The server fails before launch if required settings are missing. `.env.example` is a reference, not an automatically loaded secrets file.

## Launch and inspect
Open `http://127.0.0.1:8765/studio` for this generic setup (the one-run launcher uses port 8766). Confirm LIVE MODEL PROVIDER, review the sample brief and check the explicit paid-run box. Launch once. Independent discovery requests run in parallel; the chief synthesizes them. Read its memo and approve that exact version. Build roles run, static checks execute, then the reviewer receives the actual generated app source and report.

Check `/readiness`, open the generated app, and independently test the primary journey. Export the pack. Verify it without executing its contents:
```bash
python3 predictkit.py verify-pack /absolute/path/to/predictkit-run-pack.zip
```
No automatic submission or publication follows export.

## Collect the minimum evidence
Record the selected model, rate source/date, interpreter version, eight response IDs, request IDs when returned, usage totals, task timestamps, approval hashes, accepted artifact hashes, failures and manual browser results. Redact private prompts/account information before sharing. Internal hashes are not proof to an independent party that an API actually ran; preserve trace evidence and explain its provenance.

## Failure policy
An incomplete response, refusal, malformed output, invalid file, timeout or missing usage fails the run. There are no paid retries. Cancellation cannot undo a sent request; consult account usage when billing is unknown. A changed memo invalidates approval. Context over the declared size is rejected, not truncated silently. Fix a cause deliberately before starting a separately authorized new run.

**Budget boundary:** configured-price estimates/reservations are not a provider hard billing cap. Actual tokenization, pricing changes and uncertain requests can differ. The ledger makes that uncertainty visible; it does not guarantee an invoice total.

## Official references
- Responses structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Current pricing: https://developers.openai.com/api/docs/pricing
- Data controls: https://developers.openai.com/api/docs/guides/your-data
