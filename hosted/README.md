# Static hosted preview

Build from the repository root with Python 3.11 or newer:

```sh
python3 scripts/build_site.py
python3 -m http.server 8773 --bind 127.0.0.1 --directory dist
```

The build has no package or network dependencies. `dist/` contains the landing page, hosted Studio walkthrough, source-backed skills catalog, dated evidence desk, local SVM receipt viewer and interactive reference app. It deliberately contains no Python server, provider credentials, paid-call form or runtime API requests. The full coordinator runs after downloading the source and running `python3 predictkit.py serve --open` locally.

Vercel should use `python3 scripts/build_site.py` as its build command and `dist` as its output directory. The deployment configuration handles extensionless routes. The generated pages use repository-root asset links.

The build reads the current local files; it does not overwrite them. It redacts the recorded SVM receipt's private compiler path, preserves the transaction/account values and original boundary, and includes provenance for the resulting public derivative. The viewer displays this disclosure and embeds that derivative as its downloadable receipt. The output validation checks plain-text files and encoded receipt data for local paths and runtime tokens. `SITE_BUILD.json` records deterministic hashes of the generated files.

The example iframe allows scripts only. A source-checked, bounded height message lets it fit its content without granting same-origin access. Its probabilities and outcomes are session-only simulation data. No external resources, live model calls or Solana network calls are required to use the preview.

## Verification

```sh
python3 -m unittest discover -s tests -p test_site_build.py -v
```

The optional maker browser probe in `hosted/qa/browser-preview.cjs` uses an already installed Playwright module, configurable with `PLAYWRIGHT_MODULE`, and a preview URL configurable with `PREDICTKIT_PREVIEW_URL`. It is not needed to build or host the site. The `hosted/qa/` folder is local maker evidence and may be omitted from the public source copy.
