# Optional one-run launcher

Each operator must prepare and authorize their own one-run plan. No authorization, key or paid session is transferred with this repository. `scripts/live_session.py` accepts a locally created plan and requests a key without echo in an interactive terminal.

Follow [LIVE_RUN.md](LIVE_RUN.md) to select a supported model, verify current provider rates and configure a bounded budget. The launcher does not start paid work merely by opening the server. The exact memo must still be approved in Studio. Its local reservations estimate spend; they are not a provider billing cap.

The plan schema is explicit in `read_plan` in `scripts/live_session.py`. It contains an ID, `approved_runs: 1`, the founder brief, the pricing source and non-secret environment configuration. Do not include an API key. Store the plan only under the ignored `.local/` directory.

```bash
python3 scripts/live_session.py --plan .local/my-plan.json --check
python3 scripts/live_session.py --plan .local/my-plan.json
```

The one-run claim is persisted before execution, so restarting cannot silently reuse it. A failed paid attempt does not authorize another attempt. Keep credentials out of chat, GitHub, Vercel and shared reports. Genuine provider execution remains a separate proof step.
