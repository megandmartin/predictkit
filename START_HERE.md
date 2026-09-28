# Start here

From the repository root, run `python3 predictkit.py doctor`, then `python3 predictkit.py serve --open` with Python 3.11 or later. No API key is needed for rehearsal.

1. Open the homepage and choose **Open Studio**.
2. Edit the example brief and start a scripted rehearsal.
3. Inspect and approve the exact build memo before the build begins.
4. Open the generated app, try forecasting and resolution, and inspect role outputs.
5. Export the pack. Inspect `/readiness` to understand what that run proves.

`/skills` exposes each role's inputs, outputs and skills. `/solana-demo` shows recorded local SVM execution. The app examples remain off-chain simulations.

The hosted preview is a static introduction with interactive examples; the local Studio owns scheduling and files. See [hosting](docs/HOSTING.md), [how it works](docs/HOW_PREDICTKIT_WORKS.md) and [verification](evidence/PUBLICATION.md).

For optional paid generation, follow [live setup](docs/LIVE_RUN.md) and authorize your own model, current rates and budget. No key or spending authorization is transferred by downloading this repository.

For Solana engineering, follow [the local SVM guide](solana/LOCAL_SVM_GUIDE.md). Public-chain deployment and real-wallet integration remain separate work. Before claiming workshop readiness, complete a genuine model run, a connected chain-backed app and [three independent builder sessions](workshop/THREE_BUILDER_PILOT.md).
