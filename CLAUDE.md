# SC DataPack Pipeline — Claude Project Instructions

## CRITICAL: Deployment workflow

GitHub Pages is served from the ROOT of the `gh-pages` branch.
NOT from any folder on main. NOT from main at all.

```
gh-pages branch root/
  index.html              <- live index page
  ships_preview.html
  components_preview.html
  armor_preview.html
  weapons_preview.html
```

### To deploy a new or updated report:

```bash
git checkout gh-pages
cp <reports_dir>\<report>.html .
# edit index.html to add/update the card (match existing card style)
git add <report>.html index.html
git commit -m "feat: ..."
git push origin gh-pages
git checkout main
```

Index card style: `display: flex; flex-wrap: wrap` container, cards `width: 380px`.
Match `.card-icon / .card-title / .card-desc / .card-meta` pattern exactly.

---

## Repo structure (main branch)

```
repo root/
  runner.py           <- entry point (runs full pipeline)
  .env                <- user config (gitignored — never commit)
  .env.example        <- config template (committed)
  .gitignore
  .gitkeep files
  README.md
  CLAUDE.md           <- this file

  DOCS\
    README.md
    EXTRACTION_PLAN.md
    DATA_SOURCES.md

  SCRIPTS\
    README.md
    config\settings.py
    pipeline\
      extractor.py
      ships_preview.py
      components_preview.py
      armor_preview.py
      weapons_preview.py

  Tools\
    README.md
    unp4k-suite\      <- gitignored (user installs)
    venv\             <- gitignored (user creates)

  Data_Extraction\    <- gitignored (created on run)
  HTML\               <- gitignored (created on run)
```

## Settings / config

`SCRIPTS\config\settings.py` reads from `.env` in repo root then env vars.
Required: `SC_P4K_PATH`, `SC_UNP4K_EXE`
Optional: `SC_OUTPUT_DIR` (default: Data_Extraction\), `SC_REPORTS_DIR` (default: HTML\)

## Phase status (all complete as of 2026-02-27)

- [x] extractor.py — selective extract (Foundry + Localization only)
- [x] ships_preview.py — 276 ships, gh-pages live
- [x] components_preview.py — 2,516 components, gh-pages live
- [x] armor_preview.py — 2,230+ items, gh-pages live
- [x] weapons_preview.py — 166 ship + 333 FPS + 102 attachments, gh-pages live
- [x] runner.py — full orchestrator at repo root
