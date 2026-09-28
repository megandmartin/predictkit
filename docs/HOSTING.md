# Hosted preview and local Studio

The Vercel site is built with `python3 scripts/build_site.py` into `dist/`. It contains static HTML/CSS/JavaScript, local fonts, interactive off-chain examples, a source-derived skill catalog and a recorded local SVM demo. No secret environment variables are needed.

The long-running Python Studio is a separate local process. Run `python3 predictkit.py serve --open` to schedule workers, save artifacts and inspect a run. Do not deploy that filesystem-based runtime as a shared Vercel serverless function.

## Repeat a preview deployment

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
vercel link --project predictkit --yes
vercel deploy --target preview --yes
```

The project is configured with a static output directory and no dependency installation. Git-triggered automatic deployment is disabled so source pushes alone do not promote a production site. Use the explicit preview command after checks. Production promotion is a separate decision.

Vercel configuration follows its [static configuration](https://vercel.com/docs/project-configuration/vercel-json) and [Git deployment control](https://vercel.com/docs/project-configuration/git-configuration) documentation. The initial PredictKit preview is publicly viewable; no Vercel sign-in is required. Only reviewed static public material is served. Do not place any runtime key in hosted build settings.
