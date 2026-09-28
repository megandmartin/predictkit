# Recorded local execution viewer

Open `index.html` directly, or use the local PredictKit server's `/solana-demo` route. This is a portable, read-only presentation of the recorded `local-demo.json` evidence. It does not execute a transaction, contact a model, connect a wallet or call an RPC.

Rebuild from the repository root after recording a new supported local demo:

```bash
python3 solana/demo/build_viewer.py
```

The builder reads `evidence/solana-execution-2026-09-28/local-demo.json`, validates the expected local execution shape, embeds the exact receipt bytes and their SHA-256, and writes `index.html` and `viewer-source.json`. It rejects a missing or incompatible report. Its validation is a presentation contract, not independent proof that the execution occurred.

The viewer includes the actual question, both recorded probabilities, five transaction results, decoded final account and original program logs. Account/signature copying and receipt download work locally. Native disclosures work without JavaScript. The source JSON download is byte-identical to the evidence file.

The display font is embedded from the existing `web/fonts/spacegrotesk-variable.ttf`; its complete existing SIL Open Font License is included in the evidence disclosure. Other text uses system fonts. No external assets are loaded. The route's CSP must allow the embedded font through `font-src data:`.

The visual system inherits PredictKit's Solana Signal palette, checkpoint mark and Space Grotesk display type. It does not redefine `DESIGN.md` or change the Studio themes.
